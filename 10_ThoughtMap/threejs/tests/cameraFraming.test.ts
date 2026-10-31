import { describe, expect, it } from "vitest";

import {
  MIN_FIT_DISTANCE,
  NO_INSETS,
  computeClippingPlanes,
  computeFitDistance,
  computeViewWindow,
  easeInOutCubic,
} from "../src/scene/cameraFraming";

const FOV = 50;

describe("computeFitDistance", () => {
  it("frames a cube far enough that its height fits the vertical fov", () => {
    const distance = computeFitDistance({
      size: { x: 10, y: 10, z: 10 },
      fovDegrees: FOV,
      aspect: 1,
      padding: 1,
    });

    // half-height / tan(fov/2) + half-depth
    const expected = 5 / Math.tan((FOV * Math.PI) / 180 / 2) + 5;
    expect(distance).toBeCloseTo(expected, 6);
  });

  it("pulls back further on a narrow viewport so width still fits", () => {
    const wideBox = { x: 100, y: 10, z: 0 };

    const onWideViewport = computeFitDistance({ size: wideBox, fovDegrees: FOV, aspect: 2 });
    const onNarrowViewport = computeFitDistance({ size: wideBox, fovDegrees: FOV, aspect: 0.5 });

    expect(onNarrowViewport).toBeGreaterThan(onWideViewport);
  });

  it("applies padding proportionally", () => {
    const size = { x: 10, y: 10, z: 10 };
    const tight = computeFitDistance({ size, fovDegrees: FOV, aspect: 1, padding: 1 });
    const padded = computeFitDistance({ size, fovDegrees: FOV, aspect: 1, padding: 1.5 });

    expect(padded).toBeCloseTo(tight * 1.5, 6);
  });

  it("never returns a degenerate distance for a single node", () => {
    const distance = computeFitDistance({
      size: { x: 0, y: 0, z: 0 },
      fovDegrees: FOV,
      aspect: 1,
    });

    expect(distance).toBeGreaterThanOrEqual(MIN_FIT_DISTANCE);
    expect(Number.isFinite(distance)).toBe(true);
  });

  it("survives a flat projection with zero depth", () => {
    const distance = computeFitDistance({
      size: { x: 20, y: 20, z: 0 },
      fovDegrees: FOV,
      aspect: 1,
      padding: 1,
    });

    expect(distance).toBeCloseTo(10 / Math.tan((FOV * Math.PI) / 180 / 2), 6);
  });

  it("falls back to a safe aspect when the viewport has not been measured yet", () => {
    const size = { x: 10, y: 10, z: 10 };

    for (const aspect of [0, -1, Number.NaN, Number.POSITIVE_INFINITY]) {
      const distance = computeFitDistance({ size, fovDegrees: FOV, aspect });
      expect(Number.isFinite(distance)).toBe(true);
      expect(distance).toBeGreaterThan(0);
    }
  });

  it("clamps an out-of-range fov instead of dividing by zero", () => {
    const size = { x: 10, y: 10, z: 10 };

    for (const fovDegrees of [0, -30, 400, Number.NaN]) {
      const distance = computeFitDistance({ size, fovDegrees, aspect: 1 });
      expect(Number.isFinite(distance)).toBe(true);
      expect(distance).toBeGreaterThan(0);
    }
  });
});

describe("computeClippingPlanes", () => {
  it("keeps the whole bounding sphere between near and far", () => {
    const distance = 100;
    const radius = 40;
    const { near, far } = computeClippingPlanes(distance, radius);

    expect(near).toBeGreaterThan(0);
    expect(near).toBeLessThan(distance - radius);
    expect(far).toBeGreaterThan(distance + radius);
  });

  it("keeps a positive near plane when the camera is inside the bounds", () => {
    const { near, far } = computeClippingPlanes(10, 500);

    expect(near).toBeGreaterThan(0);
    expect(far).toBeGreaterThan(near);
  });
});

describe("computeViewWindow", () => {
  /** Canvas x of the optical axis, given a view window. */
  function axisX(view: ReturnType<typeof computeViewWindow>): number {
    return view.fullWidth / 2 - view.offsetX;
  }
  function axisY(view: ReturnType<typeof computeViewWindow>): number {
    return view.fullHeight / 2 - view.offsetY;
  }
  /** Pixels per world unit at distance 1 — must not change with insets. */
  function pixelScale(view: ReturnType<typeof computeViewWindow>): number {
    return view.fullHeight / (2 * Math.tan(((view.fov * Math.PI) / 180) / 2));
  }

  it("is inactive and unchanged without insets", () => {
    const view = computeViewWindow(1440, 900, NO_INSETS, FOV);
    expect(view.active).toBe(false);
    expect(view.fov).toBeCloseTo(FOV, 9);
    expect(view.aspect).toBeCloseTo(1440 / 900, 9);
    expect(axisX(view)).toBeCloseTo(720, 9);
    expect(axisY(view)).toBeCloseTo(450, 9);
  });

  it("puts the optical centre in the middle of the uncovered window", () => {
    // Desktop: results on the left, document on the right, search on top.
    const insets = { top: 82, right: 384, bottom: 12, left: 352 };
    const view = computeViewWindow(1440, 900, insets, FOV);

    expect(view.active).toBe(true);
    expect(axisX(view)).toBeCloseTo(352 + (1440 - 352 - 384) / 2, 6);
    expect(axisY(view)).toBeCloseTo(82 + (900 - 82 - 12) / 2, 6);
    // The rendered canvas is a whole sub-rectangle of the virtual image.
    expect(view.offsetX).toBeGreaterThanOrEqual(0);
    expect(view.offsetY).toBeGreaterThanOrEqual(0);
    expect(view.offsetX + 1440).toBeLessThanOrEqual(view.fullWidth + 1e-9);
    expect(view.offsetY + 900).toBeLessThanOrEqual(view.fullHeight + 1e-9);
  });

  it("keeps the pixel scale, so point sizes and picking are unaffected", () => {
    const plain = computeViewWindow(1024, 768, NO_INSETS, FOV);
    const shifted = computeViewWindow(1024, 768, { top: 80, right: 0, bottom: 0, left: 400 }, FOV);
    expect(pixelScale(shifted)).toBeCloseTo(768 / (2 * Math.tan((FOV * Math.PI) / 360)), 6);
    expect(pixelScale(shifted)).toBeCloseTo(pixelScale(plain), 6);
    // Square pixels: horizontal scale matches vertical.
    expect(shifted.aspect).toBeCloseTo(shifted.fullWidth / shifted.fullHeight, 9);
  });

  it("frames for the visible window, not the whole canvas", () => {
    const view = computeViewWindow(1440, 900, { top: 0, right: 400, bottom: 0, left: 400 }, FOV);
    expect(view.visibleAspect).toBeCloseTo(640 / 900, 9);
    expect(view.visibleFov).toBeCloseTo(FOV, 6);

    const shorter = computeViewWindow(1440, 900, { top: 300, right: 0, bottom: 0, left: 0 }, FOV);
    expect(shorter.visibleFov).toBeLessThan(FOV);
  });

  it("ignores insets that leave no usable window", () => {
    const view = computeViewWindow(400, 800, { top: 0, right: 200, bottom: 0, left: 180 }, FOV);
    expect(axisX(view)).toBeCloseTo(200, 9);
    expect(view.visibleAspect).toBeCloseTo(400 / 800, 9);
  });

  it("survives nonsense input", () => {
    const view = computeViewWindow(Number.NaN, 0, { top: -5, right: Number.NaN, bottom: 0, left: 0 }, 0);
    expect(Number.isFinite(view.fov)).toBe(true);
    expect(Number.isFinite(view.aspect)).toBe(true);
  });
});

describe("easeInOutCubic", () => {
  it("starts at 0, ends at 1, is symmetric and clamps", () => {
    expect(easeInOutCubic(0)).toBe(0);
    expect(easeInOutCubic(1)).toBe(1);
    expect(easeInOutCubic(0.5)).toBeCloseTo(0.5, 9);
    expect(easeInOutCubic(0.25) + easeInOutCubic(0.75)).toBeCloseTo(1, 9);
    expect(easeInOutCubic(-1)).toBe(0);
    expect(easeInOutCubic(2)).toBe(1);
  });
});
