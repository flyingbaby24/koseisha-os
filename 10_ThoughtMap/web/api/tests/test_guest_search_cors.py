"""Production-mode CORS against the actual API, using its fake search fixture."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api import main
from api.guest_search_cors import GuestSearchCORSMiddleware, SOT_PUBLIC_ORIGIN, install_guest_search_cors
from api.tests.test_search_contract import build_service


class ProductionGuestCORSTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(main.settings.is_public, "Run this security suite with public-demo or production settings")
        self.assertTrue(any(item.cls is GuestSearchCORSMiddleware for item in main.app.user_middleware))
        self.service = build_service()
        self.lookup = mock.patch.object(main, "get_search_service", return_value=self.service).start()
        # The CORS boundary check must not initialize a real /map workload.
        mock.patch.object(main, "get_map_service", return_value=object()).start()
        mock.patch.object(main._map_cache, "get_for", side_effect=HTTPException(503, "fixture map unavailable")).start()
        self.addCleanup(mock.patch.stopall)
        self.client = TestClient(main.app)

    def search(self, headers=None, **params):
        return self.client.get("/search", params={"q": "Plato", "mode": "keyword", **params}, headers=headers)

    def preflight(self, origin=SOT_PUBLIC_ORIGIN, method="GET", requested_headers=None, path="/search"):
        headers = {"Origin": origin, "Access-Control-Request-Method": method}
        if requested_headers is not None:
            headers["Access-Control-Request-Headers"] = requested_headers
        return self.client.options(path, headers=headers, follow_redirects=False)

    def assert_denied(self, response):
        self.assertNotIn("access-control-allow-origin", response.headers)
        self.assertNotEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_exact_origin_anonymous_get_allowed(self):
        response = self.search({"Origin": SOT_PUBLIC_ORIGIN, "Accept": "application/json"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["results"])
        self.assertEqual(response.headers["access-control-allow-origin"], SOT_PUBLIC_ORIGIN)
        self.assertEqual(response.headers["access-control-allow-credentials"], "false")
        self.assertIn("origin", response.headers["vary"].lower())
        self.assertEqual(self.lookup.call_count, 1)

    def test_get_all_existing_modes_preserve_exact_results(self):
        for mode in ("keyword", "semantic", "hybrid"):
            with self.subTest(mode=mode):
                anonymous = self.search(mode=mode)
                guest = self.search({"Origin": SOT_PUBLIC_ORIGIN}, mode=mode)
                self.assertEqual(guest.status_code, 200)
                self.assertEqual(guest.json(), anonymous.json())
                self.assertEqual(guest.headers["access-control-allow-origin"], SOT_PUBLIC_ORIGIN)

    def test_foreign_null_localhost_similar_and_wildcard_origins_denied(self):
        origins = ("https://example.com", "null", "http://localhost:5173", "http://127.0.0.1:4173",
                   "https://other.onrender.com", "https://sot-web.onrender.com.evil.test", "https://sot-web.onrender.com/", "*")
        for origin in origins:
            with self.subTest(origin=origin):
                response = self.search({"Origin": origin})
                self.assertEqual(response.status_code, 200)
                self.assert_denied(response)
                self.assertIn("origin", response.headers["vary"].lower())
                preflight = self.preflight(origin)
                self.assertEqual(preflight.status_code, 403)
                self.assert_denied(preflight)

    def test_duplicate_origin_is_never_reflected(self):
        response = self.search([("Origin", SOT_PUBLIC_ORIGIN), ("Origin", "https://example.com")])
        self.assert_denied(response)

    def test_get_preflight_only_accept_header_and_no_credentials(self):
        for requested in (None, "Accept", "accept", "accept, Accept"):
            with self.subTest(requested=requested):
                response = self.preflight(requested_headers=requested)
                self.assertEqual(response.status_code, 204)
                self.assertEqual(response.headers["access-control-allow-origin"], SOT_PUBLIC_ORIGIN)
                self.assertEqual(response.headers["access-control-allow-credentials"], "false")
                self.assertEqual(response.headers["access-control-allow-methods"], "GET, OPTIONS")
                self.assertEqual(response.headers["access-control-allow-headers"], "Accept")
                self.assertNotIn("*", response.headers["access-control-allow-origin"])
        self.assertEqual(self.lookup.call_count, 0)

    def test_mutation_preflight_methods_denied(self):
        for method in ("POST", "PATCH", "PUT", "DELETE", "HEAD"):
            with self.subTest(method=method):
                response = self.preflight(method=method)
                self.assertEqual(response.status_code, 403)
                self.assert_denied(response)
        self.assertEqual(self.lookup.call_count, 0)

    def test_unneeded_private_and_content_type_preflight_headers_denied(self):
        for header in ("Authorization", "Cookie", "Content-Type", "X-Personal-Write-Binding", "X-CSRF-Token", "X-Principal-ID", "X-Owner-ID", "Accept, Authorization"):
            with self.subTest(header=header):
                response = self.preflight(requested_headers=header)
                self.assertEqual(response.status_code, 403)
                self.assert_denied(response)
        self.assertEqual(self.lookup.call_count, 0)

    def test_credentialed_guest_get_rejected_before_search_lookup(self):
        for header in ("Authorization", "Cookie", "Proxy-Authorization", "X-Personal-Write-Binding", "X-CSRF-Token", "X-Principal-ID", "X-Owner-ID", "X-Supabase-Token"):
            with self.subTest(header=header):
                response = self.search({"Origin": SOT_PUBLIC_ORIGIN, header: "fixture-value"})
                self.assertEqual(response.status_code, 403)
                self.assert_denied(response)
        self.assertEqual(self.lookup.call_count, 0)

    def test_private_query_selectors_rejected_before_search_lookup(self):
        for key in ("user_email", "email", "principal", "principal_id", "owner", "owner_id", "token", "access_token", "csrf"):
            with self.subTest(key=key):
                response = self.search({"Origin": SOT_PUBLIC_ORIGIN}, **{key: "fixture-value"})
                self.assertEqual(response.status_code, 403)
                self.assert_denied(response)
        self.assertEqual(self.lookup.call_count, 0)

    def test_private_auth_admin_config_and_compute_routes_never_cors_open(self):
        for path in ("/account/me", "/auth/config", "/personal/cards", "/library", "/admin", "/internal/diagnostics", "/config", "/map", "/similarity", "/search/"):
            with self.subTest(path=path):
                self.assert_denied(self.client.get(path, headers={"Origin": SOT_PUBLIC_ORIGIN}, follow_redirects=False))
                self.assert_denied(self.preflight(path=path))

    def test_post_search_is_not_cors_open(self):
        response = self.client.post("/search", json={}, headers={"Origin": SOT_PUBLIC_ORIGIN})
        self.assertEqual(response.status_code, 405)
        self.assert_denied(response)
        self.assertEqual(self.lookup.call_count, 0)

    def test_off_scope_redirect_is_not_cors_open_or_automatically_followed(self):
        for method in ("GET", "OPTIONS"):
            response = self.client.request(method, "/search/", headers={"Origin": SOT_PUBLIC_ORIGIN, "Access-Control-Request-Method": "GET"}, follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            self.assertTrue(response.headers["location"].endswith("/search"))
            self.assert_denied(response)
        self.assertEqual(self.lookup.call_count, 0)

    def test_normal_api_error_keeps_anonymous_search_cors_only(self):
        response = self.search({"Origin": SOT_PUBLIC_ORIGIN}, top=0)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.headers["access-control-allow-origin"], SOT_PUBLIC_ORIGIN)
        self.assertEqual(response.headers["access-control-allow-credentials"], "false")

    def test_requests_without_origin_retain_existing_api_contract(self):
        response = self.search()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)
        self.assertIn("origin", response.headers["vary"].lower())

    def test_options_without_requested_method_is_denied(self):
        response = self.client.options("/search", headers={"Origin": SOT_PUBLIC_ORIGIN})
        self.assertEqual(response.status_code, 403)
        self.assert_denied(response)


class ScopePolicyTests(unittest.TestCase):
    def test_public_policy_ignores_broad_configured_origins(self):
        for origins in (("*",), ("https://example.com", "http://localhost:5173")):
            app = FastAPI()
            app.get("/search")(lambda: {"results": []})
            install_guest_search_cors(app, SimpleNamespace(is_public=True, allowed_origins=origins))
            client = TestClient(app)
            self.assertEqual(client.get("/search", headers={"Origin": SOT_PUBLIC_ORIGIN}).headers["access-control-allow-origin"], SOT_PUBLIC_ORIGIN)
            self.assertNotIn("access-control-allow-origin", client.get("/search", headers={"Origin": "https://example.com"}).headers)

    def test_existing_development_cors_retained_without_production_localhost_allowance(self):
        app = FastAPI()
        app.get("/search")(lambda: {"results": []})
        origin = "http://localhost:5173"
        install_guest_search_cors(app, SimpleNamespace(is_public=False, allowed_origins=(origin,)))
        self.assertEqual(TestClient(app).get("/search", headers={"Origin": origin}).headers["access-control-allow-origin"], origin)
