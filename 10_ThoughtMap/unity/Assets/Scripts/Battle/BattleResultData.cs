using System;
using System.Collections.Generic;

[Serializable]
public sealed class BattleResultData
{
    public bool victory;
    public int turnCount;
    public List<UnitBattleResult> playerResults = new List<UnitBattleResult>();
    public List<UnitBattleResult> enemyResults = new List<UnitBattleResult>();
    public string mvpCardId;
    public string mvpUnitId;
    public float mvpScore;
    public BattleStatistics statistics = new BattleStatistics();
    public List<string> battleLog = new List<string>();
}

[Serializable]
public sealed class UnitBattleResult
{
    public string unitId;
    public string cardId;
    public string cardName;
    public int damageDealt;
    public int damageTaken;
    public int kills;
    public int skillCount;
    public bool survived;
    public float mvpScore;
}

[Serializable]
public sealed class BattleStatistics
{
    public int totalDamage;
    public int totalTurns;
    public int totalSkills;
    public int totalKills;
}

[Serializable]
public sealed class BattleResultScoreSettings
{
    public float damageWeight = 1f;
    public float killWeight = 100f;
    public float skillWeight = 30f;
}
