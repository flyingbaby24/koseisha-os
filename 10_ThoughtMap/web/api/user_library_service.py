from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import ApiSettings
from .repositories import PROJECT_ROOT, SearchIndexRepository, create_search_index_repository
from .schemas import (
    DeleteSavedDocumentResponse,
    ParameterScore,
    SaveDocumentRequest,
    SaveDocumentResponse,
    SavedDocument,
    SavedDocumentsResponse,
)


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


class UserLibraryService:
    """Persist selected search results into a local user CSV library."""

    def __init__(
        self,
        settings: ApiSettings,
        repository: SearchIndexRepository | None = None,
        users_dir: str | Path | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository or create_search_index_repository(settings)
        self.users_dir = Path(users_dir) if users_dir is not None else DEFAULT_USERS_DIR

    def save_document(
        self,
        user_id: str,
        request: SaveDocumentRequest,
    ) -> SaveDocumentResponse:
        safe_user_id = self._safe_user_id(user_id)
        doc_id = str(request.doc_id or "").strip()
        if not doc_id:
            raise ValueError("doc_id is required")

        user_dir = self._ensure_user_dir(safe_user_id)
        favorites = self._load_favorites(user_dir)
        existing = self._find_favorite(favorites, doc_id)
        if existing is not None:
            return SaveDocumentResponse(
                saved=False,
                duplicate=True,
                item=self._favorite_to_saved_document(existing),
            )

        row = self._find_source_row(doc_id)
        saved_at = datetime.now(timezone.utc).isoformat()
        item = self._build_favorite(row, saved_at, request.parameters)

        self._append_documents_csv(user_dir, row, saved_at)
        self._append_embeddings_csv(user_dir, row, saved_at)
        favorites.append(item)
        self._write_favorites(user_dir, favorites)

        return SaveDocumentResponse(
            saved=True,
            duplicate=False,
            item=self._favorite_to_saved_document(item),
        )

    def list_saved(self, user_id: str) -> SavedDocumentsResponse:
        user_dir = self._ensure_user_dir(self._safe_user_id(user_id))
        favorites = self._load_favorites(user_dir)
        return SavedDocumentsResponse(
            items=[self._favorite_to_saved_document(item) for item in favorites]
        )

    def delete_saved(self, user_id: str, doc_id: str) -> DeleteSavedDocumentResponse:
        safe_user_id = self._safe_user_id(user_id)
        doc_id = str(doc_id or "").strip()
        user_dir = self._ensure_user_dir(safe_user_id)
        favorites = self._load_favorites(user_dir)
        kept = [item for item in favorites if str(item.get("doc_id", "")) != doc_id]
        deleted = len(kept) != len(favorites)
        if deleted:
            self._write_favorites(user_dir, kept)
            self._remove_csv_row(user_dir / "documents.csv", doc_id)
            self._remove_csv_row(user_dir / "embeddings.csv", doc_id)
        return DeleteSavedDocumentResponse(deleted=deleted, doc_id=doc_id)

    def _find_source_row(self, doc_id: str) -> pd.Series:
        index = self.repository.load_index()
        if "doc_id" not in index.columns:
            raise KeyError("Search index does not contain doc_id")

        matches = index[index["doc_id"].astype(str) == doc_id]
        if matches.empty:
            raise KeyError(f"Document not found: {doc_id}")
        return matches.iloc[0]

    def _build_favorite(
        self,
        row: pd.Series,
        saved_at: str,
        parameters: list[ParameterScore] | None,
    ) -> dict[str, object]:
        doc_id = self._text(row.get("doc_id", ""))
        return {
            "doc_id": doc_id,
            "original_doc_id": doc_id,
            "title": self._text(row.get("title", "")),
            "author": self._text(row.get("author", "")),
            "source": self._text(row.get("source", "")),
            "saved_at": saved_at,
            "parameters": [self._parameter_to_dict(parameter) for parameter in parameters] if parameters else None,
        }

    def _append_documents_csv(self, user_dir: Path, row: pd.Series, saved_at: str) -> None:
        doc_id = self._text(row.get("doc_id", ""))
        csv_path = user_dir / "documents.csv"
        frame = self._read_csv(csv_path, DOCUMENT_COLUMNS)
        if not frame.empty and doc_id in set(frame["doc_id"].astype(str)):
            return

        new_row = {column: self._text(row.get(column, "")) for column in DOCUMENT_COLUMNS}
        new_row["doc_id"] = doc_id
        new_row["original_doc_id"] = doc_id
        new_row["saved_at"] = saved_at
        self._write_csv(csv_path, pd.concat([frame, pd.DataFrame([new_row])], ignore_index=True), DOCUMENT_COLUMNS)

    def _append_embeddings_csv(self, user_dir: Path, row: pd.Series, saved_at: str) -> None:
        doc_id = self._text(row.get("doc_id", ""))
        csv_path = user_dir / "embeddings.csv"
        frame = self._read_csv(csv_path, EMBEDDING_COLUMNS)
        if not frame.empty and doc_id in set(frame["doc_id"].astype(str)):
            return

        new_row = {column: self._text(row.get(column, "")) for column in EMBEDDING_COLUMNS}
        new_row["doc_id"] = doc_id
        new_row["embedding"] = self._text(row.get("embedding", ""))
        new_row["model_name"] = self._text(row.get("model_name", row.get("model", "")))
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

    def _favorite_to_saved_document(self, item: dict[str, object]) -> SavedDocument:
        parameters = item.get("parameters")
        return SavedDocument(
            doc_id=str(item.get("doc_id", "") or ""),
            title=str(item.get("title", "") or ""),
            author=str(item.get("author", "") or ""),
            source=str(item.get("source", "") or ""),
            saved_at=str(item.get("saved_at", "") or ""),
            original_doc_id=str(item.get("original_doc_id", "") or ""),
            parameters=parameters if isinstance(parameters, list) else None,
        )

    def _parameter_to_dict(self, parameter: ParameterScore) -> dict[str, object]:
        if hasattr(parameter, "model_dump"):
            return parameter.model_dump()
        return parameter.dict()

    def _ensure_user_dir(self, user_id: str) -> Path:
        user_dir = self.users_dir / user_id
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

    def _safe_user_id(self, user_id: str) -> str:
        text = str(user_id or "default").strip()
        if not text or text != "default":
            return "default"
        return text

    def _text(self, value: object) -> str:
        if value is None or pd.isna(value):
            return ""
        return str(value)
