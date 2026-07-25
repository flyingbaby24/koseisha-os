using System;
using System.IO;
using System.Linq;
using UnityEngine;

internal static class StreamingJsonLoader
{
    public static T Load<T>(string fileName) where T : new()
    {
        string path = Path.Combine(Application.streamingAssetsPath, fileName);
        if (!File.Exists(path))
        {
            Debug.LogError($"[Content] JSON not found: {path}");
            return new T();
        }
        try
        {
            return JsonUtility.FromJson<T>(File.ReadAllText(path)) ?? new T();
        }
        catch (Exception exc)
        {
            Debug.LogError($"[Content] Could not load {fileName}: {exc.Message}");
            return new T();
        }
    }
}

public static class EnemyDeckLoader
{
    public static EnemyDeckData Load(string deckId)
    {
        EnemyDeckCollection data = StreamingJsonLoader.Load<EnemyDeckCollection>("enemy_decks.json");
        return data.decks.FirstOrDefault(deck => deck != null && deck.deckId == deckId);
    }
}

public static class RewardTableLoader
{
    public static RewardTableData Load(string tableId)
    {
        RewardTableCollection data = StreamingJsonLoader.Load<RewardTableCollection>("reward_table.json");
        return data.tables.FirstOrDefault(table => table != null && table.tableId == tableId);
    }
}

public static class DropTableLoader
{
    public static DropTableData Load(string tableId)
    {
        DropTableCollection data = StreamingJsonLoader.Load<DropTableCollection>("drop_table.json");
        return data.tables.FirstOrDefault(table => table != null && table.tableId == tableId);
    }
}

public static class SkillPoolLoader
{
    public static SkillPoolData Load(string poolId)
    {
        SkillPoolCollection data = StreamingJsonLoader.Load<SkillPoolCollection>("skill_pool.json");
        return data.pools.FirstOrDefault(pool => pool != null && pool.poolId == poolId);
    }
}
