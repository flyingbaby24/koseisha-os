using System;
using System.Collections.Generic;

[Serializable]
public class ThoughtMapBattleDeckConfig
{
    public List<string> deckCardIds = new List<string>();
    public List<string> deployedCardIds = new List<string>();
    public List<ThoughtMapBattleDeckPosition> gridPositions = new List<ThoughtMapBattleDeckPosition>();

    public bool HasDeck()
    {
        return deckCardIds != null && deckCardIds.Count > 0;
    }
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
