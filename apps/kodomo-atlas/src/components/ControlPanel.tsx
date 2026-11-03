import {
  ArrowRight,
  Baby,
  ChartColumn,
  Check,
  ChevronDown,
  CircleHelp,
  Grid2X2,
  Layers2,
  MapPin,
  PieChart,
  Settings2,
  SplitSquareHorizontal,
  Tags,
  TrendingUp,
  UsersRound,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { CSSProperties } from "react";
import SearchBox from "../SearchBox";
import { integer, metrics } from "../metrics";
import type { Metric, Region, Statistics } from "../types";
import {
  ageMetrics,
  comparePresets,
  guide,
  isAge,
  otherMetrics,
  primaryMetrics,
} from "../ui";

const icons: Record<string, LucideIcon> = {
  tfr: Baby,
  childShare: PieChart,
  children: UsersRound,
  childDensity: Grid2X2,
  age0: ChartColumn,
  change: TrendingUp,
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
  return (
    <aside className="controls-panel" aria-label="表示設定">
      <div className="controls-intro">
        <h1>
          <span>日本のどこに子どもが多い？</span>
          <span>出生率が高いのはどこ？</span>
        </h1>
        <p>色が濃いほど、値が高い（多い）地域です。</p>
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
        <div className="mode-options">
          <div className="metric-primary">
            {primaryMetrics.map((m) => {
              const Icon = icons[m];
              const active = metric === m;
              return (
                <button
                  key={m}
                  className={`metric-card ${active ? "active" : ""}`}
                  style={
                    {
                      "--metric-color": metrics[m].colors[5],
                      "--metric-soft": `${metrics[m].colors[0]}99`,
                    } as CSSProperties
                  }
                  aria-pressed={active}
                  aria-label={
                    metrics[m].label.includes(guide[m].title)
                      ? metrics[m].label
                      : `${guide[m].title}（${metrics[m].label}）`
                  }
                  aria-describedby={`metric-desc-${m}`}
                  onClick={() => props.onMetric(m)}
                >
                  <span className="metric-card-icon">
                    <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
                  </span>
                  <span className="metric-card-text" id={`metric-desc-${m}`}>
                    <span className="metric-card-title">
                      <b>{guide[m].title}</b>
                      <small>{metrics[m].period}</small>
                    </span>
                    <small>{guide[m].plain}</small>
                  </span>
                  <Ramp metric={m} />
                  <span className="metric-check" aria-hidden="true">
                    {active && <Check size={13} strokeWidth={3} />}
                  </span>
                </button>
              );
            })}
          </div>
          <div className="metric-other" role="group" aria-label="その他の指標">
            <span className="metric-other-label">その他の指標</span>
            {otherMetrics.map(({ metric: m, label }) => {
              const Icon = icons[m];
              const active = m === "age0" ? isAge(metric) : metric === m;
              return (
                <button
                  key={m}
                  className={`metric-chip ${active ? "active" : ""}`}
                  aria-pressed={active}
                  aria-label={label}
                  onClick={() => props.onMetric(m)}
                >
                  <Icon size={17} strokeWidth={1.8} aria-hidden="true" />
                  <span>{m === "age0" ? "年齢別の人口" : metrics[m].short}</span>
                </button>
              );
            })}
          </div>
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
                {active && <Check size={16} aria-hidden="true" />}
              </button>
            );
          })}
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
        </div>
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
