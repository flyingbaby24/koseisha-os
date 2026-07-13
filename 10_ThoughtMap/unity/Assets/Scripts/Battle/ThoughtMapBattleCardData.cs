using System;
using System.Collections.Generic;
using UnityEngine;

[Serializable]
public class ThoughtMapBattleCardData
{
    public string cardId;
    public string docId;
    public string cardName;
    public string sourceTitle;
    public string author;
    public string source;
    public string category;
    public string url;
    public string sourceDocId;
    public string dataScope = "official";
    public string primaryAttribute;
    public string secondaryAttribute;
    public int statPhysicalAttack;
    public int statSkillAttack;
    public int statPhysicalDefense;
    public int statSpeed;
    public int statLuck;
    public int statEvasion;
    public int statSkillDefense;
    public int statAccuracy;
    public int statHp;
    public int statSp;
    public int raritySeed;
    public int skillSeed;
    [Range(0f, 1f)] public float resonance = 0.5f;

    public readonly Dictionary<string, float> parameterScores = new Dictionary<string, float>();

    public int MaxHp => Math.Max(1, 80 + statHp);
    public int MaxSp => Math.Max(1, 30 + statSp);

    public int GetStat(string statName)
    {
        switch (statName)
        {
            case "physical_attack": return statPhysicalAttack;
            case "skill_attack": return statSkillAttack;
            case "physical_defense": return statPhysicalDefense;
            case "speed": return statSpeed;
            case "luck": return statLuck;
            case "evasion": return statEvasion;
            case "skill_defense": return statSkillDefense;
            case "accuracy": return statAccuracy;
            case "hp": return statHp;
            case "sp": return statSp;
            default: return 0;
        }
    }
}
