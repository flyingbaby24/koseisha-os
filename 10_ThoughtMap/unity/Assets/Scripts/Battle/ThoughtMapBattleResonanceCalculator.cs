using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public class ThoughtMapBattleResonanceCalculator
{
    private readonly ThoughtMapBattleResonanceConfig config;

    public ThoughtMapBattleResonanceCalculator(ThoughtMapBattleResonanceConfig config = null)
    {
        this.config = config == null ? ThoughtMapBattleResonanceConfig.RuntimeDefault : config;
    }

    public ThoughtMapResonanceResult CalculateTotalModifier(
        ThoughtMapBattleUnit unit,
        IReadOnlyList<ThoughtMapBattleUnit> allies
    )
    {
        ThoughtMapResonanceResult result = new ThoughtMapResonanceResult(unit);
        if (unit == null || unit.card == null || allies == null)
        {
            return result;
        }

        IEnumerable<ThoughtMapBattleUnit> neighbors = ThoughtMapBattleAdjacencyFinder.GetOrthogonalNeighbors(unit, allies);
        foreach (ThoughtMapBattleUnit neighbor in neighbors)
        {
            if (neighbor == null || neighbor.card == null || !neighbor.IsAlive)
            {
                continue;
            }

            float difference = Mathf.Abs(unit.card.resonance - neighbor.card.resonance);
            float modifier = config.GetStatModifierForDifference(difference);
            result.AddNeighbor(neighbor, difference, modifier);
        }

        result.totalModifier = Mathf.Clamp(
            result.rawTotalModifier,
            config.MinimumTotalStatModifier,
            config.MaximumTotalStatModifier
        );
        return result;
    }
}

public static class ThoughtMapBattleAdjacencyFinder
{
    public static IEnumerable<ThoughtMapBattleUnit> GetOrthogonalNeighbors(
        ThoughtMapBattleUnit unit,
        IReadOnlyList<ThoughtMapBattleUnit> candidates
    )
    {
        if (unit == null || candidates == null)
        {
            yield break;
        }

        foreach (ThoughtMapBattleUnit candidate in candidates)
        {
            if (candidate == null || candidate == unit)
            {
                continue;
            }

            if (unit.position.ManhattanDistance(candidate.position) == 1)
            {
                yield return candidate;
            }
        }
    }
}

public class ThoughtMapResonanceResult
{
    public readonly ThoughtMapBattleUnit unit;
    public readonly List<ThoughtMapResonanceNeighbor> neighbors = new List<ThoughtMapResonanceNeighbor>();
    public float rawTotalModifier;
    public float totalModifier;

    public ThoughtMapResonanceResult(ThoughtMapBattleUnit unit)
    {
        this.unit = unit;
    }

    public void AddNeighbor(ThoughtMapBattleUnit neighbor, float difference, float modifier)
    {
        neighbors.Add(new ThoughtMapResonanceNeighbor(neighbor, difference, modifier));
        rawTotalModifier += modifier;
    }

    public string ToDebugText()
    {
        string name = unit == null || unit.card == null ? "Unknown" : unit.card.cardName;
        if (neighbors.Count == 0)
        {
            return $"{name}: resonance={GetResonance(unit):0.00} neighbors=0 modifier={totalModifier:+0.00;-0.00;0.00}";
        }

        string neighborText = string.Join(
            "; ",
            neighbors.Select(item =>
                $"{item.neighbor.card.cardName} diff={item.difference:0.00} mod={item.modifier:+0.00;-0.00;0.00}"
            )
        );
        return $"{name}: resonance={GetResonance(unit):0.00} neighbors=[{neighborText}] total={totalModifier:+0.00;-0.00;0.00}";
    }

    private static float GetResonance(ThoughtMapBattleUnit target)
    {
        return target == null || target.card == null ? 0f : target.card.resonance;
    }
}

public readonly struct ThoughtMapResonanceNeighbor
{
    public readonly ThoughtMapBattleUnit neighbor;
    public readonly float difference;
    public readonly float modifier;

    public ThoughtMapResonanceNeighbor(ThoughtMapBattleUnit neighbor, float difference, float modifier)
    {
        this.neighbor = neighbor;
        this.difference = difference;
        this.modifier = modifier;
    }
}
