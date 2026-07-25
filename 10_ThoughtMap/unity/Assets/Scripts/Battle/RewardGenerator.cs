using System;
using System.Collections.Generic;
using System.Linq;

public sealed class RewardGenerator
{
    private readonly Random random;

    public RewardGenerator(int? seed = null)
    {
        random = seed.HasValue ? new Random(seed.Value) : new Random();
    }

    public RewardData Generate(BattleResultData result)
    {
        CampaignStageData stage = CampaignManager.Instance.CurrentStage;
        RewardTableData rewardTable = stage == null ? null : RewardTableLoader.Load(stage.rewardTableId);
        DropTableData dropTable = stage == null ? null : DropTableLoader.Load(stage.dropTableId);
        SkillPoolData skillPool = stage == null ? null : SkillPoolLoader.Load(stage.skillPoolId);
        if (stage == null || rewardTable == null || dropTable == null || skillPool == null)
        {
            throw new InvalidOperationException("Campaign reward content is incomplete. Check campaign.json and referenced table IDs.");
        }

        BattleStatistics statistics = result == null ? null : result.statistics;
        int kills = statistics == null ? 0 : statistics.totalKills;
        int damage = statistics == null ? 0 : statistics.totalDamage;
        int turns = result == null ? 0 : result.turnCount;
        RewardData reward = new RewardData
        {
            rewardId = Guid.NewGuid().ToString("N"),
            thoughtFragments = (result != null && result.victory ? rewardTable.victoryFragments : rewardTable.defeatFragments)
                + kills * rewardTable.fragmentsPerKill,
            researchPoints = Math.Max(
                rewardTable.minimumResearchPoints,
                (int)Math.Round(turns * rewardTable.researchPerTurn + damage * rewardTable.researchPerDamage)),
        };

        List<GeneratedSkillDto> skills = GeneratedSkillLibrary
            .LoadFromStreamingAssets(GeneratedSkillLibrary.DefaultRelativePath)
            .Where(skill => skill != null && !string.IsNullOrWhiteSpace(skill.skill_id) && skillPool.skillIds.Contains(skill.skill_id))
            .ToList();
        float skillChance = result != null && result.victory ? rewardTable.victorySkillChance : rewardTable.defeatSkillChance;
        if (skills.Count > 0 && random.NextDouble() < skillChance)
        {
            GeneratedSkillDto skill = skills[random.Next(skills.Count)];
            reward.hasGeneratedSkill = true;
            reward.generatedSkillId = skill.skill_id;
            reward.generatedSkillName = skill.DisplayName;
        }

        float rareChance = result != null && result.victory ? dropTable.victoryRareChance : dropTable.defeatRareChance;
        DropEntryData rareCard = SelectWeighted(dropTable.rareCards);
        if (rareCard != null && random.NextDouble() < rareChance)
        {
            reward.hasRareCard = true;
            reward.rareCardId = rareCard.id;
            reward.rareCardName = rareCard.name;
        }
        return reward;
    }

    private DropEntryData SelectWeighted(List<DropEntryData> entries)
    {
        List<DropEntryData> valid = entries == null
            ? new List<DropEntryData>()
            : entries.Where(entry => entry != null && entry.weight > 0).ToList();
        int total = valid.Sum(entry => entry.weight);
        if (total <= 0)
        {
            return null;
        }
        int roll = random.Next(total);
        foreach (DropEntryData entry in valid)
        {
            roll -= entry.weight;
            if (roll < 0)
            {
                return entry;
            }
        }
        return valid[valid.Count - 1];
    }
}
