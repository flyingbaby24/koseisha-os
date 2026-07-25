using System;

[Serializable]
public sealed class RewardData
{
    public string rewardId;
    public int thoughtFragments;
    public int researchPoints;
    public string generatedSkillId;
    public string generatedSkillName;
    public string rareCardId;
    public string rareCardName;
    public bool hasGeneratedSkill;
    public bool hasRareCard;
}
