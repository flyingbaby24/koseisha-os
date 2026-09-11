"""Benchmark the canonical UMAP projection on samples before the full run.

    python -m api.benchmark_projection --sizes 5000 15000 30000

T3 projected 4,915 documents in 92 s. UMAP does not scale linearly, so the
full-corpus runtime has to be measured rather than extrapolated from one point.
This runs the canonical configuration on increasing samples and fits the
observed growth to estimate the full run.

Configuration is never varied for speed: the point is to find out what the
canonical settings actually cost.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

import numpy as np

from .config import get_settings
from .map_projection import ProjectionConfig
from .repositories import create_search_index_repository


def peak_memory_mb() -> float | None:
    """Resident set size, when psutil is available."""
    try:
        import psutil
    except Exception:
        return None
    return psutil.Process().memory_info().rss / (1024 * 1024)


def run_once(matrix: np.ndarray, config: ProjectionConfig) -> dict[str, float]:
    from umap import UMAP

    gc.collect()
    before = peak_memory_mb()
    started = time.perf_counter()

    reducer = UMAP(
        n_components=config.n_components,
        n_neighbors=min(config.n_neighbors, max(2, matrix.shape[0] - 1)),
        min_dist=config.min_dist,
        metric=config.metric,
        random_state=config.random_seed,
    )
    coordinates = np.asarray(reducer.fit_transform(matrix), dtype=np.float64)

    elapsed = time.perf_counter() - started
    after = peak_memory_mb()

    return {
        "rows": int(matrix.shape[0]),
        "seconds": elapsed,
        "finite": bool(np.isfinite(coordinates).all()),
        "rss_before_mb": before,
        "rss_after_mb": after,
        "rss_delta_mb": (after - before) if (before is not None and after is not None) else None,
    }


def estimate_full(results: list[dict[str, float]], target_rows: int) -> dict[str, float]:
    """Fit seconds ~ a * rows^b and project it to the full corpus.

    Only measurements marked as timed are used. UMAP runs on numba, and the
    first call in a process pays JIT compilation that can exceed the projection
    itself — in one run 5,000 rows took 36 s while 15,000 took 8.5 s. Fitting
    across that produces a negative exponent and a meaningless estimate, so the
    warm-up run is excluded rather than averaged in.
    """
    usable = [r for r in results if r["rows"] > 0 and r["seconds"] > 0 and not r.get("warmup")]
    if len(usable) < 2:
        return {}

    rows = np.log(np.array([r["rows"] for r in usable], dtype=float))
    seconds = np.log(np.array([r["seconds"] for r in usable], dtype=float))
    exponent, intercept = np.polyfit(rows, seconds, 1)

    predicted = float(np.exp(intercept + exponent * np.log(target_rows)))
    return {
        "exponent": float(exponent),
        "predicted_seconds": predicted,
        "predicted_minutes": predicted / 60.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark UMAP at increasing sizes.")
    parser.add_argument("--sizes", type=int, nargs="+", default=[5000, 15000, 30000])
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed (not the UMAP seed).")
    parser.add_argument("--json", default="")
    args = parser.parse_args(argv)

    config = ProjectionConfig()
    repository = create_search_index_repository(get_settings())

    started = time.perf_counter()
    frame = repository.load_index()
    print(f"corpus loaded: {len(frame)} rows in {time.perf_counter() - started:.1f}s")

    full = np.stack(frame["_embedding_vec"].to_list()).astype(np.float32)
    print(f"matrix: {full.shape}  {full.nbytes / 1e6:.0f} MB")
    print(f"config: {config.to_dict()}")
    print()

    rng = np.random.default_rng(args.seed)
    results: list[dict[str, float]] = []

    # Compile the numba kernels on a trivial sample first, so the first real
    # measurement is not dominated by JIT compilation.
    warmup_rows = min(600, full.shape[0])
    print(f"warming up numba on {warmup_rows} rows ...", flush=True)
    warmup = run_once(np.ascontiguousarray(full[:warmup_rows]), config)
    warmup["warmup"] = True
    results.append(warmup)
    print(f"  {warmup['seconds']:.1f}s (JIT, excluded from the fit)")
    print()

    for size in args.sizes:
        if size > full.shape[0]:
            print(f"skipping {size}: corpus has only {full.shape[0]} rows")
            continue

        # A random subset, so the sample is representative of the whole corpus
        # rather than of whatever happens to sit at the front of the file.
        index = rng.choice(full.shape[0], size=size, replace=False)
        sample = np.ascontiguousarray(full[np.sort(index)])

        print(f"projecting {size} rows ...", flush=True)
        result = run_once(sample, config)
        results.append(result)
        print(
            f"  {result['seconds']:.1f}s  finite={result['finite']}"
            + (f"  rss+{result['rss_delta_mb']:.0f}MB" if result["rss_delta_mb"] is not None else "")
        )

    estimate = estimate_full(results, full.shape[0])
    print()
    if estimate:
        print(f"observed growth exponent : {estimate['exponent']:.2f}")
        print(
            f"estimated full run       : {estimate['predicted_seconds']:.0f}s "
            f"({estimate['predicted_minutes']:.1f} min) for {full.shape[0]} rows"
        )
    else:
        print("not enough samples to estimate the full run")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"results": results, "estimate": estimate, "corpus_rows": int(full.shape[0])}, indent=2),
            encoding="utf-8",
        )
        print(f"wrote {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
