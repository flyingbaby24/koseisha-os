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

  private readonly geometry: BufferGeometry;
  private readonly material: ShaderMaterial;

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
  setViewportScale(drawingBufferHeight: number, fovDegrees: number): void {
    const fov = Math.min(179, Math.max(1, fovDegrees));
    const halfFov = (fov * Math.PI) / 360;
    const scale = Math.max(1, drawingBufferHeight) / (2 * Math.tan(halfFov));
    this.material.uniforms["uProjectionScale"]!.value = scale;
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

    // Visual state lives in its own attributes so a search only rewrites
    // these two small arrays — positions and colours are never touched again.
    const state = new Float32Array(nodes.length).fill(NodeState.Normal);
    const emphasis = new Float32Array(nodes.length);

    this.geometry.setAttribute("position", new BufferAttribute(positions, 3));
    this.geometry.setAttribute("color", new BufferAttribute(colors, 3));
    this.geometry.setAttribute("aState", new BufferAttribute(state, 1));
    this.geometry.setAttribute("aEmphasis", new BufferAttribute(emphasis, 1));
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

    this.object.visible = true;
  }

  /**
   * Apply new visual state.
   *
   * Copies into the existing attribute arrays and flags them dirty. No
   * geometry is recreated, so a search costs two Float32Array writes rather
   * than rebuilding 4,915 positions.
   */
  applyVisualState(visual: VisualState): void {
    const stateAttribute = this.geometry.getAttribute("aState") as BufferAttribute | undefined;
    const emphasisAttribute = this.geometry.getAttribute("aEmphasis") as
      | BufferAttribute
      | undefined;

    if (!stateAttribute || !emphasisAttribute) {
      return;
    }

    const count = Math.min(this.count, visual.state.length);
    (stateAttribute.array as Float32Array).set(visual.state.subarray(0, count));
    (emphasisAttribute.array as Float32Array).set(visual.emphasis.subarray(0, count));

    stateAttribute.needsUpdate = true;
    emphasisAttribute.needsUpdate = true;
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
    this.object.removeFromParent();
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
 * Soft round luminous points with distance attenuation.
 *
 * Normal blending with depth writing, not additive: additive would saturate
 * dense regions to flat white and destroy exactly the density structure the
 * map exists to show.
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
      uMinSize: { value: 1.25 },
      // Ceiling for an ordinary node. Emphasised states multiply this by their
      // own scale, so a selected node still stands out when zoomed in, but the
      // background cloud can no longer balloon into overlapping blobs.
      uMaxSize: { value: 9.0 },
      uOpacity: { value: 0.95 },
    },
    vertexShader: /* glsl */ `
      attribute vec3 color;
      attribute float aState;
      attribute float aEmphasis;

      varying vec3 vColor;
      varying float vState;
      varying float vAlpha;

      uniform float uPointWorldSize;
      uniform float uProjectionScale;
      uniform float uMinSize;
      uniform float uMaxSize;
      uniform float uOpacity;

      // Must match NodeState in nodeVisualState.ts.
      const float STATE_DIMMED     = 0.0;
      const float STATE_NORMAL     = 1.0;
      const float STATE_SAVED      = 2.0;
      const float STATE_RESULT     = 3.0;
      const float STATE_TOP_RESULT = 4.0;
      const float STATE_HOVERED    = 5.0;
      const float STATE_SELECTED   = 6.0;

      void main() {
        vState = aState;

        // Size and opacity per state. Dimmed nodes stay visible so the
        // surrounding thought space keeps providing context.
        float sizeScale = 1.0;
        float alpha = uOpacity;
        float lift = 0.0;

        if (aState < STATE_NORMAL - 0.5) {          // dimmed
          sizeScale = 0.72;
          alpha = uOpacity * 0.26;
        } else if (aState < STATE_SAVED - 0.5) {    // normal
          sizeScale = 1.0;
        } else if (aState < STATE_RESULT - 0.5) {   // saved
          // Deliberately gentle: a large library must stay legible as a
          // scattering of marked points, never compete with search results.
          sizeScale = 1.25;
          lift = 0.18;
        } else if (aState < STATE_TOP_RESULT - 0.5) { // result
          sizeScale = 1.5 + 0.5 * aEmphasis;
          lift = 0.35 + 0.25 * aEmphasis;
        } else if (aState < STATE_HOVERED - 0.5) {  // top result
          sizeScale = 2.35;
          lift = 0.75;
        } else if (aState < STATE_SELECTED - 0.5) { // hovered
          sizeScale = 2.1;
          lift = 0.6;
        } else {                                     // selected
          sizeScale = 2.9;
          lift = 0.95;
        }

        // Brighten toward white rather than replacing the source colour, so a
        // node keeps its source identity while emphasised.
        vColor = mix(color, vec3(1.0), lift * 0.55);
        vAlpha = alpha;

        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);

        // Perspective attenuation in real pixels: nearer documents read
        // larger, which is the main depth cue while orbiting.
        //
        // mvPosition already carries the object's uniform scale, so
        // uPointWorldSize is used as-is — applying the scale again here would
        // double-count it and inflate every point.
        float size = uPointWorldSize * sizeScale * uProjectionScale / max(0.001, -mvPosition.z);

        gl_PointSize = clamp(size, uMinSize, uMaxSize * sizeScale);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: /* glsl */ `
      varying vec3 vColor;
      varying float vState;
      varying float vAlpha;

      void main() {
        vec2 offset = gl_PointCoord - vec2(0.5);
        float distance = length(offset);
        if (distance > 0.5) {
          discard;
        }

        // Round the square point sprite and give it a soft core.
        float falloff = smoothstep(0.5, 0.08, distance);

        // Selected and hovered nodes get a bright ring, which stays legible
        // even where the cloud is dense and a brighter dot would be lost.
        float ring = 0.0;
        if (vState > 4.5) {
          ring = smoothstep(0.5, 0.42, distance) * smoothstep(0.30, 0.40, distance);
        } else if (vState > 1.5 && vState < 2.5) {
          // Saved: a faint outer halo. Present enough to spot, quiet enough
          // that a thousand of them do not read as noise.
          ring = smoothstep(0.5, 0.44, distance) * smoothstep(0.34, 0.44, distance) * 0.35;
        }

        float alpha = clamp(vAlpha * falloff + ring * 0.9, 0.0, 1.0);
        vec3 rgb = mix(vColor, vec3(1.0), ring * 0.6);

        gl_FragColor = vec4(rgb, alpha);
      }
    `,
    transparent: true,
    depthWrite: true,
    depthTest: true,
  });
}
