from __future__ import annotations

from .models import CandidateMatch


SUPPORTED_TARGETS = {
    "self",
    "single_ally",
    "all_allies",
    "single_enemy",
    "all_enemies",
    "random_enemy",
    "attacker",
}


def generate_target(matches: list[CandidateMatch], effect_type: str) -> str:
    if effect_type in {"heal", "hot", "shield", "increase", "sp_recover"}:
        preferred = {"self", "single_ally", "all_allies"}
    elif effect_type in {"damage", "dot", "decrease", "seal", "sp_damage"}:
        preferred = {"single_enemy", "all_enemies", "random_enemy", "attacker"}
    else:
        preferred = SUPPORTED_TARGETS

    for match in matches:
        label = match.candidate.label
        if label in preferred:
            return label
    for match in matches:
        label = match.candidate.label
        if label in SUPPORTED_TARGETS:
            return label
    return "self"

