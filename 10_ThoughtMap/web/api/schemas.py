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


class MapProjectionMetadata(BaseModel):
    """Describes how the projection was produced, for cache and debug purposes."""

    generated_at: str
    dataset_fingerprint: str
    document_count: int
    embedding_dimension: int
    dimensions: int
    algorithm: str
    metric: str
    n_neighbors: int
    min_dist: float
    random_seed: int
    n_components: int | None = None
    cluster_algorithm: str | None = None
    cluster_count: int | None = None


class MapNode(BaseModel):
    """One document's place in the thought space.

    Deliberately not a SearchResult: no similarity, no parameters, no URL.
    The two representations join on doc_id.
    """

    doc_id: str
    title: str = ""
    author: str = ""
    source: str = ""
    x: float
    y: float
    z: float
    cluster: int | None = None


class MapResponse(BaseModel):
    schema_version: int
    projection: MapProjectionMetadata
    nodes: list[MapNode]


class SaveDocumentRequest(BaseModel):
    doc_id: str
    title: str = ""
    author: str = ""
    source: str = ""
    category: str = ""
    url: str | None = None
    source_url: str | None = None
    original_doc_id: str = ""
    embedding: Any | None = None
    text: str = ""
    text_preview: str = ""
    model_name: str = ""
    source_type: str = "upload"
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
    embedding: Any | None = None
    model_name: str = ""
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
