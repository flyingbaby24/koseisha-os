import { useEffect, useState, type CSSProperties } from "react";
import {
  ArrowRight,
  Armchair,
  Baby,
  Backpack,
  CalendarClock,
  ChartColumn,
  Check,
  ChevronDown,
  CircleHelp,
  Grid2X2,
  Hourglass,
  House,
  Layers2,
  MapPin,
  PieChart,
  Settings2,
  SplitSquareHorizontal,
  Tags,
  TrendingUp,
  User,
  UsersRound,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import SearchBox from "../SearchBox";
import { integer, metrics } from "../metrics";
import type { Metric, Region, Statistics } from "../types";
import {
  ageMetrics,
  categories,
  categoryOf,
  comparePresets,
  indicatorOf,
  indicators,
  isAge,
  pickVariant,
  SEX_LABELS,
  variantOf,
  type CategoryId,
  type Indicator,
} from "../ui";

const icons: Record<string, LucideIcon> = {
  baby: Baby,
  pie: PieChart,
  users: UsersRound,
  grid: Grid2X2,
  chart: ChartColumn,
  trend: TrendingUp,
  user: User,
  home: House,
  backpack: Backpack,
  ring: CalendarClock,
  elder: Hourglass,
  elderAlone: Armchair,
};

interface Props {
  data: Statistics;
  metric: Metric;
  onMetric: (metric: Metric) => void;
  secondMetric: Metric;
  compare: boolean;
  onCompare: (left: Metric, right: Metric) => void;
  onToggleCompare: () => void;
  prefecture: string;
  onPrefecture: (code: string) => void;
  scopeCount: number;
  onSelect: (region: Region) => void;
  showLabels: boolean;
  onShowLabels: () => void;
  showBackground: boolean;
  onShowBackground: () => void;
  onSources: () => void;
  page: "map" | "ranking";
}

function Ramp({ metric }: { metric: Metric }) {
  return (
    <span className="metric-ramp" aria-hidden="true">
      {metrics[metric].colors.map((color) => (
        <i key={color} style={{ background: color }} />
      ))}
    </span>
  );
}

export default function ControlPanel(props: Props) {
  const { metric } = props;
  const current = categoryOf(metric);
  // The tab follows the shown indicator (presets, detail shortcuts) but can be browsed freely.
  const [tab, setTab] = useState<CategoryId>(current);
  useEffect(() => setTab(current), [current]);
  const visible = indicators.filter((indicator) => indicator.category === tab);
  const activeIndicator = indicatorOf(metric);
  const variant = variantOf(metric);
  function choose(indicator: Indicator) {
    if (indicator === activeIndicator) return;
    // Keep the share/count (and sex) choice when moving between household indicators.
    props.onMetric(
      indicator.rate && activeIndicator.rate
        ? pickVariant(indicator, variant.mode, variant.sex)
        : indicator.metrics[0],
    );
  }
  return (
    <aside className="controls-panel" aria-label="表示設定">
      <div className="controls-intro">
        <h1>
          <span>日本のどこに子どもが多い？</span>
          <span>出生率が高いのはどこ？</span>
        </h1>
        <p>色が濃いほど値が高い（多い）地域。世帯構造・未婚・高齢化とも見比べられます。</p>
      </div>

      <section className="control-section search-section" aria-labelledby="search-heading">
        <h2 id="search-heading" className="control-label">
          地域をさがす
        </h2>
        <div className="search-row">
          <SearchBox data={props.data} onSelect={props.onSelect} />
          <div className="pref-select">
            <label htmlFor="prefecture">表示エリア</label>
            <div className="select-wrap">
              <MapPin size={16} aria-hidden="true" />
              <select
                id="prefecture"
                value={props.prefecture}
                onChange={(e) => props.onPrefecture(e.target.value)}
              >
                <option value="">日本全国</option>
                {props.data.prefectures.map((r) => (
                  <option value={r.prefCode} key={r.code}>
                    {r.name}
                  </option>
                ))}
              </select>
              <ChevronDown size={15} aria-hidden="true" />
            </div>
            <span className="pref-count">
              {integer.format(props.scopeCount)}地域
            </span>
          </div>
        </div>
      </section>

      <section className="control-section metric-section" aria-labelledby="metric-heading">
        <h2 id="metric-heading" className="control-label">
          {props.compare && props.page === "map"
            ? "地図Aの指標"
            : "地図に表示する指標"}
        </h2>
        <div className="category-tabs" role="tablist" aria-label="指標のカテゴリ">
          {categories.map((category) => {
            const selected = tab === category.id;
            return (
              <button
                key={category.id}
                id={`category-${category.id}`}
                role="tab"
                aria-selected={selected}
                aria-controls="metric-panel"
                tabIndex={selected ? 0 : -1}
                className={selected ? "active" : ""}
                onClick={() => setTab(category.id)}
                onKeyDown={(e) => {
                  if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
                  const i = categories.findIndex((c) => c.id === tab);
                  const next =
                    categories[(i + (e.key === "ArrowRight" ? 1 : categories.length - 1)) % categories.length];
                  setTab(next.id);
                  document.getElementById(`category-${next.id}`)?.focus();
                }}
              >
                {category.label}
                {category.id === current && !selected && (
                  <i className="tab-dot" aria-label="表示中の指標" />
                )}
              </button>
            );
          })}
        </div>
        {activeIndicator.rate && (
          <div className="variant-row">
            <div className="segmented" role="group" aria-label="割合と数の切り替え">
              {(["rate", "count"] as const).map((mode) => (
                <button
                  key={mode}
                  className={variant.mode === mode ? "active" : ""}
                  aria-pressed={variant.mode === mode}
                  onClick={() => props.onMetric(pickVariant(activeIndicator, mode, variant.sex))}
                >
                  {mode === "rate" ? "割合（%）" : "数"}
                </button>
              ))}
            </div>
            {activeIndicator.rate.length > 1 && (
              <div className="segmented" role="group" aria-label="男女の切り替え">
                {SEX_LABELS.map((label, sex) => (
                  <button
                    key={label}
                    className={variant.sex === sex ? "active" : ""}
                    aria-pressed={variant.sex === sex}
                    onClick={() => props.onMetric(pickVariant(activeIndicator, variant.mode, sex))}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        <div
          className="mode-options"
          id="metric-panel"
          role="tabpanel"
          aria-labelledby={`category-${tab}`}
        >
          <div className="metric-primary">
            {visible
              .filter((indicator) => indicator.primary)
              .map((indicator) => {
                const Icon = icons[indicator.icon];
                const base = indicator.metrics[0];
                const active = indicator === activeIndicator;
                return (
                  <button
                    key={indicator.id}
                    className={`metric-card ${active ? "active" : ""}`}
                    style={
                      {
                        "--metric-color": metrics[base].colors[5],
                        "--metric-soft": `${metrics[base].colors[0]}99`,
                      } as CSSProperties
                    }
                    aria-pressed={active}
                    aria-label={
                      indicator.rate
                        ? indicator.title
                        : metrics[base].label.includes(indicator.title)
                          ? metrics[base].label
                          : `${indicator.title}（${metrics[base].label}）`
                    }
                    aria-describedby={`metric-desc-${indicator.id}`}
                    onClick={() => choose(indicator)}
                  >
                    <span className="metric-card-icon">
                      <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                    </span>
                    <span className="metric-card-text" id={`metric-desc-${indicator.id}`}>
                      <span className="metric-card-title">
                        <b>{indicator.title}</b>
                      </span>
                      <small>{indicator.plain}</small>
                    </span>
                    <span className="metric-card-meta" aria-hidden="true">
                      <Ramp metric={base} />
                      <small>{metrics[base].period}</small>
                    </span>
                    <span className="metric-check" aria-hidden="true">
                      {active && <Check size={13} strokeWidth={3} />}
                    </span>
                  </button>
                );
              })}
          </div>
          {visible.some((indicator) => !indicator.primary) && (
            <div className="metric-other" role="group" aria-label="その他の指標">
              <span className="metric-other-label">その他の指標</span>
              {visible
                .filter((indicator) => !indicator.primary)
                .map((indicator) => {
                  const Icon = icons[indicator.icon];
                  const active = indicator === activeIndicator;
                  return (
                    <button
                      key={indicator.id}
                      className={`metric-chip ${active ? "active" : ""}`}
                      aria-pressed={active}
                      aria-label={
                        indicator.id === "age"
                          ? indicator.plain
                          : metrics[indicator.metrics[0]].label
                      }
                      onClick={() => choose(indicator)}
                    >
                      <Icon size={17} strokeWidth={1.8} aria-hidden="true" />
                      <span>{indicator.title}</span>
                    </button>
                  );
                })}
            </div>
          )}
        </div>
        {isAge(metric) && (
          <div className="age-tabs" role="group" aria-label="年齢階級">
            {ageMetrics.map((m) => (
              <button
                key={m}
                className={metric === m ? "active" : ""}
                aria-pressed={metric === m}
                onClick={() => props.onMetric(m)}
              >
                {metrics[m].short}
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="control-section compare-section" aria-labelledby="compare-heading">
        <h2 id="compare-heading" className="control-label">
          2つの地図で見比べる
        </h2>
        <div className="compare-presets">
          {comparePresets.map((preset) => {
            const active =
              props.compare &&
              props.page === "map" &&
              metric === preset.left &&
              props.secondMetric === preset.right;
            return (
              <button
                key={preset.id}
                className={`preset-button ${active ? "active" : ""}`}
                aria-pressed={active}
                title={`${metrics[preset.left].label}と${metrics[preset.right].label}を左右に並べて表示`}
                onClick={() => props.onCompare(preset.left, preset.right)}
              >
                <span className="preset-ramps" aria-hidden="true">
                  <Ramp metric={preset.left} />
                  <Ramp metric={preset.right} />
                </span>
                <span className="preset-text">
                  <b>{preset.title}</b>
                  <small>{preset.hint}</small>
                </span>
                {active && <Check size={15} aria-hidden="true" className="preset-check" />}
              </button>
            );
          })}
        </div>
        <button
          className={`compare-button ${props.compare && props.page === "map" ? "is-active" : ""}`}
          onClick={props.onToggleCompare}
          aria-pressed={props.compare && props.page === "map"}
        >
          <SplitSquareHorizontal size={16} aria-hidden="true" />
          <span>
            {props.compare && props.page === "map"
              ? "比較表示を終了"
              : "2つの指標を比較"}
          </span>
          {props.compare && props.page === "map" && (
            <X size={14} aria-hidden="true" />
          )}
        </button>
        <p className="compare-note">
          並べて見るための表示です。2つの指標の因果関係を示すものではありません。
        </p>
      </section>

      <details className="control-section display-options">
        <summary>
          <Settings2 size={16} aria-hidden="true" />
          地図の表示設定
          <ChevronDown size={15} aria-hidden="true" className="summary-chevron" />
        </summary>
        <div className="toggle-list">
          <button
            className={`toggle ${props.showLabels ? "active" : ""}`}
            role="switch"
            aria-checked={props.showLabels}
            onClick={props.onShowLabels}
          >
            <Tags size={16} aria-hidden="true" />
            <span>
              地名ラベル<small>主要都市と海の名前</small>
            </span>
            <i aria-hidden="true" />
          </button>
          <button
            className={`toggle ${props.showBackground ? "active" : ""}`}
            role="switch"
            aria-checked={props.showBackground}
            onClick={props.onShowBackground}
          >
            <Layers2 size={16} aria-hidden="true" />
            <span>
              背景地図<small>OpenStreetMap / CARTO（外部取得）</small>
            </span>
            <i aria-hidden="true" />
          </button>
        </div>
      </details>

      <button className="source-detail-link" onClick={props.onSources}>
        <CircleHelp size={16} aria-hidden="true" />
        指標の定義・出典・欠損値
        <ArrowRight size={14} aria-hidden="true" />
      </button>
    </aside>
  );
}
