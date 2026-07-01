from __future__ import annotations

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    author: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
