from __future__ import annotations

from .models import Concept, Effect


def _effect_summary(effect: Effect) -> str:
    return (
        f"{effect.target} {effect.effect_type} {effect.parameter} "
        f"{effect.value:g} for {effect.duration} turn(s), p={effect.probability:g}"
    )


def generate_descriptions(concepts: list[Concept], trigger: str, effects: list[Effect]) -> tuple[str, str]:
    concept = concepts[0] if concepts else Concept(label_ja="思想", label_en="Thought", category="")
    effect_text = "; ".join(_effect_summary(effect) for effect in effects)
    description_en = (
        f"Activated by {trigger}. A skill shaped by {concept.label_en}; {effect_text}."
    )
    description_ja = (
        f"{trigger}で発動。{concept.label_ja}の概念から生成されたスキル。{effect_text}。"
    )
    return description_ja, description_en

