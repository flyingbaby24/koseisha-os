"""Read-only access to the cached 3D projection artifact.

This is the only projection code the HTTP path touches. It never imports UMAP
and never generates anything: if the artifact is missing or unreadable the
request fails fast so a multi-minute fit can never happen inside a request.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import ApiSettings, get_settings
from .map_projection import DEFAULT_ARTIFACT_PATH, ProjectionError, read_artifact


logger = logging.getLogger("thoughtmap.map")


class ProjectionUnavailableError(RuntimeError):
    """No usable projection artifact. Answered as 503, never 500."""


class MapService:
    """Serves the projection artifact, parsing it at most once per file version.

    Cache invalidation is by file identity, not by process lifetime: the cache
    key is (path, mtime_ns, size). Regenerating the artifact therefore takes
    effect on the next request with no restart, while repeated requests against
    an unchanged file reuse the parsed object. There is no TTL and no hidden
    staleness — if the bytes on disk have not changed, neither has the answer.
    """

    def __init__(self, artifact_path: str | Path | None = None) -> None:
        self.artifact_path = Path(artifact_path) if artifact_path else DEFAULT_ARTIFACT_PATH

    def current_key(self) -> tuple[str, int, int] | None:
        """File identity: (path, mtime_ns, size). None if unreadable."""
        return self._current_key()

    def load(self) -> dict[str, Any]:
        """Parse the artifact. The result is NOT retained.

        At 63,891 nodes the parsed form is 37.5 MB of Python dicts, and the
        only thing done with it is to serialise it once per corpus version.
        `MapResponseCache` keeps the serialised bytes instead and calls this
        only when the file on disk has changed, so the dicts become garbage as
        soon as they have been encoded.
        """
        try:
            artifact = read_artifact(self.artifact_path)
        except FileNotFoundError as exc:
            raise ProjectionUnavailableError(
                "The 3D projection has not been generated yet. "
                "Run `python -m api.generate_map_projection` from 10_ThoughtMap/web."
            ) from exc
        except ProjectionError as exc:
            # Message is safe to surface: it names the schema problem, not paths
            # or stack frames.
            raise ProjectionUnavailableError(
                f"The stored 3D projection could not be used: {exc}"
            ) from exc

        logger.info(
            "Loaded projection artifact nodes=%d fingerprint=%s",
            len(artifact.get("nodes", [])),
            artifact.get("projection", {}).get("dataset_fingerprint", "")[:12],
        )
        return artifact

    def _current_key(self) -> tuple[str, int, int] | None:
        try:
            stat = self.artifact_path.stat()
        except OSError:
            return None
        return (str(self.artifact_path), stat.st_mtime_ns, stat.st_size)


def create_map_service(settings: ApiSettings) -> MapService:
    return MapService(getattr(settings, "map_artifact_path", None))


@lru_cache(maxsize=1)
def get_map_service() -> MapService:
    return create_map_service(get_settings())
