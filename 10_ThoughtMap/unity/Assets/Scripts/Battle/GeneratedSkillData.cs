using System;
using System.Collections.Generic;

[Serializable]
public class GeneratedSkillDto
{
    public string skill_id;
    public string doc_id;
    public string name_ja;
    public string name_en;
    public List<GeneratedSkillConceptDto> concepts = new List<GeneratedSkillConceptDto>();
    public string trigger;
    public List<GeneratedSkillConditionDto> conditions = new List<GeneratedSkillConditionDto>();
    public List<GeneratedSkillEffectDto> effects = new List<GeneratedSkillEffectDto>();
    public GeneratedSkillCostDto cost = new GeneratedSkillCostDto();
    public int cooldown;
    public int generation_version;
    public string description_ja;
    public string description_en;

    public string DisplayName => string.IsNullOrWhiteSpace(name_ja) ? name_en : name_ja;
}

[Serializable]
public class GeneratedSkillConceptDto
{
    public string label_ja;
    public string label_en;
    public string category;
    public float similarity;
    public int rank;
}

[Serializable]
public class GeneratedSkillEffectDto
{
    public int effect_order;
    public string effect_type;
    public string target;
    public string parameter;
    public string operation;
    public float value;
    public string value_type;
    public int duration;
    public float probability;
}

[Serializable]
public class GeneratedSkillConditionDto
{
    public string condition_type;
    public string parameter;
    public string @operator;
    public float value;
}

[Serializable]
public class GeneratedSkillCostDto
{
    public int sp;
    public float hp_percent;
    public bool consume_action;
}

[Serializable]
public class CardAssignedSkillData
{
    public string cardId;
    public List<string> skillIds = new List<string>();

    public CardAssignedSkillData()
    {
    }

    public CardAssignedSkillData(string cardId, IEnumerable<string> skillIds)
    {
        this.cardId = cardId;
        this.skillIds = new List<string>(skillIds);
    }
}

[Serializable]
public class GeneratedSkillArrayWrapper
{
    public List<GeneratedSkillDto> skills = new List<GeneratedSkillDto>();
}
