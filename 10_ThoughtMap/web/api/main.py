from __future__ import annotations

import logging
import os
import platform
import threading
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import WARMUP_OFF, get_settings
from .embedding_model import EmbeddingModelUnavailableError
from .query_encoder import describe_encoder, get_query_encoder
from .map_projection import DEFAULT_ARTIFACT_PATH
from .map_response_cache import (
    MapPayloadUnavailableError,
    MapResponseCache,
    accepts_gzip,
)
from .map_service import ProjectionUnavailableError, get_map_service
from .observability import (
    configure_logging,
    install_access_log_redaction,
    log_event,
    query_fingerprint,
    request_timings,
)
from .rate_limit import RateLimiter, client_key
from .readiness import (
    ReadinessState,
    evaluate_configuration,
    evaluate_manifest,
    evaluate_projection,
    evaluate_query_encoder,
    run_warmup,
)
from .schemas import (
    DeleteSavedDocumentResponse,
    EmailSaveDocumentRequest,
    MapResponse,
    SaveDocumentRequest,
    SaveDocumentResponse,
    SavedDocumentsResponse,
    SavedWorksResponse,
    SearchResponse,
)
from .search_service import get_search_service
from .user_library_service import UserLibraryService


settings = get_settings()
logger = logging.getLogger(__name__)
configure_logging()
# Uvicorn's access log records the full request target, which for /search
# and the library routes contains the query text and a person's Personal
# Library address. Redact those values before anything is written.
install_access_log_redaction()

readiness = ReadinessState(settings)
# Rebuilding the /map payload costs an 87 MB transient. Development may pay it
# to keep a hand-built artifact working; a public instance may not, and says so
# through readiness instead.
_map_cache = MapResponseCache(
    allow_rebuild=not settings.is_public,
    verify_checksums=settings.verify_map_sidecar_checksums,
)
_search_limiter = RateLimiter(settings.search_rate_limit, settings.search_rate_burst)


def _manifest_directory():
    from .repositories import _official_documents_path

    return _official_documents_path(settings.db_dir).parent


def _evaluate_static_checks() -> None:
    """Everything that can be known without loading the corpus."""
    evaluate_configuration(readiness, settings)
    evaluate_query_encoder(readiness, settings)
    manifest = evaluate_manifest(readiness, settings, _manifest_directory())
    evaluate_projection(
        readiness,
        settings,
        DEFAULT_ARTIFACT_PATH,
        manifest.document_count if manifest else 0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start serving immediately; become ready in the background.

    The corpus load and the model load together take long enough that doing
    them inline would make the process look hung to a platform health check.
    They run on a worker thread instead, so `/health` answers from the first
    moment and `/ready` reports honestly until the work is done (T6 §9).
    """
    if os.environ.get("RENDER") == "true":
        from .verify_python_runtime import verify_runtime
        verify_runtime()
    started = time.perf_counter()
    _evaluate_static_checks()
    readiness.record_stage("static_checks", (time.perf_counter() - started) * 1000.0)

    log_event(
        "startup",
        python_version=platform.python_version(),
        mode=settings.deployment_mode,
        warmup=settings.warmup,
        backend=settings.backend,
        library_enabled=settings.library_enabled,
        origins=len(settings.allowed_origins),
    )

    if settings.warmup == WARMUP_OFF:
        run_warmup(readiness, settings, lambda: [], lambda: None)
    else:
        # Claimed here, not inside the thread: between starting a thread and
        # its first statement there is a window in which the checks would be
        # absent, and an absent check cannot block readiness.
        readiness.expect("search_engine", "embedding_model")
        worker = threading.Thread(
            target=run_warmup,
            args=(
                readiness,
                settings,
                lambda: get_search_service().repository.load_corpus().frame,
                lambda: get_query_encoder(settings),
                lambda: _map_cache.get_for(get_map_service()),
            ),
            name="thoughtmap-warmup",
            daemon=True,
        )
        worker.start()

    yield

    log_event("shutdown", mode=settings.deployment_mode)


app = FastAPI(title="ThoughtMap API", lifespan=lifespan)


@lru_cache(maxsize=1)
def get_user_library_service() -> UserLibraryService:
    return UserLibraryService(settings)


def _require_library() -> UserLibraryService:
    """Gate every Personal Library route on the deployment's own policy.

    The library authenticates nobody (T6 §22). Where that is not acceptable the
    routes must not work at all, not merely be hidden in the UI — a hidden
    button is not a boundary.
    """
    if not settings.library_enabled:
        raise HTTPException(
            status_code=404,
            detail="The Personal Library is not available in this deployment.",
        )
    return get_user_library_service()


# Compresses whatever the routes have not compressed themselves. /map is the
# large payload and now ships its own pre-built gzip body, so what remains here
# is search and library responses; the threshold keeps the small ones
# uncompressed, where the CPU cost would outweigh the gain.
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Explicit origins outside development. `config` refuses to expand an unset
# variable into "*", so a public deployment that forgot to configure this
# allows nothing and says so in /ready rather than allowing everything.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never let a traceback reach a browser (T6 §26, §36).

    The detail goes to the log with its stack; the client gets a stable
    sentence it can show a person.
    """
    logger.exception("Unhandled error path=%s", request.url.path)
    log_event("error.unhandled", path=request.url.path, error=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content={"detail": "The ThoughtMap API hit an internal error. Please try again."},
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness only. Must stay cheap and must never depend on the corpus."""
    return {"status": "ok", "backend": settings.backend}


@app.get("/ready")
def ready(response: Response) -> dict[str, object]:
    """Readiness: is the canonical corpus usable on this instance?

    Reads the state the warmup task wrote. No file is re-read and no corpus is
    re-validated here, so this stays safe to poll (T6 §7).
    """
    snapshot = readiness.snapshot()
    response.headers["Cache-Control"] = "no-store"
    if not snapshot["ready"]:
        response.status_code = 503
    return snapshot


@app.get("/config")
def deployment_config(response: Response) -> dict[str, object]:
    """What this instance offers, for the frontend to configure itself from.

    Feature availability lives here rather than being re-derived in the UI, so
    "is the Personal Library on" has exactly one answer (T6 §45).
    """
    response.headers["Cache-Control"] = "no-store"
    snapshot = readiness.snapshot()
    encoder = describe_encoder(settings)
    return {
        **settings.features(),
        "corpus_version": snapshot.get("corpus_version", ""),
        # Identifies the exact ranking behaviour this instance produces, so a
        # bug report can name the encoder that produced it.
        "encoder_provider": encoder["provider"],
        "encoder_model_id": encoder["model_id"],
        "encoder_revision": encoder["revision"][:12],
    }


# Confirmation examples:
# /search?q=Plato&mode=keyword
# /search?q=Plato&mode=keyword&source=gutendex
# /search?q=Plato&mode=hybrid
# /search?q=Burn&mode=semantic&source=user_suno
# /search?q=Plato&mode=semantic&source=gutendex&filter=general
@app.get("/search", response_model=SearchResponse, response_model_exclude_none=True)
def search(
    request: Request,
    response: Response,
    q: str = Query(..., min_length=1),
    top: int = Query(10, ge=1, le=50),
    mode: Literal["semantic", "keyword", "hybrid"] = Query("semantic"),
    source: str = Query(""),
    filter: str = Query(""),
    target_doc_id: str = Query(""),
    user_email: str = Query(""),
) -> SearchResponse:
    # Refuse before any expensive work: the point of a limit is that a
    # refused request costs the backend nothing.
    allowed, retry_after = _search_limiter.allow(
        client_key(
            request.client.host if request.client else None,
            request.headers.get("x-forwarded-for"),
            settings.trust_proxy_headers,
        )
    )
    if not allowed:
        log_event("search.rate_limited", retry_after_s=retry_after)
        raise HTTPException(
            status_code=429,
            detail="Too many searches from this client. Please wait a moment.",
            headers={"Retry-After": str(max(1, int(retry_after + 0.999)))},
        )

    service = get_search_service()
    # A search response can depend on the caller (user_email), and query
    # cardinality makes shared caching a poor trade anyway (T6 §21).
    response.headers["Cache-Control"] = "no-store"

    started = time.perf_counter()
    with request_timings() as timings:
        try:
            payload = service.search_response(
                q,
                top=top,
                mode=mode,
                source=source,
                filter_name=filter,
                target_doc_id=target_doc_id,
                user_email=user_email,
            )
            result_count = len(payload.results)
        except EmbeddingModelUnavailableError as exc:
            # The deployment cannot embed text. Keyword search still works, so
            # this is a capability gap on this instance, not a malformed request.
            log_event("search.unavailable", mode=mode, error=type(exc).__name__)
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        total_ms = (time.perf_counter() - started) * 1000.0
        log_event(
            "search",
            mode=mode,
            source=source or "all",
            filter=filter or "none",
            top=top,
            results=result_count,
            query_len=len(q),
            query=query_fingerprint(q),
            search_total_ms=total_ms,
            index_ms=timings.get("index_ms"),
            embedding_ms=timings.get("embedding_ms"),
            profile_ms=timings.get("profile_ms"),
            ranking_ms=timings.get("ranking_ms"),
            response_build_ms=timings.get("response_build_ms"),
        )

    return payload


# Read-only. Serves the artifact written by `api.generate_map_projection`;
# it never runs UMAP, so this route stays fast regardless of corpus size.
#
# The response is pre-encoded and pre-compressed per corpus version
# (`map_response_cache`), so a warm request writes bytes rather than
# re-validating and re-serializing 63,891 nodes. `response_model` is therefore
# documentation here — the route returns a Response directly — and MapResponse
# remains the schema of record for the OpenAPI contract and for tests.
@app.get("/map", response_model=MapResponse, response_model_exclude_none=False)
def map_projection(request: Request) -> Response:
    started = time.perf_counter()
    try:
        # Opens the response prepared at projection time. In a public
        # deployment this never parses the artifact; a missing or stale
        # prepared response is a 503 with the command that fixes it, which
        # readiness has already reported.
        encoded = _map_cache.get_for(get_map_service())
    except (ProjectionUnavailableError, MapPayloadUnavailableError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    # The map changes only when the corpus is re-projected, and the artifact
    # already carries a content fingerprint of exactly that. Using it as the
    # ETag means a returning browser spends one small revalidation instead of
    # 3.7 MB (T6 #20).
    #
    # Corpus-wide and identical for every caller, so it is publicly cacheable.
    # `must-revalidate` keeps a re-projection from being invisible for an hour.
    headers = {"Cache-Control": "public, max-age=300, must-revalidate"}
    if encoded.etag:
        headers["ETag"] = encoded.etag
        if request.headers.get("if-none-match") == encoded.etag:
            log_event("map.not_modified", elapsed_ms=(time.perf_counter() - started) * 1000.0)
            return Response(status_code=304, headers=headers)

    wants_gzip = accepts_gzip(request.headers.get("accept-encoding", ""))
    if wants_gzip:
        headers["Content-Encoding"] = "gzip"
        # Compressed responses vary by request header, so a shared cache must
        # not hand a gzip body to a client that cannot read one.
        headers["Vary"] = "Accept-Encoding"

    size = encoded.gzipped_bytes if wants_gzip else encoded.raw_bytes
    log_event(
        "map",
        nodes=encoded.node_count,
        fingerprint=encoded.fingerprint[:12],
        bytes=size,
        encoding=headers.get("Content-Encoding", "identity"),
        source="disk" if encoded.on_disk else "memory",
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
    )

    if encoded.on_disk:
        # Streamed by the kernel from the page cache: file-backed, evictable
        # memory instead of 15.5 MB of heap the process can never give back.
        return FileResponse(
            encoded.gzip_path if wants_gzip else encoded.raw_path,
            media_type="application/json",
            headers=headers,
        )

    body = encoded.gzipped if wants_gzip else encoded.raw
    return Response(content=body, media_type="application/json", headers=headers)


def _no_store(response: Response) -> None:
    """Personal Library responses are per-person and must never be shared."""
    response.headers["Cache-Control"] = "no-store"


@app.post("/users/default/save", response_model=SaveDocumentResponse, response_model_exclude_none=True)
def save_default_document(request: SaveDocumentRequest, response: Response) -> SaveDocumentResponse:
    _no_store(response)
    started = time.perf_counter()
    try:
        service = _require_library()
        return service.save_document("default", request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        log_event("library.error", operation="save-default", error=type(exc).__name__)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        log_event(
            "library.save",
            scope="default",
            doc_id=request.doc_id,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )


@app.post("/users/by-email/save", response_model=SaveDocumentResponse, response_model_exclude_none=True)
def save_document_by_email(request: EmailSaveDocumentRequest, response: Response) -> SaveDocumentResponse:
    _no_store(response)
    started = time.perf_counter()
    try:
        service = _require_library()
        result = service.save_document_by_email(request.email, request)
        # The identity is never logged, hashed or otherwise: a log line pairing
        # a person with what they save is exactly the record a beta should not
        # be accumulating (T6 §34).
        log_event(
            "library.save",
            scope="by-email",
            doc_id=request.doc_id,
            saved=result.saved,
            duplicate=result.duplicate,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        log_event("library.error", operation="save", error=type(exc).__name__)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/users/by-email/saved", response_model=SavedWorksResponse, response_model_exclude_none=True)
def list_saved_by_email(response: Response, email: str = Query(..., min_length=1)) -> SavedWorksResponse:
    _no_store(response)
    try:
        service = _require_library()
        saved = service.list_saved_by_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        log_event("library.error", operation="list", error=type(exc).__name__)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return SavedWorksResponse(works=saved.items)


@app.delete("/users/by-email/saved/{doc_id}", response_model=DeleteSavedDocumentResponse)
def delete_saved_by_email(
    doc_id: str,
    response: Response,
    email: str = Query(..., min_length=1),
) -> DeleteSavedDocumentResponse:
    _no_store(response)
    try:
        service = _require_library()
        return service.delete_saved_by_email(email, doc_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        log_event("library.error", operation="delete", error=type(exc).__name__)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/users/default/saved", response_model=SavedDocumentsResponse, response_model_exclude_none=True)
def list_default_saved(response: Response) -> SavedDocumentsResponse:
    _no_store(response)
    try:
        service = _require_library()
        return service.list_saved("default")
    except RuntimeError as exc:
        log_event("library.error", operation="list-default", error=type(exc).__name__)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/users/default/saved/{doc_id}", response_model=DeleteSavedDocumentResponse)
def delete_default_saved(doc_id: str, response: Response) -> DeleteSavedDocumentResponse:
    _no_store(response)
    try:
        service = _require_library()
        return service.delete_saved("default", doc_id)
    except RuntimeError as exc:
        log_event("library.error", operation="delete-default", error=type(exc).__name__)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


from .frontend import mount_frontend

mount_frontend(app, required=os.environ.get("RENDER") == "true")
