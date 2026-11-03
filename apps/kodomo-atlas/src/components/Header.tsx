import { BookOpen, ChartColumn, Map as MapIcon } from "lucide-react";
import { Logo } from "./common";

export default function Header({
  page,
  onHome,
  onPage,
  onSources,
}: {
  page: "map" | "ranking";
  onHome: () => void;
  onPage: (page: "map" | "ranking") => void;
  onSources: () => void;
}) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button
          className="brand"
          onClick={onHome}
          aria-label="こどもアトラス ホーム（全国表示に戻る）"
        >
          <Logo />
        </button>
        <p className="topbar-lead">
          出生率・子ども・世帯構造を、市区町村ごとの地図で
        </p>
        <nav className="main-nav" aria-label="メインナビゲーション">
          <button
            className={page === "map" ? "active" : ""}
            aria-current={page === "map" ? "page" : undefined}
            onClick={() => onPage("map")}
          >
            <MapIcon size={17} aria-hidden="true" />
            <span>地図で見る</span>
          </button>
          <button
            className={page === "ranking" ? "active" : ""}
            aria-current={page === "ranking" ? "page" : undefined}
            onClick={() => onPage("ranking")}
          >
            <ChartColumn size={17} aria-hidden="true" />
            <span>ランキング</span>
          </button>
          <button onClick={onSources} aria-label="データについて">
            <BookOpen size={17} aria-hidden="true" />
            <span>データについて</span>
          </button>
        </nav>
      </div>
    </header>
  );
}
