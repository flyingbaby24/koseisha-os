import { useId, useMemo, useRef, useState } from "react";
import { CornerDownLeft, MapPin, Search, X } from "lucide-react";
import type { Region, Statistics } from "./types";
import { levelLabel } from "./ui";

const normalize = (text: string) =>
  text.trim().replace(/[ 　]/g, "").toLowerCase();

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
  const input = useRef<HTMLInputElement>(null);
  const id = useId();
  const results = useMemo(() => {
    const q = normalize(query);
    if (!q) return [];
    // Exact name/code first, then names starting with the query, then the rest.
    const score = (r: Region) =>
      r.name === q || r.code === q ? 0 : r.name.startsWith(q) ? 1 : 2;
    return [...data.prefectures, ...data.cities, ...data.municipalities]
      .map((region, order) => ({ region, order }))
      .filter(({ region: r }) =>
        `${r.prefecture}${r.name}${r.code}`.includes(q),
      )
      .sort((a, b) => score(a.region) - score(b.region) || a.order - b.order)
      .slice(0, 9)
      .map(({ region }) => region);
  }, [data, query]);
  const expanded = open && !!query.trim();
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
      <Search size={18} aria-hidden="true" className="search-icon" />
      <input
        ref={input}
        aria-label="都道府県・市区町村を検索"
        placeholder="地域名・コードで検索"
        value={query}
        role="combobox"
        enterKeyHint="search"
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={expanded}
        aria-controls={id}
        aria-activedescendant={
          expanded && results[active] ? `${id}-${active}` : undefined
        }
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            if (expanded) setOpen(false);
            else setQuery("");
          }
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setOpen(true);
            setActive((v) => Math.min(v + 1, results.length - 1));
          }
          if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((v) => Math.max(0, v - 1));
          }
          if (e.key === "Enter" && expanded && results[active]) {
            e.preventDefault();
            choose(results[active]);
          }
        }}
      />
      {query && (
        <button
          className="search-clear"
          aria-label="検索をクリア"
          onClick={() => {
            setQuery("");
            input.current?.focus();
          }}
        >
          <X size={16} />
        </button>
      )}
      {expanded && (
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
              tabIndex={-1}
              aria-selected={i === active}
              className={i === active ? "is-active" : ""}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => choose(region)}
            >
              <MapPin size={16} aria-hidden="true" />
              <span>
                <strong>{region.name}</strong>
                <small>
                  {region.level === "a"
                    ? "都道府県 · 地図を絞り込み"
                    : `${region.prefecture} · ${levelLabel(region)} · ${region.code}`}
                </small>
              </span>
              {i === active && (
                <CornerDownLeft size={15} aria-hidden="true" className="search-enter" />
              )}
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
