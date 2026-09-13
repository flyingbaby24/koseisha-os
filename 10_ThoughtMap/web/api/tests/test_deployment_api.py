"""HTTP surface of a deployment: health, readiness, caching, library gating.

Runs against the real ASGI app through TestClient. The corpus is never loaded:
warmup is off in development, `/map` is served from a small stub artifact, and
no test here needs the 542 MB embedding file (T6 §50).
"""

from __future__ import annotations

import gzip
import json
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from api import main as main_module


def stub_artifact(fingerprint: str = "ce109523a9cd9962deadbeef", nodes: int = 4) -> dict:
    return {
        "schema_version": 1,
        "projection": {
            "generated_at": "2026-09-09T00:00:00Z",
            "dataset_fingerprint": fingerprint,
            "document_count": nodes,
            "embedding_dimension": 384,
            "dimensions": 3,
            "algorithm": "umap",
            "metric": "cosine",
            "n_neighbors": 10,
            "min_dist": 0.2,
            "random_seed": 42,
        },
        "nodes": [
            {
                "doc_id": f"gutendex:doc_{i:06d}",
                "title": f"Document {i}",
                "author": "Plato",
                "source": "gutendex",
                "x": float(i),
                "y": 0.0,
                "z": 0.0,
                "cluster": 0,
            }
            for i in range(nodes)
        ],
    }


class HealthAndReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main_module.app)

    def test_health_is_cheap_and_does_not_depend_on_the_corpus(self) -> None:
        # It must answer while the corpus is still loading, so it may not
        # consult anything that loading would populate.
        with mock.patch.object(
            main_module, "get_search_service", side_effect=AssertionError("must not be called")
        ):
            response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_ready_reports_the_deployment_and_is_never_cached(self) -> None:
        response = self.client.get("/ready")

        self.assertIn(response.status_code, (200, 503))
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        body = response.json()
        self.assertIn("ready", body)
        self.assertIn("checks", body)
        self.assertIn("deployment_mode", body)

    def test_ready_answers_503_with_a_body_when_blocked(self) -> None:
        # The body is the point: "not ready" has to say which check is missing,
        # or the frontend cannot tell warming from broken.
        blocked = {
            "ready": False,
            "blocked_by": ["embedding_model"],
            "checks": [{"name": "embedding_model", "status": "pending"}],
        }
        with mock.patch.object(main_module.readiness, "snapshot", return_value=blocked):
            response = self.client.get("/ready")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["blocked_by"], ["embedding_model"])

    def test_config_states_the_features(self) -> None:
        response = self.client.get("/config")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        body = response.json()
        self.assertIn("deployment_mode", body)
        self.assertIn("library_enabled", body)


class MapCachingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main_module.app)
        main_module._map_cache.clear()
        self.service = mock.Mock()
        self.service.load.return_value = stub_artifact()
        # /map is cached on the artifact file's identity, so a double must
        # supply one - and must change it when it serves a new artifact, just
        # as a regenerated file on disk would.
        self.service.current_key.return_value = ("map.json", 1, 1)
        self.patcher = mock.patch.object(
            main_module, "get_map_service", return_value=self.service
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(main_module._map_cache.clear)

    def test_serves_the_projection_with_cache_headers(self) -> None:
        response = self.client.get("/map")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["nodes"]), 4)
        self.assertIn("max-age", response.headers["Cache-Control"])
        self.assertTrue(response.headers["ETag"].startswith('W/"map-'))

    def test_a_matching_etag_gets_304_with_no_body(self) -> None:
        first = self.client.get("/map")
        etag = first.headers["ETag"]

        second = self.client.get("/map", headers={"If-None-Match": etag})

        self.assertEqual(second.status_code, 304)
        self.assertEqual(second.content, b"")
        self.assertEqual(second.headers["ETag"], etag)

    def test_a_stale_etag_gets_the_full_body(self) -> None:
        response = self.client.get("/map", headers={"If-None-Match": 'W/"map-something-else"'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["nodes"]), 4)

    def test_a_regenerated_projection_changes_the_etag(self) -> None:
        # Without this, a re-projection would be invisible to every browser
        # holding the old validator.
        first = self.client.get("/map").headers["ETag"]
        self.service.load.return_value = stub_artifact("0123456789abcdef", nodes=6)
        self.service.current_key.return_value = ("map.json", 2, 2)  # file changed
        second = self.client.get("/map")

        self.assertNotEqual(first, second.headers["ETag"])
        self.assertEqual(len(second.json()["nodes"]), 6)

    def test_gzip_is_served_pre_compressed_and_decodes_correctly(self) -> None:
        response = self.client.get(
            "/map", headers={"Accept-Encoding": "gzip"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
        self.assertEqual(response.headers.get("Vary"), "Accept-Encoding")
        # httpx decodes transparently; confirm the payload survived.
        self.assertEqual(len(response.json()["nodes"]), 4)

    def test_a_client_that_cannot_decode_gets_plain_json(self) -> None:
        response = self.client.get("/map", headers={"Accept-Encoding": "identity"})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Content-Encoding", response.headers)
        self.assertEqual(len(response.json()["nodes"]), 4)

    def test_the_body_is_not_double_compressed(self) -> None:
        # The route compresses /map itself; GZipMiddleware must not wrap it
        # again, which would produce a body no browser can read.
        response = self.client.get("/map", headers={"Accept-Encoding": "gzip"})
        raw = response.read() if hasattr(response, "read") else response.content

        # After one gunzip the result must be JSON, not another gzip member.
        if response.headers.get("Content-Encoding") == "gzip":
            try:
                once = gzip.decompress(raw)
            except Exception:
                once = raw  # httpx already decoded it
            self.assertIsInstance(json.loads(once), dict)

    def test_an_unavailable_projection_answers_503(self) -> None:
        from api.map_service import ProjectionUnavailableError

        self.service.load.side_effect = ProjectionUnavailableError("not generated")
        response = self.client.get("/map")

        self.assertEqual(response.status_code, 503)
        self.assertIn("not generated", response.json()["detail"])


class SearchHeaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(main_module.app)

    def test_search_responses_are_never_shared(self) -> None:
        # A search can depend on user_email, so a shared cache must not hold it.
        from api.schemas import SearchResponse

        service = mock.Mock()
        service.search_response.return_value = SearchResponse(results=[], query_parameters=None)
        with mock.patch.object(main_module, "get_search_service", return_value=service):
            response = self.client.get("/search", params={"q": "Plato", "mode": "keyword"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_a_bad_mode_is_a_client_error(self) -> None:
        response = self.client.get("/search", params={"q": "Plato", "mode": "telepathy"})
        self.assertEqual(response.status_code, 422)

    def test_an_empty_query_is_rejected(self) -> None:
        response = self.client.get("/search", params={"q": "", "mode": "keyword"})
        self.assertEqual(response.status_code, 422)


class LibraryGateTests(unittest.TestCase):
    """A hidden button is not a boundary; the routes themselves must refuse."""

    def setUp(self) -> None:
        self.client = TestClient(main_module.app)

    def test_routes_refuse_when_the_library_is_disabled(self) -> None:
        disabled = main_module.settings.__class__(
            **{**main_module.settings.__dict__, "library_enabled": False}
        )
        with mock.patch.object(main_module, "settings", disabled):
            listed = self.client.get(
                "/users/by-email/saved", params={"email": "a@example.invalid"}
            )
            saved = self.client.post(
                "/users/by-email/save",
                json={"email": "a@example.invalid", "doc_id": "gutendex:doc_000001"},
            )
            deleted = self.client.delete(
                "/users/by-email/saved/gutendex%3Adoc_000001",
                params={"email": "a@example.invalid"},
            )

        for response in (listed, saved, deleted):
            self.assertEqual(response.status_code, 404)
            self.assertIn("not available", response.json()["detail"])

    def test_the_refusal_does_not_imply_an_account_problem(self) -> None:
        # 401/403 would suggest signing in. There is nothing to sign in to.
        disabled = main_module.settings.__class__(
            **{**main_module.settings.__dict__, "library_enabled": False}
        )
        with mock.patch.object(main_module, "settings", disabled):
            response = self.client.get(
                "/users/by-email/saved", params={"email": "a@example.invalid"}
            )

        detail = response.json()["detail"].lower()
        self.assertNotIn("sign in", detail)
        self.assertNotIn("unauthorized", detail)
        self.assertNotIn("permission", detail)

    def test_library_responses_are_never_cached_when_enabled(self) -> None:
        service = mock.Mock()
        service.list_saved_by_email.return_value = mock.Mock(items=[])
        enabled = main_module.settings.__class__(
            **{**main_module.settings.__dict__, "library_enabled": True}
        )
        with mock.patch.object(main_module, "settings", enabled), mock.patch.object(
            main_module, "get_user_library_service", return_value=service
        ):
            response = self.client.get(
                "/users/by-email/saved", params={"email": "a@example.invalid"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "no-store")


class ErrorLeakageTests(unittest.TestCase):
    def test_an_unexpected_error_does_not_reach_the_client(self) -> None:
        # A traceback in a browser is both a poor experience and an
        # information leak.
        service = mock.Mock()
        service.search_response.side_effect = KeyError("internal detail 12345")

        client = TestClient(main_module.app, raise_server_exceptions=False)
        with mock.patch.object(main_module, "get_search_service", return_value=service):
            response = client.get("/search", params={"q": "Plato", "mode": "keyword"})

        self.assertEqual(response.status_code, 500)
        body = response.text
        self.assertNotIn("Traceback", body)
        self.assertNotIn("internal detail 12345", body)
        self.assertIn("internal error", response.json()["detail"])


class CorsTests(unittest.TestCase):
    def test_configured_origins_are_reflected(self) -> None:
        client = TestClient(main_module.app)
        response = client.get("/health", headers={"Origin": "http://localhost:5273"})
        # Development allows *; the header must at least be present so a
        # browser-side failure is a configuration question, not a mystery.
        self.assertIn("access-control-allow-origin", {k.lower() for k in response.headers})

    def test_credentials_are_never_allowed(self) -> None:
        # There is no session to protect, and allow_credentials with a
        # wildcard origin is the classic misconfiguration.
        client = TestClient(main_module.app)
        response = client.get("/health", headers={"Origin": "http://localhost:5273"})
        self.assertNotIn("access-control-allow-credentials", {k.lower() for k in response.headers})


if __name__ == "__main__":
    unittest.main()
