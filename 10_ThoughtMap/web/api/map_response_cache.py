"""Serving the prepared `/map` response.

`/map` is the same 12.0 MB of JSON for every caller and changes only when the
corpus is re-projected. The bytes are therefore produced once, at projection
time, by `map_projection.write_artifact` — not here, and not at request time.

    map_projection_3d.json          the artifact, already compact JSON, which
                                    *is* the identity-encoded response
    map_projection_3d.json.gz       the gzipped response
    map_projection_3d.json.gzmeta   fingerprint, node count, sizes, checksums

What is left at runtime is validation and two open file handles. The route
answers with a `FileResponse`, so the kernel serves those pages from the page
cache: file-backed and evictable, rather than 15.5 MB of heap the process can
never give back.

This module used to build the pair on first request. It no longer does, in any
deployment a person can reach. Building it cost a 12 MB parse into ~37.5 MB of
Python dicts plus a re-serialisation and a gzip — an 87 MB transient, measured,
and the single largest peak in a cold start once the corpus load was fixed. A
512 MB instance cannot spend that on recomputing a value that was already known
when the projection was generated.

Development keeps an in-memory fallback so a freshly hand-built artifact still
serves, and it says which command to run. `public-demo` and `production` do
not: a missing or stale sidecar fails readiness and answers 503, because an
instance quietly using 87 MB more than its budget looks healthy right up to the
moment it is killed.
"""

from __future__ import annotations

import gzip
import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .map_projection import (
    SIDECAR_GZIP_LEVEL,
    gzip_path_for,
    meta_path_for,
    verify_map_sidecars,
)


logger = logging.getLogger("thoughtmap.map")

#: Kept as the name the rest of the codebase imports for the compression level.
GZIP_LEVEL = SIDECAR_GZIP_LEVEL


class MapPayloadUnavailableError(RuntimeError):
    """No usable prepared response. Answered as 503, never 500."""


@dataclass(frozen=True)
class EncodedMap:
    """One `/map` payload, as files on disk or — in development — as bytes.

    Exactly one of the byte fields and the path fields is populated. Both
    describe the same response; they differ only in where it is held.
    """

    fingerprint: str
    etag: str
    node_count: int
    raw: bytes | None = None
    gzipped: bytes | None = None
    raw_path: Path | None = None
    gzip_path: Path | None = None
    raw_size: int = 0
    gzip_size: int = 0

    @property
    def on_disk(self) -> bool:
        return self.raw_path is not None and self.gzip_path is not None

    @property
    def raw_bytes(self) -> int:
        return self.raw_size or (len(self.raw) if self.raw is not None else 0)

    @property
    def gzipped_bytes(self) -> int:
        return self.gzip_size or (len(self.gzipped) if self.gzipped is not None else 0)


def _etag_for(fingerprint: str) -> str:
    return f'W/"map-{fingerprint[:32]}"' if fingerprint else ""


def _fingerprint_of(artifact: dict[str, Any]) -> str:
    return str(artifact.get("projection", {}).get("dataset_fingerprint", ""))


class MapResponseCache:
    """Holds the validated identity of the prepared response, not its bytes.

    `allow_rebuild` is the development escape hatch. It is off in any public
    deployment, and `main` sets it from the deployment mode rather than
    leaving it to a default.
    """

    def __init__(self, allow_rebuild: bool = True, verify_checksums: bool = True) -> None:
        self._lock = threading.Lock()
        self._encoded: EncodedMap | None = None
        self._source_key: tuple[str, int, int] | None = None
        self.allow_rebuild = allow_rebuild
        self.verify_checksums = verify_checksums

    # --- the route's entry point ------------------------------------------

    def get_for(self, service) -> EncodedMap:
        """The prepared response for the service's current artifact.

        Validated once per artifact version. The in-process key is the cheap
        (path, mtime_ns, size) probe — it decides whether to re-validate, and
        nothing more; validity itself is the sidecar's recorded checksum of the
        artifact's contents, which survives the file being copied to a server.
        """
        key = service.current_key()

        cached = self._encoded
        if cached is not None and key is not None and key == self._source_key:
            return cached

        with self._lock:
            cached = self._encoded
            if cached is not None and key is not None and key == self._source_key:
                return cached

            artifact_path = getattr(service, "artifact_path", None)
            encoded: EncodedMap | None = None
            reason = ""
            if isinstance(artifact_path, Path):
                encoded, reason = self._from_prepared(artifact_path)

            if encoded is None:
                if not self.allow_rebuild:
                    raise MapPayloadUnavailableError(
                        reason or "The prepared /map response is unavailable."
                    )
                # Development only, and loudly: this is the 87 MB transient
                # that the whole sidecar exists to keep out of a deployment.
                if reason:
                    logger.warning(
                        "Building the /map response in memory because: %s "
                        "(development only)",
                        reason,
                    )
                artifact = service.load()
                encoded = self._encode(artifact)
                del artifact

            self._encoded = encoded
            self._source_key = key
            return encoded

    def _from_prepared(self, artifact_path: Path) -> tuple[EncodedMap | None, str]:
        meta, reason = verify_map_sidecars(artifact_path, self.verify_checksums)
        if meta is None:
            return None, reason

        fingerprint = str(meta["fingerprint"])
        logger.info(
            "Serving the prepared /map response: %d nodes, %.1f MB gzip, "
            "fingerprint %s",
            int(meta.get("node_count", 0)),
            int(meta["gzip_size"]) / (1024 * 1024),
            fingerprint[:12],
        )
        return (
            EncodedMap(
                fingerprint=fingerprint,
                etag=_etag_for(fingerprint),
                node_count=int(meta.get("node_count", 0)),
                raw_path=artifact_path,
                gzip_path=gzip_path_for(artifact_path),
                raw_size=int(meta["raw_size"]),
                gzip_size=int(meta["gzip_size"]),
            ),
            "",
        )

    # --- in-memory path ----------------------------------------------------

    def get(self, artifact: dict[str, Any]) -> EncodedMap:
        """Encode an artifact the caller already holds.

        For callers that build a projection rather than reading one from disk.
        """
        fingerprint = _fingerprint_of(artifact)

        cached = self._encoded
        if cached is not None and cached.fingerprint == fingerprint:
            return cached

        with self._lock:
            # Re-check: two requests can arrive together on a cold cache, and
            # encoding 12.0 MB twice would be pure waste.
            cached = self._encoded
            if cached is not None and cached.fingerprint == fingerprint:
                return cached

            encoded = self._encode(artifact)
            self._encoded = encoded
            return encoded

    @staticmethod
    def _encode(artifact: dict[str, Any]) -> EncodedMap:
        raw = json.dumps(artifact, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        fingerprint = _fingerprint_of(artifact)
        return EncodedMap(
            fingerprint=fingerprint,
            etag=_etag_for(fingerprint),
            node_count=len(artifact.get("nodes", [])),
            raw=raw,
            gzipped=gzip.compress(raw, GZIP_LEVEL),
            raw_size=len(raw),
        )

    def clear(self) -> None:
        with self._lock:
            self._encoded = None
            self._source_key = None


def accepts_gzip(accept_encoding: str) -> bool:
    """Whether the client asked for gzip.

    Deliberately simple: this only decides which of two prepared payloads to
    send, and every browser in use sends a plain `gzip` token. A client that
    does not ask gets the uncompressed payload, which is always correct.
    """
    return "gzip" in (accept_encoding or "").lower()


__all__ = [
    "EncodedMap",
    "GZIP_LEVEL",
    "MapPayloadUnavailableError",
    "MapResponseCache",
    "accepts_gzip",
    "gzip_path_for",
    "meta_path_for",
]
