from __future__ import annotations


PARAMETER_ALIASES = {
    "philosophy": "philosophy",
    "哲学": "philosophy",
    "psychology": "psychology",
    "心理": "psychology",
    "science": "science",
    "科学": "science",
    "economy": "economics",
    "economics": "economics",
    "経済": "economics",
    "karma": "karma",
    "カルマ": "karma",
    "emotion": "emotion",
    "感情": "emotion",
    "moral": "morality",
    "morality": "morality",
    "モラル": "morality",
    "ideal": "ideal",
    "ideology": "ideal",
    "理念": "ideal",
    "individual": "individual",
    "個人": "individual",
    "community": "community",
    "共同体": "community",
}

PARAMETER_ORDER = [
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

PARAMETER_TO_STAT = {
    "philosophy": "physical_attack",
    "psychology": "skill_attack",
    "science": "physical_defense",
    "economics": "speed",
    "karma": "luck",
    "emotion": "evasion",
    "morality": "skill_defense",
    "ideal": "accuracy",
    "individual": "hp",
    "community": "sp",
}


def normalize_parameter_scores(parameter_scores: dict[str, float]) -> dict[str, float]:
    normalized = {parameter: 0.0 for parameter in PARAMETER_ORDER}
    for key, value in parameter_scores.items():
        canonical = PARAMETER_ALIASES.get(str(key).strip().lower(), str(key).strip().lower())
        if canonical in normalized:
            try:
                normalized[canonical] = float(value)
            except (TypeError, ValueError):
                normalized[canonical] = 0.0
    return normalized


def dominant_parameter(parameter_scores: dict[str, float]) -> str:
    scores = normalize_parameter_scores(parameter_scores)
    return sorted(PARAMETER_ORDER, key=lambda p: (-scores[p], PARAMETER_ORDER.index(p)))[0]


def ranked_parameters(parameter_scores: dict[str, float]) -> list[tuple[str, float]]:
    scores = normalize_parameter_scores(parameter_scores)
    return sorted(scores.items(), key=lambda item: (-item[1], PARAMETER_ORDER.index(item[0])))


def parameter_to_stat(parameter: str) -> str:
    return PARAMETER_TO_STAT.get(parameter, "physical_attack")


def score_for_stat(parameter_scores: dict[str, float], stat: str) -> float:
    scores = normalize_parameter_scores(parameter_scores)
    for parameter, mapped_stat in PARAMETER_TO_STAT.items():
        if mapped_stat == stat:
            return float(scores.get(parameter, 0.0))
    return 0.0

