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

/**
 * Space taken by opaque UI on each edge of the canvas, in CSS pixels.
 *
 * The canvas fills the window, but panels cover parts of it. What the reader
 * actually sees of the map is the rectangle left over — the *map window*.
 */
export interface ViewInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export const NO_INSETS: ViewInsets = Object.freeze({ top: 0, right: 0, bottom: 0, left: 0 });

/**
 * How to render so the camera's optical centre sits in the middle of the map
 * window rather than the middle of the canvas.
 *
 * Uses `PerspectiveCamera.setViewOffset`: the canvas becomes a sub-rectangle
 * of a larger virtual image whose centre is the map window's centre. The
 * field of view is widened by exactly the factor the virtual image is taller,
 * so a world unit covers the same number of pixels as before — point sizes,
 * picking radii and the feel of zoom are unchanged. Only *where* the centre
 * is moves. Nothing is drawn twice and there is no extra pass.
 */
export interface ViewWindow {
  /** False when the insets are zero or unusable; render without an offset. */
  active: boolean;
  fullWidth: number;
  fullHeight: number;
  offsetX: number;
  offsetY: number;
  /** Camera fov (degrees) for the full virtual image. */
  fov: number;
  /** Camera aspect for the full virtual image. */
  aspect: number;
  /** Vertical fov (degrees) of the visible map window, for framing. */
  visibleFov: number;
  /** Aspect of the visible map window, for framing. */
  visibleAspect: number;
}

/** A map window narrower or shorter than this is ignored on that axis. */
export const MIN_VIEW_WINDOW_PX = 80;

export function computeViewWindow(
  width: number,
  height: number,
  insets: ViewInsets,
  baseFovDegrees: number,
): ViewWindow {
  const w = Math.max(1, Number.isFinite(width) ? width : 1);
  const h = Math.max(1, Number.isFinite(height) ? height : 1);
  const fov = clampFov(baseFovDegrees);
  const inset = (value: number) => (Number.isFinite(value) && value > 0 ? value : 0);

  let left = inset(insets.left);
  let right = inset(insets.right);
  let top = inset(insets.top);
  let bottom = inset(insets.bottom);

  // A window too small to frame anything in means the panels have taken the
  // screen; framing for the whole canvas is then the better guess.
  if (w - left - right < MIN_VIEW_WINDOW_PX) {
    left = 0;
    right = 0;
  }
  if (h - top - bottom < MIN_VIEW_WINDOW_PX) {
    top = 0;
    bottom = 0;
  }

  const visibleWidth = w - left - right;
  const visibleHeight = h - top - bottom;
  const centreX = left + visibleWidth / 2;
  const centreY = top + visibleHeight / 2;

  const fullWidth = w + 2 * Math.abs(centreX - w / 2);
  const fullHeight = h + 2 * Math.abs(centreY - h / 2);

  const tanHalf = Math.tan((fov * DEGREES_TO_RADIANS) / 2);
  const toDegrees = (tangent: number) => (2 * Math.atan(tangent)) / DEGREES_TO_RADIANS;

  return {
    active: left + right + top + bottom > 0,
    fullWidth,
    fullHeight,
    offsetX: fullWidth / 2 - centreX,
    offsetY: fullHeight / 2 - centreY,
    fov: toDegrees((tanHalf * fullHeight) / h),
    aspect: fullWidth / fullHeight,
    visibleFov: toDegrees((tanHalf * visibleHeight) / h),
    visibleAspect: visibleWidth / visibleHeight,
  };
}

/** Ease for programmatic camera moves: gentle start, gentle arrival. */
export function easeInOutCubic(t: number): number {
  const x = Math.min(1, Math.max(0, t));
  return x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2;
}
