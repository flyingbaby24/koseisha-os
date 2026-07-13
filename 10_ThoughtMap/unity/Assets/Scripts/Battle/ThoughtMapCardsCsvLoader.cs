using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

public static class ThoughtMapCardsCsvLoader
{
    private static readonly string[] ParameterColumns =
    {
        "philosophy", "psychology", "science", "economy", "economics", "karma",
        "emotion", "moral", "morality", "ideal", "individual", "community"
    };

    public static List<ThoughtMapBattleCardData> LoadFromText(string csvText)
    {
        List<ThoughtMapBattleCardData> cards = new List<ThoughtMapBattleCardData>();
        foreach (Dictionary<string, string> row in ThoughtMapCsvParser.Parse(csvText))
        {
            cards.Add(ParseCard(row));
        }
        return cards;
    }

    public static List<ThoughtMapBattleCardData> LoadFromStreamingAssets(string relativePath)
    {
        string path = Path.Combine(Application.streamingAssetsPath, relativePath);
        if (!File.Exists(path))
        {
            Debug.LogWarning($"[ThoughtMapBattle] cards.csv not found: {path}");
            return new List<ThoughtMapBattleCardData>();
        }

        return LoadFromText(File.ReadAllText(path));
    }

    private static ThoughtMapBattleCardData ParseCard(Dictionary<string, string> row)
    {
        ThoughtMapBattleCardData card = new ThoughtMapBattleCardData
        {
            cardId = Get(row, "card_id"),
            docId = FirstNonEmpty(row, "doc_id", "document_id", "source_doc_id", "original_doc_id", "id"),
            cardName = Get(row, "card_name"),
            sourceTitle = Get(row, "source_title"),
            author = Get(row, "author"),
            source = Get(row, "source"),
            primaryAttribute = Get(row, "primary_attribute"),
            secondaryAttribute = Get(row, "secondary_attribute"),
            statPhysicalAttack = GetInt(row, "stat_physical_attack"),
            statSkillAttack = GetInt(row, "stat_skill_attack"),
            statPhysicalDefense = GetInt(row, "stat_physical_defense"),
            statSpeed = GetInt(row, "stat_speed"),
            statLuck = GetInt(row, "stat_luck"),
            statEvasion = GetInt(row, "stat_evasion"),
            statSkillDefense = GetInt(row, "stat_skill_defense"),
            statAccuracy = GetInt(row, "stat_accuracy"),
            statHp = GetInt(row, "stat_hp"),
            statSp = GetInt(row, "stat_sp"),
            raritySeed = GetInt(row, "rarity_seed"),
            skillSeed = GetInt(row, "skill_seed"),
            resonance = NormalizeResonance(FirstFloat(row, 0.5f, "resonance", "resonance_coefficient", "embedding_score"))
        };

        if (string.IsNullOrWhiteSpace(card.cardName))
        {
            card.cardName = string.IsNullOrWhiteSpace(card.sourceTitle) ? card.docId : card.sourceTitle;
        }

        foreach (string parameter in ParameterColumns)
        {
            if (row.ContainsKey(parameter))
            {
                card.parameterScores[parameter] = GetFloat(row, parameter);
            }
        }

        return card;
    }

    private static string Get(Dictionary<string, string> row, string key)
    {
        return row.TryGetValue(key, out string value) ? value.Trim() : "";
    }

    private static string FirstNonEmpty(Dictionary<string, string> row, params string[] keys)
    {
        foreach (string key in keys)
        {
            string value = Get(row, key);
            if (!string.IsNullOrWhiteSpace(value))
            {
                return value;
            }
        }
        return "";
    }

    private static int GetInt(Dictionary<string, string> row, string key)
    {
        if (!row.TryGetValue(key, out string value))
        {
            return 0;
        }
        return int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out int parsed) ? parsed : 0;
    }

    private static float GetFloat(Dictionary<string, string> row, string key)
    {
        if (!row.TryGetValue(key, out string value))
        {
            return 0f;
        }
        return float.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out float parsed) ? parsed : 0f;
    }

    private static float FirstFloat(Dictionary<string, string> row, float fallback, params string[] keys)
    {
        foreach (string key in keys)
        {
            if (!row.TryGetValue(key, out string value) || string.IsNullOrWhiteSpace(value))
            {
                continue;
            }

            if (float.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out float parsed))
            {
                return parsed;
            }
        }

        return fallback;
    }

    private static float NormalizeResonance(float value)
    {
        if (value > 1f)
        {
            value /= 100f;
        }

        return Mathf.Clamp01(value);
    }
}
