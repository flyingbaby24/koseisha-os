using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;

public struct ThoughtMapParameterScaleReport
{
    public int count;
    public float scale;
    public string rawValues;
    public string normalizedValues;
}

public static class ThoughtMapBattleParameterScale
{
    public static readonly string[] ThoughtKeys =
    {
        "philosophy", "psychology", "science", "economy", "karma",
        "emotion", "morality", "ideology", "individual", "community"
    };

    public static ThoughtMapParameterScaleReport NormalizeInPlace(
        ThoughtMapBattleCardData card,
        string context,
        bool log)
    {
        ThoughtMapParameterScaleReport report = new ThoughtMapParameterScaleReport
        {
            count = 0,
            scale = 1f,
            rawValues = "<none>",
            normalizedValues = "<none>"
        };

        if (card == null || card.parameterScores == null)
        {
            return report;
        }

        Dictionary<string, float> raw = ReadCanonicalParameters(card.parameterScores);
        report.count = raw.Count;
        report.rawValues = FormatValues(raw);
        if (raw.Count == 0)
        {
            _ = log;
            return report;
        }

        float maxAbs = 0f;
        foreach (float value in raw.Values)
        {
            maxAbs = Mathf.Max(maxAbs, Mathf.Abs(value));
        }

        float scale = maxAbs <= 1.000001f ? 100f : 1f;
        Dictionary<string, float> normalized = new Dictionary<string, float>();
        foreach (string key in ThoughtKeys)
        {
            if (!raw.TryGetValue(key, out float value))
            {
                continue;
            }

            normalized[key] = NormalizeRawValue(value, scale);
        }

        card.parameterScores.Clear();
        foreach (KeyValuePair<string, float> pair in normalized)
        {
            card.parameterScores[pair.Key] = pair.Value;
        }

        report.scale = scale;
        report.normalizedValues = FormatValues(normalized);
        _ = log;

        return report;
    }

    public static int ToStat(float normalizedValue)
    {
        return Mathf.Clamp(Mathf.RoundToInt(normalizedValue), 0, 100);
    }

    public static float ToUnitScale(float normalizedValue)
    {
        return Mathf.Clamp01(normalizedValue / 100f);
    }

    public static string NormalizeKey(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "";
        }

        string key = value.Trim().ToLowerInvariant();
        switch (key)
        {
            case "economics": return "economy";
            case "moral": return "morality";
            case "ideal": return "ideology";
            case "\u54F2\u5B66": return "philosophy";
            case "\u5FC3\u7406": return "psychology";
            case "\u79D1\u5B66": return "science";
            case "\u7D4C\u6E08": return "economy";
            case "\u30AB\u30EB\u30DE": return "karma";
            case "\u611F\u60C5": return "emotion";
            case "\u30E2\u30E9\u30EB": return "morality";
            case "\u7406\u5FF5": return "ideology";
            case "\u500B\u4EBA": return "individual";
            case "\u5171\u540C\u4F53": return "community";
            default: return key;
        }
    }

    public static string FormatCardParameters(ThoughtMapBattleCardData card)
    {
        if (card == null || card.parameterScores == null)
        {
            return "<null>";
        }

        return FormatValues(ReadCanonicalParameters(card.parameterScores));
    }

    private static float NormalizeRawValue(float value, float scale)
    {
        float normalized = value * scale;
        if (float.IsNaN(normalized) || float.IsInfinity(normalized))
        {
            return 0f;
        }

        return normalized;
    }

    private static Dictionary<string, float> ReadCanonicalParameters(Dictionary<string, float> source)
    {
        Dictionary<string, float> values = new Dictionary<string, float>();
        if (source == null)
        {
            return values;
        }

        foreach (string key in ThoughtKeys)
        {
            if (TryGetParameter(source, key, out float value))
            {
                values[key] = value;
            }
        }

        return values;
    }

    private static bool TryGetParameter(Dictionary<string, float> source, string key, out float value)
    {
        value = 0f;
        if (source == null || string.IsNullOrWhiteSpace(key))
        {
            return false;
        }

        string normalizedKey = NormalizeKey(key);
        if (source.TryGetValue(normalizedKey, out value))
        {
            return true;
        }

        foreach (KeyValuePair<string, float> pair in source)
        {
            if (NormalizeKey(pair.Key) == normalizedKey)
            {
                value = pair.Value;
                return true;
            }
        }

        return false;
    }

    private static string FormatValues(Dictionary<string, float> values)
    {
        if (values == null || values.Count == 0)
        {
            return "<none>";
        }

        StringBuilder builder = new StringBuilder();
        builder.Append('[');
        for (int i = 0; i < ThoughtKeys.Length; i++)
        {
            string key = ThoughtKeys[i];
            if (i > 0)
            {
                builder.Append(", ");
            }

            builder.Append(key);
            builder.Append(':');
            builder.Append(values.TryGetValue(key, out float value) ? value.ToString("0.###") : "missing");
        }
        builder.Append(']');
        return builder.ToString();
    }
}
