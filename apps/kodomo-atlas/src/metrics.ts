import type { HouseholdMetric, Metric, Region } from "./types";

export const greens = [
  "#e6edcb",
  "#c4d9a0",
  "#9bc474",
  "#70ac53",
  "#468d3c",
  "#266c31",
  "#104b28",
];
export const MISSING_COLOR = "#9295a0";
const blues = [
  "#e5edf0",
  "#c8dce2",
  "#a0c3cf",
  "#74a9bb",
  "#49879f",
  "#2b657f",
  "#17465d",
];
/** Household / marital-status layer: one muted purple ramp, distinct from green (TFR) and blue (children). */
const plums = [
  "#f2eef6",
  "#dcd2e9",
  "#c2b1d9",
  "#a48dc4",
  "#8468a9",
  "#62468a",
  "#412a63",
];
const growth = [
  "#bf826b",
  "#dab29c",
  "#ead8c1",
  "#edf0df",
  "#b8d4b7",
  "#7eb18e",
  "#387959",
];
export const householdMetrics: HouseholdMetric[] = [
  "singleShare",
  "single",
  "coupleChildrenShare",
  "coupleChildren",
  "under18Share",
  "under18",
  "unmarriedRate",
  "unmarriedRateMale",
  "unmarriedRateFemale",
  "unmarried",
  "unmarriedMale",
  "unmarriedFemale",
  "elderlyOnlyShare",
  "elderlyOnly",
  "elderlySingleShare",
  "elderlySingle",
];
const householdSet = new Set<string>(householdMetrics);
export const isHouseholdMetric = (metric: Metric): metric is HouseholdMetric =>
  householdSet.has(metric);
/** Percentages shown with one decimal and compared in points. */
const shareSet = new Set<string>([
  "childShare",
  "change",
  "singleShare",
  "coupleChildrenShare",
  "under18Share",
  "elderlyOnlyShare",
  "elderlySingleShare",
  "unmarriedRate",
  "unmarriedRateMale",
  "unmarriedRateFemale",
]);
export const isShareMetric = (metric: Metric) => shareSet.has(metric);
export const metricList: Metric[] = [
  "tfr",
  "children",
  "childShare",
  "childDensity",
  "age0",
  "age5",
  "age10",
  "change",
  ...householdMetrics,
];
export const metrics: Record<
  Metric,
  {
    label: string;
    short: string;
    english: string;
    unit: string;
    period: string;
    source: string;
    description: string;
    breaks: number[];
    colors: string[];
  }
> = {
  tfr: {
    label: "合計特殊出生率",
    short: "出生率",
    english: "TOTAL FERTILITY RATE",
    unit: "",
    period: "2018–2022年",
    source: "厚生労働省 人口動態保健所・市区町村別統計",
    description:
      "5年間の統計を用いたベイズ推定値。日本人女性を対象とした指標です。",
    breaks: [1, 1.2, 1.4, 1.6, 1.8, 2],
    colors: greens,
  },
  children: {
    label: "0〜14歳人口",
    short: "子ども人口",
    english: "CHILD POPULATION",
    unit: "人",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第2-7表",
    description: "0〜14歳の男女・国籍総数。年齢不詳の人口は含みません。",
    breaks: [500, 2000, 5000, 10000, 20000, 50000],
    colors: blues,
  },
  childShare: {
    label: "年少人口比率",
    short: "年少人口比率",
    english: "CHILD POPULATION SHARE",
    unit: "%",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第2-7表",
    description: "年齢が判明している人口に占める、0〜14歳人口の割合です。",
    breaks: [6, 9, 12, 15, 18, 21],
    colors: blues,
  },
  childDensity: {
    label: "子どもの人口密度",
    short: "子どもの密度",
    english: "CHILD POPULATION DENSITY",
    unit: "人/km²",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第1-1・2-7表",
    description:
      "0〜14歳人口を自治体の全面積で割った密度。可住地面積あたりではありません。",
    breaks: [5, 20, 50, 100, 300, 1000],
    colors: blues,
  },
  age0: {
    label: "0〜4歳人口",
    short: "0〜4歳",
    english: "AGES 0–4",
    unit: "人",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第2-7表",
    description: "0〜4歳の男女・国籍総数。年齢不詳は含みません。",
    breaks: [100, 500, 1500, 3000, 6000, 15000],
    colors: blues,
  },
  age5: {
    label: "5〜9歳人口",
    short: "5〜9歳",
    english: "AGES 5–9",
    unit: "人",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第2-7表",
    description: "5〜9歳の男女・国籍総数。年齢不詳は含みません。",
    breaks: [100, 500, 1500, 3000, 6000, 15000],
    colors: blues,
  },
  age10: {
    label: "10〜14歳人口",
    short: "10〜14歳",
    english: "AGES 10–14",
    unit: "人",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第2-7表",
    description: "10〜14歳の男女・国籍総数。年齢不詳は含みません。",
    breaks: [100, 500, 1500, 3000, 6000, 15000],
    colors: blues,
  },
  change: {
    label: "人口増減率",
    short: "人口増減率",
    english: "POPULATION CHANGE",
    unit: "%",
    period: "2015→2020年",
    source: "総務省統計局 令和2年国勢調査 第1-1表",
    description:
      "2015年から2020年の総人口の増減率。2020年の境域に組み替えた人口を使用します。",
    breaks: [-15, -10, -5, 0, 5, 10],
    colors: growth,
  },
  singleShare: {
    label: "単独世帯の割合",
    short: "単独世帯率",
    english: "ONE-PERSON HOUSEHOLDS",
    unit: "%",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第9-1表",
    description:
      "一般世帯（家族類型「不詳」を除く）に占める単独世帯（1人で住む世帯）の割合。未婚率とは別の指標です。",
    breaks: [20, 25, 30, 35, 40, 50],
    colors: plums,
  },
  single: {
    label: "単独世帯数",
    short: "単独世帯数",
    english: "ONE-PERSON HOUSEHOLDS",
    unit: "世帯",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第9-1表",
    description:
      "単独世帯（世帯人員が1人の世帯）の数。一般世帯に限り、施設等の世帯は含みません。",
    breaks: [500, 1000, 3000, 10000, 30000, 100000],
    colors: plums,
  },
  coupleChildrenShare: {
    label: "夫婦と子どもから成る世帯の割合",
    short: "夫婦と子ども世帯率",
    english: "COUPLE-AND-CHILDREN HOUSEHOLDS",
    unit: "%",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第9-1表",
    description:
      "一般世帯（家族類型「不詳」を除く）に占める「夫婦と子供から成る世帯」の割合。子どもの年齢は問いません。",
    breaks: [12, 16, 20, 24, 28, 32],
    colors: plums,
  },
  coupleChildren: {
    label: "夫婦と子どもから成る世帯数",
    short: "夫婦と子ども世帯数",
    english: "COUPLE-AND-CHILDREN HOUSEHOLDS",
    unit: "世帯",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第9-1表",
    description:
      "世帯の家族類型「夫婦と子供から成る世帯」の数。子どもの年齢は問いません。",
    breaks: [300, 1000, 2000, 5000, 10000, 30000],
    colors: plums,
  },
  under18Share: {
    label: "18歳未満の世帯員がいる世帯の割合",
    short: "18歳未満のいる世帯率",
    english: "HOUSEHOLDS WITH UNDER-18S",
    unit: "%",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第9-1表",
    description:
      "一般世帯に占める、18歳未満の世帯員がいる世帯の割合。分母は一般世帯の総数です。",
    breaks: [10, 13, 16, 19, 22, 25],
    colors: plums,
  },
  under18: {
    label: "18歳未満の世帯員がいる世帯数",
    short: "18歳未満のいる世帯数",
    english: "HOUSEHOLDS WITH UNDER-18S",
    unit: "世帯",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第9-1表",
    description: "18歳未満の世帯員がいる一般世帯の数。",
    breaks: [300, 1000, 2000, 5000, 10000, 30000],
    colors: plums,
  },
  unmarriedRate: {
    label: "25〜39歳の未婚率",
    short: "25〜39歳未婚率",
    english: "NEVER MARRIED, AGES 25–39",
    unit: "%",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第4-3表",
    description:
      "25〜39歳の人口（配偶関係「不詳」を除く）に占める未婚者の割合。男女計。単独世帯の割合とは別の指標です。",
    breaks: [30, 35, 40, 45, 50, 55],
    colors: plums,
  },
  unmarriedRateMale: {
    label: "25〜39歳の未婚率（男性）",
    short: "未婚率（男性）",
    english: "NEVER MARRIED, MEN 25–39",
    unit: "%",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第4-3表",
    description:
      "25〜39歳の男性（配偶関係「不詳」を除く）に占める未婚者の割合。",
    breaks: [30, 35, 40, 45, 50, 55],
    colors: plums,
  },
  unmarriedRateFemale: {
    label: "25〜39歳の未婚率（女性）",
    short: "未婚率（女性）",
    english: "NEVER MARRIED, WOMEN 25–39",
    unit: "%",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第4-3表",
    description:
      "25〜39歳の女性（配偶関係「不詳」を除く）に占める未婚者の割合。",
    breaks: [30, 35, 40, 45, 50, 55],
    colors: plums,
  },
  unmarried: {
    label: "25〜39歳の未婚者数",
    short: "25〜39歳未婚者数",
    english: "NEVER MARRIED, AGES 25–39",
    unit: "人",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第4-3表",
    description:
      "25〜39歳で配偶関係が「未婚」の人数（男女計）。配偶関係「不詳」の人は含みません。",
    breaks: [100, 300, 1000, 3000, 10000, 30000],
    colors: plums,
  },
  unmarriedMale: {
    label: "25〜39歳の未婚者数（男性）",
    short: "未婚者数（男性）",
    english: "NEVER MARRIED, MEN 25–39",
    unit: "人",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第4-3表",
    description: "25〜39歳で配偶関係が「未婚」の男性の人数。",
    breaks: [100, 300, 1000, 3000, 10000, 30000],
    colors: plums,
  },
  unmarriedFemale: {
    label: "25〜39歳の未婚者数（女性）",
    short: "未婚者数（女性）",
    english: "NEVER MARRIED, WOMEN 25–39",
    unit: "人",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第4-3表",
    description: "25〜39歳で配偶関係が「未婚」の女性の人数。",
    breaks: [100, 300, 1000, 3000, 10000, 30000],
    colors: plums,
  },
  elderlyOnlyShare: {
    label: "65歳以上の世帯員のみの世帯の割合",
    short: "高齢者のみの世帯率",
    english: "HOUSEHOLDS OF 65+ ONLY",
    unit: "%",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第27-4表",
    description:
      "一般世帯に占める、世帯員が全員65歳以上の世帯の割合。65歳以上の人が「いる」世帯とは別の指標です。",
    breaks: [15, 20, 25, 30, 35, 40],
    colors: plums,
  },
  elderlyOnly: {
    label: "65歳以上の世帯員のみの世帯数",
    short: "高齢者のみの世帯数",
    english: "HOUSEHOLDS OF 65+ ONLY",
    unit: "世帯",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第27-4表",
    description: "世帯員が全員65歳以上の一般世帯の数。",
    breaks: [500, 1000, 2000, 5000, 10000, 30000],
    colors: plums,
  },
  elderlySingleShare: {
    label: "65歳以上の単独世帯の割合",
    short: "65歳以上の単独世帯率",
    english: "PEOPLE 65+ LIVING ALONE",
    unit: "%",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第9-1表",
    description:
      "一般世帯（家族類型「不詳」を除く）に占める、65歳以上の人が1人で住む世帯の割合。",
    breaks: [8, 10, 12, 15, 18, 22],
    colors: plums,
  },
  elderlySingle: {
    label: "65歳以上の単独世帯数",
    short: "65歳以上の単独世帯数",
    english: "PEOPLE 65+ LIVING ALONE",
    unit: "世帯",
    period: "2020年",
    source: "総務省統計局 令和2年国勢調査 第9-1表",
    description: "65歳以上の人が1人で住む一般世帯の数。",
    breaks: [200, 500, 1000, 2000, 5000, 15000],
    colors: plums,
  },
};
export function valueOf(
  region: Region | undefined,
  metric: Metric,
): number | null {
  if (!region) return null;
  if (isHouseholdMetric(metric)) return region.households?.[metric] ?? null;
  if (metric === "age0") return region.ages[0];
  if (metric === "age5") return region.ages[1];
  if (metric === "age10") return region.ages[2];
  return region[metric];
}
export function colorOf(value: number | null, metric: Metric): string {
  if (value === null || !Number.isFinite(value)) return MISSING_COLOR;
  const { breaks, colors } = metrics[metric];
  const index = breaks.findIndex((limit) => value < limit);
  return colors[index < 0 ? colors.length - 1 : index];
}
const decimal = new Intl.NumberFormat("ja-JP", { maximumFractionDigits: 1 });
export const integer = new Intl.NumberFormat("ja-JP", {
  maximumFractionDigits: 0,
});
export function formatValue(value: number | null, metric: Metric): string {
  if (value === null) return "—";
  if (metric === "tfr") return value.toFixed(2);
  if (isShareMetric(metric))
    return `${metric === "change" && value > 0 ? "+" : ""}${value.toFixed(1)}`;
  if (metric === "childDensity") return decimal.format(value);
  return integer.format(value);
}
export function compact(value: number): string {
  if (Math.abs(value) >= 10000) return `${decimal.format(value / 10000)}万`;
  return integer.format(value);
}
export function rangeLabels(metric: Metric): string[] {
  const { breaks } = metrics[metric];
  const fmt = (v: number) => (metric === "tfr" ? v.toFixed(2) : compact(v));
  return [
    `${fmt(breaks[0])} 未満`,
    ...breaks
      .slice(0, -1)
      .map((b, i) => `${fmt(b)} – ${fmt(breaks[i + 1])} 未満`),
    `${fmt(breaks.at(-1)!)} 以上`,
  ];
}
export function difference(
  region: Region,
  national: Region,
  metric: Metric,
): string | null {
  const value = valueOf(region, metric),
    base = valueOf(national, metric);
  if (value === null || base === null) return null;
  const diff = value - base;
  const unit = isShareMetric(metric) ? "pt" : metrics[metric].unit;
  const result =
    metric === "tfr"
      ? Math.abs(diff).toFixed(2)
      : isShareMetric(metric) || metric === "childDensity"
        ? decimal.format(Math.abs(diff))
        : integer.format(Math.abs(diff));
  return `${diff >= 0 ? "+" : "−"}${result}${unit ? ` ${unit}` : ""}`;
}
