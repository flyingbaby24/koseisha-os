"""Prove the cached embedding matrix changed no ranking.

The T7 optimization stops rebuilding a 93.6 MB matrix per request and indexes a
matrix built once at load instead. That is only acceptable if it is provably
the same computation, not merely a similar one (T7 #12).

This compares, on the real corpus:

- the matrix against a fresh `np.stack` of the same rows: bit-identical values
- similarities with and without the corpus: bit-identical scores
- full search results across modes and filters: identical doc_id order

    python -m api.verify_matrix_equivalence
    python -m api.verify_matrix_equivalence --json report.json

Filtered searches are included deliberately. The filters call
`reset_index(drop=True)`, so a positional scheme based on index labels would
pass every unfiltered check and silently rank the wrong documents once a source
filter was applied.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from search_utils import MATRIX_ROW_COLUMN, cosine_against_matrix, work_similarity_by_vector


QUERIES = ["Plato", "justice and the soul", "月と海", "quantum mechanics", "melancholy"]
SOURCES = ["", "gutendex", "user_note", "user_suno"]


def _checks() -> list[tuple[str, bool, str]]:
    from .config import get_settings
    from .search_service import create_search_service

    out: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        out.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")

    settings = get_settings()
    service = create_search_service(settings)

    started = time.perf_counter()
    corpus = service.repository.load_corpus()
    record(
        "corpus_loaded",
        corpus.document_count > 0,
        f"{corpus.document_count:,} documents, matrix "
        f"{corpus.matrix_bytes / 1048576:.1f} MB, dim {corpus.dimension}, "
        f"{time.perf_counter() - started:.1f}s",
    )

    frame = corpus.frame

    # --- the matrix is what stacking would have produced -------------------
    fresh = np.stack(frame["_embedding_vec"].to_list()).astype(np.float32, copy=False)
    record(
        "matrix_bit_identical",
        bool(np.array_equal(fresh, corpus.matrix)),
        f"max abs delta {float(np.abs(fresh - corpus.matrix).max())}",
    )
    record(
        "matrix_dtype_and_layout",
        corpus.matrix.dtype == np.float32 and corpus.matrix.flags["C_CONTIGUOUS"],
        f"{corpus.matrix.dtype}, C-contiguous={corpus.matrix.flags['C_CONTIGUOUS']}",
    )
    record(
        "norms_bit_identical",
        bool(np.array_equal(np.linalg.norm(fresh, axis=1), corpus.norms)),
        "row norms match a fresh computation",
    )
    record(
        "row_column_present",
        MATRIX_ROW_COLUMN in frame.columns
        and bool(np.array_equal(frame[MATRIX_ROW_COLUMN].to_numpy(), np.arange(len(frame)))),
        "every row knows its matrix position",
    )

    # The per-row vectors must be views into the matrix, not a second copy.
    # If this regresses, resident memory quietly grows by another 93.6 MB and
    # nothing else fails, so it is asserted rather than assumed.
    sample = frame["_embedding_vec"].iloc[0]
    shares_memory = getattr(sample, "base", None) is corpus.matrix
    record(
        "vectors_are_matrix_views",
        shares_memory,
        "the frame column and the matrix are one allocation"
        if shares_memory
        else "vectors are a second copy of the matrix",
    )

    # --- similarities are bit-identical with and without the corpus --------
    rng = np.random.default_rng(20260910)
    worst = 0.0
    for _ in range(10):
        target = np.asarray(rng.standard_normal(corpus.dimension), dtype=np.float32)
        with_corpus = cosine_against_matrix([], target, corpus.matrix, corpus.norms)
        without = cosine_against_matrix(frame["_embedding_vec"].to_list(), target)
        worst = max(worst, float(np.abs(with_corpus - without).max()))
    record("similarity_bit_identical", worst == 0.0, f"max abs delta {worst}")

    # --- ranking is identical, unfiltered and filtered ---------------------
    mismatches = 0
    for query in QUERIES:
        target = np.asarray(
            service._encode_query(query), dtype=np.float32  # noqa: SLF001
        )
        ranked_fast = work_similarity_by_vector(
            frame, target_vec=target, top=50, include_self=True, corpus=corpus
        )
        ranked_slow = work_similarity_by_vector(
            frame, target_vec=target, top=50, include_self=True, corpus=None
        )
        same = list(ranked_fast["doc_id"]) == list(ranked_slow["doc_id"])
        identical_scores = bool(
            np.array_equal(
                ranked_fast["similarity"].to_numpy(), ranked_slow["similarity"].to_numpy()
            )
        )
        if not (same and identical_scores):
            mismatches += 1
    record(
        "unfiltered_ranking_identical",
        mismatches == 0,
        f"{len(QUERIES)} queries, top-50 doc_id order and scores",
    )

    # --- the case an index-label scheme would have got wrong ---------------
    from search_utils import apply_metadata_filter

    filtered_mismatches = 0
    detail = ""
    for source in SOURCES[1:]:
        subset = apply_metadata_filter(frame, "source", source)
        if subset.empty:
            continue
        target = np.asarray(service._encode_query("Plato"), dtype=np.float32)  # noqa: SLF001
        fast = work_similarity_by_vector(
            subset, target_vec=target, top=25, include_self=True, corpus=corpus
        )
        slow = work_similarity_by_vector(
            subset, target_vec=target, top=25, include_self=True, corpus=None
        )
        if list(fast["doc_id"]) != list(slow["doc_id"]) or not np.array_equal(
            fast["similarity"].to_numpy(), slow["similarity"].to_numpy()
        ):
            filtered_mismatches += 1
            detail += f" {source}"
        # Every returned row must really belong to the filtered source.
        if "source" in fast.columns and not (fast["source"] == source).all():
            filtered_mismatches += 1
            detail += f" {source}:wrong-source"
    record(
        "filtered_ranking_identical",
        filtered_mismatches == 0,
        f"source filters reset the index; positions still correct{detail}",
    )

    # --- end-to-end responses ----------------------------------------------
    e2e_bad: list[str] = []
    for mode in ("keyword", "semantic", "hybrid"):
        for source in SOURCES:
            response = service.search_response(
                "Plato", top=10, mode=mode, source=source
            )
            if not response.results:
                continue
            if source and any(r.source != source for r in response.results):
                e2e_bad.append(f"{mode}/{source}: foreign source in results")
            if any(getattr(r, MATRIX_ROW_COLUMN, None) is not None for r in response.results):
                e2e_bad.append(f"{mode}/{source}: internal column leaked")
    record(
        "responses_well_formed",
        not e2e_bad,
        "; ".join(e2e_bad) if e2e_bad else "modes x sources return only matching rows",
    )

    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    results = _checks()
    ok = all(passed for _, passed, _ in results)

    print()
    print("RESULT:", "OK" if ok else "FAILED")

    if args.json:
        payload: dict[str, Any] = {
            "ok": ok,
            "checks": [
                {"name": name, "ok": passed, "detail": detail}
                for name, passed, detail in results
            ],
        }
        args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
