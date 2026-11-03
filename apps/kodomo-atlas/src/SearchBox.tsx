import { useId, useMemo, useState } from "react";
import { ArrowUpLeft, MapPin, Search, X } from "lucide-react";
import type { Region, Statistics } from "./types";

export default function SearchBox({
  data,
  onSelect,
}: {
  data: Statistics;
  onSelect: (region: Region) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const id = useId();
  const results = useMemo(() => {
    const q = query.trim().replace(/[ 　]/g, "").toLowerCase();
    if (!q) return [];
    return [...data.prefectures, ...data.cities, ...data.municipalities]
      .filter((r) => `${r.prefecture}${r.name}${r.code}`.includes(q))
      .sort(
        (a, b) =>
          Number(b.name === q || b.code === q) -
          Number(a.name === q || a.code === q),
      )
      .slice(0, 9);
  }, [data, query]);
  function choose(region: Region) {
    onSelect(region);
    setQuery("");
    setOpen(false);
    setActive(0);
  }
  return (
    <div
      className="search-box"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <Search size={17} aria-hidden="true" />
      <input
        aria-label="都道府県・市区町村を検索"
        placeholder="都道府県・市区町村を検索"
        value={query}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open && !!query.trim()}
        aria-controls={id}
        aria-activedescendant={
          open && results[active] ? `${id}-${active}` : undefined
        }
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setOpen(true);
            setActive((v) => Math.min(v + 1, results.length - 1));
          }
          if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((v) => Math.max(0, v - 1));
          }
          if (e.key === "Enter" && open && results[active]) {
            e.preventDefault();
            choose(results[active]);
          }
        }}
      />
      {query && (
        <button
          className="search-clear"
          aria-label="検索をクリア"
          onClick={() => setQuery("")}
        >
          <X size={14} />
        </button>
      )}
      {open && !!query.trim() && (
        <div
          id={id}
          className="search-results"
          role="listbox"
          aria-label="地域の検索結果"
        >
          {results.map((region, i) => (
            <button
              key={region.code}
              id={`${id}-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? "is-active" : ""}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => choose(region)}
            >
              <MapPin size={15} />
              <span>
                <strong>{region.name}</strong>
                <small>
                  {region.level === "a"
                    ? "都道府県"
                    : `${region.prefecture} · ${region.code}`}
                </small>
              </span>
              <ArrowUpLeft size={14} />
            </button>
          ))}
          {!results.length && (
            <p>
              一致する地域がありません。
              <br />
              <small>地域名・5桁の自治体コードで検索できます。</small>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
