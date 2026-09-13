from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Deployment modes. One switch decides what this instance is, and every
# feature-availability question is answered from it rather than from scattered
# environment checks (T6 §45).
#
#   development  local work. Permissive CORS, lazy loading, Personal Library on.
#   public-demo  publicly reachable beta. Explicit origins required, corpus and
#                model warmed at startup, Personal Library off by default
#                because it has no authentication (T6 §22-§24).
#   production   a real service. Same strictness as public-demo; the Personal
#                Library still has to be switched on deliberately.
DEVELOPMENT = "development"
PUBLIC_DEMO = "public-demo"
PRODUCTION = "production"
DEPLOYMENT_MODES = (DEVELOPMENT, PUBLIC_DEMO, PRODUCTION)

# Startup warmup strategies (T6 §9).
#   off     nothing is loaded until the first request needs it.
#   corpus  documents + embeddings are loaded before readiness.
#   full    corpus, plus the sentence-transformers model.
WARMUP_OFF = "off"
WARMUP_CORPUS = "corpus"
WARMUP_FULL = "full"
WARMUP_STRATEGIES = (WARMUP_OFF, WARMUP_CORPUS, WARMUP_FULL)

# Query encoder providers. Declared here rather than imported from
# `query_encoder`, which imports numpy and would drag that into every consumer
# of settings.
ONNX_PROVIDER = "onnx"
SENTENCE_TRANSFORMERS_PROVIDER = "sentence-transformers"
ENCODER_PROVIDERS = (ONNX_PROVIDER, SENTENCE_TRANSFORMERS_PROVIDER)

# Which implementation turns query text into token ids under the ONNX provider.
# Both produce identical ids; they differ only in footprint, by ~207 MB.
#
#   sentencepiece  41 MB. The production choice.
#   tokenizers     250 MB. The reference the SentencePiece path is verified
#                  against, kept so that equivalence stays checkable.
SENTENCEPIECE_TOKENIZER = "sentencepiece"
HUGGINGFACE_TOKENIZER = "tokenizers"
ENCODER_TOKENIZERS = (SENTENCEPIECE_TOKENIZER, HUGGINGFACE_TOKENIZER)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def normalize_database_url(value: str) -> str:
    """Force SQLAlchemy to use psycopg 3 for Render-style Postgres URLs."""
    url = str(value or "").strip()
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@dataclass(frozen=True)
class ApiSettings:
    backend: str = "csv"
    db_dir: Path | None = None
    model_name: str = DEFAULT_MODEL_NAME
    allowed_origins: tuple[str, ...] = ("*",)
    personal_backend: str = "local"
    database_url: str = ""
    # Location of the embedding artifact, which is far too large for version
    # control (~542 MB at the full 63,891-document corpus) and is therefore
    # managed outside the repository. Empty means "use embeddings_master.csv
    # next to the documents", which is the historical behaviour.
    #
    # Never guessed: nothing scans drives looking for it. If it is set and
    # missing, loading fails with that path named, which is diagnosable.
    embeddings_path: Path | None = None

    # --- T6 deployment surface -------------------------------------------
    deployment_mode: str = DEVELOPMENT
    warmup: str = WARMUP_OFF
    library_enabled: bool = True
    diagnostics_enabled: bool = True
    # Full SHA-256 of the 542 MB artifact costs a few seconds. The size check
    # in the manifest already catches the realistic failure, so the content
    # hash is opt-in for deployment verification rather than every start.
    verify_artifact_checksum: bool = False
    # Where `prepare_corpus_artifacts` may fetch the embedding artifact from.
    # Empty means "an operator places the file"; nothing downloads implicitly.
    embeddings_artifact_url: str = ""
    # Per-client search rate. 0 disables it, which is the default: a reverse
    # proxy or provider edge is the better place for this when one exists, and
    # a limiter nobody asked for would be a surprise in development.
    search_rate_limit: float = 0.0
    search_rate_burst: int = 20
    # X-Forwarded-For is client-controlled. Trust it only where a proxy is
    # known to overwrite it, or anyone can forge their way into a fresh bucket.
    trust_proxy_headers: bool = False
    # Which runtime turns query text into a vector (T7 #3-#4).
    #   onnx                  ONNX Runtime + the Rust tokenizer. Production.
    #   sentence-transformers the historical torch path. Development, and the
    #                         reference the equivalence suite compares against.
    # Chosen by configuration, never by availability: a configured encoder that
    # cannot load fails readiness rather than quietly becoming a different one.
    encoder_provider: str = SENTENCE_TRANSFORMERS_PROVIDER
    # Which tokenizer the ONNX provider uses. Same ids either way - the choice
    # is 41 MB against 250 MB, and it is explicit so that a deployment cannot
    # end up on the expensive one by accident.
    encoder_tokenizer: str = SENTENCEPIECE_TOKENIZER
    encoder_dir: Path | None = None
    verify_encoder_checksums: bool = False
    # Checksum the prepared /map response against the artifact at startup.
    # ~45 ms for 16 MB, streamed, and it is the only check that survives the
    # files being copied to a server - so it is on by default rather than
    # opt-in like the 542 MB corpus artifact's.
    verify_map_sidecar_checksums: bool = True
    # ONNX Runtime intra-op threads. 2 is the measured knee; raising it
    # multiplies threads per concurrent request.
    encoder_threads: int = 2
    # Reasons the configuration is unusable for this mode. Never raised at
    # import — the process must stay alive so /health answers and /ready can
    # explain what is wrong (T6 §7, §36).
    configuration_errors: tuple[str, ...] = field(default=())

    @property
    def is_public(self) -> bool:
        """Reachable by people who are not the operator."""
        return self.deployment_mode in (PUBLIC_DEMO, PRODUCTION)

    def features(self) -> dict[str, object]:
        """The single source of truth for what this instance offers.

        Served to the frontend so feature checks are not duplicated in the UI.
        """
        return {
            "deployment_mode": self.deployment_mode,
            "library_enabled": self.library_enabled,
            "diagnostics_enabled": self.diagnostics_enabled,
            "semantic_search_enabled": True,
        }


def _default_warmup(mode: str) -> str:
    return WARMUP_FULL if mode in (PUBLIC_DEMO, PRODUCTION) else WARMUP_OFF


def _default_encoder_provider(mode: str) -> str:
    # ONNX where a deployment is provisioned from artifacts; the torch path
    # locally, where the model is usually already in a Hugging Face cache and
    # no encoder directory has been prepared.
    return ONNX_PROVIDER if mode in (PUBLIC_DEMO, PRODUCTION) else SENTENCE_TRANSFORMERS_PROVIDER


def _default_library_enabled(mode: str) -> bool:
    # The Personal Library identifies people by a hashed email and authenticates
    # nobody. That is fine on a developer's machine and is not fine on a public
    # URL, so exposure has to be a deliberate act.
    return mode == DEVELOPMENT


def _resolve_artifact_path(value: str) -> Path | None:
    """Make the artifact path absolute once, here.

    A relative THOUGHTMAP_EMBEDDINGS_PATH used to mean two different things:
    the readiness check resolved it against the working directory, while the
    repository resolved it against the project root. The same variable then
    produced "artifact is the wrong size" from one and "artifact not found"
    from the other, for one file. Resolving at the single point where the
    setting is read gives every consumer the same answer.
    """
    if not value:
        return None
    return Path(value).expanduser().resolve()


def get_settings() -> ApiSettings:
    db_dir_text = os.getenv("THOUGHTMAP_DB_DIR", "").strip()
    embeddings_text = os.getenv("THOUGHTMAP_EMBEDDINGS_PATH", "").strip()

    mode = os.getenv("THOUGHTMAP_DEPLOYMENT_MODE", DEVELOPMENT).strip().lower() or DEVELOPMENT
    errors: list[str] = []
    if mode not in DEPLOYMENT_MODES:
        errors.append(
            f"THOUGHTMAP_DEPLOYMENT_MODE={mode!r} is not one of "
            f"{', '.join(DEPLOYMENT_MODES)}. Falling back to {DEVELOPMENT}."
        )
        mode = DEVELOPMENT

    warmup = os.getenv("THOUGHTMAP_WARMUP", "").strip().lower() or _default_warmup(mode)
    if warmup not in WARMUP_STRATEGIES:
        errors.append(
            f"THOUGHTMAP_WARMUP={warmup!r} is not one of "
            f"{', '.join(WARMUP_STRATEGIES)}. Falling back to {_default_warmup(mode)}."
        )
        warmup = _default_warmup(mode)

    origins_text = os.getenv("THOUGHTMAP_ALLOWED_ORIGINS", "").strip()
    origins = tuple(_split_csv(origins_text))
    if not origins:
        if mode == DEVELOPMENT:
            origins = ("*",)
        # Outside development, unset means no cross-origin access at all.
        #
        # That is not an error: it is exactly right for the recommended
        # same-origin deployment, where the frontend and the API share a
        # hostname and the browser never makes a cross-origin request. It also
        # already fails closed. Treating it as a configuration failure (as T6
        # did) made the recommended topology unable to become ready.
        #
        # The genuinely unsafe case is '*', which is rejected below.
    elif "*" in origins and mode != DEVELOPMENT:
        errors.append(
            f"THOUGHTMAP_ALLOWED_ORIGINS may not be '*' in {mode} mode. "
            "List the frontend origin(s) explicitly."
        )
        origins = tuple(origin for origin in origins if origin != "*")

    encoder_text = os.getenv("THOUGHTMAP_ENCODER_DIR", "").strip()
    encoder_provider = (
        os.getenv("THOUGHTMAP_ENCODER_PROVIDER", "").strip().lower()
        or _default_encoder_provider(mode)
    )
    if encoder_provider not in ENCODER_PROVIDERS:
        errors.append(
            f"THOUGHTMAP_ENCODER_PROVIDER={encoder_provider!r} is not one of "
            f"{', '.join(ENCODER_PROVIDERS)}."
        )
        encoder_provider = SENTENCE_TRANSFORMERS_PROVIDER

    encoder_tokenizer = (
        os.getenv("THOUGHTMAP_ENCODER_TOKENIZER", "").strip().lower()
        or SENTENCEPIECE_TOKENIZER
    )
    if encoder_tokenizer not in ENCODER_TOKENIZERS:
        errors.append(
            f"THOUGHTMAP_ENCODER_TOKENIZER={encoder_tokenizer!r} is not one of "
            f"{', '.join(ENCODER_TOKENIZERS)}."
        )
        encoder_tokenizer = SENTENCEPIECE_TOKENIZER

    encoder_dir = _resolve_artifact_path(encoder_text)
    if encoder_provider == ONNX_PROVIDER and encoder_dir is None:
        errors.append(
            "THOUGHTMAP_ENCODER_PROVIDER=onnx requires THOUGHTMAP_ENCODER_DIR to "
            "point at a directory prepared by `python -m api.prepare_query_encoder`."
        )

    return ApiSettings(
        backend=os.getenv("THOUGHTMAP_BACKEND", "csv").strip().lower() or "csv",
        db_dir=Path(db_dir_text) if db_dir_text else None,
        embeddings_path=_resolve_artifact_path(embeddings_text),
        model_name=os.getenv("THOUGHTMAP_MODEL_NAME", DEFAULT_MODEL_NAME),
        allowed_origins=origins,
        personal_backend=os.getenv("THOUGHTMAP_PERSONAL_BACKEND", "local").strip().lower() or "local",
        database_url=normalize_database_url(os.getenv("DATABASE_URL", "")),
        deployment_mode=mode,
        warmup=warmup,
        library_enabled=_env_flag("THOUGHTMAP_LIBRARY_ENABLED", _default_library_enabled(mode)),
        diagnostics_enabled=_env_flag("THOUGHTMAP_DIAGNOSTICS", mode == DEVELOPMENT),
        verify_artifact_checksum=_env_flag("THOUGHTMAP_VERIFY_ARTIFACT_CHECKSUM", False),
        embeddings_artifact_url=os.getenv("THOUGHTMAP_EMBEDDINGS_URL", "").strip(),
        search_rate_limit=_env_float("THOUGHTMAP_SEARCH_RATE_LIMIT", 0.0),
        search_rate_burst=int(_env_float("THOUGHTMAP_SEARCH_RATE_BURST", 20.0)),
        trust_proxy_headers=_env_flag("THOUGHTMAP_TRUST_PROXY_HEADERS", False),
        encoder_provider=encoder_provider,
        encoder_tokenizer=encoder_tokenizer,
        encoder_dir=encoder_dir,
        verify_encoder_checksums=_env_flag("THOUGHTMAP_VERIFY_ENCODER_CHECKSUMS", False),
        verify_map_sidecar_checksums=_env_flag(
            "THOUGHTMAP_VERIFY_MAP_SIDECAR_CHECKSUMS", True
        ),
        encoder_threads=max(1, int(_env_float("THOUGHTMAP_ENCODER_THREADS", 2.0))),
        configuration_errors=tuple(errors),
    )
