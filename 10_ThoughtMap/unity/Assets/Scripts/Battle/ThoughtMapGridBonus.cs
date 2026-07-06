public struct ThoughtMapGridBonus
{
    public float attackMultiplier;
    public float defenseMultiplier;
    public float hateMultiplier;

    public ThoughtMapGridBonus(float attackMultiplier, float defenseMultiplier, float hateMultiplier)
    {
        this.attackMultiplier = attackMultiplier;
        this.defenseMultiplier = defenseMultiplier;
        this.hateMultiplier = hateMultiplier;
    }
}

public static class ThoughtMapGridBonusCalculator
{
    public static ThoughtMapGridBonus GetBonus(ThoughtMapGridPosition position, string team)
    {
        bool player = team == "Player";
        int forwardY = player ? 0 : 4;
        int backY = player ? 4 : 0;

        float attack = position.y == forwardY ? 1.10f : 1.0f;
        float defense = position.y == backY ? 1.12f : 1.0f;
        float hate = position.y == forwardY ? 1.25f : 0.9f;

        if (position.x == 2 && position.y == 2)
        {
            attack *= 1.05f;
            defense *= 1.05f;
            hate *= 1.08f;
        }

        return new ThoughtMapGridBonus(attack, defense, hate);
    }
}
