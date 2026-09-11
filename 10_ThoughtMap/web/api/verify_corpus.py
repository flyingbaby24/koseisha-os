"""Deployment integrity check for the canonical corpus.

Run from `10_ThoughtMap/web` before or after a deploy:

    python -m api.verify_corpus
    python -m api.verify_corpus --compare-load-paths
    python -m api.verify_corpus --json report.json

Answers one question: is this deployment serving the corpus the manifest says
it is? A silent divergence between documents, embeddings, parameters and map
nodes is the failure T4.5 found the hard way, so counts are compared rather
than assumed (T6 #42).

Exit status is 0 only when every check passes, so this can gate a release.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class Report:
    def __init__(self) -> None:
        self.results: list[Result] = []

    def add(self, name: str, ok: bool, detail: str = "", **data: Any) -> Result:
        result = Result(name=name, ok=ok, detail=detail, data=data)
        self.results.append(result)
        return result

    @property
    def ok(self) -> bool:
        return all(result.ok for result in self.results)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [
                {"name": r.name, "ok": r.ok, "detail": r.detail, **r.data}
                for r in self.results
            ],
        }

    def print(self) -> None:
        width = max((len(r.name) for r in self.results), default=10)
        for result in self.results:
            mark = "PASS" if result.ok else "FAIL"
            print(f"[{mark}] {result.name:<{width}}  {result.detail}")
            for key, value in result.data.items():
                print(f"         {key}: {value}")
        print()
        print("RESULT:", "OK" if self.ok else "FAILED")


def verify(compare_load_paths: bool = False) -> Report:
    from .config import get_settings
    from .corpus_manifest import CorpusManifest, CorpusMismatchError
    from .map_projection import DEFAULT_ARTIFACT_PATH, read_artifact
    from .repositories import CsvSearchIndexRepository, _official_documents_path

    report = Report()
    settings = get_settings()

    if settings.configuration_errors:
        report.add(
            "configuration", False, "; ".join(settings.configuration_errors)
        )
    else:
        report.add("configuration", True, f"mode={settings.deployment_mode}")

    documents_dir = _official_documents_path(settings.db_dir).parent

    try:
        manifest = CorpusManifest.load(documents_dir)
    except CorpusMismatchError as exc:
        report.add("manifest", False, str(exc))
        return report

    if manifest is None:
        report.add("manifest", False, f"No corpus_manifest.json in {documents_dir}")
        return report

    report.add(
        "manifest",
        True,
        f"corpus_version={manifest.corpus_version or '(unset)'}",
        documents=manifest.document_count,
        embeddings=manifest.embedding_count,
        dimension=manifest.embedding_dimension,
        model=manifest.embedding_model,
    )

    # --- artifact ---------------------------------------------------------
    artifact = settings.embeddings_path
    if artifact is None:
        report.add(
            "embedding_artifact",
            False,
            "THOUGHTMAP_EMBEDDINGS_PATH is unset; the tracked legacy snapshot "
            "would be used.",
        )
    elif not artifact.exists():
        report.add("embedding_artifact", False, f"Not found: {artifact}")
    else:
        try:
            manifest.check_artifact_file(artifact)
            started = time.perf_counter()
            matched = manifest.verify_artifact_hash(artifact)
            elapsed = time.perf_counter() - started
            report.add(
                "embedding_artifact",
                matched,
                "checksum verified" if matched else "checksum does NOT match the manifest",
                path=str(artifact),
                bytes=artifact.stat().st_size,
                checksum_seconds=round(elapsed, 1),
            )
        except CorpusMismatchError as exc:
            report.add("embedding_artifact", False, str(exc))

    # --- loaded corpus ----------------------------------------------------
    started = time.perf_counter()
    repository = CsvSearchIndexRepository(settings.db_dir, settings.embeddings_path)
    try:
        index = repository.load_index()
    except Exception as exc:
        report.add("corpus_load", False, f"{type(exc).__name__}: {exc}")
        return report

    load_seconds = time.perf_counter() - started
    report.add(
        "corpus_load",
        len(index) == manifest.document_count,
        f"{len(index):,} searchable documents "
        f"(manifest records {manifest.document_count:,})",
        seconds=round(load_seconds, 1),
        vector_cache_hit=bool(repository.load_stages.get("vector_source", 0.0)),
    )

    # --- parameters -------------------------------------------------------
    with_parameters = 0
    if "parameter_scores" in index.columns:
        with_parameters = int(index["parameter_scores"].map(bool).sum())
    report.add(
        "parameter_scores",
        with_parameters == len(index),
        f"{with_parameters:,} of {len(index):,} documents carry a parameter profile",
    )

    # --- embedding dimension ---------------------------------------------
    dimensions = {len(vector) for vector in index["_embedding_vec"].head(500)}
    report.add(
        "embedding_dimension",
        dimensions == {manifest.embedding_dimension},
        f"sampled dimensions={sorted(dimensions)} expected={manifest.embedding_dimension}",
    )

    # --- map projection ---------------------------------------------------
    if not DEFAULT_ARTIFACT_PATH.exists():
        report.add("map_projection", False, f"Missing: {DEFAULT_ARTIFACT_PATH}")
    else:
        try:
            projection = read_artifact(DEFAULT_ARTIFACT_PATH)
            nodes = len(projection.get("nodes", []))
            report.add(
                "map_projection",
                nodes == len(index),
                f"{nodes:,} nodes (corpus has {len(index):,})",
                fingerprint=str(
                    projection.get("projection", {}).get("dataset_fingerprint", "")
                )[:16],
            )
        except Exception as exc:
            report.add("map_projection", False, f"{type(exc).__name__}: {exc}")

    # --- the two load paths must agree -----------------------------------
    if compare_load_paths:
        _compare_load_paths(report, settings, index)

    return report


def _compare_load_paths(report: Report, settings, cached_index) -> None:
    """The artifact-read path and the vector-cache path must be identical.

    The cache lets a start skip reading the 542 MB artifact entirely. That is
    only safe if it reproduces the artifact exactly, so this reads the artifact
    the slow way and compares doc_ids and vectors element by element.
    """
    import numpy as np

    from .repositories import CsvSearchIndexRepository, _vector_cache_path

    if settings.embeddings_path is None:
        report.add("load_path_equivalence", False, "No external artifact configured.")
        return

    cache = _vector_cache_path(settings.embeddings_path)
    moved = cache.with_suffix(cache.suffix + ".compare")
    if not cache.exists():
        report.add("load_path_equivalence", False, f"No vector cache at {cache}")
        return

    cache.rename(moved)
    try:
        started = time.perf_counter()
        fresh = CsvSearchIndexRepository(settings.db_dir, settings.embeddings_path)
        fresh_index = fresh.load_index()
        elapsed = time.perf_counter() - started
    finally:
        # Restore the cache the fresh load just rewrote, so the comparison
        # never leaves the deployment slower than it found it.
        if cache.exists():
            cache.unlink()
        moved.rename(cache)

    if len(fresh_index) != len(cached_index):
        report.add(
            "load_path_equivalence",
            False,
            f"row counts differ: artifact={len(fresh_index):,} cache={len(cached_index):,}",
        )
        return

    same_ids = list(fresh_index["doc_id"]) == list(cached_index["doc_id"])
    fresh_matrix = np.stack(fresh_index["_embedding_vec"].to_list()).astype(np.float32)
    cached_matrix = np.stack(cached_index["_embedding_vec"].to_list()).astype(np.float32)
    identical = bool(np.array_equal(fresh_matrix, cached_matrix))
    max_delta = float(np.abs(fresh_matrix - cached_matrix).max()) if not identical else 0.0

    report.add(
        "load_path_equivalence",
        same_ids and identical,
        "artifact read and vector cache produce identical vectors"
        if (same_ids and identical)
        else "artifact read and vector cache DISAGREE",
        rows=len(fresh_index),
        doc_ids_identical=same_ids,
        max_abs_delta=max_delta,
        artifact_read_seconds=round(elapsed, 1),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the deployed corpus.")
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument(
        "--compare-load-paths",
        action="store_true",
        help="Also read the artifact the slow way and compare it with the vector cache.",
    )
    args = parser.parse_args(argv)

    report = verify(compare_load_paths=args.compare_load_paths)
    report.print()

    if args.json:
        args.json.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
