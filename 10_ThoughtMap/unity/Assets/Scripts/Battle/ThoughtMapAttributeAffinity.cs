using System.Collections.Generic;

public enum ThoughtMapAttributeGroup
{
    Neutral,
    Mind,
    System,
    Human
}

public static class ThoughtMapAttributeAffinity
{
    private static readonly HashSet<string> Mind = new HashSet<string>
    {
        "philosophy", "psychology", "ideal"
    };

    private static readonly HashSet<string> System = new HashSet<string>
    {
        "science", "economics", "individual"
    };

    private static readonly HashSet<string> Human = new HashSet<string>
    {
        "emotion", "morality", "community"
    };

    public static ThoughtMapAttributeGroup GetGroup(string attribute)
    {
        string key = Normalize(attribute);
        if (key == "karma")
        {
            return ThoughtMapAttributeGroup.Neutral;
        }
        if (Mind.Contains(key))
        {
            return ThoughtMapAttributeGroup.Mind;
        }
        if (System.Contains(key))
        {
            return ThoughtMapAttributeGroup.System;
        }
        if (Human.Contains(key))
        {
            return ThoughtMapAttributeGroup.Human;
        }
        return ThoughtMapAttributeGroup.Neutral;
    }

    public static float GetMultiplier(string attackerPrimary, string attackerSecondary, string defenderPrimary)
    {
        float primary = GetSingleMultiplier(attackerPrimary, defenderPrimary, 1.2f, 0.85f);
        float secondary = GetSingleMultiplier(attackerSecondary, defenderPrimary, 1.08f, 0.95f);
        return primary * secondary;
    }

    private static float GetSingleMultiplier(string attacker, string defender, float advantage, float disadvantage)
    {
        ThoughtMapAttributeGroup atk = GetGroup(attacker);
        ThoughtMapAttributeGroup def = GetGroup(defender);
        if (atk == ThoughtMapAttributeGroup.Neutral || def == ThoughtMapAttributeGroup.Neutral || atk == def)
        {
            return 1f;
        }

        // MVP triangle: Mind reads Human, Human disrupts System, System constrains Mind.
        if ((atk == ThoughtMapAttributeGroup.Mind && def == ThoughtMapAttributeGroup.Human) ||
            (atk == ThoughtMapAttributeGroup.Human && def == ThoughtMapAttributeGroup.System) ||
            (atk == ThoughtMapAttributeGroup.System && def == ThoughtMapAttributeGroup.Mind))
        {
            return advantage;
        }

        return disadvantage;
    }

    private static string Normalize(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? "" : value.Trim().ToLowerInvariant();
    }
}
