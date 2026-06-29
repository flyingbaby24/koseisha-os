from __future__ import annotations

from typing import Iterable

import pandas as pd


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
