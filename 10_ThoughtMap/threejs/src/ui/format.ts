import type { ParameterScore } from "../api/types";
import { PARAMETER_AXIS_ORDER } from "../config/searchOptions";

/**
 * Presentation only.
 *
 * State always holds the canonical values: similarity as the API returned it,
 * and parameters as 0.0-1.0 shares summing to 1.0. Nothing here writes back.
 */

/** Similarity for display. The underlying value stays untouched in state. */
export function formatSimilarity(value: number): string {
  if (!Number.isFinite(value)) {
    return "--";
  }
  return value.toFixed(4);
}

/**
 * A 0.0-1.0 composition share shown as a percentage.
 *
 * 0.139 renders as "13.9%". The 0.139 is what remains in state.
 */
export function formatShare(value: number): string {
  if (!Number.isFinite(value)) {
    return "--";
  }
  return `${(value * 100).toFixed(1)}%`;
}

export function formatCount(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

/** Non-empty text, or a dash. */
export function orDash(value: string | undefined | null): string {
  const text = (value ?? "").trim();
  return text || "—";
}

/**
 * Put parameters in the canonical axis order.
 *
 * The API already returns them in this order, but ordering here explicitly
 * means the query profile and every result profile line up even if a document
 * carries a partial or differently ordered set. Unknown axes are kept, after
 * the known ones, so nothing is silently dropped.
 */
export function orderParameters(
  parameters: readonly ParameterScore[] | null | undefined,
): ParameterScore[] {
  if (!parameters || parameters.length === 0) {
    return [];
  }

  const byKey = new Map<string, ParameterScore>();
  for (const parameter of parameters) {
    if (parameter && typeof parameter.key === "string" && Number.isFinite(parameter.value)) {
      byKey.set(parameter.key, parameter);
    }
  }

  const ordered: ParameterScore[] = [];
  for (const key of PARAMETER_AXIS_ORDER) {
    const found = byKey.get(key);
    if (found) {
      ordered.push(found);
      byKey.delete(key);
    }
  }

  for (const remaining of byKey.values()) {
    ordered.push(remaining);
  }

  return ordered;
}

/** Largest value in a set, used to scale the T2 bars. */
export function maxParameterValue(parameters: readonly ParameterScore[]): number {
  let max = 0;
  for (const parameter of parameters) {
    if (Number.isFinite(parameter.value) && parameter.value > max) {
      max = parameter.value;
    }
  }
  return max;
}
