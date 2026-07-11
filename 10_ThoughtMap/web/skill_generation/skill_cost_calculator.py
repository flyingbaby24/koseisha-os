from __future__ import annotations

from .models import Cost


def calculate_cost(trigger: str, total_value: int, effect_count: int, config: dict) -> Cost:
    cost_config = config.get("cost", {})
    if trigger != "manual":
        return Cost(sp=int(cost_config.get("passive_sp_base", 0)))

    base = int(cost_config.get("manual_sp_base", 8))
    scale = float(cost_config.get("manual_sp_scale", 0.12))
    sp = int(round(base + total_value * scale + max(0, effect_count - 1) * 4))
    return Cost(sp=max(0, sp), hp_percent=0.0, consume_action=True)

