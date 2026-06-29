from __future__ import annotations

import hashlib
from typing import Iterable

import pandas as pd


THOUGHTMAP_PARAMETERS = [
    "philosophy",
    "psychology",
    "science",
    "economy",
    "karma",
    "emotion",
    "moral",
    "ideal",
    "individual",
    "community",
]

PARAMETER_TO_STAT = {
    "philosophy": "stat_physical_attack",
    "psychology": "stat_skill_attack",
    "science": "stat_physical_defense",
    "economy": "stat_speed",
    "karma": "stat_luck",
    "emotion": "stat_evasion",
    "moral": "stat_skill_defense",
    "ideal": "stat_accuracy",
    "individual": "stat_hp",
    "community": "stat_sp",
}

CARD_COLUMNS = [
    "card_id",
    "doc_id",
    "card_name",
    "source_title",
    "author",
    "source",
    "primary_attribute",
    "secondary_attribute",
    "stat_physical_attack",
    "stat_skill_attack",
    "stat_physical_defense",
    "stat_speed",
    "stat_luck",
    "stat_evasion",
    "stat_skill_defense",
    "stat_accuracy",
    "stat_hp",
    "stat_sp",
    "rarity_seed",
    "skill_seed",
]


def _missing_columns(frame: pd.DataFrame, required: Iterable[str]) -> list[str]:
    return [column for column in required if column not in frame.columns]


def _stable_seed(*parts: object, modulo: int = 1_000_000) -> int:
    raw = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % modulo


def _normalize_parameter_scores(parameter_scores: pd.DataFrame) -> pd.DataFrame:
    scores = parameter_scores.copy()

    for parameter in THOUGHTMAP_PARAMETERS:
        scores[parameter] = pd.to_numeric(scores[parameter], errors="coerce").fillna(0.0)
        max_value = float(scores[parameter].max()) if len(scores) else 0.0
        if 0.0 < max_value <= 1.0:
            scores[parameter] = scores[parameter] * 100.0
        scores[parameter] = scores[parameter].clip(lower=0.0, upper=100.0).round().astype(int)

    return scores


def _top_attributes(row: pd.Series) -> tuple[str, str]:
    ranked = sorted(
        THOUGHTMAP_PARAMETERS,
        key=lambda parameter: (-int(row[parameter]), THOUGHTMAP_PARAMETERS.index(parameter)),
    )
    return ranked[0], ranked[1]


def validate_card_inputs(documents: pd.DataFrame, parameter_scores: pd.DataFrame) -> None:
    document_missing = _missing_columns(documents, ["doc_id"])
    score_missing = _missing_columns(parameter_scores, ["doc_id", *THOUGHTMAP_PARAMETERS])

    errors = []
    if document_missing:
        errors.append("documents missing required column(s): " + ", ".join(document_missing))
    if score_missing:
        errors.append("parameter_scores missing required column(s): " + ", ".join(score_missing))

    if errors:
        raise ValueError("; ".join(errors))


def build_cards_from_parameters(
    documents: pd.DataFrame,
    parameter_scores: pd.DataFrame,
) -> pd.DataFrame:
    """Build cards.csv-compatible data from document metadata and parameter scores.

    This function is backend-agnostic: it does not read files, write files,
    depend on a UI framework, or apply game mechanics. It only converts
    existing ThoughtMap works into deterministic card rows.
    """
    validate_card_inputs(documents, parameter_scores)

    document_columns = [
        column for column in ["doc_id", "title", "author", "source"]
        if column in documents.columns
    ]
    docs = documents[document_columns].drop_duplicates(subset=["doc_id"]).copy()

    for column in ["title", "author", "source"]:
        if column not in docs.columns:
            docs[column] = ""

    scores = _normalize_parameter_scores(parameter_scores[["doc_id", *THOUGHTMAP_PARAMETERS]])
    merged = docs.merge(scores, on="doc_id", how="inner")

    rows = []
    for index, row in merged.reset_index(drop=True).iterrows():
        primary_attribute, secondary_attribute = _top_attributes(row)
        title = str(row.get("title", "") or "").strip()
        doc_id = str(row.get("doc_id", "") or "").strip()
        card_name = title or doc_id or f"Card {index + 1}"

        card = {
            "card_id": f"card_{index + 1:06d}",
            "doc_id": doc_id,
            "card_name": card_name,
            "source_title": title,
            "author": str(row.get("author", "") or ""),
            "source": str(row.get("source", "") or ""),
            "primary_attribute": primary_attribute,
            "secondary_attribute": secondary_attribute,
            "rarity_seed": _stable_seed(doc_id, card_name, "rarity"),
            "skill_seed": _stable_seed(doc_id, primary_attribute, secondary_attribute, "skill"),
        }

        for parameter, stat_column in PARAMETER_TO_STAT.items():
            card[stat_column] = int(row[parameter])

        rows.append(card)

    return pd.DataFrame(rows, columns=CARD_COLUMNS)
