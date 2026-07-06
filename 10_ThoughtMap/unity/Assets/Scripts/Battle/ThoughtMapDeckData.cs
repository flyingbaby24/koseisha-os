using System.Collections.Generic;
using System.Linq;

public class ThoughtMapDeckData
{
    public readonly List<ThoughtMapBattleCardData> cards = new List<ThoughtMapBattleCardData>();

    public ThoughtMapDeckData(IEnumerable<ThoughtMapBattleCardData> sourceCards, int maxCards = 10)
    {
        if (sourceCards == null)
        {
            return;
        }

        cards.AddRange(sourceCards.Where(card => card != null).Take(maxCards));
    }

    public List<ThoughtMapBattleCardData> SelectBattleCards(int count = 5)
    {
        return cards.Take(count).ToList();
    }
}
