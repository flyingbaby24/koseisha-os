import {
  ArrowRight,
  ChevronRight,
  CircleHelp,
  LocateFixed,
  MapPin,
  MousePointer2,
  X,
} from "lucide-react";
import {
  difference,
  formatValue,
  integer,
  metrics,
  valueOf,
} from "../metrics";
import type { Metric, Region } from "../types";
import {
  binIndex,
  guide,
  isCount,
  levelLabel,
  rankOf,
  sortByMetric,
  type Rank,
} from "../ui";
import { BaselineLabel } from "./common";
import { Distribution, LegendTable } from "./Distribution";

const keyMetrics: Metric[] = ["tfr", "childShare", "children", "childDensity"];

function AgeChart({ region }: { region: Region }) {
  const total = region.ages.reduce<number>((sum, n) => sum + (n ?? 0), 0);
  return (
    <div className="age-chart">
      <div className="age-chart-total">
        <span>0〜14歳人口</span>
        <b>
          {formatValue(region.children, "children")}
          <small>人</small>
        </b>
      </div>
      <div className="age-stacked" aria-hidden="true">
        {region.ages.map((n, i) => (
          <span
            key={i}
            style={{ width: `${total ? ((n ?? 0) / total) * 100 : 0}%` }}
          />
        ))}
      </div>
      <div className="age-chart-rows">
        {["0〜4歳", "5〜9歳", "10〜14歳"].map((label, i) => (
          <div key={label}>
            <span>
              <i />
              {label}
            </span>
            <b>
              {region.ages[i] === null ? "—" : integer.format(region.ages[i]!)}
              <small>人</small>
            </b>
          </div>
        ))}
      </div>
    </div>
  );
}

function RankLine({ label, rank }: { label: string; rank: Rank | null }) {
  if (!rank) return null;
  return (
    <div className="rank-line">
      <span className="rank-label">{label}</span>
      <b>
        {integer.format(rank.rank)}
        <small>位</small>
      </b>
      <span className="rank-total">
        {integer.format(rank.total)}地域中
        {rank.ties > 1 && (
          <>
            <br />
            同値 {integer.format(rank.ties)}地域
          </>
        )}
      </span>
    </div>
  );
}

function KeyStats({
  region,
  metric,
  onMetric,
}: {
  region: Region;
  metric: Metric;
  onMetric: (metric: Metric) => void;
}) {
  return (
    <div className="key-stats" role="group" aria-label="主な指標（押すと地図を切り替え）">
      {keyMetrics.map((m) => (
        <button
          key={m}
          className={m === metric ? "active" : ""}
          aria-pressed={m === metric}
          onClick={() => onMetric(m)}
          title={`地図を「${metrics[m].label}」に切り替え`}
        >
          <span className="key-stat-label">
            <i style={{ background: metrics[m].colors[4] }} />
            {guide[m].title}
          </span>
          <b>
            {formatValue(valueOf(region, m), m)}
            <small>{valueOf(region, m) === null ? "" : metrics[m].unit}</small>
          </b>
          <em>{metrics[m].period}</em>
        </button>
      ))}
    </div>
  );
}

function Footnote({
  metric,
  onSources,
}: {
  metric: Metric;
  onSources: () => void;
}) {
  return (
    <div className="detail-footnote">
      <p>
        出典：{metrics[metric].source}（{metrics[metric].period}）
      </p>
      <p>出生率は子育て環境の良し悪しを直接示す指標ではありません。</p>
      <button className="text-link" onClick={onSources}>
        <CircleHelp size={15} aria-hidden="true" />
        定義・出典・欠損値
      </button>
    </div>
  );
}

export default function DetailPanel({
  region,
  selected,
  unknownName,
  metric,
  baseline,
  scope,
  units,
  scopeName,
  onClear,
  onSelect,
  onRanking,
  onSources,
  onZoom,
  onMetric,
}: {
  region: Region;
  selected: boolean;
  unknownName?: string;
  metric: Metric;
  baseline: Region;
  scope: Region[];
  units: Region[];
  scopeName: string;
  onClear: () => void;
  onSelect: (region: Region) => void;
  onRanking: () => void;
  onSources: () => void;
  onZoom: () => void;
  onMetric: (metric: Metric) => void;
}) {
  const info = metrics[metric];
  const value = valueOf(region, metric);
  const isNational = region.code === "00000";
  const aggregate = ["a", "1"].includes(region.level);
  // Population counts of prefectures/city aggregates are never compared with the unit mean.
  const delta =
    value !== null && !isNational && (!aggregate || !isCount(metric))
      ? difference(region, baseline, metric)
      : null;

  if (unknownName)
    return (
      <aside id="region-details" className="detail-panel" tabIndex={-1} aria-label="地域の詳細データ">
        <div className="detail-header">
          <div>
            <span className="detail-pref">
              <MapPin size={14} aria-hidden="true" />
              北海道
            </span>
            <h2>{unknownName}</h2>
          </div>
          <button className="icon-button" aria-label="地域の選択を解除" onClick={onClear}>
            <X size={18} />
          </button>
        </div>
        <section className="detail-section">
          <p className="empty-data">
            この行政区域に対応する国勢調査・出生率の観測値は収録されていません。
          </p>
          <p className="small-note">欠損値を他の自治体の数値で補完していません。</p>
        </section>
        <Footnote metric={metric} onSources={onSources} />
      </aside>
    );

  if (!selected) {
    const top = sortByMetric(scope, metric).slice(0, 5);
    return (
      <aside
        id="region-details"
        className="detail-panel is-overview"
        aria-label="エリアの概要"
        tabIndex={-1}
      >
        <div className="detail-header">
          <div>
            <span className="detail-pref">
              <MapPin size={14} aria-hidden="true" />
              {isNational ? "エリアの概要" : "都道府県で絞り込み中"}
            </span>
            <h2>{isNational ? "日本全国" : scopeName}</h2>
            <p className="detail-sub">
              <span className="region-count">{integer.format(scope.length)}地域</span>
              市区町村・行政区
            </p>
          </div>
        </div>
        <section className="detail-section detail-main-stat">
          <div className="detail-stat-label">
            {info.label}
            <span>{info.period}</span>
          </div>
          <div className="detail-big-number">
            {formatValue(value, metric)}
            <small>{info.unit}</small>
          </div>
          {isNational ? (
            <p className="national-caption">
              {isCount(metric) ? "全国の合計" : "全国集計値"} ·{" "}
              {metric === "tfr"
                ? "5年間の統計に基づくベイズ推定値"
                : metric === "change"
                  ? "2015年の総人口との比較"
                  : "2020年10月1日現在"}
            </p>
          ) : delta ? (
            <p className="difference">
              <span className="difference-value">{delta}</span>
              <span>
                <BaselineLabel metric={metric} />{" "}
                {formatValue(valueOf(baseline, metric), metric)}
                {info.unit}との差
              </span>
            </p>
          ) : (
            <p className="national-caption">{scopeName}の合計 · 2020年10月1日現在</p>
          )}
          {isNational && isCount(metric) && (
            <div className="reference-box">
              <span>
                <BaselineLabel metric={metric} />
              </span>
              <b>
                {formatValue(valueOf(baseline, metric), metric)}
                <small>{info.unit}</small>
              </b>
            </div>
          )}
        </section>

        <section className="detail-section ranking-preview">
          <div className="detail-section-title">
            <h3>
              {guide[metric].high === "多い" ? "多い" : "高い"}地域
              <span>{scopeName} · 上位5</span>
            </h3>
          </div>
          <ol>
            {top.map((r) => {
              const rank = rankOf(r, scope, metric)!;
              return (
                <li key={r.code}>
                  <button className="rank-preview-row" onClick={() => onSelect(r)}>
                    <span className={`rank-number rank-${rank.rank}`}>
                      {rank.rank}
                    </span>
                    <span className="rank-place">
                      <strong>{r.name}</strong>
                      <small>{r.prefecture}</small>
                    </span>
                    <b>
                      {formatValue(valueOf(r, metric), metric)}
                      <small>{info.unit}</small>
                    </b>
                    <ChevronRight size={15} aria-hidden="true" />
                  </button>
                </li>
              );
            })}
          </ol>
          <button className="text-button" onClick={onRanking}>
            ランキングをすべて見る <ArrowRight size={15} aria-hidden="true" />
          </button>
        </section>

        <section className="detail-section">
          <div className="detail-section-title">
            <h3>
              色分けと地域数
              <span>{info.unit ? `単位：${info.unit}` : info.period}</span>
            </h3>
          </div>
          <LegendTable regions={scope} metric={metric} />
        </section>

        <section className="detail-section">
          <div className="detail-section-title">
            <h3>
              {isNational ? "全国" : scopeName}の主な指標
              <span>押すと地図を切り替え</span>
            </h3>
          </div>
          <KeyStats region={region} metric={metric} onMetric={onMetric} />
        </section>

        <div className="selection-tip">
          <MousePointer2 size={18} aria-hidden="true" />
          <p>
            地図の地域をクリック（タップ）すると、数値・順位・年齢構成を表示します。
          </p>
        </div>
        <Footnote metric={metric} onSources={onSources} />
      </aside>
    );
  }

  const nationalRank = aggregate ? null : rankOf(region, units, metric);
  const prefUnits = units.filter((r) => r.prefCode === region.prefCode);
  const prefRank = aggregate ? null : rankOf(region, prefUnits, metric);
  return (
    <aside
      id="region-details"
      className="detail-panel"
      aria-label="地域の詳細データ"
      tabIndex={-1}
    >
      <div className="detail-header">
        <div>
          <span className="detail-pref">
            <MapPin size={14} aria-hidden="true" />
            {region.prefecture}
          </span>
          <h2>{region.name}</h2>
          <p className="detail-sub">
            {levelLabel(region)} · 自治体コード {region.code}
          </p>
        </div>
        <div className="detail-header-actions">
          <button
            className="icon-button"
            aria-label="この地域を地図で拡大"
            title="この地域を地図で拡大"
            onClick={onZoom}
          >
            <LocateFixed size={18} />
          </button>
          <button
            className="icon-button"
            aria-label="地域の選択を解除"
            title="地域の選択を解除"
            onClick={onClear}
          >
            <X size={18} />
          </button>
        </div>
      </div>

      <section className="detail-section detail-main-stat">
        <div className="detail-stat-label">
          {info.label}
          <span>{info.period}</span>
        </div>
        <div className="detail-big-number">
          {formatValue(value, metric)}
          <small>{value === null ? "" : info.unit}</small>
        </div>
        {value === null ? (
          <span className="missing-label">非公表・算出不可（0ではありません）</span>
        ) : delta ? (
          <p className="difference">
            <span
              className={`difference-value ${delta.startsWith("−") ? "is-lower" : "is-higher"}`}
            >
              {delta}
            </span>
            <span>
              <BaselineLabel metric={metric} />{" "}
              {formatValue(valueOf(baseline, metric), metric)}
              {info.unit}との差
            </span>
          </p>
        ) : null}
        {value !== null && (
          <div className="position">
            <Distribution
              regions={units}
              metric={metric}
              highlight={binIndex(value, metric)}
            />
            <div className="position-scale" aria-hidden="true">
              <span>{guide[metric].low}</span>
              <span>全国の地域数の分布</span>
              <span>{guide[metric].high}</span>
            </div>
          </div>
        )}
        {(nationalRank || prefRank) && (
          <div className="rank-lines">
            <RankLine label="全国の順位" rank={nationalRank} />
            <RankLine label={`${region.prefecture}内の順位`} rank={prefRank} />
            <p className="rank-note">
              値の高い順（同じ値は同順位）。欠損・非公表の地域は順位から除外しています。
            </p>
          </div>
        )}
        {aggregate && (
          <p className="small-note">
            市全体の公表値です。地図の色・順位は行政区単位で集計しています（市全体はランキング対象外）。
          </p>
        )}
      </section>

      <section className="detail-section">
        <div className="detail-section-title">
          <h3>
            主な指標<span>押すと地図を切り替え</span>
          </h3>
        </div>
        <KeyStats region={region} metric={metric} onMetric={onMetric} />
      </section>

      <section className="detail-section">
        <div className="detail-section-title">
          <h3>
            子どもの人口<span>2020年10月1日</span>
          </h3>
        </div>
        <AgeChart region={region} />
        <dl className="population-meta">
          <div>
            <dt>総人口</dt>
            <dd>
              {region.population === null ? "—" : integer.format(region.population)}
              <small>人</small>
            </dd>
          </div>
          <div>
            <dt>年齢不詳</dt>
            <dd>
              {region.unknownAge === null ? "—" : integer.format(region.unknownAge)}
              <small>人</small>
            </dd>
          </div>
          <div>
            <dt>人口増減率（2015→2020年）</dt>
            <dd>
              {formatValue(region.change, "change")}
              <small>{region.change === null ? "" : "%"}</small>
            </dd>
          </div>
        </dl>
      </section>
      <Footnote metric={metric} onSources={onSources} />
    </aside>
  );
}
