from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    doc_id: str
    title: str
    author: str
    source: str
    similarity: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
