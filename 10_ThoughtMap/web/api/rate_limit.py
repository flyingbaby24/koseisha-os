"""Minimal per-client rate limiting for the expensive endpoints.

A semantic search costs the backend a model encode and a 63,891-row ranking,
and measurement puts one worker's ceiling at roughly 6-8 requests per second
(T6 #13). A public URL with no limit at all can have that consumed by one
script, so a beta needs *some* protection (T6 #27).

Deliberately small. This is not an account quota system and does not try to be:
no per-user tiers, no distributed state, no storage. A token bucket per client
address, in memory, is proportionate to a public demo, and a real deployment
behind a reverse proxy or a provider edge should prefer that layer instead —
which is why this is off unless configured.

Known limits, stated rather than hidden:

- Per process. Two workers permit twice the configured rate. Since the measured
  recommendation is a single worker, that is currently moot.
- Keyed on the client address, so callers behind one NAT share a bucket.
- Trusts `X-Forwarded-For` only when explicitly told to, because a forwarded
  header is client-controlled and trusting it by default would let anyone
  forge their way into a private bucket.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class Bucket:
    tokens: float
    updated: float


class RateLimiter:
    """Token bucket per client key.

    `rate` tokens accrue per second up to `burst`. One request costs one token;
    a request arriving with an empty bucket is refused rather than queued.
    """

    def __init__(self, rate: float, burst: int, now=time.monotonic) -> None:
        self.rate = float(rate)
        self.burst = int(burst)
        self._now = now
        self._lock = threading.Lock()
        self._buckets: dict[str, Bucket] = {}
        self._last_sweep = now()

    def allow(self, key: str) -> tuple[bool, float]:
        """(allowed, retry_after_seconds)."""
        if self.rate <= 0:
            return True, 0.0

        now = self._now()
        with self._lock:
            self._sweep(now)
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = Bucket(tokens=float(self.burst), updated=now)
                self._buckets[key] = bucket

            elapsed = max(0.0, now - bucket.updated)
            bucket.tokens = min(float(self.burst), bucket.tokens + elapsed * self.rate)
            bucket.updated = now

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, 0.0

            missing = 1.0 - bucket.tokens
            return False, missing / self.rate

    def _sweep(self, now: float) -> None:
        """Drop buckets that have refilled, so memory cannot grow without bound.

        A full bucket is indistinguishable from a new one, so forgetting it
        loses nothing. Without this, a stream of distinct addresses would
        accumulate an entry each — a slow leak that only shows up in
        production.
        """
        if now - self._last_sweep < 60.0:
            return
        self._last_sweep = now

        full_after = self.burst / self.rate if self.rate else 0.0
        self._buckets = {
            key: bucket
            for key, bucket in self._buckets.items()
            if now - bucket.updated < full_after + 60.0
        }

    @property
    def tracked(self) -> int:
        with self._lock:
            return len(self._buckets)


def client_key(client_host: str | None, forwarded_for: str | None, trust_proxy: bool) -> str:
    """Which client this request counts against."""
    if trust_proxy and forwarded_for:
        # Left-most entry is the original client, per convention.
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    return client_host or "unknown"
