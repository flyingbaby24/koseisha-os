from __future__ import annotations


def _score_to_100(score: float) -> float:
    value = float(score)
    if 0.0 <= value <= 1.0:
        value *= 100.0
    return max(0.0, min(100.0, value))


def calculate_value(score: float, effect_type: str, config: dict) -> int:
    value_config = config.get("value", {})
    base = float(value_config.get("base", 10))
    scale = float(value_config.get("scale", 0.55))
    minimum = int(value_config.get("min", 1))
    maximum = int(value_config.get("max", 60))

    raw = base + (_score_to_100(score) * scale)
    if effect_type in {"seal", "shield"}:
        raw *= 0.75
    if effect_type in {"damage", "heal"}:
        raw *= 1.05
    return int(max(minimum, min(maximum, round(raw))))

