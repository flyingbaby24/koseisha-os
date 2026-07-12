from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

import pandas as pd

from search_utils import parse_embedding
from storage import load_official_db, load_official_parameter_scores

from .config import ApiSettings
from .db_source import OfficialDatabaseSource


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

    def build_payload(row: pd.Series) -> dict:
        payload = {}
        for column in score_columns:
            value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
            if pd.notna(value):
                payload[column] = float(value)
        return payload

    merged["parameter_scores"] = merged.apply(build_payload, axis=1)
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


def _normalize_doc_ids(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if "doc_id" in frame.columns:
        frame["doc_id"] = frame["doc_id"].fillna("").astype(str).str.strip()
        frame = frame[frame["doc_id"] != ""]
    return frame


class SearchIndexRepository(Protocol):
    def load_index(self) -> pd.DataFrame:
        """Return a searchable DataFrame with _embedding_vec prepared."""


class CsvSearchIndexRepository:
    """Current CSV-backed search index loader.

    This is the only API layer class that needs to know about the current CSV
    storage shape. A future SQLite repository should return the same DataFrame
    contract to keep the service and Unity unchanged.
    """

    def __init__(self, db_dir: str | Path | None = None) -> None:
        self.db_dir = _resolve_project_path(db_dir) if db_dir is not None else None
        self._index: pd.DataFrame | None = None

    def load_index(self) -> pd.DataFrame:
        if self._index is not None:
            return self._index

        documents, embeddings, _ = load_official_db(self.db_dir)
        parameter_scores = load_official_parameter_scores(self.db_dir)
        merged = _normalize_doc_ids(documents).merge(_normalize_doc_ids(embeddings), on="doc_id", how="inner")
        merged = _join_parameter_scores(merged, parameter_scores)
        merged = merged.copy()
        merged["_embedding_vec"] = merged["embedding"].map(parse_embedding)
        merged = merged[merged["_embedding_vec"].notna()].reset_index(drop=True)

        self._index = merged
        return self._index


class SqliteSearchIndexRepository:
    """SQLite-backed search index loader.

    The SQLite MVP stores embeddings as TEXT JSON, matching the current CSV
    shape. This repository returns the same DataFrame contract as the CSV
    repository so SearchService and Unity can remain unchanged.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = _resolve_sqlite_path(db_path)
        self._index: pd.DataFrame | None = None

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
        return self._index


def create_search_index_repository(settings: ApiSettings) -> SearchIndexRepository:
    if settings.backend == "csv":
        return CsvSearchIndexRepository(settings.db_dir)

    if settings.backend == "sqlite":
        configured_path = settings.official_db_path or _resolve_sqlite_path(settings.db_dir)
        db_path = OfficialDatabaseSource(configured_path, settings.official_db_url).ensure_local()
        return SqliteSearchIndexRepository(db_path)

    raise ValueError(f"Unsupported THOUGHTMAP_BACKEND: {settings.backend}")
