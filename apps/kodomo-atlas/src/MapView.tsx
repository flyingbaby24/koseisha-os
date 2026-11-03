import { useEffect, useRef, useState, type ReactNode } from "react";
import L from "leaflet";
import { Home, Minus, Plus, LocateFixed } from "lucide-react";
import { fitPadding } from "./mapPadding";
import { colorOf, formatValue, metrics, valueOf } from "./metrics";
import type {
  FocusRequest,
  Geography,
  GeoProperties,
  MapPosition,
  Metric,
  Region,
} from "./types";

export const JAPAN_BOUNDS: [[number, number], [number, number]] = [
  [24, 122.2],
  [45.8, 146.5],
];
const cityLabels: [string, number, number][] = [
  ["札幌", 43.062, 141.354],
  ["仙台", 38.268, 140.869],
  ["東京", 35.681, 139.767],
  ["名古屋", 35.181, 136.906],
  ["大阪", 34.694, 135.502],
  ["広島", 34.385, 132.455],
  ["福岡", 33.59, 130.402],
  ["那覇", 26.212, 127.681],
];
const escape = (text: string) =>
  text.replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );

interface Props {
  id: string;
  geometry: Geography;
  byCode: Map<string, Region>;
  metric: Metric;
  selectedCode: string | null;
  prefecture: string;
  showLabels: boolean;
  showBackground: boolean;
  focus: FocusRequest | null;
  position: MapPosition | null;
  onPosition: (position: MapPosition) => void;
  onSelect: (code: string) => void;
  onHome: () => void;
  /** Legend, title and selection overlays drawn over the map. */
  children?: ReactNode;
}

export default function MapView(props: Props) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const polygons = useRef<L.GeoJSON | null>(null);
  const labels = useRef<L.LayerGroup | null>(null);
  const basemap = useRef<L.TileLayer | null>(null);
  const selection = useRef<L.CircleMarker | null>(null);
  const current = useRef(props);
  current.current = props;
  const [zoom, setZoom] = useState(4);
  const [tileError, setTileError] = useState(false);

  useEffect(() => {
    if (!container.current) return;
    const instance = L.map(container.current, {
      zoomControl: false,
      // SVG avoids stale Canvas redraw callbacks when React removes a comparison map.
      preferCanvas: false,
      minZoom: 3,
      maxZoom: 13,
      zoomSnap: 0.25,
      wheelPxPerZoomLevel: 100,
      maxBounds: [
        [15, 112],
        [53, 166],
      ],
      maxBoundsViscosity: 0.8,
      attributionControl: false,
    });
    map.current = instance;
    instance.createPane("labels");
    instance.getPane("labels")!.style.pointerEvents = "none";
    instance.getPane("labels")!.style.zIndex = "450";
    const initial = current.current.position;
    if (initial)
      instance.setView([initial.lat, initial.lng], initial.zoom, {
        animate: false,
      });
    else
      instance.fitBounds(JAPAN_BOUNDS, {
        ...fitPadding(container.current, 12),
        animate: false,
      });
    L.control
      .scale({ position: "bottomright", imperial: false, maxWidth: 90 })
      .addTo(instance);
    L.control
      .attribution({
        position: "bottomright",
        prefix:
          '<a href="https://leafletjs.com" target="_blank" rel="noreferrer">Leaflet</a>',
      })
      .addAttribution("国土数値情報（加工）")
      .addTo(instance);

    const labelGroup = L.layerGroup();
    cityLabels.forEach(([name, lat, lng]) => {
      L.marker([lat, lng], {
        pane: "labels",
        interactive: false,
        icon: L.divIcon({
          className: "city-label",
          html: `<i></i><span>${name}</span>`,
          iconSize: [70, 20],
          iconAnchor: [4, 10],
        }),
      }).addTo(labelGroup);
    });
    [
      ["日本海", 39.1, 134.1],
      ["太平洋", 32, 142.7],
      ["東シナ海", 28.9, 125.2],
    ].forEach(([name, lat, lng]) => {
      L.marker([Number(lat), Number(lng)], {
        pane: "labels",
        interactive: false,
        icon: L.divIcon({
          className: "sea-label",
          html: String(name),
          iconSize: [110, 24],
        }),
      }).addTo(labelGroup);
    });
    labels.current = labelGroup;
    if (current.current.showLabels) labelGroup.addTo(instance);

    instance.on("moveend", () => {
      const center = instance.getCenter();
      const nextZoom = instance.getZoom();
      setZoom(nextZoom);
      current.current.onPosition({
        lat: center.lat,
        lng: center.lng,
        zoom: nextZoom,
        source: current.current.id,
      });
    });
    setZoom(instance.getZoom());
    const observer = new ResizeObserver(() =>
      instance.invalidateSize({ pan: false }),
    );
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      instance.remove();
      map.current = null;
      labels.current = null;
      basemap.current = null;
      polygons.current = null;
      selection.current = null;
    };
  }, []);

  function style(
    feature?: GeoJSON.Feature<GeoJSON.Geometry, GeoProperties>,
  ): L.PathOptions {
    const prop = feature?.properties;
    const state = current.current;
    const record = state.byCode.get(prop?.code ?? "");
    const inScope =
      !state.prefecture || prop?.code.startsWith(state.prefecture);
    const selectedRegion = state.byCode.get(state.selectedCode ?? "");
    const selected =
      prop?.code === state.selectedCode ||
      !!selectedRegion?.memberCodes?.includes(prop?.code ?? "");
    return {
      fillColor: inScope
        ? colorOf(valueOf(record, state.metric), state.metric)
        : "#dfe4de",
      fillOpacity: inScope ? 0.94 : 0.7,
      color: selected ? "#b85f25" : "#ffffff",
      weight: selected ? (selectedRegion?.memberCodes ? 1.8 : 3.4) : 0.45,
      opacity: selected ? 1 : 0.85,
    };
  }

  useEffect(() => {
    if (!map.current) return;
    const layer = L.geoJSON(props.geometry, {
      style,
      onEachFeature: (feature, polygon) => {
        polygon.on("mouseover", () => {
          const state = current.current,
            code = feature.properties.code;
          if (state.prefecture && !code.startsWith(state.prefecture)) return;
          const region = state.byCode.get(code),
            value = valueOf(region, state.metric);
          const title = region?.name ?? feature.properties.name;
          const content = `<div class="tooltip-pref">${escape(feature.properties.prefecture)}</div><strong>${escape(title)}</strong><div class="tooltip-value">${formatValue(value, state.metric)} <small>${value === null ? "データなし・非公表" : metrics[state.metric].unit}</small></div><div class="tooltip-period">${metrics[state.metric].label} · ${metrics[state.metric].period}</div><div class="tooltip-action">クリックで詳細</div>`;
          if (!polygon.getTooltip())
            polygon.bindTooltip(content, {
              sticky: true,
              className: "data-tooltip",
              direction: "top",
              offset: [0, -12],
            });
          else polygon.setTooltipContent(content);
          polygon.openTooltip();
          if (polygon instanceof L.Path) {
            const base = style(feature);
            polygon.setStyle({
              weight: Math.max(base.weight ?? 0, 2),
              color: base.weight! > 1 ? base.color : "#1d3a2c",
              fillOpacity: 1,
            });
          }
        });
        polygon.on("mouseout", () => {
          if (polygon instanceof L.Path) polygon.setStyle(style(feature));
        });
        polygon.on("click", () => {
          const state = current.current,
            code = feature.properties.code;
          if (state.prefecture && !code.startsWith(state.prefecture)) return;
          state.onSelect(code);
        });
      },
    }).addTo(map.current);
    polygons.current = layer;
    return () => {
      layer.remove();
    };
  }, [props.geometry]);

  useEffect(() => {
    polygons.current?.setStyle(style);
    polygons.current?.eachLayer((layer) => layer.closeTooltip());
    const selectedRegion = props.byCode.get(props.selectedCode ?? "");
    polygons.current?.eachLayer((layer) => {
      if (!(layer instanceof L.Path)) return;
      const code = (
        layer as L.Path & {
          feature: GeoJSON.Feature<GeoJSON.Geometry, GeoProperties>;
        }
      ).feature.properties.code;
      if (
        code === props.selectedCode ||
        selectedRegion?.memberCodes?.includes(code)
      )
        layer.bringToFront();
    });
    if (selection.current) {
      selection.current.remove();
      selection.current = null;
    }
    const region = props.byCode.get(props.selectedCode ?? "");
    if (region?.center && map.current) {
      selection.current = L.circleMarker(region.center, {
        radius: 5,
        color: "#fff",
        weight: 2,
        fillColor: "#c87a40",
        fillOpacity: 1,
        interactive: false,
      }).addTo(map.current);
    }
  }, [props.metric, props.selectedCode, props.prefecture, props.byCode]);

  useEffect(() => {
    if (!map.current || !labels.current) return;
    if (props.showLabels) labels.current.addTo(map.current);
    else labels.current.remove();
  }, [props.showLabels]);

  useEffect(() => {
    if (!map.current) return;
    if (props.showBackground) {
      setTileError(false);
      const tile = L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
        {
          subdomains: "abcd",
          maxZoom: 19,
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions" target="_blank" rel="noreferrer">CARTO</a>',
        },
      ).addTo(map.current);
      tile.on("tileerror", () => setTileError(true));
      basemap.current = tile;
      return () => {
        tile.remove();
        basemap.current = null;
      };
    }
  }, [props.showBackground]);

  useEffect(() => {
    if (props.focus && map.current)
      map.current.fitBounds(props.focus.bounds, {
        ...fitPadding(container.current, 32),
        maxZoom: 10,
        animate: false,
      });
  }, [props.focus]);

  useEffect(() => {
    const position = props.position,
      instance = map.current;
    if (!position || !instance || position.source === props.id) return;
    const center = instance.getCenter();
    if (
      Math.abs(center.lat - position.lat) > 0.000001 ||
      Math.abs(center.lng - position.lng) > 0.000001 ||
      instance.getZoom() !== position.zoom
    ) {
      instance.setView([position.lat, position.lng], position.zoom, {
        animate: false,
      });
    }
  }, [props.position, props.id]);

  return (
    <div className="map-canvas-wrap">
      <div
        ref={container}
        className="map-canvas"
        role="region"
        aria-label={`${metrics[props.metric].label}（${metrics[props.metric].period}）の市区町村地図。矢印キーで移動、＋−キーで拡大縮小。検索とランキングからも地域を選択できます。`}
      />
      <div className="map-zoom-controls" aria-label="地図操作">
        <button
          onClick={() => map.current?.zoomIn()}
          disabled={zoom >= 13}
          title="拡大"
          aria-label="地図を拡大"
        >
          <Plus size={20} />
        </button>
        <button
          onClick={() => map.current?.zoomOut()}
          disabled={zoom <= 3}
          title="縮小"
          aria-label="地図を縮小"
        >
          <Minus size={20} />
        </button>
        <button
          onClick={props.onHome}
          title="全国を表示"
          aria-label="全国を表示"
        >
          <Home size={18} />
        </button>
        {props.selectedCode && (
          <button
            onClick={() => {
              const region = props.byCode.get(props.selectedCode!);
              if (region?.bounds)
                map.current?.fitBounds(region.bounds, {
                  ...fitPadding(container.current, 45),
                  maxZoom: 11,
                });
            }}
            title="選択した地域へ"
            aria-label="選択した地域にズーム"
          >
            <LocateFixed size={18} />
          </button>
        )}
      </div>
      {props.children}
      {!props.selectedCode && (
        <div className="map-hint" aria-hidden="true">
          <span className="hint-pointer">地域にふれると数値、クリックで詳細</span>
          <span className="hint-touch">地域をタップで数値と詳細</span>
        </div>
      )}
      {tileError && props.showBackground && (
        <div className="tile-error">
          背景地図を取得できません。行政区域は引き続き探索できます。
        </div>
      )}
    </div>
  );
}
