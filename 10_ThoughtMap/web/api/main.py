from __future__ import annotations

import logging
import time
from functools import lru_cache
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
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_user_library_service() -> UserLibraryService:
    return UserLibraryService(settings)

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
    started = time.perf_counter()
    logger.info("Personal save default request started doc_id=%s", request.doc_id)
    try:
        service = get_user_library_service()
        return service.save_document("default", request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        logger.info("Personal save default request finished elapsed=%.3fs", time.perf_counter() - started)


@app.post("/users/by-email/save", response_model=SaveDocumentResponse, response_model_exclude_none=True)
def save_document_by_email(request: EmailSaveDocumentRequest) -> SaveDocumentResponse:
    started = time.perf_counter()
    logger.info("Personal save by-email request started doc_id=%s", request.doc_id)
    try:
        service = get_user_library_service()
        response = service.save_document_by_email(request.email, request)
        logger.info(
            "Personal save by-email response ready doc_id=%s saved=%s duplicate=%s elapsed=%.3fs",
            request.doc_id,
            response.saved,
            response.duplicate,
            time.perf_counter() - started,
        )
        return response
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        logger.info("Personal save by-email request finished elapsed=%.3fs", time.perf_counter() - started)


@app.get("/users/by-email/saved", response_model=SavedWorksResponse, response_model_exclude_none=True)
def list_saved_by_email(email: str = Query(..., min_length=1)) -> SavedWorksResponse:
    try:
        service = get_user_library_service()
        saved = service.list_saved_by_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return SavedWorksResponse(works=saved.items)


@app.delete("/users/by-email/saved/{doc_id}", response_model=DeleteSavedDocumentResponse)
def delete_saved_by_email(doc_id: str, email: str = Query(..., min_length=1)) -> DeleteSavedDocumentResponse:
    try:
        service = get_user_library_service()
        return service.delete_saved_by_email(email, doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/users/default/saved", response_model=SavedDocumentsResponse, response_model_exclude_none=True)
def list_default_saved() -> SavedDocumentsResponse:
    try:
        service = get_user_library_service()
        return service.list_saved("default")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/users/default/saved/{doc_id}", response_model=DeleteSavedDocumentResponse)
def delete_default_saved(doc_id: str) -> DeleteSavedDocumentResponse:
    try:
        service = get_user_library_service()
        return service.delete_saved("default", doc_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
