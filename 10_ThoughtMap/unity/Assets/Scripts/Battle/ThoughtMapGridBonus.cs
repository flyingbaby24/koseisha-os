public struct ThoughtMapGridBonus
{
    public float attackMultiplier;
    public float defenseMultiplier;
    public float hpMultiplier;
    public float speedMultiplier;
    public float evasionMultiplier;
    public float accuracyMultiplier;
    public float hateMultiplier;

    public ThoughtMapGridBonus(float attackMultiplier, float defenseMultiplier, float hpMultiplier, float hateMultiplier)
        : this(attackMultiplier, defenseMultiplier, hpMultiplier, 1f, 1f, 1f, hateMultiplier)
    {
    }

    public ThoughtMapGridBonus(
        float attackMultiplier,
        float defenseMultiplier,
        float hpMultiplier,
        float speedMultiplier,
        float evasionMultiplier,
        float accuracyMultiplier,
        float hateMultiplier)
    {
        this.attackMultiplier = attackMultiplier;
        this.defenseMultiplier = defenseMultiplier;
        this.hpMultiplier = hpMultiplier;
        this.speedMultiplier = speedMultiplier;
        this.evasionMultiplier = evasionMultiplier;
        this.accuracyMultiplier = accuracyMultiplier;
        this.hateMultiplier = hateMultiplier;
    }
}

public static class ThoughtMapGridBonusCalculator
{
    public static ThoughtMapGridBonus GetBonus(ThoughtMapGridPosition position, string team)
    {
        bool player = team == "Player";
        int relativeY = player ? position.y : 4 - position.y;

        float attack = 1.0f;
        float defense = 1.0f;
        float hp = 1.0f;
        float speed = 1.0f;
        float evasion = 1.0f;
        float accuracy = 1.0f;
        float hate = 1.0f;

        switch (relativeY)
        {
            case 0:
                attack *= 1.10f;
                hp *= 0.95f;
                hate *= 1.25f;
                break;
            case 1:
                attack *= 1.05f;
                hate *= 1.10f;
                break;
            case 3:
                defense *= 1.06f;
                hate *= 0.95f;
                break;
            case 4:
                defense *= 1.12f;
                hate *= 0.90f;
                break;
        }

        switch (position.x)
        {
            case 0:
            case 4:
                speed *= 1.06f;
                evasion *= 1.06f;
                defense *= 0.97f;
                break;
            case 1:
            case 3:
                accuracy *= 1.04f;
                attack *= 1.03f;
                break;
            case 2:
                hp *= 1.03f;
                defense *= 1.05f;
                break;
        }

        return new ThoughtMapGridBonus(attack, defense, hp, speed, evasion, accuracy, hate);
    }
}
