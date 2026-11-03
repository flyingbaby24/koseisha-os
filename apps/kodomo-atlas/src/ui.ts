/**
 * Presentation-only helpers. Nothing here alters values, breaks or definitions in
 * metrics.ts / statistics.json; it only decides how they are grouped and worded.
 */
import type { Bounds, Metric, Region } from "./types";
import { compact, metrics, valueOf } from "./metrics";

/** Shown prominently: what first-time visitors most often look for. */
export const primaryMetrics: Metric[] = ["tfr", "childShare", "children"];
export const ageMetrics: Metric[] = ["age0", "age5", "age10"];
/** The remaining indicators, kept one tap away. */
export const otherMetrics: { metric: Metric; label: string }[] = [
  { metric: "childDensity", label: "子どもの人口密度" },
  { metric: "age0", label: "年齢別の人口分布" },
  { metric: "change", label: "人口増減率" },
];
/** Counts are compared with the 1,896-unit simple mean, never with national totals. */
export const countMetrics: Metric[] = ["children", "age0", "age5", "age10"];
export const isCount = (metric: Metric) => countMetrics.includes(metric);
export const isAge = (metric: Metric) => ageMetrics.includes(metric);

/** Plain-language glosses, consistent with metadata.definitions. */
export const guide: Record<
  Metric,
  { title: string; plain: string; low: string; high: string }
> = {
  tfr: {
    title: "出生率",
    plain: "合計特殊出生率",
    low: "低い",
    high: "高い",
  },
  childShare: {
    title: "年少人口比率",
    plain: "人口に占める子どもの割合",
    low: "低い",
    high: "高い",
  },
  children: {
    title: "子ども人口",
    plain: "0〜14歳の人数",
    low: "少ない",
    high: "多い",
  },
  childDensity: {
    title: "子どもの人口密度",
    plain: "全面積1km²あたりの0〜14歳人口",
    low: "低い",
    high: "高い",
  },
  age0: { title: "0〜4歳人口", plain: "0〜4歳の人数", low: "少ない", high: "多い" },
  age5: { title: "5〜9歳人口", plain: "5〜9歳の人数", low: "少ない", high: "多い" },
  age10: {
    title: "10〜14歳人口",
    plain: "10〜14歳の人数",
    low: "少ない",
    high: "多い",
  },
  change: {
    title: "人口増減率",
    plain: "2015→2020年の総人口の増減",
    low: "減少",
    high: "増加",
  },
};

export interface ComparePreset {
  id: string;
  left: Metric;
  right: Metric;
  title: string;
  hint: string;
}
export const comparePresets: ComparePreset[] = [
  {
    id: "tfr-share",
    left: "tfr",
    right: "childShare",
    title: "出生率 × 年少人口比率",
    hint: "出生の多さと子どもの割合",
  },
  {
    id: "children-density",
    left: "children",
    right: "childDensity",
    title: "子ども人口 × 子どもの密度",
    hint: "人数と面積あたりの多さ",
  },
];

/** Short labels for the legend's class boundaries. */
export function breakLabel(value: number, metric: Metric): string {
  if (metric === "tfr") return value.toFixed(2);
  if (metric === "change")
    return `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value)}`;
  // Short labels so six boundaries fit under a narrow legend: 2千, 1.5万 …
  if (value >= 1000 && value < 10000) return `${value / 1000}千`;
  return compact(value);
}

/** Position (0–1) of a value along the seven fixed classes; open-ended ends clamp. */
export function rampPosition(value: number | null, metric: Metric): number | null {
  if (value === null || !Number.isFinite(value)) return null;
  const { breaks } = metrics[metric];
  const bins = breaks.length + 1;
  const index = breaks.findIndex((limit) => value < limit);
  if (index === 0) return 0.5 / bins;
  if (index < 0) return (bins - 0.5) / bins;
  const low = breaks[index - 1],
    high = breaks[index];
  return (index + (value - low) / (high - low)) / bins;
}

export function binIndex(value: number | null, metric: Metric): number | null {
  if (value === null || !Number.isFinite(value)) return null;
  const index = metrics[metric].breaks.findIndex((limit) => value < limit);
  return index < 0 ? metrics[metric].breaks.length : index;
}

export interface Rank {
  rank: number;
  total: number;
  ties: number;
}
/**
 * Standard competition rank (1 + regions with a strictly higher value) among the
 * given statistical units. Missing values are excluded, as in the ranking table.
 */
export function rankOf(
  region: Region,
  regions: Region[],
  metric: Metric,
): Rank | null {
  const value = valueOf(region, metric);
  if (value === null) return null;
  let higher = 0,
    ties = 0,
    total = 0;
  for (const other of regions) {
    const v = valueOf(other, metric);
    if (v === null) continue;
    total++;
    if (v > value) higher++;
    else if (v === value) ties++;
  }
  return { rank: higher + 1, total, ties };
}

/** Descending order, ties broken by code, missing values removed. */
export function sortByMetric(
  regions: Region[],
  metric: Metric,
  descending = true,
): Region[] {
  return regions
    .filter((r) => valueOf(r, metric) !== null)
    .sort(
      (a, b) =>
        (valueOf(b, metric)! - valueOf(a, metric)!) * (descending ? 1 : -1) ||
        a.code.localeCompare(b.code),
    );
}

export function unionBounds(regions: Region[], fallback: Bounds): Bounds {
  const bounds = regions.flatMap((r) => (r.bounds ? [r.bounds] : []));
  if (!bounds.length) return fallback;
  return [
    [
      Math.min(...bounds.map((b) => b[0][0])),
      Math.min(...bounds.map((b) => b[0][1])),
    ],
    [
      Math.max(...bounds.map((b) => b[1][0])),
      Math.max(...bounds.map((b) => b[1][1])),
    ],
  ];
}

export function levelLabel(region: Region): string {
  if (region.level === "a") return "都道府県";
  if (region.level === "1")
    return region.code === "13100" ? "特別区部全体" : "市全体（行政区の合計）";
  if (region.level === "0")
    return region.prefCode === "13" ? "特別区" : "行政区";
  if (region.name.endsWith("町")) return "町";
  if (region.name.endsWith("村")) return "村";
  return "市";
}

export const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
