"""Readiness: is this process able to serve the canonical corpus?

`/health` and `/ready` answer different questions and a load balancer needs
both (T6 §7):

    /health   the process is alive and can answer HTTP. Restart me if not.
    /ready    the canonical corpus is loaded and searchable. Send me traffic.

A process can be perfectly healthy and completely unready — that is exactly the
state during startup warmup, and exactly the state when the embedding artifact
is missing. Conflating them either kills a warming process or routes traffic to
one that would serve 7% of the corpus.

Cost discipline (T6 §7): readiness must not re-validate the corpus per request.
The expensive work happens once, in the background warmup task, and this module
reports what that task achieved. Once ready, the answer is a cached object.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .config import (
    PUBLIC_DEMO,
    PRODUCTION,
    WARMUP_CORPUS,
    WARMUP_FULL,
    ApiSettings,
)
from .corpus_manifest import CorpusManifest, CorpusMismatchError
from .observability import log_event


OK = "ok"
FAILED = "failed"
PENDING = "pending"
# Not attempted on purpose. A development instance that loads lazily is not
# broken, so this must not read as a failure.
DEFERRED = "deferred"

# Terminal states, in the sense that a probe will not change them by looking
# again. Only the warmup task moves a check out of PENDING.
_BLOCKING = {FAILED, PENDING}


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name, "status": self.status}
        if self.detail:
            payload["detail"] = self.detail
        if self.data:
            payload.update(self.data)
        return payload


class ReadinessState:
    """Mutable readiness record, written by warmup and read by `/ready`.

    Guarded by a lock because the warmup task writes it from a worker thread
    while request threads read it.
    """

    def __init__(self, settings: ApiSettings) -> None:
        self._settings = settings
        self._lock = threading.Lock()
        self._checks: dict[str, Check] = {}
        self._started = time.time()
        self._warmup_started: float | None = None
        self._warmup_finished: float | None = None
        self._stage_timings: dict[str, float] = {}
        self._corpus_version = ""
        self._document_count = 0

    # --- writing ---------------------------------------------------------

    def expect(self, *names: str) -> None:
        """Declare checks that must report before this process is ready.

        Readiness is computed from the checks present, so a check that has not
        been written yet cannot block anything — which would make a process
        that is still loading its model look ready the moment the corpus
        landed. Registering the expectation first makes the default "not yet"
        rather than "apparently fine" (T6 §9).
        """
        with self._lock:
            for name in names:
                self._checks.setdefault(
                    name, Check(name=name, status=PENDING, detail="Starting up.")
                )

    def set(self, name: str, status: str, detail: str = "", **data: Any) -> None:
        with self._lock:
            self._checks[name] = Check(name=name, status=status, detail=detail, data=data)

    def record_stage(self, name: str, milliseconds: float) -> None:
        with self._lock:
            self._stage_timings[name] = round(float(milliseconds), 1)

    def set_corpus(self, version: str, documents: int) -> None:
        with self._lock:
            self._corpus_version = version
            self._document_count = documents

    def warmup_started(self) -> None:
        with self._lock:
            self._warmup_started = time.time()

    def warmup_finished(self) -> None:
        with self._lock:
            self._warmup_finished = time.time()

    # --- reading ---------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            checks = [check.as_dict() for check in self._checks.values()]
            blocking = [
                check.name for check in self._checks.values() if check.status in _BLOCKING
            ]
            ready = bool(self._checks) and not blocking
            payload: dict[str, Any] = {
                "ready": ready,
                "deployment_mode": self._settings.deployment_mode,
                "corpus_version": self._corpus_version,
                "document_count": self._document_count,
                "warmup": self._settings.warmup,
                "checks": checks,
                "uptime_s": round(time.time() - self._started, 1),
            }
            if blocking:
                payload["blocked_by"] = blocking
            if self._stage_timings:
                payload["startup_ms"] = dict(self._stage_timings)
            if self._warmup_started is not None:
                payload["warmup_elapsed_s"] = round(
                    (self._warmup_finished or time.time()) - self._warmup_started, 1
                )
            return payload

    @property
    def ready(self) -> bool:
        return bool(self.snapshot()["ready"])


def evaluate_configuration(state: ReadinessState, settings: ApiSettings) -> None:
    """Cheap checks that need no corpus. Safe to run at import time."""
    if settings.configuration_errors:
        state.set(
            "configuration",
            FAILED,
            detail="; ".join(settings.configuration_errors),
        )
    else:
        state.set(
            "configuration",
            OK,
            mode=settings.deployment_mode,
            # Zero origins is the same-origin deployment: correct, and worth
            # showing so nobody has to guess whether it was configured.
            cross_origin=(
                "same-origin only"
                if not settings.allowed_origins
                else ", ".join(settings.allowed_origins)
            ),
        )


def evaluate_manifest(
    state: ReadinessState,
    settings: ApiSettings,
    manifest_dir: Path,
) -> CorpusManifest | None:
    """Manifest presence, artifact presence and the cheap size check.

    Deliberately does not read the artifact: a `stat()` is enough to catch the
    stale snapshot, and readiness must stay cheap.
    """
    try:
        manifest = CorpusManifest.load(manifest_dir)
    except CorpusMismatchError as exc:
        state.set("corpus_manifest", FAILED, detail=str(exc))
        return None

    if manifest is None:
        # Legitimate for a corpus predating T4.6, but not for a public
        # deployment: without it nothing verifies which corpus is being served.
        status = FAILED if settings.is_public else DEFERRED
        state.set(
            "corpus_manifest",
            status,
            detail=f"No {manifest_dir / 'corpus_manifest.json'}. "
            "A public deployment must pin the corpus it serves.",
        )
        return None

    state.set(
        "corpus_manifest",
        OK,
        corpus_version=manifest.corpus_version,
        expected_documents=manifest.document_count,
        embedding_model=manifest.embedding_model,
    )
    state.set_corpus(manifest.corpus_version, manifest.document_count)

    artifact = settings.embeddings_path
    if artifact is None:
        state.set(
            "embedding_artifact",
            FAILED if settings.is_public else DEFERRED,
            detail="THOUGHTMAP_EMBEDDINGS_PATH is not set, so the tracked legacy "
            f"snapshot would be used. Point it at {manifest.embedding_artifact_filename}.",
        )
        return manifest

    if not artifact.exists():
        state.set(
            "embedding_artifact",
            FAILED,
            detail=f"Configured embedding artifact not found: {artifact}",
        )
        return manifest

    try:
        manifest.check_artifact_file(artifact)
    except CorpusMismatchError as exc:
        state.set("embedding_artifact", FAILED, detail=str(exc))
        return manifest

    data: dict[str, Any] = {"bytes": artifact.stat().st_size}
    if settings.verify_artifact_checksum:
        started = time.perf_counter()
        matched = manifest.verify_artifact_hash(artifact)
        data["checksum_ms"] = round((time.perf_counter() - started) * 1000.0, 1)
        if not matched:
            state.set(
                "embedding_artifact",
                FAILED,
                detail=f"SHA-256 of {artifact} does not match the manifest.",
                **data,
            )
            return manifest
        data["checksum"] = "verified"

    state.set("embedding_artifact", OK, **data)
    return manifest


def evaluate_query_encoder(state: ReadinessState, settings: ApiSettings) -> None:
    """Check the configured encoder's artifacts without loading the model.

    Cheap: manifest, file presence and recorded sizes. The model itself is
    loaded by warmup, which reports separately.

    There is deliberately no fallback. A deployment configured for ONNX whose
    encoder is missing fails readiness with the reason; it does not quietly
    switch to sentence-transformers, because then the same commit could rank
    differently on two machines and nothing would say so (T7 #7).
    """
    from .config import ONNX_PROVIDER

    if settings.encoder_provider != ONNX_PROVIDER:
        state.set(
            "query_encoder",
            DEFERRED if not settings.is_public else OK,
            detail=f"provider={settings.encoder_provider}",
            provider=settings.encoder_provider,
        )
        return

    directory = settings.encoder_dir
    if directory is None:
        state.set(
            "query_encoder",
            FAILED,
            detail="THOUGHTMAP_ENCODER_PROVIDER=onnx but THOUGHTMAP_ENCODER_DIR is unset.",
        )
        return

    try:
        from .query_encoder import (
            QueryEncoderUnavailableError,
            encoder_manifest,
            verify_encoder_artifacts,
        )

        manifest = encoder_manifest(directory)
        verify_encoder_artifacts(
            directory, manifest, verify_checksums=settings.verify_encoder_checksums
        )
    except Exception as exc:
        state.set("query_encoder", FAILED, detail=f"{type(exc).__name__}: {exc}")
        return

    manifest = manifest or {}
    state.set(
        "query_encoder",
        OK,
        provider=ONNX_PROVIDER,
        model_id=manifest.get("model_id", ""),
        revision=(manifest.get("revision", "") or "")[:12],
        encoder_version=manifest.get("encoder_version", ""),
    )


def evaluate_projection(
    state: ReadinessState,
    settings: ApiSettings,
    projection_path: Path,
    expected_nodes: int,
) -> None:
    """The map is required for a public deployment and optional locally.

    Only the file header is read — the node count comes from the artifact's own
    metadata, so this stays a small read rather than a 12 MB parse.
    """
    if not projection_path.exists():
        state.set(
            "map_projection",
            FAILED if settings.is_public else DEFERRED,
            detail=f"No projection artifact at {projection_path}. "
            "Run `python -m api.generate_map_projection`.",
        )
        return

    try:
        from .map_projection import read_artifact

        artifact = read_artifact(projection_path)
        nodes = len(artifact.get("nodes", []))
    except Exception as exc:  # unreadable or schema-invalid
        state.set("map_projection", FAILED, detail=f"Projection unusable: {exc}")
        return

    if expected_nodes and nodes != expected_nodes:
        state.set(
            "map_projection",
            FAILED,
            detail=f"Projection has {nodes:,} nodes but the corpus has "
            f"{expected_nodes:,}. Regenerate the projection for this corpus version.",
            nodes=nodes,
        )
        return

    state.set("map_projection", OK, nodes=nodes)


def run_warmup(
    state: ReadinessState,
    settings: ApiSettings,
    load_index: Callable[[], Any],
    load_model: Callable[[], Any],
) -> None:
    """Do the expensive startup work once, recording each stage.

    Runs on a worker thread so the event loop can answer `/health` and `/ready`
    throughout. Any failure is recorded rather than raised: a process that
    cannot load the corpus must stay up and explain itself, not crash-loop.
    """
    state.warmup_started()
    # Both outcomes are claimed up front, so readiness stays false for the whole
    # of warmup rather than flipping true the instant the corpus finished and
    # before the model exists.
    state.expect("search_engine", "embedding_model")

    if settings.warmup in (WARMUP_CORPUS, WARMUP_FULL):
        started = time.perf_counter()
        try:
            index = load_index()
            elapsed = (time.perf_counter() - started) * 1000.0
            state.record_stage("corpus_load", elapsed)
            state.set("search_engine", OK, documents=len(index))
            log_event("warmup.corpus", documents=len(index), elapsed_ms=elapsed)
        except Exception as exc:
            state.record_stage("corpus_load", (time.perf_counter() - started) * 1000.0)
            state.set("search_engine", FAILED, detail=f"{type(exc).__name__}: {exc}")
            log_event("warmup.corpus.failed", error=type(exc).__name__)
            state.warmup_finished()
            return
    else:
        state.set("search_engine", DEFERRED, detail="Loads on first search.")

    if settings.warmup == WARMUP_FULL:
        started = time.perf_counter()
        try:
            load_model()
            elapsed = (time.perf_counter() - started) * 1000.0
            state.record_stage("model_load", elapsed)
            state.set(
                "embedding_model",
                OK,
                provider=settings.encoder_provider,
                model=settings.model_name,
            )
            log_event(
                "warmup.model",
                provider=settings.encoder_provider,
                elapsed_ms=elapsed,
            )
        except Exception as exc:
            state.record_stage("model_load", (time.perf_counter() - started) * 1000.0)
            # Keyword search still works without it, so this is only fatal
            # where semantic search is part of the offer.
            status = FAILED if settings.deployment_mode in (PUBLIC_DEMO, PRODUCTION) else DEFERRED
            state.set("embedding_model", status, detail=f"{type(exc).__name__}: {exc}")
            log_event("warmup.model.failed", error=type(exc).__name__)
    else:
        state.set("embedding_model", DEFERRED, detail="Loads on first semantic search.")

    state.warmup_finished()
