import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowUpRight, Database } from "lucide-react";
import { JAPAN_BOUNDS } from "./MapView";
import { comparisonReference, regionIndex } from "./regions";
import { householdReference, joinHouseholds } from "./households";
import type {
  Bounds,
  FocusRequest,
  Geography,
  HouseholdData,
  MapPosition,
  Metric,
  Region,
  Statistics,
} from "./types";
import { prefersReducedMotion, unionBounds } from "./ui";
import { Logo } from "./components/common";
import Header from "./components/Header";
import ControlPanel from "./components/ControlPanel";
import MapStage from "./components/MapStage";
import DetailPanel from "./components/DetailPanel";
import RankingTable from "./components/RankingTable";
import DataDialog from "./components/DataDialog";

const PHONE = "(max-width: 760px)";

export default function App() {
  const [data, setData] = useState<Statistics | null>(null);
  const [geometry, setGeometry] = useState<Geography | null>(null);
  const [householdMeta, setHouseholdMeta] = useState<
    HouseholdData["metadata"] | null
  >(null);
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
  const nextFocus = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await Promise.all(
          [
            "data/statistics.json",
            "data/municipalities.geojson",
            "data/households.json",
          ].map((url) =>
            fetch(`${import.meta.env.BASE_URL}${url}`, {
              signal: controller.signal,
            }),
          ),
        );
        if (response.some((r) => !r.ok))
          throw new Error(
            "公開統計データを読み込めませんでした。READMEのデータ取得手順をご確認ください。",
          );
        const [statistics, geography, households] = await Promise.all(
          response.map((r) => r.json()),
        );
        // The household layer is joined by code; statistics.json itself is unchanged.
        setData(joinHouseholds(statistics, households));
        setHouseholdMeta(households.metadata);
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
  const baseline = useMemo(
    () =>
      data
        ? { ...comparisonReference(data), households: householdReference(data) }
        : null,
    [data],
  );
  const selectedRegion = selectedCode ? byCode.get(selectedCode) : undefined;
  const detailRegion = selectedCode
    ? selectedRegion
    : (data?.prefectures.find((r) => r.prefCode === prefecture) ??
      data?.national);
  const unknownName =
    selectedCode && !selectedRegion
      ? geometry?.features.find((f) => f.properties.code === selectedCode)
          ?.properties.name
      : undefined;
  const comparing = compare && page === "map";

  // Escape clears the selected region (outside text fields and the dialog).
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape" || sourcesOpen || !selectedCode) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, select, textarea, dialog")) return;
      setSelectedCode(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [sourcesOpen, selectedCode]);

  // On phones the comparison starts below the maps; bring both maps into view.
  const wasComparing = useRef(false);
  useEffect(() => {
    if (comparing && !wasComparing.current && window.matchMedia(PHONE).matches)
      document
        .querySelector(".maps-area")
        ?.scrollIntoView({ block: "start", behavior: prefersReducedMotion() ? "instant" : "smooth" });
    wasComparing.current = comparing;
  }, [comparing]);

  function focusBounds(bounds: Bounds) {
    setFocus({ bounds, key: ++nextFocus.current });
  }
  function changePrefecture(code: string) {
    setPrefecture(code);
    setSelectedCode(null);
    focusBounds(
      code
        ? unionBounds(
            data!.municipalities.filter((r) => r.prefCode === code),
            JAPAN_BOUNDS,
          )
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
        JAPAN_BOUNDS,
      );
    focusBounds(bounds);
    setPage("map");
  }
  function home() {
    setPrefecture("");
    setSelectedCode(null);
    focusBounds(JAPAN_BOUNDS);
  }
  function chooseMetric(next: Metric) {
    // Keep the two comparison maps on different indicators.
    if (compare && next === secondMetric) setSecondMetric(metric);
    setMetric(next);
  }
  function chooseSecondMetric(next: Metric) {
    if (next === metric) setMetric(secondMetric);
    setSecondMetric(next);
  }
  function startCompare(left: Metric, right: Metric) {
    if (comparing && metric === left && secondMetric === right) {
      setCompare(false);
      return;
    }
    setMetric(left);
    setSecondMetric(right);
    setCompare(true);
    setPage("map");
  }
  function toggleCompare() {
    if (comparing) {
      setCompare(false);
      return;
    }
    if (secondMetric === metric)
      setSecondMetric(metric === "childShare" ? "tfr" : "childShare");
    setCompare(true);
    setPage("map");
  }
  function showDetails() {
    const target = document.getElementById("region-details");
    target?.scrollIntoView({
      behavior: prefersReducedMotion() ? "instant" : "smooth",
      block: "start",
    });
    target?.focus({ preventScroll: true });
  }

  return (
    <>
      <a className="skip-link" href="#main">
        本文へスキップ
      </a>
      <Header
        page={page}
        onHome={() => {
          if (data) home();
          setPage("map");
        }}
        onPage={setPage}
        onSources={() => setSourcesOpen(true)}
      />
      <main id="main" className="page-shell" tabIndex={-1}>
        {error ? (
          <section className="load-error" role="alert">
            <Database size={28} />
            <h1>データを読み込めませんでした</h1>
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
            <h1>日本の地域データをひらいています</h1>
            <p>全国の公開統計と市区町村の境界を読み込み中…</p>
          </section>
        ) : (
          <div
            className={`workspace ${comparing ? "is-comparing" : ""} ${page === "ranking" ? "is-ranking" : ""} ${selectedCode ? "has-selection" : ""}`}
          >
            <ControlPanel
              data={data}
              metric={metric}
              onMetric={chooseMetric}
              secondMetric={secondMetric}
              compare={compare}
              onCompare={startCompare}
              onToggleCompare={toggleCompare}
              prefecture={prefecture}
              onPrefecture={changePrefecture}
              scopeCount={scope.length}
              onSelect={selectRegion}
              showLabels={showLabels}
              onShowLabels={() => setShowLabels((v) => !v)}
              showBackground={showBackground}
              onShowBackground={() => setShowBackground((v) => !v)}
              onSources={() => setSourcesOpen(true)}
              page={page}
            />
            {page === "ranking" ? (
              <div className="ranking-area">
                <RankingTable
                  regions={scope}
                  metric={metric}
                  baseline={baseline}
                  scopeName={scopeName}
                  onSelect={selectRegion}
                />
              </div>
            ) : (
              <>
                <MapStage
                  geometry={geometry}
                  byCode={byCode}
                  metric={metric}
                  secondMetric={secondMetric}
                  onSecondMetric={chooseSecondMetric}
                  compare={compare}
                  onExitCompare={() => setCompare(false)}
                  selectedCode={selectedCode}
                  selectedRegion={selectedRegion}
                  unknownName={unknownName}
                  baseline={baseline}
                  prefecture={prefecture}
                  showLabels={showLabels}
                  showBackground={showBackground}
                  focus={focus}
                  position={position}
                  onPosition={setPosition}
                  onSelect={setSelectedCode}
                  onClear={() => setSelectedCode(null)}
                  onHome={home}
                  onShowDetails={showDetails}
                />
                <DetailPanel
                  region={detailRegion ?? data.national}
                  selected={!!selectedCode}
                  unknownName={unknownName}
                  metric={metric}
                  baseline={baseline}
                  scope={scope}
                  units={data.municipalities}
                  scopeName={scopeName}
                  onClear={() => setSelectedCode(null)}
                  onSelect={selectRegion}
                  onRanking={() => setPage("ranking")}
                  onSources={() => setSourcesOpen(true)}
                  onZoom={() => {
                    if (selectedRegion) selectRegion(selectedRegion);
                  }}
                  onMetric={chooseMetric}
                />
              </>
            )}
          </div>
        )}
      </main>
      <footer className="site-footer">
        <span>
          <span className="footer-brand">こどもアトラス</span>
          日本の未来を、地図から。
        </span>
        <span className="footer-note">
          出生率は子育て環境の良し悪しを直接示す指標ではありません。
        </span>
        <span>
          DATA: MHLW / e-Stat / MLIT
          <button onClick={() => setSourcesOpen(true)}>
            出典・利用上の注意
            <ArrowUpRight size={13} />
          </button>
        </span>
      </footer>
      {sourcesOpen && data && (
        <DataDialog
          data={data}
          households={householdMeta}
          onClose={() => setSourcesOpen(false)}
        />
      )}
    </>
  );
}
