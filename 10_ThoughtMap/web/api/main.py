from __future__ import annotations

from typing import Literal
import base64
import hashlib
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request

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

GITHUB_REPO = os.getenv("GITHUB_REPO", "flyingbaby24/koseisha-os")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


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


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return headers


def github_user_csv_path(user_id: str) -> str:
    return (
        "10_ThoughtMap/data/thoughtmap_db/users/"
        f"{user_id}/thoughtmap_embeddings.csv"
    )


def github_contents_url(path: str) -> str:
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"


def read_github_file(path: str) -> tuple[str, str]:
    url = github_contents_url(path) + "?" + urllib.parse.urlencode(
        {"ref": GITHUB_BRANCH}
    )

    request = urllib.request.Request(
        url,
        headers=github_headers(),
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))

        content = base64.b64decode(data["content"]).decode("utf-8-sig")
        sha = data.get("sha", "")
        return content, sha

    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "", ""
        raise


def write_github_file(path: str, text: str, message: str) -> dict:
    _old_text, sha = read_github_file(path)

    payload = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8-sig")).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }

    if sha:
        payload["sha"] = sha

    request = urllib.request.Request(
        github_contents_url(path),
        data=json.dumps(payload).encode("utf-8"),
        headers=github_headers(),
        method="PUT",
    )

    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


@app.get("/users/by-email/saved")
def list_saved_by_email(email: str = Query(..., min_length=3)) -> dict:
    user_id = make_user_id_from_email(email)
    path = github_user_csv_path(user_id)

    try:
        text, _sha = read_github_file(path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"failed to read GitHub library: {exc}",
        ) from exc

    if not text:
        return {
            "user_id": user_id,
            "works": [],
        }

    df = pd.read_csv(io.StringIO(text), dtype=str).fillna("")

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

    if not GITHUB_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_TOKEN is not configured.",
        )

    df = pd.DataFrame(request.rows)

    required = {"doc_id", "title", "source", "embedding"}
    missing = required - set(df.columns)

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"missing columns: {sorted(missing)}",
        )

    path = github_user_csv_path(user_id)
    csv_text = df.to_csv(index=False)

    try:
        result = write_github_file(
            path=path,
            text=csv_text,
            message=f"Update ThoughtMap personal library {user_id}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"failed to save GitHub library: {exc}",
        ) from exc

    return {
        "status": "saved",
        "user_id": user_id,
        "count": len(df),
        "path": path,
        "commit": result.get("commit", {}).get("sha", ""),
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
