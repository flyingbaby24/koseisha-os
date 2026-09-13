from __future__ import annotations

import json
import math
import re
import logging
import time
from functools import lru_cache
from typing import Callable

import numpy as np
import pandas as pd

from search_utils import (
    MATRIX_ROW_COLUMN,
    format_similarity,
    normalize_text,
    parse_embedding,
    work_similarity_by_vector,
    apply_metadata_filter,
    apply_parameter_filter,
    filter_options,
    parameter_names,
)

from .config import ApiSettings, get_settings
from .embedding_model import TextEncoder, load_embedding_model
from .observability import stage
from .query_encoder import get_query_encoder
from .query_profile import QueryProfileService
from .repositories import SearchIndexRepository, create_search_index_repository
from .schemas import ParameterScore, SearchResponse, SearchResult
from .user_embedding_sqlite import load_user_embedding_frame


# Internal mode names. `embedding` covers both origins of the comparison
# vector: a query text, or an existing document identified by target_doc_id.
SEARCH_MODES = {"keyword", "embedding", "hybrid"}

# The public HTTP contract (docs/api_contract.md, Unity, Streamlit) says
# `semantic`. The internal implementation has always called it `embedding`.
# Translate at this boundary rather than renaming either side.
PUBLIC_MODE_ALIASES = {"semantic": "embedding"}

# Existing hybrid weighting, unchanged: semantic similarity dominates and the
# keyword score breaks ties among keyword matches.
HYBRID_SIMILARITY_WEIGHT = 0.8
HYBRID_KEYWORD_WEIGHT = 0.2

logger = logging.getLogger("thoughtmap.search")

PARAMETER_COLUMNS = [
    "parameters",
    "parameter_scores",
    "filter_scores",
    "composition",
    "thought_composition",
    "scores",
]

KEYWORD_COLUMNS = [
    "title",
    "author",
    "source",
    "source_url",
    "category",
    "subcategory",
    "tags",
    "notes",
    "doc_id",
]


class ThoughtMapSearchService:
    def __init__(
        self,
        repository: SearchIndexRepository,
        model_name: str,
        model_loader: Callable[[], TextEncoder] | None = None,
        query_profile_service: QueryProfileService | None = None,
    ) -> None:
        self.repository = repository
        self.model_name = model_name
        self._model_loader = model_loader or (lambda: load_embedding_model(model_name))
        self.query_profile_service = query_profile_service or QueryProfileService(self._model_loader)
        self._model: TextEncoder | None = None

    def search_response(
        self,
        q: str = "",
        top: int = 10,
        mode: str = "keyword",
        source: str = "",
        category: str = "",
        filter_name: str = "",
        target_doc_id: str = "",
        user_email: str = "",
    ) -> SearchResponse:
        results = self.search(
            query=q,
            top=top,
            mode=mode,
            source=source,
            category=category,
            filter_name=filter_name,
            target_doc_id=target_doc_id,
            user_email=user_email,
        )

        return SearchResponse(
            results=results,
            query_parameters=self.query_parameters(q, filter_name),
        )

    def query_parameters(self, q: str, filter_name: str = "") -> list[ParameterScore] | None:
        """Thought Composition profile of the query text itself.

        Same axes and same scale as `results[].parameters`, so a client can
        overlay the two. Returns None when the text is empty or the embedding
        model is unavailable; a missing profile never fails the search.
        """
        return self.query_profile_service.score_query(q, filter_name)

    def search(
        self,
        query: str = "",
        top: int = 10,
        mode: str = "keyword",
        source: str = "",
        category: str = "",
        filter_name: str = "",
        target_doc_id: str = "",
        user_email: str = "",
    ) -> list[SearchResult]:
        query = str(query or "").strip()
        mode = str(mode or "keyword").strip().lower()
        source = str(source or "").strip()
        category = str(category or "").strip()
        target_doc_id = str(target_doc_id or "").strip()
        user_email = str(user_email or "").strip()

        mode = PUBLIC_MODE_ALIASES.get(mode, mode)

        if mode not in SEARCH_MODES:
            raise ValueError(f"Unsupported search mode: {mode}")

        started = time.perf_counter()
        with stage("index_ms"):
            corpus, index = self._load_corpus()
        counts = {"library": len(index)}
        index = apply_metadata_filter(index, "source", source)
        counts["source"] = len(index)
        index = apply_metadata_filter(index, "category", category, multi=True)
        counts["category"] = len(index)
        index = apply_parameter_filter(index, filter_name, corpus)
        counts["parameter"] = len(index)

        if index.empty:
            logger.info("page=api mode=%s source=%r category=%r parameter=%r counts=%s candidates=0 results=0 elapsed=%.4f", mode, source, category, filter_name, counts, time.perf_counter()-started)
            return []

        with stage("ranking_ms"):
            results = self._rank(
                index=index,
                query=query,
                mode=mode,
                top=top,
                target_doc_id=target_doc_id,
                user_email=user_email,
                corpus=corpus,
            )
        if results is None:
            return []

        with stage("response_build_ms"):
            output = self._to_search_results(results, corpus)
        logger.info("page=api mode=%s source=%r category=%r parameter=%r counts=%s candidates=%d results=%d elapsed=%.4f", mode, source, category, filter_name, counts, len(index), len(output), time.perf_counter()-started)
        return output

    def _load_corpus(self):
        """(corpus, frame) from the repository.

        `load_corpus` is an optional extension to the repository protocol: the
        prepared matrix is a performance hint, not a requirement. A repository
        that only implements `load_index` — a test double, or a storage backend
        written before T7 — still works, and simply ranks by stacking.
        """
        loader = getattr(self.repository, "load_corpus", None)
        if loader is None:
            return None, self.repository.load_index()

        corpus = loader()
        return corpus, corpus.frame

    def _rank(
        self,
        index: pd.DataFrame,
        query: str,
        mode: str,
        top: int,
        target_doc_id: str,
        user_email: str,
        corpus=None,
    ) -> pd.DataFrame | None:
        """Dispatch to the ranking path for this mode.

        Extracted from `search` so the ranking cost can be timed as one stage
        (T6 §35). The branches, their order and their arguments are unchanged;
        `None` means "no query to rank", which the caller turns into [].
        """
        if mode == "keyword":
            if not query:
                return None
            return self._keyword_search(index, query, top)

        if mode == "embedding":
            # Document-origin similarity when a target is named, query-text
            # similarity otherwise. Both compare against the same index with
            # the same cosine ranking.
            if target_doc_id:
                return self._embedding_search(
                    index=index,
                    target_doc_id=target_doc_id,
                    top=top,
                    user_email=user_email,
                    corpus=corpus,
                )
            if query:
                return self._query_embedding_search(
                    index=index, query=query, top=top, corpus=corpus
                )
            raise ValueError("q or target_doc_id is required for semantic mode.")

        if target_doc_id:
            return self._hybrid_embedding_search(
                index=index,
                query=query,
                target_doc_id=target_doc_id,
                top=top,
                user_email=user_email,
                corpus=corpus,
            )
        if query:
            return self._hybrid_query_search(
                index=index, query=query, top=top, corpus=corpus
            )
        raise ValueError("q or target_doc_id is required for hybrid mode.")

    def filter_options(self) -> dict[str, list[str]]:
        index = self.repository.load_index()
        return {
            "sources": filter_options(index, "source"),
            "categories": filter_options(index, "category", multi=True),
            "parameters": ["general", *parameter_names(index)],
        }

    def _filter_by_source(self, index: pd.DataFrame, source: str) -> pd.DataFrame:
        return apply_metadata_filter(index, "source", source)

    def _filter_by_category(self, index: pd.DataFrame, category: str) -> pd.DataFrame:
        return apply_metadata_filter(index, "category", category, multi=True)

    def keyword_scores(self, index: pd.DataFrame, query: str) -> np.ndarray:
        """Keyword score for every row, computed column-wise.

        Identical rule to `_keyword_score`, which remains the single-row
        definition: for each metadata column, an exact match scores highest, a
        substring match scores the partial weight, and a match on every query
        term scores the partial weight minus 0.05. A row takes the best score
        across columns.

        Vectorised in T4.6. The per-row version cost ~3.4 s at 63,891
        documents, which made keyword the slowest mode of the three.
        """
        query_text = normalize_text(query).lower()
        if not query_text:
            return np.zeros(len(index), dtype=float)

        query_terms = [term for term in re.split(r"\s+", query_text) if term]
        best = np.zeros(len(index), dtype=float)

        for column in KEYWORD_COLUMNS:
            if column not in index.columns:
                continue

            values = index[column].fillna("").astype(str).str.strip().str.lower()
            present = values.to_numpy() != ""
            if not present.any():
                continue

            exact = present & (values.to_numpy() == query_text)
            contains = present & ~exact & values.str.contains(query_text, regex=False).to_numpy()

            all_terms = np.zeros(len(index), dtype=bool)
            if query_terms:
                all_terms = present & ~exact & ~contains
                for term in query_terms:
                    if not all_terms.any():
                        break
                    all_terms &= values.str.contains(term, regex=False).to_numpy()

            exact_score = self._exact_match_score(column)
            partial_score = self._partial_match_score(column)

            column_scores = np.where(
                exact,
                exact_score,
                np.where(contains, partial_score, np.where(all_terms, partial_score - 0.05, 0.0)),
            )
            np.maximum(best, column_scores, out=best)

        return np.round(np.maximum(best, 0.0), 4)

    def _keyword_search(self, index: pd.DataFrame, query: str, top: int) -> pd.DataFrame:
        results = index.copy()
        results["similarity"] = self.keyword_scores(index, query)
        results = results[results["similarity"] > 0]
        results = results.sort_values(
            ["similarity", "title"],
            ascending=[False, True],
        ).head(top).reset_index(drop=True)
        return format_similarity(results)

    def _embedding_search(
        self,
        index: pd.DataFrame,
        target_doc_id: str,
        top: int,
        user_email: str = "",
        corpus=None,
    ) -> pd.DataFrame:
        target_vec, exclude_doc_id = self._resolve_target_embedding(
            index=index,
            target_doc_id=target_doc_id,
            user_email=user_email,
        )

        results = work_similarity_by_vector(
            index,
            target_vec=target_vec,
            top=top,
            exclude_doc_id=exclude_doc_id,
            include_self=False,
            corpus=corpus,
        )

        return format_similarity(results)

    def _encode_query(self, query: str) -> np.ndarray:
        """Embed the query text with the configured model.

        Only the query is encoded here. Stored document embeddings are read as
        they are and are never regenerated.
        """
        if self._model is None:
            self._model = self._model_loader()

        with stage("embedding_ms"):
            encoded = self._model.encode([query], show_progress_bar=False)

        vector = np.asarray(encoded, dtype=np.float32)
        if vector.ndim > 1:
            vector = vector[0]
        return vector

    def _query_embedding_search(
        self, index: pd.DataFrame, query: str, top: int, corpus=None
    ) -> pd.DataFrame:
        """Rank the index by cosine similarity to the query text.

        Uses the same `work_similarity_by_vector` ranking as document-origin
        similarity; only the origin of the comparison vector differs. Nothing
        is excluded, because the query is not itself a document in the index.
        """
        results = work_similarity_by_vector(
            index,
            target_vec=self._encode_query(query),
            top=top,
            exclude_doc_id="",
            include_self=True,
            corpus=corpus,
        )
        return format_similarity(results)

    def _hybrid_query_search(
        self, index: pd.DataFrame, query: str, top: int, corpus=None
    ) -> pd.DataFrame:
        """Keyword matches ranked by query-text semantic similarity.

        Mirrors the existing document-origin hybrid path — keyword matches are
        the candidate set, then ranked by the 0.8/0.2 similarity/keyword blend —
        with the query embedding as the comparison vector instead of a target
        document's. When nothing matches by keyword, it falls back to pure
        semantic ranking, the "fallback results" behaviour that
        docs/api_contract.md already describes for this mode.
        """
        query_vec = self._encode_query(query)

        candidates = index.copy()
        candidates["keyword_score"] = self.keyword_scores(index, query)
        candidates = candidates[candidates["keyword_score"] > 0].copy()

        if candidates.empty:
            results = work_similarity_by_vector(
                index,
                target_vec=query_vec,
                top=top,
                exclude_doc_id="",
                include_self=True,
                corpus=corpus,
            )
            return format_similarity(results)

        results = work_similarity_by_vector(
            candidates,
            target_vec=query_vec,
            top=max(top, len(candidates)),
            exclude_doc_id="",
            include_self=True,
            corpus=corpus,
        )
        results = format_similarity(results)

        keyword_scores = candidates[["doc_id", "keyword_score"]].copy()
        results = results.merge(keyword_scores, on="doc_id", how="left")
        results["keyword_score"] = results["keyword_score"].fillna(0.0)
        results["similarity"] = (
            results["similarity"].astype(float) * HYBRID_SIMILARITY_WEIGHT
            + results["keyword_score"].astype(float) * HYBRID_KEYWORD_WEIGHT
        )
        results = results.sort_values(
            ["similarity", "keyword_score", "title"],
            ascending=[False, False, True],
        ).head(top).reset_index(drop=True)

        return results

    def _hybrid_embedding_search(
        self,
        index: pd.DataFrame,
        query: str,
        target_doc_id: str,
        top: int,
        user_email: str = "",
        corpus=None,
    ) -> pd.DataFrame:
        target_vec, exclude_doc_id = self._resolve_target_embedding(
            index=index,
            target_doc_id=target_doc_id,
            user_email=user_email,
        )

        candidates = index.copy()

        if query:
            candidates["keyword_score"] = self.keyword_scores(candidates, query)
            candidates = candidates[candidates["keyword_score"] > 0].copy()

        if candidates.empty:
            return pd.DataFrame()

        results = work_similarity_by_vector(
            candidates,
            target_vec=target_vec,
            top=max(top, len(candidates)),
            exclude_doc_id=exclude_doc_id,
            include_self=False,
            corpus=corpus,
        )

        results = format_similarity(results)

        if query and "keyword_score" in candidates.columns:
            keyword_scores = candidates[["doc_id", "keyword_score"]].copy()
            results = results.merge(keyword_scores, on="doc_id", how="left")
            results["keyword_score"] = results["keyword_score"].fillna(0.0)
            results["similarity"] = (
                results["similarity"].astype(float) * HYBRID_SIMILARITY_WEIGHT
                + results["keyword_score"].astype(float) * HYBRID_KEYWORD_WEIGHT
            )
            results = results.sort_values(
                ["similarity", "keyword_score", "title"],
                ascending=[False, False, True],
            ).head(top).reset_index(drop=True)
        else:
            results = results.head(top).reset_index(drop=True)

        return results

    def _resolve_target_embedding(
        self,
        index: pd.DataFrame,
        target_doc_id: str,
        user_email: str = "",
    ) -> tuple[object, str]:
        if user_email:
            target = self._find_user_target_row(user_email, target_doc_id)
            target_vec = target.get("_embedding_vec")
            exclude_doc_id = str(target.get("doc_id", "") or target_doc_id)
        else:
            target = self._find_target_row(index, target_doc_id)
            target_vec = target.get("_embedding_vec")
            exclude_doc_id = str(target.get("doc_id", "") or target_doc_id)

        if target_vec is None:
            raise ValueError(f"Target document has no embedding: {target_doc_id}")

        return target_vec, exclude_doc_id

    def _load_user_embeddings(self, user_email: str) -> pd.DataFrame:
        if not str(user_email or "").strip():
            raise ValueError("user_email is required for personal embedding search.")

        df = load_user_embedding_frame(user_email)

        if "embedding" not in df.columns:
            raise ValueError("Personal embedding DB must contain an embedding column.")

        if "doc_id" not in df.columns:
            df["doc_id"] = [f"user_doc_{i:06d}" for i in range(len(df))]

        for col in ["title", "author", "source", "category", "subcategory", "source_url", "url"]:
            if col not in df.columns:
                df[col] = ""

        df["_embedding_vec"] = df["embedding"].map(parse_embedding)
        df = df[df["_embedding_vec"].notna()].copy()

        if df.empty:
            raise ValueError("Personal embedding DB has no valid embedding rows.")

        return df.reset_index(drop=True)

    def _find_user_target_row(self, user_email: str, target_doc_id: str) -> pd.Series:
        user_df = self._load_user_embeddings(user_email)
        target_key = normalize_text(target_doc_id)

        exact = user_df[user_df["doc_id"].map(normalize_text) == target_key]
        if not exact.empty:
            return exact.iloc[0]

        title_match = user_df[user_df["title"].map(normalize_text) == target_key]
        if not title_match.empty:
            return title_match.iloc[0]

        partial = user_df[
            user_df["doc_id"].map(normalize_text).str.contains(re.escape(target_key), na=False)
            | user_df["title"].map(normalize_text).str.contains(re.escape(target_key), na=False)
        ]
        if not partial.empty:
            return partial.iloc[0]

        raise ValueError(f"Target work not found in personal embeddings: {target_doc_id}")

    def _find_target_row(self, index: pd.DataFrame, target_doc_id: str) -> pd.Series:
        if "doc_id" not in index.columns:
            raise ValueError("Search index has no doc_id column.")

        target_key = normalize_text(target_doc_id)

        exact = index[index["doc_id"].map(normalize_text) == target_key]
        if not exact.empty:
            return exact.iloc[0]

        partial = index[index["doc_id"].map(normalize_text).str.contains(re.escape(target_key), na=False)]
        if not partial.empty:
            return partial.iloc[0]

        raise ValueError(f"Target document not found: {target_doc_id}")

    def _keyword_score(self, row: pd.Series, query: str) -> float:
        query_text = normalize_text(query).lower()
        if not query_text:
            return 0.0

        query_terms = [term for term in re.split(r"\s+", query_text) if term]
        best = 0.0

        for column in KEYWORD_COLUMNS:
            if column not in row.index:
                continue

            value = normalize_text(row.get(column, "")).lower()
            if not value:
                continue

            if value == query_text:
                best = max(best, self._exact_match_score(column))
            elif query_text in value:
                best = max(best, self._partial_match_score(column))
            elif query_terms and all(term in value for term in query_terms):
                best = max(best, self._partial_match_score(column) - 0.05)

        return round(max(0.0, best), 4)

    def _exact_match_score(self, column: str) -> float:
        if column == "title":
            return 1.0
        if column == "author":
            return 0.97
        if column == "doc_id":
            return 0.95
        if column == "source":
            return 0.9
        if column == "category":
            return 0.88
        if column == "source_url":
            return 0.85
        return 0.8

    def _partial_match_score(self, column: str) -> float:
        if column == "title":
            return 0.9
        if column == "author":
            return 0.87
        if column == "doc_id":
            return 0.82
        if column == "source":
            return 0.78
        if column == "category":
            return 0.76
        if column == "source_url":
            return 0.75
        return 0.65

    def _to_search_results(self, results: pd.DataFrame, corpus=None) -> list[SearchResult]:
        output: list[SearchResult] = []

        if results is None or results.empty:
            return output

        for _, row in results.iterrows():
            parameters = self._extract_parameters(row, corpus)
            output.append(
                SearchResult(
                    doc_id=str(row.get("doc_id", "") or ""),
                    title=str(row.get("title", "") or ""),
                    author=str(row.get("author", "") or ""),
                    source=str(row.get("source", "") or ""),
                    similarity=float(row.get("similarity", 0.0) or 0.0),
                    url=self._resolve_url(row),
                    parameters=parameters,
                )
            )

        return output

    def _extract_parameters(self, row: pd.Series, corpus=None) -> list[dict] | None:
        # Preferred: the corpus matrix, via the row position carried through
        # ranking. Costs one small list per returned row.
        if corpus is not None and MATRIX_ROW_COLUMN in row.index:
            position = row.get(MATRIX_ROW_COLUMN)
            if position is not None and not pd.isna(position):
                parameters = corpus.parameters_for(int(position))
                if parameters:
                    return parameters

        # Fallback for frames that still carry the values inline: personal
        # documents, and any caller that builds its own frame.
        for column in PARAMETER_COLUMNS:
            if column not in row.index:
                continue

            parameters = self._parse_parameter_value(row.get(column))

            if parameters:
                return parameters

        return None

    def _parse_parameter_value(self, value: object) -> list[dict]:
        if value is None:
            return []

        if isinstance(value, float) and math.isnan(value):
            return []

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []

            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                return []

        if isinstance(value, dict):
            return self._parameters_from_dict(value)

        if isinstance(value, list):
            return self._parameters_from_list(value)

        return []

    def _parameters_from_dict(self, data: dict) -> list[dict]:
        if "key" in data and "value" in data:
            parameter = self._make_parameter(data.get("key"), data.get("value"))
            return [parameter] if parameter else []

        for nested_key in PARAMETER_COLUMNS:
            nested = data.get(nested_key)
            parameters = self._parse_parameter_value(nested)
            if parameters:
                return parameters

        parameters = []

        for key, value in data.items():
            parameter = self._make_parameter(key, value)
            if parameter:
                parameters.append(parameter)

        return parameters

    def _parameters_from_list(self, items: list) -> list[dict]:
        parameters = []

        for item in items:
            if isinstance(item, dict):
                if "key" in item and "value" in item:
                    parameter = self._make_parameter(item.get("key"), item.get("value"))
                    if parameter:
                        parameters.append(parameter)
                    continue

                parameters.extend(self._parameters_from_dict(item))
                continue

            if isinstance(item, (list, tuple)) and len(item) >= 2:
                parameter = self._make_parameter(item[0], item[1])
                if parameter:
                    parameters.append(parameter)

        return parameters

    def _make_parameter(self, key: object, value: object) -> dict | None:
        key_text = normalize_text(key)

        if not key_text:
            return None

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None

        if math.isnan(numeric_value) or math.isinf(numeric_value):
            return None

        return {
            "key": key_text,
            "value": numeric_value,
        }

    def _resolve_url(self, row: pd.Series) -> str | None:
        for column in ("url", "source_url", "link"):
            if column in row.index:
                value = normalize_text(row.get(column, ""))
                if value:
                    return value

        doc_id = normalize_text(row.get("doc_id", ""))
        source = normalize_text(row.get("source", "")).lower()
        gutenberg_id = normalize_text(row.get("gutenberg_id", ""))

        inferred_id = gutenberg_id or self._infer_gutenberg_id(doc_id)

        if inferred_id and (source == "gutendex" or doc_id.lower().startswith("gutendex:")):
            return f"https://www.gutenberg.org/ebooks/{inferred_id}"

        return None

    def _infer_gutenberg_id(self, doc_id: str) -> str:
        text = normalize_text(doc_id)
        if not text:
            return ""

        matches = re.findall(r"\d+", text)
        if not matches:
            return ""

        return str(int(matches[-1]))


def create_search_service(settings: ApiSettings) -> ThoughtMapSearchService:
    repository = create_search_index_repository(settings)
    # One encoder per configuration, shared by ranking and the radar profile.
    # They are separate consumers with separate caches, so handing them an
    # uncached factory gave each its own session and its own copy of the
    # weights.
    model_loader = lambda: get_query_encoder(settings)
    return ThoughtMapSearchService(
        repository=repository,
        model_name=settings.model_name,
        model_loader=model_loader,
        query_profile_service=QueryProfileService(model_loader),
    )


@lru_cache(maxsize=1)
def get_search_service() -> ThoughtMapSearchService:
    return create_search_service(get_settings())
