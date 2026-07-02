from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

import pandas as pd

from search_utils import parse_embedding
from storage import load_official_db

from .config import ApiSettings


PROJECT_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_SQLITE_PATH = (
    PROJECT_ROOT
    / "data"
    / "thoughtmap_db"
    / "official"
    / "thoughtmap.sqlite"
)


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
        merged = documents.merge(embeddings, on="doc_id", how="inner")
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
                    ON documents.doc_id = embeddings.doc_id
                """,
                conn,
            )

        merged = merged.copy()
        merged["_embedding_vec"] = merged["embedding"].map(parse_embedding)
        merged = merged[merged["_embedding_vec"].notna()].reset_index(drop=True)

        self._index = merged
        return self._index


def create_search_index_repository(settings: ApiSettings) -> SearchIndexRepository:
    if settings.backend == "csv":
        return CsvSearchIndexRepository(settings.db_dir)

    if settings.backend == "sqlite":
        return SqliteSearchIndexRepository(settings.db_dir)

    raise ValueError(f"Unsupported THOUGHTMAP_BACKEND: {settings.backend}")
