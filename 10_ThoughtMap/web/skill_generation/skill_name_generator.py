from __future__ import annotations

from .models import Concept, Effect


EFFECT_NAME_JA = {
    "increase": "増幅",
    "decrease": "低下",
    "damage": "打撃",
    "heal": "回復",
    "dot": "浸食",
    "hot": "再生",
    "seal": "封印",
    "shield": "守護",
    "sp_recover": "充填",
    "sp_damage": "消耗",
}

EFFECT_NAME_EN = {
    "increase": "Amplification",
    "decrease": "Suppression",
    "damage": "Strike",
    "heal": "Restoration",
    "dot": "Erosion",
    "hot": "Regeneration",
    "seal": "Seal",
    "shield": "Ward",
    "sp_recover": "Charge",
    "sp_damage": "Drain",
}


def generate_skill_names(concepts: list[Concept], effects: list[Effect]) -> tuple[str, str]:
    concept = concepts[0] if concepts else Concept(label_ja="思想", label_en="Thought", category="")
    primary = effects[0].effect_type if effects else "increase"
    return (
        f"{concept.label_ja}の{EFFECT_NAME_JA.get(primary, '技法')}",
        f"{concept.label_en} {EFFECT_NAME_EN.get(primary, 'Technique')}",
    )

