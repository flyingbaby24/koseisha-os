/**
 * Every search option value the UI can send, defined once.
 *
 * No option string literals belong in the UI modules; they read from here.
 */

import type { SearchMode } from "../api/types";

export interface SelectOption {
  /** Sent to the API. Empty string means "omit this parameter". */
  value: string;
  label: string;
}

export const MODE_OPTIONS: ReadonlyArray<{ value: SearchMode; label: string }> = [
  { value: "semantic", label: "Semantic" },
  { value: "keyword", label: "Keyword" },
  { value: "hybrid", label: "Hybrid" },
];

export const DEFAULT_MODE: SearchMode = "semantic";

/**
 * Source namespaces present in the official corpus.
 *
 * Confirmed against `ThoughtMapSearchService.filter_options()` on the live
 * index (4915 documents): gutendex 3330, user_suno 992, user_note 471,
 * zip 122. Unity's `SearchHeaderV2View` lists only `gutendex` and `user_suno`;
 * the other two are equally real and were simply never added there.
 */
export const SOURCE_OPTIONS: readonly SelectOption[] = [
  { value: "", label: "All sources" },
  { value: "gutendex", label: "Gutendex" },
  { value: "user_suno", label: "Suno" },
  { value: "user_note", label: "Note" },
  { value: "zip", label: "Zip import" },
];

export const DEFAULT_SOURCE = "";

/**
 * Parameter filter choices.
 *
 * `apply_parameter_filter` keeps documents whose *highest* scoring axis equals
 * the selected value, so valid values are axis names. `general` (like `all`
 * and empty) is intentionally a no-narrowing selection: it names the whole
 * ten-axis definition set, not one axis.
 *
 * Unity additionally offers `basic_thought`, `basic_literature`, and
 * `jinn_os`. Those are filter *definition file* names, not axis names —
 * verified against the live index, each returns 0 of 4915 rows. They are
 * deliberately not offered here. This matches the backend's own
 * `filter_options()`, which returns `["general", ...axis names]`.
 */
export const FILTER_OPTIONS: readonly SelectOption[] = [
  { value: "", label: "No filter" },
  { value: "general", label: "General (all axes)" },
  { value: "philosophy", label: "Philosophy" },
  { value: "psychology", label: "Psychology" },
  { value: "science", label: "Science" },
  { value: "economics", label: "Economics" },
  { value: "karma", label: "Karma" },
  { value: "emotion", label: "Emotion" },
  { value: "morality", label: "Morality" },
  { value: "ideal", label: "Ideal" },
  { value: "individual", label: "Individual" },
  { value: "community", label: "Community" },
];

export const DEFAULT_FILTER = "";

/** The API accepts 1..50 (`top: int = Query(10, ge=1, le=50)`). */
export const TOP_MIN = 1;
export const TOP_MAX = 50;
export const DEFAULT_TOP = 10;

export const TOP_OPTIONS: readonly number[] = [5, 10, 20, 30, 50];

/**
 * Canonical Thought Composition axis order, defined once and used by both the
 * query profile and the per-result profile so the two are readable together.
 *
 * This is `web/filters/general.json` key order, which is the order
 * `parameter_scores.csv` was generated in and the order the API returns.
 */
export const PARAMETER_AXIS_ORDER: readonly string[] = [
  "philosophy",
  "psychology",
  "science",
  "economics",
  "karma",
  "emotion",
  "morality",
  "ideal",
  "individual",
  "community",
];

/** Display labels for axes. Falls back to the raw key for anything unexpected. */
export const PARAMETER_AXIS_LABELS: Readonly<Record<string, string>> = {
  philosophy: "Philosophy",
  psychology: "Psychology",
  science: "Science",
  economics: "Economics",
  karma: "Karma",
  emotion: "Emotion",
  morality: "Morality",
  ideal: "Ideal",
  individual: "Individual",
  community: "Community",
};

export function axisLabel(key: string): string {
  return PARAMETER_AXIS_LABELS[key] ?? key;
}
