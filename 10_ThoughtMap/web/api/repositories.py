from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd

from search_utils import parse_embedding
from storage import load_official_db

from .config import ApiSettings


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
        self.db_dir = Path(db_dir) if db_dir is not None else None
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
    """Placeholder boundary for the future SQLite backend."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else None

    def load_index(self) -> pd.DataFrame:
        raise NotImplementedError(
            "SQLite search index loading is not implemented yet. "
            "Use THOUGHTMAP_BACKEND=csv until the SQLite repository is added."
        )


def create_search_index_repository(settings: ApiSettings) -> SearchIndexRepository:
    if settings.backend == "csv":
        return CsvSearchIndexRepository(settings.db_dir)

    if settings.backend == "sqlite":
        return SqliteSearchIndexRepository(settings.db_dir)

    raise ValueError(f"Unsupported THOUGHTMAP_BACKEND: {settings.backend}")
