from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from search_utils import (
    format_similarity,
    normalize_text,
    parse_embedding,
    work_similarity_by_vector,
)

from .config import ApiSettings, get_settings
from .repositories import SearchIndexRepository, create_search_index_repository
from .schemas import SearchResponse, SearchResult


SEARCH_MODES = {"keyword", "embedding", "hybrid"}

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
    ) -> None:
        self.repository = repository
        self.model_name = model_name

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
            target_doc_id=target_doc_id,
            user_email=user_email,
        )

        return SearchResponse(
            results=results,
            query_parameters=None,
        )

    def search(
        self,
        query: str = "",
        top: int = 10,
        mode: str = "keyword",
        source: str = "",
        category: str = "",
        target_doc_id: str = "",
        user_email: str = "",
    ) -> list[SearchResult]:
        query = str(query or "").strip()
        mode = str(mode or "keyword").strip().lower()
        source = str(source or "").strip()
        category = str(category or "").strip()
        target_doc_id = str(target_doc_id or "").strip()
        user_email = str(user_email or "").strip()

        if mode not in SEARCH_MODES:
            raise ValueError(f"Unsupported search mode: {mode}")

        index = self.repository.load_index()
        index = self._filter_by_source(index, source)
        index = self._filter_by_category(index, category)

        if index.empty:
            return []

        if mode == "keyword":
            if not query:
                return []
            results = self._keyword_search(index, query, top)

        elif mode == "embedding":
            if not target_doc_id:
                raise ValueError("target_doc_id is required for embedding mode.")
            results = self._embedding_search(
                index=index,
                target_doc_id=target_doc_id,
                top=top,
                user_email=user_email,
            )

        else:
            if not target_doc_id:
                raise ValueError("target_doc_id is required for hybrid mode.")
            results = self._hybrid_embedding_search(
                index=index,
                query=query,
                target_doc_id=target_doc_id,
                top=top,
                user_email=user_email,
            )

        return self._to_search_results(results)

    def _filter_by_source(self, index: pd.DataFrame, source: str) -> pd.DataFrame:
        if not source or source.lower() == "all" or "source" not in index.columns:
            return index
        return index[index["source"].map(normalize_text).str.lower() == source.lower()].reset_index(drop=True)

    def _filter_by_category(self, index: pd.DataFrame, category: str) -> pd.DataFrame:
        if not category or category.lower() == "all" or "category" not in index.columns:
            return index
        return index[index["category"].map(normalize_text).str.lower() == category.lower()].reset_index(drop=True)

    def _keyword_search(self, index: pd.DataFrame, query: str, top: int) -> pd.DataFrame:
        results = index.copy()
        results["similarity"] = results.apply(lambda row: self._keyword_score(row, query), axis=1)
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
        )

        return format_similarity(results)

    def _hybrid_embedding_search(
        self,
        index: pd.DataFrame,
        query: str,
        target_doc_id: str,
        top: int,
        user_email: str = "",
    ) -> pd.DataFrame:
        target_vec, exclude_doc_id = self._resolve_target_embedding(
            index=index,
            target_doc_id=target_doc_id,
            user_email=user_email,
        )

        candidates = index.copy()

        if query:
            candidates["keyword_score"] = candidates.apply(
                lambda row: self._keyword_score(row, query),
                axis=1,
            )
            candidates = candidates[candidates["keyword_score"] > 0].copy()

        if candidates.empty:
            return pd.DataFrame()

        results = work_similarity_by_vector(
            candidates,
            target_vec=target_vec,
            top=max(top, len(candidates)),
            exclude_doc_id=exclude_doc_id,
            include_self=False,
        )

        results = format_similarity(results)

        if query and "keyword_score" in candidates.columns:
            keyword_scores = candidates[["doc_id", "keyword_score"]].copy()
            results = results.merge(keyword_scores, on="doc_id", how="left")
            results["keyword_score"] = results["keyword_score"].fillna(0.0)
            results["similarity"] = (
                results["similarity"].astype(float) * 0.8
                + results["keyword_score"].astype(float) * 0.2
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

    def _user_embedding_path(self, user_email: str) -> Path:
        normalized = str(user_email or "").strip().lower()
        if not normalized:
            raise ValueError("user_email is required for personal embedding search.")

        user_id = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
        base_dir = Path(__file__).resolve().parents[1]
        return base_dir / "user_data" / user_id / "thoughtmap_embeddings.csv"

    def _load_user_embeddings(self, user_email: str) -> pd.DataFrame:
        csv_path = self._user_embedding_path(user_email)

        if not csv_path.exists():
            raise ValueError(f"Personal embedding DB not found: {csv_path}")

        df = pd.read_csv(csv_path, dtype=str).fillna("")

        if "embedding" not in df.columns:
            raise ValueError("Personal embedding CSV must contain an embedding column.")

        if "doc_id" not in df.columns:
            df["doc_id"] = [f"user_doc_{i:06d}" for i in range(len(df))]

        for col in ["title", "author", "source", "category", "subcategory", "source_url", "url"]:
            if col not in df.columns:
                df[col] = ""

        df["_embedding_vec"] = df["embedding"].map(parse_embedding)
        df = df[df["_embedding_vec"].notna()].copy()

        if df.empty:
            raise ValueError("Personal embedding CSV has no valid embedding rows.")

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

    def _to_search_results(self, results: pd.DataFrame) -> list[SearchResult]:
        output: list[SearchResult] = []

        if results is None or results.empty:
            return output

        for _, row in results.iterrows():
            output.append(
                SearchResult(
                    doc_id=str(row.get("doc_id", "") or ""),
                    title=str(row.get("title", "") or ""),
                    author=str(row.get("author", "") or ""),
                    source=str(row.get("source", "") or ""),
                    similarity=float(row.get("similarity", 0.0) or 0.0),
                    url=self._resolve_url(row),
                    parameters=None,
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


def create_search_service(settings: ApiSettings) -> ThoughtMapSearchService:
    repository = create_search_index_repository(settings)
    return ThoughtMapSearchService(
        repository=repository,
        model_name=settings.model_name,
    )


@lru_cache(maxsize=1)
def get_search_service() -> ThoughtMapSearchService:
    return create_search_service(get_settings())
