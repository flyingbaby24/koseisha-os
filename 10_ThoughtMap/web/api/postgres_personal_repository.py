from __future__ import annotations

import json
import uuid
from typing import Any

import pandas as pd
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    insert,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func

from .config import normalize_database_url
from .personal_repository import (
    build_saved_item,
    normalize_parameters,
    row_text,
    saved_document_from_mapping,
)
from .schemas import DeleteSavedDocumentResponse, SaveDocumentResponse, SavedDocumentsResponse


metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email_hash", String(64), nullable=False, unique=True, index=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

saved_works = Table(
    "saved_works",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("doc_id", Text, nullable=False),
    Column("original_doc_id", Text, nullable=False),
    Column("title", Text, nullable=False, default=""),
    Column("author", Text, nullable=False, default=""),
    Column("source", Text, nullable=False, default=""),
    Column("category", Text, nullable=False, default=""),
    Column("url", Text, nullable=True),
    Column("source_url", Text, nullable=True),
    Column("parameters_json", JSON, nullable=True),
    Column("saved_at", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("user_id", "doc_id", name="uq_saved_works_user_doc_id"),
)

saved_embeddings = Table(
    "saved_embeddings",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("doc_id", Text, nullable=False),
    Column("embedding_json", JSON, nullable=False),
    Column("model_name", Text, nullable=False, default=""),
    Column("saved_at", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("user_id", "doc_id", name="uq_saved_embeddings_user_doc_id"),
)


class PostgresPersonalRepository:
    """PostgreSQL-backed Personal library repository."""

    def __init__(self, database_url: str) -> None:
        normalized_url = normalize_database_url(database_url)
        if not normalized_url:
            raise RuntimeError(
                "DATABASE_URL is required when THOUGHTMAP_PERSONAL_BACKEND=postgres"
            )
        self.engine: Engine = create_engine(normalized_url, pool_pre_ping=True)

    def save_document(
        self,
        email_hash: str,
        row: pd.Series,
        saved_at: str,
        parameters: object | None,
    ) -> SaveDocumentResponse:
        user_id = self._get_or_create_user_id(email_hash)
        doc_id = row_text(row, "doc_id")
        if not doc_id:
            raise ValueError("doc_id is required")

        with self.engine.begin() as conn:
            existing = conn.execute(
                select(saved_works).where(
                    saved_works.c.user_id == user_id,
                    saved_works.c.doc_id == doc_id,
                )
            ).mappings().first()
            if existing is not None:
                return SaveDocumentResponse(
                    saved=False,
                    duplicate=True,
                    item=saved_document_from_mapping(self._work_row_to_item(dict(existing))),
                )

            item = build_saved_item(row, saved_at, parameters)
            conn.execute(
                insert(saved_works).values(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    doc_id=item["doc_id"],
                    original_doc_id=item["original_doc_id"],
                    title=item["title"],
                    author=item["author"],
                    source=item["source"],
                    category=item["category"],
                    url=item.get("url"),
                    source_url=item.get("source_url"),
                    parameters_json=item.get("parameters"),
                    saved_at=saved_at,
                )
            )

            embedding_json = self._parse_embedding(row_text(row, "embedding"))
            if embedding_json is not None:
                conn.execute(
                    insert(saved_embeddings).values(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        doc_id=doc_id,
                        embedding_json=embedding_json,
                        model_name=row_text(row, "model_name", row_text(row, "model")),
                        saved_at=saved_at,
                    )
                )

        return SaveDocumentResponse(
            saved=True,
            duplicate=False,
            item=saved_document_from_mapping(item),
        )

    def list_saved(self, email_hash: str) -> SavedDocumentsResponse:
        user_id = self._find_user_id(email_hash)
        if user_id is None:
            return SavedDocumentsResponse(items=[])

        with self.engine.begin() as conn:
            rows = conn.execute(
                select(saved_works)
                .where(saved_works.c.user_id == user_id)
                .order_by(saved_works.c.created_at.desc())
            ).mappings().all()

        return SavedDocumentsResponse(
            items=[saved_document_from_mapping(self._work_row_to_item(dict(row))) for row in rows]
        )

    def delete_saved(self, email_hash: str, doc_id: str) -> DeleteSavedDocumentResponse:
        doc_id = str(doc_id or "").strip()
        user_id = self._find_user_id(email_hash)
        if user_id is None:
            return DeleteSavedDocumentResponse(deleted=False, doc_id=doc_id)

        with self.engine.begin() as conn:
            conn.execute(
                delete(saved_embeddings).where(
                    saved_embeddings.c.user_id == user_id,
                    saved_embeddings.c.doc_id == doc_id,
                )
            )
            result = conn.execute(
                delete(saved_works).where(
                    saved_works.c.user_id == user_id,
                    saved_works.c.doc_id == doc_id,
                )
            )

        return DeleteSavedDocumentResponse(deleted=(result.rowcount or 0) > 0, doc_id=doc_id)

    def _find_user_id(self, email_hash: str) -> str | None:
        with self.engine.begin() as conn:
            return conn.execute(
                select(users.c.id).where(users.c.email_hash == email_hash)
            ).scalar_one_or_none()

    def _get_or_create_user_id(self, email_hash: str) -> str:
        existing = self._find_user_id(email_hash)
        if existing:
            return existing

        user_id = str(uuid.uuid4())
        try:
            with self.engine.begin() as conn:
                conn.execute(insert(users).values(id=user_id, email_hash=email_hash))
        except IntegrityError:
            existing = self._find_user_id(email_hash)
            if existing:
                return existing
            raise
        return user_id

    def _work_row_to_item(self, row: dict[str, Any]) -> dict[str, object]:
        return {
            "doc_id": row.get("doc_id", ""),
            "original_doc_id": row.get("original_doc_id", ""),
            "title": row.get("title", ""),
            "author": row.get("author", ""),
            "source": row.get("source", ""),
            "category": row.get("category", ""),
            "url": row.get("url"),
            "source_url": row.get("source_url"),
            "saved_at": row.get("saved_at", ""),
            "parameters": normalize_parameters(row.get("parameters_json")),
        }

    def _parse_embedding(self, value: str) -> list[float] | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, list):
            return None
        return [float(item) for item in parsed]
