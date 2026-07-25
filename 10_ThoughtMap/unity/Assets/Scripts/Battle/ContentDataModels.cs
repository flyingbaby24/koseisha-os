using System;
using System.Collections.Generic;

[Serializable] public sealed class CampaignData { public string defaultStageId; public List<CampaignStageData> stages = new List<CampaignStageData>(); }
[Serializable] public sealed class CampaignStageData
{
    public string stageId;
    public string displayName;
    public string enemyDeckId;
    public string rewardTableId;
    public string dropTableId;
    public string skillPoolId;
    public string nextStageId;
}

[Serializable] public sealed class EnemyDeckCollection { public List<EnemyDeckData> decks = new List<EnemyDeckData>(); }
[Serializable] public sealed class EnemyDeckData
{
    public string deckId;
    public List<string> cardIds = new List<string>();
    public List<ThoughtMapBattleDeckPosition> visualPositions = new List<ThoughtMapBattleDeckPosition>();
}

[Serializable] public sealed class RewardTableCollection { public List<RewardTableData> tables = new List<RewardTableData>(); }
[Serializable] public sealed class RewardTableData
{
    public string tableId;
    public int victoryFragments;
    public int defeatFragments;
    public int fragmentsPerKill;
    public int minimumResearchPoints;
    public int researchPerTurn;
    public float researchPerDamage;
    public float victorySkillChance;
    public float defeatSkillChance;
}

[Serializable] public sealed class DropTableCollection { public List<DropTableData> tables = new List<DropTableData>(); }
[Serializable] public sealed class DropTableData
{
    public string tableId;
    public float victoryRareChance;
    public float defeatRareChance;
    public List<DropEntryData> rareCards = new List<DropEntryData>();
}
[Serializable] public sealed class DropEntryData { public string id; public string name; public int weight = 1; }

[Serializable] public sealed class SkillPoolCollection { public List<SkillPoolData> pools = new List<SkillPoolData>(); }
[Serializable] public sealed class SkillPoolData { public string poolId; public List<string> skillIds = new List<string>(); }
