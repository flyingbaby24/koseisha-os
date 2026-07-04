from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd
from sentence_transformers import SentenceTransformer

from search_utils import format_similarity, normalize_text, work_similarity_by_vector

from .config import ApiSettings, get_settings
from .filter_service import ParameterFilterService
from .repositories import SearchIndexRepository, create_search_index_repository
from .schemas import SearchResponse, SearchResult


SEARCH_MODES = {"semantic", "keyword", "hybrid"}
DEFAULT_PARAMETER_FILTER = "general"
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
    """Application-level search service used by HTTP clients.

    The service owns query embedding and search orchestration. Data loading stays
    behind a repository, so moving from CSV to SQLite later does not affect API
    responses or Unity.
    """

    def __init__(
        self,
        repository: SearchIndexRepository,
        model_name: str,
    ) -> None:
        self.repository = repository
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self._filter_service: ParameterFilterService | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def filter_service(self) -> ParameterFilterService:
        if self._filter_service is None:
            self._filter_service = ParameterFilterService(self.model)
        return self._filter_service

    def search_response(
        self,
        query: str,
        top: int = 10,
        mode: str = "semantic",
        source: str = "",
        filter_name: str = "",
    ) -> SearchResponse:
        query = str(query or "").strip()
        filter_name = self._effective_filter_name(filter_name)
        results = self.search(query, top=top, mode=mode, source=source, filter_name=filter_name)
        query_parameters = self.filter_service.score_text(query, filter_name) if filter_name else None
        return SearchResponse(results=results, query_parameters=query_parameters)

    def search(
        self,
        query: str,
        top: int = 10,
        mode: str = "semantic",
        source: str = "",
        filter_name: str = "",
    ) -> list[SearchResult]:
        query = str(query or "").strip()
        mode = str(mode or "semantic").strip().lower()
        source = str(source or "").strip()
        filter_name = self._effective_filter_name(filter_name)
        if not query:
            return []
        if mode not in SEARCH_MODES:
            raise ValueError(f"Unsupported search mode: {mode}")

        index = self.repository.load_index()
        index = self._filter_by_source(index, source)
        if index.empty:
            return []

        if mode == "keyword":
            results = self._keyword_search(index, query, top)
        elif mode == "hybrid":
            results = self._hybrid_search(index, query, top)
        else:
            results = self._semantic_search(index, query, top)

        return self._to_search_results(results, index=index, filter_name=filter_name)

    def _effective_filter_name(self, filter_name: str) -> str:
        name = str(filter_name or "").strip().lower()
        if not name or name == "all":
            return DEFAULT_PARAMETER_FILTER
        return name

    def _filter_by_source(self, index: pd.DataFrame, source: str) -> pd.DataFrame:
        if not source or "source" not in index.columns:
            return index
        return index[index["source"].map(normalize_text) == source].reset_index(drop=True)

    def _semantic_search(self, index: pd.DataFrame, query: str, top: int) -> pd.DataFrame:
        query_vec = self.model.encode([query], show_progress_bar=False)[0]
        results = work_similarity_by_vector(index, query_vec, top=top)
        return format_similarity(results)

    def _keyword_search(self, index: pd.DataFrame, query: str, top: int) -> pd.DataFrame:
        results = index.copy()
        results["similarity"] = results.apply(lambda row: self._keyword_score(row, query), axis=1)
        results = results[results["similarity"] > 0]
        results = results.sort_values(
            ["similarity", "title"],
            ascending=[False, True],
        ).head(top).reset_index(drop=True)
        return format_similarity(results)

    def _hybrid_search(self, index: pd.DataFrame, query: str, top: int) -> pd.DataFrame:
        semantic = self._semantic_search(index, query, max(top, len(index)))
        keyword_scores = index[["doc_id"]].copy()
        keyword_scores["keyword_score"] = index.apply(
            lambda row: self._keyword_score(row, query),
            axis=1,
        )

        results = semantic.merge(keyword_scores, on="doc_id", how="left")
        results["keyword_score"] = results["keyword_score"].fillna(0.0)
        results["semantic_score"] = results["similarity"].astype(float)
        results["similarity"] = results.apply(
            lambda row: self._hybrid_score(
                float(row.get("keyword_score", 0.0) or 0.0),
                float(row.get("semantic_score", 0.0) or 0.0),
            ),
            axis=1,
        )
        results = results.sort_values(
            ["keyword_score", "similarity", "title"],
            ascending=[False, False, True],
        ).head(top).reset_index(drop=True)
        return format_similarity(results)

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
        if column == "source_url":
            return 0.75
        return 0.65

    def _hybrid_score(self, keyword_score: float, semantic_score: float) -> float:
        if keyword_score > 0:
            return 1.0 + keyword_score + (semantic_score * 0.1)
        return semantic_score

    def _to_search_results(
        self,
        results: pd.DataFrame,
        index: pd.DataFrame,
        filter_name: str = "",
    ) -> list[SearchResult]:
        output: list[SearchResult] = []
        embedding_by_doc_id = self._embedding_lookup(index) if filter_name else {}

        for _, row in results.iterrows():
            doc_id = str(row.get("doc_id", "") or "")
            parameters = None
            if filter_name:
                parameters = self.filter_service.score_embedding(
                    embedding_by_doc_id.get(doc_id),
                    filter_name,
                )

            output.append(
                SearchResult(
                    doc_id=doc_id,
                    title=str(row.get("title", "") or ""),
                    author=str(row.get("author", "") or ""),
                    source=str(row.get("source", "") or ""),
                    similarity=float(row.get("similarity", 0.0) or 0.0),
                    url=self._resolve_url(row),
                    parameters=parameters,
                )
            )
        return output

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

    def _embedding_lookup(self, index: pd.DataFrame) -> dict[str, object]:
        if "doc_id" not in index.columns or "_embedding_vec" not in index.columns:
            return {}
        return {
            str(row.get("doc_id", "") or ""): row.get("_embedding_vec")
            for _, row in index.iterrows()
        }


def create_search_service(settings: ApiSettings) -> ThoughtMapSearchService:
    repository = create_search_index_repository(settings)
    return ThoughtMapSearchService(repository=repository, model_name=settings.model_name)


@lru_cache(maxsize=1)
def get_search_service() -> ThoughtMapSearchService:
    return create_search_service(get_settings())
