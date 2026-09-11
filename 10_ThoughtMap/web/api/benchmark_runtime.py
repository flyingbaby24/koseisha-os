"""Search latency, concurrency and memory at full corpus scale.

Two modes, because they answer different questions:

    python -m api.benchmark_runtime --mode inprocess
        Ranking cost with no HTTP, no serialization, no server. Use this to
        compare algorithms or storage layouts.

    python -m api.benchmark_runtime --mode http --base-url http://127.0.0.1:8078
        What a client actually waits for, including JSON serialization and the
        server's own concurrency behaviour. Use this for the deployment gate.

Latency is reported as p50/p95 over repeated calls rather than as a mean: a
mean hides the tail, and the tail is what a person notices (T6 #12, #13).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Sequence

from .process_memory import peak_mb, resident_mb


MODES = ("keyword", "semantic", "hybrid")

# A spread of query shapes rather than one word repeated: a single query would
# sit entirely in whatever caches exist and flatter the result.
DEFAULT_QUERIES = (
    "Plato",
    "the nature of justice",
    "月と海",
    "romantic poetry about loss",
    "quantum mechanics",
)


def percentile(values: Sequence[float], fraction: float) -> float:
    """Nearest-rank percentile. Explicit, so small samples stay interpretable."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def summarise(name: str, samples: Sequence[float], errors: int = 0) -> dict[str, Any]:
    return {
        "name": name,
        "samples": len(samples),
        "errors": errors,
        "p50_ms": round(percentile(samples, 0.50), 1),
        "p95_ms": round(percentile(samples, 0.95), 1),
        "min_ms": round(min(samples), 1) if samples else 0.0,
        "max_ms": round(max(samples), 1) if samples else 0.0,
        "mean_ms": round(statistics.fmean(samples), 1) if samples else 0.0,
    }


def _time_calls(call: Callable[[str], Any], queries: Sequence[str], repeats: int) -> tuple[list[float], int]:
    samples: list[float] = []
    errors = 0
    for index in range(repeats):
        query = queries[index % len(queries)]
        started = time.perf_counter()
        try:
            call(query)
        except Exception:
            errors += 1
            continue
        samples.append((time.perf_counter() - started) * 1000.0)
    return samples, errors


# --------------------------------------------------------------------------
# in-process
# --------------------------------------------------------------------------


def benchmark_inprocess(repeats: int, queries: Sequence[str]) -> dict[str, Any]:
    from .config import get_settings
    from .search_service import create_search_service

    settings = get_settings()
    report: dict[str, Any] = {"mode": "inprocess", "queries": list(queries)}

    started = time.perf_counter()
    service = create_search_service(settings)
    index = service.repository.load_index()
    report["cold_corpus_load_s"] = round(time.perf_counter() - started, 2)
    report["documents"] = len(index)
    report["memory_after_corpus_mb"] = resident_mb()

    # First call of each mode, on a process that has never served one. This is
    # what the first user after a restart would experience without warmup.
    cold: dict[str, float] = {}
    for mode in MODES:
        started = time.perf_counter()
        try:
            service.search_response(queries[0], mode=mode, top=10)
        except Exception as exc:
            cold[mode] = -1.0
            report.setdefault("cold_errors", {})[mode] = f"{type(exc).__name__}: {exc}"
            continue
        cold[mode] = round((time.perf_counter() - started) * 1000.0, 1)
    report["cold_first_call_ms"] = cold
    report["memory_after_model_mb"] = resident_mb()

    results = []
    for mode in MODES:
        samples, errors = _time_calls(
            lambda query, mode=mode: service.search_response(query, mode=mode, top=10),
            queries,
            repeats,
        )
        results.append(summarise(mode, samples, errors))
    report["warm"] = results

    # Same call again, ignoring the query profile, to separate ranking cost
    # from the query-embedding cost every mode pays.
    ranking_only = []
    for mode in MODES:
        samples, errors = _time_calls(
            lambda query, mode=mode: service.search(query=query, mode=mode, top=10),
            queries,
            repeats,
        )
        ranking_only.append(summarise(mode, samples, errors))
    report["warm_without_query_profile"] = ranking_only

    report["memory_steady_mb"] = resident_mb()
    report["memory_peak_mb"] = peak_mb()
    return report


# --------------------------------------------------------------------------
# http
# --------------------------------------------------------------------------


def _get(url: str, timeout: float = 60.0) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read(), dict(response.headers)


def _search_url(base_url: str, query: str, mode: str, top: int = 10) -> str:
    params = urllib.parse.urlencode({"q": query, "mode": mode, "top": top})
    return f"{base_url.rstrip('/')}/search?{params}"


def benchmark_http(
    base_url: str,
    repeats: int,
    queries: Sequence[str],
    concurrency_levels: Sequence[int],
) -> dict[str, Any]:
    report: dict[str, Any] = {"mode": "http", "base_url": base_url, "queries": list(queries)}

    # Sequential, one mode at a time.
    warm = []
    for mode in MODES:
        samples, errors = _time_calls(
            lambda query, mode=mode: _get(_search_url(base_url, query, mode)),
            queries,
            repeats,
        )
        warm.append(summarise(mode, samples, errors))
    report["warm"] = warm

    # Concurrency. Each level issues `repeats` requests spread over `level`
    # threads, so the work is constant and only the arrival pattern changes.
    concurrency: list[dict[str, Any]] = []
    for level in concurrency_levels:
        for mode in ("keyword", "semantic"):
            samples: list[float] = []
            errors = 0

            def one(index: int, mode: str = mode) -> float | None:
                query = queries[index % len(queries)]
                started = time.perf_counter()
                try:
                    _get(_search_url(base_url, query, mode))
                except Exception:
                    return None
                return (time.perf_counter() - started) * 1000.0

            wall_started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=level) as pool:
                for value in pool.map(one, range(repeats)):
                    if value is None:
                        errors += 1
                    else:
                        samples.append(value)
            wall = time.perf_counter() - wall_started

            entry = summarise(f"{mode}@{level}", samples, errors)
            entry["concurrency"] = level
            entry["mode_name"] = mode
            entry["wall_s"] = round(wall, 2)
            entry["throughput_rps"] = round(len(samples) / wall, 1) if wall else 0.0
            concurrency.append(entry)
    report["concurrency"] = concurrency

    # /map transfer, uncompressed and gzipped.
    report["map"] = _benchmark_map(base_url)

    try:
        status, body, _ = _get(f"{base_url.rstrip('/')}/ready")
        report["ready"] = json.loads(body)
        report["ready_status"] = status
    except Exception as exc:
        report["ready_error"] = f"{type(exc).__name__}: {exc}"

    return report


def _benchmark_map(base_url: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/map"
    out: dict[str, Any] = {}

    for label, headers in (
        ("identity", {"Accept-Encoding": "identity"}),
        ("gzip", {"Accept-Encoding": "gzip"}),
        ("br", {"Accept-Encoding": "br"}),
    ):
        request = urllib.request.Request(url, headers={"Accept": "application/json", **headers})
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                body = response.read()
                out[label] = {
                    "ms": round((time.perf_counter() - started) * 1000.0, 1),
                    "bytes": len(body),
                    "content_encoding": response.headers.get("Content-Encoding", "none"),
                    "cache_control": response.headers.get("Cache-Control", ""),
                    "etag": response.headers.get("ETag", ""),
                }
        except Exception as exc:
            out[label] = {"error": f"{type(exc).__name__}: {exc}"}

    # Conditional request: the whole point of the ETag.
    etag = str(out.get("gzip", {}).get("etag") or "")
    if etag:
        request = urllib.request.Request(
            url, headers={"Accept": "application/json", "If-None-Match": etag}
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                out["conditional"] = {
                    "status": response.status,
                    "ms": round((time.perf_counter() - started) * 1000.0, 1),
                    "bytes": len(response.read()),
                }
        except urllib.error.HTTPError as exc:
            # urllib raises on 304; that is the success case here.
            out["conditional"] = {
                "status": exc.code,
                "ms": round((time.perf_counter() - started) * 1000.0, 1),
                "bytes": 0,
            }
        except Exception as exc:
            out["conditional"] = {"error": f"{type(exc).__name__}: {exc}"}

    return out


def _print(report: dict[str, Any]) -> None:
    print(json.dumps(report, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark ThoughtMap search at full scale.")
    parser.add_argument("--mode", choices=("inprocess", "http"), default="inprocess")
    parser.add_argument("--base-url", default="http://127.0.0.1:8078")
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument(
        "--concurrency",
        default="1,2,5,10",
        help="Comma-separated concurrency levels for --mode http.",
    )
    args = parser.parse_args(argv)

    if args.mode == "inprocess":
        report = benchmark_inprocess(args.repeats, DEFAULT_QUERIES)
    else:
        levels = [int(value) for value in args.concurrency.split(",") if value.strip()]
        report = benchmark_http(args.base_url, args.repeats, DEFAULT_QUERIES, levels)

    _print(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
