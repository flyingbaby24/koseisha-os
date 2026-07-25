using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

public sealed class ThoughtMapPersonalRepository : MonoBehaviour
{
    private const string DefaultBaseUrl = "https://koseisha-os.onrender.com";
    [SerializeField] private string baseUrl = DefaultBaseUrl;
    [SerializeField] private int timeoutSeconds = 20;
    public string DeckCachePath => Path.Combine(Application.persistentDataPath, "decks.json");
    public string HistoryCachePath => Path.Combine(Application.persistentDataPath, "battle_history.json");

    public IEnumerator GetDecks(string email, Action<PersonalDeckLibrary, bool> onSuccess)
    {
        string url = $"{BaseUrl}/users/{Escape(email)}/decks";
        yield return GetJson(url,
            json => onSuccess?.Invoke(Parse<PersonalDeckLibrary>(json) ?? LoadDeckCache(), false),
            _ => onSuccess?.Invoke(LoadDeckCache(), true));
    }

    public IEnumerator SaveDeck(string email, PersonalDeckRecord deck, bool saveAs, Action<bool> onComplete)
    {
        PersonalDeckLibrary cache = LoadDeckCache();
        int index = cache.decks.FindIndex(item => item.deckId == deck.deckId);
        if (index >= 0) cache.decks[index] = deck; else cache.decks.Add(deck);
        cache.lastUsedDeckId = deck.deckId;
        SaveDeckCache(cache);
        string url = $"{BaseUrl}/users/{Escape(email)}/decks";
        yield return SendJson(url, saveAs ? "POST" : "PUT", JsonUtility.ToJson(deck), success => onComplete?.Invoke(success));
    }

    public IEnumerator DeleteDeck(string email, string deckId, Action<bool> onComplete)
    {
        PersonalDeckLibrary cache = LoadDeckCache();
        cache.decks.RemoveAll(deck => deck.deckId == deckId);
        if (cache.lastUsedDeckId == deckId) cache.lastUsedDeckId = cache.decks.FirstOrDefault()?.deckId;
        SaveDeckCache(cache);
        yield return SendJson($"{BaseUrl}/users/{Escape(email)}/decks/{Escape(deckId)}", "DELETE", null, success => onComplete?.Invoke(success));
    }

    public IEnumerator GetProgress(string email, Action<PlayerProgressData, bool> onSuccess)
    {
        yield return GetJson($"{BaseUrl}/users/{Escape(email)}/player-progress",
            json => onSuccess?.Invoke(Parse<PlayerProgressData>(json) ?? new PlayerProgressRepository().Load(), false),
            _ => onSuccess?.Invoke(new PlayerProgressRepository().Load(), true));
    }

    public IEnumerator SaveProgress(string email, PlayerProgressData progress, Action<bool> onComplete)
    {
        yield return SendJson($"{BaseUrl}/users/{Escape(email)}/player-progress", "PUT", JsonUtility.ToJson(progress), success => onComplete?.Invoke(success));
    }

    public IEnumerator SaveFavorite(string email, string cardId, bool favorite, Action<bool> onComplete)
    {
        string body = $"{{\"cardId\":{Quote(cardId)},\"favorite\":{favorite.ToString().ToLowerInvariant()}}}";
        yield return SendJson($"{BaseUrl}/users/{Escape(email)}/favorites", "PUT", body, success => onComplete?.Invoke(success));
    }

    public IEnumerator SaveGeneratedSkill(string email, string cardId, GeneratedSkillDto skill, Action<bool> onComplete)
    {
        string body = $"{{\"cardId\":{Quote(cardId)},\"skill\":{JsonUtility.ToJson(skill)}}}";
        yield return SendJson($"{BaseUrl}/users/{Escape(email)}/generated-skills", "POST", body, success => onComplete?.Invoke(success));
    }

    public IEnumerator SaveBattleHistory(string email, BattleHistoryRecord record, Action<bool> onComplete)
    {
        BattleHistoryCollection cache = LoadHistoryCache();
        cache.items.RemoveAll(item => item.battleId == record.battleId);
        cache.items.Add(record);
        File.WriteAllText(HistoryCachePath, JsonUtility.ToJson(cache, true), new UTF8Encoding(false));
        yield return SendJson($"{BaseUrl}/users/{Escape(email)}/battle-history", "POST", JsonUtility.ToJson(record), success => onComplete?.Invoke(success));
    }

    public BattleStatisticsData CalculateStatistics()
    {
        List<BattleHistoryRecord> history = LoadHistoryCache().items.OrderBy(item => item.date).ToList();
        BattleStatisticsData result = new BattleStatisticsData();
        if (history.Count == 0) return result;
        result.battleCount = history.Count;
        result.winRate = history.Count(item => item.victory) / (float)history.Count;
        result.averageTurn = (float)history.Average(item => item.turn);
        result.averageDamage = (float)history.Average(item => item.damage);
        result.highestDamage = history.Max(item => item.damage);
        result.favoriteDeck = MostCommon(history.Select(item => item.deckId));
        result.mostUsedCard = MostCommon(history.SelectMany(item => item.cardIds ?? new List<string>()));
        result.mostUsedSkill = MostCommon(history.SelectMany(item => item.skillIds ?? new List<string>()));
        int streak = 0;
        foreach (BattleHistoryRecord item in history) { streak = item.victory ? streak + 1 : 0; result.longestWinStreak = Math.Max(result.longestWinStreak, streak); }
        return result;
    }

    public PersonalDeckLibrary LoadDeckCache()
    {
        try { return File.Exists(DeckCachePath) ? Parse<PersonalDeckLibrary>(File.ReadAllText(DeckCachePath)) ?? new PersonalDeckLibrary() : new PersonalDeckLibrary(); }
        catch { return new PersonalDeckLibrary(); }
    }
    public void SaveDeckCache(PersonalDeckLibrary library) => File.WriteAllText(DeckCachePath, JsonUtility.ToJson(library, true), new UTF8Encoding(false));
    public BattleHistoryCollection LoadHistoryCache()
    {
        try { return File.Exists(HistoryCachePath) ? Parse<BattleHistoryCollection>(File.ReadAllText(HistoryCachePath)) ?? new BattleHistoryCollection() : new BattleHistoryCollection(); }
        catch { return new BattleHistoryCollection(); }
    }

    private string BaseUrl => string.IsNullOrWhiteSpace(baseUrl) ? DefaultBaseUrl : baseUrl.TrimEnd('/');
    private IEnumerator GetJson(string url, Action<string> success, Action<string> failure)
    {
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            request.timeout = timeoutSeconds; yield return request.SendWebRequest();
            if (request.result == UnityWebRequest.Result.Success) success?.Invoke(request.downloadHandler.text); else failure?.Invoke(request.error);
        }
    }
    private IEnumerator SendJson(string url, string method, string json, Action<bool> complete)
    {
        using (UnityWebRequest request = new UnityWebRequest(url, method))
        {
            if (json != null) request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
            request.downloadHandler = new DownloadHandlerBuffer(); request.SetRequestHeader("Content-Type", "application/json"); request.timeout = timeoutSeconds;
            yield return request.SendWebRequest();
            bool online = request.result == UnityWebRequest.Result.Success;
            if (!online) Debug.LogWarning($"[PersonalRepository] Offline cache used. {method} {url} status={request.responseCode}");
            complete?.Invoke(online);
        }
    }
    private static T Parse<T>(string json) where T : class { try { return JsonUtility.FromJson<T>(json); } catch { return null; } }
    private static string Escape(string value) => UnityWebRequest.EscapeURL(value ?? "");
    private static string Quote(string value) => "\"" + (value ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    private static string MostCommon(IEnumerable<string> values) => values.Where(value => !string.IsNullOrWhiteSpace(value)).GroupBy(value => value).OrderByDescending(group => group.Count()).Select(group => group.Key).FirstOrDefault() ?? "";
}
