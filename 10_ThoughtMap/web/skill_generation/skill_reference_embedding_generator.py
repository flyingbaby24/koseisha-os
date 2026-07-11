from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import numpy as np

from .models import Candidate, Concept


DEFAULT_CACHE_PATH = Path(__file__).with_name("reference_skill_embeddings.json")

TRIGGER_CANDIDATES = {
    "manual": "manual activation deliberate command intentional action",
    "battle_start": "battle opening preparation first encounter",
    "turn_start": "new turn rhythm repeated beginning momentum",
    "on_attack": "attack strike offensive action pressure",
    "on_skill_use": "skill activation technique invocation resonance",
    "on_damage_taken": "taking damage endurance reaction pain",
    "on_evade": "evade dodge avoid escape movement",
    "low_hp": "low health crisis survival desperate state",
    "always": "constant aura continuous passive condition",
}

TARGET_CANDIDATES = {
    "self": "self inner own body personal focus",
    "single_ally": "one ally support companion protection",
    "all_allies": "all allies group community harmony",
    "single_enemy": "one enemy opponent target confrontation",
    "all_enemies": "all enemies area pressure disruption",
    "random_enemy": "random enemy uncertainty chance chaos",
    "attacker": "attacker retaliation counter response",
}

EFFECT_CANDIDATES = {
    "increase": "increase strengthen raise enhance improve",
    "decrease": "decrease weaken reduce diminish suppress",
    "damage": "damage strike harm break attack",
    "heal": "heal restore mend recover life",
    "dot": "damage over time erosion poison burn",
    "hot": "healing over time regeneration renewal",
    "seal": "seal silence restrict disable bind",
    "shield": "shield protect barrier guard defense",
    "sp_recover": "sp recover energy restore resource",
    "sp_damage": "sp damage drain exhaust resource",
}

STAT_CANDIDATES = {
    "physical_attack": "physical attack force body impact",
    "skill_attack": "skill attack technique mind spell",
    "physical_defense": "physical defense armor body resistance",
    "skill_defense": "skill defense mental ward protection",
    "speed": "speed acceleration tempo movement",
    "evasion": "evasion dodge escape avoidance",
    "accuracy": "accuracy precision aim certainty",
    "luck": "luck chance karma fortune fate",
    "hp": "hp life body survival vitality",
    "sp": "sp energy spirit resource concentration",
}


def build_reference_candidates(concepts: Iterable[Concept]) -> list[Candidate]:
    candidates: list[Candidate] = []
    for concept in concepts:
        candidates.append(
            Candidate(
                candidate_id=f"concept:{concept.key}",
                candidate_type="concept",
                label=concept.label_en,
                text=f"{concept.label_en}. {concept.label_ja}. {concept.category}",
                metadata={
                    "label_ja": concept.label_ja,
                    "label_en": concept.label_en,
                    "category": concept.category,
                },
            )
        )

    for candidate_type, values in [
        ("trigger", TRIGGER_CANDIDATES),
        ("target", TARGET_CANDIDATES),
        ("effect", EFFECT_CANDIDATES),
        ("stat", STAT_CANDIDATES),
    ]:
        for label, text in values.items():
            candidates.append(
                Candidate(
                    candidate_id=f"{candidate_type}:{label}",
                    candidate_type=candidate_type,
                    label=label,
                    text=text,
                )
            )
    return candidates


def _load_sentence_transformer(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required to generate Source of Thought "
            "reference embeddings. Install the same local ThoughtMap embedding "
            "dependencies, or provide a valid reference embedding cache."
        ) from exc

    try:
        return SentenceTransformer(model_name)
    except Exception as exc:
        raise RuntimeError(f"Failed to load SentenceTransformer model '{model_name}'.") from exc


def _cache_matches(
    payload: dict,
    model_name: str,
    generation_version: int,
    candidate_ids: list[str],
    expected_dimension: int | None,
) -> bool:
    metadata = payload.get("metadata", {})
    if metadata.get("model_name") != model_name:
        return False
    if int(metadata.get("generation_version", -1)) != int(generation_version):
        return False
    if expected_dimension is not None and int(metadata.get("embedding_dimension", -1)) != expected_dimension:
        return False
    entries = payload.get("entries", [])
    return [entry.get("candidate_id") for entry in entries] == candidate_ids


def load_or_generate_reference_embeddings(
    concepts: Iterable[Concept],
    model_name: str,
    generation_version: int,
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    expected_dimension: int | None = None,
) -> dict[str, np.ndarray]:
    candidates = build_reference_candidates(concepts)
    candidate_ids = [candidate.candidate_id for candidate in candidates]
    cache = Path(cache_path)

    if cache.exists():
        payload = json.loads(cache.read_text(encoding="utf-8"))
        if _cache_matches(payload, model_name, generation_version, candidate_ids, expected_dimension):
            return {
                entry["candidate_id"]: np.asarray(entry["embedding"], dtype=np.float32)
                for entry in payload.get("entries", [])
            }

    model = _load_sentence_transformer(model_name)
    vectors = model.encode([candidate.text for candidate in candidates], show_progress_bar=False)
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim != 2:
        raise RuntimeError("Reference embedding generation did not return a 2D matrix.")

    dimension = int(vectors.shape[1])
    if expected_dimension is not None and dimension != expected_dimension:
        raise ValueError(
            f"Reference embedding dimension mismatch: input={expected_dimension}, "
            f"model={dimension}, model_name={model_name}"
        )

    payload = {
        "metadata": {
            "model_name": model_name,
            "embedding_dimension": dimension,
            "generation_version": int(generation_version),
        },
        "entries": [
            {
                "candidate_id": candidate.candidate_id,
                "candidate_type": candidate.candidate_type,
                "label": candidate.label,
                "text": candidate.text,
                "metadata": candidate.metadata,
                "embedding": [float(x) for x in vectors[index]],
            }
            for index, candidate in enumerate(candidates)
        ],
    }
    cache.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        candidate.candidate_id: vectors[index]
        for index, candidate in enumerate(candidates)
    }


def candidates_by_type(concepts: Iterable[Concept]) -> dict[str, list[Candidate]]:
    grouped: dict[str, list[Candidate]] = {}
    for candidate in build_reference_candidates(concepts):
        grouped.setdefault(candidate.candidate_type, []).append(candidate)
    return grouped

