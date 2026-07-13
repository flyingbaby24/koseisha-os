using System.Collections.Generic;
using System.Linq;
using System;
using UnityEngine;

public class ThoughtMapBattleSimulator
{
    private readonly ThoughtMapHateCalculator hateCalculator;
    private readonly ThoughtMapBattleResonanceCalculator resonanceCalculator;
    private readonly ThoughtMapBattleResonanceConfig resonanceConfig;
    private readonly IThoughtMapEmbeddingSimilarityProvider similarityProvider;
    private readonly bool debugResonanceAndHate;

    public ThoughtMapBattleSimulator(
        IThoughtMapEmbeddingSimilarityProvider similarityProvider = null,
        ThoughtMapBattleResonanceConfig resonanceConfig = null,
        bool debugResonanceAndHate = false
    )
    {
        this.similarityProvider = similarityProvider ?? new ThoughtMapParameterSimilarityProvider();
        this.resonanceConfig = resonanceConfig == null ? ThoughtMapBattleResonanceConfig.RuntimeDefault : resonanceConfig;
        this.debugResonanceAndHate = debugResonanceAndHate;
        this.resonanceCalculator = new ThoughtMapBattleResonanceCalculator(this.resonanceConfig);
        this.hateCalculator = new ThoughtMapHateCalculator(this.resonanceConfig, debugResonanceAndHate);
    }

    public ThoughtMapBattleReport Simulate(
        List<ThoughtMapBattleUnit> playerUnits,
        List<ThoughtMapBattleUnit> enemyUnits,
        int maxRounds = 20,
        Action<int> onRoundStart = null
    )
    {
        ThoughtMapBattleReport report = new ThoughtMapBattleReport();
        if (playerUnits == null || enemyUnits == null || playerUnits.Count == 0 || enemyUnits.Count == 0)
        {
            report.logLines.Add("Battle aborted: both sides need deployed cards.");
            return report;
        }

        report.logLines.Add("=== Source of Thought Battle MVP ===");
        report.logLines.Add($"Player: {DescribeTeam(playerUnits)}");
        report.logLines.Add($"Enemy : {DescribeTeam(enemyUnits)}");
        LogInitialPositionBonuses(playerUnits, report);
        LogInitialPositionBonuses(enemyUnits, report);
        LogInitialResonance(playerUnits, report);
        LogInitialResonance(enemyUnits, report);

        for (int round = 1; round <= maxRounds; round++)
        {
            report.rounds = round;
            onRoundStart?.Invoke(round);
            report.logLines.Add($"-- Round {round} --");

            List<ThoughtMapBattleUnit> turnOrder = playerUnits
                .Concat(enemyUnits)
                .Where(unit => unit.IsAlive)
                .OrderByDescending(unit => GetFinalStat(unit, GetAllies(unit, playerUnits, enemyUnits), unit.card.statSpeed))
                .ThenByDescending(unit => GetFinalStat(unit, GetAllies(unit, playerUnits, enemyUnits), unit.card.statLuck))
                .ToList();

            foreach (ThoughtMapBattleUnit unit in turnOrder)
            {
                if (!unit.IsAlive)
                {
                    continue;
                }

                List<ThoughtMapBattleUnit> allies = unit.team == "Player" ? playerUnits : enemyUnits;
                List<ThoughtMapBattleUnit> enemies = unit.team == "Player" ? enemyUnits : playerUnits;
                if (!enemies.Any(enemy => enemy.IsAlive))
                {
                    break;
                }

                ThoughtMapBattleUnit target = hateCalculator.SelectTarget(unit, enemies, round, report.logLines);
                if (target == null)
                {
                    continue;
                }

                string targetKey = GetUnitKey(target);
                if (!string.IsNullOrEmpty(unit.lastTargetKey) && unit.lastTargetKey != targetKey)
                {
                    report.logLines.Add(
                        $"Turn {round}: Target Changed | {DescribeUnit(unit)} -> {DescribeUnit(target)}"
                    );
                }
                unit.lastTargetKey = targetKey;

                ResolveAttack(unit, target, allies, enemies, report, round);
            }

            if (!playerUnits.Any(unit => unit.IsAlive) || !enemyUnits.Any(unit => unit.IsAlive))
            {
                break;
            }
        }

        bool playerAlive = playerUnits.Any(unit => unit.IsAlive);
        bool enemyAlive = enemyUnits.Any(unit => unit.IsAlive);
        report.winner = playerAlive == enemyAlive ? "Draw" : playerAlive ? "Player" : "Enemy";
        FillSummary(report, playerUnits, enemyUnits);
        report.logLines.Add($"=== Winner: {report.winner} after {report.rounds} round(s) ===");
        report.logLines.Add(report.ToSummaryText());
        return report;
    }

    private void ResolveAttack(
        ThoughtMapBattleUnit attacker,
        ThoughtMapBattleUnit target,
        List<ThoughtMapBattleUnit> allies,
        List<ThoughtMapBattleUnit> targetAllies,
        ThoughtMapBattleReport report,
        int round
    )
    {
        bool useSkill = attacker.sp >= 20 && attacker.card.statSkillAttack >= attacker.card.statPhysicalAttack;
        ThoughtMapResonanceResult attackerResonance = resonanceCalculator.CalculateTotalModifier(attacker, allies);
        ThoughtMapResonanceResult targetResonance = resonanceCalculator.CalculateTotalModifier(target, targetAllies);
        int attack = useSkill
            ? GetFinalStat(attacker, allies, attacker.card.statSkillAttack)
            : GetFinalStat(attacker, allies, attacker.card.statPhysicalAttack);
        int defense = useSkill
            ? GetFinalStat(target, targetAllies, target.card.statSkillDefense)
            : GetFinalStat(target, targetAllies, target.card.statPhysicalDefense);

        float affinity = ThoughtMapAttributeAffinity.GetMultiplier(
            attacker.card.primaryAttribute,
            attacker.card.secondaryAttribute,
            target.card.primaryAttribute
        );
        ThoughtMapGridBonus attackerGrid = ThoughtMapGridBonusCalculator.GetBonus(attacker.position, attacker.team);
        ThoughtMapGridBonus targetGrid = ThoughtMapGridBonusCalculator.GetBonus(target.position, target.team);
        ThoughtMapSupportBonus support = GetSupportBonus(attacker, allies);
        int accuracy = GetFinalStat(attacker, allies, attacker.card.statAccuracy);
        int evasion = GetFinalStat(target, targetAllies, target.card.statEvasion);
        float hitChance = Mathf.Clamp01(0.72f + ((accuracy - evasion) / 220f));
        float roll = ((attacker.card.raritySeed + target.card.skillSeed + report.rounds * 13) % 100) / 100f;

        if (roll > hitChance)
        {
            target.hate += 0.25f;
            report.events.Add(new ThoughtMapBattleEvent
            {
                round = round,
                attackerId = attacker.battleId,
                attackerTeam = attacker.team,
                targetId = target.battleId,
                targetTeam = target.team,
                damage = 0,
                targetHp = target.hp,
                targetMaxHp = target.maxHp,
                miss = true,
                defeated = false,
                method = useSkill ? "skill" : "attack",
            });
            report.logLines.Add(
                $"Turn {round}: {DescribeUnit(attacker)} -> {DescribeUnit(target)} | miss | " +
                $"Resonance ATK {FormatPercent(1f + attackerResonance.totalModifier)} DEF {FormatPercent(1f + targetResonance.totalModifier)}"
            );
            return;
        }

        float rawDamage = Mathf.Max(1f, attack - defense * 0.45f);
        int damage = Mathf.Max(1, Mathf.RoundToInt(rawDamage * affinity * attackerGrid.attackMultiplier * support.multiplier / targetGrid.defenseMultiplier));
        target.hp = Mathf.Max(0, target.hp - damage);
        attacker.damageDone += damage;
        target.damageTaken += damage;
        target.hate += damage / 30f;
        attacker.hate += 0.15f;
        if (useSkill)
        {
            attacker.sp = Mathf.Max(0, attacker.sp - 20);
        }
        else
        {
            attacker.sp = Mathf.Min(attacker.card.MaxSp, attacker.sp + 8);
        }

        string method = useSkill ? "skill" : "attack";
        report.logLines.Add(
            $"Turn {round}: {DescribeUnit(attacker)} -> {DescribeUnit(target)} | {method} | " +
            $"damage {damage} | HP {target.hp}/{target.maxHp} " +
            $"| {DescribeAffinity(affinity)} x{affinity:0.00} | " +
            $"Position Bonus ATK {FormatPercent(attackerGrid.attackMultiplier)} DEF {FormatPercent(targetGrid.defenseMultiplier)} HP {FormatPercent(attackerGrid.hpMultiplier)} | " +
            $"Resonance ATK {FormatPercent(1f + attackerResonance.totalModifier)} DEF {FormatPercent(1f + targetResonance.totalModifier)} | " +
            $"Support Bonus {FormatPercent(support.multiplier)} Similarity {support.similarity:0.00}"
        );

        if (!target.IsAlive)
        {
            report.logLines.Add($"Turn {round}: defeated | {DescribeUnit(target)}");
        }

        report.events.Add(new ThoughtMapBattleEvent
        {
            round = round,
            attackerId = attacker.battleId,
            attackerTeam = attacker.team,
            targetId = target.battleId,
            targetTeam = target.team,
            damage = damage,
            targetHp = target.hp,
            targetMaxHp = target.maxHp,
            miss = false,
            defeated = !target.IsAlive,
            method = method,
        });
    }

    private ThoughtMapSupportBonus GetSupportBonus(ThoughtMapBattleUnit attacker, List<ThoughtMapBattleUnit> allies)
    {
        float bestSimilarity = 0f;
        foreach (ThoughtMapBattleUnit ally in allies)
        {
            if (ally == attacker || ally == null || !ally.IsAlive)
            {
                continue;
            }

            if (attacker.position.ManhattanDistance(ally.position) == 1)
            {
                bestSimilarity = Mathf.Max(bestSimilarity, similarityProvider.GetSimilarity(attacker.card, ally.card));
            }
        }

        return new ThoughtMapSupportBonus(bestSimilarity, 1f + Mathf.Clamp(bestSimilarity, 0f, 1f) * 0.12f);
    }

    private string DescribeTeam(List<ThoughtMapBattleUnit> units)
    {
        return string.Join(", ", units.Select(unit => $"{unit.card.cardName}@{unit.position}"));
    }

    private List<ThoughtMapBattleUnit> GetAllies(
        ThoughtMapBattleUnit unit,
        List<ThoughtMapBattleUnit> playerUnits,
        List<ThoughtMapBattleUnit> enemyUnits
    )
    {
        return unit != null && unit.team == "Player" ? playerUnits : enemyUnits;
    }

    private int GetFinalStat(ThoughtMapBattleUnit unit, List<ThoughtMapBattleUnit> allies, int baseValue)
    {
        ThoughtMapResonanceResult resonance = resonanceCalculator.CalculateTotalModifier(unit, allies);
        return Mathf.Max(1, Mathf.RoundToInt(baseValue * (1f + resonance.totalModifier)));
    }

    private string DescribeUnit(ThoughtMapBattleUnit unit)
    {
        if (unit == null || unit.card == null)
        {
            return "Unknown";
        }

        return $"{unit.team}:{unit.card.cardName}";
    }

    private void LogInitialPositionBonuses(List<ThoughtMapBattleUnit> units, ThoughtMapBattleReport report)
    {
        foreach (ThoughtMapBattleUnit unit in units)
        {
            ThoughtMapGridBonus bonus = ThoughtMapGridBonusCalculator.GetBonus(unit.position, unit.team);
            report.logLines.Add(
                $"Position Bonus | {DescribeUnit(unit)} @{unit.position} | " +
                $"ATK {FormatPercent(bonus.attackMultiplier)} DEF {FormatPercent(bonus.defenseMultiplier)} " +
                $"HP {FormatPercent(bonus.hpMultiplier)} Hate {FormatPercent(bonus.hateMultiplier)}"
            );
        }
    }

    private void LogInitialResonance(List<ThoughtMapBattleUnit> units, ThoughtMapBattleReport report)
    {
        if (!debugResonanceAndHate && !resonanceConfig.DebugLogging)
        {
            return;
        }

        foreach (ThoughtMapBattleUnit unit in units)
        {
            ThoughtMapResonanceResult result = resonanceCalculator.CalculateTotalModifier(unit, units);
            report.logLines.Add("Resonance | " + result.ToDebugText());
        }
    }

    private void FillSummary(
        ThoughtMapBattleReport report,
        List<ThoughtMapBattleUnit> playerUnits,
        List<ThoughtMapBattleUnit> enemyUnits
    )
    {
        report.playerDamageDone = playerUnits.Sum(unit => unit.damageDone);
        report.enemyDamageDone = enemyUnits.Sum(unit => unit.damageDone);
        report.playerDamageTaken = playerUnits.Sum(unit => unit.damageTaken);
        report.enemyDamageTaken = enemyUnits.Sum(unit => unit.damageTaken);
        report.playerCardsSurvived = playerUnits.Count(unit => unit.IsAlive);
        report.enemyCardsSurvived = enemyUnits.Count(unit => unit.IsAlive);
        report.playerCardsLost = playerUnits.Count(unit => !unit.IsAlive);
        report.enemyCardsLost = enemyUnits.Count(unit => !unit.IsAlive);
    }

    private string DescribeAffinity(float affinity)
    {
        if (affinity >= 1.05f)
        {
            return "Effective";
        }

        if (affinity <= 0.95f)
        {
            return "Resist";
        }

        return "Neutral";
    }

    private string FormatPercent(float multiplier)
    {
        float percent = (multiplier - 1f) * 100f;
        return percent >= 0f ? $"+{percent:0}%" : $"{percent:0}%";
    }

    private string GetUnitKey(ThoughtMapBattleUnit unit)
    {
        if (unit == null || unit.card == null)
        {
            return "";
        }

        return $"{unit.team}:{unit.card.cardId}:{unit.position}";
    }

    private struct ThoughtMapSupportBonus
    {
        public readonly float similarity;
        public readonly float multiplier;

        public ThoughtMapSupportBonus(float similarity, float multiplier)
        {
            this.similarity = similarity;
            this.multiplier = multiplier;
        }
    }
}
