from __future__ import annotations


def calculate_probability(effect_type: str, trigger: str, concept_similarity: float, config: dict) -> float:
    probability = config.get("probability", {})
    base = float(probability.get("base", 0.7))
    minimum = float(probability.get("min", 0.2))
    maximum = float(probability.get("max", 1.0))

    value = base + (float(concept_similarity) * 0.18)
    if trigger == "always":
        value = 1.0
    elif trigger in {"on_evade", "low_hp"}:
        value -= 0.08
    if effect_type in {"seal", "sp_damage"}:
        value -= 0.1
    return round(max(minimum, min(maximum, value)), 3)

