/**
 * Radar geometry and scale. Pure maths — no DOM, no SVG, fully unit testable.
 *
 * ## The scale problem
 *
 * A Thought Composition is a *composition*: ten axes summing to 1.0. So a
 * perfectly ordinary profile sits around 0.1 per axis, and a strong one reaches
 * maybe 0.15. Drawn against a fixed 0..1 domain, every real profile collapses
 * into a tiny blob near the centre and nothing is readable.
 *
 * The opposite mistake is worse: normalising each polygon to its own maximum
 * makes every profile fill the chart, so a query and a document always look
 * equally intense and the comparison means nothing.
 *
 * So: a **shared** domain, derived from both profiles together, snapped to a
 * round number and clamped. Query and document are always drawn on the same
 * scale, and the rings are labelled with the actual percentages.
 */

import { PARAMETER_AXIS_ORDER } from "../config/searchOptions";
import type { ParameterScore } from "../api/types";

export interface RadarPoint {
  x: number;
  y: number;
}

export interface RadarAxis {
  key: string;
  label: string;
  /** Unit-circle direction, for drawing spokes and placing labels. */
  direction: RadarPoint;
  /** Outer end of the spoke, at `radius`. */
  outer: RadarPoint;
  /** Where the axis label sits, pushed out past the spoke. */
  labelAnchor: RadarPoint;
  /** Text anchor that keeps labels from overrunning the chart edges. */
  textAnchor: "start" | "middle" | "end";
}

/**
 * Smallest domain the chart will use. A uniform ten-axis profile is 0.1, so
 * this keeps a flat profile at 50% radius rather than pinned to the rim.
 */
export const MIN_RADAR_DOMAIN = 0.2;

/** Largest domain. Beyond this a single dominant axis flattens everything else. */
export const MAX_RADAR_DOMAIN = 1.0;

/** Headroom above the largest plotted value, so the peak is not on the rim. */
const DOMAIN_HEADROOM = 1.25;

/**
 * Upper bound of the shared value domain for one or more profiles.
 *
 * Snapped up to a 0.05 step so the ring labels are round numbers and the chart
 * does not visibly rescale on every keystroke.
 */
export function computeSharedDomain(
  profiles: ReadonlyArray<readonly ParameterScore[] | null | undefined>,
): number {
  let peak = 0;

  for (const profile of profiles) {
    if (!profile) {
      continue;
    }
    for (const score of profile) {
      if (Number.isFinite(score.value) && score.value > peak) {
        peak = score.value;
      }
    }
  }

  if (peak <= 0) {
    return MIN_RADAR_DOMAIN;
  }

  const padded = peak * DOMAIN_HEADROOM;
  const snapped = Math.ceil(padded / 0.05) * 0.05;
  return Math.min(MAX_RADAR_DOMAIN, Math.max(MIN_RADAR_DOMAIN, snapped));
}

/**
 * Axis directions for the canonical ten axes.
 *
 * The first axis points straight up and the rest run clockwise, so the shape is
 * stable and comparable between any two profiles.
 */
export function computeAxes(
  radius: number,
  labelOffset = 18,
  keys: readonly string[] = PARAMETER_AXIS_ORDER,
  labelFor: (key: string) => string = (key) => key,
): RadarAxis[] {
  const count = keys.length;

  return keys.map((key, index) => {
    const angle = -Math.PI / 2 + (index / count) * Math.PI * 2;
    const direction = { x: Math.cos(angle), y: Math.sin(angle) };

    const labelRadius = radius + labelOffset;
    const anchorX = direction.x * labelRadius;

    // Labels left of centre are right-anchored and vice versa, so long words
    // grow away from the chart instead of across it.
    let textAnchor: RadarAxis["textAnchor"] = "middle";
    if (anchorX > 1) {
      textAnchor = "start";
    } else if (anchorX < -1) {
      textAnchor = "end";
    }

    return {
      key,
      label: labelFor(key),
      direction,
      outer: { x: direction.x * radius, y: direction.y * radius },
      labelAnchor: { x: anchorX, y: direction.y * labelRadius },
      textAnchor,
    };
  });
}

/**
 * Plot a profile onto the axes.
 *
 * A missing axis plots at the centre rather than being skipped, which keeps the
 * polygon closed and the shape honest about what is absent. Values above the
 * domain are clamped to the rim instead of escaping the chart.
 */
export function computePolygon(
  profile: readonly ParameterScore[] | null | undefined,
  axes: readonly RadarAxis[],
  domain: number,
  radius: number,
): RadarPoint[] {
  const safeDomain = domain > 0 ? domain : MIN_RADAR_DOMAIN;
  const byKey = new Map<string, number>();

  for (const score of profile ?? []) {
    if (score && typeof score.key === "string" && Number.isFinite(score.value)) {
      byKey.set(score.key, score.value);
    }
  }

  return axes.map((axis) => {
    const value = byKey.get(axis.key) ?? 0;
    const ratio = Math.max(0, Math.min(1, value / safeDomain));
    // A negative direction times zero is -0, which compares unequal to 0 and
    // would read as "-0" anywhere the number is inspected. Normalise it.
    return {
      x: noNegativeZero(axis.direction.x * ratio * radius),
      y: noNegativeZero(axis.direction.y * ratio * radius),
    };
  });
}

/** `x,y x,y ...` for an SVG polygon. */
export function toPolygonPoints(points: readonly RadarPoint[]): string {
  return points.map((point) => `${round(point.x)},${round(point.y)}`).join(" ");
}

/** Ring values for the concentric guides, ascending. */
export function computeRings(domain: number, count = 4): number[] {
  const safeDomain = domain > 0 ? domain : MIN_RADAR_DOMAIN;
  const rings: number[] = [];
  for (let step = 1; step <= count; step += 1) {
    rings.push((safeDomain * step) / count);
  }
  return rings;
}

/** True when a profile carries no positive affinity on any axis. */
export function isEmptyProfile(profile: readonly ParameterScore[] | null | undefined): boolean {
  if (!profile || profile.length === 0) {
    return true;
  }
  return profile.every((score) => !Number.isFinite(score.value) || score.value <= 0);
}

function round(value: number): number {
  return noNegativeZero(Math.round(value * 100) / 100);
}

function noNegativeZero(value: number): number {
  return value === 0 ? 0 : value;
}
