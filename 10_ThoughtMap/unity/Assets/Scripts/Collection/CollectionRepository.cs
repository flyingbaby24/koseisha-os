using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;

[Serializable]
public sealed class CollectionSaveData
{
    public List<string> favoriteCardIds = new List<string>();
    public List<SavedDocument> cachedDocuments = new List<SavedDocument>();
}

public sealed class CollectionCardEntry
{
    public string cardId;
    public ThoughtMapBattleCardData card;
    public SavedDocument document;
    public bool owned;
    public bool favorite;
    public string source;
}

public sealed class CollectionRepository
{
    private CollectionSaveData saveData;
    public string SavePath => Path.Combine(Application.persistentDataPath, "collection.json");

    public CollectionSaveData LoadSaveData()
    {
        if (saveData != null)
        {
            return saveData;
        }
        try
        {
            saveData = File.Exists(SavePath)
                ? JsonUtility.FromJson<CollectionSaveData>(File.ReadAllText(SavePath, Encoding.UTF8))
                : new CollectionSaveData();
        }
        catch (Exception exc)
        {
            Debug.LogError("[Collection] Could not load collection.json: " + exc.Message);
            saveData = new CollectionSaveData();
        }
        if (saveData == null) saveData = new CollectionSaveData();
        if (saveData.favoriteCardIds == null) saveData.favoriteCardIds = new List<string>();
        if (saveData.cachedDocuments == null) saveData.cachedDocuments = new List<SavedDocument>();
        return saveData;
    }

    public void MergePersonalLibrary(IEnumerable<SavedDocument> documents)
    {
        CollectionSaveData data = LoadSaveData();
        foreach (SavedDocument document in documents ?? Enumerable.Empty<SavedDocument>())
        {
            if (document == null || string.IsNullOrWhiteSpace(document.doc_id)) continue;
            int index = data.cachedDocuments.FindIndex(item => item != null && item.doc_id == document.doc_id);
            if (index >= 0) data.cachedDocuments[index] = document;
            else data.cachedDocuments.Add(document);
        }
        Save();
    }

    public void AddSearchResult(ThoughtMapSearchResult result)
    {
        if (result == null || string.IsNullOrWhiteSpace(result.doc_id)) return;
        SavedDocument document = new SavedDocument
        {
            doc_id = result.doc_id,
            title = result.title,
            source_title = result.title,
            author = result.author,
            source = result.source,
            url = result.url,
            parameters = result.parameters,
        };
        MergePersonalLibrary(new[] { document });
    }

    public void SetFavorite(string cardId, bool favorite)
    {
        CollectionSaveData data = LoadSaveData();
        data.favoriteCardIds.RemoveAll(id => id == cardId);
        if (favorite) data.favoriteCardIds.Add(cardId);
        Save();
    }

    public List<CollectionCardEntry> BuildEntries()
    {
        CollectionSaveData data = LoadSaveData();
        List<ThoughtMapBattleCardData> catalog = ThoughtMapCardsCsvLoader.LoadFromStreamingAssets("cards.csv");
        Dictionary<string, CollectionCardEntry> entries = catalog.ToDictionary(
            GetCardId,
            card => new CollectionCardEntry
            {
                cardId = GetCardId(card), card = card, owned = false, source = card.sourceTitle,
            });

        foreach (SavedDocument document in data.cachedDocuments.Where(document => document != null))
        {
            ThoughtMapBattleCardData card = ThoughtMapBattleCardFactory.FromSavedDocument(document, "collection");
            string id = GetCardId(card);
            entries[id] = new CollectionCardEntry
            {
                cardId = id, card = card, document = document, owned = true, source = document.source,
            };
        }

        PlayerProgressData progress = new PlayerProgressRepository().Load();
        foreach (string rareId in progress.rareCardIds ?? new List<string>())
        {
            if (entries.TryGetValue(rareId, out CollectionCardEntry existing)) existing.owned = true;
            else entries[rareId] = new CollectionCardEntry
            {
                cardId = rareId,
                card = new ThoughtMapBattleCardData { cardId = rareId, cardName = rareId, sourceTitle = "Rare Drop" },
                owned = true,
                source = "Rare Drop",
            };
        }

        foreach (CollectionCardEntry entry in entries.Values)
        {
            entry.favorite = data.favoriteCardIds.Contains(entry.cardId);
        }
        return entries.Values.ToList();
    }

    private void Save()
    {
        File.WriteAllText(SavePath, JsonUtility.ToJson(LoadSaveData(), true), new UTF8Encoding(false));
    }

    private static string GetCardId(ThoughtMapBattleCardData card)
    {
        if (card == null) return string.Empty;
        return !string.IsNullOrWhiteSpace(card.cardId) ? card.cardId : card.docId;
    }
}
