import type { ReactNode } from "react";
import { formatValue, metrics, MISSING_COLOR, rangeLabels } from "../metrics";
import type { Metric } from "../types";
import { binIndex, breakLabel, guide, isCount, rampPosition } from "../ui";

/**
 * The on-map legend: indicator name, statistics period and the seven fixed classes,
 * with the national aggregate marked on the ramp (rates only) and the selected
 * region's class outlined.
 */
export default function MapKey({
  metric,
  badge,
  title,
  nationalValue,
  selectedValue,
  selectedName,
}: {
  metric: Metric;
  badge?: ReactNode;
  title?: ReactNode;
  nationalValue: number | null;
  selectedValue: number | null;
  selectedName?: string;
}) {
  const info = metrics[metric];
  const words = guide[metric];
  const national = isCount(metric) ? null : rampPosition(nationalValue, metric);
  const selectedBin = selectedName ? binIndex(selectedValue, metric) : null;
  const bins = info.colors.length;
  return (
    <div className="map-key">
      <div className="map-panel-heading">
        {badge}
        <div className="map-key-title">
          {title ?? <h3>{info.label}</h3>}
          <span className="map-year">{info.period}</span>
        </div>
      </div>
      <div className="map-key-scale" aria-hidden="true">
        <span className="ramp-end">{words.low}</span>
        <div className="ramp">
          {national !== null && (
            <span
              className="ramp-national"
              style={{ left: `${national * 100}%` }}
            >
              <span>全国 {formatValue(nationalValue, metric)}</span>
            </span>
          )}
          <div className="ramp-swatches">
            {info.colors.map((color, i) => (
              <i
                key={color}
                className={selectedBin === i ? "is-selected" : ""}
                style={{ background: color }}
              />
            ))}
          </div>
          <div className="ramp-ticks">
            {info.breaks.map((value, i) => (
              <span key={value} style={{ left: `${((i + 1) / bins) * 100}%` }}>
                {breakLabel(value, metric)}
              </span>
            ))}
          </div>
        </div>
        <span className="ramp-end">{words.high}</span>
      </div>
      <div className="map-key-foot">
        <span className="key-missing">
          <i style={{ background: MISSING_COLOR }} />
          データなし・非公表
        </span>
        {info.unit && <span className="key-unit">単位：{info.unit}</span>}
      </div>
      <p className="sr-only">
        色分け：{rangeLabels(metric).join("、")}
        {info.unit && `（${info.unit}）`}。灰色はデータなし・非公表。
        {national !== null &&
          `全国集計値は${formatValue(nationalValue, metric)}${info.unit}。`}
        {selectedName &&
          selectedBin !== null &&
          `${selectedName}は「${rangeLabels(metric)[selectedBin]}」の区分。`}
      </p>
    </div>
  );
}
