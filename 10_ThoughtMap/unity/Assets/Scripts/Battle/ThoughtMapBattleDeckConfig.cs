using System;
using System.Collections.Generic;

[Serializable]
public class ThoughtMapBattleDeckConfig
{
    public List<string> deckCardIds = new List<string>();
    public List<string> deployedCardIds = new List<string>();
    public List<ThoughtMapBattleDeckPosition> gridPositions = new List<ThoughtMapBattleDeckPosition>();
    public List<CardAssignedSkillData> assignedSkills = new List<CardAssignedSkillData>();
    public List<ThoughtMapBattlePreparedUnitData> preparedUnits = new List<ThoughtMapBattlePreparedUnitData>();

    public bool HasDeck()
    {
        return deckCardIds != null && deckCardIds.Count > 0;
    }
}

[Serializable]
public class ThoughtMapBattlePreparedUnitData
{
    public string cardId;
    public int x;
    public int y;
    public float resonanceModifier;
    public float attackMultiplier = 1f;
    public float defenseMultiplier = 1f;
    public float hpMultiplier = 1f;
    public float speedMultiplier = 1f;
    public float hateMultiplier = 1f;
    public int maxHp;
    public int physicalAttack;
    public int skillAttack;
    public int physicalDefense;
    public int skillDefense;
    public int speed;
}

[Serializable]
public class ThoughtMapBattleDeckPosition
{
    public string cardId;
    public int x;
    public int y;

    public ThoughtMapBattleDeckPosition(string cardId, int x, int y)
    {
        this.cardId = cardId;
        this.x = x;
        this.y = y;
    }
}
