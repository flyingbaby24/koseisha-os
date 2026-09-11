"""The vectorised keyword scorer must agree with the per-row definition.

`_keyword_score` remains the single-row statement of the rule. `keyword_scores`
computes the same thing column-wise for the whole index; these tests pin them
together so the fast path can never drift from the definition.
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from api.search_service import ThoughtMapSearchService


class FakeRepository:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame

    def load_index(self) -> pd.DataFrame:
        return self.frame


def service_for(frame: pd.DataFrame) -> ThoughtMapSearchService:
    return ThoughtMapSearchService(repository=FakeRepository(frame), model_name="fake")


def sample_index() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"doc_id": "gutendex:doc_000001", "title": "The Republic of Plato", "author": "Plato",
             "source": "gutendex", "source_url": "https://gutenberg.org/1", "category": "philosophy",
             "subcategory": "", "tags": "", "notes": ""},
            {"doc_id": "gutendex:doc_000002", "title": "Plato", "author": "Anonymous",
             "source": "gutendex", "source_url": "", "category": "", "subcategory": "",
             "tags": "", "notes": ""},
            {"doc_id": "user_suno:doc_000003", "title": "Love and War", "author": "Someone",
             "source": "user_suno", "source_url": "", "category": "music", "subcategory": "",
             "tags": "", "notes": "a song about plato and love"},
            {"doc_id": "zip:doc_000004", "title": "Unrelated", "author": "Nobody",
             "source": "zip", "source_url": "", "category": "", "subcategory": "",
             "tags": "", "notes": ""},
            {"doc_id": "user_note:doc_000005", "title": "", "author": "",
             "source": "user_note", "source_url": "", "category": "", "subcategory": "",
             "tags": "", "notes": ""},
        ]
    )


class KeywordEquivalenceTests(unittest.TestCase):
    def assert_matches(self, frame: pd.DataFrame, query: str) -> None:
        service = service_for(frame)
        expected = np.array(
            [service._keyword_score(row, query) for _, row in frame.iterrows()], dtype=float
        )
        actual = service.keyword_scores(frame, query)
        np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)

    def test_matches_for_an_exact_title(self) -> None:
        self.assert_matches(sample_index(), "Plato")

    def test_matches_for_a_substring(self) -> None:
        self.assert_matches(sample_index(), "republic")

    def test_matches_for_a_multi_term_query(self) -> None:
        # Hits the "all terms present" branch via the notes column.
        self.assert_matches(sample_index(), "plato love")

    def test_matches_for_a_source_query(self) -> None:
        self.assert_matches(sample_index(), "gutendex")

    def test_matches_for_a_doc_id_query(self) -> None:
        self.assert_matches(sample_index(), "gutendex:doc_000002")

    def test_matches_for_a_query_nothing_contains(self) -> None:
        self.assert_matches(sample_index(), "zzzzqqqq")

    def test_matches_for_mixed_case_and_padding(self) -> None:
        self.assert_matches(sample_index(), "  PLATO  ")

    def test_matches_for_an_empty_query(self) -> None:
        service = service_for(sample_index())
        scores = service.keyword_scores(sample_index(), "   ")
        self.assertTrue((scores == 0).all())

    def test_exact_title_outranks_a_substring_match(self) -> None:
        service = service_for(sample_index())
        scores = service.keyword_scores(sample_index(), "Plato")
        # Row 1 is exactly "Plato"; row 0 merely contains it.
        self.assertGreater(scores[1], scores[0])

    def test_matches_when_a_keyword_column_is_absent(self) -> None:
        frame = sample_index().drop(columns=["notes", "tags"])
        self.assert_matches(frame, "plato love")

    def test_matches_across_random_queries(self) -> None:
        frame = sample_index()
        for query in ("plato", "war", "love and war", "music", "nobody", "doc_000004", "the"):
            with self.subTest(query=query):
                self.assert_matches(frame, query)

    def test_is_fast_on_a_full_corpus_sized_index(self) -> None:
        import time

        size = 64_000
        frame = pd.DataFrame(
            {
                "doc_id": [f"gutendex:doc_{i:06d}" for i in range(size)],
                "title": [f"Title {i} of the work" for i in range(size)],
                "author": [f"Author {i % 5000}" for i in range(size)],
                "source": ["gutendex"] * size,
                "source_url": [""] * size,
                "category": [""] * size,
                "subcategory": [""] * size,
                "tags": [""] * size,
                "notes": [""] * size,
            }
        )
        service = service_for(frame)

        started = time.perf_counter()
        scores = service.keyword_scores(frame, "Plato")
        elapsed = time.perf_counter() - started

        self.assertEqual(len(scores), size)
        self.assertLess(elapsed, 2.0, f"keyword scoring 64k documents took {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
