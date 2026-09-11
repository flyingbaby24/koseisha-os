/**
 * Pure camera framing math.
 *
 * Kept free of three.js and the DOM so "Fit All" / "Fit Results" behaviour can
 * be unit tested without a WebGL context.
 */

export interface FitOptions {
  /** Bounding-box extent to frame, in world units. */
  size: { x: number; y: number; z: number };
  /** Vertical field of view in degrees (three.js PerspectiveCamera.fov). */
  fovDegrees: number;
  /** Viewport aspect ratio (width / height). */
  aspect: number;
  /** Extra breathing room. 1 = tight fit, 1.2 = 20% margin. */
  padding?: number;
}

const DEGREES_TO_RADIANS = Math.PI / 180;

/** Smallest distance that is still numerically safe to place a camera at. */
export const MIN_FIT_DISTANCE = 0.001;

/**
 * Distance from the bounding-box centre at which the whole box fits in view.
 *
 * Both the vertical and the horizontal field of view are considered, so a wide
 * flat cluster is framed correctly on a narrow viewport and vice versa. Half of
 * the box depth is added so the near face does not end up behind the camera.
 */
export function computeFitDistance(options: FitOptions): number {
  const padding = options.padding ?? 1.2;
  const fov = clampFov(options.fovDegrees);
  const aspect = options.aspect > 0 && Number.isFinite(options.aspect) ? options.aspect : 1;

  const halfWidth = safeExtent(options.size.x) / 2;
  const halfHeight = safeExtent(options.size.y) / 2;
  const halfDepth = safeExtent(options.size.z) / 2;

  const halfFovY = (fov * DEGREES_TO_RADIANS) / 2;
  const halfFovX = Math.atan(Math.tan(halfFovY) * aspect);

  const distanceForHeight = halfHeight / Math.tan(halfFovY);
  const distanceForWidth = halfWidth / Math.tan(halfFovX);

  const distance = (Math.max(distanceForHeight, distanceForWidth) + halfDepth) * padding;

  return Math.max(MIN_FIT_DISTANCE, distance);
}

/**
 * Distance at which to sit from a single focused node.
 *
 * Derived from the map's own extent rather than hard-coded for this corpus, so
 * a differently sized projection still frames sensibly. The default puts the
 * camera at 12% of the map's width from the node: close enough that the node
 * and its immediate neighbourhood dominate, far enough that the surrounding
 * structure stays legible and the move does not feel like a teleport.
 */
export function computeFocusDistance(mapExtent: number, fraction = 0.12): number {
  if (!Number.isFinite(mapExtent) || mapExtent <= 0) {
    return Math.max(MIN_FIT_DISTANCE, 10);
  }
  return Math.max(MIN_FIT_DISTANCE, mapExtent * fraction);
}

/** Near/far planes that comfortably contain a fit at `distance`. */
export function computeClippingPlanes(distance: number, radius: number): { near: number; far: number } {
  const safeDistance = Math.max(MIN_FIT_DISTANCE, distance);
  const safeRadius = Math.max(0, radius);
  return {
    near: Math.max(0.01, (safeDistance - safeRadius) / 100),
    far: (safeDistance + safeRadius) * 10,
  };
}

function clampFov(value: number): number {
  if (!Number.isFinite(value)) {
    return 50;
  }
  return Math.min(179, Math.max(1, value));
}

/**
 * A degenerate axis (all nodes on a plane, or a single node) would otherwise
 * produce a zero fit distance and put the camera inside the geometry.
 */
function safeExtent(value: number): number {
  if (!Number.isFinite(value) || value <= 0) {
    return 0;
  }
  return value;
}
