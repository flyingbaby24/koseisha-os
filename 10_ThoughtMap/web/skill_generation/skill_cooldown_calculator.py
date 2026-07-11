from __future__ import annotations


def calculate_cooldown(trigger: str, max_value: int, config: dict) -> int:
    cooldown = config.get("cooldown", {})
    if trigger != "manual":
        return int(cooldown.get("passive", 0))

    value = int(cooldown.get("manual", 2))
    threshold = int(cooldown.get("strong_effect_threshold", 45))
    if max_value >= threshold:
        value += int(cooldown.get("strong_effect_extra", 1))
    return max(0, value)

