"""Structured logging and per-request stage timing.

Small on purpose (T6 §34-§35). A beta needs to answer "which stage got slower"
from the logs; it does not need a metrics platform. Everything here is
dependency-free and degrades to a no-op when no request is in flight.

Two rules the rest of the code depends on:

- Timing never changes behaviour. If a stage is not recorded, the response is
  identical; nothing branches on a measurement.
- Nothing here logs document text, query-result content, or a Personal Library
  identity. Queries are recorded by length and hash, not by text, so a public
  beta's logs cannot become a record of what individuals searched for.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator


logger = logging.getLogger("thoughtmap.request")

# Per-request stage timings. A ContextVar rather than an attribute on the
# service, because one service object serves every concurrent request and
# instance state would interleave between them.
_timings: ContextVar[dict[str, float] | None] = ContextVar("thoughtmap_timings", default=None)


@contextmanager
def request_timings() -> Iterator[dict[str, float]]:
    """Collect stage timings for one request."""
    collected: dict[str, float] = {}
    token = _timings.set(collected)
    try:
        yield collected
    finally:
        _timings.reset(token)


@contextmanager
def stage(name: str) -> Iterator[None]:
    """Time one stage into the active request, or do nothing outside one.

    Nested and repeated stages accumulate, so a mode that embeds twice reports
    the total embedding cost rather than the last one.
    """
    collected = _timings.get()
    if collected is None:
        yield
        return

    started = time.perf_counter()
    try:
        yield
    finally:
        collected[name] = collected.get(name, 0.0) + (time.perf_counter() - started) * 1000.0


def record(name: str, milliseconds: float) -> None:
    """Add an already-measured stage to the active request."""
    collected = _timings.get()
    if collected is not None:
        collected[name] = collected.get(name, 0.0) + float(milliseconds)


def query_fingerprint(query: str) -> str:
    """A stable, short, non-reversible handle for a query string.

    Enough to spot one query being hammered or to correlate a slow request with
    an error, without writing what anyone typed into a log file.
    """
    text = str(query or "")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def log_event(event: str, **fields: Any) -> None:
    """Emit one structured line.

    `key=value` for simple values and a JSON tail for nested ones, so the
    output stays greppable by eye and parseable by a log processor.
    """
    simple: list[str] = [f"event={event}"]
    nested: dict[str, Any] = {}

    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, (dict, list, tuple)):
            nested[key] = value
        elif isinstance(value, float):
            simple.append(f"{key}={value:.3f}")
        else:
            simple.append(f"{key}={value}")

    line = " ".join(simple)
    if nested:
        line = f"{line} detail={json.dumps(nested, default=str, ensure_ascii=False)}"

    logger.info(line)


#: Query-string parameters whose *values* must never reach a log file.
#:
#: `q` is what somebody typed into the search box. `email` is a Personal
#: Library identity. Both appear in full in an ordinary access-log line, which
#: is how a beta's logs quietly become a record of who searched for what.
REDACTED_PARAMETERS = ("q", "email", "user_email", "target_doc_id")


def redact_query_string(path: str) -> str:
    """Replace sensitive query-parameter values with a marker.

    Keeps the shape of the request — path, parameter names, everything
    operationally useful — and removes only the values that identify a person
    or what they were looking for.
    """
    if "?" not in path:
        return path

    base, _, query = path.partition("?")
    parts = []
    for pair in query.split("&"):
        name, separator, value = pair.partition("=")
        if separator and name in REDACTED_PARAMETERS and value:
            parts.append(f"{name}=<redacted>")
        else:
            parts.append(pair)
    return f"{base}?{'&'.join(parts)}"


class RedactAccessLogFilter(logging.Filter):
    """Strip sensitive query values from uvicorn's access log.

    uvicorn formats access lines as `'%s - "%s %s HTTP/%s" %d'` with the full
    request target as the third argument, so the redaction happens there,
    before the line is ever formatted.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            redacted = redact_query_string(args[2])
            if redacted != args[2]:
                record.args = args[:2] + (redacted,) + args[3:]
        return True


def install_access_log_redaction() -> None:
    """Apply the redaction filter to uvicorn's access logger.

    Idempotent: called once at startup, and safe if uvicorn is not the server.
    """
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactAccessLogFilter) for f in access.filters):
        access.addFilter(RedactAccessLogFilter())


def configure_logging(level: str = "INFO") -> None:
    """Install a single-line formatter if the host has not configured one.

    Uvicorn configures its own handlers; this only fills the gap when the app
    is started some other way, and never adds a second handler to the root.
    """
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
        root.addHandler(handler)
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))
