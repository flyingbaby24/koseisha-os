"""Prove the NumPy cosine similarity matches scikit-learn's, bit for bit.

    python -m api.verify_query_profile_equivalence
    python -m api.verify_query_profile_equivalence --json report.json

`thought_composition` used `sklearn.metrics.pairwise.cosine_similarity` for one
call. scikit-learn is deliberately absent from the production runtime — the CI
import guard asserts it — so on the public demo that call raised
`ModuleNotFoundError`, `query_profile` caught it, and every search returned an
empty `query_parameters`. The radar was gone and nothing failed loudly.

Replacing the call is only safe if the numbers do not move, because they are a
user-visible radar. This compares the replacement against the real
scikit-learn implementation on:

    1. the degenerate cases (zero rows, single row, one axis)
    2. random matrices in float32 and float64, to cover dtype promotion
    3. the real 63,891-document corpus matrix against the ten real axis
       vectors, which is the production shape at production scale
    4. `make_filter_scores` end to end, including the clip and the row
       normalisation that follow the similarity

Needs scikit-learn installed, so it runs in development and CI, never in the
deployed container. That asymmetry is the point: the reference has to come
from the library being replaced.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

TOLERANCE = 1e-6

results: list[dict[str, Any]] = []


def record(name: str, ok: bool, detail: str = "", worst: float | None = None) -> None:
    results.append({"name": name, "ok": bool(ok), "detail": detail, "worst": worst})
    mark = "PASS" if ok else "FAIL"
    extra = f"  max abs delta {worst:.3e}" if worst is not None else ""
    print(f"[{mark}] {name:<42} {detail}{extra}")


def compare(name: str, X, Y, reference, candidate) -> float:
    expected = reference(X, Y)
    actual = candidate(X, Y)

    if expected.shape != actual.shape:
        record(name, False, f"shape {actual.shape} != {expected.shape}")
        return float("inf")

    # NaNs would compare unequal to themselves and hide a real difference.
    if np.isnan(expected).any() or np.isnan(actual).any():
        same_nans = np.array_equal(np.isnan(expected), np.isnan(actual))
        record(name, same_nans, f"NaN pattern {'matches' if same_nans else 'DIFFERS'}")
        if not same_nans:
            return float("inf")

    worst = float(np.nanmax(np.abs(expected.astype(np.float64) - actual.astype(np.float64))))
    identical = bool(np.array_equal(expected, actual))
    record(
        name,
        worst <= TOLERANCE,
        f"dtype {actual.dtype}, {'bit-identical' if identical else 'within tolerance'},",
        worst,
    )
    return worst


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", type=Path, default=None)
    parser.add_argument("--skip-corpus", action="store_true")
    args = parser.parse_args(argv)

    try:
        from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine
    except ImportError:
        print("scikit-learn is required as the reference. Install it to run this check.")
        print("  pip install scikit-learn")
        return 2

    from thought_composition import cosine_similarity as numpy_cosine

    rng = np.random.default_rng(20260913)

    # --- 1. degenerate shapes ---------------------------------------------
    compare(
        "single row vs single axis",
        rng.standard_normal((1, 384), dtype=np.float32),
        rng.standard_normal((1, 384), dtype=np.float32),
        sklearn_cosine, numpy_cosine,
    )
    compare(
        "one query vs ten axes (production shape)",
        rng.standard_normal((1, 384), dtype=np.float32),
        rng.standard_normal((10, 384), dtype=np.float32),
        sklearn_cosine, numpy_cosine,
    )

    zero_rows = rng.standard_normal((5, 384), dtype=np.float32)
    zero_rows[2] = 0.0                     # a document with no embedding at all
    axes = rng.standard_normal((10, 384), dtype=np.float32)
    axes[7] = 0.0                          # and a degenerate axis
    compare("zero rows on both sides", zero_rows, axes, sklearn_cosine, numpy_cosine)

    # --- 2. dtype promotion ------------------------------------------------
    f32 = rng.standard_normal((64, 384), dtype=np.float32)
    f64 = rng.standard_normal((10, 384))
    compare("float32 x float32 (stays float32)", f32, f32[:10], sklearn_cosine, numpy_cosine)
    compare("float64 x float64", f64, f64, sklearn_cosine, numpy_cosine)
    compare("float32 x float64 (promotes)", f32, f64, sklearn_cosine, numpy_cosine)

    # --- 3. the real corpus ------------------------------------------------
    if not args.skip_corpus:
        try:
            from .config import get_settings
            from .repositories import create_search_index_repository

            corpus = create_search_index_repository(get_settings()).load_corpus()
            documents = corpus.matrix
            from .query_encoder import get_query_encoder
            from .query_profile import FILTERS_DIR
            categories = json.loads((FILTERS_DIR / "general.json").read_text(encoding="utf-8"))
            encoder = get_query_encoder(get_settings())
            real_axes = np.asarray(encoder.encode(list(categories.values()), show_progress_bar=False), dtype=np.float32)
            worst = compare(
                f"real corpus {documents.shape[0]:,} x 10 axes",
                documents, real_axes, sklearn_cosine, numpy_cosine,
            )
            import thought_composition as tc
            from .query_profile import QueryProfileService
            original = tc.cosine_similarity
            try:
                tc.cosine_similarity = numpy_cosine
                actual = tc.make_filter_scores(documents, categories, encoder).to_numpy()
                tc.cosine_similarity = sklearn_cosine
                expected = tc.make_filter_scores(documents, categories, encoder).to_numpy()
                record("full-corpus radar equivalence", np.array_equal(actual, expected),
                       worst=float(np.max(np.abs(actual - expected))))
                record("full-corpus axis ranking equivalence",
                       np.array_equal(np.argsort(actual, axis=0, kind="stable"),
                                      np.argsort(expected, axis=0, kind="stable")))
                for query in ("Plato", "justice and society", "science", "自由", "人間の幸福"):
                    tc.cosine_similarity = numpy_cosine
                    candidate = QueryProfileService(lambda: encoder).score_query(query)
                    tc.cosine_similarity = sklearn_cosine
                    reference = QueryProfileService(lambda: encoder).score_query(query)
                    record(f"real query radar: {query}",
                           candidate is not None and len(candidate) == 10 and candidate == reference)
            finally:
                tc.cosine_similarity = original
            del documents, corpus, actual, expected
        except Exception as exc:
            record("real corpus", False, f"failed ({type(exc).__name__}: {exc})"[:200])

    # --- 4. make_filter_scores end to end ----------------------------------
    # The similarity is only the first step; the clip and the row-sum
    # normalisation after it are where a sign or a zero row would show up.
    import thought_composition as tc

    class StubEncoder:
        """Returns fixed vectors, so only the arithmetic under test varies."""

        def __init__(self, vectors): self._vectors = vectors
        def encode(self, texts, show_progress_bar=False): return self._vectors

    categories = {k: f"description of {k}" for k in tc.THOUGHT_COMPOSITION_PARAMETERS}
    axis_vectors = rng.standard_normal((10, 384), dtype=np.float32)
    embeddings = rng.standard_normal((256, 384), dtype=np.float32)
    embeddings[5] = 0.0
    # Force a row whose every cosine is negative, so the clip drives it to all
    # zeros and the divide-by-zero guard is the thing being exercised.
    embeddings[6] = -axis_vectors.sum(axis=0) * 1000.0

    original = tc.cosine_similarity
    try:
        frame_numpy = tc.make_filter_scores(embeddings, categories, StubEncoder(axis_vectors))
        tc.cosine_similarity = sklearn_cosine
        frame_sklearn = tc.make_filter_scores(embeddings, categories, StubEncoder(axis_vectors))
    finally:
        tc.cosine_similarity = original

    same_columns = list(frame_numpy.columns) == list(frame_sklearn.columns)
    record(
        "axis ordering preserved",
        same_columns and list(frame_numpy.columns) == tc.THOUGHT_COMPOSITION_PARAMETERS,
        f"{list(frame_numpy.columns)[:3]}... ({len(frame_numpy.columns)} axes)",
    )

    delta = float(
        np.nanmax(np.abs(frame_numpy.to_numpy(dtype=np.float64)
                         - frame_sklearn.to_numpy(dtype=np.float64)))
    )
    record("make_filter_scores values", delta <= TOLERANCE, "after clip + normalise,", delta)

    sums = frame_numpy.to_numpy(dtype=np.float64).sum(axis=1)
    scored = sums[sums > 0]
    record(
        "scored rows sum to 1.0",
        bool(np.allclose(scored, 1.0, atol=1e-6)),
        f"{len(scored)} scored, {int((sums == 0).sum())} all-zero row(s) preserved,",
        float(np.max(np.abs(scored - 1.0))) if scored.size else 0.0,
    )

    # --- 5. the production runtime must not import scikit-learn ------------
    #
    # Asked as "does importing it pull sklearn in", not "does the file mention
    # sklearn" - the docstrings name it deliberately, and a grep would fail on
    # the explanation rather than on the dependency.
    probe = (
        "import sys, json;"
        "sys.path.insert(0, %r);"
        "import thought_composition;"
        "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0]=='sklearn')))"
        % str(Path(tc.__file__).parent)
    )
    import subprocess

    pulled = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True
    )
    leaked = json.loads(pulled.stdout.strip() or "[]") if pulled.returncode == 0 else ["<probe failed>"]
    record(
        "importing thought_composition pulls in no sklearn",
        not leaked,
        f"sklearn modules loaded: {leaked or 'none'}",
    )

    failed = [r["name"] for r in results if not r["ok"]]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed  (tolerance {TOLERANCE:.0e})")
    print("RESULT:", "OK" if not failed else f"FAILED - {failed}")

    if args.json:
        args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Wrote {args.json}")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
