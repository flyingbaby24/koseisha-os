using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public enum BattleSkillEffectType { Unsupported, DirectDamage, Heal, Shield, AttackBuff, DefenseDebuff, DamageOverTime, Taunt, Stun }
public enum BattleSkillTargetType { Self, SingleAlly, LowestHpAlly, SingleEnemy, HighestHateEnemy, AllEnemies }
public enum BattleStatusTick { TurnStart, TurnEnd }

[Serializable]
public sealed class BattleSkillEffect
{
    public BattleSkillEffectType effectType;
    public BattleSkillTargetType target;
    public string parameter;
    public float value;
    public bool percent;
    public int duration;
    public float probability = 1f;

    public static BattleSkillEffect FromDto(GeneratedSkillEffectDto dto)
    {
        return new BattleSkillEffect
        {
            effectType = ParseEffect(dto == null ? null : dto.effect_type, dto == null ? null : dto.operation),
            target = ParseTarget(dto == null ? null : dto.target),
            parameter = dto == null ? string.Empty : (dto.parameter ?? string.Empty).Trim().ToLowerInvariant(),
            value = dto == null ? 0f : dto.value,
            percent = dto != null && string.Equals(dto.value_type, "percent", StringComparison.OrdinalIgnoreCase),
            duration = Mathf.Max(1, dto == null ? 1 : dto.duration),
            probability = dto == null || dto.probability <= 0f ? 1f : Mathf.Clamp01(dto.probability),
        };
    }

    private static BattleSkillEffectType ParseEffect(string type, string operation)
    {
        string key = (type ?? string.Empty).Trim().ToLowerInvariant();
        string op = (operation ?? string.Empty).Trim().ToLowerInvariant();
        if (key is "direct_damage" or "damage" or "skill_damage") return BattleSkillEffectType.DirectDamage;
        if (key == "heal") return BattleSkillEffectType.Heal;
        if (key == "shield") return BattleSkillEffectType.Shield;
        if (key is "attack_buff" or "buff" || key == "increase" && op != "recover") return BattleSkillEffectType.AttackBuff;
        if (key is "defense_debuff" or "debuff" or "seal" || key == "decrease") return BattleSkillEffectType.DefenseDebuff;
        if (key is "dot" or "burn" or "poison") return BattleSkillEffectType.DamageOverTime;
        if (key == "taunt") return BattleSkillEffectType.Taunt;
        if (key == "stun") return BattleSkillEffectType.Stun;
        return BattleSkillEffectType.Unsupported;
    }

    private static BattleSkillTargetType ParseTarget(string value)
    {
        return (value ?? string.Empty).Trim().ToLowerInvariant() switch
        {
            "self" => BattleSkillTargetType.Self,
            "single_ally" or "random_ally" => BattleSkillTargetType.SingleAlly,
            "all_allies" => BattleSkillTargetType.SingleAlly,
            "lowest_hp_ally" => BattleSkillTargetType.LowestHpAlly,
            "all_enemies" => BattleSkillTargetType.AllEnemies,
            "highest_hate_enemy" => BattleSkillTargetType.HighestHateEnemy,
            _ => BattleSkillTargetType.SingleEnemy,
        };
    }
}

[Serializable]
public sealed class BattleSkillDefinition
{
    public string skillId;
    public string displayName;
    public string trigger;
    public bool consumesAction;
    public List<BattleSkillEffect> effects = new List<BattleSkillEffect>();

    public static BattleSkillDefinition FromDto(GeneratedSkillDto dto)
    {
        if (dto == null) return null;
        return new BattleSkillDefinition
        {
            skillId = dto.skill_id ?? string.Empty,
            displayName = dto.DisplayName,
            trigger = (dto.trigger ?? string.Empty).Trim().ToLowerInvariant(),
            consumesAction = dto.cost == null || dto.cost.consume_action,
            effects = (dto.effects ?? new List<GeneratedSkillEffectDto>()).OrderBy(e => e.effect_order).Select(BattleSkillEffect.FromDto).ToList(),
        };
    }
}

[Serializable]
public sealed class ActiveStatusEffect
{
    public BattleSkillEffectType effectType;
    public string sourceUnitId;
    public string targetUnitId;
    public string parameter;
    public float value;
    public int remainingTurns;
    public int stackCount = 1;
    public int appliedTurn;
    public BattleStatusTick tick = BattleStatusTick.TurnStart;
}

public sealed class BattleStatusEffectController
{
    private readonly List<ActiveStatusEffect> active = new List<ActiveStatusEffect>();
    public event Action<string> Changed;
    public IReadOnlyList<ActiveStatusEffect> ActiveEffects => active;

    public void Add(ActiveStatusEffect effect)
    {
        if (effect == null) return;
        ActiveStatusEffect existing = active.FirstOrDefault(x => x.effectType == effect.effectType && x.sourceUnitId == effect.sourceUnitId && x.targetUnitId == effect.targetUnitId && x.parameter == effect.parameter);
        if (existing == null) { active.Add(effect); Changed?.Invoke(effect.targetUnitId); return; }
        existing.stackCount = Mathf.Min(3, existing.stackCount + 1);
        existing.value = Mathf.Max(existing.value, effect.value);
        existing.remainingTurns = Mathf.Max(existing.remainingTurns, effect.remainingTurns);
        existing.appliedTurn = effect.appliedTurn;
        Changed?.Invoke(effect.targetUnitId);
    }
    public void Remove(ActiveStatusEffect effect) { if (effect != null && active.Remove(effect)) Changed?.Invoke(effect.targetUnitId); }

    public IEnumerable<ActiveStatusEffect> For(ThoughtMapBattleUnit unit) => unit == null ? Enumerable.Empty<ActiveStatusEffect>() : active.Where(x => x.targetUnitId == unit.battleId);
    public int Shield(ThoughtMapBattleUnit unit) => Mathf.RoundToInt(For(unit).Where(x => x.effectType == BattleSkillEffectType.Shield).Sum(x => x.value * x.stackCount));
    public int EffectiveAttack(ThoughtMapBattleUnit unit, bool magic)
    {
        int baseValue = magic ? unit.skillAttack : unit.physicalAttack;
        string stat = magic ? "skill_attack" : "physical_attack";
        float bonus = For(unit).Where(x => x.effectType == BattleSkillEffectType.AttackBuff && Matches(x.parameter, stat)).Sum(x => x.value * x.stackCount);
        return Mathf.Max(0, baseValue + Mathf.RoundToInt(bonus));
    }
    public int EffectiveDefense(ThoughtMapBattleUnit unit, bool magic)
    {
        int baseValue = magic ? unit.skillDefense : unit.physicalDefense;
        string stat = magic ? "skill_defense" : "physical_defense";
        float penalty = For(unit).Where(x => x.effectType == BattleSkillEffectType.DefenseDebuff && Matches(x.parameter, stat)).Sum(x => x.value * x.stackCount);
        return Mathf.Max(0, baseValue - Mathf.RoundToInt(penalty));
    }
    public float TauntMultiplier(ThoughtMapBattleUnit unit) => 1f + For(unit).Where(x => x.effectType == BattleSkillEffectType.Taunt).Sum(x => Mathf.Max(0f, x.value) * x.stackCount);

    public int AbsorbShield(ThoughtMapBattleUnit target, int incoming, Action<string> log)
    {
        int remaining = Mathf.Max(0, incoming);
        foreach (ActiveStatusEffect shield in For(target).Where(x => x.effectType == BattleSkillEffectType.Shield).ToList())
        {
            if (remaining <= 0) break;
            int available = Mathf.Max(0, Mathf.RoundToInt(shield.value * shield.stackCount));
            int absorbed = Mathf.Min(available, remaining);
            remaining -= absorbed;
            float perStack = shield.stackCount <= 0 ? 0f : absorbed / (float)shield.stackCount;
            shield.value = Mathf.Max(0f, shield.value - perStack);
            int left = Shield(target);
            log?.Invoke($"{target.battleId} Shield absorbs {absorbed}, remaining {left}");
            if (shield.value <= .01f) active.Remove(shield);
            Changed?.Invoke(target.battleId);
        }
        return remaining;
    }

    public bool ConsumeStun(ThoughtMapBattleUnit unit)
    {
        ActiveStatusEffect stun = For(unit).FirstOrDefault(x => x.effectType == BattleSkillEffectType.Stun);
        if (stun == null) return false;
        active.Remove(stun);
        Changed?.Invoke(unit.battleId);
        return true;
    }

    public void RemoveForDead(ThoughtMapBattleUnit unit)
    {
        if (unit != null && !unit.IsAlive && active.RemoveAll(x => x.targetUnitId == unit.battleId) > 0) Changed?.Invoke(unit.battleId);
    }

    public void EndUnitTurn(ThoughtMapBattleUnit unit, int turn, Action<string> log)
    {
        bool changed = false;
        foreach (ActiveStatusEffect effect in For(unit).ToList())
        {
            if (effect.effectType is BattleSkillEffectType.DamageOverTime or BattleSkillEffectType.Stun) continue;
            if (effect.appliedTurn == turn) continue;
            effect.remainingTurns--;
            changed = true;
            if (effect.remainingTurns > 0) continue;
            active.Remove(effect);
            string name = effect.effectType == BattleSkillEffectType.Taunt ? "Taunt" : effect.effectType.ToString();
            log?.Invoke($"{unit.battleId} {name} expired");
        }
        unit.skillHateModifier = unit.preparedHateMultiplier * TauntMultiplier(unit);
        if (changed) Changed?.Invoke(unit.battleId);
    }

    public void Notify(string unitId) { if (!string.IsNullOrWhiteSpace(unitId)) Changed?.Invoke(unitId); }

    private static bool Matches(string parameter, string stat)
    {
        if (string.IsNullOrWhiteSpace(parameter) || parameter == "attack" || parameter == "defense" || parameter == stat) return true;
        bool explicitCombatStat = parameter is "physical_attack" or "skill_attack" or "physical_defense" or "skill_defense";
        return !explicitCombatStat;
    }
}

public sealed class BattleSkillResolution
{
    public bool used;
    public bool supported = true;
    public string skillName;
    public readonly List<BattlePhase1Event> events = new List<BattlePhase1Event>();
}

public sealed class BattleSkillResolver
{
    private readonly BattleStatusEffectController statuses;
    private readonly System.Random random;
    public BattleSkillResolver(BattleStatusEffectController statuses, System.Random random) { this.statuses = statuses; this.random = random; }

    public BattleSkillResolution Resolve(GeneratedSkillDto dto, ThoughtMapBattleUnit source, ThoughtMapBattleUnit preferredTarget, IList<ThoughtMapBattleUnit> allies, IList<ThoughtMapBattleUnit> enemies, int turn, Action<string> log)
    {
        BattleSkillDefinition skill = BattleSkillDefinition.FromDto(dto);
        BattleSkillResolution result = new BattleSkillResolution { used = skill != null, skillName = skill == null ? string.Empty : skill.displayName };
        if (skill == null) return result;
        log?.Invoke($"{source.battleId} uses {skill.displayName}");
        if (skill.effects.Count == 0 || skill.effects.Any(effect => effect.effectType == BattleSkillEffectType.Unsupported))
        {
            result.supported = false;
            log?.Invoke($"{source.battleId} unsupported Skill effect in {skill.displayName}; fallback to normal attack");
            return result;
        }
        foreach (BattleSkillEffect effect in skill.effects)
        {
            if (random.NextDouble() > effect.probability) continue;
            foreach (ThoughtMapBattleUnit target in SelectTargets(effect.target, source, preferredTarget, allies, enemies).Where(x => x != null && x.IsAlive))
                Apply(effect, source, target, turn, result, log);
        }
        return result;
    }

    private void Apply(BattleSkillEffect effect, ThoughtMapBattleUnit source, ThoughtMapBattleUnit target, int turn, BattleSkillResolution result, Action<string> log)
    {
        int value = Mathf.Max(1, Mathf.RoundToInt(effect.value));
        switch (effect.effectType)
        {
            case BattleSkillEffectType.DirectDamage:
                bool magic = effect.parameter != "physical_attack";
                int attack = statuses.EffectiveAttack(source, magic);
                int defense = statuses.EffectiveDefense(target, magic);
                float multiplier = effect.value > 1f ? effect.value / 100f : effect.value;
                int raw = effect.percent ? Mathf.RoundToInt(attack * multiplier) : attack + value;
                int damage = statuses.AbsorbShield(target, Mathf.Max(1, raw - defense), log);
                target.hp = Mathf.Max(0, target.hp - damage); source.damageDone += damage; target.damageTaken += damage;
                log?.Invoke($"{target.battleId} takes {damage} skill damage");
                result.events.Add(Event(BattlePresentationPhase.DamageApplied, source, target, damage, turn, effect.effectType));
                break;
            case BattleSkillEffectType.Heal:
                int healed = Mathf.Min(value, target.maxHp - target.hp); target.hp += healed;
                log?.Invoke($"{target.battleId} recovers {healed} HP");
                result.events.Add(Event(BattlePresentationPhase.SkillEffectApplied, source, target, healed, turn, effect.effectType));
                break;
            case BattleSkillEffectType.Shield:
                AddStatus(effect, source, target, turn); log?.Invoke($"{target.battleId} gains Shield {value} for {effect.duration} turns");
                result.events.Add(Event(BattlePresentationPhase.SkillEffectApplied, source, target, value, turn, effect.effectType));
                break;
            case BattleSkillEffectType.AttackBuff:
            case BattleSkillEffectType.DefenseDebuff:
            case BattleSkillEffectType.DamageOverTime:
            case BattleSkillEffectType.Taunt:
            case BattleSkillEffectType.Stun:
                AddStatus(effect, source, target, turn);
                string label = effect.effectType == BattleSkillEffectType.DefenseDebuff ? $"{NormalizeParameter(effect.parameter)} -{value}" : effect.effectType.ToString();
                log?.Invoke($"{target.battleId} {label} for {effect.duration} turns");
                result.events.Add(Event(BattlePresentationPhase.SkillEffectApplied, source, target, value, turn, effect.effectType));
                break;
        }
    }

    public List<BattlePhase1Event> ProcessTurnStart(ThoughtMapBattleUnit unit, IEnumerable<ThoughtMapBattleUnit> allUnits, int turn, Action<string> log)
    {
        List<BattlePhase1Event> events = new List<BattlePhase1Event>();
        foreach (ActiveStatusEffect dot in statuses.For(unit).Where(x => x.effectType == BattleSkillEffectType.DamageOverTime).ToList())
        {
            if (!unit.IsAlive) break;
            int damage = statuses.AbsorbShield(unit, Mathf.Max(1, Mathf.RoundToInt(dot.value * dot.stackCount)), log);
            ThoughtMapBattleUnit source = allUnits.FirstOrDefault(x => x.battleId == dot.sourceUnitId);
            unit.hp = Mathf.Max(0, unit.hp - damage); unit.damageTaken += damage; if (source != null) source.damageDone += damage;
            dot.remainingTurns--;
            statuses.Notify(unit.battleId);
            log?.Invoke($"{unit.battleId} DOT deals {damage} damage ({Mathf.Max(0, dot.remainingTurns)} turns remaining)");
            events.Add(Event(BattlePresentationPhase.DamageApplied, source, unit, damage, turn, BattleSkillEffectType.DamageOverTime));
            if (dot.remainingTurns <= 0)
            {
                statuses.Remove(dot);
                log?.Invoke($"{unit.battleId} DamageOverTime expired");
            }
        }
        return events;
    }

    private void AddStatus(BattleSkillEffect effect, ThoughtMapBattleUnit source, ThoughtMapBattleUnit target, int turn)
    {
        statuses.Add(new ActiveStatusEffect { effectType = effect.effectType, sourceUnitId = source.battleId, targetUnitId = target.battleId, parameter = effect.parameter, value = Mathf.Max(1f, effect.value), remainingTurns = effect.duration, appliedTurn = turn });
        if (effect.effectType == BattleSkillEffectType.Taunt) target.skillHateModifier = target.preparedHateMultiplier * statuses.TauntMultiplier(target);
    }

    private IEnumerable<ThoughtMapBattleUnit> SelectTargets(BattleSkillTargetType targetType, ThoughtMapBattleUnit source, ThoughtMapBattleUnit preferred, IList<ThoughtMapBattleUnit> allies, IList<ThoughtMapBattleUnit> enemies)
    {
        List<ThoughtMapBattleUnit> livingAllies = allies.Where(x => x != null && x.IsAlive).ToList();
        List<ThoughtMapBattleUnit> livingEnemies = enemies.Where(x => x != null && x.IsAlive).ToList();
        return targetType switch
        {
            BattleSkillTargetType.Self => new[] { source },
            BattleSkillTargetType.SingleAlly => new[] { livingAllies.FirstOrDefault(x => x != source) ?? source },
            BattleSkillTargetType.LowestHpAlly => new[] { livingAllies.OrderBy(x => x.hp / (float)x.maxHp).FirstOrDefault() },
            BattleSkillTargetType.AllEnemies => livingEnemies,
            BattleSkillTargetType.HighestHateEnemy => new[] { livingEnemies.OrderByDescending(x => x.hate).FirstOrDefault() },
            _ => new[] { preferred != null && preferred.IsAlive ? preferred : livingEnemies.FirstOrDefault() },
        };
    }

    private static BattlePhase1Event Event(BattlePresentationPhase phase, ThoughtMapBattleUnit source, ThoughtMapBattleUnit target, int amount, int turn, BattleSkillEffectType effect) => new BattlePhase1Event { phase = phase, turn = turn, attacker = source, target = target, damage = amount, remainingHp = target == null ? 0 : target.hp, maxHp = target == null ? 0 : target.maxHp, defeated = target != null && !target.IsAlive, skillEffectType = effect };
    private static string NormalizeParameter(string value) => string.IsNullOrWhiteSpace(value) ? "DEF" : value.ToUpperInvariant().Replace("PHYSICAL_", "P.").Replace("SKILL_", "S.");
}
