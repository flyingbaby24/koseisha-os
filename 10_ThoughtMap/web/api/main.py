from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .schemas import (
    DeleteSavedDocumentResponse,
    EmailSaveDocumentRequest,
    SaveDocumentRequest,
    SaveDocumentResponse,
    SavedDocumentsResponse,
    SavedWorksResponse,
    SearchResponse,
)
from .search_service import get_search_service
from .user_library_service import UserLibraryService


settings = get_settings()
app = FastAPI(title="ThoughtMap API")

# Keep this configurable for local Unity Editor, device testing, and WebGL.
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


# Confirmation examples:
# /search?q=Plato&mode=keyword
# /search?q=Plato&mode=keyword&source=gutendex
# /search?q=Plato&mode=hybrid
# /search?q=Burn&mode=semantic&source=user_suno
# /search?q=Plato&mode=semantic&source=gutendex&filter=general
@app.get("/search", response_model=SearchResponse, response_model_exclude_none=True)
def search(
    q: str = Query(..., min_length=1),
    top: int = Query(10, ge=1, le=50),
    mode: Literal["semantic", "keyword", "hybrid"] = Query("semantic"),
    source: str = Query(""),
    filter: str = Query(""),
) -> SearchResponse:
    service = get_search_service()
    return service.search_response(q, top=top, mode=mode, source=source, filter_name=filter)


@app.post("/users/default/save", response_model=SaveDocumentResponse, response_model_exclude_none=True)
def save_default_document(request: SaveDocumentRequest) -> SaveDocumentResponse:
    try:
        service = UserLibraryService(settings)
        return service.save_document("default", request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/users/by-email/save", response_model=SaveDocumentResponse, response_model_exclude_none=True)
def save_document_by_email(request: EmailSaveDocumentRequest) -> SaveDocumentResponse:
    try:
        service = UserLibraryService(settings)
        return service.save_document_by_email(request.email, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/users/by-email/saved", response_model=SavedWorksResponse, response_model_exclude_none=True)
def list_saved_by_email(email: str = Query(..., min_length=1)) -> SavedWorksResponse:
    try:
        service = UserLibraryService(settings)
        saved = service.list_saved_by_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return SavedWorksResponse(works=saved.items)


@app.delete("/users/by-email/saved/{doc_id}", response_model=DeleteSavedDocumentResponse)
def delete_saved_by_email(doc_id: str, email: str = Query(..., min_length=1)) -> DeleteSavedDocumentResponse:
    try:
        service = UserLibraryService(settings)
        return service.delete_saved_by_email(email, doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/users/default/saved", response_model=SavedDocumentsResponse, response_model_exclude_none=True)
def list_default_saved() -> SavedDocumentsResponse:
    try:
        service = UserLibraryService(settings)
        return service.list_saved("default")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/users/default/saved/{doc_id}", response_model=DeleteSavedDocumentResponse)
def delete_default_saved(doc_id: str) -> DeleteSavedDocumentResponse:
    try:
        service = UserLibraryService(settings)
        return service.delete_saved("default", doc_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
