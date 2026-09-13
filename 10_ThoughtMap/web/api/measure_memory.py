"""Steady-state memory of the public-demo runtime, measured the same way twice.

    python -m api.measure_memory
    python -m api.measure_memory --label "after dedup" --json out.json

Brings the process to the state a deployed instance reaches after warmup and a
few searches, then reports resident memory. The point is comparability: every
optimization is measured by this one script, in this one order, so the numbers
can be put side by side.

Steady RSS is the number that decides whether the service fits an instance.
Peak matters too, because an instance is killed on peak, not on average.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path
from typing import Any


def _rss() -> float:
    from .process_memory import resident_mb

    gc.collect()
    return resident_mb() or 0.0


def _peak() -> float:
    from .process_memory import peak_mb

    return peak_mb() or 0.0


def _private() -> float:
    """Memory that would survive every file page being evicted."""
    from .process_memory import private_mb

    return private_mb() or 0.0


def measure(searches: int = 12) -> dict[str, Any]:
    stages: list[tuple[str, float, float, float]] = []

    # The peak counter is monotonic, so the jump between two marks is the
    # transient that stage allocated and freed. That is the number an instance
    # is killed on, and without it a stage that briefly doubles its own cost
    # looks free.
    def mark(label: str) -> float:
        value = _rss()
        delta = value - (stages[-1][1] if stages else 0.0)
        peak = _peak()
        peak_delta = peak - (stages[-1][3] if stages else 0.0)
        stages.append((label, value, delta, peak))
        print(f"  {label:<40} {value:8.1f} MB   (+{delta:7.1f})"
              f"   peak {peak:8.1f}   (+{peak_delta:6.1f})")
        return value

    print("stage-by-stage resident memory")
    print("-" * 64)
    mark("interpreter + imports")

    from .config import get_settings
    from .map_response_cache import MapResponseCache
    from .map_service import MapService
    from .search_service import create_search_service

    settings = get_settings()
    service = create_search_service(settings)
    mark("service constructed")

    corpus = service.repository.load_corpus()
    mark("corpus loaded")

    # Warmup loads the encoder exactly as the lifespan task does: through the
    # cached factory, so this measures one session and not an extra one.
    from .query_encoder import get_query_encoder

    encoder_holder = get_query_encoder(settings)
    encoder_holder.encode(["warmup"])
    mark("encoder warmed (as lifespan does)")

    map_cache = MapResponseCache()
    encoded = map_cache.get_for(MapService())
    mark("map response prepared")

    # The deployed process trims here too, at the end of `run_warmup`. Doing it
    # in the same place keeps this harness a measurement of the server rather
    # than of a slightly different program.
    from .process_memory import release_free_heap

    trimmed = release_free_heap()
    mark("free heap released" if trimmed else "heap trim unavailable (no-op)")

    for index in range(searches):
        mode = ("keyword", "semantic", "hybrid")[index % 3]
        service.search_response(f"Plato {index}", mode=mode, top=10)
    mark(f"after {searches} searches")

    steady = _rss()
    peak = _peak()

    print()
    print(f"  STEADY RSS {steady:8.1f} MB")
    print(f"  PEAK   RSS {peak:8.1f} MB")

    # Resident memory here is mostly file-backed — 449 MB of memory-mapped ONNX
    # weights, the prepared /map response, the interpreter — and those pages are
    # evictable. How much is *not* evictable is the number that decides whether
    # a 512 MB instance is enough, and it is only measurable on Linux:
    # smaps_rollup reports Anonymous exactly.
    #
    # Windows has no equivalent. `PrivateUsage` is commit charge, which counts
    # committed-but-untouched reservations — ONNX Runtime's arena and BLAS
    # between them commit close to a gigabyte this process never touches — so
    # it reads ~1,475 MB against a 502 MB working set. Printing that would
    # invite exactly the wrong conclusion, so it is not printed.
    private = _private()
    if sys.platform.startswith("linux"):
        print(f"  ANONYMOUS  {private:8.1f} MB   (unreclaimable; what must fit)")
    else:
        print("  anonymous vs file-backed: Linux only — see api.verify_heap_trim")

    encoders_shared = service._model is service.query_profile_service._model  # noqa: SLF001
    print(f"  one encoder session: {encoders_shared}")
    print(f"  documents: {len(corpus.frame):,}   frame columns: {len(corpus.frame.columns)}")
    print(f"  map payload: raw {encoded.raw_bytes / 1048576:.1f} MB, "
          f"gzip {encoded.gzipped_bytes / 1048576:.1f} MB, "
          f"held {'on disk' if encoded.on_disk else 'in memory'}")

    print(f"  heap trim: {'applied' if trimmed else 'unavailable on this platform'}")

    return {
        "steady_mb": round(steady, 1),
        "peak_mb": round(peak, 1),
        # Meaningful on Linux (smaps_rollup Anonymous); commit charge on
        # Windows, where it is not comparable. See the note above.
        "anonymous_mb": round(private, 1) if sys.platform.startswith("linux") else None,
        "heap_trimmed": bool(trimmed),
        "tokenizer": getattr(settings, "encoder_tokenizer", ""),
        "map_payload_on_disk": bool(encoded.on_disk),
        "documents": len(corpus.frame),
        "frame_columns": len(corpus.frame.columns),
        "encoders_shared": bool(encoders_shared),
        "stages": [
            {
                "label": label,
                "rss_mb": round(value, 1),
                "delta_mb": round(delta, 1),
                "peak_mb": round(peak, 1),
            }
            for label, value, delta, peak in stages
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--label", default="")
    parser.add_argument("--searches", type=int, default=12)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.label:
        print(f"=== {args.label} ===")
    report = measure(args.searches)
    report["label"] = args.label

    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
