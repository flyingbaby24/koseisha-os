from __future__ import annotations

from .models import CandidateMatch


SUPPORTED_EFFECTS = {
    "increase",
    "decrease",
    "damage",
    "heal",
    "dot",
    "hot",
    "seal",
    "shield",
    "sp_recover",
    "sp_damage",
}


def generate_effect_types(matches: list[CandidateMatch], max_effects: int = 2) -> list[str]:
    effects: list[str] = []
    for match in matches:
        label = match.candidate.label
        if label in SUPPORTED_EFFECTS and label not in effects:
            effects.append(label)
        if len(effects) >= max_effects:
            break
    return effects or ["increase"]

