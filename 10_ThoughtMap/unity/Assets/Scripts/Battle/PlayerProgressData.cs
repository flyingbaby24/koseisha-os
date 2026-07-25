using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

[Serializable]
public sealed class PlayerProgressData
{
    public int thoughtFragments;
    public int researchPoints;
    public List<string> generatedSkillIds = new List<string>();
    public List<string> rareCardIds = new List<string>();
    public List<string> claimedRewardIds = new List<string>();
}

public sealed class PlayerProgressRepository
{
    public string SavePath => Path.Combine(Application.persistentDataPath, "player_progress.json");

    public PlayerProgressData Load()
    {
        if (!File.Exists(SavePath))
        {
            return new PlayerProgressData();
        }
        try
        {
            return JsonUtility.FromJson<PlayerProgressData>(File.ReadAllText(SavePath, Encoding.UTF8))
                ?? new PlayerProgressData();
        }
        catch (Exception exc)
        {
            Debug.LogError("[PlayerProgress] Could not load player_progress.json: " + exc);
            return new PlayerProgressData();
        }
    }

    public PlayerProgressData ClaimAndSave(RewardData reward)
    {
        PlayerProgressData progress = Load();
        if (reward == null || progress.claimedRewardIds.Contains(reward.rewardId))
        {
            return progress;
        }
        progress.thoughtFragments += Math.Max(0, reward.thoughtFragments);
        progress.researchPoints += Math.Max(0, reward.researchPoints);
        if (reward.hasGeneratedSkill && !string.IsNullOrWhiteSpace(reward.generatedSkillId) &&
            !progress.generatedSkillIds.Contains(reward.generatedSkillId))
        {
            progress.generatedSkillIds.Add(reward.generatedSkillId);
        }
        if (reward.hasRareCard && !string.IsNullOrWhiteSpace(reward.rareCardId) &&
            !progress.rareCardIds.Contains(reward.rareCardId))
        {
            progress.rareCardIds.Add(reward.rareCardId);
        }
        progress.claimedRewardIds.Add(reward.rewardId);
        File.WriteAllText(SavePath, JsonUtility.ToJson(progress, true), new UTF8Encoding(false));
        Debug.Log($"[PlayerProgress] Saved: {SavePath}");
        return progress;
    }
}
