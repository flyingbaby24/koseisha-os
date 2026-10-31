import {
  BufferAttribute,
  BufferGeometry,
  Points,
  ShaderMaterial,
  Vector3,
  type Camera,
  type Scene,
} from "three";

import type { MapNode } from "../api/mapTypes";
import { sourceStyle } from "../config/sourceStyles";
import { buildNodeIndex, type NodeIndex } from "./nodeIndex";
import { NodeState, type VisualState } from "./nodeVisualState";
import { ndcToScreen } from "./picking";
import {
  computeBounds,
  computeTransform,
  type ProjectionBounds,
  type ProjectionTransform,
} from "./projectionBounds";

/**
 * The document cloud.
 *
 * ## Why THREE.Points rather than InstancedMesh
 *
 * Both were considered. Points wins for this data:
 *
 * - One draw call and three floats per node. At 4915 nodes that is ~59 KB of
 *   position data; the same corpus as InstancedMesh needs a 16-float matrix
 *   each (~315 KB) plus real sphere geometry, for dots a few pixels wide where
 *   the extra geometry is never visible.
 * - It scales to the 25k-50k range this has to survive without changing shape.
 * - `gl_PointSize` attenuation gives the depth cue the map needs for free.
 *
 * InstancedMesh would only pay off if nodes needed genuine 3D form, per-node
 * rotation, or lighting. They do not. Its other advantage — cheap per-instance
 * raycasting — is not decisive either: T4 resolves a pick to a *buffer index*
 * through `NodeIndex`, which works identically for both, and a spatial index
 * over the position array beats per-object raycasting in both cases.
 *
 * Positions are written in raw projection space. The uniform scale and centre
 * offset live on this object's transform, so the semantic geometry stays in
 * the data exactly as UMAP produced it.
 */
export class NodeRenderer {
  readonly object: Points;
  /**
   * The emphasis layer: only nodes at Saved or above (results, saved works,
   * hover, selection) — tens to hundreds of points, never the corpus.
   *
   * Drawn after the cloud without depth testing, so a selected document deep
   * inside a dense region is never hidden behind thousands of neighbours, and
   * in state order, so the selection is always painted last. A second draw
   * call of a few hundred points is the whole cost; there is no post-process
   * and no per-node object.
   */
  readonly emphasisObject: Points;

  private readonly geometry: BufferGeometry;
  private readonly material: ShaderMaterial;
  private readonly emphasisGeometry: BufferGeometry;
  private readonly emphasisMaterial: ShaderMaterial;
  private emphasisCapacity = 0;

  private currentIndex: NodeIndex = buildNodeIndex([]);
  private currentBounds: ProjectionBounds = computeBounds([]);
  private currentTransform: ProjectionTransform = computeTransform(this.currentBounds);

  /** Reused across picks so hover allocates nothing per pointer move. */
  private screenBuffer = new Float32Array(0);
  private readonly scratchVector = new Vector3();

  constructor() {
    this.geometry = new BufferGeometry();
    this.material = createNodeMaterial();

    this.object = new Points(this.geometry, this.material);
    this.object.name = "ThoughtMapNodes";
    // T4 installs real picking. Until then nothing should resolve a hit here.
    this.object.raycast = () => {};
    this.object.visible = false;

    this.emphasisGeometry = new BufferGeometry();
    this.emphasisGeometry.setDrawRange(0, 0);
    this.emphasisMaterial = createEmphasisMaterial(this.material);
    this.emphasisObject = new Points(this.emphasisGeometry, this.emphasisMaterial);
    this.emphasisObject.name = "ThoughtMapEmphasis";
    this.emphasisObject.raycast = () => {};
    // A handful of points whose positions change with every search: a
    // bounding sphere would cost more to maintain than drawing them does.
    this.emphasisObject.frustumCulled = false;
    this.emphasisObject.renderOrder = 2;
    this.emphasisObject.visible = false;
  }

  get nodeIndex(): NodeIndex {
    return this.currentIndex;
  }

  get bounds(): ProjectionBounds {
    return this.currentBounds;
  }

  get transform(): ProjectionTransform {
    return this.currentTransform;
  }

  get count(): number {
    return this.currentIndex.nodeIndexToDocId.length;
  }

  addTo(scene: Scene): void {
    scene.add(this.object);
    scene.add(this.emphasisObject);
  }

  /**
   * Keep point size in real pixels as the viewport changes.
   *
   * `gl_PointSize` is in device pixels, so a world-space size has to be
   * converted with the same perspective term the projection matrix uses:
   * `bufferHeight / (2 * tan(fov / 2))`. Without this the points are sized by
   * an arbitrary constant and end up sub-pixel at a normal viewing distance —
   * drawn, counted by the renderer, and invisible.
   */
  setViewportScale(drawingBufferHeight: number, fovDegrees: number, pixelRatio = 1): void {
    const fov = Math.min(179, Math.max(1, fovDegrees));
    const halfFov = (fov * Math.PI) / 360;
    const scale = Math.max(1, drawingBufferHeight) / (2 * Math.tan(halfFov));
    // Uniform objects are shared with the emphasis material, so one write
    // keeps both layers on the same scale.
    this.material.uniforms["uProjectionScale"]!.value = scale;
    this.material.uniforms["uPixelRatio"]!.value =
      Number.isFinite(pixelRatio) && pixelRatio > 0 ? pixelRatio : 1;
  }

  /**
   * Depth cue: nodes beyond what the camera is looking at recede.
   *
   * Two uniform writes per rendered frame, nothing per node. Without it a
   * 64k-point cloud reads as a flat texture; with it the near side of the
   * space is visibly in front of the far side while orbiting.
   */
  setDepthCue(focusDistance: number): void {
    const extent = Math.max(1e-3, this.worldExtent);
    const near = Math.max(0, focusDistance - extent * 0.08);
    this.material.uniforms["uFadeNear"]!.value = near;
    this.material.uniforms["uFadeFar"]!.value = near + extent * 0.9;
  }

  /**
   * Replace the cloud with a new set of nodes.
   *
   * Buffers are reallocated once per load, not per frame. Nothing here runs on
   * the render loop.
   */
  setNodes(nodes: readonly MapNode[]): void {
    this.currentIndex = buildNodeIndex(nodes);
    this.currentBounds = computeBounds(nodes);
    this.currentTransform = computeTransform(this.currentBounds);

    this.emphasisGeometry.setDrawRange(0, 0);
    this.emphasisObject.visible = false;

    if (nodes.length === 0) {
      this.geometry.setDrawRange(0, 0);
      this.object.visible = false;
      return;
    }

    const positions = new Float32Array(nodes.length * 3);
    const colors = new Float32Array(nodes.length * 3);

    for (let index = 0; index < nodes.length; index += 1) {
      const node = nodes[index]!;
      const offset = index * 3;

      positions[offset] = node.x;
      positions[offset + 1] = node.y;
      positions[offset + 2] = node.z;

      // Unknown sources fall back rather than throwing, so a new namespace in
      // the corpus still renders.
      const [r, g, b] = sourceStyle(node.source).color;
      colors[offset] = r;
      colors[offset + 1] = g;
      colors[offset + 2] = b;
    }

    // Visual state lives in its own attribute so a search only rewrites this
    // one small array — positions and colours are never touched again. Rank
    // emphasis and the saved flag only matter to the emphasis layer, which
    // carries its own copies for the few nodes it draws.
    const state = new Float32Array(nodes.length).fill(NodeState.Normal);

    this.geometry.setAttribute("position", new BufferAttribute(positions, 3));
    this.geometry.setAttribute("color", new BufferAttribute(colors, 3));
    this.geometry.setAttribute("aState", new BufferAttribute(state, 1));
    this.geometry.setDrawRange(0, nodes.length);
    this.geometry.computeBoundingSphere();
    this.geometry.computeBoundingBox();

    // Denser corpora need smaller points to stay legible in the same volume.
    this.material.uniforms["uPointWorldSize"]!.value = pointSizeForCount(nodes.length);

    // One uniform scale for all three axes, plus a centre offset. Never
    // per-axis: that would stretch the space and misstate semantic distance.
    const { scale, offset } = this.currentTransform;
    this.object.scale.setScalar(scale);
    this.object.position.set(offset.x, offset.y, offset.z);
    this.object.updateMatrixWorld(true);

    // Same raw coordinates, same transform: the layers can never drift apart.
    this.emphasisObject.scale.copy(this.object.scale);
    this.emphasisObject.position.copy(this.object.position);
    this.emphasisObject.updateMatrixWorld(true);

    this.object.visible = true;
  }

  /**
   * Apply new visual state.
   *
   * Copies into the existing state array and flags it dirty; no cloud
   * geometry is recreated, so a search costs one Float32Array write rather
   * than rebuilding 63,891 positions. The emphasis layer is rewritten in
   * place for the handful of nodes it draws.
   */
  applyVisualState(visual: VisualState): void {
    const stateAttribute = this.geometry.getAttribute("aState") as BufferAttribute | undefined;
    if (!stateAttribute) {
      return;
    }

    const count = Math.min(this.count, visual.state.length);
    (stateAttribute.array as Float32Array).set(visual.state.subarray(0, count));
    stateAttribute.needsUpdate = true;

    this.writeEmphasis(visual, count);
  }

  /** Number of nodes the emphasis layer is currently drawing. */
  get emphasisCount(): number {
    return this.emphasisGeometry.drawRange.count;
  }

  private writeEmphasis(visual: VisualState, nodeCount: number): void {
    const source = this.geometry.getAttribute("position") as BufferAttribute | undefined;
    const sourceColor = this.geometry.getAttribute("color") as BufferAttribute | undefined;
    const indices = visual.emphasised.filter((index) => index >= 0 && index < nodeCount);

    if (!source || !sourceColor || indices.length === 0) {
      this.emphasisGeometry.setDrawRange(0, 0);
      this.emphasisObject.visible = false;
      return;
    }

    this.ensureEmphasisCapacity(indices.length);

    const positions = this.emphasisGeometry.getAttribute("position") as BufferAttribute;
    const colors = this.emphasisGeometry.getAttribute("color") as BufferAttribute;
    const states = this.emphasisGeometry.getAttribute("aState") as BufferAttribute;
    const emphasis = this.emphasisGeometry.getAttribute("aEmphasis") as BufferAttribute;
    const saved = this.emphasisGeometry.getAttribute("aSaved") as BufferAttribute;

    const sourcePositions = source.array as Float32Array;
    const sourceColors = sourceColor.array as Float32Array;
    const outPositions = positions.array as Float32Array;
    const outColors = colors.array as Float32Array;

    for (let slot = 0; slot < indices.length; slot += 1) {
      const index = indices[slot]!;
      const from = index * 3;
      const to = slot * 3;
      outPositions[to] = sourcePositions[from]!;
      outPositions[to + 1] = sourcePositions[from + 1]!;
      outPositions[to + 2] = sourcePositions[from + 2]!;
      outColors[to] = sourceColors[from]!;
      outColors[to + 1] = sourceColors[from + 1]!;
      outColors[to + 2] = sourceColors[from + 2]!;
      (states.array as Float32Array)[slot] = visual.state[index]!;
      (emphasis.array as Float32Array)[slot] = visual.emphasis[index]!;
      (saved.array as Float32Array)[slot] = visual.saved[index]!;
    }

    for (const attribute of [positions, colors, states, emphasis, saved]) {
      attribute.needsUpdate = true;
    }
    this.emphasisGeometry.setDrawRange(0, indices.length);
    this.emphasisObject.visible = true;
  }

  /** Grow (never per update) the emphasis buffers to hold `count` nodes. */
  private ensureEmphasisCapacity(count: number): void {
    if (count <= this.emphasisCapacity) {
      return;
    }
    let capacity = Math.max(64, this.emphasisCapacity);
    while (capacity < count) {
      capacity *= 2;
    }
    this.emphasisCapacity = capacity;

    this.emphasisGeometry.setAttribute(
      "position",
      new BufferAttribute(new Float32Array(capacity * 3), 3),
    );
    this.emphasisGeometry.setAttribute("color", new BufferAttribute(new Float32Array(capacity * 3), 3));
    this.emphasisGeometry.setAttribute("aState", new BufferAttribute(new Float32Array(capacity), 1));
    this.emphasisGeometry.setAttribute("aEmphasis", new BufferAttribute(new Float32Array(capacity), 1));
    this.emphasisGeometry.setAttribute("aSaved", new BufferAttribute(new Float32Array(capacity), 1));
  }

  /**
   * Project every node to CSS-pixel screen space for picking.
   *
   * Writes into a reused buffer as [x, y, depth] triples. Called once per pick
   * or hover, never per frame.
   */
  projectToScreen(camera: Camera, width: number, height: number): Float32Array {
    const count = this.count;
    const required = count * 3;

    if (this.screenBuffer.length < required) {
      this.screenBuffer = new Float32Array(required);
    }

    const position = this.geometry.getAttribute("position") as BufferAttribute | undefined;
    if (!position || count === 0) {
      return this.screenBuffer;
    }

    this.object.updateMatrixWorld();
    camera.updateMatrixWorld();

    for (let index = 0; index < count; index += 1) {
      this.scratchVector
        .set(position.getX(index), position.getY(index), position.getZ(index))
        .applyMatrix4(this.object.matrixWorld)
        .project(camera);

      const screen = ndcToScreen(this.scratchVector.x, this.scratchVector.y, width, height);
      const offset = index * 3;
      this.screenBuffer[offset] = screen.x;
      this.screenBuffer[offset + 1] = screen.y;
      this.screenBuffer[offset + 2] = this.scratchVector.z;
    }

    return this.screenBuffer;
  }

  /** World-space position of one node, for camera focus. */
  worldPositionOf(index: number, target = new Vector3()): Vector3 | null {
    const position = this.geometry.getAttribute("position") as BufferAttribute | undefined;
    if (!position || index < 0 || index >= this.count) {
      return null;
    }

    this.object.updateMatrixWorld();
    return target
      .set(position.getX(index), position.getY(index), position.getZ(index))
      .applyMatrix4(this.object.matrixWorld);
  }

  /** Widest world-space extent of the cloud, used to derive focus distance. */
  get worldExtent(): number {
    return this.currentBounds.maxExtent * this.currentTransform.scale;
  }

  clear(): void {
    this.setNodes([]);
  }

  dispose(): void {
    this.geometry.dispose();
    this.material.dispose();
    this.emphasisGeometry.dispose();
    this.emphasisMaterial.dispose();
    this.object.removeFromParent();
    this.emphasisObject.removeFromParent();
  }
}

/** Corpus size the base point diameter was tuned against (phase T3). */
export const REFERENCE_NODE_COUNT = 4915;

/** Base diameter, in world units, at REFERENCE_NODE_COUNT. */
const REFERENCE_POINT_SIZE = 0.7;

/**
 * Point diameter for a corpus of `count` documents.
 *
 * The map is always scaled to the same world extent, so a larger corpus packs
 * more documents into the same volume. Holding the diameter fixed made 63,891
 * nodes overlap into blobs where 4,915 read as a field of distinct points.
 *
 * Screen coverage goes as the square of the radius, so keeping total ink
 * roughly constant means the radius scales with 1/sqrt(count). Clamped at both
 * ends: never so small it disappears, never so large it overlaps.
 */
export function pointSizeForCount(count: number): number {
  if (!Number.isFinite(count) || count <= 0) {
    return REFERENCE_POINT_SIZE;
  }
  const scaled = REFERENCE_POINT_SIZE * Math.sqrt(REFERENCE_NODE_COUNT / count);
  return Math.min(REFERENCE_POINT_SIZE, Math.max(0.16, scaled));
}

/**
 * The document cloud: soft round points with distance attenuation and a depth
 * cue.
 *
 * Normal blending without depth writes. Additive blending would saturate dense
 * regions to flat white and destroy exactly the density structure the map
 * exists to show; depth *writes* would let each soft sprite's transparent
 * corners punch dark holes in the points behind it, which is what made dense
 * regions read as blotches. Without them, density reads as colour that
 * deepens where documents gather.
 *
 * Nodes at Saved or above are skipped here: the emphasis layer draws them.
 */
function createNodeMaterial(): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: {
      // Diameter of one document in *world* units, i.e. after the object's
      // uniform scale. Set per corpus by `pointSizeForCount`, because the map
      // is always fitted to the same world extent: more documents means the
      // same volume holds more of them, so each has to be smaller.
      uPointWorldSize: { value: pointSizeForCount(REFERENCE_NODE_COUNT) },
      // Replaced on the first resize; this default matches a 900px viewport at
      // 50° so the very first frame is already sized sensibly.
      uProjectionScale: { value: 965.0 },
      uPixelRatio: { value: 1.0 },
      // CSS pixels; multiplied by the pixel ratio in the shader so a point
      // looks the same size on a standard and a high-density display.
      uMinSize: { value: 1.25 },
      // Ceiling for an ordinary node. Emphasised states multiply this by their
      // own scale, so a selected node still stands out when zoomed in, but the
      // background cloud can no longer balloon into overlapping blobs.
      uMaxSize: { value: 9.0 },
      uOpacity: { value: 0.8 },
      // View-space depth band over which nodes recede. Set per frame from the
      // camera's distance to its target (`setDepthCue`).
      uFadeNear: { value: 60.0 },
      uFadeFar: { value: 160.0 },
    },
    vertexShader: /* glsl */ `
      attribute vec3 color;
      attribute float aState;

      varying vec3 vColor;
      varying float vAlpha;

      uniform float uPointWorldSize;
      uniform float uProjectionScale;
      uniform float uPixelRatio;
      uniform float uMinSize;
      uniform float uMaxSize;
      uniform float uOpacity;
      uniform float uFadeNear;
      uniform float uFadeFar;

      // Must match NodeState in nodeVisualState.ts.
      const float STATE_DIMMED = 0.0;
      const float STATE_SAVED  = 2.0;

      // Cool slate that non-results drift toward while a search is active, so
      // the structure stays legible but stops competing for attention.
      const vec3 RECEDE = vec3(0.30, 0.38, 0.52);

      void main() {
        if (aState > STATE_SAVED - 0.5) {
          // Drawn, larger and on top, by the emphasis layer.
          vColor = vec3(0.0);
          vAlpha = 0.0;
          gl_PointSize = 0.0;
          gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
          return;
        }

        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        float depth = max(0.001, -mvPosition.z);
        // 1 at and in front of the focus, falling to 0 at the far side.
        float near = 1.0 - smoothstep(uFadeNear, uFadeFar, depth);

        float sizeScale = 1.0;
        float alpha = uOpacity;
        vec3 rgb = color;

        if (aState < STATE_DIMMED + 0.5) {
          // Dimmed, never removed: the surrounding space is still context.
          sizeScale = 0.78;
          alpha = uOpacity * 0.24;
          rgb = mix(color, RECEDE, 0.5);
        }

        vColor = rgb * mix(0.5, 1.0, near);
        vAlpha = alpha * mix(0.42, 1.0, near);

        // Perspective attenuation in real pixels: nearer documents read
        // larger, which is the main depth cue while orbiting.
        //
        // mvPosition already carries the object's uniform scale, so
        // uPointWorldSize is used as-is — applying the scale again here would
        // double-count it and inflate every point.
        float size = uPointWorldSize * sizeScale * uProjectionScale / depth;
        gl_PointSize = clamp(size, uMinSize * uPixelRatio, uMaxSize * sizeScale * uPixelRatio);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: /* glsl */ `
      varying vec3 vColor;
      varying float vAlpha;

      void main() {
        float distance = length(gl_PointCoord - vec2(0.5));
        if (distance > 0.5) {
          discard;
        }
        // Round sprite with a soft edge and a slightly brighter core.
        float falloff = smoothstep(0.5, 0.12, distance);
        float core = smoothstep(0.24, 0.0, distance);
        gl_FragColor = vec4(vColor * (0.88 + 0.3 * core), vAlpha * falloff);
      }
    `,
    transparent: true,
    depthWrite: false,
    depthTest: true,
  });
}

/**
 * The emphasis layer's material. Shares the cloud's uniform objects, so size,
 * pixel ratio and depth cue can never disagree between the two layers.
 *
 * One glyph per meaning, readable without colour as well as with it:
 *
 *   saved      mint ring around a small source-coloured core
 *   result     cyan-tinted glowing dot, stronger with rank (top: white rim)
 *   hovered    white ring
 *   selected   gold reticle — ring, gap, bright core — and a minimum size
 *
 * A saved document that is also a result, hovered or selected keeps a thin
 * mint outer rim, so being outranked never erases "this is in your library".
 */
function createEmphasisMaterial(base: ShaderMaterial): ShaderMaterial {
  return new ShaderMaterial({
    uniforms: base.uniforms,
    vertexShader: /* glsl */ `
      attribute vec3 color;
      attribute float aState;
      attribute float aEmphasis;
      attribute float aSaved;

      varying vec3 vColor;
      varying float vState;
      varying float vEmphasis;
      varying float vSaved;
      varying float vNear;

      uniform float uPointWorldSize;
      uniform float uProjectionScale;
      uniform float uPixelRatio;
      uniform float uMaxSize;
      uniform float uFadeNear;
      uniform float uFadeFar;

      void main() {
        vColor = color;
        vState = aState;
        vEmphasis = aEmphasis;
        vSaved = aSaved;

        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        float depth = max(0.001, -mvPosition.z);
        vNear = 1.0 - smoothstep(uFadeNear, uFadeFar, depth);

        // Size relative to an ordinary node, and a floor in CSS pixels so an
        // emphasised node never shrinks out of sight when zoomed out.
        float sizeScale;
        float minPx;
        if (aState < 2.5) {          // saved
          sizeScale = 1.9;
          minPx = 7.0;
        } else if (aState < 3.5) {   // result
          sizeScale = 2.0 + 0.7 * aEmphasis;
          minPx = 6.0 + 3.0 * aEmphasis;
        } else if (aState < 4.5) {   // top result
          sizeScale = 2.9;
          minPx = 11.0;
        } else if (aState < 5.5) {   // hovered
          sizeScale = 3.0;
          minPx = 13.0;
        } else {                     // selected
          sizeScale = 3.8;
          minPx = 18.0;
        }
        if (aSaved > 0.5 && aState > 2.5) {
          // Room for the saved rim outside the state's own glyph.
          sizeScale *= 1.15;
          minPx += 3.0;
        }

        float size = uPointWorldSize * sizeScale * uProjectionScale / depth;
        float lower = minPx * uPixelRatio;
        float upper = max(lower, uMaxSize * sizeScale * uPixelRatio);
        gl_PointSize = clamp(size, lower, upper);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: /* glsl */ `
      varying vec3 vColor;
      varying float vState;
      varying float vEmphasis;
      varying float vSaved;
      varying float vNear;

      // Semantic colours. Must match --tm-query, --tm-document and
      // --tm-saved in main.css, so the map, the result list and the radar use
      // one vocabulary.
      const vec3 QUERY = vec3(0.31, 0.82, 1.0);
      const vec3 DOCUMENT = vec3(1.0, 0.77, 0.42);
      const vec3 SAVED = vec3(0.61, 0.91, 0.77);

      // Anti-aliased annulus between two radii (sprite space, 0..0.5).
      float band(float d, float inner, float outer) {
        return smoothstep(inner - 0.035, inner, d) * (1.0 - smoothstep(outer, outer + 0.035, d));
      }

      void main() {
        float d = length(gl_PointCoord - vec2(0.5));
        if (d > 0.5) {
          discard;
        }

        bool saved = vSaved > 0.5;
        float edge = saved && vState > 2.5 ? 0.41 : 0.5;
        vec3 rgb;
        float alpha;

        if (vState < 2.5) {
          // Saved: ring and a small core in the document's own source colour.
          float ring = band(d, 0.30, 0.44);
          float core = 1.0 - smoothstep(0.12, 0.17, d);
          rgb = mix(vColor, SAVED, ring);
          alpha = max(ring * 0.95, core * 0.85);
        } else if (vState < 4.5) {
          // Result: the query's colour, glowing in proportion to rank.
          vec3 tint = mix(vColor, QUERY, 0.6);
          float core = 1.0 - smoothstep(0.10, 0.22, d);
          float glow = pow(1.0 - smoothstep(0.0, edge, d), 2.0) * (0.35 + 0.35 * vEmphasis);
          rgb = mix(tint, vec3(1.0), core * (0.3 + 0.45 * vEmphasis));
          alpha = clamp(core + glow, 0.0, 1.0);
          if (vState > 3.5) {
            float rim = band(d, edge - 0.11, edge - 0.04);
            rgb = mix(rgb, vec3(1.0), rim);
            alpha = max(alpha, rim);
          }
        } else if (vState < 5.5) {
          // Hovered: a white ring; the core keeps its source identity.
          float ring = band(d, 0.29, 0.38);
          float core = 1.0 - smoothstep(0.12, 0.19, d);
          rgb = mix(mix(vColor, vec3(1.0), 0.45), vec3(1.0), ring);
          alpha = max(ring, core * 0.95);
        } else {
          // Selected: a gold reticle — unmistakable at any density.
          float ring = band(d, 0.27, 0.37);
          float core = 1.0 - smoothstep(0.09, 0.15, d);
          float halo = (1.0 - smoothstep(0.37, edge, d)) * step(0.37, d) * 0.28;
          rgb = mix(DOCUMENT, vec3(1.0), core * 0.55);
          alpha = max(max(ring, core), halo);
        }

        if (saved && vState > 2.5) {
          float rim = band(d, 0.44, 0.48);
          rgb = mix(rgb, SAVED, rim);
          alpha = max(alpha, rim);
        }

        // Emphasis recedes far less than the cloud: it must stay findable.
        alpha *= mix(0.7, 1.0, vNear);
        if (alpha < 0.01) {
          discard;
        }
        gl_FragColor = vec4(rgb, alpha);
      }
    `,
    transparent: true,
    depthWrite: false,
    // Always over the cloud. The cloud writes no depth anyway; disabling the
    // test makes the guarantee explicit rather than incidental.
    depthTest: false,
  });
}
