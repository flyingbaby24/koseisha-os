using System;
using System.Collections;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public sealed class DeckLibraryManager : MonoBehaviour
{
    private ProductBattlePrepPanelView prep;
    private ThoughtMapPersonalRepository repository;
    private PersonalDeckLibrary library = new PersonalDeckLibrary();
    private TMP_InputField nameInput;
    private TMP_Text stateText;
    private int selectedIndex = -1;

    private void Awake()
    {
        prep = GetComponent<ProductBattlePrepPanelView>();
        repository = GetComponent<ThoughtMapPersonalRepository>() ?? gameObject.AddComponent<ThoughtMapPersonalRepository>();
        BuildView();
    }

    private IEnumerator Start()
    {
        yield return null;
        yield return repository.GetDecks(ThoughtMapPersonalSession.Email, HandleLoaded);
    }

    private void HandleLoaded(PersonalDeckLibrary value, bool cacheUsed)
    {
        library = value ?? new PersonalDeckLibrary();
        selectedIndex = library.decks.FindIndex(deck => deck.deckId == library.lastUsedDeckId);
        if (selectedIndex < 0 && library.decks.Count > 0) selectedIndex = 0;
        RefreshLabel(cacheUsed ? "Offline cache" : "Personal synced");
        RestoreLastUsedDeck();
    }

    public void RestoreLastUsedDeck()
    {
        if (selectedIndex >= 0) prep.ApplyDeckConfig(library.decks[selectedIndex].config);
    }

    public void SyncCurrentDeck()
    {
        if (Selected != null) SaveSelected();
    }

    private void SelectOffset(int offset)
    {
        if (library.decks.Count == 0) return;
        selectedIndex = (selectedIndex + offset + library.decks.Count) % library.decks.Count;
        nameInput.text = library.decks[selectedIndex].name;
        RefreshLabel("Selected");
    }

    private void LoadSelected()
    {
        PersonalDeckRecord deck = Selected;
        if (deck == null) return;
        if (prep.ApplyDeckConfig(deck.config))
        {
            library.lastUsedDeckId = deck.deckId;
            repository.SaveDeckCache(library);
            prep.SaveDeckJson();
            RefreshLabel("Loaded");
        }
    }

    private void SaveSelected()
    {
        if (Selected == null) { SaveAs(); return; }
        Selected.name = CleanName(nameInput.text, Selected.name);
        Selected.updatedAt = DateTime.UtcNow.ToString("o");
        Selected.config = prep.BuildCurrentDeckConfig();
        StartCoroutine(repository.SaveDeck(CurrentEmail, Selected, false, online => RefreshLabel(online ? "Saved" : "Saved to cache")));
    }

    private void SaveAs()
    {
        PersonalDeckRecord deck = new PersonalDeckRecord
        {
            deckId = Guid.NewGuid().ToString("N"),
            name = CleanName(nameInput.text, $"Deck {library.decks.Count + 1}"),
            updatedAt = DateTime.UtcNow.ToString("o"),
            config = prep.BuildCurrentDeckConfig()
        };
        library.decks.Add(deck);
        selectedIndex = library.decks.Count - 1;
        StartCoroutine(repository.SaveDeck(CurrentEmail, deck, true, online => RefreshLabel(online ? "Created" : "Created in cache")));
    }

    private void Rename()
    {
        if (Selected == null) return;
        Selected.name = CleanName(nameInput.text, Selected.name);
        Selected.updatedAt = DateTime.UtcNow.ToString("o");
        StartCoroutine(repository.SaveDeck(CurrentEmail, Selected, false, online => RefreshLabel(online ? "Renamed" : "Renamed in cache")));
    }

    private void Duplicate()
    {
        if (Selected == null) return;
        nameInput.text = Selected.name + " Copy";
        PersonalDeckRecord source = Selected;
        PersonalDeckRecord copy = new PersonalDeckRecord
        {
            deckId = Guid.NewGuid().ToString("N"),
            name = nameInput.text,
            updatedAt = DateTime.UtcNow.ToString("o"),
            config = JsonUtility.FromJson<ThoughtMapBattleDeckConfig>(JsonUtility.ToJson(source.config))
        };
        library.decks.Add(copy);
        selectedIndex = library.decks.Count - 1;
        StartCoroutine(repository.SaveDeck(CurrentEmail, copy, true, online => RefreshLabel(online ? "Duplicated" : "Duplicated in cache")));
    }

    private void DeleteSelected()
    {
        PersonalDeckRecord deck = Selected;
        if (deck == null) return;
        library.decks.RemoveAt(selectedIndex);
        selectedIndex = library.decks.Count == 0 ? -1 : Mathf.Clamp(selectedIndex, 0, library.decks.Count - 1);
        StartCoroutine(repository.DeleteDeck(CurrentEmail, deck.deckId, online => RefreshLabel(online ? "Deleted" : "Deleted from cache")));
    }

    private PersonalDeckRecord Selected => selectedIndex >= 0 && selectedIndex < library.decks.Count ? library.decks[selectedIndex] : null;
    private string CurrentEmail => string.IsNullOrWhiteSpace(prep.PersonalEmail) ? ThoughtMapPersonalSession.Email : prep.PersonalEmail;

    private void RefreshLabel(string status)
    {
        PersonalDeckRecord deck = Selected;
        if (nameInput != null && deck != null) nameInput.text = deck.name;
        if (stateText != null) stateText.text = $"Deck {Mathf.Max(0, selectedIndex + 1)}/{library.decks.Count}  {status}";
    }

    private void BuildView()
    {
        TMP_FontAsset font = FindObjectsByType<TMP_Text>(FindObjectsInactive.Include, FindObjectsSortMode.None).Select(item => item.font).FirstOrDefault(item => item != null);
        GameObject root = new GameObject("DeckLibrary", typeof(RectTransform), typeof(Image), typeof(HorizontalLayoutGroup));
        root.transform.SetParent(transform, false);
        RectTransform rect = root.GetComponent<RectTransform>();
        rect.anchorMin = new Vector2(0.18f, 0.935f); rect.anchorMax = new Vector2(0.82f, 0.995f); rect.offsetMin = rect.offsetMax = Vector2.zero;
        root.GetComponent<Image>().color = new Color(0.01f, 0.07f, 0.1f, 0.94f);
        HorizontalLayoutGroup layout = root.GetComponent<HorizontalLayoutGroup>(); layout.spacing = 5; layout.padding = new RectOffset(8, 8, 5, 5); layout.childControlHeight = true; layout.childForceExpandHeight = true; layout.childForceExpandWidth = false;
        MakeText(root.transform, "Deck", font, 16, 50);
        MakeButton(root.transform, "<", font, 42, () => SelectOffset(-1));
        nameInput = MakeInput(root.transform, font, 190);
        MakeButton(root.transform, ">", font, 42, () => SelectOffset(1));
        MakeButton(root.transform, "Load", font, 66, LoadSelected);
        MakeButton(root.transform, "Save", font, 66, SaveSelected);
        MakeButton(root.transform, "Save As", font, 82, SaveAs);
        MakeButton(root.transform, "Rename", font, 78, Rename);
        MakeButton(root.transform, "Duplicate", font, 92, Duplicate);
        MakeButton(root.transform, "Delete", font, 70, DeleteSelected);
        stateText = MakeText(root.transform, "", font, 14, 170);
    }

    private static TMP_Text MakeText(Transform parent, string value, TMP_FontAsset font, float size, float width)
    {
        GameObject go = new GameObject("Text", typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI), typeof(LayoutElement)); go.transform.SetParent(parent, false);
        TMP_Text text = go.GetComponent<TMP_Text>(); text.text = value; text.font = font; text.fontSize = size; text.color = Color.white; text.alignment = TextAlignmentOptions.Center; text.raycastTarget = false;
        go.GetComponent<LayoutElement>().preferredWidth = width; return text;
    }
    private static void MakeButton(Transform parent, string label, TMP_FontAsset font, float width, UnityEngine.Events.UnityAction action)
    {
        GameObject go = new GameObject(label, typeof(RectTransform), typeof(Image), typeof(Button), typeof(LayoutElement)); go.transform.SetParent(parent, false); go.GetComponent<Image>().color = new Color(0.02f, 0.25f, 0.34f); go.GetComponent<LayoutElement>().preferredWidth = width;
        TMP_Text text = MakeText(go.transform, label, font, 14, width); RectTransform tr = text.rectTransform; tr.anchorMin = Vector2.zero; tr.anchorMax = Vector2.one; tr.offsetMin = tr.offsetMax = Vector2.zero; go.GetComponent<Button>().onClick.AddListener(action);
    }
    private static TMP_InputField MakeInput(Transform parent, TMP_FontAsset font, float width)
    {
        GameObject go = new GameObject("DeckName", typeof(RectTransform), typeof(Image), typeof(TMP_InputField), typeof(LayoutElement)); go.transform.SetParent(parent, false); go.GetComponent<Image>().color = new Color(0.025f, 0.14f, 0.18f); go.GetComponent<LayoutElement>().preferredWidth = width;
        TMP_Text text = MakeText(go.transform, "", font, 15, width); RectTransform tr = text.rectTransform; tr.anchorMin = Vector2.zero; tr.anchorMax = Vector2.one; tr.offsetMin = new Vector2(8, 2); tr.offsetMax = new Vector2(-8, -2); TMP_InputField input = go.GetComponent<TMP_InputField>(); input.textComponent = text; return input;
    }
    private static string CleanName(string value, string fallback) => string.IsNullOrWhiteSpace(value) ? fallback : value.Trim();
}
