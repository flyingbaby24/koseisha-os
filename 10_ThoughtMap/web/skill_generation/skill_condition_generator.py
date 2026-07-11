from __future__ import annotations

from .models import Condition


def generate_conditions(trigger: str) -> list[Condition]:
    if trigger == "low_hp":
        return [Condition(condition_type="hp_percent", parameter="hp", operator="<=", value=35.0)]
    return []

