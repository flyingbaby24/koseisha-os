using System.Collections.Generic;
using System.IO;
using UnityEngine;

public static class GeneratedSkillLibrary
{
    public const string DefaultRelativePath = "GeneratedSkills/generated_skills.json";

    public static List<GeneratedSkillDto> LoadFromStreamingAssets(string relativePath, bool debugLog = false)
    {
        string path = Path.Combine(Application.streamingAssetsPath, string.IsNullOrWhiteSpace(relativePath) ? DefaultRelativePath : relativePath);
        if (!File.Exists(path))
        {
            Debug.LogWarning("[GeneratedSkill] JSON file not found: " + path);
            return new List<GeneratedSkillDto>();
        }

        string json = File.ReadAllText(path);
        List<GeneratedSkillDto> skills = Parse(json);
        if (debugLog)
        {
            Debug.Log($"[GeneratedSkill] loadedFromJson={skills.Count} path={path}");
        }
        return skills;
    }

    public static List<GeneratedSkillDto> Parse(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return new List<GeneratedSkillDto>();
        }

        string trimmed = json.Trim();
        if (trimmed.StartsWith("["))
        {
            GeneratedSkillArrayWrapper wrapper = JsonUtility.FromJson<GeneratedSkillArrayWrapper>("{\"skills\":" + trimmed + "}");
            return wrapper == null || wrapper.skills == null ? new List<GeneratedSkillDto>() : wrapper.skills;
        }

        if (trimmed.Contains("\"skills\""))
        {
            GeneratedSkillArrayWrapper wrapper = JsonUtility.FromJson<GeneratedSkillArrayWrapper>(trimmed);
            return wrapper == null || wrapper.skills == null ? new List<GeneratedSkillDto>() : wrapper.skills;
        }

        GeneratedSkillDto skill = JsonUtility.FromJson<GeneratedSkillDto>(trimmed);
        List<GeneratedSkillDto> result = new List<GeneratedSkillDto>();
        if (skill != null && !string.IsNullOrWhiteSpace(skill.skill_id))
        {
            result.Add(skill);
        }
        return result;
    }

    public static Dictionary<string, GeneratedSkillDto> ToDictionary(IEnumerable<GeneratedSkillDto> skills)
    {
        Dictionary<string, GeneratedSkillDto> result = new Dictionary<string, GeneratedSkillDto>();
        if (skills == null)
        {
            return result;
        }

        foreach (GeneratedSkillDto skill in skills)
        {
            if (skill == null || string.IsNullOrWhiteSpace(skill.skill_id))
            {
                continue;
            }
            result[skill.skill_id] = skill;
        }
        return result;
    }

    public static string EffectSummary(GeneratedSkillDto skill)
    {
        if (skill == null || skill.effects == null || skill.effects.Count == 0)
        {
            return "No effect";
        }

        List<string> parts = new List<string>();
        foreach (GeneratedSkillEffectDto effect in skill.effects)
        {
            if (effect == null)
            {
                continue;
            }
            parts.Add($"{Readable(effect.target)} / {Readable(effect.effect_type)} / {Readable(effect.parameter)} {effect.value:0.#}");
        }
        return parts.Count == 0 ? "No effect" : string.Join(" + ", parts);
    }

    public static string CostSummary(GeneratedSkillDto skill)
    {
        if (skill == null || skill.cost == null)
        {
            return "Cost: -";
        }

        List<string> parts = new List<string>();
        if (skill.cost.sp > 0) parts.Add("SP " + skill.cost.sp);
        if (skill.cost.hp_percent > 0f) parts.Add("HP " + skill.cost.hp_percent.ToString("0.#") + "%");
        if (skill.cost.consume_action) parts.Add("Action");
        return parts.Count == 0 ? "Cost: SP 0" : "Cost: " + string.Join(", ", parts);
    }

    public static string ShortSummary(GeneratedSkillDto skill)
    {
        if (skill == null)
        {
            return "Empty";
        }
        string effect = skill.effects != null && skill.effects.Count > 0 ? Readable(skill.effects[0].effect_type) : "Effect";
        return $"{Readable(skill.trigger)} / {effect} / CT {skill.cooldown}";
    }

    private static string Readable(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "-";
        }
        return value.Replace("_", " ");
    }
}
