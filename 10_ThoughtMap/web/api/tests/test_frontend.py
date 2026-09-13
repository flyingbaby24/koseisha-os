import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.frontend import mount_frontend


class FrontendTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dist = Path(self.temp.name) / "dist"
        (self.dist / "assets").mkdir(parents=True)
        (self.dist / "index.html").write_text('<html><script src="./assets/index-abc123.js"></script></html>')
        (self.dist / "assets/index-abc123.js").write_text('console.log("bundle")')
        (self.dist / "assets/index-abc123.js.map").write_text('private debug source')
        (self.dist / ".env").write_text('must not be served')
        (self.dist.parent / "private.txt").write_text('outside dist')
        app = FastAPI()
        for route in ("/ready", "/search", "/map", "/config"):
            app.add_api_route(route, lambda: {"api": True})
        mount_frontend(app, self.dist, required=True)
        self.client = TestClient(app)

    def test_root_and_index(self):
        for path in ("/", "/index.html"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/html", response.headers["content-type"])
            self.assertEqual(response.headers["cache-control"], "no-cache")

    def test_hashed_asset(self):
        response = self.client.get("/assets/index-abc123.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("immutable", response.headers["cache-control"])
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")

    def test_api_precedence(self):
        for path in ("/ready", "/search", "/map", "/config"):
            self.assertEqual(self.client.get(path).json(), {"api": True})

    def test_unknown_private_and_api_paths_stay_404(self):
        for path in ("/not-a-route", "/assets/missing.js", "/search/missing", "/users/default/saved", "/.env", "/assets/index-abc123.js.map", "/%2e%2e/private.txt"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404, path)
            self.assertNotIn("<html>", response.text)

    def test_missing_production_build_fails(self):
        with self.assertRaisesRegex(RuntimeError, "Production frontend missing"):
            mount_frontend(FastAPI(), self.dist / "missing", required=True)

    def test_optional_development_without_build(self):
        app = FastAPI()
        mount_frontend(app, self.dist / "missing")
        self.assertEqual(TestClient(app).get("/").status_code, 404)
