using System;
using System.Collections.Generic;

[Serializable] public sealed class PersonalDeckRecord
{
    public string deckId;
    public string name;
    public string updatedAt;
    public ThoughtMapBattleDeckConfig config = new ThoughtMapBattleDeckConfig();
}
[Serializable] public sealed class PersonalDeckLibrary
{
    public string lastUsedDeckId;
    public List<PersonalDeckRecord> decks = new List<PersonalDeckRecord>();
}
[Serializable] public sealed class BattleHistoryRecord
{
    public string battleId;
    public string date;
    public string deckId;
    public string stageId;
    public bool victory;
    public int turn;
    public string mvp;
    public int damage;
    public RewardData reward;
    public List<string> battleLog = new List<string>();
    public List<string> cardIds = new List<string>();
    public List<string> skillIds = new List<string>();
}
[Serializable] public sealed class BattleHistoryCollection { public List<BattleHistoryRecord> items = new List<BattleHistoryRecord>(); }
[Serializable] public sealed class BattleStatisticsData
{
    public int battleCount;
    public float winRate;
    public float averageTurn;
    public float averageDamage;
    public string favoriteDeck;
    public string mostUsedCard;
    public string mostUsedSkill;
    public int highestDamage;
    public int longestWinStreak;
}

public static class ThoughtMapPersonalSession
{
    private const string EmailKey = "thoughtmap.personal.email";
    public static string Email
    {
        get => UnityEngine.PlayerPrefs.GetString(EmailKey, "");
        set { UnityEngine.PlayerPrefs.SetString(EmailKey, value == null ? "" : value.Trim()); UnityEngine.PlayerPrefs.Save(); }
    }
}
