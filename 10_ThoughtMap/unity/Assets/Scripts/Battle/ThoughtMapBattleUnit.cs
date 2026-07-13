public class ThoughtMapBattleUnit
{
    public ThoughtMapBattleCardData card;
    public string team;
    public ThoughtMapGridPosition position;
    public int hp;
    public int maxHp;
    public int sp;
    public float hate;
    public int damageDone;
    public int damageTaken;
    public string lastTargetKey = "";
    public string battleId = "";
    public float skillHateModifier = 1f;

    public bool IsAlive => hp > 0;

    public ThoughtMapBattleUnit(ThoughtMapBattleCardData card, string team, ThoughtMapGridPosition position)
    {
        this.card = card;
        this.team = team;
        this.position = position;
        ThoughtMapGridBonus gridBonus = ThoughtMapGridBonusCalculator.GetBonus(position, team);
        maxHp = card == null ? 1 : UnityEngine.Mathf.Max(1, UnityEngine.Mathf.RoundToInt(card.MaxHp * gridBonus.hpMultiplier));
        hp = maxHp;
        sp = card == null ? 0 : card.MaxSp;
        hate = 0f;
        damageDone = 0;
        damageTaken = 0;
    }
}
