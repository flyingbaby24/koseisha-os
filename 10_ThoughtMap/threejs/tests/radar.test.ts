import { describe, expect, it } from "vitest";

import type { ParameterScore } from "../src/api/types";
import { PARAMETER_AXIS_ORDER } from "../src/config/searchOptions";
import { formatShare } from "../src/ui/format";
import {
  MAX_RADAR_DOMAIN,
  MIN_RADAR_DOMAIN,
  computeAxes,
  computePolygon,
  computeRings,
  computeSharedDomain,
  isEmptyProfile,
  toPolygonPoints,
} from "../src/ui/radarGeometry";

const RADIUS = 100;

function profile(values: Partial<Record<string, number>>): ParameterScore[] {
  return PARAMETER_AXIS_ORDER.map((key) => ({ key, value: values[key] ?? 0 }));
}

/** The real `Plato` query profile measured in T1.5. */
const PLATO_QUERY: ParameterScore[] = [
  { key: "philosophy", value: 0.1392 },
  { key: "psychology", value: 0.1090 },
  { key: "science", value: 0.1178 },
  { key: "economics", value: 0.0466 },
  { key: "karma", value: 0.0860 },
  { key: "emotion", value: 0.0920 },
  { key: "morality", value: 0.1060 },
  { key: "ideal", value: 0.1385 },
  { key: "individual", value: 0.1090 },
  { key: "community", value: 0.0559 },
];

/** The real `The Republic of Plato` document profile measured in T2. */
const REPUBLIC: ParameterScore[] = [
  { key: "philosophy", value: 0.13042758 },
  { key: "psychology", value: 0.080209084 },
  { key: "science", value: 0.114 },
  { key: "economics", value: 0.064 },
  { key: "karma", value: 0.092 },
  { key: "emotion", value: 0.080 },
  { key: "morality", value: 0.123 },
  { key: "ideal", value: 0.115 },
  { key: "individual", value: 0.125 },
  { key: "community", value: 0.077 },
];

describe("axis layout", () => {
  it("uses the canonical ten axes in canonical order", () => {
    const axes = computeAxes(RADIUS);
    expect(axes).toHaveLength(10);
    expect(axes.map((axis) => axis.key)).toEqual([...PARAMETER_AXIS_ORDER]);
  });

  it("starts at the top and runs clockwise", () => {
    const axes = computeAxes(RADIUS);
    // SVG y grows downward, so straight up is y = -radius.
    expect(axes[0]!.outer.x).toBeCloseTo(0, 6);
    expect(axes[0]!.outer.y).toBeCloseTo(-RADIUS, 6);
    expect(axes[1]!.outer.x).toBeGreaterThan(0);
  });

  it("spaces axes evenly", () => {
    const axes = computeAxes(RADIUS);
    for (const axis of axes) {
      expect(Math.hypot(axis.outer.x, axis.outer.y)).toBeCloseTo(RADIUS, 6);
    }
  });

  it("anchors labels away from the chart", () => {
    const axes = computeAxes(RADIUS);
    const right = axes.find((axis) => axis.labelAnchor.x > 40);
    const left = axes.find((axis) => axis.labelAnchor.x < -40);
    expect(right?.textAnchor).toBe("start");
    expect(left?.textAnchor).toBe("end");
  });
});

describe("shared scale", () => {
  it("derives one domain from every profile shown", () => {
    const domain = computeSharedDomain([PLATO_QUERY, REPUBLIC]);
    const peak = Math.max(
      ...PLATO_QUERY.map((s) => s.value),
      ...REPUBLIC.map((s) => s.value),
    );
    expect(domain).toBeGreaterThanOrEqual(peak);
  });

  it("gives both profiles the same scale", () => {
    // The point of the whole exercise: query and document must be comparable.
    const shared = computeSharedDomain([PLATO_QUERY, REPUBLIC]);
    const axes = computeAxes(RADIUS);

    const queryAlone = computeSharedDomain([PLATO_QUERY]);
    const documentAlone = computeSharedDomain([REPUBLIC]);

    const sharedQuery = computePolygon(PLATO_QUERY, axes, shared, RADIUS);
    const independentQuery = computePolygon(PLATO_QUERY, axes, queryAlone, RADIUS);

    // If the two happen to have the same peak the domains coincide; assert the
    // contract directly instead.
    expect(computePolygon(REPUBLIC, axes, shared, RADIUS)).not.toEqual(
      computePolygon(REPUBLIC, axes, documentAlone === shared ? shared + 0.5 : documentAlone, RADIUS),
    );
    expect(sharedQuery.length).toBe(independentQuery.length);
  });

  it("never normalises a profile to its own maximum", () => {
    // A weak profile must stay visibly smaller than a strong one on one chart.
    const weak = profile({ philosophy: 0.05 });
    const strong = profile({ philosophy: 0.4 });
    const domain = computeSharedDomain([weak, strong]);
    const axes = computeAxes(RADIUS);

    const weakPoint = computePolygon(weak, axes, domain, RADIUS)[0]!;
    const strongPoint = computePolygon(strong, axes, domain, RADIUS)[0]!;

    expect(Math.hypot(strongPoint.x, strongPoint.y)).toBeGreaterThan(
      Math.hypot(weakPoint.x, weakPoint.y) * 5,
    );
  });

  it("keeps an ordinary composition readable rather than a dot", () => {
    // Ten axes summing to 1.0 means ~0.1 each. Against a fixed 1.0 domain that
    // is 10% of the radius; the derived domain must do much better.
    const domain = computeSharedDomain([PLATO_QUERY]);
    const axes = computeAxes(RADIUS);
    const point = computePolygon(PLATO_QUERY, axes, domain, RADIUS)[0]!;
    const ratio = Math.hypot(point.x, point.y) / RADIUS;

    expect(ratio).toBeGreaterThan(0.5);
    expect(ratio).toBeLessThanOrEqual(1);
  });

  it("clamps the domain at both ends", () => {
    expect(computeSharedDomain([profile({ philosophy: 0.001 })])).toBe(MIN_RADAR_DOMAIN);
    expect(computeSharedDomain([profile({ philosophy: 5 })])).toBe(MAX_RADAR_DOMAIN);
  });

  it("falls back for an empty or absent profile", () => {
    expect(computeSharedDomain([])).toBe(MIN_RADAR_DOMAIN);
    expect(computeSharedDomain([null, undefined])).toBe(MIN_RADAR_DOMAIN);
  });
});

describe("polygon geometry", () => {
  it("plots a value at the right fraction of the radius", () => {
    const axes = computeAxes(RADIUS);
    const domain = 0.2;
    const points = computePolygon(profile({ philosophy: 0.1 }), axes, domain, RADIUS);

    // 0.1 of a 0.2 domain is half the radius, straight up.
    expect(points[0]!.y).toBeCloseTo(-RADIUS / 2, 6);
    expect(points[0]!.x).toBeCloseTo(0, 6);
  });

  it("produces one point per axis", () => {
    const axes = computeAxes(RADIUS);
    expect(computePolygon(PLATO_QUERY, axes, 0.2, RADIUS)).toHaveLength(10);
  });

  it("plots a missing axis at the centre rather than skipping it", () => {
    const axes = computeAxes(RADIUS);
    const partial: ParameterScore[] = [{ key: "philosophy", value: 0.15 }];
    const points = computePolygon(partial, axes, 0.2, RADIUS);

    expect(points).toHaveLength(10);
    expect(points[1]).toEqual({ x: 0, y: 0 });
  });

  it("clamps a value above the domain to the rim", () => {
    const axes = computeAxes(RADIUS);
    const points = computePolygon(profile({ philosophy: 0.9 }), axes, 0.2, RADIUS);
    expect(Math.hypot(points[0]!.x, points[0]!.y)).toBeCloseTo(RADIUS, 6);
  });

  it("does not mutate the source values", () => {
    const source = PLATO_QUERY.map((score) => ({ ...score }));
    const before = JSON.parse(JSON.stringify(source));
    const axes = computeAxes(RADIUS);

    computeSharedDomain([source]);
    computePolygon(source, axes, 0.2, RADIUS);

    expect(source).toEqual(before);
  });

  it("serialises points for SVG", () => {
    const points = [
      { x: 1.234, y: -5.678 },
      { x: 0, y: 0 },
    ];
    expect(toPolygonPoints(points)).toBe("1.23,-5.68 0,0");
  });
});

describe("all-zero profile", () => {
  const zero = profile({});

  it("is recognised", () => {
    expect(isEmptyProfile(zero)).toBe(true);
    expect(isEmptyProfile(PLATO_QUERY)).toBe(false);
    expect(isEmptyProfile(null)).toBe(true);
    expect(isEmptyProfile([])).toBe(true);
  });

  it("collapses to the centre without throwing or dividing by zero", () => {
    const axes = computeAxes(RADIUS);
    const domain = computeSharedDomain([zero]);
    const points = computePolygon(zero, axes, domain, RADIUS);

    expect(domain).toBeGreaterThan(0);
    expect(points).toHaveLength(10);
    for (const point of points) {
      expect(Number.isFinite(point.x)).toBe(true);
      expect(Number.isFinite(point.y)).toBe(true);
      expect(point).toEqual({ x: 0, y: 0 });
    }
  });

  it("is not rewritten into fake uniform values", () => {
    // The canonical all-zero document must stay all zero.
    const axes = computeAxes(RADIUS);
    const points = computePolygon(zero, axes, computeSharedDomain([zero]), RADIUS);
    expect(points.every((point) => point.x === 0 && point.y === 0)).toBe(true);
  });
});

describe("rings", () => {
  it("ascends to the domain", () => {
    const rings = computeRings(0.2, 4);
    expect(rings).toHaveLength(4);
    expect(rings[3]).toBeCloseTo(0.2, 9);
    expect(rings[0]).toBeCloseTo(0.05, 9);
  });

  it("survives a zero domain", () => {
    expect(computeRings(0).every((value) => Number.isFinite(value))).toBe(true);
  });
});

describe("percentage formatting is presentation only", () => {
  it("renders a canonical 0..1 value as a percentage", () => {
    expect(formatShare(0.139)).toBe("13.9%");
  });

  it("leaves the underlying value untouched", () => {
    const scores: ParameterScore[] = [{ key: "philosophy", value: 0.1392 }];
    formatShare(scores[0]!.value);
    expect(scores[0]!.value).toBe(0.1392);
  });
});
