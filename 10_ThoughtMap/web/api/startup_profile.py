"""Measure what a cold start actually spends its time on.

Run from `10_ThoughtMap/web`:

    python -m api.startup_profile
    python -m api.startup_profile --json profile.json
    python -m api.startup_profile --drop-vector-cache   # measure a true cold parse

Every number here is wall time in one fresh process. The point is to stop
guessing: before T6 the working assumption was that startup is "the model", and
the measurement is the only way to know whether that is true (T6 #8).

The stages are read from the code that actually ran - `CsvSearchIndexRepository`
records its own load stages - rather than re-implemented here, so this cannot
drift away from the real path.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from .process_memory import peak_mb, resident_mb


def _now() -> float:
    return time.perf_counter()


def _mb(value: int) -> float:
    return round(value / (1024 * 1024), 1)


def _resident_mb() -> float | None:
    return resident_mb()


def _peak_mb() -> float | None:
    return peak_mb()


def profile(warm_model: bool = True, sample_query: str = "Plato") -> dict[str, Any]:
    stages: dict[str, float] = {}
    facts: dict[str, Any] = {}
    process_start = _now()

    # --- Python import ---------------------------------------------------
    # Measured from inside, so it excludes interpreter boot; `--json` callers
    # that need the true process time should wrap this script.
    started = _now()
    from .config import get_settings  # noqa: PLC0415
    from .repositories import create_search_index_repository  # noqa: PLC0415
    from .search_service import ThoughtMapSearchService  # noqa: PLC0415
    from .query_profile import QueryProfileService  # noqa: PLC0415
    from .query_encoder import create_query_encoder, describe_encoder  # noqa: PLC0415

    stages["python_import"] = (_now() - started) * 1000.0

    # --- configuration ---------------------------------------------------
    started = _now()
    settings = get_settings()
    stages["configuration"] = (_now() - started) * 1000.0
    facts["deployment_mode"] = settings.deployment_mode
    facts["embeddings_path"] = str(settings.embeddings_path or "")
    if settings.configuration_errors:
        facts["configuration_errors"] = list(settings.configuration_errors)

    # --- corpus ----------------------------------------------------------
    started = _now()
    repository = create_search_index_repository(settings)
    stages["repository_init"] = (_now() - started) * 1000.0

    started = _now()
    index = repository.load_index()
    stages["corpus_load_total"] = (_now() - started) * 1000.0

    # The repository's own per-stage breakdown of that total.
    for name, value in getattr(repository, "load_stages", {}).items():
        if name == "vector_source":
            facts["vector_cache_hit"] = bool(value)
            continue
        stages[f"corpus.{name}"] = value

    facts["documents"] = len(index)
    facts["resident_mb_after_corpus"] = _resident_mb()

    # --- search service --------------------------------------------------
    facts["encoder"] = describe_encoder(settings)

    started = _now()
    def model_loader():
        return create_query_encoder(settings)

    service = ThoughtMapSearchService(
        repository=repository,
        model_name=settings.model_name,
        model_loader=model_loader,
        query_profile_service=QueryProfileService(model_loader),
    )
    stages["search_service_init"] = (_now() - started) * 1000.0

    # --- keyword search, before any model exists -------------------------
    # Isolates ranking cost from embedding cost. `search()` alone skips the
    # query profile, which /search would also compute.
    started = _now()
    keyword_results = service.search(query=sample_query, mode="keyword", top=10)
    stages["first_keyword_search"] = (_now() - started) * 1000.0
    facts["keyword_results"] = len(keyword_results)

    # --- SentenceTransformer --------------------------------------------
    if warm_model:
        started = _now()
        try:
            model = create_query_encoder(settings)
            stages["encoder_load"] = (_now() - started) * 1000.0
            facts["model"] = settings.model_name
            facts["resident_mb_after_encoder"] = _resident_mb()

            started = _now()
            model.encode([sample_query], show_progress_bar=False)
            stages["first_encode"] = (_now() - started) * 1000.0

            started = _now()
            model.encode([sample_query], show_progress_bar=False)
            stages["warm_encode"] = (_now() - started) * 1000.0

            started = _now()
            service.search(query=sample_query, mode="semantic", top=10)
            stages["first_semantic_search"] = (_now() - started) * 1000.0
        except Exception as exc:
            facts["model_error"] = f"{type(exc).__name__}: {exc}"

    stages["total"] = (_now() - process_start) * 1000.0
    facts["resident_mb_final"] = _resident_mb()
    facts["peak_resident_mb"] = _peak_mb()

    return {
        "stages_ms": {name: round(value, 1) for name, value in stages.items()},
        "facts": facts,
    }


def _drop_vector_cache(settings) -> str:
    path = settings.embeddings_path
    if path is None:
        return "no artifact configured"
    cache = Path(str(path) + ".vectors.npz")
    if not cache.exists():
        return f"no cache at {cache}"
    size = cache.stat().st_size
    cache.unlink()
    return f"removed {cache} ({_mb(size)} MB)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Profile ThoughtMap API startup.")
    parser.add_argument("--json", type=Path, default=None, help="Write the profile to this file.")
    parser.add_argument("--query", default="Plato", help="Sample query for the search stages.")
    parser.add_argument(
        "--skip-model",
        action="store_true",
        help="Do not load sentence-transformers (corpus stages only).",
    )
    parser.add_argument(
        "--drop-vector-cache",
        action="store_true",
        help="Delete the parsed-vector cache first, to measure a true cold parse.",
    )
    args = parser.parse_args(argv)

    if args.drop_vector_cache:
        from .config import get_settings

        print(f"vector cache: {_drop_vector_cache(get_settings())}")

    report = profile(warm_model=not args.skip_model, sample_query=args.query)

    width = max(len(name) for name in report["stages_ms"])
    print("\nStartup stages (ms)")
    print("-" * (width + 14))
    for name, value in report["stages_ms"].items():
        print(f"{name:<{width}}  {value:>10,.1f}")

    print("\nFacts")
    for name, value in report["facts"].items():
        print(f"  {name}: {value}")

    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
