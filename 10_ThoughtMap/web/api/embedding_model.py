from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Protocol


logger = logging.getLogger("thoughtmap.embedding")


class EmbeddingModelUnavailableError(RuntimeError):
    """The configured sentence-transformers model could not be loaded.

    Raised instead of a bare ImportError/OSError so the HTTP layer can answer
    503 (dependency not installed on this deployment) rather than 500.
    """


class TextEncoder(Protocol):
    """The subset of SentenceTransformer used across the API.

    `thought_composition.make_filter_scores` calls exactly this, so anything
    satisfying it can stand in for the model.
    """

    def encode(self, sentences: Any, show_progress_bar: bool = False) -> Any: ...


@lru_cache(maxsize=2)
def load_embedding_model(model_name: str) -> TextEncoder:
    """Load and cache the query-encoding model.

    Deliberately lazy: `requirements-api.txt` deployments that only ever serve
    keyword search should not pay the import cost, and importing this module
    must never break API startup.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:  # ImportError, or a broken torch install
        raise EmbeddingModelUnavailableError(
            "sentence-transformers is not installed, so semantic/hybrid search "
            "and query parameter profiles are unavailable. Install the API "
            "requirements (web/requirements-api.txt) to enable them. "
            f"cause={type(exc).__name__}: {exc}"
        ) from exc

    try:
        model = SentenceTransformer(model_name)
    except Exception as exc:
        raise EmbeddingModelUnavailableError(
            "SentenceTransformer model could not be loaded. "
            f"model={model_name}; cause={type(exc).__name__}: {exc}"
        ) from exc

    logger.info("SentenceTransformer model loaded model=%s", model_name)
    return model


class CachedCategoryEncoder:
    """Memoises `encode()` for a fixed, small set of texts.

    `make_filter_scores` re-encodes the ten filter category descriptions on
    every call. Those texts never change within a process, so this adapter is
    passed in its place to keep per-request work down to encoding the query
    itself. The scoring logic in `thought_composition` is untouched.
    """

    def __init__(self, model: TextEncoder) -> None:
        self._model = model
        self._cache: dict[tuple[str, ...], Any] = {}

    def encode(self, sentences: Any, show_progress_bar: bool = False) -> Any:
        key = tuple(str(text) for text in sentences)
        cached = self._cache.get(key)
        if cached is None:
            cached = self._model.encode(list(sentences), show_progress_bar=show_progress_bar)
            self._cache[key] = cached
        return cached
