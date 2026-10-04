"""CORS for the anonymous SoT Guest public search, not for account routes."""
from __future__ import annotations

from urllib.parse import parse_qsl

from fastapi.middleware.cors import CORSMiddleware

SOT_PUBLIC_ORIGIN = "https://sot-web.onrender.com"
_ORIGIN = SOT_PUBLIC_ORIGIN.encode("ascii")
_PRIVATE_HEADERS = frozenset({
    b"authorization", b"proxy-authorization", b"cookie", b"x-personal-write-binding",
    b"x-csrf-token", b"x-xsrf-token", b"x-principal-id", b"x-owner-id",
})
_PRIVATE_PREFIXES = (b"x-personal-", b"x-principal-", b"x-owner-", b"x-supabase-", b"x-csrf-", b"x-xsrf-")
_PRIVATE_QUERY = frozenset({
    "user_email", "email", "principal", "principal_id", "owner", "owner_id",
    "token", "access_token", "csrf",
})


class GuestSearchCORSMiddleware:
    """Public-mode middleware; no origin reflection or credential forwarding."""

    def __init__(self, app):
        self.app = app

    @staticmethod
    async def _deny(send):
        # Do not expose even the denial to an unapproved CORS caller.
        await send({"type": "http.response.start", "status": 403, "headers": [
            (b"content-length", b"0"), (b"cache-control", b"no-store"),
            (b"vary", b"Origin, Access-Control-Request-Method, Access-Control-Request-Headers"),
        ]})
        await send({"type": "http.response.body", "body": b""})

    @staticmethod
    def _vary_origin(send, allow_origin=False):
        async def scoped_send(message):
            if message["type"] == "http.response.start":
                response_headers = [(key, value) for key, value in message.get("headers", []) if not key.lower().startswith(b"access-control-")]
                vary = [value for key, value in response_headers if key.lower() == b"vary"]
                response_headers = [(key, value) for key, value in response_headers if key.lower() != b"vary"]
                tokens = [token.strip() for value in vary for token in value.split(b",") if token.strip()]
                if not any(token.lower() == b"origin" for token in tokens):
                    tokens.append(b"Origin")
                response_headers.append((b"vary", b", ".join(tokens)))
                if allow_origin:
                    response_headers.extend([
                        (b"access-control-allow-origin", _ORIGIN),
                        (b"access-control-allow-credentials", b"false"),
                    ])
                message = {**message, "headers": response_headers}
            await send(message)
        return scoped_send

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != "/search":
            await self.app(scope, receive, send)
            return
        headers = [(key.lower(), value) for key, value in scope.get("headers", [])]
        origins = [value for key, value in headers if key == b"origin"]
        method = scope.get("method", "")
        if not origins:
            # Server-to-server and same-origin requests keep the original API.
            await self.app(scope, receive, self._vary_origin(send))
            return
        if origins != [_ORIGIN] or method not in ("GET", "OPTIONS"):
            if method == "OPTIONS":
                await self._deny(send)
            else:
                await self.app(scope, receive, self._vary_origin(send))
            return
        if any(key in _PRIVATE_HEADERS or key.startswith(_PRIVATE_PREFIXES) for key, _ in headers):
            await self._deny(send)
            return
        if any(key.lower() in _PRIVATE_QUERY for key, _ in parse_qsl(scope.get("query_string", b"").decode("utf-8", "replace"))):
            await self._deny(send)
            return
        if method == "OPTIONS":
            requested_methods = [value for key, value in headers if key == b"access-control-request-method"]
            requested_header_values = [value for key, value in headers if key == b"access-control-request-headers"]
            requested_headers = [value.strip().lower() for entry in requested_header_values for value in entry.split(b",") if value.strip()]
            if len(requested_methods) != 1 or requested_methods[0] not in (b"GET", b"OPTIONS") or any(value != b"accept" for value in requested_headers):
                await self._deny(send)
                return
            await send({"type": "http.response.start", "status": 204, "headers": [
                (b"access-control-allow-origin", _ORIGIN),
                (b"access-control-allow-credentials", b"false"),
                (b"access-control-allow-methods", b"GET, OPTIONS"),
                (b"access-control-allow-headers", b"Accept"),
                (b"vary", b"Origin, Access-Control-Request-Method, Access-Control-Request-Headers"),
                (b"cache-control", b"no-store"), (b"content-length", b"0"),
            ]})
            await send({"type": "http.response.body", "body": b""})
            return

        await self.app(scope, receive, self._vary_origin(send, allow_origin=True))


def install_guest_search_cors(app, settings):
    """Never install deployment-wide CORS on public/private HTTP routes."""
    if settings.is_public:
        app.add_middleware(GuestSearchCORSMiddleware)
    else:
        # Preserve the existing local development contract, without extending it.
        app.add_middleware(
            CORSMiddleware, allow_origins=list(settings.allowed_origins),
            allow_credentials=False, allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["*"],
        )
