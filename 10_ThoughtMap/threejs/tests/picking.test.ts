import { describe, expect, it } from "vitest";

import {
  DRAG_THRESHOLD_PX,
  MOUSE_PICK_RADIUS_PX,
  TOUCH_PICK_RADIUS_PX,
  clampTooltipPosition,
  exceedsDragThreshold,
  ndcToScreen,
  pickNearestNode,
  pickRadiusForPointer,
} from "../src/scene/picking";

/** Build a screen buffer of [x, y, depth] triples. */
function screen(points: Array<[number, number, number]>): Float32Array {
  const buffer = new Float32Array(points.length * 3);
  points.forEach(([x, y, depth], index) => {
    buffer[index * 3] = x;
    buffer[index * 3 + 1] = y;
    buffer[index * 3 + 2] = depth;
  });
  return buffer;
}

describe("click vs drag", () => {
  it("treats a still pointer as a click", () => {
    expect(exceedsDragThreshold({ x: 100, y: 100 }, { x: 100, y: 100 })).toBe(false);
  });

  it("tolerates the small jitter of a real click", () => {
    expect(exceedsDragThreshold({ x: 100, y: 100 }, { x: 102, y: 101 })).toBe(false);
  });

  it("treats a deliberate move as a drag", () => {
    expect(exceedsDragThreshold({ x: 100, y: 100 }, { x: 140, y: 100 })).toBe(true);
  });

  it("measures diagonal travel, not just one axis", () => {
    // Just under the threshold on each axis, but over it diagonally.
    const almost = DRAG_THRESHOLD_PX - 1;
    expect(exceedsDragThreshold({ x: 0, y: 0 }, { x: almost, y: almost })).toBe(true);
  });

  it("honours a custom threshold", () => {
    expect(exceedsDragThreshold({ x: 0, y: 0 }, { x: 20, y: 0 }, 50)).toBe(false);
  });
});

describe("pick tolerance", () => {
  it("is larger for touch than for a mouse", () => {
    expect(pickRadiusForPointer("touch")).toBe(TOUCH_PICK_RADIUS_PX);
    expect(pickRadiusForPointer("mouse")).toBe(MOUSE_PICK_RADIUS_PX);
    expect(pickRadiusForPointer("touch")).toBeGreaterThan(pickRadiusForPointer("mouse"));
  });

  it("does not demand pixel-perfect tapping", () => {
    // A fingertip covers far more than a couple of pixels.
    expect(pickRadiusForPointer("touch")).toBeGreaterThanOrEqual(20);
  });

  it("falls back to mouse tolerance for an unknown pointer type", () => {
    expect(pickRadiusForPointer(undefined)).toBe(MOUSE_PICK_RADIUS_PX);
    expect(pickRadiusForPointer("gamepad")).toBe(MOUSE_PICK_RADIUS_PX);
  });
});

describe("pickNearestNode", () => {
  it("returns the nearest node within the radius", () => {
    const buffer = screen([
      [100, 100, 0],
      [200, 200, 0],
      [104, 103, 0],
    ]);
    expect(pickNearestNode(buffer, 3, 105, 104, 12).index).toBe(2);
  });

  it("returns nothing for empty space", () => {
    const buffer = screen([
      [10, 10, 0],
      [500, 500, 0],
    ]);
    expect(pickNearestNode(buffer, 2, 250, 250, 12).index).toBe(-1);
  });

  it("respects the radius boundary", () => {
    const buffer = screen([[100, 100, 0]]);
    expect(pickNearestNode(buffer, 1, 110, 100, 12).index).toBe(0);
    expect(pickNearestNode(buffer, 1, 120, 100, 12).index).toBe(-1);
  });

  it("finds a node with a touch radius that a mouse radius would miss", () => {
    const buffer = screen([[100, 100, 0]]);
    expect(pickNearestNode(buffer, 1, 118, 100, MOUSE_PICK_RADIUS_PX).index).toBe(-1);
    expect(pickNearestNode(buffer, 1, 118, 100, TOUCH_PICK_RADIUS_PX).index).toBe(0);
  });

  it("ignores nodes behind the camera", () => {
    // Depth outside [-1, 1] is off-screen and must not steal a click.
    const buffer = screen([
      [100, 100, 1.4],
      [300, 300, 0],
    ]);
    expect(pickNearestNode(buffer, 2, 100, 100, 12).index).toBe(-1);
  });

  it("prefers the nearer node when two sit under the cursor", () => {
    const buffer = screen([
      [100, 100, 0.9],
      [100, 100, 0.1],
    ]);
    expect(pickNearestNode(buffer, 2, 100, 100, 12).index).toBe(1);
  });

  it("reports the pixel distance to the hit", () => {
    const buffer = screen([[100, 100, 0]]);
    expect(pickNearestNode(buffer, 1, 103, 104, 12).distancePx).toBeCloseTo(5, 6);
  });

  it("handles an empty cloud", () => {
    expect(pickNearestNode(new Float32Array(0), 0, 10, 10, 12).index).toBe(-1);
  });

  it("scans a large cloud quickly", () => {
    const count = 50_000;
    const buffer = new Float32Array(count * 3);
    for (let i = 0; i < count; i += 1) {
      buffer[i * 3] = (i % 1000) * 1.4;
      buffer[i * 3 + 1] = Math.floor(i / 1000) * 9;
      buffer[i * 3 + 2] = 0;
    }

    const started = performance.now();
    for (let i = 0; i < 20; i += 1) {
      pickNearestNode(buffer, count, 700, 220, 12);
    }
    const perPick = (performance.now() - started) / 20;

    expect(perPick).toBeLessThan(10);
  });
});

describe("ndcToScreen", () => {
  it("maps the centre of NDC to the centre of the canvas", () => {
    expect(ndcToScreen(0, 0, 800, 600)).toEqual({ x: 400, y: 300 });
  });

  it("flips the y axis", () => {
    // NDC +1 is the top of the screen, which is y = 0 in CSS pixels.
    expect(ndcToScreen(-1, 1, 800, 600)).toEqual({ x: 0, y: 0 });
    expect(ndcToScreen(1, -1, 800, 600)).toEqual({ x: 800, y: 600 });
  });
});

describe("tooltip placement", () => {
  it("leaves a tooltip alone when it already fits", () => {
    expect(clampTooltipPosition(100, 100, 200, 60, 800, 600)).toEqual({ x: 100, y: 100 });
  });

  it("pulls a tooltip back inside the right and bottom edges", () => {
    const placed = clampTooltipPosition(780, 580, 200, 60, 800, 600);
    expect(placed.x).toBeLessThanOrEqual(800 - 200);
    expect(placed.y).toBeLessThanOrEqual(600 - 60);
  });

  it("keeps a tooltip inside the top and left edges", () => {
    const placed = clampTooltipPosition(-40, -40, 200, 60, 800, 600);
    expect(placed.x).toBeGreaterThanOrEqual(0);
    expect(placed.y).toBeGreaterThanOrEqual(0);
  });

  it("degrades sanely when the tooltip is wider than the canvas", () => {
    const placed = clampTooltipPosition(10, 10, 400, 60, 300, 200);
    expect(Number.isFinite(placed.x)).toBe(true);
    expect(Number.isFinite(placed.y)).toBe(true);
  });
});
