public class ThoughtMapBattleUnit
{
    public ThoughtMapBattleCardData card;
    public string team;
    public ThoughtMapGridPosition position;
    public int hp;
    public int sp;
    public float hate;

    public bool IsAlive => hp > 0;

    public ThoughtMapBattleUnit(ThoughtMapBattleCardData card, string team, ThoughtMapGridPosition position)
    {
        this.card = card;
        this.team = team;
        this.position = position;
        hp = card == null ? 1 : card.MaxHp;
        sp = card == null ? 0 : card.MaxSp;
        hate = 0f;
    }
}
