from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from .config import ApiSettings
from .repositories import PROJECT_ROOT
from .schemas import (
    DeleteSavedDocumentResponse,
    ParameterScore,
    SaveDocumentResponse,
    SavedDocument,
    SavedDocumentsResponse,
)


DEFAULT_COMPAT_EMAIL = "default@example.local"
DEFAULT_USERS_DIR = PROJECT_ROOT / "data" / "thoughtmap_db" / "users"
DOCUMENT_COLUMNS = [
    "doc_id",
    "title",
    "author",
    "source",
    "source_url",
    "category",
    "subcategory",
    "tags",
    "notes",
    "original_doc_id",
    "saved_at",
]
EMBEDDING_COLUMNS = [
    "doc_id",
    "embedding",
    "model_name",
    "original_doc_id",
    "saved_at",
]


class PersonalRepository(Protocol):
    def save_document(
        self,
        email_hash: str,
        row: pd.Series,
        saved_at: str,
        parameters: object | None,
    ) -> SaveDocumentResponse:
        """Save one source document for a normalized user hash."""

    def list_saved(self, email_hash: str) -> SavedDocumentsResponse:
        """List saved documents for a normalized user hash."""

    def delete_saved(self, email_hash: str, doc_id: str) -> DeleteSavedDocumentResponse:
        """Delete a saved document for a normalized user hash."""


def create_personal_repository(settings: ApiSettings) -> PersonalRepository:
    if settings.personal_backend == "postgres":
        if not str(settings.database_url or "").strip():
            raise RuntimeError(
                "DATABASE_URL is required when THOUGHTMAP_PERSONAL_BACKEND=postgres"
            )
        from .postgres_personal_repository import PostgresPersonalRepository

        return PostgresPersonalRepository(settings.database_url)

    if settings.personal_backend in {"local", "file", "csv"}:
        return LocalFilePersonalRepository()

    raise ValueError(f"Unsupported THOUGHTMAP_PERSONAL_BACKEND: {settings.personal_backend}")


def normalize_email(email: str) -> str:
    normalized = str(email or "").strip().lower()
    if not normalized:
        raise ValueError("email is required")
    return normalized


def email_hash_for(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()


def default_email_hash() -> str:
    return email_hash_for(DEFAULT_COMPAT_EMAIL)


def normalize_parameters(parameters: object | None) -> list[dict[str, object]] | None:
    if parameters is None:
        return None

    if isinstance(parameters, dict):
        normalized = []
        for key, value in parameters.items():
            normalized.append({"key": str(key), "value": float(value)})
        return normalized

    if isinstance(parameters, list):
        normalized = []
        for item in parameters:
            if isinstance(item, ParameterScore):
                item = _model_to_dict(item)
            if not isinstance(item, dict):
                continue
            key = item.get("key")
            value = item.get("value")
            if key is None or value is None:
                continue
            normalized.append({"key": str(key), "value": float(value)})
        return normalized

    return None


def saved_document_from_mapping(item: dict[str, object]) -> SavedDocument:
    parameters = item.get("parameters")
    return SavedDocument(
        doc_id=str(item.get("doc_id", "") or ""),
        title=str(item.get("title", "") or ""),
        author=str(item.get("author", "") or ""),
        source=str(item.get("source", "") or ""),
        category=str(item.get("category", "") or ""),
        url=_optional_text(item.get("url") or item.get("source_url")),
        source_url=_optional_text(item.get("source_url") or item.get("url")),
        saved_at=str(item.get("saved_at", "") or ""),
        original_doc_id=str(item.get("original_doc_id", "") or ""),
        parameters=parameters if isinstance(parameters, list) else None,
    )


def row_text(row: pd.Series | dict[str, object], key: str, default: object = "") -> str:
    value = row.get(key, default)
    if value is None or pd.isna(value):
        return ""
    return str(value)


def build_saved_item(
    row: pd.Series,
    saved_at: str,
    parameters: object | None,
) -> dict[str, object]:
    doc_id = row_text(row, "doc_id")
    source_url = row_text(row, "source_url", row_text(row, "url"))
    return {
        "doc_id": doc_id,
        "original_doc_id": doc_id,
        "title": row_text(row, "title"),
        "author": row_text(row, "author"),
        "source": row_text(row, "source"),
        "category": row_text(row, "category"),
        "url": source_url or None,
        "source_url": source_url or None,
        "saved_at": saved_at,
        "parameters": normalize_parameters(parameters),
    }


class LocalFilePersonalRepository:
    """Legacy local-file personal library repository.

    This remains available for local development only. In Render/postgres mode,
    new saves go through PostgresPersonalRepository instead.
    """

    def __init__(self, users_dir: str | Path | None = None) -> None:
        self.users_dir = Path(users_dir) if users_dir is not None else DEFAULT_USERS_DIR

    def save_document(
        self,
        email_hash: str,
        row: pd.Series,
        saved_at: str,
        parameters: object | None,
    ) -> SaveDocumentResponse:
        user_dir = self._ensure_user_dir(email_hash)
        favorites = self._load_favorites(user_dir)
        doc_id = row_text(row, "doc_id")
        existing = self._find_favorite(favorites, doc_id)
        if existing is not None:
            return SaveDocumentResponse(
                saved=False,
                duplicate=True,
                item=saved_document_from_mapping(existing),
            )

        item = build_saved_item(row, saved_at, parameters)
        self._append_documents_csv(user_dir, row, saved_at)
        self._append_embeddings_csv(user_dir, row, saved_at)
        favorites.append(item)
        self._write_favorites(user_dir, favorites)

        return SaveDocumentResponse(
            saved=True,
            duplicate=False,
            item=saved_document_from_mapping(item),
        )

    def list_saved(self, email_hash: str) -> SavedDocumentsResponse:
        user_dir = self._ensure_user_dir(email_hash)
        favorites = self._load_favorites(user_dir)
        return SavedDocumentsResponse(
            items=[saved_document_from_mapping(item) for item in favorites]
        )

    def delete_saved(self, email_hash: str, doc_id: str) -> DeleteSavedDocumentResponse:
        doc_id = str(doc_id or "").strip()
        user_dir = self._ensure_user_dir(email_hash)
        favorites = self._load_favorites(user_dir)
        kept = [item for item in favorites if str(item.get("doc_id", "")) != doc_id]
        deleted = len(kept) != len(favorites)
        if deleted:
            self._write_favorites(user_dir, kept)
            self._remove_csv_row(user_dir / "documents.csv", doc_id)
            self._remove_csv_row(user_dir / "embeddings.csv", doc_id)
        return DeleteSavedDocumentResponse(deleted=deleted, doc_id=doc_id)

    def _append_documents_csv(self, user_dir: Path, row: pd.Series, saved_at: str) -> None:
        doc_id = row_text(row, "doc_id")
        csv_path = user_dir / "documents.csv"
        frame = self._read_csv(csv_path, DOCUMENT_COLUMNS)
        if not frame.empty and doc_id in set(frame["doc_id"].astype(str)):
            return

        new_row = {column: row_text(row, column) for column in DOCUMENT_COLUMNS}
        new_row["doc_id"] = doc_id
        new_row["original_doc_id"] = doc_id
        new_row["saved_at"] = saved_at
        self._write_csv(csv_path, pd.concat([frame, pd.DataFrame([new_row])], ignore_index=True), DOCUMENT_COLUMNS)

    def _append_embeddings_csv(self, user_dir: Path, row: pd.Series, saved_at: str) -> None:
        doc_id = row_text(row, "doc_id")
        csv_path = user_dir / "embeddings.csv"
        frame = self._read_csv(csv_path, EMBEDDING_COLUMNS)
        if not frame.empty and doc_id in set(frame["doc_id"].astype(str)):
            return

        new_row = {column: row_text(row, column) for column in EMBEDDING_COLUMNS}
        new_row["doc_id"] = doc_id
        new_row["embedding"] = row_text(row, "embedding")
        new_row["model_name"] = row_text(row, "model_name", row_text(row, "model"))
        new_row["original_doc_id"] = doc_id
        new_row["saved_at"] = saved_at
        self._write_csv(csv_path, pd.concat([frame, pd.DataFrame([new_row])], ignore_index=True), EMBEDDING_COLUMNS)

    def _remove_csv_row(self, csv_path: Path, doc_id: str) -> None:
        if not csv_path.exists():
            return
        frame = pd.read_csv(csv_path, dtype=str).fillna("")
        if "doc_id" not in frame.columns:
            return
        frame = frame[frame["doc_id"].astype(str) != doc_id]
        frame.to_csv(csv_path, index=False, encoding="utf-8-sig")

    def _load_favorites(self, user_dir: Path) -> list[dict[str, object]]:
        path = user_dir / "favorites.json"
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw if isinstance(raw, list) else []

    def _write_favorites(self, user_dir: Path, favorites: list[dict[str, object]]) -> None:
        path = user_dir / "favorites.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)

    def _find_favorite(
        self,
        favorites: list[dict[str, object]],
        doc_id: str,
    ) -> dict[str, object] | None:
        for item in favorites:
            if str(item.get("doc_id", "")) == doc_id:
                return item
        return None

    def _ensure_user_dir(self, email_hash: str) -> Path:
        user_key = "default" if email_hash == default_email_hash() else email_hash
        user_dir = self.users_dir / user_key
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _read_csv(self, csv_path: Path, columns: list[str]) -> pd.DataFrame:
        if not csv_path.exists():
            return pd.DataFrame(columns=columns)
        frame = pd.read_csv(csv_path, dtype=str).fillna("")
        for column in columns:
            if column not in frame.columns:
                frame[column] = ""
        return frame[columns]

    def _write_csv(self, csv_path: Path, frame: pd.DataFrame, columns: list[str]) -> None:
        frame = frame.copy()
        for column in columns:
            if column not in frame.columns:
                frame[column] = ""
        frame[columns].to_csv(csv_path, index=False, encoding="utf-8-sig")


def _model_to_dict(model: ParameterScore) -> dict[str, object]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _optional_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
