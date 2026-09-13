from __future__ import annotations

import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd

from search_utils import parse_embedding
from storage import (
    DEFAULT_OFFICIAL_DB_DIR,
    load_documents,
    load_embeddings,
    load_official_db,
    load_official_parameter_scores,
)

from .config import ApiSettings
from .corpus_manifest import CorpusManifest
from .db_source import OfficialDatabaseSource
from .search_corpus import SearchCorpus, build_search_corpus


logger = logging.getLogger("thoughtmap.repository")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_SQLITE_PATH = (
    PROJECT_ROOT
    / "data"
    / "thoughtmap_db"
    / "official"
    / "thoughtmap.sqlite"
)

PARAMETER_SCORE_METADATA_COLUMNS = {
    "doc_id",
    "title",
    "author",
    "source",
    "source_url",
    "category",
    "subcategory",
    "created_at",
    "updated_at",
}


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _resolve_sqlite_path(db_path: str | Path | None) -> Path:
    if db_path is None:
        return DEFAULT_SQLITE_PATH

    path = _resolve_project_path(db_path)
    if path.suffix:
        return path

    return path / "thoughtmap.sqlite"


def _parameter_score_columns(parameter_scores: pd.DataFrame) -> list[str]:
    score_columns = []

    for column in parameter_scores.columns:
        if column in PARAMETER_SCORE_METADATA_COLUMNS:
            continue

        numeric = pd.to_numeric(parameter_scores[column], errors="coerce")
        if numeric.notna().any():
            score_columns.append(column)

    return score_columns


def _add_parameter_scores_payload(merged: pd.DataFrame, score_columns: list[str]) -> pd.DataFrame:
    if not score_columns:
        return merged

    merged = merged.copy()

    # Convert every score column once, then assemble the per-row dicts.
    #
    # The previous version called pd.to_numeric on a one-element Series per
    # column per row: 638,910 Series constructions at full corpus size, which
    # dominated repository load. Same output, same NaN-dropping rule.
    numeric = merged[score_columns].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=float)
    finite = np.isfinite(values)

    merged["parameter_scores"] = [
        {
            column: float(value)
            for column, value, keep in zip(score_columns, row_values, row_finite)
            if keep
        }
        for row_values, row_finite in zip(values, finite)
    ]
    return merged


def _join_parameter_scores(merged: pd.DataFrame, parameter_scores: pd.DataFrame | None) -> pd.DataFrame:
    if parameter_scores is None or parameter_scores.empty or "doc_id" not in parameter_scores.columns:
        return merged

    parameter_scores = parameter_scores.copy()
    parameter_scores["doc_id"] = parameter_scores["doc_id"].fillna("").astype(str).str.strip()
    parameter_scores = parameter_scores[parameter_scores["doc_id"] != ""]
    merged = merged.copy()
    merged["doc_id"] = merged["doc_id"].fillna("").astype(str).str.strip()
    score_columns = _parameter_score_columns(parameter_scores)
    if not score_columns:
        return merged

    join_columns = ["doc_id", *score_columns]
    scores = parameter_scores[join_columns].copy()
    scores = scores.drop_duplicates("doc_id", keep="last")

    merged = merged.merge(scores, on="doc_id", how="left")
    return _add_parameter_scores_payload(merged, score_columns)


def _sqlite_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


# Bumped when the cache layout changes, so an old cache is ignored rather
# than misread.
VECTOR_CACHE_VERSION = 2


def _vector_cache_path(embeddings_path: Path) -> Path:
    return embeddings_path.with_suffix(embeddings_path.suffix + ".vectors.npz")


def _artifact_identity(embeddings_path: Path, artifact_sha256: str = "") -> dict[str, object]:
    """How this cache decides it belongs to this artifact.

    Two keys, in order of strength:

    - `artifact_sha256` from the corpus manifest. Content-addressed, so a cache
      built on a build machine stays valid after the artifact is copied to a
      server - which is the whole point of shipping the two together (T6 #4).
    - size + mtime_ns. The fallback when no manifest is available. Correct
      locally, but copying a file changes mtime, so it cannot travel.
    """
    stat = embeddings_path.stat()
    return {
        "version": VECTOR_CACHE_VERSION,
        "sha256": str(artifact_sha256 or ""),
        "size": int(stat.st_size),
        "mtime_ns": int(stat.st_mtime_ns),
    }


def _read_cache(
    embeddings_path: Path, artifact_sha256: str = "", *, want_vectors: bool = True
) -> dict[str, "np.ndarray"] | None:
    """Validate the cache beside this artifact and return what was asked for.

    Parsing 63,891 JSON vectors out of a 542 MB CSV costs ~90 s every time the
    process starts. The parse is pure, so its result is cached beside the
    artifact.

    `want_vectors=False` reads the doc_id order and the identity fields and
    leaves the 93.6 MB of vectors on disk. That is what a start does first: the
    order decides *which* matrix is wanted — the stored one as it stands, or a
    reordering of it — and reading 93.6 MB before knowing the answer is how the
    load ends up holding two matrices at once.

    Every rejection path returns None and falls back to parsing, so a stale,
    truncated or corrupt cache costs time and can never produce wrong vectors.
    """
    import numpy as np

    cache = _vector_cache_path(embeddings_path)
    if not cache.exists():
        return None

    try:
        identity = _artifact_identity(embeddings_path, artifact_sha256)
        with np.load(cache, allow_pickle=False) as data:
            if int(data["cache_version"]) != VECTOR_CACHE_VERSION:
                logger.info("Vector cache ignored: written by a different cache version.")
                return None

            cached_sha = str(data["source_sha256"]) if "source_sha256" in data else ""
            if identity["sha256"] and cached_sha:
                # A content match beats file metadata: a copied artifact is
                # still the same artifact, even with a new mtime.
                if cached_sha != identity["sha256"]:
                    logger.info("Vector cache ignored: artifact checksum differs.")
                    return None
                matched_by = "sha256"
            elif (
                int(data["source_size"]) != identity["size"]
                or int(data["source_mtime_ns"]) != identity["mtime_ns"]
            ):
                logger.info("Vector cache ignored: artifact size/mtime differs.")
                return None
            else:
                matched_by = "mtime"

            # `doc_id` is ~1.7 MB and is always read: it is the cache's index.
            doc_id = np.asarray(data["doc_id"])
            if len(doc_id) == 0:
                logger.warning("Vector cache ignored: no documents; reparsing.")
                return None

            if not want_vectors:
                return {"doc_id": doc_id, "matched_by": matched_by}

            vectors = np.asarray(data["vectors"])

            # Corruption detection. np.load validates the zip container and each
            # array header, but not that the two arrays still describe each
            # other, which is what a partial write actually breaks. Checked
            # here, before any caller indexes one by the other.
            if vectors.ndim != 2 or len(doc_id) != len(vectors):
                logger.warning("Vector cache ignored: array shapes disagree; reparsing.")
                return None

            # Materialise inside the `with` so nothing depends on the file
            # handle after it closes.
            return {"doc_id": doc_id, "vectors": vectors, "matched_by": matched_by}
    except Exception as exc:
        logger.warning("Vector cache unreadable (%s); reparsing.", type(exc).__name__)
        return None


def _load_cached_vectors(
    embeddings_path: Path, artifact_sha256: str = ""
) -> dict[str, "np.ndarray"] | None:
    """The whole cache: doc_ids and the vectors they index."""
    return _read_cache(embeddings_path, artifact_sha256, want_vectors=True)


def _load_cache_order(
    embeddings_path: Path, artifact_sha256: str = ""
) -> dict[str, "np.ndarray"] | None:
    """The cache's doc_id order, without reading its vectors."""
    return _read_cache(embeddings_path, artifact_sha256, want_vectors=False)


def cache_positions(doc_ids, cached_doc_ids) -> tuple["np.ndarray", "np.ndarray"]:
    """Where each wanted doc_id sits in the cache.

    Returns `(keep, positions)`: `keep` marks the rows the cache covers, and
    `positions[i]` is the cache row for wanted row *i* (-1 where absent).

    `positions[keep] == arange(keep.sum())` is the question the whole ordered-
    cache design turns on — it means the stored matrix is already this frame's
    matrix, row for row, and can be used without a reordering copy.
    """
    import numpy as np

    index = {doc: position for position, doc in enumerate(cached_doc_ids.tolist())}
    positions = np.fromiter(
        (index.get(doc, -1) for doc in doc_ids),
        dtype=np.int64,
        count=len(doc_ids),
    )
    return positions >= 0, positions


def is_identity_order(positions: "np.ndarray") -> bool:
    """Whether these positions are 0, 1, 2, … — i.e. no reorder is needed."""
    import numpy as np

    return bool(np.array_equal(positions, np.arange(len(positions), dtype=np.int64)))


def _load_cache_vectors_checked(
    embeddings_path: Path, artifact_sha256: str, expected_doc_ids: "np.ndarray"
) -> "np.ndarray | None":
    """Read the cached matrix, re-proving it still belongs to `expected_doc_ids`.

    The order is read in one open and the vectors in another, so in between the
    file could in principle have been replaced — by a concurrent start that
    rewrote it, most plausibly. Identity is therefore re-validated on the second
    open, and the doc_id order is compared against the one the positions were
    computed from. A mismatch returns None and the caller parses instead, which
    is slow and right rather than fast and wrong.
    """
    import numpy as np

    cached = _load_cached_vectors(embeddings_path, artifact_sha256)
    if cached is None:
        logger.warning("Vector cache became unreadable between reads; reparsing.")
        return None

    if not np.array_equal(cached["doc_id"], expected_doc_ids):
        logger.warning("Vector cache changed between reads; reparsing.")
        return None

    vectors = cached["vectors"]
    if vectors.dtype != np.float32:
        # Every writer stores float32. Anything else is a cache this code did
        # not write, and converting it would silently change the values ranking
        # depends on.
        logger.warning(
            "Vector cache holds %s, not float32; reparsing.", vectors.dtype
        )
        return None
    return vectors


def _store_cached_vectors(
    embeddings_path: Path, doc_ids, vectors, artifact_sha256: str = ""
) -> None:
    """Write the cache atomically beside the artifact.

    Atomic because a process killed mid-write would otherwise leave a truncated
    .npz that every later start has to discover and discard. The temporary file
    is replaced into place in one operation, so a reader sees either the old
    cache or the complete new one - never half of either.
    """
    import numpy as np

    cache = _vector_cache_path(embeddings_path)
    temporary = cache.with_suffix(cache.suffix + ".tmp{}".format(os.getpid()))

    try:
        identity = _artifact_identity(embeddings_path, artifact_sha256)
        with temporary.open("wb") as handle:
            np.savez(
                handle,
                doc_id=np.asarray(doc_ids, dtype=object).astype("U"),
                vectors=np.asarray(vectors, dtype=np.float32),
                cache_version=np.int64(VECTOR_CACHE_VERSION),
                source_sha256=np.str_(identity["sha256"]),
                source_size=np.int64(identity["size"]),
                source_mtime_ns=np.int64(identity["mtime_ns"]),
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, cache)
        logger.info("Vector cache written: %s", cache)
    except Exception as exc:
        # A read-only or full artifact directory is not a failure; the next
        # start simply parses again.
        logger.info("Vector cache not written (%s).", type(exc).__name__)
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


#: Columns the search runtime actually reads. Everything else is dropped after
#: the corpus is loaded.
#:
#: The documents master carries 40 columns because it is also the ingestion and
#: reconciliation record - provenance, external identifiers, timestamps, import
#: status. None of that reaches an API response or influences a ranking, and at
#: 63,891 rows the unread columns cost 33 MB of resident memory.
#:
#: Derived from, and kept in step with:
#:   search_utils.RESULT_COLUMNS            what a result row carries
#:   search_utils.OPTIONAL_PARAMETER_COLUMNS the radar payload
#:   search_service.KEYWORD_COLUMNS          what keyword search scores against
#:   the metadata filters (source, category)
RUNTIME_COLUMNS: frozenset[str] = frozenset(
    {
        # identity and result payload
        "doc_id",
        "title",
        "author",
        "source",
        "source_url",
        "url",
        "gutenberg_id",
        "category",
        "subcategory",
        "model_name",
        # keyword scoring
        "tags",
        "notes",
        # radar payload
        "parameters",
        "parameter_scores",
        "filter_scores",
        "composition",
        "thought_composition",
        "scores",
        # vectors
        "embedding",
        "_embedding_vec",
        "_matrix_row",
    }
)


def _drop_unused_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep only the columns the runtime reads.

    Returns a frame that no longer references the dropped column data, so the
    strings behind them become collectable. Uses a copy rather than an in-place
    drop: an in-place drop on a frame built by `merge` can leave the original
    block manager alive and free nothing.
    """
    unused = [column for column in frame.columns if column not in RUNTIME_COLUMNS]
    if not unused:
        return frame

    kept = frame.drop(columns=unused).copy()
    logger.info(
        "Dropped %d unused corpus columns, kept %d", len(unused), len(kept.columns)
    )
    return kept


def _official_documents_path(db_dir: Path | None) -> Path:
    base = Path(db_dir) if db_dir is not None else DEFAULT_OFFICIAL_DB_DIR
    return base / "documents_master.csv"


def _normalize_doc_ids(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if "doc_id" in frame.columns:
        frame["doc_id"] = frame["doc_id"].fillna("").astype(str).str.strip()
        frame = frame[frame["doc_id"] != ""]
    return frame


class SearchIndexRepository(Protocol):
    def load_index(self) -> pd.DataFrame:
        """Return a searchable DataFrame with _embedding_vec prepared."""

    def load_corpus(self) -> "SearchCorpus":
        """Return the same rows with their embedding matrix prepared once."""


class CsvSearchIndexRepository:
    """Current CSV-backed search index loader.

    This is the only API layer class that needs to know about the current CSV
    storage shape. A future SQLite repository should return the same DataFrame
    contract to keep the service and Unity unchanged.
    """

    def __init__(
        self,
        db_dir: str | Path | None = None,
        embeddings_path: str | Path | None = None,
    ) -> None:
        self.db_dir = _resolve_project_path(db_dir) if db_dir is not None else None
        # The embedding artifact lives outside version control at full corpus
        # size, so its location is configurable independently of the documents.
        self.embeddings_path = (
            _resolve_project_path(embeddings_path) if embeddings_path is not None else None
        )
        self._index: pd.DataFrame | None = None
        self._corpus: SearchCorpus | None = None
        self._artifact_sha256 = ""
        self._corpus_version = ""
        self._cached_vectors: dict[str, "np.ndarray"] | None = None
        # Wall time of each load stage, in milliseconds. Written on the one
        # real load so startup can be profiled without a parallel copy of this
        # code that could drift from it (T6 #8).
        self.load_stages: dict[str, float] = {}

    @contextmanager
    def _stage(self, name: str):
        started = time.perf_counter()
        try:
            yield
        finally:
            self.load_stages[name] = (time.perf_counter() - started) * 1000.0

    def load_index(self) -> pd.DataFrame:
        if self._index is not None:
            return self._index

        with self._stage("manifest"):
            manifest = CorpusManifest.load(
                _official_documents_path(self.db_dir).parent
            )

        if self.embeddings_path is None:
            with self._stage("documents_and_embeddings"):
                documents, embeddings, _ = load_official_db(self.db_dir)
        else:
            if not self.embeddings_path.exists():
                raise FileNotFoundError(
                    f"Configured embedding artifact not found: {self.embeddings_path}. "
                    "Set THOUGHTMAP_EMBEDDINGS_PATH to the external embedding master, "
                    "or unset it to use embeddings_master.csv beside the documents."
                )
            # Read the documents alone. Going through load_official_db here
            # would also read and validate the *superseded* local embeddings
            # file, wasting the read and emitting alignment warnings about a
            # file that is about to be replaced.
            # Catch the wrong artifact before spending a minute reading it.
            with self._stage("artifact_validation"):
                if manifest is not None:
                    manifest.check_artifact_file(self.embeddings_path)
                    self._artifact_sha256 = manifest.embedding_artifact_sha256
                    self._corpus_version = manifest.corpus_version

            with self._stage("documents_load"):
                documents = load_documents(_official_documents_path(self.db_dir))

            with self._stage("vector_cache"):
                # Order only. The vectors are read later, once the merge has
                # settled and it is known whether the stored matrix is already
                # the one this frame needs.
                self._cached_vectors = _load_cache_order(
                    self.embeddings_path, self._artifact_sha256
                )

            if self._can_skip_artifact_read(manifest):
                # The cache already holds every doc_id and vector in the
                # artifact, and its checksum proves it was built from this
                # exact artifact - the same checksum the manifest pins. Reading
                # 542 MB of CSV to recover strings we would immediately discard
                # is the single largest avoidable cost in a restart: it is the
                # difference between a ~50 s and a ~8 s corpus load, and it
                # keeps roughly 700 MB of embedding text out of the process.
                with self._stage("embeddings_from_cache"):
                    embeddings = pd.DataFrame(
                        {
                            "doc_id": self._cached_vectors["doc_id"],
                            "model_name": manifest.embedding_model,
                        }
                    )
            else:
                with self._stage("embeddings_read"):
                    embeddings = load_embeddings(self.embeddings_path)

        with self._stage("parameters_load"):
            parameter_scores = load_official_parameter_scores(self.db_dir)

        with self._stage("merge"):
            document_count = len(_normalize_doc_ids(documents))
            merged = _normalize_doc_ids(documents).merge(_normalize_doc_ids(embeddings), on="doc_id", how="inner")

        # The searchable corpus is the intersection. Since the embedding
        # artifact lives outside version control, the common misconfiguration is
        # a full documents master paired with a partial embedding file — which
        # would otherwise silently serve a fraction of the corpus.
        if manifest is not None:
            manifest.check_loaded_corpus(len(merged), document_count)
            if "model_name" in merged.columns:
                manifest.check_model(set(merged["model_name"].dropna().astype(str)))
        elif document_count and len(merged) < document_count * 0.9:
            logger.warning(
                "Only %d of %d documents have an embedding. The embedding artifact "
                "is probably stale or unset; point THOUGHTMAP_EMBEDDINGS_PATH at the "
                "artifact named in corpus_manifest.json.",
                len(merged),
                document_count,
            )
        with self._stage("parameter_join"):
            merged = _join_parameter_scores(merged, parameter_scores)
            merged = merged.copy()

        with self._stage("vectors"):
            merged, prepared_matrix = self._vectors_from_cache(merged)
            if prepared_matrix is None:
                merged["_embedding_vec"] = self._parse_vectors(merged)
                merged = merged[merged["_embedding_vec"].notna()].reset_index(drop=True)

        # Narrow the frame before anything else holds a reference to it.
        with self._stage("drop_unused_columns"):
            merged = _drop_unused_columns(merged)

        # Stack the embedding matrix once, here, rather than once per search.
        # This is the only place it is built (T7 #10-#11). When the cache was
        # already in this frame's order, `prepared_matrix` *is* that matrix and
        # nothing is stacked at all.
        with self._stage("matrix"):
            self._corpus = build_search_corpus(
                merged, self._corpus_version, matrix=prepared_matrix
            )
            prepared_matrix = None

        # The corpus frame *is* the index. Keeping `merged` as well would hold
        # a second DataFrame plus the 63,891 independently allocated vectors
        # the corpus has already replaced with views into its matrix — about
        # 100 MB retained for nothing.
        # `merged` itself still references the 63,891 original arrays; letting
        # it fall out of scope at return frees them, leaving only the matrix.
        self._index = self._corpus.frame

        # The per-document vectors now live in the frame and the matrix; the
        # cache copy would be a third full copy held for nothing.
        self._cached_vectors = None
        logger.info(
            "Search index loaded documents=%d matrix=%.1fMB stages=%s",
            len(self._index),
            self._corpus.matrix_bytes / (1024 * 1024) if self._corpus else 0.0,
            {name: round(value, 1) for name, value in self.load_stages.items()},
        )
        return self._index

    def load_corpus(self) -> SearchCorpus:
        """The frame and its prepared matrix. Loads on first call, then reused."""
        self.load_index()
        assert self._corpus is not None
        return self._corpus

    def _can_skip_artifact_read(self, manifest: CorpusManifest | None) -> bool:
        """May the embedding CSV be left unread this start?

        Only when all three hold:

        - a manifest exists, so there is a pinned expected corpus at all;
        - the artifact on disk matched that manifest's recorded size;
        - the cache matched by **checksum**, not merely by size and mtime.

        The checksum requirement is what makes this safe rather than merely
        fast. Matching on mtime says "probably the same file on this machine";
        matching on content says "this is the artifact the manifest describes",
        which is the same claim the guard makes before search is allowed to run
        at all. Anything weaker falls back to reading the artifact.
        """
        return (
            manifest is not None
            and bool(self._artifact_sha256)
            and self._cached_vectors is not None
            and self._cached_vectors.get("matched_by") == "sha256"
        )

    def _vectors_from_cache(
        self, merged: pd.DataFrame
    ) -> tuple[pd.DataFrame, "np.ndarray | None"]:
        """Serve the search matrix straight out of the cache when the order fits.

        The expensive moment in a corpus load used to be here. The cache stored
        vectors in whatever order the artifact happened to have; the frame
        wanted them in corpus order; so the load built a second 93.6 MB matrix
        by reordering the first, and for as long as that took, the process held
        both. Measured, `build_search_corpus` spiked +189 MB against 308 MB
        retained — the largest transient in the whole startup.

        So the cache is written in corpus order instead. When it still matches —
        which is every start after the first — `positions` is 0, 1, 2, … and
        the array that comes off disk *is* the search matrix. Nothing is
        stacked, nothing is reordered, and exactly one matrix exists.

        When it does not match, this reorders once and rewrites the cache in the
        new order, so the next start is back on the fast path. That is also how
        a cache written before this change migrates: no rebuild from the 542 MB
        artifact, just one reordering write.

        Returns `(frame, matrix)`. A `None` matrix means "fall back to parsing",
        and the frame comes back untouched so the caller can do exactly that.
        """
        import numpy as np

        cached = self._cached_vectors
        if cached is None:
            return merged, None

        keep, positions = cache_positions(merged["doc_id"], cached["doc_id"])
        covered = int(keep.sum())
        if covered == 0:
            # The cache and the documents have nothing in common. Something is
            # badly misconfigured; parsing will produce the right answer or a
            # clear failure, and either beats guessing here.
            logger.warning("Vector cache covers none of the merged documents; reparsing.")
            return merged, None

        if covered != len(merged):
            # Rows the cache does not cover are exactly the rows the old
            # `notna()` filter dropped.
            merged = merged[keep].reset_index(drop=True)
            positions = positions[keep]

        vectors = _load_cache_vectors_checked(
            self.embeddings_path, self._artifact_sha256, cached["doc_id"]
        )
        if vectors is None:
            return merged, None

        self.load_stages["vector_source"] = 1.0  # cache hit

        if is_identity_order(positions):
            matrix = vectors
            self.load_stages["vector_reorder"] = 0.0
            logger.info(
                "Vector cache is in corpus order: %d vectors used as the search "
                "matrix directly, no reorder copy.",
                len(matrix),
            )
        else:
            # One copy, unavoidable: a permutation cannot be applied in place.
            # `vectors` dies with this frame, leaving only `matrix`.
            started = time.perf_counter()
            matrix = np.ascontiguousarray(vectors[positions], dtype=np.float32)
            del vectors
            self.load_stages["vector_reorder"] = (time.perf_counter() - started) * 1000.0
            logger.info(
                "Vector cache was not in corpus order; reordered %d vectors and "
                "rewriting the cache so the next start does not have to.",
                len(matrix),
            )
            _store_cached_vectors(
                self.embeddings_path,
                merged["doc_id"].tolist(),
                matrix,
                self._artifact_sha256,
            )

        # The doc_id index has done its job; the matrix is the only copy now.
        self._cached_vectors = None
        return merged, matrix

    def _parse_vectors(self, merged: pd.DataFrame) -> pd.Series:
        """Vectors for the merged frame, from cache when it is valid."""
        import numpy as np

        if self.embeddings_path is None:
            return merged["embedding"].map(parse_embedding)

        cached = self._cached_vectors
        if cached is not None:
            lookup = dict(zip(cached["doc_id"].tolist(), cached["vectors"]))
            if all(doc_id in lookup for doc_id in merged["doc_id"]):
                self.load_stages["vector_source"] = 1.0  # cache hit
                return pd.Series(
                    [lookup[doc_id] for doc_id in merged["doc_id"]], index=merged.index
                )

        if "embedding" not in merged.columns:
            # Only reachable if the cache covered the artifact well enough to
            # skip the read, then failed to cover the merged frame. Re-read
            # rather than serve a partial corpus.
            raise RuntimeError(
                "The vector cache did not cover every document after the join. "
                f"Delete {_vector_cache_path(self.embeddings_path)} and restart "
                "to rebuild it from the artifact."
            )

        self.load_stages["vector_source"] = 0.0  # parsed from the artifact
        vectors = merged["embedding"].map(parse_embedding)

        usable = vectors.notna()
        if usable.any():
            lengths = {len(v) for v in vectors[usable]}
            # Only a rectangular set can be cached as one array; a ragged set is
            # a data defect and is left to the normal path.
            if len(lengths) == 1:
                _store_cached_vectors(
                    self.embeddings_path,
                    merged.loc[usable, "doc_id"].tolist(),
                    np.stack(vectors[usable].to_list()),
                    self._artifact_sha256,
                )

        return vectors


class SqliteSearchIndexRepository:
    """SQLite-backed search index loader.

    The SQLite MVP stores embeddings as TEXT JSON, matching the current CSV
    shape. This repository returns the same DataFrame contract as the CSV
    repository so SearchService and Unity can remain unchanged.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = _resolve_sqlite_path(db_path)
        self._index: pd.DataFrame | None = None
        self._corpus: SearchCorpus | None = None

    def load_index(self) -> pd.DataFrame:
        if self._index is not None:
            return self._index

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"SQLite database not found: {self.db_path}. "
                "Create it with api.migrate_csv_to_sqlite first."
            )

        with sqlite3.connect(self.db_path) as conn:
            merged = pd.read_sql_query(
                """
                SELECT
                    documents.*,
                    embeddings.embedding,
                    embeddings.model_name
                FROM documents
                INNER JOIN embeddings
                    ON TRIM(CAST(documents.doc_id AS TEXT)) = TRIM(CAST(embeddings.doc_id AS TEXT))
                """,
                conn,
            )
            parameter_scores = None
            if _sqlite_table_exists(conn, "parameter_scores"):
                parameter_scores = pd.read_sql_query(
                    "SELECT * FROM parameter_scores",
                    conn,
                )

        # Older SQLite files predate the parameter_scores table. Keep the
        # documented CSV sidecar usable until the next migration refreshes DB.
        if parameter_scores is None:
            parameter_scores = load_official_parameter_scores(self.db_path.parent)

        merged = merged.copy()
        merged = _join_parameter_scores(merged, parameter_scores)
        merged["_embedding_vec"] = merged["embedding"].map(parse_embedding)
        merged = merged[merged["_embedding_vec"].notna()].reset_index(drop=True)

        self._index = merged
        self._corpus = build_search_corpus(merged)
        return self._index

    def load_corpus(self) -> SearchCorpus:
        self.load_index()
        assert self._corpus is not None
        return self._corpus


def create_search_index_repository(settings: ApiSettings) -> SearchIndexRepository:
    if settings.backend == "csv":
        return CsvSearchIndexRepository(settings.db_dir, settings.embeddings_path)

    if settings.backend == "sqlite":
        # These two settings belong to a SQLite deployment that the CSV
        # runtime does not define. getattr keeps a wrong THOUGHTMAP_BACKEND
        # from failing with an AttributeError that names neither problem.
        configured_path = getattr(settings, "official_db_path", None) or _resolve_sqlite_path(
            settings.db_dir
        )
        db_url = getattr(settings, "official_db_url", "")
        db_path = OfficialDatabaseSource(configured_path, db_url).ensure_local()
        return SqliteSearchIndexRepository(db_path)

    raise ValueError(f"Unsupported THOUGHTMAP_BACKEND: {settings.backend}")
