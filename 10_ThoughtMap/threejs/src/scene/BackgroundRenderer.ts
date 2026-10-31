import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  DataTexture,
  FogExp2,
  LinearFilter,
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
/** Edge length of the generated round-sprite mask. Tiny; built once. */
const DUST_SPRITE_SIZE = 32;

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
  private readonly sprite: DataTexture;

  constructor(seed = 20260908) {
    this.object.name = "BackgroundRenderer";
    this.object.renderOrder = -1;

    this.geometry = createDustGeometry(DUST_COUNT, DUST_RADIUS, seed);
    // Without a mask a point sprite is a square, and a dust mote that drifts
    // close to the camera became a visible grey tile. A soft round mask keeps
    // every mote reading as distant light.
    this.sprite = createRoundSprite(DUST_SPRITE_SIZE);
    this.material = new PointsMaterial({
      color: new Color(DUST_COLOR),
      alphaMap: this.sprite,
      size: 0.8,
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
    this.sprite.dispose();
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

/** A radial falloff mask, generated in memory — no image request, no canvas. */
function createRoundSprite(size: number): DataTexture {
  const data = new Uint8Array(size * size * 4);
  const centre = (size - 1) / 2;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const distance = Math.hypot(x - centre, y - centre) / (size / 2);
      const value = Math.round(255 * Math.max(0, 1 - distance) ** 1.6);
      const offset = (y * size + x) * 4;
      data[offset] = value;
      data[offset + 1] = value;
      data[offset + 2] = value;
      data[offset + 3] = 255;
    }
  }
  const texture = new DataTexture(data, size, size);
  texture.magFilter = LinearFilter;
  texture.minFilter = LinearFilter;
  texture.needsUpdate = true;
  return texture;
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
