from __future__ import annotations

from typing import Literal
import hashlib
from pathlib import Path

import pandas as pd
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


# Search modes:
# keyword:
#   q is used as a keyword against title / author / doc_id / source.
#
# embedding:
#   target_doc_id is used to fetch an existing embedding.
#   No sentence-transformers runtime encoding is performed.
#
# hybrid:
#   q narrows candidates by keyword.
#   target_doc_id provides the embedding vector for similarity ranking.
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


def make_user_id_from_email(email: str) -> str:
    normalized = str(email or "").strip().lower()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


@app.get("/users/by-email/saved")
def list_saved_by_email(email: str = Query(..., min_length=3)) -> dict:
    user_id = make_user_id_from_email(email)

    base_dir = Path(__file__).resolve().parents[1]
    csv_path = base_dir / "user_data" / user_id / "thoughtmap_embeddings.csv"

    if not csv_path.exists():
        return {
            "user_id": user_id,
            "works": [],
        }

    df = pd.read_csv(csv_path, dtype=str).fillna("")

    works = []
    for _, row in df.iterrows():
        works.append({
            "doc_id": row.get("doc_id", ""),
            "title": row.get("title", ""),
            "author": row.get("author", ""),
            "source": row.get("source", ""),
            "category": row.get("category", ""),
        })

    return {
        "user_id": user_id,
        "works": works,
    }


class SaveEmbeddingsByEmailRequest(BaseModel):
    email: str
    rows: list[dict]


@app.post("/users/by-email/save-embeddings")
def save_embeddings_by_email(
    request: SaveEmbeddingsByEmailRequest,
) -> dict:

    user_id = make_user_id_from_email(request.email)

    if not user_id:
        raise HTTPException(status_code=400, detail="email is required.")

    if not request.rows:
        raise HTTPException(status_code=400, detail="rows are required.")

    base_dir = Path(__file__).resolve().parents[1]
    user_dir = base_dir / "user_data" / user_id
    user_dir.mkdir(parents=True, exist_ok=True)

    csv_path = user_dir / "thoughtmap_embeddings.csv"

    df = pd.DataFrame(request.rows)

    required = {"doc_id", "title", "source", "embedding"}
    missing = required - set(df.columns)

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"missing columns: {sorted(missing)}",
        )

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    return {
        "status": "saved",
        "user_id": user_id,
        "count": len(df),
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
