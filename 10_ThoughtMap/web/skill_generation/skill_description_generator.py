from __future__ import annotations

from .models import Concept, Cost, Effect


TRIGGER_JA = {
    "manual": "手動で使用したとき",
    "battle_start": "戦闘開始時",
    "turn_start": "ターン開始時",
    "on_attack": "攻撃時",
    "on_skill_use": "スキル使用時",
    "on_damage_taken": "ダメージを受けたとき",
    "on_evade": "回避したとき",
    "low_hp": "HPが低下したとき",
    "always": "常時",
}

TRIGGER_EN = {
    "manual": "when used manually",
    "battle_start": "at the start of battle",
    "turn_start": "at the start of a turn",
    "on_attack": "when attacking",
    "on_skill_use": "when using a skill",
    "on_damage_taken": "when taking damage",
    "on_evade": "when evading",
    "low_hp": "when HP is low",
    "always": "continuously",
}

TARGET_JA = {
    "self": "自身",
    "single_ally": "味方単体",
    "all_allies": "味方全体",
    "single_enemy": "敵単体",
    "all_enemies": "敵全体",
    "random_enemy": "ランダムな敵",
    "attacker": "攻撃してきた相手",
}

TARGET_EN = {
    "self": "self",
    "single_ally": "one ally",
    "all_allies": "all allies",
    "single_enemy": "one enemy",
    "all_enemies": "all enemies",
    "random_enemy": "a random enemy",
    "attacker": "the attacker",
}

PARAMETER_JA = {
    "physical_attack": "物理攻撃力",
    "skill_attack": "スキル攻撃力",
    "physical_defense": "物理防御力",
    "skill_defense": "スキル防御力",
    "speed": "素早さ",
    "evasion": "回避率",
    "accuracy": "命中率",
    "luck": "運",
    "hp": "HP",
    "sp": "SP",
}

PARAMETER_EN = {
    "physical_attack": "physical attack",
    "skill_attack": "skill attack",
    "physical_defense": "physical defense",
    "skill_defense": "skill defense",
    "speed": "speed",
    "evasion": "evasion",
    "accuracy": "accuracy",
    "luck": "luck",
    "hp": "HP",
    "sp": "SP",
}


def _duration_ja(effect: Effect) -> str:
    if effect.duration <= 0:
        return "即時"
    return f"{effect.duration}ターン"


def _duration_en(effect: Effect) -> str:
    if effect.duration <= 0:
        return "immediately"
    return f"for {effect.duration} turn(s)"


def _effect_summary_ja(effect: Effect) -> str:
    target = TARGET_JA.get(effect.target, effect.target)
    parameter = PARAMETER_JA.get(effect.parameter, effect.parameter)
    value = f"{effect.value:g}"

    if effect.effect_type == "increase":
        body = f"{target}の{parameter}を{value}上昇させる"
    elif effect.effect_type == "decrease":
        body = f"{target}の{parameter}を{value}低下させる"
    elif effect.effect_type == "damage":
        body = f"{target}に{value}ダメージを与える"
    elif effect.effect_type == "heal":
        body = f"{target}のHPを{value}回復する"
    elif effect.effect_type == "dot":
        body = f"{target}へ継続ダメージ{value}を与える"
    elif effect.effect_type == "hot":
        body = f"{target}へ継続回復{value}を与える"
    elif effect.effect_type == "seal":
        body = f"{target}を封印する"
    elif effect.effect_type == "shield":
        body = f"{target}に防御シールド{value}を与える"
    elif effect.effect_type == "sp_recover":
        body = f"{target}のSPを{value}回復する"
    elif effect.effect_type == "sp_damage":
        body = f"{target}のSPを{value}減少させる"
    else:
        body = f"{target}に{effect.effect_type}を与える"

    chance = int(round(effect.probability * 100))
    return f"{body}。効果時間: {_duration_ja(effect)}。発動率: {chance}%"


def _effect_summary_en(effect: Effect) -> str:
    target = TARGET_EN.get(effect.target, effect.target)
    parameter = PARAMETER_EN.get(effect.parameter, effect.parameter)
    value = f"{effect.value:g}"

    if effect.effect_type == "increase":
        body = f"increases {target}'s {parameter} by {value}"
    elif effect.effect_type == "decrease":
        body = f"reduces {target}'s {parameter} by {value}"
    elif effect.effect_type == "damage":
        body = f"deals {value} damage to {target}"
    elif effect.effect_type == "heal":
        body = f"restores {value} HP to {target}"
    elif effect.effect_type == "dot":
        body = f"deals {value} damage over time to {target}"
    elif effect.effect_type == "hot":
        body = f"restores {value} HP over time to {target}"
    elif effect.effect_type == "seal":
        body = f"seals {target}"
    elif effect.effect_type == "shield":
        body = f"grants a {value}-point shield to {target}"
    elif effect.effect_type == "sp_recover":
        body = f"restores {value} SP to {target}"
    elif effect.effect_type == "sp_damage":
        body = f"drains {value} SP from {target}"
    else:
        body = f"applies {effect.effect_type} to {target}"

    chance = int(round(effect.probability * 100))
    return f"{body}. Duration: {_duration_en(effect)}. Chance: {chance}%"


def generate_descriptions(
    concepts: list[Concept],
    trigger: str,
    effects: list[Effect],
    cost: Cost,
    cooldown: int,
) -> tuple[str, str]:
    concept = concepts[0] if concepts else Concept(label_ja="思想", label_en="Thought", category="")
    effect_text_ja = " ".join(_effect_summary_ja(effect) for effect in effects)
    effect_text_en = " ".join(_effect_summary_en(effect) for effect in effects)
    cost_ja = f"消費SP: {cost.sp}。" if cost.sp else "SP消費なし。"
    cost_en = f"SP cost: {cost.sp}." if cost.sp else "No SP cost."
    cooldown_ja = f"クールダウン: {cooldown}ターン。" if cooldown else "クールダウンなし。"
    cooldown_en = f"Cooldown: {cooldown} turn(s)." if cooldown else "No cooldown."

    description_ja = (
        f"「{concept.label_ja}」の概念から生成されたスキルです。"
        f"{TRIGGER_JA.get(trigger, trigger)}に発動し、{effect_text_ja} "
        f"{cost_ja} {cooldown_ja}"
    )
    description_en = (
        f"A skill shaped by the concept of {concept.label_en}. "
        f"It activates {TRIGGER_EN.get(trigger, trigger)} and {effect_text_en} "
        f"{cost_en} {cooldown_en}"
    )
    return description_ja, description_en
