from __future__ import annotations

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
    parameters: list[ParameterScore] | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query_parameters: list[ParameterScore] | None = None
