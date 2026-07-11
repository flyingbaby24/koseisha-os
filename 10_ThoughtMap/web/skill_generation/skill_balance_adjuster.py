from __future__ import annotations

from dataclasses import replace

from .models import Effect


def adjust_effects(effects: list[Effect], config: dict) -> list[Effect]:
    balance = config.get("balance", {})
    max_total_power = float(balance.get("max_total_power", 90))
    multi_effect_multiplier = float(balance.get("multi_effect_multiplier", 0.72))

    adjusted = effects
    if len(adjusted) > 1:
        adjusted = [
            replace(effect, value=max(1, round(effect.value * multi_effect_multiplier)))
            for effect in adjusted
        ]

    total = sum(float(effect.value) * max(1, effect.duration or 1) * effect.probability for effect in adjusted)
    if total > max_total_power and total > 0:
        ratio = max_total_power / total
        adjusted = [
            replace(effect, value=max(1, round(effect.value * ratio)))
            for effect in adjusted
        ]
    return adjusted

