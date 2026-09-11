"""Contract tests for the public /search modes restored in phase T1.5.

These cover the HTTP contract in docs/api_contract.md: `semantic`, `keyword`,
and `hybrid` all work from query text alone, and `query_parameters` is
populated. A deterministic fake encoder stands in for sentence-transformers so
the suite stays fast and does not require torch; the real model is exercised by
the live API smoke test recorded in docs/threejs-migration-plan.md.
"""

from __future__ import annotations

import hashlib
import unittest
from unittest import mock

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api import main as api_main
from api.embedding_model import EmbeddingModelUnavailableError
from api.query_profile import QueryProfileService
from api.schemas import SearchResponse
from api.search_service import ThoughtMapSearchService


# Terms the fake encoder understands. Overlap dominates the vector, so
# similarity rankings in these tests are predictable.
VOCAB = (
    "philosophy",
    "justice",
    "music",
    "science",
    "love",
    "war",
    "law",
    "mind",
    "economy",
    "community",
)


def fake_vector(text: str) -> np.ndarray:
    """Deterministic embedding: vocabulary overlap plus stable tie-break noise.

    Uses sha256 rather than hash() because Python randomises str hashing per
    process, which would make "identical query gives identical profile" pass or
    fail depending on the run.
    """
    lowered = str(text).lower()
    base = np.array([1.0 if term in lowered else 0.0 for term in VOCAB], dtype=np.float32)
    digest = hashlib.sha256(lowered.encode("utf-8")).digest()
    noise = np.frombuffer(digest[: len(VOCAB)], dtype=np.uint8).astype(np.float32) / 2550.0
    return base + noise


class FakeEncoder:
    def __init__(self) -> None:
        self.calls = 0

    def encode(self, sentences, show_progress_bar: bool = False):
        self.calls += 1
        return np.stack([fake_vector(text) for text in sentences])


DOCUMENTS = [
    {
        "doc_id": "gutendex:doc_000001",
        "title": "The Republic",
        "author": "Plato",
        "source": "gutendex",
        "source_url": "https://www.gutenberg.org/ebooks/1497",
        "_text": "philosophy justice law",
        "parameter_scores": {"philosophy": 0.6, "morality": 0.4},
    },
    {
        "doc_id": "gutendex:doc_000002",
        "title": "Elements of Political Economy",
        "author": "James Mill",
        "source": "gutendex",
        "source_url": "",
        "_text": "economy law community",
        "parameter_scores": {"economics": 0.7, "community": 0.3},
    },
    {
        "doc_id": "user_suno:doc_000003",
        "title": "Burn",
        "author": "Unknown",
        "source": "user_suno",
        "source_url": "",
        "_text": "love music war",
        "parameter_scores": {"emotion": 0.9, "philosophy": 0.1},
    },
    {
        "doc_id": "user_note:doc_000004",
        "title": "Notes on Mind",
        "author": "Anonymous",
        "source": "user_note",
        "source_url": "",
        "_text": "mind science",
        "parameter_scores": {"psychology": 0.5, "science": 0.5},
    },
]


def build_index() -> pd.DataFrame:
    frame = pd.DataFrame(DOCUMENTS)
    frame["_embedding_vec"] = frame["_text"].map(fake_vector)
    frame["embedding"] = frame["_embedding_vec"].map(lambda vec: str(list(map(float, vec))))
    frame["category"] = ""
    return frame


class FakeRepository:
    def __init__(self, frame: pd.DataFrame | None = None) -> None:
        self.frame = build_index() if frame is None else frame

    def load_index(self) -> pd.DataFrame:
        return self.frame


def build_service(encoder: FakeEncoder | None = None) -> ThoughtMapSearchService:
    encoder = encoder or FakeEncoder()
    loader = lambda: encoder
    return ThoughtMapSearchService(
        repository=FakeRepository(),
        model_name="fake-model",
        model_loader=loader,
        # The real filter definitions, so the canonical parameter keys are
        # asserted rather than a set invented by the test.
        query_profile_service=QueryProfileService(loader),
    )


class SearchModeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = build_service()

    def test_keyword_mode_matches_metadata(self) -> None:
        results = self.service.search(query="Plato", mode="keyword", top=10)
        self.assertTrue(results)
        self.assertEqual(results[0].author, "Plato")

    def test_semantic_mode_needs_no_target_doc_id(self) -> None:
        results = self.service.search(query="philosophy justice", mode="semantic", top=10)
        self.assertTrue(results)
        self.assertEqual(results[0].doc_id, "gutendex:doc_000001")

    def test_semantic_is_an_alias_for_the_internal_embedding_mode(self) -> None:
        as_semantic = self.service.search(query="mind science", mode="semantic", top=3)
        as_embedding = self.service.search(query="mind science", mode="embedding", top=3)
        self.assertEqual(
            [item.doc_id for item in as_semantic],
            [item.doc_id for item in as_embedding],
        )

    def test_semantic_ranks_every_document_not_only_keyword_matches(self) -> None:
        results = self.service.search(query="philosophy", mode="semantic", top=50)
        self.assertEqual(len(results), len(DOCUMENTS))

    def test_hybrid_mode_needs_no_target_doc_id(self) -> None:
        results = self.service.search(query="law", mode="hybrid", top=10)
        self.assertTrue(results)

    def test_hybrid_prefers_keyword_matches(self) -> None:
        # "Burn" only matches doc 3 by title; hybrid restricts to keyword hits.
        results = self.service.search(query="Burn", mode="hybrid", top=10)
        self.assertEqual([item.doc_id for item in results], ["user_suno:doc_000003"])

    def test_hybrid_falls_back_to_semantic_when_nothing_matches_by_keyword(self) -> None:
        # No metadata contains this word, so the keyword candidate set is empty.
        results = self.service.search(query="philosophy justice", mode="hybrid", top=10)
        self.assertTrue(results)
        self.assertEqual(results[0].doc_id, "gutendex:doc_000001")

    def test_hybrid_blend_uses_existing_weights(self) -> None:
        # "gutendex" matches the source column of two documents, so this
        # exercises the blend rather than the empty-candidate fallback.
        query = "gutendex"
        hybrid = self.service.search(query=query, mode="hybrid", top=10)
        blended = {item.doc_id: item.similarity for item in hybrid}
        self.assertGreaterEqual(len(blended), 2, "expected the keyword-candidate blend path")

        index = build_index()
        query_vec = fake_vector(query)
        for doc_id, actual in blended.items():
            with self.subTest(doc_id=doc_id):
                match = index[index["doc_id"] == doc_id].iloc[0]
                vec = match["_embedding_vec"]
                cosine = float(
                    np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec))
                )
                keyword = self.service._keyword_score(match, query)
                expected = round(cosine, 4) * 0.8 + keyword * 0.2
                self.assertAlmostEqual(actual, expected, places=6)

    def test_hybrid_fallback_returns_unblended_similarity(self) -> None:
        # No metadata column contains "philosophy", so hybrid falls back to
        # pure semantic ranking and similarity is the raw cosine.
        query = "philosophy"
        results = self.service.search(query=query, mode="hybrid", top=10)
        self.assertEqual(len(results), len(DOCUMENTS))

        index = build_index()
        query_vec = fake_vector(query)
        top = results[0]
        vec = index[index["doc_id"] == top.doc_id].iloc[0]["_embedding_vec"]
        cosine = float(np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec)))
        self.assertAlmostEqual(top.similarity, round(cosine, 4), places=6)

    def test_target_doc_id_path_is_preserved(self) -> None:
        results = self.service.search(
            query="",
            mode="semantic",
            target_doc_id="gutendex:doc_000001",
            top=10,
        )
        self.assertTrue(results)
        # Document-origin similarity excludes the origin document itself.
        self.assertNotIn("gutendex:doc_000001", [item.doc_id for item in results])

    def test_unsupported_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.service.search(query="Plato", mode="telepathy")

    def test_empty_query_returns_no_keyword_results(self) -> None:
        self.assertEqual(self.service.search(query="   ", mode="keyword"), [])

    def test_empty_query_without_target_is_rejected_for_vector_modes(self) -> None:
        for mode in ("semantic", "hybrid"):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    self.service.search(query="   ", mode=mode)


class SearchFilterContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = build_service()

    def test_top_limits_results_in_every_mode(self) -> None:
        for mode in ("keyword", "semantic", "hybrid"):
            with self.subTest(mode=mode):
                results = self.service.search(query="law", mode=mode, top=1)
                self.assertLessEqual(len(results), 1)

    def test_source_filter_applies_in_every_mode(self) -> None:
        for mode in ("keyword", "semantic", "hybrid"):
            with self.subTest(mode=mode):
                results = self.service.search(query="law", mode=mode, source="user_suno", top=10)
                self.assertTrue(all(item.source == "user_suno" for item in results))

    def test_source_filter_with_no_matches_returns_empty(self) -> None:
        results = self.service.search(query="law", mode="semantic", source="nonexistent", top=10)
        self.assertEqual(results, [])

    def test_response_schema_is_stable(self) -> None:
        response = self.service.search_response("Plato", mode="semantic", top=2)
        self.assertIsInstance(response, SearchResponse)

        payload = response.model_dump()
        self.assertEqual(set(payload), {"results", "query_parameters"})

        for result in payload["results"]:
            self.assertEqual(
                set(result),
                {"doc_id", "title", "author", "source", "similarity", "url", "parameters"},
            )
            self.assertIsInstance(result["doc_id"], str)
            self.assertIsInstance(result["similarity"], float)

    def test_result_url_resolution_is_preserved(self) -> None:
        results = self.service.search(query="Republic", mode="keyword", top=1)
        self.assertEqual(results[0].url, "https://www.gutenberg.org/ebooks/1497")


class QueryParameterContractTests(unittest.TestCase):
    """Canonical scale: a Thought Composition, ten values in 0..1 summing to 1."""

    EXPECTED_KEYS = [
        "philosophy",
        "psychology",
        "science",
        "economics",
        "karma",
        "emotion",
        "morality",
        "ideal",
        "individual",
        "community",
    ]

    def setUp(self) -> None:
        self.service = build_service()

    def test_query_parameters_are_populated_for_a_normal_query(self) -> None:
        response = self.service.search_response("Plato", mode="keyword", top=3)
        self.assertIsNotNone(response.query_parameters)
        self.assertTrue(response.query_parameters)

    def test_query_parameters_use_the_canonical_keys(self) -> None:
        scores = self.service.query_parameters("Plato")
        assert scores is not None
        self.assertEqual([score.key for score in scores], self.EXPECTED_KEYS)

    def test_query_parameter_values_are_finite_and_in_range(self) -> None:
        scores = self.service.query_parameters("justice and the good life")
        assert scores is not None
        for score in scores:
            with self.subTest(key=score.key):
                self.assertTrue(np.isfinite(score.value))
                self.assertGreaterEqual(score.value, 0.0)
                self.assertLessEqual(score.value, 1.0)

    def test_query_parameters_form_a_composition_summing_to_one(self) -> None:
        scores = self.service.query_parameters("justice and the good life")
        assert scores is not None
        self.assertAlmostEqual(sum(score.value for score in scores), 1.0, places=5)

    def test_query_parameters_are_deterministic_for_the_same_query(self) -> None:
        first = self.service.query_parameters("Plato")
        second = self.service.query_parameters("Plato")
        assert first is not None and second is not None
        self.assertEqual([s.key for s in first], [s.key for s in second])
        for a, b in zip(first, second):
            self.assertAlmostEqual(a.value, b.value, places=9)

    def test_empty_query_has_no_profile(self) -> None:
        self.assertIsNone(self.service.query_parameters("   "))

    def test_missing_model_degrades_to_no_profile_rather_than_failing(self) -> None:
        def unavailable():
            raise EmbeddingModelUnavailableError("sentence-transformers is not installed")

        service = ThoughtMapSearchService(
            repository=FakeRepository(),
            model_name="fake-model",
            model_loader=unavailable,
            query_profile_service=QueryProfileService(unavailable),
        )

        self.assertIsNone(service.query_parameters("Plato"))
        # Keyword search must keep working on a deployment without the model.
        self.assertTrue(service.search(query="Plato", mode="keyword", top=3))


class SearchHttpContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = build_service()
        patcher = mock.patch.object(api_main, "get_search_service", return_value=self.service)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(api_main.app)

    def test_all_three_public_modes_return_200(self) -> None:
        for mode in ("keyword", "semantic", "hybrid"):
            with self.subTest(mode=mode):
                response = self.client.get("/search", params={"q": "Plato", "mode": mode})
                self.assertEqual(response.status_code, 200)

    def test_public_modes_return_ranked_results_not_placeholders(self) -> None:
        for mode in ("keyword", "semantic", "hybrid"):
            with self.subTest(mode=mode):
                payload = self.client.get(
                    "/search", params={"q": "Plato", "mode": mode}
                ).json()
                self.assertTrue(payload["results"])
                similarities = [item["similarity"] for item in payload["results"]]
                self.assertEqual(similarities, sorted(similarities, reverse=True))

    def test_response_includes_query_parameters(self) -> None:
        payload = self.client.get("/search", params={"q": "Plato", "mode": "semantic"}).json()
        self.assertIn("query_parameters", payload)
        self.assertEqual(len(payload["query_parameters"]), 10)

    def test_default_mode_is_semantic_and_succeeds(self) -> None:
        response = self.client.get("/search", params={"q": "Plato"})
        self.assertEqual(response.status_code, 200)

    def test_unsupported_mode_is_rejected_by_the_route(self) -> None:
        response = self.client.get("/search", params={"q": "Plato", "mode": "telepathy"})
        self.assertEqual(response.status_code, 422)

    def test_missing_or_empty_query_is_rejected(self) -> None:
        self.assertEqual(self.client.get("/search").status_code, 422)
        self.assertEqual(self.client.get("/search", params={"q": ""}).status_code, 422)

    def test_out_of_range_top_is_rejected(self) -> None:
        self.assertEqual(
            self.client.get("/search", params={"q": "Plato", "top": 0}).status_code, 422
        )
        self.assertEqual(
            self.client.get("/search", params={"q": "Plato", "top": 51}).status_code, 422
        )

    def test_whitespace_query_without_target_is_a_client_error(self) -> None:
        response = self.client.get("/search", params={"q": "   ", "mode": "semantic"})
        self.assertEqual(response.status_code, 400)

    def test_missing_embedding_model_reports_503(self) -> None:
        def unavailable():
            raise EmbeddingModelUnavailableError("sentence-transformers is not installed")

        service = ThoughtMapSearchService(
            repository=FakeRepository(),
            model_name="fake-model",
            model_loader=unavailable,
            query_profile_service=QueryProfileService(unavailable),
        )

        with mock.patch.object(api_main, "get_search_service", return_value=service):
            response = self.client.get("/search", params={"q": "Plato", "mode": "semantic"})

        self.assertEqual(response.status_code, 503)

    def test_source_and_top_are_honoured_over_http(self) -> None:
        payload = self.client.get(
            "/search",
            params={"q": "law", "mode": "semantic", "source": "gutendex", "top": 1},
        ).json()
        self.assertLessEqual(len(payload["results"]), 1)
        self.assertTrue(all(item["source"] == "gutendex" for item in payload["results"]))


if __name__ == "__main__":
    unittest.main()
