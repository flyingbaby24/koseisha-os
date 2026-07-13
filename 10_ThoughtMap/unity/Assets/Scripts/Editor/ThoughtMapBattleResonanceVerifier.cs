using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class ThoughtMapBattleResonanceVerifier
{
    [MenuItem("Tools/Source of Thought/Verify Battle Resonance And Hate")]
    public static void Verify()
    {
        List<string> failures = new List<string>();
        ThoughtMapBattleResonanceConfig config = ThoughtMapBattleResonanceConfig.RuntimeDefault;
        ThoughtMapBattleResonanceCalculator resonance = new ThoughtMapBattleResonanceCalculator(config);
        ThoughtMapHateCalculator hate = new ThoughtMapHateCalculator(config, true);

        ThoughtMapBattleUnit center = Unit("Center", 0.0f, "Player", 2, 2);
        ThoughtMapBattleUnit diagonal = Unit("Diagonal", 0.0f, "Player", 3, 3);
        ThoughtMapBattleUnit rightSame = Unit("RightSame", 0.0f, "Player", 3, 2);
        ThoughtMapBattleUnit leftDifferent = Unit("LeftDifferent", 0.5f, "Player", 1, 2);
        ThoughtMapBattleUnit upSame = Unit("UpSame", 0.0f, "Player", 2, 3);
        ThoughtMapBattleUnit downSame = Unit("DownSame", 0.0f, "Player", 2, 1);

        ThoughtMapResonanceResult diagonalOnly = resonance.CalculateTotalModifier(center, new List<ThoughtMapBattleUnit> { center, diagonal });
        Check(diagonalOnly.neighbors.Count == 0, "Diagonal placement does not resonate.", failures);

        ThoughtMapResonanceResult orthogonal = resonance.CalculateTotalModifier(center, new List<ThoughtMapBattleUnit> { center, rightSame });
        Check(orthogonal.neighbors.Count == 1 && orthogonal.totalModifier > 0f, "Orthogonal placement resonates.", failures);

        ThoughtMapResonanceResult diffZero = resonance.CalculateTotalModifier(center, new List<ThoughtMapBattleUnit> { center, rightSame });
        ThoughtMapResonanceResult diffHalf = resonance.CalculateTotalModifier(center, new List<ThoughtMapBattleUnit> { center, leftDifferent });
        Check(!Mathf.Approximately(diffZero.totalModifier, diffHalf.totalModifier), "Resonance diff 0.0 and 0.5 produce different modifiers.", failures);

        ThoughtMapResonanceResult stacked = resonance.CalculateTotalModifier(center, new List<ThoughtMapBattleUnit> { center, rightSame, upSame });
        Check(stacked.totalModifier > diffZero.totalModifier, "Multiple adjacent modifiers stack.", failures);

        ThoughtMapResonanceResult clamped = resonance.CalculateTotalModifier(center, new List<ThoughtMapBattleUnit> { center, rightSame, upSame, downSame });
        Check(
            clamped.totalModifier <= config.MaximumTotalStatModifier &&
            clamped.totalModifier >= config.MinimumTotalStatModifier,
            "Resonance modifier stays within clamp.",
            failures
        );

        ThoughtMapBattleUnit attacker = Unit("Attacker", 0.0f, "Enemy", 2, 4);
        ThoughtMapBattleUnit frontSameColumn = Unit("Front", 0.1f, "Player", 2, 0);
        ThoughtMapBattleUnit farColumn = Unit("FarColumn", 0.1f, "Player", 4, 0);
        ThoughtMapBattleUnit backSameColumn = Unit("Back", 0.1f, "Player", 2, 4);
        ThoughtMapBattleUnit largeDiff = Unit("LargeDiff", 0.9f, "Player", 2, 0);
        ThoughtMapBattleUnit smallDiff = Unit("SmallDiff", 0.05f, "Player", 2, 0);
        ThoughtMapBattleUnit taunt = Unit("Taunt", 0.1f, "Player", 2, 0);
        ThoughtMapBattleUnit stealth = Unit("Stealth", 0.1f, "Player", 2, 0);
        taunt.skillHateModifier = 1.8f;
        stealth.skillHateModifier = 0.4f;

        Check(
            hate.CalculateHate(attacker, frontSameColumn, 1) > hate.CalculateHate(attacker, farColumn, 1),
            "Same-column front target has higher hate than far-column target.",
            failures
        );
        Check(
            hate.CalculateHate(attacker, frontSameColumn, 1) > hate.CalculateHate(attacker, backSameColumn, 1),
            "Back target has lower hate than front target.",
            failures
        );
        Check(
            hate.CalculateHate(attacker, largeDiff, 1) > hate.CalculateHate(attacker, smallDiff, 1),
            "Larger resonance difference increases hate.",
            failures
        );
        Check(
            hate.CalculateHate(attacker, taunt, 1) > hate.CalculateHate(attacker, frontSameColumn, 1) &&
            hate.CalculateHate(attacker, stealth, 1) < hate.CalculateHate(attacker, frontSameColumn, 1),
            "Taunt and stealth skill modifiers affect hate.",
            failures
        );

        if (failures.Count == 0)
        {
            Debug.Log("[Source of Thought Battle Verify] All resonance and hate checks passed.");
            return;
        }

        Debug.LogError("[Source of Thought Battle Verify] Failed checks:\n- " + string.Join("\n- ", failures));
    }

    private static ThoughtMapBattleUnit Unit(string name, float resonance, string team, int x, int y)
    {
        ThoughtMapBattleCardData card = new ThoughtMapBattleCardData
        {
            cardId = name,
            cardName = name,
            resonance = resonance,
            statPhysicalAttack = 50,
            statSkillAttack = 40,
            statPhysicalDefense = 20,
            statSkillDefense = 20,
            statSpeed = 30,
            statLuck = 10,
            statAccuracy = 50,
            statEvasion = 10,
            statHp = 50,
            statSp = 20,
            raritySeed = name.GetHashCode(),
            skillSeed = name.Length * 13,
            primaryAttribute = "Fire",
            secondaryAttribute = "Water",
        };

        return new ThoughtMapBattleUnit(card, team, new ThoughtMapGridPosition(x, y));
    }

    private static void Check(bool condition, string label, List<string> failures)
    {
        if (!condition)
        {
            failures.Add(label);
        }
    }
}
