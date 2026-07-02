from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .schemas import SearchResponse
from .search_service import get_search_service


settings = get_settings()
app = FastAPI(title="ThoughtMap API")

# Keep this configurable for local Unity Editor, device testing, and WebGL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "backend": settings.backend}


# Confirmation examples:
# /search?q=Plato&mode=keyword
# /search?q=Plato&mode=keyword&source=gutendex
# /search?q=Plato&mode=hybrid
# /search?q=Burn&mode=semantic&source=user_suno
@app.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    top: int = Query(10, ge=1, le=50),
    mode: Literal["semantic", "keyword", "hybrid"] = Query("semantic"),
    source: str = Query(""),
) -> SearchResponse:
    service = get_search_service()
    return SearchResponse(results=service.search(q, top=top, mode=mode, source=source))
