from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from search_utils import cosine

from .schemas import ParameterScore


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FILTERS_DIR = PROJECT_ROOT / "filters"


class ParameterFilterService:
    """Load JSON parameter filters and score text or document embeddings."""

    def __init__(
        self,
        model: Any,
        filters_dir: str | Path | None = None,
    ) -> None:
        self.model = model
        self.filters_dir = Path(filters_dir) if filters_dir is not None else DEFAULT_FILTERS_DIR
        self._definitions: dict[str, dict[str, str]] = {}
        self._vectors: dict[str, list[tuple[str, np.ndarray]]] = {}

    def score_text(
        self,
        text: str,
        filter_name: str,
    ) -> list[ParameterScore] | None:
        name = self._normalize_filter_name(filter_name)
        text = str(text or "").strip()
        if not name or name == "all" or not text:
            return None

        embedding_vec = np.asarray(self.model.encode([text], show_progress_bar=False)[0], dtype=np.float32)
        return self.score_embedding(embedding_vec, name)

    def score_embedding(
        self,
        embedding_vec: np.ndarray | None,
        filter_name: str,
    ) -> list[ParameterScore] | None:
        name = self._normalize_filter_name(filter_name)
        if not name or name == "all" or embedding_vec is None:
            return None

        parameter_vectors = self._load_parameter_vectors(name)
        if not parameter_vectors:
            return None

        scores: list[ParameterScore] = []
        for key, parameter_vec in parameter_vectors:
            value = self._score_to_100(cosine(embedding_vec, parameter_vec))
            scores.append(ParameterScore(key=key, value=value))

        return scores

    def _load_parameter_vectors(self, filter_name: str) -> list[tuple[str, np.ndarray]]:
        if filter_name in self._vectors:
            return self._vectors[filter_name]

        definition = self._load_definition(filter_name)
        if not definition:
            self._vectors[filter_name] = []
            return []

        keys = list(definition.keys())
        texts = [definition[key] for key in keys]
        encoded = self.model.encode(texts, show_progress_bar=False)
        self._vectors[filter_name] = [
            (key, np.asarray(vec, dtype=np.float32))
            for key, vec in zip(keys, encoded)
        ]
        return self._vectors[filter_name]

    def _load_definition(self, filter_name: str) -> dict[str, str]:
        if filter_name in self._definitions:
            return self._definitions[filter_name]

        path = self.filters_dir / f"{filter_name}.json"
        if not path.exists():
            self._definitions[filter_name] = {}
            return {}

        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        if not isinstance(raw, dict):
            raise ValueError(f"Filter JSON must be an object: {path}")

        definition: dict[str, str] = {}
        for key, value in raw.items():
            key_text = str(key or "").strip()
            value_text = str(value or "").strip()
            if key_text and value_text:
                definition[key_text] = value_text

        self._definitions[filter_name] = definition
        return definition

    def _normalize_filter_name(self, filter_name: str) -> str:
        name = str(filter_name or "").strip().lower()
        if not name:
            return ""
        return Path(name).stem

    def _score_to_100(self, similarity: float) -> float:
        clipped = max(0.0, min(1.0, float(similarity or 0.0)))
        return round(clipped * 100.0, 2)
