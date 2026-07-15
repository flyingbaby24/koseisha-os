using System;
using System.Collections.Generic;
using UnityEngine;

public static class ThoughtMapBattleCardFactory
{
    private static readonly string[] ThoughtOrder =
    {
        "philosophy", "psychology", "science", "economy", "karma",
        "emotion", "morality", "ideology", "individual", "community"
    };

    public static ThoughtMapBattleCardData FromSavedDocument(SavedDocument document, string dataScope)
    {
        if (document == null)
        {
            return null;
        }

        string docId = FirstNonEmpty(document.doc_id, document.original_doc_id, document.source_doc_id, document.title, "unknown");
        string scope = string.IsNullOrWhiteSpace(dataScope) ? "personal" : dataScope.Trim().ToLowerInvariant();
        string title = FirstNonEmpty(document.title, document.source_title, document.doc_id, "Untitled");
        if (string.Equals(scope, "personal", StringComparison.OrdinalIgnoreCase))
        {
            Debug.Log(
                $"[PersonalLibrary Route] FromSavedDocument called doc_id='{docId}' title='{title}' parameters_array_count={(document.parameters == null ? 0 : document.parameters.Length)}"
            );
        }

        ThoughtMapBattleCardData card = new ThoughtMapBattleCardData
        {
            docId = docId,
            sourceDocId = FirstNonEmpty(document.source_doc_id, document.original_doc_id, document.doc_id, docId),
            cardId = BuildCardId(scope, docId),
            cardName = title,
            sourceTitle = FirstNonEmpty(document.source_title, document.title, ""),
            author = document.author ?? "",
            source = document.source ?? "",
            category = document.category ?? "",
            url = FirstNonEmpty(document.url, document.source_url),
            dataScope = scope,
            primaryAttribute = NormalizeKey(document.primary_attribute),
            secondaryAttribute = NormalizeKey(document.secondary_attribute),
            raritySeed = document.rarity_seed != 0 ? document.rarity_seed : StableSeed(docId, 17),
            skillSeed = document.skill_seed != 0 ? document.skill_seed : StableSeed(docId, 31),
            resonance = 0.5f
        };

        CopyParameters(card, document.parameters);
        CopyDirectParameters(card, document);
        ApplyExplicitStats(card, document);
        NormalizeAndApplyParameterStats(card, "PersonalLibrary FromSavedDocument", string.Equals(scope, "personal", StringComparison.OrdinalIgnoreCase));
        LogPersonalConversion(card);
        if (string.Equals(scope, "personal", StringComparison.OrdinalIgnoreCase))
        {
            Debug.Log(
                $"[PersonalLibrary Route] FromSavedDocument completed doc_id='{card.docId}' cardId='{card.cardId}' primaryAttribute='{card.primaryAttribute}' parameter_count={card.parameterScores.Count}"
            );
        }
        return card;
    }

    public static void NormalizeAndApplyParameterStats(ThoughtMapBattleCardData card, string context, bool log)
    {
        if (card == null)
        {
            return;
        }

        ThoughtMapBattleParameterScale.NormalizeInPlace(card, context, log);
        ApplyParameterStats(card);
        if (log)
        {
            Debug.Log(
                $"[Battle CardData Scale] {context} card='{card.cardName}' doc_id='{card.docId}' " +
                $"cardDataParameters={ThoughtMapBattleParameterScale.FormatCardParameters(card)} " +
                $"baseStats=[HP:{card.statHp}, SP:{card.statSp}, P_ATK:{card.statPhysicalAttack}, S_ATK:{card.statSkillAttack}, P_DEF:{card.statPhysicalDefense}, S_DEF:{card.statSkillDefense}, SPD:{card.statSpeed}, EVA:{card.statEvasion}, ACC:{card.statAccuracy}, LUCK:{card.statLuck}]"
            );
        }
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

    private static void CopyDirectParameters(ThoughtMapBattleCardData card, SavedDocument document)
    {
        if (card == null || document == null)
        {
            return;
        }

        SetParameterIfPresent(card, "philosophy", document.philosophy);
        SetParameterIfPresent(card, "psychology", document.psychology);
        SetParameterIfPresent(card, "science", document.science);
        SetParameterIfPresent(card, "economy", document.economy != 0f ? document.economy : document.economics);
        SetParameterIfPresent(card, "karma", document.karma);
        SetParameterIfPresent(card, "emotion", document.emotion);
        SetParameterIfPresent(card, "morality", FirstNonZero(document.morality, document.moral));
        SetParameterIfPresent(card, "ideology", FirstNonZero(document.ideology, document.ideal));
        SetParameterIfPresent(card, "individual", document.individual);
        SetParameterIfPresent(card, "community", document.community);
    }

    private static void SetParameterIfPresent(ThoughtMapBattleCardData card, string key, float value)
    {
        if (Mathf.Abs(value) > 0.000001f)
        {
            card.parameterScores[key] = value;
        }
    }

    private static void ApplyExplicitStats(ThoughtMapBattleCardData card, SavedDocument document)
    {
        if (card == null || document == null)
        {
            return;
        }

        card.statPhysicalAttack = document.stat_physical_attack;
        card.statSkillAttack = document.stat_skill_attack;
        card.statPhysicalDefense = document.stat_physical_defense;
        card.statSpeed = document.stat_speed;
        card.statLuck = document.stat_luck;
        card.statEvasion = document.stat_evasion;
        card.statSkillDefense = document.stat_skill_defense;
        card.statAccuracy = document.stat_accuracy;
        card.statHp = document.stat_hp;
        card.statSp = document.stat_sp;
    }

    private static void ApplyParameterStats(ThoughtMapBattleCardData card)
    {
        float philosophy = GetParameter(card, "philosophy");
        float psychology = GetParameter(card, "psychology");
        float science = GetParameter(card, "science");
        float economy = GetParameter(card, "economy", "economics");
        float karma = GetParameter(card, "karma");
        float emotion = GetParameter(card, "emotion");
        float moral = GetParameter(card, "morality", "moral");
        float ideal = GetParameter(card, "ideology", "ideal");
        float individual = GetParameter(card, "individual");
        float community = GetParameter(card, "community");

        if (card.statPhysicalAttack == 0) card.statPhysicalAttack = ThoughtMapBattleParameterScale.ToStat(philosophy);
        if (card.statSkillAttack == 0) card.statSkillAttack = ThoughtMapBattleParameterScale.ToStat(psychology);
        if (card.statPhysicalDefense == 0) card.statPhysicalDefense = ThoughtMapBattleParameterScale.ToStat(science);
        if (card.statSpeed == 0) card.statSpeed = ThoughtMapBattleParameterScale.ToStat(economy);
        if (card.statLuck == 0) card.statLuck = ThoughtMapBattleParameterScale.ToStat(karma);
        if (card.statEvasion == 0) card.statEvasion = ThoughtMapBattleParameterScale.ToStat(emotion);
        if (card.statSkillDefense == 0) card.statSkillDefense = ThoughtMapBattleParameterScale.ToStat(moral);
        if (card.statAccuracy == 0) card.statAccuracy = ThoughtMapBattleParameterScale.ToStat(ideal);
        if (card.statHp == 0) card.statHp = ThoughtMapBattleParameterScale.ToStat(individual);
        if (card.statSp == 0) card.statSp = ThoughtMapBattleParameterScale.ToStat(community);

        if (string.IsNullOrWhiteSpace(card.primaryAttribute) || IsPlaceholderAttribute(card.primaryAttribute))
        {
            card.primaryAttribute = DominantParameter(card);
        }
        if (string.IsNullOrWhiteSpace(card.secondaryAttribute) || IsPlaceholderAttribute(card.secondaryAttribute))
        {
            card.secondaryAttribute = SecondaryParameter(card, card.primaryAttribute);
        }

        float sum = ThoughtMapBattleParameterScale.ToUnitScale(philosophy) + ThoughtMapBattleParameterScale.ToUnitScale(psychology) + ThoughtMapBattleParameterScale.ToUnitScale(science)
            + ThoughtMapBattleParameterScale.ToUnitScale(economy) + ThoughtMapBattleParameterScale.ToUnitScale(karma) + ThoughtMapBattleParameterScale.ToUnitScale(emotion)
            + ThoughtMapBattleParameterScale.ToUnitScale(moral) + ThoughtMapBattleParameterScale.ToUnitScale(ideal) + ThoughtMapBattleParameterScale.ToUnitScale(individual)
            + ThoughtMapBattleParameterScale.ToUnitScale(community);
        card.resonance = Mathf.Clamp01(sum / ThoughtOrder.Length);
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
        if (!HasAnyParameter(card))
        {
            return "";
        }

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
        if (!HasAnyParameter(card))
        {
            return "";
        }

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

    private static bool HasAnyParameter(ThoughtMapBattleCardData card)
    {
        if (card == null || card.parameterScores == null)
        {
            return false;
        }

        foreach (string key in ThoughtOrder)
        {
            if (Mathf.Abs(GetParameter(card, key)) > 0.000001f)
            {
                return true;
            }
        }

        return false;
    }

    private static bool IsPlaceholderAttribute(string value)
    {
        string key = NormalizeKey(value);
        return string.IsNullOrWhiteSpace(key) ||
            key == "card" ||
            key == "unknown" ||
            key == "none" ||
            key == "-";
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
            default: return ThoughtMapBattleParameterScale.NormalizeKey(key);
        }
    }

    private static float FirstNonZero(params float[] values)
    {
        if (values == null)
        {
            return 0f;
        }

        foreach (float value in values)
        {
            if (Mathf.Abs(value) > 0.000001f)
            {
                return value;
            }
        }

        return 0f;
    }

    private static void LogPersonalConversion(ThoughtMapBattleCardData card)
    {
        if (card == null || !string.Equals(card.dataScope, "personal", StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        Debug.Log(
            "[PersonalLibrary CardData] " +
            $"doc_id='{card.docId}' parameters={card.parameterScores.Count} " +
            $"values=[philosophy:{GetParameter(card, "philosophy"):0.###}, psychology:{GetParameter(card, "psychology"):0.###}, science:{GetParameter(card, "science"):0.###}, economy:{GetParameter(card, "economy"):0.###}, karma:{GetParameter(card, "karma"):0.###}, emotion:{GetParameter(card, "emotion"):0.###}, morality:{GetParameter(card, "morality"):0.###}, ideology:{GetParameter(card, "ideology"):0.###}, individual:{GetParameter(card, "individual"):0.###}, community:{GetParameter(card, "community"):0.###}] " +
            $"dominant='{card.primaryAttribute}' " +
            $"stats=[HP:{card.statHp}, SP:{card.statSp}, P_ATK:{card.statPhysicalAttack}, S_ATK:{card.statSkillAttack}, P_DEF:{card.statPhysicalDefense}, S_DEF:{card.statSkillDefense}, SPD:{card.statSpeed}, EVA:{card.statEvasion}, ACC:{card.statAccuracy}, LUCK:{card.statLuck}]"
        );
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
