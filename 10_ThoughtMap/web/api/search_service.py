from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from search_utils import format_similarity, work_similarity_by_vector

from .config import ApiSettings, get_settings
from .repositories import SearchIndexRepository, create_search_index_repository
from .schemas import SearchResult


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

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def search(self, query: str, top: int = 10) -> list[SearchResult]:
        query = str(query or "").strip()
        if not query:
            return []

        index = self.repository.load_index()
        query_vec = self.model.encode([query], show_progress_bar=False)[0]
        results = work_similarity_by_vector(index, query_vec, top=top)
        results = format_similarity(results)

        output: list[SearchResult] = []
        for _, row in results.iterrows():
            output.append(
                SearchResult(
                    title=str(row.get("title", "") or ""),
                    author=str(row.get("author", "") or ""),
                )
            )
        return output


def create_search_service(settings: ApiSettings) -> ThoughtMapSearchService:
    repository = create_search_index_repository(settings)
    return ThoughtMapSearchService(repository=repository, model_name=settings.model_name)


@lru_cache(maxsize=1)
def get_search_service() -> ThoughtMapSearchService:
    return create_search_service(get_settings())
