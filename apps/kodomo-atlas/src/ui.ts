/**
 * Presentation-only helpers. Nothing here alters values, breaks or definitions in
 * metrics.ts / statistics.json; it only decides how they are grouped and worded.
 */
import type { Bounds, Metric, Region } from "./types";
import { compact, metrics, valueOf } from "./metrics";

export type CategoryId = "children" | "households" | "aging";
export const categories: { id: CategoryId; label: string }[] = [
  { id: "children", label: "出生・子ども" },
  { id: "households", label: "世帯構造" },
  { id: "aging", label: "未婚・高齢化" },
];

/**
 * An indicator as the visitor sees it. Household indicators come as a share and a count
 * (`rate` / `count`), the never-married rate also by sex: [total, male, female].
 */
export interface Indicator {
  id: string;
  category: CategoryId;
  title: string;
  plain: string;
  icon: string;
  primary: boolean;
  metrics: Metric[];
  rate?: Metric[];
  count?: Metric[];
}
const family = (
  id: string,
  category: CategoryId,
  title: string,
  plain: string,
  icon: string,
  rate: Metric[],
  count: Metric[],
): Indicator => ({
  id,
  category,
  title,
  plain,
  icon,
  primary: true,
  rate,
  count,
  metrics: [...rate, ...count],
});
export const indicators: Indicator[] = [
  { id: "tfr", category: "children", title: "出生率", plain: "合計特殊出生率", icon: "baby", primary: true, metrics: ["tfr"] },
  { id: "childShare", category: "children", title: "年少人口比率", plain: "人口に占める子どもの割合", icon: "pie", primary: true, metrics: ["childShare"] },
  { id: "children", category: "children", title: "子ども人口", plain: "0〜14歳の人数", icon: "users", primary: true, metrics: ["children"] },
  { id: "childDensity", category: "children", title: "子どもの密度", plain: "子どもの人口密度", icon: "grid", primary: false, metrics: ["childDensity"] },
  { id: "age", category: "children", title: "年齢別の人口", plain: "年齢別の人口分布", icon: "chart", primary: false, metrics: ["age0", "age5", "age10"] },
  family("single", "households", "単独世帯", "1人で住む世帯", "user", ["singleShare"], ["single"]),
  family("coupleChildren", "households", "夫婦と子どもの世帯", "夫婦と子供から成る世帯", "home", ["coupleChildrenShare"], ["coupleChildren"]),
  family("under18", "households", "18歳未満のいる世帯", "18歳未満の世帯員がいる世帯", "backpack", ["under18Share"], ["under18"]),
  family("unmarried", "aging", "25〜39歳の未婚", "25〜39歳で未婚の人", "ring", ["unmarriedRate", "unmarriedRateMale", "unmarriedRateFemale"], ["unmarried", "unmarriedMale", "unmarriedFemale"]),
  family("elderlyOnly", "aging", "高齢者のみの世帯", "世帯員が全員65歳以上", "elder", ["elderlyOnlyShare"], ["elderlyOnly"]),
  family("elderlySingle", "aging", "65歳以上の単独世帯", "65歳以上の人が1人で住む", "elderAlone", ["elderlySingleShare"], ["elderlySingle"]),
  { id: "change", category: "aging", title: "人口増減率", plain: "2015→2020年の総人口", icon: "trend", primary: false, metrics: ["change"] },
];
export const indicatorOf = (metric: Metric): Indicator =>
  indicators.find((i) => i.metrics.includes(metric))!;
export const categoryOf = (metric: Metric): CategoryId =>
  indicatorOf(metric).category;
export type Mode = "rate" | "count";
export const SEX_LABELS = ["男女計", "男性", "女性"];
/** Which share/count and sex variant a metric is (household indicators only). */
export function variantOf(metric: Metric): { mode: Mode; sex: number } {
  const indicator = indicatorOf(metric);
  const count = indicator.count?.indexOf(metric) ?? -1;
  if (count >= 0) return { mode: "count", sex: count };
  return { mode: "rate", sex: Math.max(0, indicator.rate?.indexOf(metric) ?? 0) };
}
/** The metric of `indicator` closest to the requested variant. */
export function pickVariant(indicator: Indicator, mode: Mode, sex: number): Metric {
  const list = (mode === "count" ? indicator.count : indicator.rate) ?? indicator.metrics;
  return list[Math.min(sex, list.length - 1)];
}

export const ageMetrics: Metric[] = ["age0", "age5", "age10"];
/** Counts are compared with the 1,896-unit simple mean, never with national totals. */
export const countMetrics: Metric[] = [
  "children",
  "age0",
  "age5",
  "age10",
  "single",
  "coupleChildren",
  "under18",
  "elderlyOnly",
  "elderlySingle",
  "unmarried",
  "unmarriedMale",
  "unmarriedFemale",
];
export const isCount = (metric: Metric) => countMetrics.includes(metric);
export const isAge = (metric: Metric) => ageMetrics.includes(metric);

const share = (title: string, plain: string) => ({ title, plain, low: "低い", high: "高い" });
const many = (title: string, plain: string) => ({ title, plain, low: "少ない", high: "多い" });
/** Plain-language glosses, consistent with metadata.definitions. */
export const guide: Record<
  Metric,
  { title: string; plain: string; low: string; high: string }
> = {
  tfr: share("出生率", "合計特殊出生率"),
  childShare: share("年少人口比率", "人口に占める子どもの割合"),
  children: many("子ども人口", "0〜14歳の人数"),
  childDensity: share("子どもの人口密度", "全面積1km²あたりの0〜14歳人口"),
  age0: many("0〜4歳人口", "0〜4歳の人数"),
  age5: many("5〜9歳人口", "5〜9歳の人数"),
  age10: many("10〜14歳人口", "10〜14歳の人数"),
  change: { title: "人口増減率", plain: "2015→2020年の総人口の増減", low: "減少", high: "増加" },
  singleShare: share("単独世帯率", "一般世帯に占める単独世帯"),
  single: many("単独世帯数", "1人で住む世帯の数"),
  coupleChildrenShare: share("夫婦と子ども世帯率", "一般世帯に占める夫婦と子供の世帯"),
  coupleChildren: many("夫婦と子ども世帯数", "夫婦と子供から成る世帯の数"),
  under18Share: share("18歳未満のいる世帯率", "一般世帯に占める18歳未満のいる世帯"),
  under18: many("18歳未満のいる世帯数", "18歳未満の世帯員がいる世帯の数"),
  unmarriedRate: share("25〜39歳未婚率", "25〜39歳に占める未婚者"),
  unmarriedRateMale: share("未婚率（男性）", "25〜39歳男性に占める未婚者"),
  unmarriedRateFemale: share("未婚率（女性）", "25〜39歳女性に占める未婚者"),
  unmarried: many("25〜39歳未婚者数", "25〜39歳の未婚者の数"),
  unmarriedMale: many("未婚者数（男性）", "25〜39歳の未婚男性の数"),
  unmarriedFemale: many("未婚者数（女性）", "25〜39歳の未婚女性の数"),
  elderlyOnlyShare: share("高齢者のみの世帯率", "世帯員が全員65歳以上の世帯"),
  elderlyOnly: many("高齢者のみの世帯数", "世帯員が全員65歳以上の世帯の数"),
  elderlySingleShare: share("65歳以上の単独世帯率", "65歳以上の人が1人で住む世帯"),
  elderlySingle: many("65歳以上の単独世帯数", "65歳以上の人が1人で住む世帯の数"),
};

export interface ComparePreset {
  id: string;
  left: Metric;
  right: Metric;
  title: string;
  hint: string;
}
/** Side-by-side views only: no preset claims a relationship between the two maps. */
export const comparePresets: ComparePreset[] = [
  { id: "tfr-share", left: "tfr", right: "childShare", title: "出生率 × 年少人口比率", hint: "出生の水準と子どもの割合" },
  { id: "children-density", left: "children", right: "childDensity", title: "子ども人口 × 子どもの密度", hint: "人数と面積あたりの多さ" },
  { id: "tfr-unmarried", left: "tfr", right: "unmarriedRate", title: "出生率 × 25〜39歳未婚率", hint: "出生の水準と未婚の割合" },
  { id: "share-elderly", left: "childShare", right: "elderlyOnlyShare", title: "年少人口比率 × 高齢者のみの世帯率", hint: "子どもの割合と高齢者だけの世帯" },
  { id: "tfr-single", left: "tfr", right: "singleShare", title: "出生率 × 単独世帯率", hint: "出生の水準と1人で住む世帯" },
  { id: "under18-single", left: "under18Share", right: "singleShare", title: "18歳未満のいる世帯率 × 単独世帯率", hint: "子どものいる世帯と1人の世帯" },
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
