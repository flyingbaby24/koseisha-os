import { describe, expect, it } from "vitest";

import {
  MIN_FIT_DISTANCE,
  computeClippingPlanes,
  computeFitDistance,
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
