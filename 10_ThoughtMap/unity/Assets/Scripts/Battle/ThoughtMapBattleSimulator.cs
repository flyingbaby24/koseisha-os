using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public class ThoughtMapBattleSimulator
{
    private readonly ThoughtMapHateCalculator hateCalculator = new ThoughtMapHateCalculator();
    private readonly IThoughtMapEmbeddingSimilarityProvider similarityProvider;

    public ThoughtMapBattleSimulator(IThoughtMapEmbeddingSimilarityProvider similarityProvider = null)
    {
        this.similarityProvider = similarityProvider ?? new ThoughtMapParameterSimilarityProvider();
    }

    public ThoughtMapBattleReport Simulate(
        List<ThoughtMapBattleUnit> playerUnits,
        List<ThoughtMapBattleUnit> enemyUnits,
        int maxRounds = 20
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

        for (int round = 1; round <= maxRounds; round++)
        {
            report.rounds = round;
            report.logLines.Add($"-- Round {round} --");

            List<ThoughtMapBattleUnit> turnOrder = playerUnits
                .Concat(enemyUnits)
                .Where(unit => unit.IsAlive)
                .OrderByDescending(unit => unit.card.statSpeed)
                .ThenByDescending(unit => unit.card.statLuck)
                .ToList();

            foreach (ThoughtMapBattleUnit unit in turnOrder)
            {
                if (!unit.IsAlive)
                {
                    continue;
                }

                List<ThoughtMapBattleUnit> enemies = unit.team == "Player" ? enemyUnits : playerUnits;
                if (!enemies.Any(enemy => enemy.IsAlive))
                {
                    break;
                }

                ThoughtMapBattleUnit target = hateCalculator.SelectTarget(unit, enemies, round);
                if (target == null)
                {
                    continue;
                }

                ResolveAttack(unit, target, unit.team == "Player" ? playerUnits : enemyUnits, report);
            }

            if (!playerUnits.Any(unit => unit.IsAlive) || !enemyUnits.Any(unit => unit.IsAlive))
            {
                break;
            }
        }

        bool playerAlive = playerUnits.Any(unit => unit.IsAlive);
        bool enemyAlive = enemyUnits.Any(unit => unit.IsAlive);
        report.winner = playerAlive == enemyAlive ? "Draw" : playerAlive ? "Player" : "Enemy";
        report.logLines.Add($"=== Winner: {report.winner} after {report.rounds} round(s) ===");
        return report;
    }

    private void ResolveAttack(
        ThoughtMapBattleUnit attacker,
        ThoughtMapBattleUnit target,
        List<ThoughtMapBattleUnit> allies,
        ThoughtMapBattleReport report
    )
    {
        bool useSkill = attacker.sp >= 20 && attacker.card.statSkillAttack >= attacker.card.statPhysicalAttack;
        int attack = useSkill ? attacker.card.statSkillAttack : attacker.card.statPhysicalAttack;
        int defense = useSkill ? target.card.statSkillDefense : target.card.statPhysicalDefense;

        float affinity = ThoughtMapAttributeAffinity.GetMultiplier(
            attacker.card.primaryAttribute,
            attacker.card.secondaryAttribute,
            target.card.primaryAttribute
        );
        ThoughtMapGridBonus attackerGrid = ThoughtMapGridBonusCalculator.GetBonus(attacker.position, attacker.team);
        ThoughtMapGridBonus targetGrid = ThoughtMapGridBonusCalculator.GetBonus(target.position, target.team);
        float adjacency = GetAdjacencyMultiplier(attacker, allies);
        float hitChance = Mathf.Clamp01(0.72f + ((attacker.card.statAccuracy - target.card.statEvasion) / 220f));
        float roll = ((attacker.card.raritySeed + target.card.skillSeed + report.rounds * 13) % 100) / 100f;

        if (roll > hitChance)
        {
            target.hate += 0.25f;
            report.logLines.Add($"{attacker.card.cardName} attacks {target.card.cardName}, but misses.");
            return;
        }

        float rawDamage = Mathf.Max(1f, attack - defense * 0.45f);
        int damage = Mathf.Max(1, Mathf.RoundToInt(rawDamage * affinity * attackerGrid.attackMultiplier * adjacency / targetGrid.defenseMultiplier));
        target.hp = Mathf.Max(0, target.hp - damage);
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
            $"{attacker.card.cardName} uses {method} on {target.card.cardName}: {damage} damage " +
            $"(affinity x{affinity:0.00}, grid x{attackerGrid.attackMultiplier:0.00}, adjacent x{adjacency:0.00}) " +
            $"HP {target.hp}/{target.card.MaxHp}"
        );

        if (!target.IsAlive)
        {
            report.logLines.Add($"{target.card.cardName} is defeated.");
        }
    }

    private float GetAdjacencyMultiplier(ThoughtMapBattleUnit attacker, List<ThoughtMapBattleUnit> allies)
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

        return 1f + Mathf.Clamp(bestSimilarity, 0f, 1f) * 0.12f;
    }

    private string DescribeTeam(List<ThoughtMapBattleUnit> units)
    {
        return string.Join(", ", units.Select(unit => $"{unit.card.cardName}@{unit.position}"));
    }
}
