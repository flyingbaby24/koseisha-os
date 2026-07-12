from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .schemas import (
    DeleteSavedDocumentResponse,
    SaveDocumentRequest,
    SaveDocumentResponse,
    SavedDocumentsResponse,
    SearchResponse,
)
from .search_service import get_search_service
from .user_embedding_sqlite import (
    list_user_embeddings,
    save_user_embeddings,
)
from .user_library_service import UserLibraryService


settings = get_settings()
app = FastAPI(title="ThoughtMap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "backend": settings.backend}


@app.get("/search", response_model=SearchResponse, response_model_exclude_none=True)
def search(
    q: str = Query("", description="Keyword query. Required for keyword mode. Optional for hybrid."),
    top: int = Query(10, ge=1, le=50),
    mode: Literal["keyword", "embedding", "hybrid"] = Query("keyword"),
    source: str = Query(""),
    category: str = Query(""),
    filter: str = Query(""),
    target_doc_id: str = Query("", description="Existing document id used as the target embedding."),
    user_email: str = Query("", description="Optional user email for personal saved embeddings."),
) -> SearchResponse:
    service = get_search_service()

    if mode == "keyword" and not q.strip():
        raise HTTPException(status_code=400, detail="q is required for keyword mode.")

    if mode in {"embedding", "hybrid"} and not target_doc_id.strip():
        raise HTTPException(status_code=400, detail="target_doc_id is required for embedding/hybrid mode.")

    try:
        return service.search_response(
            q=q,
            top=top,
            mode=mode,
            source=source,
            category=category,
            filter_name=filter,
            target_doc_id=target_doc_id,
            user_email=user_email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/search/filter-options")
def search_filter_options() -> dict[str, list[str]]:
    try:
        return get_search_service().filter_options()
    except (FileNotFoundError, OSError, ValueError):
        return {"sources": ["all"], "categories": ["all"], "parameters": ["general"]}


@app.get("/users/by-email/saved")
def list_saved_by_email(email: str = Query(..., min_length=3)) -> dict:
    try:
        return list_user_embeddings(email)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"failed to read user embeddings: {exc}",
        ) from exc


class SaveEmbeddingsByEmailRequest(BaseModel):
    email: str
    rows: list[dict]


@app.post("/users/by-email/save-embeddings")
def save_embeddings_by_email(request: SaveEmbeddingsByEmailRequest) -> dict:
    try:
        result = save_user_embeddings(
            email=request.email,
            rows=request.rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"failed to save user embeddings: {exc}",
        ) from exc

    return {
        "status": "saved",
        **result,
    }


@app.post("/users/default/save", response_model=SaveDocumentResponse, response_model_exclude_none=True)
def save_default_document(request: SaveDocumentRequest) -> SaveDocumentResponse:
    service = UserLibraryService(settings)
    try:
        return service.save_document("default", request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/users/default/saved", response_model=SavedDocumentsResponse, response_model_exclude_none=True)
def list_default_saved() -> SavedDocumentsResponse:
    service = UserLibraryService(settings)
    return service.list_saved("default")


@app.delete("/users/default/saved/{doc_id}", response_model=DeleteSavedDocumentResponse)
def delete_default_saved(doc_id: str) -> DeleteSavedDocumentResponse:
    service = UserLibraryService(settings)
    return service.delete_saved("default", doc_id)
