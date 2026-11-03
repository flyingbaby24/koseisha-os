import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownUp,
  ArrowRight,
  ArrowUpRight,
  Baby,
  BookOpen,
  ChartColumn,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Database,
  Download,
  ExternalLink,
  Grid2X2,
  Layers2,
  Map as MapIcon,
  MapPin,
  MousePointer2,
  PanelLeftClose,
  PieChart,
  SlidersHorizontal,
  SplitSquareHorizontal,
  TrendingUp,
  UsersRound,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import MapView, { JAPAN_BOUNDS } from "./MapView";
import SearchBox from "./SearchBox";
import { comparisonReference, regionIndex, unitCounts } from "./regions";
import {
  colorOf,
  difference,
  formatValue,
  integer,
  metricList,
  metrics,
  MISSING_COLOR,
  rangeLabels,
  valueOf,
} from "./metrics";
import type {
  Bounds,
  FocusRequest,
  Geography,
  MapPosition,
  Metric,
  Region,
  Statistics,
} from "./types";

const modeOptions: { metric: Metric; icon: LucideIcon; label: string }[] = [
  { metric: "tfr", icon: Baby, label: "合計特殊出生率" },
  { metric: "children", icon: UsersRound, label: "0〜14歳人口" },
  { metric: "childShare", icon: PieChart, label: "年少人口比率" },
  { metric: "childDensity", icon: Grid2X2, label: "子どもの人口密度" },
  { metric: "age0", icon: ChartColumn, label: "年齢別の人口分布" },
  { metric: "change", icon: TrendingUp, label: "人口増減率" },
];

function unionBounds(regions: Region[]): Bounds {
  const bounds = regions.flatMap((r) => (r.bounds ? [r.bounds] : []));
  if (!bounds.length) return JAPAN_BOUNDS;
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

function Logo() {
  return (
    <>
      <span className="brand-mark" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </span>
      <span className="brand-name">
        こどもアトラス<span>KODOMO ATLAS</span>
      </span>
    </>
  );
}

function BaselineLabel({ metric }: { metric: Metric }) {
  return (
    <>
      {["children", "age0", "age5", "age10"].includes(metric)
        ? "自治体平均（参考）"
        : "全国集計値"}
    </>
  );
}

function Distribution({
  regions,
  metric,
}: {
  regions: Region[];
  metric: Metric;
}) {
  const counts = getBinCounts(regions, metric);
  const max = Math.max(...counts, 1);
  return (
    <div
      className="distribution"
      role="img"
      aria-label={`市区町村の分布。${rangeLabels(metric)
        .map((label, i) => `${label}が${counts[i]}地域`)
        .join("、")}`}
    >
      <div className="histogram">
        {counts.map((count, i) => (
          <div key={i} className="histogram-column">
            <span
              style={{
                height: `${(count / max) * 100}%`,
                background: metrics[metric].colors[i],
              }}
              title={`${rangeLabels(metric)[i]}：${count}地域`}
            />
          </div>
        ))}
      </div>
      <div className="histogram-labels">
        <span>低い</span>
        <span>高い</span>
      </div>
    </div>
  );
}

function getBinCounts(regions: Region[], metric: Metric): number[] {
  const bins = Array(7).fill(0) as number[];
  regions.forEach((region) => {
    const v = valueOf(region, metric);
    if (v === null) return;
    const index = metrics[metric].breaks.findIndex((limit) => v < limit);
    bins[index < 0 ? 6 : index]++;
  });
  return bins;
}

function Legend({ regions, metric }: { regions: Region[]; metric: Metric }) {
  const counts = getBinCounts(regions, metric);
  const missing = regions.filter((r) => valueOf(r, metric) === null).length;
  return (
    <div className="legend">
      <div className="control-label">
        <span>
          色分けの目安
          {metrics[metric].unit && <small>（{metrics[metric].unit}）</small>}
        </span>
        <span className="subtle">地域数</span>
      </div>
      <Distribution regions={regions} metric={metric} />
      <div className="legend-rows">
        {rangeLabels(metric).map((label, i) => (
          <div className="legend-row" key={i}>
            <i style={{ background: metrics[metric].colors[i] }} />
            <span>{label}</span>
            <b>{integer.format(counts[i])}</b>
          </div>
        ))}
      </div>
      <div className="legend-row missing">
        <i style={{ background: MISSING_COLOR }} />
        <span>欠損・非公表（0とは別）</span>
        <b>{missing}</b>
      </div>
      <p className="legend-note">
        全国共通の固定区分 · 極端な値で区分は変わりません
      </p>
    </div>
  );
}

function AgeChart({ region }: { region: Region }) {
  const total = region.ages.reduce<number>((sum, n) => sum + (n ?? 0), 0);
  return (
    <div className="age-chart">
      <div className="detail-section-title">
        <span>子ども人口の年齢構成</span>
        <small>2020年</small>
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

function DetailPanel({
  region,
  selected,
  metric,
  baseline,
  scope,
  onClear,
  onSelect,
  onRanking,
  onSources,
  onZoom,
  unknownName,
}: {
  region: Region;
  selected: boolean;
  metric: Metric;
  baseline: Region;
  scope: Region[];
  onClear: () => void;
  onSelect: (region: Region) => void;
  onRanking: () => void;
  onSources: () => void;
  onZoom: () => void;
  unknownName?: string;
}) {
  const value = valueOf(region, metric);
  const isMunicipality = !["a", "1"].includes(region.level);
  const delta = difference(region, baseline, metric);
  const top = [...scope]
    .filter((r) => valueOf(r, metric) !== null)
    .sort(
      (a, b) =>
        valueOf(b, metric)! - valueOf(a, metric)! ||
        a.code.localeCompare(b.code),
    )
    .slice(0, 4);
  if (unknownName)
    return (
      <aside id="region-details" className="detail-panel" tabIndex={-1}>
        <div className="detail-card">
          <span className="eyebrow">REGION DATA</span>
          <h2>{unknownName}</h2>
          <p className="empty-data">
            この行政区域に対応する国勢調査・出生率の観測値は収録されていません。
          </p>
          <p className="small-note">
            欠損値を他の自治体の数値で補完していません。
          </p>
          <button className="text-button" onClick={onSources}>
            出典と欠損値を確認 <ArrowRight size={14} />
          </button>
          <button className="button secondary full" onClick={onClear}>
            全国の集計に戻る
          </button>
        </div>
      </aside>
    );
  return (
    <aside
      id="region-details"
      className="detail-panel"
      aria-label="地域の詳細データ"
      aria-live="polite"
      tabIndex={-1}
    >
      <section className="detail-card">
        <div className="detail-eyebrow">
          <span className="eyebrow">
            {selected ? "REGION DATA" : "AREA OVERVIEW"}
          </span>
          {selected && (
            <button
              className="icon-button"
              aria-label="地域の選択を解除"
              onClick={onClear}
            >
              <X size={16} />
            </button>
          )}
        </div>
        <div className="detail-region">
          <span>
            <MapPin size={13} />
            {region.code === "00000" ? "日本全国" : region.prefecture}
          </span>
          <h2>{region.code === "00000" ? "全国のサマリー" : region.name}</h2>
          <p>
            {selected
              ? `自治体コード ${region.code}${region.level === "1" ? " · 市・区部全体" : ""}`
              : `${integer.format(scope.length)} 市区町村・行政区`}
          </p>
        </div>
        <div className="detail-main-stat">
          <div className="detail-stat-label">
            {metrics[metric].label}
            <span>{metrics[metric].period}</span>
          </div>
          <div className="detail-big-number">
            {formatValue(value, metric)}
            <small>{metrics[metric].unit}</small>
          </div>
          {value === null ? (
            <span className="missing-label">非公表・算出不可</span>
          ) : selected && isMunicipality && delta ? (
            <div className="difference">
              <span className="difference-value">{delta}</span>
              <span>
                <BaselineLabel metric={metric} />
                との差
              </span>
            </div>
          ) : (
            <div className="national-caption">
              {metric === "tfr"
                ? "5年間の統計に基づくベイズ推定値"
                : metric === "change"
                  ? "2015年の総人口との比較"
                  : "2020年10月1日現在"}
            </div>
          )}
        </div>
        <div className="detail-mini-grid">
          {(["tfr", "children", "childShare", "childDensity"] as Metric[])
            .filter((m) => m !== metric)
            .slice(0, 2)
            .map((m) => (
              <div key={m}>
                <span>{metrics[m].label}</span>
                <b>
                  {formatValue(valueOf(region, m), m)}
                  <small>{metrics[m].unit}</small>
                </b>
                <em>{metrics[m].period}</em>
              </div>
            ))}
        </div>
        <AgeChart region={region} />
        {selected && (
          <div className="population-meta">
            <span>
              総人口{" "}
              <b>
                {region.population === null
                  ? "—"
                  : integer.format(region.population)}
                人
              </b>
            </span>
            <span>
              年齢不詳{" "}
              <b>
                {region.unknownAge === null
                  ? "—"
                  : integer.format(region.unknownAge)}
                人
              </b>
            </span>
          </div>
        )}
        {selected ? (
          <button className="text-button" onClick={onZoom}>
            この地域を地図で拡大 <ArrowUpRight size={15} />
          </button>
        ) : (
          <div className="selection-tip">
            <MousePointer2 size={16} />
            <p>
              気になる地域をクリックすると、
              <br />
              全国値との差や年齢構成がわかります。
            </p>
          </div>
        )}
      </section>
      <section className="ranking-preview">
        <div className="detail-section-title">
          <h3>{metrics[metric].short}ランキング</h3>
          <span>上位</span>
        </div>
        {top.map((r, i) => (
          <button
            className="rank-preview-row"
            key={r.code}
            onClick={() => onSelect(r)}
          >
            <span className={`rank-number rank-${i + 1}`}>
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="rank-place">
              <strong>{r.name}</strong>
              <small>{r.prefecture}</small>
            </span>
            <b>
              {formatValue(valueOf(r, metric), metric)}
              <small>{metrics[metric].unit}</small>
            </b>
            <ChevronRight size={13} />
          </button>
        ))}
        <button className="text-button" onClick={onRanking}>
          ランキングをすべて見る <ArrowRight size={14} />
        </button>
      </section>
      <p className="detail-footnote">
        {metrics[metric].source}
        <button onClick={onSources} aria-label="統計の説明を開く">
          <CircleHelp size={13} />
        </button>
      </p>
    </aside>
  );
}

function DataDialog({
  data,
  onClose,
}: {
  data: Statistics;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const instance = dialog.current;
    instance?.showModal();
    return () => {
      instance?.close();
      previous?.focus();
    };
  }, []);
  const missing = data.municipalities.filter((r) => r.tfr === null);
  const units = unitCounts(data);
  return (
    <dialog
      ref={dialog}
      className="data-dialog"
      aria-labelledby="data-title"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-heading">
        <div>
          <span className="eyebrow">DATA & METHODOLOGY</span>
          <h2 id="data-title">この地図のデータについて</h2>
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="説明を閉じる"
        >
          <X size={21} />
        </button>
      </div>
      <div className="dialog-body">
        <p className="dialog-intro">
          公表された統計を、市区町村コードでつなぎました。
          <br />
          それぞれの指標が表す時点・対象・集計方法をご確認ください。
        </p>
        <div className="data-year-notice">
          <Database size={20} />
          <p>
            <b>出生率は2018〜2022年、人口は2020年。</b>
            <span>異なる年度の指標を、同じ年の実績として扱っていません。</span>
          </p>
        </div>
        <h3>データの出典</h3>
        <div className="source-list">
          {data.metadata.sources.map((source, i) => (
            <article key={source.file}>
              <span className="source-index">0{i + 1}</span>
              <div>
                <h4>
                  <a href={source.page} target="_blank" rel="noreferrer">
                    {source.title}
                    <ExternalLink size={13} />
                  </a>
                </h4>
                <p>
                  {source.period}
                  <span>公表 {source.published}</span>
                </p>
                <a
                  className="source-download"
                  href={source.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  公式ファイルをダウンロード <Download size={12} />
                </a>
              </div>
            </article>
          ))}
        </div>
        <h3>集計と指標の定義</h3>
        <dl className="definition-list">
          {Object.entries(data.metadata.definitions).map(
            ([key, description]) => (
              <div key={key}>
                <dt>
                  {
                    (
                      {
                        tfr: "合計特殊出生率",
                        children: "子ども人口・年齢別人口",
                        childShare: "年少人口比率",
                        childDensity: "子どもの人口密度",
                        change: "人口増減率",
                        geography: "行政区域",
                        units: "表示・集計単位",
                      } as Record<string, string>
                    )[key]
                  }
                </dt>
                <dd>{description}</dd>
              </div>
            ),
          )}
          <div>
            <dt>全国との比較</dt>
            <dd>
              出生率・年少人口比率・密度・人口増減率は全国の集計値と比較し、自治体の単純平均には置き換えません。人口数・年齢別人口だけは「自治体平均（参考）」として1,896市区町村・行政区の単純平均を示します。これは全国集計値とは別の参考値です。都道府県・市全体の人口数にはこの差を表示しません。
            </dd>
          </div>
        </dl>
        <h3>1,896地域の内訳</h3>
        <p className="method-text">
          {units.cities}市（政令指定都市を除く）＋{units.towns}町＋
          {units.villages}村＋
          {units.specialWards}特別区＋{units.cityWards}行政区＝
          {data.municipalities.length}地域です。
          20政令指定都市の市全体と東京都区部の21集計行は検索用に保持し、地図の人口集計・ランキングには重ねていません。
        </p>
        <h3>欠損値・非公表値</h3>
        <p className="method-text">
          出生率が非公表の9町村は灰色で表示し、ランキングから除外します。出生率0は最低区分の色で数値「0.00」、欠損は灰色と「—」で区別します。収録データの出生率0の地域はありません。ゼロへの置換や近隣地域の値による補完はしていません。
        </p>
        <div className="missing-regions">
          {missing.map((r) => (
            <span key={r.code}>
              {r.prefecture} {r.name}
              <small>{r.code}</small>
            </span>
          ))}
        </div>
        <p className="method-text">
          年少人口比率は{data.metadata.missingByMetric.childShare}
          地域、人口増減率は{data.metadata.missingByMetric.change}
          地域で算出不可。北方地域の6行政区域には対応する人口統計がなく、欠損色で表示します。コードのない境界未定部分は表示対象外です。
        </p>
        <p className="method-text">
          年齢不詳人口は補完していません。年少人口比率の分母からは除かれ、総人口には含まれます。出生率だけで子育て環境の良し悪しや因果関係を示すものではありません。
        </p>
        <div className="data-provenance">
          <Check size={16} />
          <div>
            <b>元データのSHA-256を記録</b>
            <p>
              加工日時：
              {new Date(data.metadata.generatedAt).toLocaleString("ja-JP")}
              <br />
              行政区域：{integer.format(data.metadata.geometryCount)}区域 /
              人口収録：{integer.format(data.metadata.municipalityCount)}地域
            </p>
            <a href={`${import.meta.env.BASE_URL}data/statistics.json`} target="_blank" rel="noreferrer">
              加工済みデータ・取得元・ハッシュを確認 <ExternalLink size={12} />
            </a>
          </div>
        </div>
      </div>
    </dialog>
  );
}

function RankingTable({
  regions,
  metric,
  baseline,
  onSelect,
}: {
  regions: Region[];
  metric: Metric;
  baseline: Region;
  onSelect: (region: Region) => void;
}) {
  const [descending, setDescending] = useState(true);
  const [page, setPage] = useState(0);
  useEffect(() => {
    setPage(0);
  }, [regions, metric, descending]);
  const ranked = useMemo(
    () =>
      [...regions]
        .filter((r) => valueOf(r, metric) !== null)
        .sort(
          (a, b) =>
            (valueOf(b, metric)! - valueOf(a, metric)!) *
              (descending ? 1 : -1) || a.code.localeCompare(b.code),
        ),
    [regions, metric, descending],
  );
  const totalPages = Math.ceil(ranked.length / 25);
  function download() {
    const rows = [
      [
        "順位",
        "市区町村コード",
        "都道府県",
        "市区町村",
        metrics[metric].label,
        "単位",
        "統計期間",
      ],
      ...ranked.map((r, i) => [
        i + 1,
        r.code,
        r.prefecture,
        r.name,
        valueOf(r, metric),
        metrics[metric].unit,
        metrics[metric].period,
      ]),
    ];
    const csv =
      "\uFEFF" +
      rows
        .map((row) =>
          row.map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`).join(","),
        )
        .join("\r\n");
    const url = URL.createObjectURL(
      new Blob([csv], { type: "text/csv;charset=utf-8;" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `kodomo-atlas-${metric}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <section className="ranking-table-card">
      <div className="ranking-table-heading">
        <div>
          <span className="eyebrow">MUNICIPALITY RANKING</span>
          <h2>{metrics[metric].label}のランキング</h2>
          <p>
            {metrics[metric].period} · {integer.format(ranked.length)}地域 ·
            欠損値は除外
          </p>
        </div>
        <button className="button secondary" onClick={download}>
          <Download size={15} />
          CSV
        </button>
      </div>
      <div className="ranking-table-tools">
        <span>地域を選択すると地図で詳細を表示します</span>
        <button onClick={() => setDescending((v) => !v)}>
          <ArrowDownUp size={14} />
          {descending ? "高い順" : "低い順"}
          <ChevronDown size={13} />
        </button>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>順位</th>
              <th>市区町村</th>
              <th>
                {metrics[metric].label}
                {metrics[metric].unit && ` (${metrics[metric].unit})`}
              </th>
              <th>
                <BaselineLabel metric={metric} />
                との差
              </th>
              <th />
            </tr>
          </thead>
          <tbody>
            {ranked.slice(page * 25, (page + 1) * 25).map((r, i) => (
              <tr key={r.code}>
                <td className="table-rank">{page * 25 + i + 1}</td>
                <td>
                  <button className="table-place" onClick={() => onSelect(r)}>
                    <strong>{r.name}</strong>
                    <small>
                      {r.prefecture} · {r.code}
                    </small>
                  </button>
                </td>
                <td className="table-value">
                  <i
                    style={{ background: colorOf(valueOf(r, metric), metric) }}
                  />
                  {formatValue(valueOf(r, metric), metric)}
                </td>
                <td className="table-difference">
                  {difference(r, baseline, metric)}
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={`${r.name}を地図で表示`}
                    onClick={() => onSelect(r)}
                  >
                    <ArrowUpRight size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-pagination">
        <span>
          {ranked.length ? page * 25 + 1 : 0}–
          {Math.min((page + 1) * 25, ranked.length)} /{" "}
          {integer.format(ranked.length)}地域
        </span>
        <div>
          <button
            className="icon-button"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            aria-label="前のページ"
          >
            <ChevronLeft size={17} />
          </button>
          <span>
            {page + 1} / {Math.max(totalPages, 1)}
          </span>
          <button
            className="icon-button"
            disabled={page + 1 >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            aria-label="次のページ"
          >
            <ChevronRight size={17} />
          </button>
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [data, setData] = useState<Statistics | null>(null);
  const [geometry, setGeometry] = useState<Geography | null>(null);
  const [error, setError] = useState("");
  const [metric, setMetric] = useState<Metric>("tfr");
  const [secondMetric, setSecondMetric] = useState<Metric>("childShare");
  const [prefecture, setPrefecture] = useState("");
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [compare, setCompare] = useState(false);
  const [page, setPage] = useState<"map" | "ranking">("map");
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const [showBackground, setShowBackground] = useState(false);
  const [focus, setFocus] = useState<FocusRequest | null>(null);
  const [position, setPosition] = useState<MapPosition | null>(null);
  const [mobileSettings, setMobileSettings] = useState(false);
  const nextFocus = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await Promise.all(
          ["data/statistics.json", "data/municipalities.geojson"].map((url) =>
            fetch(`${import.meta.env.BASE_URL}${url}`, { signal: controller.signal }),
          ),
        );
        if (response.some((r) => !r.ok))
          throw new Error(
            "公開統計データを読み込めませんでした。READMEのデータ取得手順をご確認ください。",
          );
        const [statistics, geography] = await Promise.all(
          response.map((r) => r.json()),
        );
        setData(statistics);
        setGeometry(geography);
      } catch (e) {
        if (!controller.signal.aborted)
          setError(
            e instanceof Error ? e.message : "データの読み込みに失敗しました。",
          );
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  const byCode = useMemo(
    () => (data ? regionIndex(data) : new Map<string, Region>()),
    [data],
  );
  const scope = useMemo(
    () =>
      data?.municipalities.filter(
        (r) => !prefecture || r.prefCode === prefecture,
      ) ?? [],
    [data, prefecture],
  );
  const scopeName =
    data?.prefectures.find((r) => r.prefCode === prefecture)?.name ?? "全国";
  const baseline = useMemo(() => {
    if (!data) return null;
    return comparisonReference(data);
  }, [data]);
  const detailRegion = selectedCode
    ? byCode.get(selectedCode)
    : (data?.prefectures.find((r) => r.prefCode === prefecture) ??
      data?.national);
  const unknownName =
    selectedCode && !detailRegion
      ? geometry?.features.find((f) => f.properties.code === selectedCode)
          ?.properties.name
      : undefined;
  const selectedMetricValue = detailRegion
    ? valueOf(detailRegion, metric)
    : null;

  function focusBounds(bounds: Bounds) {
    setFocus({ bounds, key: ++nextFocus.current });
  }
  function changePrefecture(code: string) {
    setPrefecture(code);
    setSelectedCode(null);
    focusBounds(
      code
        ? unionBounds(data!.municipalities.filter((r) => r.prefCode === code))
        : JAPAN_BOUNDS,
    );
  }
  function selectRegion(region: Region) {
    if (region.level === "a") {
      changePrefecture(region.prefCode);
      setPage("map");
      return;
    }
    setSelectedCode(region.code);
    if (prefecture && region.prefCode !== prefecture)
      setPrefecture(region.prefCode);
    const resolved = byCode.get(region.code) ?? region;
    const bounds =
      resolved.bounds ??
      unionBounds(
        data!.municipalities.filter((r) =>
          region.code === "13100"
            ? r.prefCode === "13" && r.level === "0"
            : r.name.startsWith(region.name),
        ),
      );
    focusBounds(bounds);
    setPage("map");
    setMobileSettings(false);
  }
  function home() {
    setPrefecture("");
    setSelectedCode(null);
    focusBounds(JAPAN_BOUNDS);
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <button
            className="brand"
            onClick={() => {
              if (data) home();
              setPage("map");
            }}
            aria-label="こどもアトラス ホーム"
          >
            <Logo />
          </button>
          <nav className="main-nav" aria-label="メインナビゲーション">
            <button
              className={page === "map" ? "active" : ""}
              onClick={() => setPage("map")}
            >
              <MapIcon size={16} />
              <span>地図で見る</span>
            </button>
            <button
              className={page === "ranking" ? "active" : ""}
              onClick={() => setPage("ranking")}
            >
              <ChartColumn size={16} />
              <span>ランキング</span>
            </button>
            <button onClick={() => setSourcesOpen(true)}>
              <BookOpen size={16} />
              <span>データについて</span>
            </button>
          </nav>
          <button className="data-status" onClick={() => setSourcesOpen(true)}>
            <span />
            <span>公的統計データを使用</span>
            <ExternalLink size={12} />
          </button>
        </div>
      </header>
      <main className="page-shell">
        <section className="intro">
          <div>
            <div className="eyebrow intro-eyebrow">
              <span />
              JAPAN DEMOGRAPHIC EXPLORER
            </div>
            <h1>
              日本の未来を、<span>地図から。</span>
            </h1>
            <p>出生率と子どもの人口から、まちごとの姿を見つけよう。</p>
          </div>
          <div className="intro-note">
            <span className="tiny-map">
              <MapIcon size={34} strokeWidth={1} />
            </span>
            <p>
              47都道府県、その先の
              <br />
              <b>小さな地域の違いまで。</b>
            </p>
          </div>
        </section>
        {error ? (
          <section className="load-error" role="alert">
            <Database size={28} />
            <h2>データを読み込めませんでした</h2>
            <p>{error}</p>
            <button className="button" onClick={() => location.reload()}>
              再読み込み
            </button>
          </section>
        ) : !data || !geometry || !baseline ? (
          <section className="loading-state" aria-busy="true">
            <div className="loading-map">
              <Logo />
            </div>
            <span className="loading-spinner" />
            <h2>日本の地域データをひらいています</h2>
            <p>全国の公開統計と市区町村の境界を読み込み中…</p>
          </section>
        ) : (
          <>
            <section className="summary-grid" aria-label="全国の主要指標">
              <article className="summary-card">
                <div>
                  <span className="summary-label">全国の合計特殊出生率</span>
                  <div className="summary-value">
                    {data.national.tfr!.toFixed(2)}
                    <small>人</small>
                  </div>
                  <span className="summary-period">
                    2018–2022年 · ベイズ推定値
                  </span>
                </div>
                <span className="summary-icon">
                  <Baby size={23} strokeWidth={1.5} />
                </span>
              </article>
              <article className="summary-card">
                <div>
                  <span className="summary-label">全国の0〜14歳人口</span>
                  <div className="summary-value">
                    {(data.national.children! / 10000).toLocaleString("ja-JP", {
                      minimumFractionDigits: 1,
                      maximumFractionDigits: 1,
                    })}
                    <small>万人</small>
                  </div>
                  <span className="summary-period">
                    2020年国勢調査 · 年齢判明分
                  </span>
                </div>
                <span className="summary-icon blue">
                  <UsersRound size={23} strokeWidth={1.5} />
                </span>
              </article>
              <article className="summary-card">
                <div>
                  <span className="summary-label">全国の年少人口比率</span>
                  <div className="summary-value">
                    {data.national.childShare!.toFixed(1)}
                    <small>%</small>
                  </div>
                  <span className="summary-period">
                    2020年 · 年齢不詳を除く
                  </span>
                </div>
                <span className="summary-icon olive">
                  <PieChart size={23} strokeWidth={1.5} />
                </span>
              </article>
              <article className="summary-card coverage-card">
                <div>
                  <span className="summary-label">
                    探索できる市区町村・行政区
                  </span>
                  <div className="summary-value">
                    {integer.format(data.metadata.municipalityCount)}
                    <small>地域</small>
                  </div>
                  <button
                    className="summary-period source-link"
                    onClick={() => setSourcesOpen(true)}
                  >
                    収録データと出典 <ArrowUpRight size={12} />
                  </button>
                </div>
                <span className="summary-icon tan">
                  <MapPin size={23} strokeWidth={1.5} />
                </span>
              </article>
            </section>
            <div className="explorer-heading">
              <div>
                <span className="section-dot" />
                <h2>
                  {page === "map" ? "地域を探索する" : "数値から地域を見つける"}
                </h2>
                <span className="explorer-subtitle">
                  {page === "map" ? "LOCAL PERSPECTIVES" : "REGIONAL RANKING"}
                </span>
              </div>
              <div className="explorer-actions">
                <button
                  className="mobile-filter-button"
                  onClick={() => setMobileSettings((v) => !v)}
                >
                  <SlidersHorizontal size={15} />
                  表示設定
                  <ChevronDown size={14} />
                </button>
                {page === "map" && (
                  <button
                    className={`compare-button ${compare ? "is-active" : ""}`}
                    onClick={() => setCompare((v) => !v)}
                    aria-pressed={compare}
                  >
                    <SplitSquareHorizontal size={16} />
                    <span>
                      {compare ? "比較表示を終了" : "2つの指標を比較"}
                    </span>
                    {compare ? <X size={13} /> : <ArrowRight size={14} />}
                  </button>
                )}
              </div>
            </div>
            <div
              className={`workspace ${compare && page === "map" ? "is-comparing" : ""} ${page === "ranking" ? "is-ranking" : ""}`}
            >
              <aside
                className={`controls-panel ${mobileSettings ? "mobile-open" : ""}`}
                aria-label="表示設定"
              >
                <div className="controls-panel-heading">
                  <span>
                    <SlidersHorizontal size={15} />
                    表示設定
                  </span>
                  <button
                    className="icon-button"
                    onClick={() => setMobileSettings((v) => !v)}
                    aria-label="表示設定を閉じる"
                  >
                    <PanelLeftClose size={16} />
                  </button>
                </div>
                <div className="controls-body">
                  <SearchBox data={data} onSelect={selectRegion} />
                  <div className="pref-select">
                    <label htmlFor="prefecture">表示エリア</label>
                    <div className="select-wrap">
                      <MapPin size={15} />
                      <select
                        id="prefecture"
                        value={prefecture}
                        onChange={(e) => changePrefecture(e.target.value)}
                      >
                        <option value="">日本全国</option>
                        {data.prefectures.map((r) => (
                          <option value={r.prefCode} key={r.code}>
                            {r.name}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={14} />
                    </div>
                  </div>
                  <div className="mode-control">
                    <div className="control-label">
                      <span>表示する指標</span>
                      <span className="step-number">01 — 06</span>
                    </div>
                    <div className="mode-options">
                      {modeOptions.map((option) => {
                        const active =
                          option.metric === "age0"
                            ? ["age0", "age5", "age10"].includes(metric)
                            : metric === option.metric;
                        const Icon = option.icon;
                        return (
                          <button
                            key={option.metric}
                            className={active ? "active" : ""}
                            aria-pressed={active}
                            onClick={() => setMetric(option.metric)}
                          >
                            <Icon size={17} strokeWidth={1.6} />
                            <span>{option.label}</span>
                            <i>
                              {active && <Check size={11} strokeWidth={3} />}
                            </i>
                          </button>
                        );
                      })}
                    </div>
                    {["age0", "age5", "age10"].includes(metric) && (
                      <div className="age-tabs" aria-label="年齢階級">
                        {(["age0", "age5", "age10"] as Metric[]).map((m) => (
                          <button
                            key={m}
                            className={metric === m ? "active" : ""}
                            aria-pressed={metric === m}
                            onClick={() => setMetric(m)}
                          >
                            {metrics[m].short}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="metric-period">
                    <Database size={13} />
                    <span>統計期間</span>
                    <b>{metrics[metric].period}</b>
                  </div>
                  <Legend regions={scope} metric={metric} />
                  <div className="reference-box">
                    <span>
                      <BaselineLabel metric={metric} />
                    </span>
                    <b>
                      {formatValue(valueOf(baseline, metric), metric)}
                      <small>{metrics[metric].unit}</small>
                    </b>
                  </div>
                  <p className="metric-description">
                    {metrics[metric].description}
                  </p>
                  <button
                    className="source-detail-link"
                    onClick={() => setSourcesOpen(true)}
                  >
                    <CircleHelp size={14} />
                    指標の定義・出典・欠損値
                    <ArrowUpRight size={13} />
                  </button>
                </div>
              </aside>
              {page === "ranking" ? (
                <RankingTable
                  regions={scope}
                  metric={metric}
                  baseline={baseline}
                  onSelect={selectRegion}
                />
              ) : (
                <>
                  <section className="maps-area" aria-label="人口統計マップ">
                    <div className="map-shared-toolbar">
                      <div>
                        <span className="live-dot" />
                        <b>{scopeName}の市区町村</b>
                        <span className="region-count">
                          {integer.format(scope.length)}地域
                        </span>
                      </div>
                      <div className="map-display-toggles">
                        <button
                          className={showLabels ? "active" : ""}
                          onClick={() => setShowLabels((v) => !v)}
                          aria-pressed={showLabels}
                        >
                          地名
                        </button>
                        <button
                          className={showBackground ? "active" : ""}
                          onClick={() => setShowBackground((v) => !v)}
                          aria-pressed={showBackground}
                        >
                          <Layers2 size={13} />
                          背景地図
                        </button>
                      </div>
                    </div>
                    <div className="map-panels">
                      {(compare ? [metric, secondMetric] : [metric]).map(
                        (m, i) => (
                          <div className="map-panel" key={i}>
                            <div className="map-panel-heading">
                              <span
                                className="panel-letter"
                                style={{
                                  background: metrics[m].colors[0],
                                  color: metrics[m].colors[6],
                                }}
                              >
                                {compare ? (
                                  i === 0 ? (
                                    "A"
                                  ) : (
                                    "B"
                                  )
                                ) : (
                                  <MapIcon size={14} />
                                )}
                              </span>
                              {i === 1 ? (
                                <div className="compare-metric-select">
                                  <select
                                    aria-label="比較する2つ目の指標"
                                    value={secondMetric}
                                    onChange={(e) =>
                                      setSecondMetric(e.target.value as Metric)
                                    }
                                  >
                                    {metricList.map((key) => (
                                      <option key={key} value={key}>
                                        {metrics[key].label}
                                      </option>
                                    ))}
                                  </select>
                                  <ChevronDown size={13} />
                                </div>
                              ) : (
                                <h3>{metrics[m].label}</h3>
                              )}
                              <span className="map-year">
                                {metrics[m].period}
                              </span>
                            </div>
                            <MapView
                              id={i === 0 ? "left" : "right"}
                              geometry={geometry}
                              byCode={byCode}
                              metric={m}
                              selectedCode={selectedCode}
                              prefecture={prefecture}
                              showLabels={showLabels}
                              showBackground={showBackground}
                              focus={focus}
                              position={compare ? position : null}
                              onPosition={setPosition}
                              onSelect={setSelectedCode}
                              onHome={home}
                            />
                            <div className="map-color-key">
                              <span>低い</span>
                              <div>
                                {metrics[m].colors.map((color) => (
                                  <i
                                    key={color}
                                    style={{ background: color }}
                                  />
                                ))}
                              </div>
                              <span>高い</span>
                              <span className="key-missing">
                                <i style={{ background: MISSING_COLOR }} />
                                データなし
                              </span>
                            </div>
                            {compare && (
                              <details className="compare-legend" open>
                                <summary>
                                  凡例と色分け範囲 <ChevronDown size={12} />
                                </summary>
                                <div>
                                  <Legend regions={scope} metric={m} />
                                </div>
                              </details>
                            )}
                          </div>
                        ),
                      )}
                    </div>
                    {selectedCode && !compare && (
                      <div className="map-selected-region">
                        <MapPin size={14} />
                        <span>
                          <b>{detailRegion?.name ?? unknownName}</b>
                          <small>
                            {formatValue(selectedMetricValue, metric)}
                            {selectedMetricValue === null
                              ? " データなし"
                              : metrics[metric].unit}
                          </small>
                        </span>
                        <button
                          onClick={() => {
                            const target =
                              document.getElementById("region-details");
                            target?.scrollIntoView({
                              behavior: window.matchMedia(
                                "(prefers-reduced-motion: reduce)",
                              ).matches
                                ? "instant"
                                : "smooth",
                              block: "center",
                            });
                            target?.focus({ preventScroll: true });
                          }}
                        >
                          地域の詳細 <ArrowRight size={13} />
                        </button>
                      </div>
                    )}
                    {compare && (
                      <div className="compare-info">
                        <SplitSquareHorizontal size={16} />
                        <span>
                          2つの地図は移動・ズームが連動します。
                          {selectedCode && detailRegion ? (
                            <b>
                              {detailRegion.name}
                              {detailRegion.level === "1" ? "（全体）" : ""}：
                              {metrics[metric].short}{" "}
                              {formatValue(selectedMetricValue, metric)}
                              {metrics[metric].unit} /{" "}
                              {metrics[secondMetric].short}{" "}
                              {formatValue(
                                valueOf(detailRegion, secondMetric),
                                secondMetric,
                              )}
                              {metrics[secondMetric].unit}
                            </b>
                          ) : unknownName ? (
                            <b>{unknownName}：対応する統計データなし</b>
                          ) : (
                            "同じ地域を、異なる指標で見比べてみましょう。"
                          )}
                          {detailRegion?.level === "1" && (
                            <small className="compare-aggregate-note">
                              地図の色は行政区別、選択した数値は市・区部全体の公表値です。
                            </small>
                          )}
                        </span>
                      </div>
                    )}
                    <div className="map-bottom-note">
                      <span>
                        <span className="note-dot" />
                        出生率 {metrics.tfr.period} / 人口 2020年
                      </span>
                      <button onClick={() => setSourcesOpen(true)}>
                        出典と集計方法 <ArrowUpRight size={12} />
                      </button>
                    </div>
                    {!compare && (
                      <div className="map-insight">
                        <span className="insight-icon">
                          <MousePointer2 size={17} />
                        </span>
                        <div>
                          <b>数の多さと、割合の高さ。その違いを見つけよう。</b>
                          <p>
                            「子ども人口」と「年少人口比率」を切り替えると、都市と郊外の違った一面が見えてきます。
                          </p>
                        </div>
                        <button
                          onClick={() => {
                            setCompare(true);
                            setMetric("children");
                            setSecondMetric("childShare");
                          }}
                          aria-label="子ども人口と年少人口比率を比較"
                        >
                          <ArrowUpRight size={18} />
                        </button>
                      </div>
                    )}
                  </section>
                  <DetailPanel
                    region={detailRegion ?? data.national}
                    selected={!!selectedCode}
                    unknownName={unknownName}
                    metric={metric}
                    baseline={baseline}
                    scope={scope}
                    onClear={() => setSelectedCode(null)}
                    onSelect={selectRegion}
                    onRanking={() => setPage("ranking")}
                    onSources={() => setSourcesOpen(true)}
                    onZoom={() => {
                      if (detailRegion) selectRegion(detailRegion);
                    }}
                  />
                </>
              )}
            </div>
            <div className="bottom-guidance">
              <span>
                <Database size={13} />
                データから地域の姿を知る、小さなきっかけに。
              </span>
              <span>
                出生率は子育て環境の良し悪しを直接示す指標ではありません。
              </span>
            </div>
          </>
        )}
      </main>
      <footer className="site-footer">
        <span>
          <span className="footer-brand">こどもアトラス</span>
          日本の未来を、地図から。
        </span>
        <span>
          DATA: MHLW / e-Stat / MLIT
          <button onClick={() => setSourcesOpen(true)}>
            出典・利用上の注意
            <ArrowUpRight size={12} />
          </button>
        </span>
      </footer>
      {sourcesOpen && data && (
        <DataDialog data={data} onClose={() => setSourcesOpen(false)} />
      )}
    </>
  );
}
