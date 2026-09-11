import { describe, expect, it } from "vitest";

import type { MapNode } from "../src/api/mapTypes";
import { FALLBACK_SOURCE_STYLE, sourceStyle, summariseSources } from "../src/config/sourceStyles";
import { buildNodeIndex, docIdAt, indexOfDocId } from "../src/scene/nodeIndex";
import {
  applyTransform,
  computeBounds,
  computeTransform,
  isVolumetric,
  TARGET_WORLD_EXTENT,
} from "../src/scene/projectionBounds";
import { computeFitDistance } from "../src/scene/cameraFraming";

function node(docId: string, x: number, y: number, z: number, source = "gutendex"): MapNode {
  return { doc_id: docId, title: docId, author: "", source, x, y, z, cluster: 0 };
}

describe("computeBounds", () => {
  it("returns an empty box for no points", () => {
    const bounds = computeBounds([]);
    expect(bounds.count).toBe(0);
    expect(bounds.maxExtent).toBe(0);
    expect(bounds.radius).toBe(0);
  });

  it("computes min, max, centre and size", () => {
    const bounds = computeBounds([
      { x: -1, y: -2, z: -3 },
      { x: 3, y: 2, z: 1 },
    ]);

    expect(bounds.min).toEqual({ x: -1, y: -2, z: -3 });
    expect(bounds.max).toEqual({ x: 3, y: 2, z: 1 });
    expect(bounds.center).toEqual({ x: 1, y: 0, z: -1 });
    expect(bounds.size).toEqual({ x: 4, y: 4, z: 4 });
    expect(bounds.maxExtent).toBe(4);
  });

  it("uses the widest axis for maxExtent", () => {
    const bounds = computeBounds([
      { x: 0, y: 0, z: 0 },
      { x: 2, y: 10, z: 5 },
    ]);
    expect(bounds.maxExtent).toBe(10);
  });

  it("computes a radius that contains every point", () => {
    const points = [
      { x: -5, y: 0, z: 0 },
      { x: 5, y: 0, z: 0 },
      { x: 0, y: 3, z: 0 },
    ];
    const bounds = computeBounds(points);
    for (const point of points) {
      const distance = Math.hypot(
        point.x - bounds.center.x,
        point.y - bounds.center.y,
        point.z - bounds.center.z,
      );
      expect(distance).toBeLessThanOrEqual(bounds.radius + 1e-9);
    }
  });

  it("skips non-finite points rather than producing NaN bounds", () => {
    const bounds = computeBounds([
      { x: 0, y: 0, z: 0 },
      { x: Number.NaN, y: 1, z: 1 },
      { x: 2, y: 2, z: 2 },
    ]);

    expect(bounds.count).toBe(2);
    expect(Number.isFinite(bounds.maxExtent)).toBe(true);
    expect(bounds.max).toEqual({ x: 2, y: 2, z: 2 });
  });
});

describe("computeTransform", () => {
  it("applies one uniform scale, never per-axis", () => {
    // A deliberately lopsided cloud: 20 x 4 x 2.
    const bounds = computeBounds([
      { x: 0, y: 0, z: 0 },
      { x: 20, y: 4, z: 2 },
    ]);
    const transform = computeTransform(bounds);

    const scaled = applyTransform({ x: 20, y: 4, z: 2 }, transform);
    const origin = applyTransform({ x: 0, y: 0, z: 0 }, transform);

    const width = scaled.x - origin.x;
    const height = scaled.y - origin.y;
    const depth = scaled.z - origin.z;

    // Proportions must survive: 20:4:2 stays 10:2:1.
    expect(height / width).toBeCloseTo(4 / 20, 10);
    expect(depth / width).toBeCloseTo(2 / 20, 10);
  });

  it("scales the widest axis to the target extent", () => {
    const bounds = computeBounds([
      { x: 0, y: 0, z: 0 },
      { x: 20, y: 4, z: 2 },
    ]);
    const transform = computeTransform(bounds);
    expect(bounds.maxExtent * transform.scale).toBeCloseTo(TARGET_WORLD_EXTENT, 9);
  });

  it("centres the cloud on the origin", () => {
    const bounds = computeBounds([
      { x: 10, y: 20, z: 30 },
      { x: 30, y: 40, z: 50 },
    ]);
    const transform = computeTransform(bounds);

    const centre = applyTransform(bounds.center, transform);
    expect(centre.x).toBeCloseTo(0, 9);
    expect(centre.y).toBeCloseTo(0, 9);
    expect(centre.z).toBeCloseTo(0, 9);
  });

  it("does not divide by zero for a single node", () => {
    const transform = computeTransform(computeBounds([{ x: 5, y: 5, z: 5 }]));
    expect(Number.isFinite(transform.scale)).toBe(true);
    expect(transform.scale).toBe(1);
  });

  it("handles an empty cloud", () => {
    const transform = computeTransform(computeBounds([]));
    expect(transform.scale).toBe(1);
    expect(transform.offset).toEqual({ x: -0, y: -0, z: -0 });
  });
});

describe("isVolumetric", () => {
  it("recognises a genuinely three-dimensional cloud", () => {
    // The real corpus: extents 19.23 x 19.56 x 25.10.
    const bounds = computeBounds([
      { x: -4.2915, y: -2.6504, z: -9.9655 },
      { x: 14.9359, y: 16.9066, z: 15.1324 },
    ]);
    expect(isVolumetric(bounds)).toBe(true);
  });

  it("recognises a flat cloud", () => {
    const bounds = computeBounds([
      { x: 0, y: 0, z: 0 },
      { x: 100, y: 100, z: 0.001 },
    ]);
    expect(isVolumetric(bounds)).toBe(false);
  });
});

describe("camera fit against real projection bounds", () => {
  it("frames the whole map at a finite, positive distance", () => {
    const bounds = computeBounds([
      { x: -4.2915, y: -2.6504, z: -9.9655 },
      { x: 14.9359, y: 16.9066, z: 15.1324 },
    ]);
    const transform = computeTransform(bounds);

    const distance = computeFitDistance({
      size: {
        x: bounds.size.x * transform.scale,
        y: bounds.size.y * transform.scale,
        z: bounds.size.z * transform.scale,
      },
      fovDegrees: 50,
      aspect: 16 / 9,
      padding: 1.2,
    });

    expect(Number.isFinite(distance)).toBe(true);
    expect(distance).toBeGreaterThan(0);
    // Comfortably outside the cloud, not lost in the distance either.
    expect(distance).toBeGreaterThan(TARGET_WORLD_EXTENT / 2);
    expect(distance).toBeLessThan(TARGET_WORLD_EXTENT * 5);
  });

  it("pulls back further on a narrow viewport", () => {
    const size = { x: 100, y: 78, z: 96 };
    const wide = computeFitDistance({ size, fovDegrees: 50, aspect: 16 / 9 });
    const narrow = computeFitDistance({ size, fovDegrees: 50, aspect: 0.46 });
    expect(narrow).toBeGreaterThan(wide);
  });
});

describe("node index", () => {
  const nodes = [node("a", 0, 0, 0), node("b", 1, 1, 1), node("c", 2, 2, 2)];

  it("maps buffer index to doc_id and back", () => {
    const index = buildNodeIndex(nodes);

    expect(index.nodeIndexToDocId).toEqual(["a", "b", "c"]);
    expect(docIdAt(index, 1)).toBe("b");
    expect(indexOfDocId(index, "c")).toBe(2);
  });

  it("round-trips every node", () => {
    const index = buildNodeIndex(nodes);
    for (let i = 0; i < nodes.length; i += 1) {
      const docId = docIdAt(index, i);
      expect(docId).not.toBeNull();
      expect(indexOfDocId(index, docId!)).toBe(i);
    }
  });

  it("returns null for an unknown index or doc_id", () => {
    const index = buildNodeIndex(nodes);
    expect(docIdAt(index, 99)).toBeNull();
    expect(indexOfDocId(index, "missing")).toBeNull();
  });

  it("handles an empty map", () => {
    const index = buildNodeIndex([]);
    expect(index.nodeIndexToDocId).toEqual([]);
    expect(indexOfDocId(index, "a")).toBeNull();
  });
});

describe("source styles", () => {
  it("gives every known corpus source its own colour", () => {
    const colors = ["gutendex", "user_suno", "user_note", "zip"].map((source) =>
      sourceStyle(source).color.join(","),
    );
    expect(new Set(colors).size).toBe(4);
  });

  it("falls back for an unknown source rather than throwing", () => {
    expect(() => sourceStyle("a_brand_new_source")).not.toThrow();
    expect(sourceStyle("a_brand_new_source")).toBe(FALLBACK_SOURCE_STYLE);
    expect(sourceStyle("")).toBe(FALLBACK_SOURCE_STYLE);
    expect(sourceStyle(undefined)).toBe(FALLBACK_SOURCE_STYLE);
  });

  it("is case and whitespace insensitive", () => {
    expect(sourceStyle("  GUTENDEX ")).toBe(sourceStyle("gutendex"));
  });

  it("summarises counts per source, most common first", () => {
    const summary = summariseSources([
      { source: "gutendex" },
      { source: "gutendex" },
      { source: "zip" },
      { source: "brand_new" },
    ]);

    expect(summary[0]).toMatchObject({ source: "gutendex", count: 2 });
    expect(summary.map((entry) => entry.source)).toContain("brand_new");
    expect(summary.reduce((total, entry) => total + entry.count, 0)).toBe(4);
  });
});
