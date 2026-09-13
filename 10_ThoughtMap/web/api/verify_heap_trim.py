"""Measure what `malloc_trim(0)` actually reclaims, on Linux, under a cap.

    python -m api.verify_heap_trim
    python -m api.verify_heap_trim --limit-mb 512 --json trim.json

Every memory number this project has published was measured on Windows, where
the CRT has no way to hand free heap back to the OS and `release_free_heap()`
is a no-op. Two of the remaining questions can therefore only be answered on
Linux:

  1. Does the free heap left over from the corpus load actually get returned?
     Releasing the corpus object gives back 106.6 MB of 219.4 MB, so roughly
     113 MB is free-but-retained. glibc can return that; the Windows CRT cannot.

  2. Do the file-backed pages — the 366 MB ONNX vocabulary table and the 15.5 MB
     `/map` payload — behave as evictable under pressure rather than counting
     against the process the way anonymous memory does?

This brings the process to the state a deployed instance reaches after warmup,
trims, and reports both numbers, plus the split between anonymous and
file-backed memory that decides question 2. Run it inside a memory-capped
cgroup to make the answer about a 512 MB instance rather than about a laptop:

    systemd-run --user --scope -p MemoryMax=512M -p MemorySwapMax=0 \\
        python -m api.verify_heap_trim --limit-mb 512

or, without systemd:

    sudo mkdir -p /sys/fs/cgroup/thoughtmap
    echo 536870912 | sudo tee /sys/fs/cgroup/thoughtmap/memory.max
    echo 0         | sudo tee /sys/fs/cgroup/thoughtmap/memory.swap.max
    echo $$        | sudo tee /sys/fs/cgroup/thoughtmap/cgroup.procs
    python -m api.verify_heap_trim --limit-mb 512

Refuses to run anywhere but Linux. A trim number from a platform that cannot
trim is worse than no number, because it would be quoted later.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path
from typing import Any


def _proc_kb(field: str) -> int:
    """One field of /proc/self/smaps_rollup, in KB. 0 when unavailable."""
    try:
        with open("/proc/self/smaps_rollup", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith(field):
                    return int(line.split()[1])
    except OSError:
        pass
    return 0


def _status_kb(field: str) -> int:
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith(field):
                    return int(line.split()[1])
    except OSError:
        pass
    return 0


def _cgroup_limit_mb() -> float | None:
    """The cgroup v2 memory ceiling this process is actually under."""
    try:
        cgroup = Path("/proc/self/cgroup").read_text(encoding="utf-8").strip()
        relative = cgroup.split(":")[-1].lstrip("/")
        for candidate in (
            Path("/sys/fs/cgroup") / relative / "memory.max",
            Path("/sys/fs/cgroup/memory.max"),
        ):
            if candidate.exists():
                raw = candidate.read_text(encoding="utf-8").strip()
                if raw == "max":
                    return None
                return int(raw) / (1024 * 1024)
    except (OSError, ValueError):
        pass
    return None


def _snapshot() -> dict[str, float]:
    """Where this process's memory is, and how much of it can be reclaimed."""
    gc.collect()
    rss = _status_kb("VmRSS:") / 1024
    anonymous = _proc_kb("Anonymous:") / 1024
    file_backed = _proc_kb("Rss:") / 1024 - anonymous if _proc_kb("Rss:") else 0.0
    return {
        "rss_mb": round(rss, 1),
        # Anonymous memory is the part no amount of eviction can reclaim: it is
        # what actually has to fit.
        "anonymous_mb": round(anonymous, 1),
        # File-backed pages — mapped model weights, the /map sidecar, the
        # interpreter and shared libraries. Under pressure the kernel drops
        # these and re-reads them instead of killing the process.
        "file_backed_mb": round(max(file_backed, 0.0), 1),
    }


def run(searches: int = 12) -> dict[str, Any]:
    from .config import get_settings
    from .map_response_cache import MapResponseCache
    from .map_service import MapService
    from .process_memory import release_free_heap
    from .query_encoder import get_query_encoder
    from .search_service import create_search_service

    settings = get_settings()

    print("bringing the process to a warmed deployed state ...")
    service = create_search_service(settings)
    corpus = service.repository.load_corpus()
    encoder = get_query_encoder(settings)
    encoder.encode(["warmup"])
    MapResponseCache().get_for(MapService())
    for index in range(searches):
        mode = ("keyword", "semantic", "hybrid")[index % 3]
        service.search_response(f"Plato {index}", mode=mode, top=10)

    before = _snapshot()
    trimmed = release_free_heap()
    after = _snapshot()

    return {
        "platform": sys.platform,
        "documents": len(corpus.frame),
        "trim_ran": bool(trimmed),
        "before": before,
        "after": after,
        "reclaimed_mb": round(before["rss_mb"] - after["rss_mb"], 1),
        "cgroup_limit_mb": _cgroup_limit_mb(),
        "peak_rss_mb": round(_status_kb("VmHWM:") / 1024, 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--searches", type=int, default=12)
    parser.add_argument(
        "--limit-mb",
        type=float,
        default=512.0,
        help="The instance size to judge the result against.",
    )
    parser.add_argument(
        "--headroom-mb",
        type=float,
        default=40.0,
        help="How much slack below the limit counts as safe.",
    )
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    if not sys.platform.startswith("linux"):
        print(f"This measures glibc's malloc_trim, which {sys.platform} does not have.")
        print("Run it on Linux — see the module docstring for a capped cgroup.")
        return 2

    report = run(args.searches)

    print()
    print(f"documents          : {report['documents']:,}")
    print(f"cgroup memory.max  : "
          f"{report['cgroup_limit_mb'] or 'unlimited (not running under a cap)'}")
    print()
    print(f"{'':<20}{'RSS':>10}{'anonymous':>12}{'file-backed':>14}")
    for label, key in (("before trim", "before"), ("after trim", "after")):
        snapshot = report[key]
        print(f"{label:<20}{snapshot['rss_mb']:10.1f}{snapshot['anonymous_mb']:12.1f}"
              f"{snapshot['file_backed_mb']:14.1f}")
    print()
    print(f"malloc_trim ran    : {report['trim_ran']}")
    print(f"reclaimed          : {report['reclaimed_mb']:.1f} MB")
    print(f"peak RSS           : {report['peak_rss_mb']:.1f} MB")

    steady = report["after"]["rss_mb"]
    anonymous = report["after"]["anonymous_mb"]
    limit = args.limit_mb
    safe = limit - args.headroom_mb

    print()
    print(f"against a {limit:.0f} MB instance:")
    print(f"  steady RSS       : {steady:.1f} MB ({steady / limit:.0%} of the limit)")
    print(f"  unreclaimable    : {anonymous:.1f} MB ({anonymous / limit:.0%}) "
          "— what must fit even under pressure")
    print(f"  peak             : {report['peak_rss_mb']:.1f} MB "
          f"({'over' if report['peak_rss_mb'] > limit else 'under'} the limit)")

    verdict = (
        "FITS with headroom"
        if steady <= safe and report["peak_rss_mb"] <= limit
        else "FITS but without the requested headroom"
        if steady <= limit and report["peak_rss_mb"] <= limit
        else "DOES NOT FIT"
    )
    print(f"\nRESULT: {verdict}")

    if args.json:
        report["limit_mb"] = limit
        report["verdict"] = verdict
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")

    return 0 if verdict != "DOES NOT FIT" else 1


if __name__ == "__main__":
    sys.exit(main())
