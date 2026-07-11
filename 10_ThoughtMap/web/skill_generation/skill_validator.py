from __future__ import annotations

from .models import Skill
from .skill_effect_type_generator import SUPPORTED_EFFECTS
from .skill_target_generator import SUPPORTED_TARGETS
from .skill_trigger_generator import SUPPORTED_TRIGGERS


UNSAFE_ALWAYS_EFFECTS = {
    "damage",
    "heal",
    "seal",
    "sp_recover",
    "sp_damage",
}


def validate_skill(skill: Skill) -> None:
    if not skill.doc_id:
        raise ValueError("Skill is missing doc_id.")
    if skill.trigger not in SUPPORTED_TRIGGERS:
        raise ValueError(f"Unsupported trigger: {skill.trigger}")
    if not 1 <= len(skill.effects) <= 2:
        raise ValueError("Skill must contain 1 or 2 effects.")
    if skill.trigger == "always":
        unsafe = [effect.effect_type for effect in skill.effects if effect.effect_type in UNSAFE_ALWAYS_EFFECTS]
        if unsafe:
            raise ValueError(
                "trigger=always cannot be used with instant/control effect(s): "
                + ", ".join(unsafe)
            )

    for effect in skill.effects:
        if effect.effect_type not in SUPPORTED_EFFECTS:
            raise ValueError(f"Unsupported effect_type: {effect.effect_type}")
        if effect.target not in SUPPORTED_TARGETS:
            raise ValueError(f"Unsupported target: {effect.target}")
        if effect.value <= 0:
            raise ValueError("Effect value must be positive.")
        if not 0.0 <= effect.probability <= 1.0:
            raise ValueError("Effect probability must be between 0 and 1.")
