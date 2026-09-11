/**
 * Screen-space point picking, and the click-vs-drag rule.
 *
 * Pure math, no three.js and no DOM, so every decision here is unit testable
 * without a WebGL context.
 *
 * ## Why screen space rather than Raycaster
 *
 * `THREE.Raycaster` picks Points with a **world-space** threshold. That single
 * number cannot mean the same thing at every zoom level: tuned for a wide view
 * it swallows half the cloud close up, and tuned for close up it becomes
 * unclickable when zoomed out. It also picks the point nearest along the ray,
 * not the point nearest to the cursor, so a far node can win a click that
 * visually belonged to a near one.
 *
 * Projecting the nodes and choosing the nearest within a **pixel** radius
 * fixes all three: tolerance is stated in the same units as the pointer, it is
 * constant across zoom, and touch simply gets a larger radius. At 4,915 nodes
 * a full pass is a fraction of a millisecond.
 */

/** Pointer travel, in CSS pixels, beyond which a gesture is a camera drag. */
export const DRAG_THRESHOLD_PX = 5;

/** Pick tolerance for a precise pointer. */
export const MOUSE_PICK_RADIUS_PX = 12;

/**
 * Pick tolerance for touch. Larger because a fingertip covers far more than
 * one pixel, and the map must not demand 2px accuracy.
 */
export const TOUCH_PICK_RADIUS_PX = 24;

export interface PointerOrigin {
  x: number;
  y: number;
}

/**
 * True when the pointer has travelled far enough to count as a camera drag
 * rather than a click.
 *
 * Squared comparison: no square root on a pointermove path.
 */
export function exceedsDragThreshold(
  origin: PointerOrigin,
  current: PointerOrigin,
  threshold = DRAG_THRESHOLD_PX,
): boolean {
  const dx = current.x - origin.x;
  const dy = current.y - origin.y;
  return dx * dx + dy * dy > threshold * threshold;
}

export function pickRadiusForPointer(pointerType: string | undefined): number {
  return pointerType === "touch" || pointerType === "pen"
    ? TOUCH_PICK_RADIUS_PX
    : MOUSE_PICK_RADIUS_PX;
}

export interface PickResult {
  /** Buffer index of the hit node, or -1 for empty space. */
  index: number;
  /** Pixel distance from the pointer to that node. */
  distancePx: number;
}

export const NO_PICK: PickResult = { index: -1, distancePx: Infinity };

/**
 * Nearest node to (px, py) within `radiusPx`.
 *
 * `screen` is a flat [x, y, depth] triple per node, in CSS pixels plus NDC
 * depth. A node with depth outside [-1, 1] is behind the camera or beyond the
 * far plane and is skipped — that is what stops off-screen geometry from
 * stealing a click.
 *
 * Ties break toward the nearer node, so a point in front wins over one behind
 * it at the same cursor distance.
 */
export function pickNearestNode(
  screen: Float32Array,
  count: number,
  px: number,
  py: number,
  radiusPx: number,
): PickResult {
  const radiusSquared = radiusPx * radiusPx;

  let bestIndex = -1;
  let bestDistanceSquared = radiusSquared;
  let bestDepth = Infinity;

  for (let index = 0; index < count; index += 1) {
    const offset = index * 3;
    const depth = screen[offset + 2]!;

    if (depth < -1 || depth > 1) {
      continue;
    }

    const dx = screen[offset]! - px;
    const dy = screen[offset + 1]! - py;
    const distanceSquared = dx * dx + dy * dy;

    if (distanceSquared > bestDistanceSquared) {
      continue;
    }

    // Equal-distance ties go to whichever node is closer to the camera.
    if (distanceSquared < bestDistanceSquared || depth < bestDepth) {
      bestIndex = index;
      bestDistanceSquared = distanceSquared;
      bestDepth = depth;
    }
  }

  if (bestIndex === -1) {
    return NO_PICK;
  }

  return { index: bestIndex, distancePx: Math.sqrt(bestDistanceSquared) };
}

/** Convert NDC (-1..1) to CSS pixel coordinates with the y axis flipped. */
export function ndcToScreen(
  ndcX: number,
  ndcY: number,
  width: number,
  height: number,
): { x: number; y: number } {
  return {
    x: (ndcX * 0.5 + 0.5) * width,
    y: (-ndcY * 0.5 + 0.5) * height,
  };
}

/** Keep a tooltip fully inside the canvas. */
export function clampTooltipPosition(
  x: number,
  y: number,
  tooltipWidth: number,
  tooltipHeight: number,
  containerWidth: number,
  containerHeight: number,
  margin = 12,
): { x: number; y: number } {
  const maxX = Math.max(margin, containerWidth - tooltipWidth - margin);
  const maxY = Math.max(margin, containerHeight - tooltipHeight - margin);
  return {
    x: Math.min(Math.max(margin, x), maxX),
    y: Math.min(Math.max(margin, y), maxY),
  };
}
