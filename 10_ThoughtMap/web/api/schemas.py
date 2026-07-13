from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ParameterScore(BaseModel):
    key: str
    value: float


class SearchResult(BaseModel):
    doc_id: str
    title: str
    author: str
    source: str
    similarity: float
    url: str | None = None
    parameters: list[ParameterScore] | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query_parameters: list[ParameterScore] | None = None


class SaveDocumentRequest(BaseModel):
    doc_id: str
    parameters: Any | None = None


class EmailSaveDocumentRequest(SaveDocumentRequest):
    email: str


class SavedDocument(BaseModel):
    doc_id: str
    title: str = ""
    author: str = ""
    source: str = ""
    category: str = ""
    url: str | None = None
    source_url: str | None = None
    saved_at: str = ""
    original_doc_id: str = ""
    parameters: list[ParameterScore] | None = None


class SaveDocumentResponse(BaseModel):
    saved: bool
    duplicate: bool = False
    item: SavedDocument


class SavedDocumentsResponse(BaseModel):
    items: list[SavedDocument]


class SavedWorksResponse(BaseModel):
    works: list[SavedDocument]


class DeleteSavedDocumentResponse(BaseModel):
    deleted: bool
    doc_id: str
