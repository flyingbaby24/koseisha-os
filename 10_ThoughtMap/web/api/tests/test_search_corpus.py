"""The corpus matrix must stay aligned with its frame, or ranking is nonsense.

Every test here is about one hazard: a row of the matrix ceasing to be the row
of the frame it claims to be. That failure produces confident, plausible,
completely wrong results, so the guarantees are pinned rather than trusted
(T7 §11-§12).
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from api.search_corpus import SearchCorpus, build_search_corpus, strip_internal_columns
from search_utils import (
    MATRIX_ROW_COLUMN,
    apply_metadata_filter,
    cosine_against_matrix,
    prepared_vectors,
    subset_positions,
    work_similarity_by_vector,
)


def frame_of(count: int, dimension: int = 4, sources: list[str] | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    vectors = [
        np.asarray(rng.standard_normal(dimension), dtype=np.float32) for _ in range(count)
    ]
    return pd.DataFrame(
        {
            "doc_id": [f"doc_{i:04d}" for i in range(count)],
            "title": [f"Title {i}" for i in range(count)],
            "source": (sources or ["gutendex"] * count),
            "_embedding_vec": vectors,
        }
    )


class BuildTests(unittest.TestCase):
    def test_matrix_matches_a_fresh_stack(self) -> None:
        frame = frame_of(20)
        corpus = build_search_corpus(frame)
        expected = np.stack(frame["_embedding_vec"].to_list()).astype(np.float32)
        self.assertTrue(np.array_equal(corpus.matrix, expected))

    def test_matrix_is_float32_and_contiguous(self) -> None:
        # The ranking path hands this straight to BLAS; a non-contiguous or
        # float64 array would silently copy or change the arithmetic.
        corpus = build_search_corpus(frame_of(10))
        self.assertEqual(corpus.matrix.dtype, np.float32)
        self.assertTrue(corpus.matrix.flags["C_CONTIGUOUS"])

    def test_norms_match_a_fresh_computation(self) -> None:
        corpus = build_search_corpus(frame_of(15))
        self.assertTrue(
            np.array_equal(corpus.norms, np.linalg.norm(corpus.matrix, axis=1))
        )

    def test_every_row_is_stamped_with_its_position(self) -> None:
        corpus = build_search_corpus(frame_of(12))
        self.assertTrue(
            np.array_equal(
                corpus.frame[MATRIX_ROW_COLUMN].to_numpy(), np.arange(12)
            )
        )

    def test_vectors_become_views_into_the_matrix(self) -> None:
        # Otherwise the corpus costs a second full copy of the embeddings.
        corpus = build_search_corpus(frame_of(8))
        self.assertIs(corpus.frame["_embedding_vec"].iloc[0].base, corpus.matrix)

    def test_an_empty_frame_is_not_an_error(self) -> None:
        corpus = build_search_corpus(pd.DataFrame())
        self.assertEqual(corpus.document_count, 0)
        self.assertEqual(corpus.matrix.size, 0)

    def test_ragged_vectors_produce_no_matrix(self) -> None:
        # A data defect. Stacking a partial set would be worse than not
        # stacking: the per-row fallback still handles it correctly.
        frame = frame_of(5)
        frame.at[2, "_embedding_vec"] = np.zeros(3, dtype=np.float32)
        corpus = build_search_corpus(frame)
        self.assertEqual(corpus.matrix.size, 0)

    def test_misaligned_construction_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            SearchCorpus(
                frame=frame_of(5),
                matrix=np.zeros((4, 4), dtype=np.float32),
                norms=np.zeros(4),
            )

    def test_norms_length_is_checked(self) -> None:
        with self.assertRaises(ValueError):
            SearchCorpus(
                frame=frame_of(4),
                matrix=np.zeros((4, 4), dtype=np.float32),
                norms=np.zeros(3),
            )

    def test_reports_its_shape(self) -> None:
        corpus = build_search_corpus(frame_of(6, dimension=8))
        self.assertEqual(corpus.document_count, 6)
        self.assertEqual(corpus.dimension, 8)
        self.assertEqual(corpus.matrix_bytes, 6 * 8 * 4)


class PositionTests(unittest.TestCase):
    def test_positions_of_the_whole_corpus(self) -> None:
        corpus = build_search_corpus(frame_of(10))
        self.assertTrue(
            np.array_equal(subset_positions(corpus.frame, 10), np.arange(10))
        )

    def test_positions_survive_a_filter_that_resets_the_index(self) -> None:
        # The bug this exists to prevent: `apply_metadata_filter` ends with
        # `reset_index(drop=True)`, so index labels become 0..N-1 of the
        # subset. A label-based scheme would index the matrix with those and
        # rank entirely the wrong documents.
        sources = ["gutendex"] * 5 + ["user_note"] * 5
        corpus = build_search_corpus(frame_of(10, sources=sources))
        subset = apply_metadata_filter(corpus.frame, "source", "user_note")

        self.assertTrue(np.array_equal(subset.index.to_numpy(), np.arange(5)))
        self.assertTrue(
            np.array_equal(subset_positions(subset, 10), np.arange(5, 10)),
            "positions must point at the original rows, not the subset's",
        )

    def test_a_frame_without_the_column_is_refused(self) -> None:
        frame = frame_of(5).drop(columns=[], errors="ignore")
        self.assertIsNone(subset_positions(frame, 5))

    def test_out_of_range_positions_are_refused(self) -> None:
        corpus = build_search_corpus(frame_of(5))
        frame = corpus.frame.copy()
        frame[MATRIX_ROW_COLUMN] = np.arange(100, 105)
        self.assertIsNone(subset_positions(frame, 5))

    def test_prepared_vectors_reuses_the_matrix_when_unfiltered(self) -> None:
        corpus = build_search_corpus(frame_of(10))
        matrix, norms = prepared_vectors(corpus.frame, corpus)
        self.assertIs(matrix, corpus.matrix)
        self.assertIs(norms, corpus.norms)

    def test_prepared_vectors_slices_when_filtered(self) -> None:
        sources = ["gutendex"] * 5 + ["user_note"] * 5
        corpus = build_search_corpus(frame_of(10, sources=sources))
        subset = apply_metadata_filter(corpus.frame, "source", "user_note")

        matrix, norms = prepared_vectors(subset, corpus)
        self.assertEqual(len(matrix), 5)
        self.assertTrue(np.array_equal(matrix, corpus.matrix[5:]))
        # Recomputed over the subset rather than sliced from the full norms.
        self.assertTrue(np.array_equal(norms, np.linalg.norm(matrix, axis=1)))

    def test_prepared_vectors_declines_without_a_corpus(self) -> None:
        self.assertEqual(prepared_vectors(frame_of(3), None), (None, None))


class RankingEquivalenceTests(unittest.TestCase):
    def test_scores_are_identical_with_and_without_a_corpus(self) -> None:
        corpus = build_search_corpus(frame_of(50))
        target = np.asarray(np.random.default_rng(3).standard_normal(4), dtype=np.float32)

        fast = cosine_against_matrix([], target, corpus.matrix, corpus.norms)
        slow = cosine_against_matrix(corpus.frame["_embedding_vec"].to_list(), target)
        self.assertTrue(np.array_equal(fast, slow))

    def test_ranking_is_identical_with_and_without_a_corpus(self) -> None:
        corpus = build_search_corpus(frame_of(60))
        target = np.asarray(np.random.default_rng(11).standard_normal(4), dtype=np.float32)

        fast = work_similarity_by_vector(
            corpus.frame, target_vec=target, top=15, include_self=True, corpus=corpus
        )
        slow = work_similarity_by_vector(
            corpus.frame, target_vec=target, top=15, include_self=True, corpus=None
        )
        self.assertEqual(list(fast["doc_id"]), list(slow["doc_id"]))
        self.assertTrue(
            np.array_equal(fast["similarity"].to_numpy(), slow["similarity"].to_numpy())
        )

    def test_filtered_ranking_returns_only_the_filtered_rows(self) -> None:
        sources = ["gutendex"] * 30 + ["user_note"] * 30
        corpus = build_search_corpus(frame_of(60, sources=sources))
        subset = apply_metadata_filter(corpus.frame, "source", "user_note")
        target = np.asarray(np.random.default_rng(5).standard_normal(4), dtype=np.float32)

        ranked = work_similarity_by_vector(
            subset, target_vec=target, top=10, include_self=True, corpus=corpus
        )
        self.assertTrue((ranked["source"] == "user_note").all())

        slow = work_similarity_by_vector(
            subset, target_vec=target, top=10, include_self=True, corpus=None
        )
        self.assertEqual(list(ranked["doc_id"]), list(slow["doc_id"]))

    def test_exclusion_still_applies_with_a_corpus(self) -> None:
        corpus = build_search_corpus(frame_of(20))
        target = np.asarray(corpus.matrix[3], dtype=np.float32)

        ranked = work_similarity_by_vector(
            corpus.frame,
            target_vec=target,
            top=10,
            exclude_doc_id="doc_0003",
            include_self=False,
            corpus=corpus,
        )
        self.assertNotIn("doc_0003", list(ranked["doc_id"]))

    def test_ragged_fallback_still_works_with_a_corpus_present(self) -> None:
        # The corpus refuses to build a matrix for ragged input; ranking must
        # still produce an answer rather than raising.
        frame = frame_of(6)
        frame.at[1, "_embedding_vec"] = np.zeros(2, dtype=np.float32)
        corpus = build_search_corpus(frame)

        ranked = work_similarity_by_vector(
            frame,
            target_vec=np.zeros(4, dtype=np.float32),
            top=3,
            include_self=True,
            corpus=corpus,
        )
        self.assertLessEqual(len(ranked), 3)


class InternalColumnTests(unittest.TestCase):
    def test_internal_columns_can_be_stripped(self) -> None:
        corpus = build_search_corpus(frame_of(4))
        cleaned = strip_internal_columns(corpus.frame)
        self.assertNotIn(MATRIX_ROW_COLUMN, cleaned.columns)
        self.assertNotIn("_embedding_vec", cleaned.columns)

    def test_stripping_is_safe_on_a_plain_frame(self) -> None:
        frame = pd.DataFrame({"doc_id": ["a"]})
        self.assertEqual(list(strip_internal_columns(frame).columns), ["doc_id"])


if __name__ == "__main__":
    unittest.main()
