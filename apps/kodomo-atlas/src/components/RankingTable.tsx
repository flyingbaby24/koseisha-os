import { useEffect, useMemo, useState } from "react";
import {
  ArrowDownUp,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Download,
} from "lucide-react";
import {
  colorOf,
  difference,
  formatValue,
  integer,
  metrics,
  valueOf,
} from "../metrics";
import type { Metric, Region } from "../types";
import { sortByMetric } from "../ui";
import { BaselineLabel } from "./common";

const PAGE = 25;

/** Competition ranks over an already sorted list: equal values share a rank. */
function competitionRanks(ranked: Region[], metric: Metric): number[] {
  const ranks: number[] = [];
  ranked.forEach((region, i) => {
    const same =
      i > 0 && valueOf(region, metric) === valueOf(ranked[i - 1], metric);
    ranks.push(same ? ranks[i - 1] : i + 1);
  });
  return ranks;
}

export default function RankingTable({
  regions,
  metric,
  baseline,
  scopeName,
  onSelect,
}: {
  regions: Region[];
  metric: Metric;
  baseline: Region;
  scopeName: string;
  onSelect: (region: Region) => void;
}) {
  const [descending, setDescending] = useState(true);
  const [page, setPage] = useState(0);
  useEffect(() => {
    setPage(0);
  }, [regions, metric, descending]);
  const ranked = useMemo(
    () => sortByMetric(regions, metric, descending),
    [regions, metric, descending],
  );
  const ranks = useMemo(() => competitionRanks(ranked, metric), [ranked, metric]);
  const totalPages = Math.ceil(ranked.length / PAGE);
  const missing = regions.length - ranked.length;
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
        ranks[i],
        r.code,
        r.prefecture,
        r.name,
        valueOf(r, metric),
        metrics[metric].unit,
        metrics[metric].period,
      ]),
    ];
    const csv =
      "﻿" +
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
    <section className="ranking-table-card" aria-labelledby="ranking-title">
      <div className="ranking-table-heading">
        <div>
          <span className="eyebrow">{scopeName}のランキング</span>
          <h2 id="ranking-title">{metrics[metric].label}</h2>
          <p>
            {metrics[metric].period} · {integer.format(ranked.length)}地域
            {missing > 0 && `（欠損・非公表の${missing}地域は除外）`}
          </p>
        </div>
        <div className="ranking-actions">
          <button
            className="button secondary"
            onClick={() => setDescending((v) => !v)}
            aria-label={`並び順：${descending ? "高い順" : "低い順"}（押すと切り替え）`}
          >
            <ArrowDownUp size={16} aria-hidden="true" />
            {descending ? "高い順" : "低い順"}
          </button>
          <button className="button secondary" onClick={download}>
            <Download size={16} aria-hidden="true" />
            CSV
          </button>
        </div>
      </div>
      <p className="ranking-hint">
        地域名を押すと地図に戻り、その地域の詳細を表示します。同じ値の地域は同順位です。
      </p>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th scope="col">順位</th>
              <th scope="col">市区町村</th>
              <th scope="col" className="num">
                {metrics[metric].label}
                {metrics[metric].unit && ` (${metrics[metric].unit})`}
              </th>
              <th scope="col" className="num">
                <BaselineLabel metric={metric} />
                との差
              </th>
              <th scope="col">
                <span className="sr-only">地図</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {ranked.slice(page * PAGE, (page + 1) * PAGE).map((r, i) => (
              <tr key={r.code}>
                <td className="table-rank">{ranks[page * PAGE + i]}</td>
                <td>
                  <button className="table-place" onClick={() => onSelect(r)}>
                    <strong>{r.name}</strong>
                    <small>
                      {r.prefecture} · {r.code}
                    </small>
                  </button>
                </td>
                <td className="table-value num">
                  <i
                    style={{ background: colorOf(valueOf(r, metric), metric) }}
                    aria-hidden="true"
                  />
                  {formatValue(valueOf(r, metric), metric)}
                </td>
                <td className="table-difference num">
                  {difference(r, baseline, metric)}
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={`${r.name}を地図で表示`}
                    onClick={() => onSelect(r)}
                  >
                    <ArrowUpRight size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-pagination">
        <span>
          {ranked.length ? page * PAGE + 1 : 0}–
          {Math.min((page + 1) * PAGE, ranked.length)} /{" "}
          {integer.format(ranked.length)}地域
        </span>
        <div>
          <button
            className="icon-button"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            aria-label="前のページ"
          >
            <ChevronLeft size={18} />
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
            <ChevronRight size={18} />
          </button>
        </div>
      </div>
    </section>
  );
}
