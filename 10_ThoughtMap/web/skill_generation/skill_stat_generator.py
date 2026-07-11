from __future__ import annotations

from .models import CandidateMatch
from .skill_parameter_mapper import dominant_parameter, parameter_to_stat


def generate_stat(matches: list[CandidateMatch], parameter_scores: dict[str, float]) -> str:
    for match in matches:
        label = match.candidate.label
        if label:
            return label
    return parameter_to_stat(dominant_parameter(parameter_scores))

