import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  FogExp2,
  Group,
  Points,
  PointsMaterial,
  type Scene,
} from "three";

const BACKGROUND_COLOR = 0x05070d;
const FOG_COLOR = 0x05070d;
const FOG_DENSITY = 0.0035;

const DUST_COUNT = 1400;
const DUST_RADIUS = 420;
const DUST_COLOR = 0x2e4a72;

/**
 * Static depth cue behind the Thought Map: dark ground, exponential fog, and a
 * sparse dust field.
 *
 * Deliberately static. The scene renders on demand, so an animated background
 * would force a permanent render loop for decoration and cost more than it adds.
 */
export class BackgroundRenderer {
  readonly object = new Group();

  private readonly geometry: BufferGeometry;
  private readonly material: PointsMaterial;

  constructor(seed = 20260908) {
    this.object.name = "BackgroundRenderer";
    this.object.renderOrder = -1;

    this.geometry = createDustGeometry(DUST_COUNT, DUST_RADIUS, seed);
    this.material = new PointsMaterial({
      color: new Color(DUST_COLOR),
      size: 0.9,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.55,
      depthWrite: false,
      blending: AdditiveBlending,
    });

    const dust = new Points(this.geometry, this.material);
    dust.name = "BackgroundDust";
    // The dust is decoration; it must never affect Fit All or picking.
    dust.frustumCulled = false;
    dust.matrixAutoUpdate = false;
    dust.raycast = () => {};

    this.object.add(dust);
  }

  /** Apply the background colour and fog to the scene that hosts this object. */
  applyTo(scene: Scene): void {
    scene.background = new Color(BACKGROUND_COLOR);
    scene.fog = new FogExp2(FOG_COLOR, FOG_DENSITY);
    scene.add(this.object);
  }

  dispose(): void {
    this.geometry.dispose();
    this.material.dispose();
    this.object.removeFromParent();
  }
}

/**
 * Deterministic dust placement.
 *
 * A fixed seed keeps the background identical across reloads, which matters for
 * visual regression checks and for screenshots in bug reports.
 */
function createDustGeometry(count: number, radius: number, seed: number): BufferGeometry {
  const random = createSeededRandom(seed);
  const positions = new Float32Array(count * 3);

  for (let i = 0; i < count; i += 1) {
    // Rejection-free uniform point in a ball.
    const u = random();
    const distance = radius * Math.cbrt(u);
    const theta = random() * Math.PI * 2;
    const phi = Math.acos(2 * random() - 1);

    const sinPhi = Math.sin(phi);
    positions[i * 3] = distance * sinPhi * Math.cos(theta);
    positions[i * 3 + 1] = distance * sinPhi * Math.sin(theta);
    positions[i * 3 + 2] = distance * Math.cos(phi);
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(positions, 3));
  return geometry;
}

/** mulberry32 — small, fast, and reproducible across engines. */
function createSeededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
