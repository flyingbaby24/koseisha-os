from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    from api.config import DEFAULT_MODEL_NAME
except Exception:
    DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

from .models import Effect, Skill, SkillInput
from .skill_balance_adjuster import adjust_effects
from .skill_concept_loader import DEFAULT_CONCEPTS_PATH, load_concepts
from .skill_concept_matcher import match_candidates, match_concepts
from .skill_condition_generator import generate_conditions
from .skill_cost_calculator import calculate_cost
from .skill_cooldown_calculator import calculate_cooldown
from .skill_description_generator import generate_descriptions
from .skill_duration_calculator import calculate_duration
from .skill_effect_type_generator import generate_effect_types
from .skill_name_generator import generate_skill_names
from .skill_parameter_mapper import ranked_parameters, score_for_stat
from .skill_probability_calculator import calculate_probability
from .skill_reference_embedding_generator import (
    DEFAULT_CACHE_PATH,
    candidates_by_type,
    load_or_generate_reference_embeddings,
)
from .skill_stat_generator import generate_stat
from .skill_target_generator import generate_target
from .skill_trigger_generator import generate_trigger
from .skill_validator import validate_skill
from .skill_value_calculator import calculate_value


DEFAULT_BALANCE_CONFIG_PATH = Path(__file__).with_name("balance_config.json")


def load_balance_config(path: str | Path = DEFAULT_BALANCE_CONFIG_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _stable_skill_id(doc_id: str, generation_version: int, parts: list[str]) -> str:
    raw = "|".join([doc_id, str(generation_version), *parts])
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"skill:{generation_version}:{digest}"


def _operation_for_effect(effect_type: str) -> str:
    if effect_type in {"increase", "shield"}:
        return "increase"
    if effect_type in {"decrease", "seal"}:
        return "decrease"
    if effect_type in {"heal", "hot", "sp_recover"}:
        return "recover"
    if effect_type in {"damage", "dot", "sp_damage"}:
        return "damage"
    return effect_type


def _effect_parameter(effect_type: str, stat: str) -> str:
    if effect_type in {"heal", "hot"}:
        return "hp"
    if effect_type in {"sp_recover", "sp_damage"}:
        return "sp"
    if effect_type == "shield":
        return "physical_defense"
    return stat


def _select_effect_count(effect_matches, parameter_scores: dict[str, float]) -> int:
    if len(effect_matches) < 2:
        return 1
    ranked = ranked_parameters(parameter_scores)
    top_gap = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else 100.0
    similarity_gap = effect_matches[0].similarity - effect_matches[1].similarity
    return 2 if top_gap <= 15.0 and similarity_gap <= 0.08 else 1


def _normalize_trigger_for_effects(trigger: str, effect_types: list[str]) -> str:
    """Avoid continuous passive triggers for instant or control effects."""
    if trigger != "always":
        return trigger

    unsafe_always_effects = {
        "damage",
        "heal",
        "seal",
        "sp_recover",
        "sp_damage",
    }
    if any(effect_type in unsafe_always_effects for effect_type in effect_types):
        return "turn_start"
    return trigger


def generate_skill(
    skill_input: SkillInput,
    generation_version: int = 1,
    model_name: str = DEFAULT_MODEL_NAME,
    concept_csv_path: str | Path = DEFAULT_CONCEPTS_PATH,
    reference_cache_path: str | Path = DEFAULT_CACHE_PATH,
    balance_config_path: str | Path = DEFAULT_BALANCE_CONFIG_PATH,
) -> Skill:
    input_embedding = np.asarray(skill_input.embedding, dtype=np.float32)
    if input_embedding.ndim != 1 or input_embedding.size == 0:
        raise ValueError("Skill input embedding must be a non-empty 1D vector.")

    concepts = load_concepts(concept_csv_path)
    grouped_candidates = candidates_by_type(concepts)
    reference_embeddings = load_or_generate_reference_embeddings(
        concepts,
        model_name=model_name,
        generation_version=generation_version,
        cache_path=reference_cache_path,
        expected_dimension=int(input_embedding.size),
    )
    config = load_balance_config(balance_config_path)

    matched_concepts = match_concepts(input_embedding, concepts, reference_embeddings, top=5)
    trigger_matches = match_candidates(
        input_embedding,
        grouped_candidates.get("trigger", []),
        reference_embeddings,
        top=5,
    )
    effect_matches = match_candidates(
        input_embedding,
        grouped_candidates.get("effect", []),
        reference_embeddings,
        top=5,
    )
    target_matches = match_candidates(
        input_embedding,
        grouped_candidates.get("target", []),
        reference_embeddings,
        top=7,
    )
    stat_matches = match_candidates(
        input_embedding,
        grouped_candidates.get("stat", []),
        reference_embeddings,
        top=3,
    )

    trigger = generate_trigger(trigger_matches)
    effect_count = _select_effect_count(effect_matches, skill_input.parameter_scores)
    effect_types = generate_effect_types(effect_matches, max_effects=effect_count)
    trigger = _normalize_trigger_for_effects(trigger, effect_types)
    stat = generate_stat(stat_matches, skill_input.parameter_scores)
    concept_similarity = matched_concepts[0].similarity if matched_concepts else 0.0

    effects: list[Effect] = []
    for index, effect_type in enumerate(effect_types, start=1):
        target = generate_target(target_matches, effect_type)
        parameter = _effect_parameter(effect_type, stat)
        score = score_for_stat(skill_input.parameter_scores, parameter)
        value = calculate_value(score, effect_type, config)
        effects.append(
            Effect(
                effect_order=index,
                effect_type=effect_type,
                target=target,
                parameter=parameter,
                operation=_operation_for_effect(effect_type),
                value=value,
                value_type="flat",
                duration=calculate_duration(effect_type, config),
                probability=calculate_probability(effect_type, trigger, concept_similarity, config),
            )
        )

    effects = adjust_effects(effects, config)
    total_value = int(sum(effect.value for effect in effects))
    max_value = int(max(effect.value for effect in effects))
    cost = calculate_cost(trigger, total_value, len(effects), config)
    cooldown = calculate_cooldown(trigger, max_value, config)
    name_ja, name_en = generate_skill_names(matched_concepts, effects)
    description_ja, description_en = generate_descriptions(
        matched_concepts,
        trigger,
        effects,
        cost,
        cooldown,
    )

    skill = Skill(
        skill_id=_stable_skill_id(
            skill_input.doc_id,
            generation_version,
            [trigger, name_en, ",".join(effect.effect_type for effect in effects)],
        ),
        doc_id=skill_input.doc_id,
        name_ja=name_ja,
        name_en=name_en,
        concepts=matched_concepts,
        trigger=trigger,
        conditions=generate_conditions(trigger),
        effects=effects,
        cost=cost,
        cooldown=cooldown,
        generation_version=generation_version,
        description_ja=description_ja,
        description_en=description_en,
    )
    validate_skill(skill)
    return skill
