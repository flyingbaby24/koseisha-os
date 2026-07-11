from __future__ import annotations

import math

import numpy as np

from .models import Candidate, CandidateMatch, Concept


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0 or math.isnan(denom):
        return 0.0
    return float(np.dot(a, b) / denom)


def match_candidates(
    input_embedding: np.ndarray,
    candidates: list[Candidate],
    embeddings: dict[str, np.ndarray],
    top: int = 1,
) -> list[CandidateMatch]:
    rows: list[tuple[Candidate, float]] = []
    for candidate in candidates:
        vector = embeddings.get(candidate.candidate_id)
        if vector is None:
            continue
        if len(input_embedding) != len(vector):
            raise ValueError(
                f"Embedding dimension mismatch for {candidate.candidate_id}: "
                f"input={len(input_embedding)}, candidate={len(vector)}"
            )
        rows.append((candidate, cosine(input_embedding, vector)))

    rows.sort(key=lambda item: (-item[1], item[0].candidate_id))
    return [
        CandidateMatch(candidate=candidate, similarity=similarity, rank=index + 1)
        for index, (candidate, similarity) in enumerate(rows[:top])
    ]


def match_concepts(
    input_embedding: np.ndarray,
    concepts: list[Concept],
    embeddings: dict[str, np.ndarray],
    top: int = 5,
) -> list[Concept]:
    candidates = [
        Candidate(
            candidate_id=f"concept:{concept.key}",
            candidate_type="concept",
            label=concept.label_en,
            text=concept.label_en,
            metadata={
                "label_ja": concept.label_ja,
                "label_en": concept.label_en,
                "category": concept.category,
            },
        )
        for concept in concepts
    ]
    matches = match_candidates(input_embedding, candidates, embeddings, top=top)
    return [
        Concept(
            label_ja=match.candidate.metadata.get("label_ja", ""),
            label_en=match.candidate.metadata.get("label_en", match.candidate.label),
            category=match.candidate.metadata.get("category", ""),
            similarity=round(float(match.similarity), 6),
            rank=match.rank,
        )
        for match in matches
    ]

