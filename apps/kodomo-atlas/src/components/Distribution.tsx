import { integer, metrics, MISSING_COLOR, rangeLabels, valueOf } from "../metrics";
import type { Metric, Region } from "../types";

export function getBinCounts(regions: Region[], metric: Metric): number[] {
  const bins = Array(metrics[metric].colors.length).fill(0) as number[];
  regions.forEach((region) => {
    const v = valueOf(region, metric);
    if (v === null) return;
    const index = metrics[metric].breaks.findIndex((limit) => v < limit);
    bins[index < 0 ? bins.length - 1 : index]++;
  });
  return bins;
}

/** Histogram of the fixed classes; `highlight` marks the selected region's class. */
export function Distribution({
  regions,
  metric,
  highlight = null,
}: {
  regions: Region[];
  metric: Metric;
  highlight?: number | null;
}) {
  const counts = getBinCounts(regions, metric);
  const max = Math.max(...counts, 1);
  const labels = rangeLabels(metric);
  return (
    <div
      className="distribution"
      role="img"
      aria-label={`地域数の分布。${labels
        .map((label, i) => `${label}が${counts[i]}地域`)
        .join("、")}${highlight !== null ? `。選択した地域は「${labels[highlight]}」の区分です` : ""}`}
    >
      <div className="histogram">
        {counts.map((count, i) => (
          <div
            key={i}
            className={`histogram-column ${highlight === i ? "is-highlight" : ""}`}
          >
            <span
              style={{
                height: `${Math.max((count / max) * 100, count ? 3 : 0)}%`,
                background: metrics[metric].colors[i],
              }}
              title={`${labels[i]}：${count}地域`}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Full legend with region counts per fixed class and the missing count. */
export function LegendTable({
  regions,
  metric,
  highlight = null,
}: {
  regions: Region[];
  metric: Metric;
  highlight?: number | null;
}) {
  const counts = getBinCounts(regions, metric);
  const missing = regions.filter((r) => valueOf(r, metric) === null).length;
  return (
    <div className="legend">
      <Distribution regions={regions} metric={metric} highlight={highlight} />
      <div className="legend-rows">
        {rangeLabels(metric).map((label, i) => (
          <div
            className={`legend-row ${highlight === i ? "is-highlight" : ""}`}
            key={i}
          >
            <i style={{ background: metrics[metric].colors[i] }} />
            <span>
              {label}
              {metrics[metric].unit && i === 0 && (
                <small> {metrics[metric].unit}</small>
              )}
            </span>
            <b>{integer.format(counts[i])}</b>
          </div>
        ))}
        <div className="legend-row missing">
          <i style={{ background: MISSING_COLOR }} />
          <span>欠損・非公表（0とは別）</span>
          <b>{missing}</b>
        </div>
      </div>
      <p className="legend-note">
        全国共通の固定区分です。極端な値や都道府県の絞り込みで区分は変わりません。
      </p>
    </div>
  );
}
