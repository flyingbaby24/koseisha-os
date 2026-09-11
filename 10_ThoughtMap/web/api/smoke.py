"""End-to-end smoke test against a running deployment.

    python -m api.smoke --base-url http://127.0.0.1:8078
    python -m api.smoke --base-url http://127.0.0.1:8078 --frontend-url http://127.0.0.1:5274
    python -m api.smoke --base-url ... --library-identity smoke@example.invalid

Checks the paths a first visitor actually exercises, in order, and exits
non-zero if any of them fail (T6 #41). It is deliberately an *external* client:
it imports no application module and shares no process with the server, so it
tests the deployment rather than the code.

The Personal Library is only exercised when `--library-identity` is given AND
the deployment reports the feature as enabled. Anything it saves, it deletes
again before exiting, including when a check in between fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class Headers(dict):
    """Case-insensitive view of response headers.

    HTTP header names are case-insensitive and servers differ: uvicorn emits
    them lower-case, other stacks title-case them. A plain dict lookup for
    "ETag" therefore silently misses `etag:` and reports a missing header that
    is right there on the wire.
    """

    def __init__(self, source) -> None:
        super().__init__(source or {})
        self._lower = {str(key).lower(): value for key, value in self.items()}

    def get(self, key, default=None):  # type: ignore[override]
        return self._lower.get(str(key).lower(), default)

    def __contains__(self, key) -> bool:  # type: ignore[override]
        return str(key).lower() in self._lower


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    ms: float = 0.0


class Smoke:
    def __init__(self, base_url: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.checks: list[Check] = []

    # --- plumbing --------------------------------------------------------

    def request(
        self,
        path: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any, Headers]:
        url = f"{self.base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"

        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        for key, value in (headers or {}).items():
            request.add_header(key, value)

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                return response.status, _maybe_json(raw), Headers(response.headers)
        except urllib.error.HTTPError as exc:
            return exc.code, _maybe_json(exc.read()), Headers(exc.headers or {})

    def check(self, name: str, ok: bool, detail: str = "", ms: float = 0.0) -> bool:
        self.checks.append(Check(name=name, ok=ok, detail=detail, ms=ms))
        mark = "PASS" if ok else "FAIL"
        timing = f"  {ms:,.0f} ms" if ms else ""
        print(f"[{mark}] {name}{timing}  {detail}")
        return ok

    # --- checks ----------------------------------------------------------

    def health(self) -> bool:
        started = time.perf_counter()
        status, body, _ = self.request("/health")
        ms = (time.perf_counter() - started) * 1000
        ok = status == 200 and isinstance(body, dict) and body.get("status") == "ok"
        return self.check("/health", ok, f"status={status}", ms)

    def ready(self, wait_s: float) -> dict[str, Any]:
        """Poll until ready, because a fresh deployment is legitimately warming."""
        deadline = time.time() + wait_s
        started = time.perf_counter()
        body: Any = {}
        status = 0

        while True:
            status, body, _ = self.request("/ready")
            if status == 200:
                break
            if time.time() >= deadline:
                break
            time.sleep(2.0)

        ms = (time.perf_counter() - started) * 1000
        snapshot = body if isinstance(body, dict) else {}
        blocked = snapshot.get("blocked_by") or []
        self.check(
            "/ready",
            status == 200,
            f"status={status} corpus={snapshot.get('corpus_version', '?')} "
            f"documents={snapshot.get('document_count', '?')}"
            + (f" blocked_by={blocked}" if blocked else ""),
            ms,
        )
        return snapshot

    def config(self) -> dict[str, Any]:
        status, body, _ = self.request("/config")
        features = body if isinstance(body, dict) else {}
        self.check(
            "/config",
            status == 200,
            f"mode={features.get('deployment_mode')} "
            f"library={features.get('library_enabled')}",
        )
        return features

    def map(self, expected_documents: int | None) -> None:
        started = time.perf_counter()
        status, body, headers = self.request("/map")
        ms = (time.perf_counter() - started) * 1000

        nodes = len(body.get("nodes", [])) if isinstance(body, dict) else 0
        ok = status == 200 and nodes > 0
        if expected_documents:
            ok = ok and nodes == expected_documents
        self.check(
            "/map",
            ok,
            f"status={status} nodes={nodes:,} encoding={headers.get('Content-Encoding', 'none')}",
            ms,
        )

        etag = headers.get("ETag", "")
        self.check("/map ETag", bool(etag), etag or "no ETag header")
        self.check(
            "/map Cache-Control",
            "max-age" in headers.get("Cache-Control", ""),
            headers.get("Cache-Control", "(absent)"),
        )

        if etag:
            started = time.perf_counter()
            status, _, _ = self.request("/map", headers={"If-None-Match": etag})
            ms = (time.perf_counter() - started) * 1000
            self.check("/map conditional", status == 304, f"status={status}", ms)

    def search(self, mode: str) -> str:
        started = time.perf_counter()
        status, body, headers = self.request(
            "/search", params={"q": "Plato", "mode": mode, "top": 10}
        )
        ms = (time.perf_counter() - started) * 1000

        results = body.get("results", []) if isinstance(body, dict) else []
        ok = status == 200 and len(results) > 0
        top = results[0].get("title", "") if results else ""
        self.check(f"/search {mode}", ok, f"status={status} results={len(results)} top={top!r}", ms)

        if mode == "semantic":
            self.check(
                "/search no-store",
                headers.get("Cache-Control") == "no-store",
                headers.get("Cache-Control", "(absent)"),
            )
            profile = body.get("query_parameters") if isinstance(body, dict) else None
            self.check(
                "query radar profile",
                isinstance(profile, list) and len(profile) == 10,
                f"axes={len(profile) if isinstance(profile, list) else 0}",
            )

        return str(results[0].get("doc_id", "")) if results else ""

    def detail_join(self, doc_id: str) -> None:
        """A result must carry what the radar needs, without a second request."""
        status, body, _ = self.request("/search", params={"q": "Plato", "mode": "semantic", "top": 10})
        results = body.get("results", []) if isinstance(body, dict) else []
        match = next((item for item in results if item.get("doc_id") == doc_id), None)
        parameters = (match or {}).get("parameters") or []
        self.check(
            "result carries radar parameters",
            status == 200 and len(parameters) > 0,
            f"doc_id={doc_id} axes={len(parameters)}",
        )

    def library(self, identity: str, doc_id: str) -> None:
        saved = False
        try:
            status, body, headers = self.request(
                "/users/by-email/save",
                method="POST",
                body={
                    "email": identity,
                    "doc_id": doc_id,
                    "title": "Smoke test document",
                    "source": "gutendex",
                },
            )
            saved = status == 200
            self.check(
                "library save",
                saved,
                f"status={status} saved={_get(body, 'saved')} duplicate={_get(body, 'duplicate')}",
            )
            self.check(
                "library no-store",
                headers.get("Cache-Control") == "no-store",
                headers.get("Cache-Control", "(absent)"),
            )

            status, body, _ = self.request(
                "/users/by-email/saved", params={"email": identity}
            )
            works = body.get("works", []) if isinstance(body, dict) else []
            self.check(
                "library list",
                status == 200 and any(w.get("doc_id") == doc_id for w in works),
                f"status={status} works={len(works)}",
            )
        finally:
            # Always clean up, including after a failure above: a smoke run must
            # not leave rows behind in a real deployment.
            if saved:
                quoted = urllib.parse.quote(doc_id, safe="")
                status, body, _ = self.request(
                    f"/users/by-email/saved/{quoted}",
                    method="DELETE",
                    params={"email": identity},
                )
                self.check(
                    "library delete (cleanup)",
                    status == 200 and _get(body, "deleted") is True,
                    f"status={status}",
                )

    def library_disabled(self) -> None:
        status, _, _ = self.request(
            "/users/by-email/saved", params={"email": "disabled-check@example.invalid"}
        )
        self.check(
            "library route refuses when disabled",
            status == 404,
            f"status={status} (expected 404)",
        )

    def frontend(self, url: str) -> None:
        try:
            request = urllib.request.Request(url, headers={"Accept": "text/html"})
            with urllib.request.urlopen(request, timeout=30) as response:
                html = response.read().decode("utf-8", "replace")
                status = response.status
        except Exception as exc:
            self.check("frontend loads", False, f"{type(exc).__name__}: {exc}")
            return

        self.check(
            "frontend loads",
            status == 200 and "tm-viewport" in html,
            f"status={status} bytes={len(html):,}",
        )
        self.check(
            "frontend references a bundle",
            'type="module"' in html or "assets/" in html,
            "no module script found" if "assets/" not in html else "",
        )

    # --- report ----------------------------------------------------------

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def report(self) -> None:
        failed = [check.name for check in self.checks if not check.ok]
        print()
        print(f"{len(self.checks) - len(failed)}/{len(self.checks)} checks passed")
        if failed:
            print("failed: " + ", ".join(failed))
        print("RESULT:", "OK" if self.ok else "FAILED")


def _maybe_json(raw: bytes) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return raw.decode("utf-8", "replace")


def _get(body: Any, key: str) -> Any:
    return body.get(key) if isinstance(body, dict) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a ThoughtMap deployment.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8078")
    parser.add_argument("--frontend-url", default=None)
    parser.add_argument(
        "--library-identity",
        default=None,
        help="Exercise save/list/delete with this identity, then clean up.",
    )
    parser.add_argument(
        "--wait-ready",
        type=float,
        default=180.0,
        help="Seconds to wait for readiness before failing.",
    )
    args = parser.parse_args(argv)

    smoke = Smoke(args.base_url)
    print(f"ThoughtMap smoke test against {smoke.base_url}\n")

    smoke.health()
    snapshot = smoke.ready(args.wait_ready)
    features = smoke.config()

    documents = snapshot.get("document_count") or 0
    smoke.map(documents if isinstance(documents, int) else None)

    smoke.search("keyword")
    doc_id = smoke.search("semantic")
    smoke.search("hybrid")
    if doc_id:
        smoke.detail_join(doc_id)

    if features.get("library_enabled"):
        if args.library_identity and doc_id:
            smoke.library(args.library_identity, doc_id)
        else:
            print("[SKIP] library round trip (no --library-identity)")
    else:
        smoke.library_disabled()

    if args.frontend_url:
        smoke.frontend(args.frontend_url)

    smoke.report()
    return 0 if smoke.ok else 1


if __name__ == "__main__":
    sys.exit(main())
