using System;
using System.Collections.Generic;
using UnityEngine;

public static class ThoughtMapBattleCardFactory
{
    private static readonly string[] ThoughtOrder =
    {
        "philosophy", "psychology", "science", "economy", "karma",
        "emotion", "moral", "ideal", "individual", "community"
    };

    public static ThoughtMapBattleCardData FromSavedDocument(SavedDocument document, string dataScope)
    {
        if (document == null)
        {
            return null;
        }

        string docId = FirstNonEmpty(document.doc_id, document.original_doc_id, document.title, "unknown");
        string scope = string.IsNullOrWhiteSpace(dataScope) ? "personal" : dataScope.Trim().ToLowerInvariant();

        ThoughtMapBattleCardData card = new ThoughtMapBattleCardData
        {
            docId = docId,
            sourceDocId = FirstNonEmpty(document.original_doc_id, document.doc_id, docId),
            cardId = BuildCardId(scope, docId),
            cardName = FirstNonEmpty(document.title, document.doc_id, "Untitled"),
            sourceTitle = document.title ?? "",
            author = document.author ?? "",
            source = document.source ?? "",
            category = document.category ?? "",
            url = FirstNonEmpty(document.url, document.source_url),
            dataScope = scope,
            raritySeed = StableSeed(docId, 17),
            skillSeed = StableSeed(docId, 31),
            resonance = 0.5f
        };

        CopyParameters(card, document.parameters);
        ApplyParameterStats(card);
        return card;
    }

    private static void CopyParameters(ThoughtMapBattleCardData card, ThoughtMapParameterScore[] parameters)
    {
        if (card == null || parameters == null)
        {
            return;
        }

        foreach (ThoughtMapParameterScore parameter in parameters)
        {
            if (parameter == null || string.IsNullOrWhiteSpace(parameter.key))
            {
                continue;
            }

            card.parameterScores[NormalizeKey(parameter.key)] = parameter.value;
        }
    }

    private static void ApplyParameterStats(ThoughtMapBattleCardData card)
    {
        float philosophy = GetParameter(card, "philosophy");
        float psychology = GetParameter(card, "psychology");
        float science = GetParameter(card, "science");
        float economy = GetParameter(card, "economy", "economics");
        float karma = GetParameter(card, "karma");
        float emotion = GetParameter(card, "emotion");
        float moral = GetParameter(card, "moral", "morality");
        float ideal = GetParameter(card, "ideal");
        float individual = GetParameter(card, "individual");
        float community = GetParameter(card, "community");

        card.statPhysicalAttack = ToStat(philosophy);
        card.statSkillAttack = ToStat(psychology);
        card.statPhysicalDefense = ToStat(science);
        card.statSpeed = ToStat(economy);
        card.statLuck = ToStat(karma);
        card.statEvasion = ToStat(emotion);
        card.statSkillDefense = ToStat(moral);
        card.statAccuracy = ToStat(ideal);
        card.statHp = ToStat(individual);
        card.statSp = ToStat(community);
        card.primaryAttribute = DominantParameter(card);
        card.secondaryAttribute = SecondaryParameter(card, card.primaryAttribute);

        float sum = NormalizeScore01(philosophy) + NormalizeScore01(psychology) + NormalizeScore01(science)
            + NormalizeScore01(economy) + NormalizeScore01(karma) + NormalizeScore01(emotion)
            + NormalizeScore01(moral) + NormalizeScore01(ideal) + NormalizeScore01(individual)
            + NormalizeScore01(community);
        card.resonance = Mathf.Clamp01(sum / ThoughtOrder.Length);
    }

    private static int ToStat(float value)
    {
        if (value <= 1f)
        {
            value *= 100f;
        }

        return Mathf.Clamp(Mathf.RoundToInt(value), 0, 100);
    }

    private static float NormalizeScore01(float value)
    {
        return value <= 1f ? Mathf.Clamp01(value) : Mathf.Clamp01(value / 100f);
    }

    private static float GetParameter(ThoughtMapBattleCardData card, params string[] aliases)
    {
        if (card == null || aliases == null)
        {
            return 0f;
        }

        foreach (string alias in aliases)
        {
            if (card.parameterScores.TryGetValue(NormalizeKey(alias), out float value))
            {
                return value;
            }
        }

        return 0f;
    }

    private static string DominantParameter(ThoughtMapBattleCardData card)
    {
        string bestKey = "";
        float bestValue = float.NegativeInfinity;
        foreach (string key in ThoughtOrder)
        {
            float value = GetParameter(card, key);
            if (value > bestValue)
            {
                bestValue = value;
                bestKey = key;
            }
        }
        return bestKey;
    }

    private static string SecondaryParameter(ThoughtMapBattleCardData card, string primary)
    {
        string bestKey = "";
        float bestValue = float.NegativeInfinity;
        foreach (string key in ThoughtOrder)
        {
            if (string.Equals(key, primary, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            float value = GetParameter(card, key);
            if (value > bestValue)
            {
                bestValue = value;
                bestKey = key;
            }
        }
        return bestKey;
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
            case "economics": return "economy";
            case "morality": return "moral";
            case "哲学": return "philosophy";
            case "心理": return "psychology";
            case "科学": return "science";
            case "経済": return "economy";
            case "カルマ": return "karma";
            case "感情": return "emotion";
            case "モラル": return "moral";
            case "理念": return "ideal";
            case "個人": return "individual";
            case "共同体": return "community";
            default: return key;
        }
    }

    private static string BuildCardId(string scope, string docId)
    {
        string safeScope = string.IsNullOrWhiteSpace(scope) ? "personal" : scope.Trim().ToLowerInvariant();
        string safeDocId = string.IsNullOrWhiteSpace(docId) ? "unknown" : docId.Trim();
        return $"{safeScope}:{safeDocId}";
    }

    private static int StableSeed(string value, int salt)
    {
        unchecked
        {
            int hash = 23 + salt;
            string text = value ?? "";
            for (int i = 0; i < text.Length; i++)
            {
                hash = (hash * 31) + text[i];
            }
            return hash == int.MinValue ? int.MaxValue : Mathf.Abs(hash);
        }
    }

    private static string FirstNonEmpty(params string[] values)
    {
        foreach (string value in values)
        {
            if (!string.IsNullOrWhiteSpace(value))
            {
                return value;
            }
        }
        return "";
    }
}
