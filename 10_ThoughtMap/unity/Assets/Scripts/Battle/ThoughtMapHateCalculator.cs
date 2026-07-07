using System.Collections.Generic;
using System.Linq;

public class ThoughtMapHateCalculator
{
    public ThoughtMapBattleUnit SelectTarget(
        ThoughtMapBattleUnit attacker,
        List<ThoughtMapBattleUnit> enemies,
        int round,
        IReadOnlyList<string> log = null
    )
    {
        if (attacker == null || enemies == null)
        {
            return null;
        }

        ThoughtMapBattleUnit best = null;
        float bestScore = float.MinValue;
        foreach (ThoughtMapBattleUnit enemy in enemies.Where(unit => unit != null && unit.IsAlive))
        {
            float score = CalculateHate(attacker, enemy, round);
            if (score > bestScore)
            {
                best = enemy;
                bestScore = score;
            }
        }
        return best;
    }

    public float CalculateHate(ThoughtMapBattleUnit attacker, ThoughtMapBattleUnit target, int round)
    {
        ThoughtMapGridBonus bonus = ThoughtMapGridBonusCalculator.GetBonus(target.position, target.team);
        float lowHpPressure = 1f - ((float)target.hp / UnityEngine.Mathf.Max(1, target.maxHp));
        float distancePressure = 1f / (1f + attacker.position.ManhattanDistance(target.position));
        float threat = (target.card.statPhysicalAttack + target.card.statSkillAttack + target.card.statSpeed) / 300f;
        float seededNoise = ((target.card.raritySeed + target.card.skillSeed + round * 31) % 17) / 100f;
        return target.hate + bonus.hateMultiplier + lowHpPressure + distancePressure + threat + seededNoise;
    }
}
