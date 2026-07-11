from __future__ import annotations


def calculate_duration(effect_type: str, config: dict) -> int:
    duration = config.get("duration", {})
    if effect_type in {"damage", "heal", "sp_recover", "sp_damage"}:
        return int(duration.get("instant", 0))
    if effect_type in {"dot"}:
        return int(duration.get("damage_over_time", 3))
    if effect_type in {"hot"}:
        return int(duration.get("damage_over_time", 3))
    if effect_type == "seal":
        return int(duration.get("seal", 1))
    if effect_type == "shield":
        return int(duration.get("shield", 2))
    return int(duration.get("buff", 2))

