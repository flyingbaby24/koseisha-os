using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public class ThoughtMapHateCalculator
{
    private readonly ThoughtMapBattleResonanceConfig config;
    private readonly bool debug;

    public ThoughtMapHateCalculator(ThoughtMapBattleResonanceConfig config = null, bool debug = false)
    {
        this.config = config == null ? ThoughtMapBattleResonanceConfig.RuntimeDefault : config;
        this.debug = debug;
    }

    public ThoughtMapBattleUnit SelectTarget(
        ThoughtMapBattleUnit attacker,
        List<ThoughtMapBattleUnit> enemies,
        int round,
        IList<string> log = null
    )
    {
        if (attacker == null || enemies == null)
        {
            return null;
        }

        ThoughtMapBattleUnit best = null;
        float bestScore = float.MinValue;
        foreach (ThoughtMapBattleUnit enemy in enemies.Where(unit => unit != null && unit.IsAlive))
        {
            ThoughtMapHateBreakdown breakdown = CalculateHateBreakdown(attacker, enemy, round);
            float score = breakdown.targetScore;
            if (ShouldLog(log))
            {
                log.Add(breakdown.ToDebugText(attacker, enemy));
            }

            if (score > bestScore)
            {
                best = enemy;
                bestScore = score;
            }
        }

        if (ShouldLog(log) && best != null)
        {
            log.Add($"Hate Select | {Describe(attacker)} -> {Describe(best)} score={bestScore:0.000}");
        }
        return best;
    }

    public float CalculateHate(ThoughtMapBattleUnit attacker, ThoughtMapBattleUnit target, int round)
    {
        return CalculateHateBreakdown(attacker, target, round).targetScore;
    }

    public ThoughtMapHateBreakdown CalculateHateBreakdown(ThoughtMapBattleUnit attacker, ThoughtMapBattleUnit target, int round)
    {
        ThoughtMapHateBreakdown breakdown = new ThoughtMapHateBreakdown();
        if (attacker == null || target == null || attacker.card == null || target.card == null)
        {
            return breakdown;
        }

        breakdown.columnWeight = GetColumnWeight(attacker.position, target.position);
        breakdown.depthWeight = GetDepthWeight(target.position, target.team);
        breakdown.resonanceDifference = Mathf.Abs(attacker.card.resonance - target.card.resonance);
        breakdown.resonanceWeight = config.GetHateMultiplierForDifference(breakdown.resonanceDifference);
        breakdown.skillModifier = Mathf.Max(0f, target.skillHateModifier);
        breakdown.randomModifier = GetDeterministicRandomModifier(attacker, target, round);
        breakdown.targetScore =
            breakdown.columnWeight *
            breakdown.depthWeight *
            breakdown.resonanceWeight *
            breakdown.skillModifier *
            breakdown.randomModifier;
        return breakdown;
    }

    private float GetColumnWeight(ThoughtMapGridPosition attackerPosition, ThoughtMapGridPosition targetPosition)
    {
        int columnDistance = Mathf.Abs(attackerPosition.x - targetPosition.x);
        if (columnDistance == 0)
        {
            return config.SameColumnWeight;
        }

        return columnDistance == 1 ? config.AdjacentColumnWeight : config.FarColumnWeight;
    }

    private float GetDepthWeight(ThoughtMapGridPosition targetPosition, string targetTeam)
    {
        bool player = targetTeam == "Player";
        int frontY = player ? 0 : 4;
        float distanceFromFront = Mathf.Abs(targetPosition.y - frontY) / 4f;
        return Mathf.Lerp(config.FrontDepthWeight, config.BackDepthWeight, Mathf.Clamp01(distanceFromFront));
    }

    private float GetDeterministicRandomModifier(ThoughtMapBattleUnit attacker, ThoughtMapBattleUnit target, int round)
    {
        int seed =
            (attacker.card.raritySeed * 31) +
            (attacker.card.skillSeed * 17) +
            (target.card.raritySeed * 13) +
            (target.card.skillSeed * 7) +
            (round * 19);
        float t = Mathf.Abs(seed % 1000) / 999f;
        return Mathf.Lerp(config.RandomModifierMin, config.RandomModifierMax, t);
    }

    private bool ShouldLog(IList<string> log)
    {
        return log != null && (debug || config.DebugLogging);
    }

    private string Describe(ThoughtMapBattleUnit unit)
    {
        if (unit == null || unit.card == null)
        {
            return "Unknown";
        }

        return $"{unit.team}:{unit.card.cardName}";
    }
}

public struct ThoughtMapHateBreakdown
{
    public float columnWeight;
    public float depthWeight;
    public float resonanceDifference;
    public float resonanceWeight;
    public float skillModifier;
    public float randomModifier;
    public float targetScore;

    public string ToDebugText(ThoughtMapBattleUnit attacker, ThoughtMapBattleUnit target)
    {
        string attackerName = attacker == null || attacker.card == null ? "Unknown" : attacker.card.cardName;
        string targetName = target == null || target.card == null ? "Unknown" : target.card.cardName;
        return
            $"Hate Candidate | {attackerName} -> {targetName} | " +
            $"ColumnWeight={columnWeight:0.00} DepthWeight={depthWeight:0.00} " +
            $"ResonanceWeight={resonanceWeight:0.00} diff={resonanceDifference:0.00} " +
            $"SkillModifier={skillModifier:0.00} RandomModifier={randomModifier:0.00} " +
            $"TargetScore={targetScore:0.000}";
    }
}
