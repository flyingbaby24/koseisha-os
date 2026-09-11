"""Pre-encoded `/map` payloads.

`/map` is the same 12.6 MB of JSON for every caller and changes only when the
corpus is re-projected. Before T6 each request re-validated 63,891 nodes
through pydantic, re-serialized them, and re-compressed the result — about
900 ms of CPU to produce bytes identical to the previous request's.

So the bytes are produced once per artifact version and kept. The cache key is
the artifact's own content fingerprint, so a regenerated projection replaces
the payload without a restart and a stale payload cannot be served (T6 #19,
#20).

Memory cost is roughly 12.6 MB + 3.7 MB per corpus version, one version at a
time. That is a good trade against ~900 ms of CPU on every cold client, and it
is counted in the deployment's memory budget.
"""

from __future__ import annotations

import gzip
import json
import threading
from dataclasses import dataclass
from typing import Any


# Level 6 is zlib's default: within ~2% of level 9's size on this payload for a
# fraction of the CPU. It is paid once per corpus version either way, but there
# is no reason to spend the difference.
GZIP_LEVEL = 6


@dataclass(frozen=True)
class EncodedMap:
    fingerprint: str
    etag: str
    raw: bytes
    gzipped: bytes
    node_count: int

    @property
    def raw_bytes(self) -> int:
        return len(self.raw)

    @property
    def gzipped_bytes(self) -> int:
        return len(self.gzipped)


class MapResponseCache:
    """One encoded payload, replaced when the projection fingerprint changes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._encoded: EncodedMap | None = None

    def get(self, artifact: dict[str, Any]) -> EncodedMap:
        fingerprint = str(artifact.get("projection", {}).get("dataset_fingerprint", ""))

        cached = self._encoded
        if cached is not None and cached.fingerprint == fingerprint:
            return cached

        with self._lock:
            # Re-check: two requests can arrive together on a cold cache, and
            # encoding 12.6 MB twice would be pure waste.
            cached = self._encoded
            if cached is not None and cached.fingerprint == fingerprint:
                return cached

            raw = json.dumps(artifact, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            encoded = EncodedMap(
                fingerprint=fingerprint,
                etag=f'W/"map-{fingerprint[:32]}"' if fingerprint else "",
                raw=raw,
                gzipped=gzip.compress(raw, GZIP_LEVEL),
                node_count=len(artifact.get("nodes", [])),
            )
            self._encoded = encoded
            return encoded

    def clear(self) -> None:
        with self._lock:
            self._encoded = None


def accepts_gzip(accept_encoding: str) -> bool:
    """Whether the client asked for gzip.

    Deliberately simple: this only decides which of two pre-built byte strings
    to send, and every browser in use sends a plain `gzip` token. A client that
    does not ask gets the uncompressed payload, which is always correct.
    """
    return "gzip" in (accept_encoding or "").lower()
