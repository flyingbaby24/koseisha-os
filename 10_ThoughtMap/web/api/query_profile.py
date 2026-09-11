from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

import numpy as np

from .embedding_model import CachedCategoryEncoder, EmbeddingModelUnavailableError, TextEncoder
from .observability import stage
from .schemas import ParameterScore


logger = logging.getLogger("thoughtmap.query_profile")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# The same directory `api.generate_parameter_scores` reads when it writes
# parameter_scores.csv. NOTE: 10_ThoughtMap/filters/ holds an older, divergent
# copy of these definitions; scoring a query against that copy would put
# query_parameters on a different footing than results[].parameters.
FILTERS_DIR = PROJECT_ROOT / "web" / "filters"

DEFAULT_FILTER_NAME = "general"

# Filter values that mean "no explicit selection". Kept consistent with
# search_utils.NO_FILTER_VALUES, where "general" is also the default set.
NO_SELECTION_VALUES = {"", "all", "general"}


class QueryProfileService:
    """Score the search query text on the official Thought Composition axes.

    Reuses `thought_composition.make_filter_scores`, the same function that
    produced `parameter_scores.csv`, so `query_parameters` and
    `results[].parameters` are on one scale and are directly comparable.

    That function clips cosine similarity at zero and divides each row by its
    own sum, so a profile is a **composition**: ten values in 0.0..1.0 summing
    to 1.0. It is not an independent 0..100 score per axis.
    """

    def __init__(
        self,
        model_loader: Callable[[], TextEncoder],
        filters_dir: str | Path | None = None,
    ) -> None:
        self._model_loader = model_loader
        self._filters_dir = Path(filters_dir) if filters_dir is not None else FILTERS_DIR
        self._definitions: dict[str, dict[str, str]] = {}
        self._model: TextEncoder | None = None
        self._category_encoder: CachedCategoryEncoder | None = None

    def score_query(self, text: str, filter_name: str = "") -> list[ParameterScore] | None:
        """Return the query's parameter composition, or None if unavailable.

        None (rather than an error) when the text is empty, the filter has no
        definition, or the embedding model is not installed on this deployment.
        A missing query profile must never fail an otherwise valid search.
        """
        text = str(text or "").strip()
        if not text:
            return None

        categories = self._load_definition(self._resolve_filter_name(filter_name))
        if not categories:
            return None

        try:
            scores = self._score(text, categories)
        except EmbeddingModelUnavailableError as exc:
            logger.info("Query profile unavailable: %s", exc)
            return None
        except Exception:
            logger.exception("Query profile calculation failed; returning no profile.")
            return None

        return scores

    def _score(self, text: str, categories: dict[str, str]) -> list[ParameterScore] | None:
        from thought_composition import make_filter_scores

        model, category_encoder = self._get_encoders()

        # The query text is different every call, so it goes to the raw model;
        # only the fixed category descriptions are worth caching.
        #
        # Timed separately because this runs for *every* mode, keyword included:
        # the query profile is part of the response contract, so keyword search
        # pays a model encode too. That is the single largest term in keyword
        # latency, and without this stage it is invisible (T6 §8, §18).
        with stage("profile_ms"):
            encoded = model.encode([text], show_progress_bar=False)

        query_vec = np.asarray(encoded, dtype=np.float32)
        if query_vec.ndim == 1:
            query_vec = query_vec.reshape(1, -1)

        filter_scores = make_filter_scores(query_vec, categories, category_encoder)
        if filter_scores is None or filter_scores.empty:
            return None

        row = filter_scores.iloc[0]
        return [
            ParameterScore(key=str(key), value=float(row[key]))
            for key in filter_scores.columns
            if np.isfinite(float(row[key]))
        ]

    def _get_encoders(self) -> tuple[TextEncoder, CachedCategoryEncoder]:
        if self._model is None or self._category_encoder is None:
            model = self._model_loader()
            self._model = model
            self._category_encoder = CachedCategoryEncoder(model)
        return self._model, self._category_encoder

    def _resolve_filter_name(self, filter_name: str) -> str:
        name = str(filter_name or "").strip().lower()
        if name in NO_SELECTION_VALUES:
            return DEFAULT_FILTER_NAME
        return Path(name).stem or DEFAULT_FILTER_NAME

    def _load_definition(self, filter_name: str) -> dict[str, str]:
        cached = self._definitions.get(filter_name)
        if cached is not None:
            return cached

        path = self._filters_dir / f"{filter_name}.json"
        if not path.exists():
            logger.info("Filter definition not found, no query profile: %s", path)
            self._definitions[filter_name] = {}
            return {}

        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Filter JSON must be an object: {path}")

        definition = {
            str(key).strip(): str(value).strip()
            for key, value in raw.items()
            if str(key or "").strip() and str(value or "").strip()
        }
        self._definitions[filter_name] = definition
        return definition
