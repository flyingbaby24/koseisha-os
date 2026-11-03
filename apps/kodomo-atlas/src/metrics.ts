import type { Metric, Region } from "./types";

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
const growth = [
  "#bf826b",
  "#dab29c",
  "#ead8c1",
  "#edf0df",
  "#b8d4b7",
  "#7eb18e",
  "#387959",
];
export const metricList: Metric[] = [
  "tfr",
  "children",
  "childShare",
  "childDensity",
  "age0",
  "age5",
  "age10",
  "change",
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
};
export function valueOf(
  region: Region | undefined,
  metric: Metric,
): number | null {
  if (!region) return null;
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
  if (metric === "childShare" || metric === "change")
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
  const unit =
    metric === "childShare" || metric === "change"
      ? "pt"
      : metrics[metric].unit;
  const result =
    metric === "tfr"
      ? Math.abs(diff).toFixed(2)
      : metric === "childShare" ||
          metric === "change" ||
          metric === "childDensity"
        ? decimal.format(Math.abs(diff))
        : integer.format(Math.abs(diff));
  return `${diff >= 0 ? "+" : "−"}${result}${unit ? ` ${unit}` : ""}`;
}
