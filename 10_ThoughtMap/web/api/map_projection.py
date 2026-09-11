"""Deterministic 3D projection of the official ThoughtMap corpus.

The projection is generated offline into a versioned artifact. Nothing in the
HTTP path ever runs UMAP: `map_service` only reads the artifact this module
writes.

Historical configuration (audited in phase T3):

- `src/Lyrics/00_embed.py`, `01_title_map.py`, `04_cluster_export.py` and the
  matching `src/note/` scripts all use
  `UMAP(n_neighbors=10, min_dist=0.2, metric="cosine", random_state=42)`.
  That is the canonical *document-level* layout config and is reused here.
  (`06_cluster_map.py` uses n_neighbors=3/min_dist=0.3, but its input is the
  handful of cluster centroids, not documents, so it does not apply.)
- `KMeans(n_clusters=8, random_state=42)` is canonical across both pipelines.

Only `n_components` is new: the historical scripts are all 2D, this is 3D.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


logger = logging.getLogger("thoughtmap.map_projection")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_ARTIFACT_PATH = (
    PROJECT_ROOT / "data" / "thoughtmap_db" / "official" / "map_projection_3d.json"
)

# Bump when the artifact's on-disk shape changes in a way readers must notice.
PROJECTION_SCHEMA_VERSION = 1

# Coordinates are rounded before writing: it keeps the artifact roughly a third
# smaller and is far below any visible precision at render scale. Rounding is
# deterministic, so it does not weaken the reproducibility guarantee.
COORDINATE_DECIMALS = 6


@dataclass(frozen=True)
class ProjectionConfig:
    """Everything that changes the resulting coordinates.

    Every field here feeds the dataset fingerprint, so changing any of them
    invalidates a cached artifact.
    """

    algorithm: str = "umap"
    n_components: int = 3
    metric: str = "cosine"
    n_neighbors: int = 10
    min_dist: float = 0.2
    random_seed: int = 42
    cluster_algorithm: str | None = "kmeans"
    cluster_count: int | None = 8

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectionStats:
    """Reported after generation; also useful as cheap diagnostics."""

    document_count: int = 0
    embedding_dimension: int = 0
    runtime_seconds: float = 0.0
    bounds: dict[str, tuple[float, float]] = field(default_factory=dict)
    axis_variance: dict[str, float] = field(default_factory=dict)
    bounding_sphere_radius: float = 0.0
    cluster_populations: dict[str, int] = field(default_factory=dict)


class ProjectionError(RuntimeError):
    """Generation or validation failed. The artifact is never published."""


# --------------------------------------------------------------------------
# Fingerprint
# --------------------------------------------------------------------------


def compute_dataset_fingerprint(
    doc_ids: Iterable[str],
    vectors: Iterable[np.ndarray],
    config: ProjectionConfig,
) -> str:
    """Fingerprint of exactly the inputs that determine the coordinates.

    Covers document identity, embedding values, and the projection config —
    the three things §6 requires it to detect. Deliberately *not* covered:
    title, author, source and any other display metadata, because none of them
    move a node. A title correction therefore does not invalidate the geometry;
    regenerate to refresh the labels carried in the artifact.

    Order-independent: pairs are sorted by doc_id first, so a reordered CSV
    produces the same fingerprint.
    """
    digest = hashlib.sha256()
    digest.update(b"thoughtmap-projection-v1\n")

    # Config first, so a config change alone changes the fingerprint.
    digest.update(json.dumps(config.to_dict(), sort_keys=True).encode("utf-8"))
    digest.update(b"\n")

    pairs = sorted(
        zip((str(doc_id) for doc_id in doc_ids), vectors),
        key=lambda pair: pair[0],
    )

    for doc_id, vector in pairs:
        digest.update(doc_id.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(np.asarray(vector, dtype=np.float32).tobytes())
        digest.update(b"\n")

    return digest.hexdigest()


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------


class ProjectionGenerator:
    """Builds the 3D projection artifact from the official search index.

    Reads through the same repository `/search` uses, so the map and the search
    results are guaranteed to describe the same set of documents.
    """

    def __init__(
        self,
        index_loader,
        config: ProjectionConfig | None = None,
    ) -> None:
        self.index_loader = index_loader
        self.config = config or ProjectionConfig()

    def generate(self) -> tuple[dict[str, Any], ProjectionStats]:
        started = time.perf_counter()

        frame = self._load_frame()
        doc_ids = frame["doc_id"].tolist()
        vectors = frame["_embedding_vec"].tolist()

        matrix = self._stack_embeddings(vectors)
        fingerprint = compute_dataset_fingerprint(doc_ids, vectors, self.config)

        logger.info(
            "Projecting %d documents (dim=%d) with %s",
            len(doc_ids),
            matrix.shape[1],
            self.config.to_dict(),
        )

        coordinates = self._project(matrix)
        clusters = self._cluster(matrix)

        artifact = self._build_artifact(frame, coordinates, clusters, fingerprint, matrix.shape[1])
        validate_artifact(artifact, expected_count=len(doc_ids))

        stats = self._build_stats(coordinates, clusters, matrix.shape[1])
        stats.runtime_seconds = time.perf_counter() - started

        return artifact, stats

    def _load_frame(self) -> pd.DataFrame:
        frame = self.index_loader()

        if frame is None or frame.empty:
            raise ProjectionError("Search index is empty; nothing to project.")

        for column in ("doc_id", "_embedding_vec"):
            if column not in frame.columns:
                raise ProjectionError(f"Search index is missing required column: {column}")

        frame = frame.copy()
        frame["doc_id"] = frame["doc_id"].fillna("").astype(str).str.strip()

        blank = int((frame["doc_id"] == "").sum())
        if blank:
            # Never silently dropped: a blank id cannot be joined to a search
            # result later, so it is a data problem worth failing on.
            raise ProjectionError(f"{blank} document(s) have a blank doc_id.")

        missing_vectors = int(frame["_embedding_vec"].isna().sum())
        if missing_vectors:
            raise ProjectionError(f"{missing_vectors} document(s) have no parsed embedding.")

        duplicates = frame["doc_id"].duplicated()
        if duplicates.any():
            examples = frame.loc[duplicates, "doc_id"].head(5).tolist()
            raise ProjectionError(
                f"{int(duplicates.sum())} duplicate doc_id value(s) in the index, "
                f"for example: {examples}"
            )

        # Sorting makes generation independent of CSV row order.
        return frame.sort_values("doc_id").reset_index(drop=True)

    def _stack_embeddings(self, vectors: list[np.ndarray]) -> np.ndarray:
        dimensions = {int(np.asarray(vector).shape[0]) for vector in vectors}
        if len(dimensions) != 1:
            raise ProjectionError(f"Embeddings have inconsistent dimensions: {sorted(dimensions)}")

        matrix = np.stack([np.asarray(vector, dtype=np.float32) for vector in vectors])

        if not np.isfinite(matrix).all():
            raise ProjectionError("Embedding matrix contains NaN or Infinity.")

        return matrix

    def _project(self, matrix: np.ndarray) -> np.ndarray:
        count = matrix.shape[0]

        # UMAP needs more neighbours than it has points; clamp rather than
        # crash on a tiny corpus (this is also what web/app.py does).
        n_neighbors = min(self.config.n_neighbors, max(2, count - 1))

        try:
            from umap import UMAP
        except Exception as exc:
            raise ProjectionError(
                "umap-learn is required to generate the projection. "
                "Install web/requirements.txt before running the generator."
            ) from exc

        reducer = UMAP(
            n_components=self.config.n_components,
            n_neighbors=n_neighbors,
            min_dist=self.config.min_dist,
            metric=self.config.metric,
            # Explicit, never the library default: this is what makes repeated
            # generation reproducible.
            random_state=self.config.random_seed,
        )
        coordinates = np.asarray(reducer.fit_transform(matrix), dtype=np.float64)

        if coordinates.shape != (count, self.config.n_components):
            raise ProjectionError(
                f"UMAP returned {coordinates.shape}, expected {(count, self.config.n_components)}."
            )

        return coordinates

    def _cluster(self, matrix: np.ndarray) -> np.ndarray | None:
        if not self.config.cluster_algorithm or not self.config.cluster_count:
            return None

        if self.config.cluster_algorithm != "kmeans":
            raise ProjectionError(f"Unsupported cluster algorithm: {self.config.cluster_algorithm}")

        from sklearn.cluster import KMeans

        count = min(self.config.cluster_count, matrix.shape[0])

        # Clustered in embedding space, not projection space — the same choice
        # src/Lyrics/04_cluster_export.py makes.
        kmeans = KMeans(n_clusters=count, random_state=self.config.random_seed, n_init=10)
        return np.asarray(kmeans.fit_predict(matrix), dtype=int)

    def _build_artifact(
        self,
        frame: pd.DataFrame,
        coordinates: np.ndarray,
        clusters: np.ndarray | None,
        fingerprint: str,
        embedding_dimension: int,
    ) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []

        for position, (_, row) in enumerate(frame.iterrows()):
            point = coordinates[position]
            node: dict[str, Any] = {
                "doc_id": str(row.get("doc_id", "")),
                "title": _text(row.get("title")),
                "author": _text(row.get("author")),
                "source": _text(row.get("source")),
                "x": round(float(point[0]), COORDINATE_DECIMALS),
                "y": round(float(point[1]), COORDINATE_DECIMALS),
                "z": round(float(point[2]), COORDINATE_DECIMALS),
            }
            node["cluster"] = int(clusters[position]) if clusters is not None else None
            nodes.append(node)

        return {
            "schema_version": PROJECTION_SCHEMA_VERSION,
            "projection": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "dataset_fingerprint": fingerprint,
                "document_count": len(nodes),
                "embedding_dimension": int(embedding_dimension),
                "dimensions": self.config.n_components,
                **self.config.to_dict(),
            },
            "nodes": nodes,
        }

    def _build_stats(
        self,
        coordinates: np.ndarray,
        clusters: np.ndarray | None,
        embedding_dimension: int,
    ) -> ProjectionStats:
        stats = ProjectionStats(
            document_count=int(coordinates.shape[0]),
            embedding_dimension=int(embedding_dimension),
        )

        for axis, name in enumerate(("x", "y", "z")):
            column = coordinates[:, axis]
            stats.bounds[name] = (float(column.min()), float(column.max()))
            stats.axis_variance[name] = float(column.var())

        centre = coordinates.mean(axis=0)
        stats.bounding_sphere_radius = float(
            np.linalg.norm(coordinates - centre, axis=1).max()
        )

        if clusters is not None:
            values, counts = np.unique(clusters, return_counts=True)
            stats.cluster_populations = {
                str(int(value)): int(count) for value, count in zip(values, counts)
            }

        return stats


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

REQUIRED_PROJECTION_KEYS = {
    "generated_at",
    "dataset_fingerprint",
    "document_count",
    "embedding_dimension",
    "algorithm",
    "n_components",
    "metric",
    "n_neighbors",
    "min_dist",
    "random_seed",
}


def validate_artifact(artifact: dict[str, Any], expected_count: int | None = None) -> None:
    """Fail loudly rather than publishing a partial or malformed projection."""
    if not isinstance(artifact, dict):
        raise ProjectionError("Artifact must be a JSON object.")

    if artifact.get("schema_version") != PROJECTION_SCHEMA_VERSION:
        raise ProjectionError(
            f"Unsupported projection schema_version: {artifact.get('schema_version')!r} "
            f"(expected {PROJECTION_SCHEMA_VERSION})."
        )

    projection = artifact.get("projection")
    if not isinstance(projection, dict):
        raise ProjectionError("Artifact is missing the projection metadata object.")

    missing = REQUIRED_PROJECTION_KEYS - set(projection)
    if missing:
        raise ProjectionError(f"Projection metadata is missing: {sorted(missing)}")

    nodes = artifact.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ProjectionError("Artifact contains no nodes.")

    if expected_count is not None and len(nodes) != expected_count:
        raise ProjectionError(
            f"Projected {len(nodes)} node(s) but the index holds {expected_count}."
        )

    if projection.get("document_count") != len(nodes):
        raise ProjectionError(
            f"Metadata document_count={projection.get('document_count')} "
            f"disagrees with {len(nodes)} node(s)."
        )

    seen: set[str] = set()
    seen_positions: set[tuple[float, float, float]] = set()

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ProjectionError(f"Node {index} is not an object.")

        doc_id = node.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id.strip():
            raise ProjectionError(f"Node {index} has a missing or blank doc_id.")
        if doc_id in seen:
            raise ProjectionError(f"Duplicate doc_id in projection: {doc_id}")
        seen.add(doc_id)

        point = []
        for axis in ("x", "y", "z"):
            value = node.get(axis)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ProjectionError(f"Node {doc_id} has a non-numeric {axis}.")
            numeric = float(value)
            if not np.isfinite(numeric):
                raise ProjectionError(f"Node {doc_id} has a non-finite {axis}: {value!r}")
            point.append(numeric)

        position = (point[0], point[1], point[2])
        if position in seen_positions:
            raise ProjectionError(
                f"Duplicate projection coordinate {position} at doc_id {doc_id}; "
                "two documents collapsed onto the same point."
            )
        seen_positions.add(position)


# --------------------------------------------------------------------------
# Atomic write / read
# --------------------------------------------------------------------------


def write_artifact(artifact: dict[str, Any], path: str | Path) -> Path:
    """Write the artifact atomically.

    An interrupted run leaves the previous artifact untouched. The temp file is
    closed before os.replace, which on Windows would otherwise fail with an open
    handle — the same failure mode fixed in `db_source` during T1.5.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    handle, temp_name = tempfile.mkstemp(
        prefix=f"{target.name}.", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temp_name)

    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(artifact, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())

        # Read it back before publishing, so a truncated or corrupted write is
        # caught here rather than by the API at request time.
        validate_artifact(json.loads(temporary.read_text(encoding="utf-8")))

        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return target


def read_artifact(path: str | Path) -> dict[str, Any]:
    """Load and validate an artifact from disk."""
    target = Path(path)

    if not target.exists():
        raise FileNotFoundError(f"Projection artifact not found: {target}")

    try:
        artifact = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectionError(f"Projection artifact is not valid JSON: {target}") from exc

    validate_artifact(artifact)
    return artifact
