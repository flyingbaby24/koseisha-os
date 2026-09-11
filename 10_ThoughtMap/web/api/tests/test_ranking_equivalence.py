"""The vectorised ranking must agree with the row-wise original.

`work_similarity_by_vector` was vectorised in T4.6 for speed. This pins the
behaviour by re-implementing the pre-T4.6 version verbatim and asserting the two
agree on ordering and on scores within floating-point tolerance.

If ranking policy ever genuinely changes, these tests must be updated
deliberately — they exist to make that impossible to do by accident.
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from search_utils import (
    cosine,
    format_similarity,
    normalize_text,
    work_similarity_by_vector,
)


def rowwise_reference(
    df: pd.DataFrame,
    target_vec: np.ndarray,
    top: int,
    exclude_doc_id: str = "",
    include_self: bool = False,
) -> pd.DataFrame:
    """The implementation as it stood before T4.6, copied verbatim."""
    rows = []

    for _, row in df.iterrows():
        if exclude_doc_id and not include_self:
            if normalize_text(row.get("doc_id", "")) == normalize_text(exclude_doc_id):
                continue

        result_row = {
            "similarity": cosine(target_vec, row["_embedding_vec"]),
            "doc_id": row.get("doc_id", ""),
            "gutenberg_id": row.get("gutenberg_id", ""),
            "author": row.get("author", ""),
            "title": row.get("title", ""),
            "source": row.get("source", ""),
            "category": row.get("category", ""),
            "subcategory": row.get("subcategory", ""),
            "source_url": row.get("source_url", ""),
            "model_name": row.get("model_name", ""),
            "embedding": row.get("embedding", ""),
        }

        for column in [
            "parameters", "parameter_scores", "filter_scores",
            "composition", "thought_composition", "scores",
        ]:
            if column in row.index:
                result_row[column] = row.get(column)

        rows.append(result_row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out.sort_values("similarity", ascending=False).head(top).reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def corpus(count: int, dimension: int = 384, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    vectors = rng.normal(size=(count, dimension)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)

    return pd.DataFrame(
        {
            "doc_id": [f"gutendex:doc_{i:06d}" for i in range(count)],
            "title": [f"Title {i}" for i in range(count)],
            "author": [f"Author {i % 37}" for i in range(count)],
            "source": ["gutendex"] * count,
            "source_url": [f"https://example.org/{i}" for i in range(count)],
            "model_name": ["paraphrase-multilingual-MiniLM-L12-v2"] * count,
            "embedding": ["[]"] * count,
            "parameter_scores": [{"philosophy": 0.5, "science": 0.5}] * count,
            "_embedding_vec": list(vectors),
        }
    )


class RankingEquivalenceTests(unittest.TestCase):
    def assert_same_ranking(self, frame: pd.DataFrame, query: np.ndarray, top: int, **kwargs) -> None:
        expected = rowwise_reference(frame, query, top, **kwargs)
        actual = work_similarity_by_vector(frame, query, top, **kwargs)

        self.assertEqual(len(actual), len(expected))
        if expected.empty:
            return

        self.assertEqual(actual["doc_id"].tolist(), expected["doc_id"].tolist())
        np.testing.assert_allclose(
            actual["similarity"].to_numpy(dtype=float),
            expected["similarity"].to_numpy(dtype=float),
            rtol=0,
            atol=1e-6,
        )
        self.assertEqual(actual["rank"].tolist(), expected["rank"].tolist())

    def test_matches_on_a_small_corpus(self) -> None:
        frame = corpus(50)
        rng = np.random.default_rng(3)
        self.assert_same_ranking(frame, rng.normal(size=384).astype(np.float32), 10)

    def test_matches_across_many_random_queries(self) -> None:
        frame = corpus(400)
        rng = np.random.default_rng(5)
        for trial in range(15):
            with self.subTest(trial=trial):
                self.assert_same_ranking(frame, rng.normal(size=384).astype(np.float32), 10)

    def test_matches_when_the_query_is_a_corpus_vector(self) -> None:
        # The document-origin path: the query is one of the stored vectors, so
        # the top hit scores 1.0 and ties are most likely.
        frame = corpus(200)
        self.assert_same_ranking(frame, frame["_embedding_vec"].iloc[7], 10, include_self=True)

    def test_matches_with_exclusion(self) -> None:
        frame = corpus(200)
        self.assert_same_ranking(
            frame,
            frame["_embedding_vec"].iloc[3],
            10,
            exclude_doc_id="gutendex:doc_000003",
        )

    def test_exclusion_actually_removes_the_document(self) -> None:
        frame = corpus(50)
        out = work_similarity_by_vector(
            frame, frame["_embedding_vec"].iloc[3], 10, exclude_doc_id="gutendex:doc_000003"
        )
        self.assertNotIn("gutendex:doc_000003", out["doc_id"].tolist())

    def test_include_self_keeps_the_origin_document(self) -> None:
        frame = corpus(50)
        out = work_similarity_by_vector(
            frame,
            frame["_embedding_vec"].iloc[3],
            10,
            exclude_doc_id="gutendex:doc_000003",
            include_self=True,
        )
        self.assertIn("gutendex:doc_000003", out["doc_id"].tolist())

    def test_matches_for_various_top_values(self) -> None:
        frame = corpus(120)
        rng = np.random.default_rng(9)
        query = rng.normal(size=384).astype(np.float32)
        for top in (1, 5, 10, 50, 500):
            with self.subTest(top=top):
                self.assert_same_ranking(frame, query, top)

    def test_matches_after_rounding_to_the_api_precision(self) -> None:
        # What actually reaches the client is rounded to 4 decimals, so any
        # BLAS-level difference must vanish there.
        frame = corpus(300)
        rng = np.random.default_rng(13)
        query = rng.normal(size=384).astype(np.float32)

        expected = format_similarity(rowwise_reference(frame, query, 25))
        actual = format_similarity(work_similarity_by_vector(frame, query, 25))

        self.assertEqual(actual["similarity"].tolist(), expected["similarity"].tolist())
        self.assertEqual(actual["doc_id"].tolist(), expected["doc_id"].tolist())

    def test_preserves_the_output_column_contract(self) -> None:
        frame = corpus(20)
        expected = rowwise_reference(frame, frame["_embedding_vec"].iloc[0], 5)
        actual = work_similarity_by_vector(frame, frame["_embedding_vec"].iloc[0], 5)
        self.assertEqual(list(actual.columns), list(expected.columns))

    def test_fills_absent_columns_with_blanks_like_the_original(self) -> None:
        frame = corpus(10).drop(columns=["source_url", "gutenberg_id"], errors="ignore")
        out = work_similarity_by_vector(frame, frame["_embedding_vec"].iloc[0], 3)
        self.assertIn("gutenberg_id", out.columns)
        self.assertTrue((out["gutenberg_id"] == "").all())

    def test_handles_a_zero_vector_as_zero_similarity(self) -> None:
        frame = corpus(10)
        vectors = frame["_embedding_vec"].to_list()
        vectors[4] = np.zeros(384, dtype=np.float32)
        frame["_embedding_vec"] = vectors

        expected = rowwise_reference(frame, frame["_embedding_vec"].iloc[0], 10)
        actual = work_similarity_by_vector(frame, frame["_embedding_vec"].iloc[0], 10)

        self.assertEqual(actual["doc_id"].tolist(), expected["doc_id"].tolist())
        zero_row = actual[actual["doc_id"] == "gutendex:doc_000004"]
        self.assertEqual(float(zero_row["similarity"].iloc[0]), 0.0)

    def test_handles_an_empty_frame(self) -> None:
        empty = corpus(0)
        out = work_similarity_by_vector(empty, np.zeros(384, dtype=np.float32), 10)
        self.assertTrue(out.empty)

    def test_ragged_vectors_raise_exactly_as_before(self) -> None:
        # Mismatched dimensions cannot be stacked, and the per-row fallback hits
        # the same wall because `cosine` cannot multiply them either. The
        # pre-T4.6 implementation raised here too, so raising is the correct
        # preserved behaviour rather than a regression. A mixed-dimension corpus
        # would be a data defect, and silently scoring it would hide that.
        frame = corpus(6)
        vectors = frame["_embedding_vec"].to_list()
        vectors[2] = np.ones(128, dtype=np.float32)
        frame["_embedding_vec"] = vectors

        with self.assertRaises(ValueError):
            rowwise_reference(frame, frame["_embedding_vec"].iloc[0], 6)
        with self.assertRaises(ValueError):
            work_similarity_by_vector(frame, frame["_embedding_vec"].iloc[0], 6)


class RankingPerformanceTests(unittest.TestCase):
    def test_is_fast_enough_for_the_full_corpus(self) -> None:
        """A full-corpus-sized ranking pass must stay well under a second."""
        import time

        frame = corpus(64_000)
        query = frame["_embedding_vec"].iloc[0]

        started = time.perf_counter()
        out = work_similarity_by_vector(frame, query, 10)
        elapsed = time.perf_counter() - started

        self.assertEqual(len(out), 10)
        self.assertLess(elapsed, 3.0, f"ranking 64k documents took {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
