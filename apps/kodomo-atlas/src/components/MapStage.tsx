import { ArrowDown, ChevronDown, SplitSquareHorizontal, X } from "lucide-react";
import MapView from "../MapView";
import { difference, formatValue, metricList, metrics, valueOf } from "../metrics";
import type {
  FocusRequest,
  Geography,
  MapPosition,
  Metric,
  Region,
} from "../types";
import { categories, categoryOf, isCount } from "../ui";
import MapKey from "./MapKey";
import { BaselineLabel } from "./common";

interface Props {
  geometry: Geography;
  byCode: Map<string, Region>;
  metric: Metric;
  secondMetric: Metric;
  onSecondMetric: (metric: Metric) => void;
  compare: boolean;
  onExitCompare: () => void;
  selectedCode: string | null;
  selectedRegion?: Region;
  unknownName?: string;
  baseline: Region;
  prefecture: string;
  showLabels: boolean;
  showBackground: boolean;
  focus: FocusRequest | null;
  position: MapPosition | null;
  onPosition: (position: MapPosition) => void;
  onSelect: (code: string) => void;
  onClear: () => void;
  onHome: () => void;
  onShowDetails: () => void;
}

function SelectionCard({
  region,
  name,
  metric,
  baseline,
  live,
  onClear,
  onShowDetails,
}: {
  region?: Region;
  name: string;
  metric: Metric;
  baseline: Region;
  live: boolean;
  onClear: () => void;
  onShowDetails: () => void;
}) {
  const info = metrics[metric];
  const value = valueOf(region, metric);
  const aggregate = region?.level === "1";
  const delta =
    region && value !== null && (!aggregate || !isCount(metric))
      ? difference(region, baseline, metric)
      : null;
  return (
    <div
      className="map-selection-info"
      role={live ? "status" : undefined}
      aria-live={live ? "polite" : undefined}
    >
      <div className="selection-head">
        <div className="selected-region-name">
          {name}
          {aggregate && <small>市・区部全体</small>}
          {region && <span className="selected-pref">{region.prefecture}</span>}
        </div>
        <button
          className="icon-button selection-close"
          aria-label="選択を解除"
          title="選択を解除"
          onClick={onClear}
        >
          <X size={16} />
        </button>
      </div>
      <strong>
        {formatValue(value, metric)}
        <small>{value === null ? "データなし・非公表" : info.unit}</small>
      </strong>
      {delta && (
        <p className="selection-diff">
          <BaselineLabel metric={metric} />{" "}
          {formatValue(valueOf(baseline, metric), metric)}
          {info.unit} より <b>{delta}</b>
        </p>
      )}
      <p className="selection-metric">
        {info.label} · {info.period}
      </p>
      {aggregate && <p className="selected-unit-note">地図の色は行政区別</p>}
      <button className="selection-more" onClick={onShowDetails}>
        地域の詳細 <ArrowDown size={14} />
      </button>
    </div>
  );
}

export default function MapStage(props: Props) {
  const maps = props.compare
    ? [props.metric, props.secondMetric]
    : [props.metric];
  const name = props.selectedRegion?.name ?? props.unknownName;
  return (
    <section className="maps-area" aria-label="人口統計マップ">
      {props.compare && (
        <div className="compare-bar">
          <SplitSquareHorizontal size={18} aria-hidden="true" />
          <p>
            <b>2つの指標を比較中</b>
            <span>地図の移動・ズームは連動します</span>
          </p>
          <button className="compare-exit" onClick={props.onExitCompare}>
            比較を終了
            <X size={15} />
          </button>
        </div>
      )}
      <div className="map-panels">
        {maps.map((m, i) => (
          <div className="map-panel" key={i}>
            <MapView
              id={i === 0 ? "left" : "right"}
              geometry={props.geometry}
              byCode={props.byCode}
              metric={m}
              selectedCode={props.selectedCode}
              prefecture={props.prefecture}
              showLabels={props.showLabels}
              showBackground={props.showBackground}
              focus={props.focus}
              position={props.compare ? props.position : null}
              onPosition={props.onPosition}
              onSelect={props.onSelect}
              onHome={props.onHome}
            >
              <MapKey
                metric={m}
                nationalValue={valueOf(props.baseline, m)}
                selectedValue={valueOf(props.selectedRegion, m)}
                selectedName={props.selectedRegion?.name}
                badge={
                  props.compare && (
                    <span
                      className="panel-letter"
                      style={{
                        background: metrics[m].colors[1],
                        color: metrics[m].colors[6],
                      }}
                    >
                      {i === 0 ? "A" : "B"}
                    </span>
                  )
                }
                title={
                  i === 1 ? (
                    <div className="compare-metric-select">
                      <select
                        aria-label="比較する2つ目の指標"
                        value={props.secondMetric}
                        onChange={(e) =>
                          props.onSecondMetric(e.target.value as Metric)
                        }
                      >
                        {categories.map((category) => (
                          <optgroup key={category.id} label={category.label}>
                            {metricList
                              .filter((key) => categoryOf(key) === category.id)
                              .map((key) => (
                                <option key={key} value={key}>
                                  {metrics[key].label}
                                </option>
                              ))}
                          </optgroup>
                        ))}
                      </select>
                      <ChevronDown size={15} aria-hidden="true" />
                    </div>
                  ) : undefined
                }
              />
              {name && (
                <SelectionCard
                  region={props.selectedRegion}
                  name={name}
                  metric={m}
                  baseline={props.baseline}
                  live={i === 0}
                  onClear={props.onClear}
                  onShowDetails={props.onShowDetails}
                />
              )}
            </MapView>
          </div>
        ))}
      </div>
    </section>
  );
}
