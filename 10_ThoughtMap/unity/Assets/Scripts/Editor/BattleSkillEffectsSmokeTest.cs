using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class BattleSkillEffectsSmokeTest
{
    private const int Seed = 240719;

    [MenuItem("Tools/Source of Thought/Verify Battle Skill Effects Phase 1")]
    public static void Run()
    {
        List<string> unitLogs = VerifyStatusRules();
        BattlePhase1Result battle = VerifyFullBattle();
        string[] required = { "uses", "skill damage", "recovers", "Shield", "AttackBuff", "P.DEF", "DamageOverTime", "Taunt", "Stun", "Battle Finished" };
        string joined = string.Join("\n", unitLogs.Concat(battle.logLines));
        foreach (string token in required) Require(joined.IndexOf(token, StringComparison.OrdinalIgnoreCase) >= 0, "Missing log token: " + token);
        Require(battle.finished, "Battle did not finish.");
        Require(battle.playerUnits.Count == 5 && battle.enemyUnits.Count == 5, "Expected 5 vs 5.");
        Debug.Log($"[BattleSkillSmoke] PASS seed={Seed} units=5v5 turn={battle.turn} winner={(battle.playerWon ? "Player" : "Enemy")} active-effects-expired=true\n{joined}");
    }

    private static List<string> VerifyStatusRules()
    {
        List<string> log = new List<string>();
        ThoughtMapBattleUnit source = Unit("P1", "Player", 70, 32, 8, 7);
        ThoughtMapBattleUnit ally = Unit("P2", "Player", 45, 24, 7, 7); ally.hp = 30;
        ThoughtMapBattleUnit target = Unit("E1", "Enemy", 60, 26, 8, 8);
        ThoughtMapBattleUnit enemy2 = Unit("E2", "Enemy", 60, 25, 7, 7);
        List<ThoughtMapBattleUnit> allies = new List<ThoughtMapBattleUnit> { source, ally };
        List<ThoughtMapBattleUnit> enemies = new List<ThoughtMapBattleUnit> { target, enemy2 };
        BattleStatusEffectController statuses = new BattleStatusEffectController();
        BattleSkillResolver resolver = new BattleSkillResolver(statuses, new System.Random(Seed));

        resolver.Resolve(Skill("Direct Probe", "direct_damage", "single_enemy", "skill_attack", 12, 1), source, target, allies, enemies, 1, log.Add);
        int beforeHeal = ally.hp;
        resolver.Resolve(Skill("Recovery Probe", "heal", "lowest_hp_ally", "hp", 14, 1), source, target, allies, enemies, 1, log.Add);
        Require(ally.hp > beforeHeal && ally.hp <= ally.maxHp, "Heal clamp failed.");

        resolver.Resolve(Skill("Shield Probe", "shield", "single_ally", "hp", 20, 2), source, target, allies, enemies, 1, log.Add);
        int hpBeforeShield = ally.hp;
        int afterShield = statuses.AbsorbShield(ally, 15, log.Add);
        Require(afterShield == 0 && ally.hp == hpBeforeShield && statuses.Shield(ally) == 5, "Shield priority failed.");

        resolver.Resolve(Skill("Attack Probe", "attack_buff", "self", "physical_attack", 9, 2), source, target, allies, enemies, 1, log.Add);
        Require(statuses.EffectiveAttack(source, false) == source.physicalAttack + 9, "Attack buff failed.");
        resolver.Resolve(Skill("Mind Break", "defense_debuff", "single_enemy", "physical_defense", 12, 2), source, target, allies, enemies, 1, log.Add);
        Require(statuses.EffectiveDefense(target, false) == Mathf.Max(0, target.physicalDefense - 12), "Defense lower bound failed.");
        resolver.Resolve(Skill("Taunt Probe", "taunt", "self", "hate", 8, 2), target, source, enemies, allies, 1, log.Add);
        Require(target.skillHateModifier > target.preparedHateMultiplier, "Taunt modifier failed.");
        resolver.Resolve(Skill("Stun Probe", "stun", "single_enemy", "action", 1, 1), source, target, allies, enemies, 1, log.Add);
        Require(statuses.ConsumeStun(target) && !statuses.ConsumeStun(target), "Stun must skip exactly once.");

        target.hp = 4;
        resolver.Resolve(Skill("Burn Probe", "dot", "single_enemy", "hp", 8, 2), source, target, allies, enemies, 1, log.Add);
        resolver.ProcessTurnStart(target, allies.Concat(enemies), 2, log.Add);
        Require(!target.IsAlive, "DOT did not defeat target.");
        statuses.RemoveForDead(target);

        statuses.EndUnitTurn(source, 1, log.Add);
        statuses.EndUnitTurn(source, 2, log.Add);
        statuses.EndUnitTurn(source, 3, log.Add);
        Require(statuses.EffectiveAttack(source, false) == source.physicalAttack, "Expired buff remained active.");
        return log;
    }

    private static BattlePhase1Result VerifyFullBattle()
    {
        List<ThoughtMapBattleCardData> players = Enumerable.Range(1, 5).Select(i => Card("pc" + i, 34 + i, 26 + i)).ToList();
        List<ThoughtMapBattleCardData> enemies = Enumerable.Range(1, 5).Select(i => Card("ec" + i, 29 + i, 20 + i)).ToList();
        List<ThoughtMapBattlePreparedUnitData> prepared = players.Select((c, i) => new ThoughtMapBattlePreparedUnitData { cardId = c.cardId, x = i, y = 1, maxHp = 105, physicalAttack = c.statPhysicalAttack, skillAttack = c.statSkillAttack, physicalDefense = 9, skillDefense = 9, speed = 30 + i, hateMultiplier = 1f }).ToList();
        Dictionary<string, List<GeneratedSkillDto>> assigned = new Dictionary<string, List<GeneratedSkillDto>>
        {
            ["pc1"] = new List<GeneratedSkillDto> { Skill("Direct Damage", "direct_damage", "single_enemy", "skill_attack", 5, 1), Skill("Shield", "shield", "single_ally", "hp", 10, 2) },
            ["pc2"] = new List<GeneratedSkillDto> { Skill("Heal", "heal", "lowest_hp_ally", "hp", 8, 1), Skill("Attack Buff", "attack_buff", "self", "physical_attack", 5, 2) },
            ["pc3"] = new List<GeneratedSkillDto> { Skill("Defense Debuff", "defense_debuff", "single_enemy", "physical_defense", 5, 2), Skill("DOT", "dot", "single_enemy", "hp", 4, 2) },
            ["pc4"] = new List<GeneratedSkillDto> { Skill("Taunt", "taunt", "self", "hate", 5, 2) },
            ["pc5"] = new List<GeneratedSkillDto> { Skill("Stun", "stun", "single_enemy", "action", 1, 1) },
        };
        Dictionary<string, List<GeneratedSkillDto>> enemyAssigned = new Dictionary<string, List<GeneratedSkillDto>>
        {
            ["ec1"] = new List<GeneratedSkillDto> { Skill("Enemy Direct Damage", "direct_damage", "single_enemy", "skill_attack", 3, 1), Skill("Enemy Shield", "shield", "single_ally", "hp", 6, 2) },
            ["ec2"] = new List<GeneratedSkillDto> { Skill("Enemy Heal", "heal", "lowest_hp_ally", "hp", 4, 1), Skill("Enemy Attack Buff", "attack_buff", "self", "physical_attack", 3, 2) },
            ["ec3"] = new List<GeneratedSkillDto> { Skill("Enemy Defense Debuff", "defense_debuff", "single_enemy", "physical_defense", 3, 2), Skill("Enemy DOT", "dot", "single_enemy", "hp", 3, 2) },
            ["ec4"] = new List<GeneratedSkillDto> { Skill("Enemy Taunt", "taunt", "self", "hate", 3, 2) },
            ["ec5"] = new List<GeneratedSkillDto> { Skill("Enemy Stun", "stun", "single_enemy", "action", 1, 1) },
        };
        return new BattleController(null, Seed).Run(players, enemies, null, null, null, prepared, assigned, enemyAssigned);
    }

    private static GeneratedSkillDto Skill(string name, string type, string target, string parameter, float value, int duration)
    {
        GeneratedSkillDto dto = new GeneratedSkillDto { skill_id = "smoke_" + name.Replace(" ", "_").ToLowerInvariant(), name_en = name, trigger = "turn_start", cost = new GeneratedSkillCostDto { consume_action = false } };
        dto.effects.Add(new GeneratedSkillEffectDto { effect_order = 1, effect_type = type, target = target, parameter = parameter, operation = type.Contains("damage") || type == "dot" ? "damage" : "add", value = value, value_type = "flat", duration = duration, probability = 1f });
        return dto;
    }

    private static ThoughtMapBattleUnit Unit(string id, string team, int hp, int attack, int defense, int speed)
    {
        ThoughtMapBattleUnit unit = new ThoughtMapBattleUnit(Card(id, attack, attack - 2), team, new ThoughtMapGridPosition(2, team == "Player" ? 1 : 3)) { battleId = id, maxHp = hp, hp = hp, physicalDefense = defense, skillDefense = defense, speed = speed, preparedHateMultiplier = 1f, skillHateModifier = 1f };
        return unit;
    }

    private static ThoughtMapBattleCardData Card(string id, int attack, int skillAttack) => new ThoughtMapBattleCardData { cardId = id, docId = id, cardName = id, statHp = 25, statPhysicalAttack = attack, statSkillAttack = skillAttack, statPhysicalDefense = 9, statSkillDefense = 9, statSpeed = 20, resonance = .5f, raritySeed = id.GetHashCode(), skillSeed = id.GetHashCode() / 3 };
    private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException("[BattleSkillSmoke] " + message); }
}
