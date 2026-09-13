from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def _row_norms(matrix: np.ndarray) -> np.ndarray:
    """Euclidean norm of each row.

    `sqrt(einsum(...))` rather than `np.linalg.norm(..., axis=1)` because that
    is the reduction scikit-learn's `row_norms` performs, and the two can
    differ by an ULP on float32. The point of this function is to reproduce
    those bits, so it copies the arithmetic rather than an equivalent of it.
    """
    return np.sqrt(np.einsum("ij,ij->i", matrix, matrix))


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """Scale each row to unit length, leaving an all-zero row at zero.

    Mirrors `sklearn.preprocessing.normalize`, including its handling of the
    degenerate row: a zero norm is replaced by 1.0 before the division, so a
    zero row divides to zeros rather than NaNs.
    """
    norms = _row_norms(matrix)
    norms[norms == 0.0] = 1.0
    return matrix / norms[:, np.newaxis]


def cosine_similarity(X, Y):
    """Pairwise cosine similarity between the rows of `X` and of `Y`.

    A drop-in replacement for `sklearn.metrics.pairwise.cosine_similarity`,
    kept deliberately narrow: that one call was the *only* thing the Thought
    Composition pipeline used scikit-learn for, and importing scikit-learn is
    not possible in the production container — the runtime deliberately
    excludes it, so `make_filter_scores` raised `ModuleNotFoundError` and the
    query radar silently degraded to "no profile" on the public demo.

    The algorithm is unchanged: L2-normalise both sides, then take the inner
    product. Two details are reproduced rather than reinvented, because these
    values feed a user-visible radar:

    - **dtype promotion.** scikit-learn's `check_pairwise_arrays` computes in
      float32 only when *both* inputs are float32, and in float64 otherwise.
      Query vectors are float32, so this keeps the production path in float32
      exactly as it was.
    - **zero rows.** See `_normalize_rows`.

    `api.verify_query_profile_equivalence` checks this against the
    scikit-learn implementation on the full 63,891-document corpus.
    """
    X = np.asarray(X)
    Y = np.asarray(Y)

    dtype = np.float32 if (X.dtype == np.float32 and Y.dtype == np.float32) else np.float64
    X = np.asarray(X, dtype=dtype)
    Y = np.asarray(Y, dtype=dtype)

    if X.ndim == 1:
        X = X.reshape(1, -1)
    if Y.ndim == 1:
        Y = Y.reshape(1, -1)

    if X.shape[1] != Y.shape[1]:
        raise ValueError(
            f"Incompatible dimensions: X has {X.shape[1]} features, "
            f"Y has {Y.shape[1]}."
        )

    return _normalize_rows(X) @ _normalize_rows(Y).T


THOUGHT_COMPOSITION_PARAMETERS = [
    "philosophy",
    "psychology",
    "science",
    "economics",
    "karma",
    "emotion",
    "morality",
    "ideal",
    "individual",
    "community",
]


def make_filter_scores(embeddings, categories, model):
    if not categories:
        return None

    category_names = list(categories.keys())
    category_texts = list(categories.values())
    category_embeddings = model.encode(category_texts, show_progress_bar=False)
    scores = cosine_similarity(embeddings, category_embeddings)

    scores = np.clip(scores, 0, None)
    totals = scores.sum(axis=1, keepdims=True)
    scores = np.divide(scores, totals, out=np.zeros_like(scores), where=totals != 0)

    return pd.DataFrame(scores, columns=category_names)


def missing_parameter_columns(
    filter_score_df: pd.DataFrame,
    parameters: Iterable[str] = THOUGHT_COMPOSITION_PARAMETERS,
) -> list[str]:
    return [parameter for parameter in parameters if parameter not in filter_score_df.columns]


def make_parameter_scores(
    documents: pd.DataFrame,
    filter_score_df: pd.DataFrame,
    parameters: Iterable[str] = THOUGHT_COMPOSITION_PARAMETERS,
) -> pd.DataFrame:
    """Extract reusable per-document Thought Composition parameter scores.

    The values come directly from the existing Thought Composition pipeline.
    This helper does not calculate a new scoring system; it only packages the
    already-computed filter affinities into a CSV-friendly table for downstream
    tools such as card generation.
    """
    parameter_list = list(parameters)

    if filter_score_df is None:
        raise ValueError("filter_score_df is required")

    if "doc_id" not in documents.columns:
        raise ValueError("documents missing required column: doc_id")

    missing = missing_parameter_columns(filter_score_df, parameter_list)
    if missing:
        raise ValueError(
            "filter_score_df missing Thought Composition parameter column(s): "
            + ", ".join(missing)
        )

    if len(documents) != len(filter_score_df):
        raise ValueError(
            "documents and filter_score_df must have the same number of rows"
        )

    metadata_columns = [
        column for column in ["doc_id", "title", "author", "source"]
        if column in documents.columns
    ]
    metadata = documents[metadata_columns].reset_index(drop=True).copy()
    scores = filter_score_df[parameter_list].reset_index(drop=True).copy()

    for parameter in parameter_list:
        scores[parameter] = pd.to_numeric(scores[parameter], errors="coerce").fillna(0.0)

    return pd.concat([metadata, scores], axis=1)
