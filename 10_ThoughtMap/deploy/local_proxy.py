"""A same-origin reverse proxy for local production-like verification.

    python deploy/local_proxy.py --dist threejs/dist --api http://127.0.0.1:8078 --port 8090

    /            -> the built frontend, with the cache policy from
                    Caddyfile.example and nginx.conf.example
    /api/*       -> the FastAPI service

Exists so the deployment can be checked end-to-end through a proxy rather than
against uvicorn directly (T7 §25, §27): CORS, cache headers, ETag revalidation
and readiness all behave differently once something sits in front.

**Local verification only.** Single-threaded-per-request, no TLS, no access
control. Production uses Caddy or nginx; the configurations in this directory
are the real thing, and this mirrors their header policy so a divergence shows
up here.
"""

from __future__ import annotations

import argparse
import http.server
import socketserver
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


# Mirrors deploy/Caddyfile.example and deploy/nginx.conf.example.
IMMUTABLE = "public, max-age=31536000, immutable"
REVALIDATE = "no-cache"

# Headers the proxy must not copy from the upstream response: they describe the
# upstream connection, not this one.
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
}


def make_handler(dist: Path, api: str):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(dist), **kwargs)

        def log_message(self, fmt: str, *args) -> None:  # quieter
            sys.stderr.write("proxy: " + (fmt % args) + "\n")

        # --- API ----------------------------------------------------------
        def _proxy(self, method: str) -> None:
            path = self.path[len("/api") :] or "/"
            url = api.rstrip("/") + path

            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None

            request = urllib.request.Request(url, data=body, method=method)
            for name, value in self.headers.items():
                if name.lower() in {"host", "content-length", "connection"}:
                    continue
                request.add_header(name, value)
            # Overwritten, never appended: a client must not be able to forge
            # the address the rate limiter counts against.
            request.add_header("X-Forwarded-For", self.client_address[0])
            request.add_header("X-Forwarded-Proto", "http")

            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    self._relay(response.status, response.headers, response.read())
            except urllib.error.HTTPError as exc:
                # 304 and 4xx/5xx are real answers and must reach the client
                # unchanged, including their headers.
                self._relay(exc.code, exc.headers or {}, exc.read() if exc.fp else b"")
            except Exception as exc:
                message = f"upstream unreachable: {type(exc).__name__}".encode()
                self.send_response(502)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(message)))
                self.end_headers()
                self.wfile.write(message)

        def _relay(self, status: int, headers, body: bytes) -> None:
            self.send_response(status)
            for name, value in (headers.items() if headers else []):
                if name.lower() in HOP_BY_HOP:
                    continue
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body and self.command != "HEAD":
                self.wfile.write(body)

        # --- static -------------------------------------------------------
        def end_headers(self) -> None:
            if not self.path.startswith("/api"):
                path = urllib.parse.urlparse(self.path).path
                if path.startswith("/assets/"):
                    # Content-hashed: the name changes when the bytes do.
                    self.send_header("Cache-Control", IMMUTABLE)
                else:
                    # index.html points at those hashed names, so caching it
                    # hard would pin a visitor to an old build.
                    self.send_header("Cache-Control", REVALIDATE)
                self.send_header("X-Content-Type-Options", "nosniff")
            super().end_headers()

        def do_GET(self) -> None:
            if self.path.startswith("/api"):
                return self._proxy("GET")
            if urllib.parse.urlparse(self.path).path.endswith(".map"):
                # Built, but not for the public.
                self.send_error(404)
                return
            if urllib.parse.urlparse(self.path).path == "/":
                self.path = "/index.html"
            return super().do_GET()

        def do_HEAD(self) -> None:
            if self.path.startswith("/api"):
                return self._proxy("HEAD")
            return super().do_HEAD()

        def do_POST(self) -> None:
            self._proxy("POST")

        def do_DELETE(self) -> None:
            self._proxy("DELETE")

    return Handler


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8078")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)

    dist = args.dist.resolve()
    if not (dist / "index.html").exists():
        print(f"No index.html in {dist}. Run `npm run build` first.")
        return 1

    handler = make_handler(dist, args.api)
    with Server((args.host, args.port), handler) as server:
        print(f"serving {dist} at http://{args.host}:{args.port}/")
        print(f"proxying /api/* -> {args.api}")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
