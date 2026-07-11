from __future__ import annotations

from .models import CandidateMatch


SUPPORTED_TRIGGERS = {
    "manual",
    "battle_start",
    "turn_start",
    "on_attack",
    "on_skill_use",
    "on_damage_taken",
    "on_evade",
    "low_hp",
    "always",
}


def generate_trigger(matches: list[CandidateMatch]) -> str:
    for match in matches:
        label = match.candidate.label
        if label in SUPPORTED_TRIGGERS:
            return label
    return "manual"

