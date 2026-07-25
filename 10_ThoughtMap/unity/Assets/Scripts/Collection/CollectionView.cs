using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public sealed class CollectionView : MonoBehaviour
{
    private CollectionRepository repository;
    private GameObject overlay;
    private RectTransform listContent;
    private TMP_InputField searchInput;
    private TMP_Dropdown filterDropdown;
    private TMP_Dropdown sortDropdown;
    private TMP_Text detailText;
    private TMP_Text countText;
    private TMP_FontAsset font;
    private CollectionCardEntry selected;

    public void Build(CollectionRepository source)
    {
        repository = source;
        Canvas canvas = GetComponentInParent<Canvas>();
        font = UnityEngine.Object.FindObjectsByType<TMP_Text>(FindObjectsInactive.Include, FindObjectsSortMode.None)
            .Select(text => text.font).FirstOrDefault(asset => asset != null);
        RectTransform root = transform as RectTransform;
        root.anchorMin = Vector2.zero;
        root.anchorMax = Vector2.one;
        root.offsetMin = Vector2.zero;
        root.offsetMax = Vector2.zero;
        root.SetAsLastSibling();

        Button open = CreateButton(root, "OpenCollectionButton", "Collection", new Vector2(180f, 48f));
        RectTransform openRect = open.transform as RectTransform;
        openRect.anchorMin = openRect.anchorMax = new Vector2(1f, 1f);
        openRect.pivot = new Vector2(1f, 1f);
        openRect.anchoredPosition = new Vector2(-24f, -24f);
        open.onClick.AddListener(Open);

        overlay = CreateObject("CollectionOverlay", root, typeof(Image));
        RectTransform overlayRect = overlay.GetComponent<RectTransform>();
        overlayRect.anchorMin = Vector2.zero;
        overlayRect.anchorMax = Vector2.one;
        overlayRect.offsetMin = Vector2.zero;
        overlayRect.offsetMax = Vector2.zero;
        overlay.GetComponent<Image>().color = new Color(0.005f, 0.025f, 0.045f, 0.98f);
        BuildHeader(overlayRect);
        BuildBody(overlayRect);
        overlay.SetActive(false);
    }

    public void Refresh()
    {
        if (overlay != null && overlay.activeSelf) Render();
    }

    private void Open()
    {
        overlay.SetActive(true);
        overlay.transform.SetAsLastSibling();
        Render();
    }

    private void BuildHeader(RectTransform parent)
    {
        GameObject header = CreateObject("Header", parent, typeof(HorizontalLayoutGroup));
        RectTransform rect = header.GetComponent<RectTransform>();
        rect.anchorMin = new Vector2(0.03f, 0.9f);
        rect.anchorMax = new Vector2(0.97f, 0.98f);
        rect.offsetMin = rect.offsetMax = Vector2.zero;
        HorizontalLayoutGroup layout = header.GetComponent<HorizontalLayoutGroup>();
        layout.spacing = 14f;
        layout.childAlignment = TextAnchor.MiddleLeft;
        layout.childControlWidth = false;
        layout.childControlHeight = true;

        TMP_Text title = CreateText(header.transform, "Title", "Research Collection", 32, TextAlignmentOptions.Left);
        SetWidth(title.gameObject, 310f);
        countText = CreateText(header.transform, "Count", "", 18, TextAlignmentOptions.Left);
        SetWidth(countText.gameObject, 180f);
        searchInput = CreateInput(header.transform, "Collection Search", 300f);
        searchInput.onValueChanged.AddListener(_ => Render());
        filterDropdown = CreateDropdown(header.transform, new[] { "All", "Owned", "Unowned", "Favorite", "Recently Added", "Recently Used" }, 170f);
        filterDropdown.onValueChanged.AddListener(_ => Render());
        sortDropdown = CreateDropdown(header.transform, new[] { "Name", "Rarity", "Source" }, 150f);
        sortDropdown.onValueChanged.AddListener(_ => Render());
        Button close = CreateButton(header.transform, "Close", "Close", new Vector2(120f, 46f));
        close.onClick.AddListener(() => overlay.SetActive(false));
    }

    private void BuildBody(RectTransform parent)
    {
        GameObject listPanel = CreateObject("CollectionList", parent, typeof(Image));
        RectTransform listRect = listPanel.GetComponent<RectTransform>();
        listRect.anchorMin = new Vector2(0.03f, 0.05f);
        listRect.anchorMax = new Vector2(0.49f, 0.88f);
        listRect.offsetMin = listRect.offsetMax = Vector2.zero;
        listPanel.GetComponent<Image>().color = new Color(0.01f, 0.08f, 0.12f, 0.96f);
        GameObject scrollObject = CreateObject("Scroll", listRect, typeof(ScrollRect));
        RectTransform scrollRect = scrollObject.GetComponent<RectTransform>();
        scrollRect.anchorMin = Vector2.zero; scrollRect.anchorMax = Vector2.one;
        scrollRect.offsetMin = new Vector2(10f, 10f); scrollRect.offsetMax = new Vector2(-10f, -10f);
        GameObject viewport = CreateObject("Viewport", scrollRect, typeof(Image), typeof(Mask));
        RectTransform viewportRect = viewport.GetComponent<RectTransform>();
        viewportRect.anchorMin = Vector2.zero; viewportRect.anchorMax = Vector2.one;
        viewportRect.offsetMin = viewportRect.offsetMax = Vector2.zero;
        viewport.GetComponent<Image>().color = new Color(0f, 0f, 0f, 0.01f);
        viewport.GetComponent<Mask>().showMaskGraphic = false;
        GameObject content = CreateObject("Content", viewportRect, typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));
        listContent = content.GetComponent<RectTransform>();
        listContent.anchorMin = new Vector2(0f, 1f); listContent.anchorMax = new Vector2(1f, 1f); listContent.pivot = new Vector2(0.5f, 1f);
        listContent.sizeDelta = Vector2.zero;
        VerticalLayoutGroup contentLayout = content.GetComponent<VerticalLayoutGroup>();
        contentLayout.spacing = 5f; contentLayout.childControlWidth = true; contentLayout.childControlHeight = true; contentLayout.childForceExpandHeight = false;
        content.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        ScrollRect scroll = scrollObject.GetComponent<ScrollRect>();
        scroll.viewport = viewportRect; scroll.content = listContent; scroll.horizontal = false;

        GameObject detail = CreateObject("DocumentDetail", parent, typeof(Image));
        RectTransform detailRect = detail.GetComponent<RectTransform>();
        detailRect.anchorMin = new Vector2(0.51f, 0.05f); detailRect.anchorMax = new Vector2(0.97f, 0.88f);
        detailRect.offsetMin = detailRect.offsetMax = Vector2.zero;
        detail.GetComponent<Image>().color = new Color(0.012f, 0.065f, 0.1f, 0.98f);
        detailText = CreateText(detailRect, "DetailText", "Select a card.", 20, TextAlignmentOptions.TopLeft);
        detailText.enableWordWrapping = true;
        detailText.overflowMode = TextOverflowModes.Overflow;
        detailText.rectTransform.anchorMin = new Vector2(0.04f, 0.12f); detailText.rectTransform.anchorMax = new Vector2(0.96f, 0.96f);
        detailText.rectTransform.offsetMin = detailText.rectTransform.offsetMax = Vector2.zero;
        Button favorite = CreateButton(detailRect, "FavoriteButton", "Toggle Favorite", new Vector2(220f, 48f));
        RectTransform favoriteRect = favorite.transform as RectTransform;
        favoriteRect.anchorMin = favoriteRect.anchorMax = new Vector2(0.5f, 0.04f); favoriteRect.pivot = new Vector2(0.5f, 0f);
        favorite.onClick.AddListener(ToggleFavorite);
    }

    private void Render()
    {
        if (repository == null || listContent == null) return;
        foreach (Transform child in listContent) Destroy(child.gameObject);
        List<CollectionCardEntry> all = repository.BuildEntries();
        IEnumerable<CollectionCardEntry> query = all;
        string text = searchInput == null ? "" : searchInput.text.Trim();
        if (!string.IsNullOrWhiteSpace(text)) query = query.Where(entry => Contains(entry.card.cardName, text) || Contains(entry.card.author, text) || Contains(entry.source, text));
        string filter = filterDropdown.options[filterDropdown.value].text;
        if (filter == "Owned") query = query.Where(entry => entry.owned);
        else if (filter == "Unowned") query = query.Where(entry => !entry.owned);
        else if (filter == "Favorite") query = query.Where(entry => entry.favorite);
        else if (filter == "Recently Added") query = query.Where(entry => entry.owned).Take(30);
        else if (filter == "Recently Used")
        {
            ThoughtMapPersonalRepository personal = GetComponentInParent<ThoughtMapPersonalRepository>();
            HashSet<string> used = new HashSet<string>((personal == null ? new BattleHistoryCollection() : personal.LoadHistoryCache()).items
                .OrderByDescending(item => item.date).Take(10).SelectMany(item => item.cardIds ?? new List<string>()));
            query = query.Where(entry => used.Contains(entry.cardId));
        }
        string sort = sortDropdown.options[sortDropdown.value].text;
        query = sort == "Rarity" ? query.OrderByDescending(entry => entry.card.raritySeed)
            : sort == "Source" ? query.OrderBy(entry => entry.source).ThenBy(entry => entry.card.cardName)
            : query.OrderBy(entry => entry.card.cardName);
        List<CollectionCardEntry> shown = query.ToList();
        countText.text = $"Owned {all.Count(entry => entry.owned)} / {all.Count}";
        foreach (CollectionCardEntry entry in shown)
        {
            Button row = CreateButton(listContent, "Card_" + entry.cardId, $"{(entry.favorite ? "★" : " ")} {(entry.owned ? "Owned" : "Locked")}  {entry.card.cardName}", new Vector2(0f, 48f));
            SetHeight(row.gameObject, 48f);
            row.onClick.AddListener(() => Select(entry, all));
        }
    }

    private void Select(CollectionCardEntry entry, List<CollectionCardEntry> all)
    {
        selected = entry;
        StringBuilder builder = new StringBuilder();
        builder.AppendLine(entry.card.cardName);
        builder.AppendLine($"{entry.card.author} / {entry.source}");
        builder.AppendLine(entry.owned ? "Owned" : "Not Owned");
        builder.AppendLine(entry.favorite ? "Favorite ★" : "Favorite ☆");
        builder.AppendLine();
        builder.AppendLine("ThoughtMap Analysis");
        foreach (KeyValuePair<string, float> score in entry.card.parameterScores.OrderByDescending(pair => pair.Value)) builder.AppendLine($"{score.Key}: {score.Value:0.##}");
        if (entry.document != null && !string.IsNullOrWhiteSpace(entry.document.summary)) builder.AppendLine("\n" + entry.document.summary);
        builder.AppendLine("\nSimilar Works");
        foreach (CollectionCardEntry similar in all.Where(other => other != entry).OrderByDescending(other => Similarity(entry.card, other.card)).Take(5))
            builder.AppendLine($"{similar.card.cardName}  {Similarity(entry.card, similar.card):P0}");
        builder.AppendLine("\nResearch Progress");
        List<CollectionCardEntry> owned = all.Where(item => item.owned).ToList();
        foreach (string category in new[] { "philosophy", "psychology", "economy", "science" })
        {
            float value = owned.Count == 0 ? 0f : owned.Average(item => item.card.parameterScores.TryGetValue(category, out float score) ? score : 0f);
            builder.AppendLine($"{char.ToUpperInvariant(category[0]) + category.Substring(1)}  {Mathf.Clamp01(value) * 100f:0}%");
        }
        ThoughtMapPersonalRepository personal = GetComponentInParent<ThoughtMapPersonalRepository>();
        if (personal != null)
        {
            BattleStatisticsData stats = personal.CalculateStatistics();
            builder.AppendLine("\nBattle Statistics");
            builder.AppendLine($"Battles {stats.battleCount} / Win Rate {stats.winRate:P0} / Average Turn {stats.averageTurn:0.0}");
            builder.AppendLine($"Highest Damage {stats.highestDamage} / Favorite Deck {stats.favoriteDeck}");
        }
        detailText.text = builder.ToString();
    }

    private void ToggleFavorite()
    {
        if (selected == null) return;
        selected.favorite = !selected.favorite;
        repository.SetFavorite(selected.cardId, selected.favorite);
        ThoughtMapPersonalRepository personal = GetComponentInParent<ThoughtMapPersonalRepository>();
        if (personal != null && !string.IsNullOrWhiteSpace(ThoughtMapPersonalSession.Email))
            StartCoroutine(personal.SaveFavorite(ThoughtMapPersonalSession.Email, selected.cardId, selected.favorite, null));
        Select(selected, repository.BuildEntries());
        Render();
    }

    private static float Similarity(ThoughtMapBattleCardData a, ThoughtMapBattleCardData b) => new ThoughtMapParameterSimilarityProvider().GetSimilarity(a, b);
    private static bool Contains(string source, string value) => !string.IsNullOrWhiteSpace(source) && source.IndexOf(value, StringComparison.OrdinalIgnoreCase) >= 0;

    private TMP_Text CreateText(Transform parent, string name, string value, float size, TextAlignmentOptions alignment)
    {
        GameObject target = CreateObject(name, parent, typeof(CanvasRenderer), typeof(TextMeshProUGUI), typeof(LayoutElement));
        TMP_Text result = target.GetComponent<TMP_Text>(); result.text = value; result.font = font; result.fontSize = size; result.color = Color.white; result.alignment = alignment; result.raycastTarget = false; return result;
    }
    private TMP_InputField CreateInput(Transform parent, string placeholder, float width)
    {
        GameObject root = CreateObject("SearchInput", parent, typeof(Image), typeof(TMP_InputField), typeof(LayoutElement)); SetWidth(root, width); root.GetComponent<Image>().color = new Color(0.03f, 0.16f, 0.22f);
        TMP_Text text = CreateText(root.transform, "Text", "", 18, TextAlignmentOptions.Left); text.rectTransform.anchorMin = Vector2.zero; text.rectTransform.anchorMax = Vector2.one; text.rectTransform.offsetMin = new Vector2(12, 4); text.rectTransform.offsetMax = new Vector2(-12, -4);
        TMP_Text hint = CreateText(root.transform, "Placeholder", placeholder, 18, TextAlignmentOptions.Left); hint.color = new Color(0.5f, 0.6f, 0.65f); hint.rectTransform.anchorMin = Vector2.zero; hint.rectTransform.anchorMax = Vector2.one; hint.rectTransform.offsetMin = new Vector2(12, 4); hint.rectTransform.offsetMax = new Vector2(-12, -4);
        TMP_InputField input = root.GetComponent<TMP_InputField>(); input.textComponent = text; input.placeholder = hint; return input;
    }
    private TMP_Dropdown CreateDropdown(Transform parent, string[] options, float width)
    {
        GameObject root = CreateObject("Dropdown", parent, typeof(Image), typeof(TMP_Dropdown), typeof(LayoutElement)); SetWidth(root, width); root.GetComponent<Image>().color = new Color(0.03f, 0.16f, 0.22f);
        TMP_Text label = CreateText(root.transform, "Label", options[0], 17, TextAlignmentOptions.Center); label.rectTransform.anchorMin = Vector2.zero; label.rectTransform.anchorMax = Vector2.one; label.rectTransform.offsetMin = label.rectTransform.offsetMax = Vector2.zero;
        TMP_Dropdown dropdown = root.GetComponent<TMP_Dropdown>(); dropdown.captionText = label; dropdown.options = options.Select(option => new TMP_Dropdown.OptionData(option)).ToList(); return dropdown;
    }
    private Button CreateButton(Transform parent, string name, string label, Vector2 size)
    {
        GameObject target = CreateObject(name, parent, typeof(Image), typeof(Button), typeof(LayoutElement)); target.GetComponent<Image>().color = new Color(0.025f, 0.28f, 0.4f, 0.96f); target.GetComponent<RectTransform>().sizeDelta = size;
        TMP_Text text = CreateText(target.transform, "Label", label, 18, TextAlignmentOptions.Center); text.rectTransform.anchorMin = Vector2.zero; text.rectTransform.anchorMax = Vector2.one; text.rectTransform.offsetMin = text.rectTransform.offsetMax = Vector2.zero;
        return target.GetComponent<Button>();
    }
    private static GameObject CreateObject(string name, Transform parent, params Type[] components) { List<Type> types = new List<Type>{typeof(RectTransform)}; types.AddRange(components); GameObject target = new GameObject(name, types.ToArray()); target.transform.SetParent(parent, false); return target; }
    private static void SetWidth(GameObject target, float width) { LayoutElement e = target.GetComponent<LayoutElement>() ?? target.AddComponent<LayoutElement>(); e.preferredWidth = width; }
    private static void SetHeight(GameObject target, float height) { LayoutElement e = target.GetComponent<LayoutElement>() ?? target.AddComponent<LayoutElement>(); e.preferredHeight = height; }
}
