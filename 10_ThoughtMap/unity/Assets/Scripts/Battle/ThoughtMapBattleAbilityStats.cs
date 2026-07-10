using System.Collections.Generic;
using UnityEngine;

public static class ThoughtMapBattleAbilityStats
{
    public static readonly ThoughtMapBattleAbilityDefinition[] DisplayOrder =
    {
        new ThoughtMapBattleAbilityDefinition("HP", "HP", "individual", new Color(0.34f, 0.36f, 0.40f, 1f), "individual", "\u500B\u4EBA"),
        new ThoughtMapBattleAbilityDefinition("SP", "SP", "community", new Color(0.55f, 0.34f, 0.18f, 1f), "community", "\u5171\u540C\u4F53"),
        new ThoughtMapBattleAbilityDefinition("P.ATK", "Physical Attack", "philosophy", new Color(0.15f, 0.42f, 1f, 1f), "philosophy", "\u54F2\u5B66"),
        new ThoughtMapBattleAbilityDefinition("S.ATK", "Skill Attack", "psychology", new Color(1f, 0.82f, 0.18f, 1f), "psychology", "\u5FC3\u7406"),
        new ThoughtMapBattleAbilityDefinition("P.DEF", "Physical Defense", "science", new Color(0.25f, 0.78f, 0.32f, 1f), "science", "\u79D1\u5B66"),
        new ThoughtMapBattleAbilityDefinition("S.DEF", "Skill Defense", "moral", new Color(0.62f, 0.28f, 0.92f, 1f), "moral", "morality", "\u30E2\u30E9\u30EB"),
        new ThoughtMapBattleAbilityDefinition("SPD", "Speed", "economy", new Color(1f, 0.50f, 0.12f, 1f), "economy", "economics", "\u7D4C\u6E08"),
        new ThoughtMapBattleAbilityDefinition("EVA", "Evasion", "emotion", new Color(1f, 0.42f, 0.72f, 1f), "emotion", "\u611F\u60C5"),
        new ThoughtMapBattleAbilityDefinition("ACC", "Accuracy", "ideal", new Color(0.95f, 0.18f, 0.18f, 1f), "ideal", "\u7406\u5FF5"),
        new ThoughtMapBattleAbilityDefinition("LUCK", "Luck", "karma", new Color(1f, 0.88f, 0.42f, 1f), "karma", "\u30AB\u30EB\u30DE")
    };

    public static ThoughtMapBattleAbilityValue[] BuildValues(ThoughtMapBattleCardData card)
    {
        ThoughtMapBattleAbilityValue[] values = new ThoughtMapBattleAbilityValue[DisplayOrder.Length];
        for (int i = 0; i < DisplayOrder.Length; i++)
        {
            ThoughtMapBattleAbilityDefinition definition = DisplayOrder[i];
            float rawValue = GetParameterValue(card, definition.aliases);
            values[i] = new ThoughtMapBattleAbilityValue(definition, rawValue, NormalizeFill(rawValue));
        }
        return values;
    }

    public static float NormalizeFill(float value)
    {
        if (value <= 1f)
        {
            return Mathf.Clamp01(value);
        }

        return Mathf.Clamp01(value / 100f);
    }

    private static float GetParameterValue(ThoughtMapBattleCardData card, string[] aliases)
    {
        if (card == null || card.parameterScores == null || aliases == null)
        {
            return 0f;
        }

        foreach (string alias in aliases)
        {
            if (card.parameterScores.TryGetValue(alias, out float value))
            {
                return value;
            }

            string normalizedAlias = NormalizeKey(alias);
            foreach (KeyValuePair<string, float> pair in card.parameterScores)
            {
                if (NormalizeKey(pair.Key) == normalizedAlias)
                {
                    return pair.Value;
                }
            }
        }

        return 0f;
    }

    private static string NormalizeKey(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "";
        }

        string key = value.Trim().ToLowerInvariant();
        switch (key)
        {
            case "\u54F2\u5B66": return "philosophy";
            case "\u5FC3\u7406": return "psychology";
            case "\u79D1\u5B66": return "science";
            case "\u7D4C\u6E08": return "economy";
            case "economics": return "economy";
            case "\u30AB\u30EB\u30DE": return "karma";
            case "\u611F\u60C5": return "emotion";
            case "\u30E2\u30E9\u30EB": return "moral";
            case "morality": return "moral";
            case "\u7406\u5FF5": return "ideal";
            case "\u500B\u4EBA": return "individual";
            case "\u5171\u540C\u4F53": return "community";
            default: return key;
        }
    }
}

public struct ThoughtMapBattleAbilityDefinition
{
    public readonly string shortName;
    public readonly string displayName;
    public readonly string thoughtKey;
    public readonly Color color;
    public readonly string[] aliases;

    public ThoughtMapBattleAbilityDefinition(string shortName, string displayName, string thoughtKey, Color color, params string[] aliases)
    {
        this.shortName = shortName;
        this.displayName = displayName;
        this.thoughtKey = thoughtKey;
        this.color = color;
        this.aliases = aliases;
    }
}

public struct ThoughtMapBattleAbilityValue
{
    public readonly ThoughtMapBattleAbilityDefinition definition;
    public readonly float rawValue;
    public readonly float fillAmount;

    public ThoughtMapBattleAbilityValue(ThoughtMapBattleAbilityDefinition definition, float rawValue, float fillAmount)
    {
        this.definition = definition;
        this.rawValue = rawValue;
        this.fillAmount = fillAmount;
    }
}
