from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
import json

import pandas as pd

from .config import ApiSettings
from .personal_repository import (
    DEFAULT_COMPAT_EMAIL,
    PersonalRepository,
    create_personal_repository,
    default_email_hash,
    email_hash_for,
)
from .repositories import SearchIndexRepository, create_search_index_repository
from .schemas import (
    DeleteSavedDocumentResponse,
    SaveDocumentRequest,
    SaveDocumentResponse,
    SavedDocumentsResponse,
)


logger = logging.getLogger(__name__)


class UserLibraryService:
    """Save selected official search results into the Personal repository."""

    def __init__(
        self,
        settings: ApiSettings,
        repository: SearchIndexRepository | None = None,
        personal_repository: PersonalRepository | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository or create_search_index_repository(settings)
        self.personal_repository = personal_repository or create_personal_repository(settings)

    def save_document(
        self,
        user_id: str,
        request: SaveDocumentRequest,
    ) -> SaveDocumentResponse:
        # Compatibility path: historical default user maps to a fixed hash.
        return self.save_document_by_email(DEFAULT_COMPAT_EMAIL, request)

    def list_saved(self, user_id: str) -> SavedDocumentsResponse:
        return self.personal_repository.list_saved(default_email_hash())

    def delete_saved(self, user_id: str, doc_id: str) -> DeleteSavedDocumentResponse:
        return self.personal_repository.delete_saved(default_email_hash(), str(doc_id or "").strip())

    def save_document_by_email(
        self,
        email: str,
        request: SaveDocumentRequest,
    ) -> SaveDocumentResponse:
        started = time.perf_counter()
        doc_id = str(request.doc_id or "").strip()
        if not doc_id:
            raise ValueError("doc_id is required")

        if self._should_use_official_lookup(request):
            lookup_doc_id = str(request.original_doc_id or request.doc_id or "").strip()
            logger.info("Personal service official lookup started doc_id=%s", lookup_doc_id)
            row = self._find_source_row(lookup_doc_id)
            logger.info("Personal service official lookup finished doc_id=%s elapsed=%.3fs", lookup_doc_id, time.perf_counter() - started)
        else:
            row = self._build_request_row(request)
            logger.info("Personal service using request metadata doc_id=%s", doc_id)

        saved_at = datetime.now(timezone.utc).isoformat()
        logger.info("Personal service repository save started doc_id=%s", doc_id)
        response = self.personal_repository.save_document(
            email_hash=email_hash_for(email),
            row=row,
            saved_at=saved_at,
            parameters=request.parameters,
        )
        logger.info(
            "Personal service repository save finished doc_id=%s saved=%s duplicate=%s elapsed=%.3fs",
            doc_id,
            response.saved,
            response.duplicate,
            time.perf_counter() - started,
        )
        return response

    def _should_use_official_lookup(self, request: SaveDocumentRequest) -> bool:
        source_type = str(getattr(request, "source_type", "") or "").strip().lower()
        return source_type == "official"

    def _build_request_row(self, request: SaveDocumentRequest) -> dict[str, object]:
        doc_id = str(request.doc_id or "").strip()
        source_url = str(request.source_url or request.url or "").strip()
        return {
            "doc_id": doc_id,
            "original_doc_id": str(request.original_doc_id or doc_id).strip(),
            "title": str(request.title or doc_id).strip(),
            "author": str(request.author or "").strip(),
            "source": str(request.source or "upload").strip(),
            "category": str(request.category or "").strip(),
            "url": source_url,
            "source_url": source_url,
            "embedding": self._embedding_to_json(request.embedding),
            "model_name": str(request.model_name or "").strip(),
            "text": str(request.text or "").strip(),
            "text_preview": str(request.text_preview or "").strip(),
        }

    def _embedding_to_json(self, embedding: object | None) -> str:
        if embedding is None:
            return ""
        if isinstance(embedding, str):
            return embedding
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()
        try:
            return json.dumps(embedding, ensure_ascii=False)
        except TypeError:
            return ""

    def list_saved_by_email(self, email: str) -> SavedDocumentsResponse:
        return self.personal_repository.list_saved(email_hash_for(email))

    def delete_saved_by_email(self, email: str, doc_id: str) -> DeleteSavedDocumentResponse:
        return self.personal_repository.delete_saved(
            email_hash=email_hash_for(email),
            doc_id=str(doc_id or "").strip(),
        )

    def _find_source_row(self, doc_id: str) -> pd.Series:
        index = self.repository.load_index()
        if "doc_id" not in index.columns:
            raise KeyError("Search index does not contain doc_id")

        matches = index[index["doc_id"].astype(str) == doc_id]
        if matches.empty:
            raise KeyError(f"Document not found: {doc_id}")
        return matches.iloc[0]
