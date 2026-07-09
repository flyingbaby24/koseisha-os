using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

public class ProductBattlePrepPanelView : MonoBehaviour
{
    private const float LightweightRowHeight = 38f;
    private const float LightweightRowSpacing = 4f;

    [Header("Input")]
    [SerializeField] private TextAsset cardsCsvAsset;
    [SerializeField] private string streamingAssetsCsvPath = "cards.csv";
    [SerializeField] private string deckFileName = "deck.json";
    [SerializeField] private string battleSceneName = "BattleScene";
    [SerializeField] private bool loadCardsOnStart = true;
    [SerializeField] private bool autoFillDeckOnLoad;

    [Header("Prefabs")]
    [SerializeField] private ProductBattleCardListRowView cardListRowPrefab;
    [SerializeField] private ProductBattleCardListRowView deckListRowPrefab;
    [SerializeField] private ProductBattleGridCellView gridCellPrefab;

    [Header("Scene References")]
    [SerializeField] private Transform cardListContent;
    [SerializeField] private Transform deckListContent;
    [SerializeField] private Transform formationGridContent;
    [SerializeField] private ProductBattleCardDetailPanelView cardDetailPanel;
    [SerializeField] private ProductBattleLogPanelView debugLogPanel;
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private Button loadCardsButton;
    [SerializeField] private Button addToDeckButton;
    [SerializeField] private Button saveDeckButton;
    [SerializeField] private Button startBattleButton;
    [SerializeField] private Button simulateButton;
    [SerializeField] private Button clearButton;

    [Header("Sprites")]
    [SerializeField] private Sprite defaultCardArt;
    [SerializeField] private Sprite defaultAttributeIcon;
    [SerializeField] private Sprite[] cardArtPool;
    [SerializeField] private AttributeSpriteMap[] attributeSprites;

    [Header("Rules")]
    [SerializeField] private int deckLimit = 10;
    [SerializeField] private int deployLimit = 5;
    [SerializeField] private int cardListRenderLimit = 60;
    [SerializeField] private int playerRows = 3;

    private readonly List<ThoughtMapBattleCardData> loadedCards = new List<ThoughtMapBattleCardData>();
    private readonly List<ThoughtMapBattleCardData> deckCards = new List<ThoughtMapBattleCardData>();
    private readonly Dictionary<int, ThoughtMapBattleCardData> placement = new Dictionary<int, ThoughtMapBattleCardData>();
    private readonly List<ProductBattleGridCellView> gridCells = new List<ProductBattleGridCellView>();
    private int selectedDeckIndex = -1;
    private int selectedLibraryIndex = -1;

    private void Awake()
    {
        WireButtons();
        EnsureListContentReferences();
        if (cardListContent != null)
        {
            NormalizeLightweightListScrollArea(cardListContent);
        }
        else
        {
            WarnMissingListContent("Card List", "CardListPanel/Viewport/Content");
        }

        if (deckListContent != null)
        {
            NormalizeLightweightListScrollArea(deckListContent);
        }
        else
        {
            WarnMissingListContent("Deck 10", "DeckListPanel/Viewport/Content");
        }
        CollectSceneGridCells();
        RenderGrid();
        cardDetailPanel?.Clear();
    }

    private void Start()
    {
        if (loadCardsOnStart)
        {
            LoadCards();
        }
    }

    private void WireButtons()
    {
        AddClick(loadCardsButton, LoadCards);
        AddClick(addToDeckButton, AddSelectedCardToDeck);
        AddClick(saveDeckButton, SaveDeckJson);
        AddClick(startBattleButton, StartBattleScene);
        AddClick(simulateButton, SimulatePreview);
        AddClick(clearButton, ClearPlacement);
    }

    [ContextMenu("Load Cards")]
    public void LoadCards()
    {
        loadedCards.Clear();
        deckCards.Clear();
        placement.Clear();
        selectedDeckIndex = -1;
        selectedLibraryIndex = -1;

        try
        {
            List<ThoughtMapBattleCardData> cards = cardsCsvAsset != null
                ? ThoughtMapCardsCsvLoader.LoadFromText(cardsCsvAsset.text)
                : ThoughtMapCardsCsvLoader.LoadFromStreamingAssets(streamingAssetsCsvPath);

            loadedCards.AddRange(cards);
            if (autoFillDeckOnLoad)
            {
                deckCards.AddRange(cards.Take(deckLimit));
            }
            string spriteWarning = GetSpriteWarning();
            WriteStatus(string.IsNullOrEmpty(spriteWarning)
                ? $"Loaded {loadedCards.Count} cards. Select a card, then Add to Deck."
                : $"{spriteWarning}. Loaded {loadedCards.Count} cards.");
        }
        catch (System.Exception exc)
        {
            WriteStatus("Could not load cards.csv: " + exc.Message);
        }

        RenderAll();
    }

    public void ClearPlacement()
    {
        placement.Clear();
        selectedDeckIndex = -1;
        selectedLibraryIndex = -1;
        RenderAll();
        WriteStatus("Cleared formation.");
    }

    public void AddSelectedCardToDeck()
    {
        if (selectedLibraryIndex < 0 || selectedLibraryIndex >= loadedCards.Count)
        {
            WriteStatus("Select a Card List card first.");
            return;
        }

        ThoughtMapBattleCardData selected = loadedCards[selectedLibraryIndex];
        int existingIndex = deckCards.IndexOf(selected);
        if (existingIndex >= 0)
        {
            selectedDeckIndex = existingIndex;
            selectedLibraryIndex = -1;
            RenderAll();
            WriteStatus($"Card already in Deck as P{existingIndex + 1}.");
            return;
        }

        if (deckCards.Count >= deckLimit)
        {
            WriteStatus($"Deck limit is {deckLimit}. Remove a deck card before adding another.");
            return;
        }

        deckCards.Add(selected);
        selectedDeckIndex = deckCards.Count - 1;
        selectedLibraryIndex = -1;
        RenderAll();
        WriteStatus($"Added P{selectedDeckIndex + 1} to Deck.");
    }

    private void RenderAll()
    {
        RenderCardLibrary();
        RenderDeck();
        RenderGrid();
        ShowSelectedDetail();
    }

    private void RenderCardLibrary()
    {
        if (cardListContent == null)
        {
            EnsureListContentReferences();
        }
        if (cardListContent == null)
        {
            WarnMissingListContent("Card List", "CardListPanel/Viewport/Content");
            return;
        }

        ScrollRect scroll = GetScrollRectForContent(cardListContent);
        float scrollPosition = scroll == null ? 1f : scroll.verticalNormalizedPosition;
        NormalizeLightweightListScrollArea(cardListContent);
        ClearChildren(cardListContent);

        int count = Mathf.Min(loadedCards.Count, cardListRenderLimit);
        for (int i = 0; i < count; i++)
        {
            ProductBattleCardListRowView view = CreateListRow(cardListContent, cardListRowPrefab, "CardListRow");
            string state = deckCards.Contains(loadedCards[i]) ? "In Deck" : "";
            view.Bind(loadedCards[i], i, GetCardId(loadedCards[i]), i == selectedLibraryIndex, deckCards.Contains(loadedCards[i]), state);
            view.SetClickHandler(OnLibraryCardClicked);
        }
        RestoreScrollPosition(scroll, scrollPosition);
    }

    private void RenderDeck()
    {
        if (deckListContent == null)
        {
            EnsureListContentReferences();
        }
        if (deckListContent == null)
        {
            WarnMissingListContent("Deck 10", "DeckListPanel/Viewport/Content");
            return;
        }

        ScrollRect scroll = GetScrollRectForContent(deckListContent);
        float scrollPosition = scroll == null ? 1f : scroll.verticalNormalizedPosition;
        NormalizeLightweightListScrollArea(deckListContent);
        ClearChildren(deckListContent);

        for (int i = 0; i < deckCards.Count; i++)
        {
            ProductBattleCardListRowView view = CreateListRow(deckListContent, deckListRowPrefab, "DeckListRow");
            string state = placement.ContainsValue(deckCards[i]) ? "Placed" : "Ready";
            view.Bind(deckCards[i], i, $"P{i + 1}", i == selectedDeckIndex, placement.ContainsValue(deckCards[i]), state);
            view.SetClickHandler(OnDeckCardClicked);
        }
        RestoreScrollPosition(scroll, scrollPosition);
    }

    private void RenderGrid()
    {
        EnsureGridCells();
        for (int index = 0; index < gridCells.Count; index++)
        {
            int x = index % 5;
            int y = index / 5;
            bool available = y < playerRows;
            if (placement.TryGetValue(index, out ThoughtMapBattleCardData card))
            {
                int deckIndex = deckCards.IndexOf(card);
                gridCells[index].BindCard(x, y, card, $"P{deckIndex + 1}", ResolveCardArt(deckIndex), ResolveAttributeIcon(card));
            }
            else
            {
                gridCells[index].BindEmpty(x, y, available);
            }
            gridCells[index].SetClickHandler(OnGridCellClicked);
        }
    }

    private void EnsureGridCells()
    {
        CollectSceneGridCells();
        if (gridCells.Count >= 25 || gridCellPrefab == null || formationGridContent == null)
        {
            return;
        }

        ClearChildren(formationGridContent);
        gridCells.Clear();
        for (int i = 0; i < 25; i++)
        {
            ProductBattleGridCellView cell = Instantiate(gridCellPrefab, formationGridContent);
            gridCells.Add(cell);
        }
    }

    private void CollectSceneGridCells()
    {
        if (formationGridContent == null)
        {
            return;
        }
        gridCells.Clear();
        gridCells.AddRange(formationGridContent.GetComponentsInChildren<ProductBattleGridCellView>(true));
    }

    private void OnDeckCardClicked(ProductBattleCardListRowView view)
    {
        selectedDeckIndex = view == null ? -1 : view.Index;
        selectedLibraryIndex = -1;
        RenderDeck();
        RenderCardLibrary();
        ShowSelectedDetail();
        WriteStatus(selectedDeckIndex >= 0 ? $"Selected P{selectedDeckIndex + 1}." : "No card selected.");
    }

    private void OnLibraryCardClicked(ProductBattleCardListRowView view)
    {
        selectedLibraryIndex = view == null ? -1 : view.Index;
        RenderCardLibrary();
        ShowSelectedDetail();
        WriteStatus(selectedLibraryIndex >= 0 ? $"Previewing C{selectedLibraryIndex + 1}." : "No card selected.");
    }

    private void OnGridCellClicked(ProductBattleGridCellView cell)
    {
        if (cell == null)
        {
            return;
        }

        int index = cell.Y * 5 + cell.X;
        if (placement.ContainsKey(index))
        {
            placement.Remove(index);
            RenderAll();
            WriteStatus("Removed card from formation.");
            return;
        }

        if (cell.Y >= playerRows)
        {
            WriteStatus("Place player cards on the near-side rows.");
            return;
        }

        if (selectedDeckIndex < 0 || selectedDeckIndex >= deckCards.Count)
        {
            WriteStatus("Select a deck card first.");
            return;
        }

        ThoughtMapBattleCardData selected = deckCards[selectedDeckIndex];
        int oldCell = placement.FirstOrDefault(pair => pair.Value == selected).Key;
        if (placement.ContainsValue(selected))
        {
            placement.Remove(oldCell);
        }
        else if (placement.Count >= deployLimit)
        {
            WriteStatus($"Deploy limit is {deployLimit}. Remove a card before placing another.");
            return;
        }

        placement[index] = selected;
        RenderAll();
        WriteStatus($"Placed P{selectedDeckIndex + 1} at ({cell.X + 1},{cell.Y + 1}).");
    }

    private void ShowSelectedDetail()
    {
        if (cardDetailPanel == null)
        {
            return;
        }

        if (selectedLibraryIndex >= 0 && selectedLibraryIndex < loadedCards.Count)
        {
            ThoughtMapBattleCardData libraryCard = loadedCards[selectedLibraryIndex];
            cardDetailPanel.Show(libraryCard, ResolveCardArt(selectedLibraryIndex), ResolveAttributeIcon(libraryCard));
            return;
        }

        if (selectedDeckIndex < 0 || selectedDeckIndex >= deckCards.Count)
        {
            cardDetailPanel.Clear();
            return;
        }

        ThoughtMapBattleCardData card = deckCards[selectedDeckIndex];
        cardDetailPanel.Show(card, ResolveCardArt(selectedDeckIndex), ResolveAttributeIcon(card));
    }

    public void SimulatePreview()
    {
        StringBuilder builder = new StringBuilder();
        builder.AppendLine("=== Battle Prep Preview ===");
        builder.AppendLine($"Deck Cards: {deckCards.Count}");
        builder.AppendLine($"Placed Cards: {placement.Count}/{deployLimit}");
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement.OrderBy(pair => pair.Key))
        {
            int x = pair.Key % 5;
            int y = pair.Key / 5;
            builder.AppendLine($"P{deckCards.IndexOf(pair.Value) + 1} {pair.Value.cardName} @({x + 1},{y + 1})");
        }
        debugLogPanel?.SetCollapsed(false);
        debugLogPanel?.SetLog(builder.ToString());
        WriteStatus("Preview updated.");
    }

    public void SaveDeckJson()
    {
        ThoughtMapBattleDeckConfig config = new ThoughtMapBattleDeckConfig();
        config.deckCardIds = deckCards.Select(GetCardId).ToList();
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement.OrderBy(pair => pair.Key))
        {
            int x = pair.Key % 5;
            int y = pair.Key / 5;
            config.deployedCardIds.Add(GetCardId(pair.Value));
            config.gridPositions.Add(new ThoughtMapBattleDeckPosition(GetCardId(pair.Value), x, y));
        }

        string path = Path.Combine(Application.persistentDataPath, deckFileName);
        File.WriteAllText(path, JsonUtility.ToJson(config, true), Encoding.UTF8);
        WriteStatus("Saved deck: " + path);
    }

    public void StartBattleScene()
    {
        SaveDeckJson();
        WriteStatus("Opening BattleScene: " + battleSceneName);
        SceneManager.LoadScene(battleSceneName);
    }

    private Sprite ResolveCardArt(int index)
    {
        if (cardArtPool != null && cardArtPool.Length > 0)
        {
            return cardArtPool[Mathf.Abs(index) % cardArtPool.Length];
        }
        return defaultCardArt;
    }

    private Sprite ResolveAttributeIcon(ThoughtMapBattleCardData card)
    {
        string key = card == null ? "" : card.primaryAttribute;
        if (attributeSprites != null)
        {
            foreach (AttributeSpriteMap map in attributeSprites)
            {
                if (!string.IsNullOrWhiteSpace(map.attribute) && map.attribute == key)
                {
                    return map.sprite;
                }
            }
        }
        return defaultAttributeIcon;
    }

    private string GetSpriteWarning()
    {
        bool cardPoolEmpty = cardArtPool == null || cardArtPool.Length == 0;
        bool hasDefaultCardArt = defaultCardArt != null;
        bool hasDefaultAttributeIcon = defaultAttributeIcon != null;

        if (cardPoolEmpty && !hasDefaultCardArt)
        {
            return "Card Art Pool is empty and Default Card Art is not assigned";
        }

        if (cardPoolEmpty)
        {
            return "Card Art Pool is empty";
        }

        if (!hasDefaultAttributeIcon)
        {
            return "Default Attribute Icon is not assigned";
        }

        return "";
    }

    private void AddClick(Button button, UnityEngine.Events.UnityAction action)
    {
        if (button == null)
        {
            return;
        }
        button.onClick.RemoveListener(action);
        button.onClick.AddListener(action);
    }

    [ContextMenu("Log Runtime Layout Diagnostics")]
    public void LogRuntimeLayoutDiagnostics()
    {
        LogScrollAreaDiagnostics("CardListPanel", cardListContent);
        LogScrollAreaDiagnostics("DeckListPanel", deckListContent);
    }

    private ProductBattleCardListRowView CreateListRow(Transform parent, ProductBattleCardListRowView prefab, string objectName)
    {
        ProductBattleCardListRowView view;
        if (prefab != null)
        {
            view = Instantiate(prefab, parent);
        }
        else
        {
            GameObject row = new GameObject(objectName, typeof(RectTransform));
            row.transform.SetParent(parent, false);
            view = row.AddComponent<ProductBattleCardListRowView>();
        }

        view.NormalizeForList(LightweightRowHeight);
        return view;
    }

    private void EnsureListContentReferences()
    {
        if (cardListContent == null)
        {
            cardListContent = FindPanelContent("CardListPanel");
        }

        if (deckListContent == null)
        {
            deckListContent = FindPanelContent("DeckListPanel");
        }
    }

    private Transform FindPanelContent(string panelName)
    {
        Transform panel = FindDescendant(transform, panelName);
        if (panel == null)
        {
            return null;
        }

        Transform viewport = FindDirectChild(panel, "Viewport");
        if (viewport != null)
        {
            Transform content = FindDirectChild(viewport, "Content");
            if (content != null)
            {
                return content;
            }
        }

        return FindDirectChild(panel, "Content");
    }

    private Transform FindDescendant(Transform root, string objectName)
    {
        if (root == null)
        {
            return null;
        }

        if (root.name == objectName)
        {
            return root;
        }

        for (int i = 0; i < root.childCount; i++)
        {
            Transform found = FindDescendant(root.GetChild(i), objectName);
            if (found != null)
            {
                return found;
            }
        }

        return null;
    }

    private Transform FindDirectChild(Transform root, string objectName)
    {
        if (root == null)
        {
            return null;
        }

        for (int i = 0; i < root.childCount; i++)
        {
            Transform child = root.GetChild(i);
            if (child.name == objectName)
            {
                return child;
            }
        }

        return null;
    }

    private void WarnMissingListContent(string label, string expectedPath)
    {
        string message = $"{label} Content is not assigned. Expected {expectedPath}. Run Tools > Source of Thought > Repair Product Battle Prep ScrollViews.";
        if (statusText != null)
        {
            statusText.text = message;
        }
        Debug.LogWarning("[ProductBattlePrep] " + message, this);
    }

    private void NormalizeLightweightListScrollArea(Transform content)
    {
        if (content == null)
        {
            Debug.LogWarning("[ProductBattlePrep] Cannot normalize lightweight list because Content is null.", this);
            return;
        }

        RectTransform contentRect = content as RectTransform;
        if (contentRect == null)
        {
            Debug.LogWarning($"[ProductBattlePrep] Cannot normalize lightweight list because {content.name} is not a RectTransform.", this);
            return;
        }

        RectTransform viewport = EnsureRuntimeViewportContent(contentRect);
        if (viewport == null)
        {
            Debug.LogWarning($"[ProductBattlePrep] Cannot normalize lightweight list because Viewport is missing for {content.name}.", this);
            return;
        }

        contentRect.anchorMin = new Vector2(0f, 1f);
        contentRect.anchorMax = new Vector2(1f, 1f);
        contentRect.pivot = new Vector2(0.5f, 1f);
        contentRect.anchoredPosition = Vector2.zero;
        contentRect.sizeDelta = Vector2.zero;
        contentRect.offsetMin = new Vector2(0f, contentRect.offsetMin.y);
        contentRect.offsetMax = new Vector2(0f, contentRect.offsetMax.y);

        GridLayoutGroup grid = content.GetComponent<GridLayoutGroup>();
        if (grid != null)
        {
            RemoveComponent(grid);
        }

        VerticalLayoutGroup vertical = content.GetComponent<VerticalLayoutGroup>();
        if (vertical == null)
        {
            vertical = content.gameObject.AddComponent<VerticalLayoutGroup>();
        }
        if (vertical == null)
        {
            Debug.LogWarning($"[ProductBattlePrep] Could not create VerticalLayoutGroup on {content.name}.", this);
            return;
        }
        vertical.padding = new RectOffset(6, 6, 6, 6);
        vertical.spacing = LightweightRowSpacing;
        vertical.childAlignment = TextAnchor.UpperCenter;
        vertical.childControlWidth = true;
        vertical.childControlHeight = true;
        vertical.childForceExpandWidth = true;
        vertical.childForceExpandHeight = false;

        ContentSizeFitter fitter = content.GetComponent<ContentSizeFitter>();
        if (fitter == null)
        {
            fitter = content.gameObject.AddComponent<ContentSizeFitter>();
        }
        if (fitter == null)
        {
            Debug.LogWarning($"[ProductBattlePrep] Could not create ContentSizeFitter on {content.name}.", this);
            return;
        }
        fitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        if (viewport != null)
        {
            Image viewportImage = viewport.GetComponent<Image>();
            if (viewportImage == null)
            {
                viewportImage = viewport.gameObject.AddComponent<Image>();
                viewportImage.color = new Color(0f, 0f, 0f, 0.08f);
            }
            viewportImage.raycastTarget = true;

            Mask mask = viewport.GetComponent<Mask>();
            if (mask == null)
            {
                mask = viewport.gameObject.AddComponent<Mask>();
            }
            mask.showMaskGraphic = false;

            RectTransform panel = viewport.parent as RectTransform;
            if (panel != null)
            {
                ScrollRect scroll = panel.GetComponent<ScrollRect>();
                if (scroll == null)
                {
                    scroll = panel.gameObject.AddComponent<ScrollRect>();
                }
                scroll.viewport = viewport;
                scroll.content = contentRect;
                scroll.horizontal = false;
                scroll.vertical = true;
                scroll.movementType = ScrollRect.MovementType.Clamped;
                scroll.inertia = true;
            }
        }
    }

    private RectTransform EnsureRuntimeViewportContent(RectTransform contentRect)
    {
        if (contentRect == null)
        {
            return null;
        }

        RectTransform viewport = contentRect.parent != null && contentRect.parent.name == "Viewport"
            ? contentRect.parent as RectTransform
            : null;
        RectTransform panel = viewport == null ? contentRect.parent as RectTransform : viewport.parent as RectTransform;
        if (panel == null)
        {
            return viewport;
        }

        if (viewport == null)
        {
            viewport = FindDirectChild(panel, "Viewport") as RectTransform;
        }

        if (viewport == null)
        {
            GameObject viewportObject = new GameObject("Viewport", typeof(RectTransform), typeof(Image), typeof(Mask));
            viewportObject.transform.SetParent(panel, false);
            viewport = viewportObject.GetComponent<RectTransform>();
        }

        viewport.SetParent(panel, false);
        viewport.SetSiblingIndex(Mathf.Min(1, panel.childCount - 1));
        viewport.anchorMin = new Vector2(0.03f, 0.03f);
        viewport.anchorMax = new Vector2(0.97f, 0.90f);
        viewport.pivot = new Vector2(0.5f, 0.5f);
        viewport.anchoredPosition = Vector2.zero;
        viewport.sizeDelta = Vector2.zero;
        viewport.offsetMin = Vector2.zero;
        viewport.offsetMax = Vector2.zero;

        if (contentRect.parent != viewport)
        {
            contentRect.SetParent(viewport, false);
        }
        contentRect.gameObject.name = "Content";
        return viewport;
    }

    private ScrollRect GetScrollRectForContent(Transform content)
    {
        RectTransform contentRect = content as RectTransform;
        RectTransform viewport = contentRect == null ? null : contentRect.parent as RectTransform;
        RectTransform panel = viewport == null ? null : viewport.parent as RectTransform;
        return panel == null ? null : panel.GetComponent<ScrollRect>();
    }

    private void RestoreScrollPosition(ScrollRect scroll, float position)
    {
        if (scroll == null)
        {
            return;
        }

        Canvas.ForceUpdateCanvases();
        scroll.verticalNormalizedPosition = Mathf.Clamp01(position);
    }

    private void RemoveComponent(Component component)
    {
        if (component == null)
        {
            return;
        }

        if (component is Behaviour behaviour)
        {
            behaviour.enabled = false;
        }

        if (Application.isPlaying)
        {
            Destroy(component);
        }
        else
        {
            DestroyImmediate(component);
        }
    }

    private void LogScrollAreaDiagnostics(string label, Transform content)
    {
        if (content == null)
        {
            Debug.LogWarning($"[ProductBattlePrep] {label}: content is not assigned.", this);
            return;
        }

        GridLayoutGroup grid = content.GetComponent<GridLayoutGroup>();
        VerticalLayoutGroup vertical = content.GetComponent<VerticalLayoutGroup>();
        ContentSizeFitter fitter = content.GetComponent<ContentSizeFitter>();
        RectTransform viewport = content.parent as RectTransform;
        ScrollRect scroll = viewport == null || viewport.parent == null ? null : viewport.parent.GetComponent<ScrollRect>();
        Mask mask = viewport == null ? null : viewport.GetComponent<Mask>();
        string gridCell = grid == null || !grid.enabled ? "missing" : grid.cellSize.ToString();
        string verticalInfo = vertical == null ? "missing" : "spacing " + vertical.spacing;
        string fitterInfo = fitter == null ? "missing" : fitter.horizontalFit + "/" + fitter.verticalFit;
        string scrollViewport = scroll == null || scroll.viewport == null ? "missing" : scroll.viewport.name;
        string scrollContent = scroll == null || scroll.content == null ? "missing" : scroll.content.name;
        string maskInfo = mask == null ? "missing" : mask.showMaskGraphic.ToString();

        Debug.Log(
            $"[ProductBattlePrep] {label}: " +
            $"Grid cellSize={gridCell}, " +
            $"VerticalLayout={verticalInfo}, " +
            $"Fitter={fitterInfo}, " +
            $"Scroll viewport={scrollViewport}, " +
            $"Scroll content={scrollContent}, " +
            $"Mask={maskInfo}",
            this
        );

        ProductBattleCardListRowView[] rows = content.GetComponentsInChildren<ProductBattleCardListRowView>(true);
        for (int i = 0; i < rows.Length; i++)
        {
            RectTransform rect = rows[i].GetComponent<RectTransform>();
            LayoutElement layout = rows[i].GetComponent<LayoutElement>();
            Graphic[] graphics = rows[i].GetComponentsInChildren<Graphic>(true);
            int raycastTargets = graphics.Count(graphic => graphic.raycastTarget);
            string cardSize = rect == null ? "missing" : rect.rect.size.ToString();
            string layoutInfo = layout == null
                ? "missing"
                : "min " + layout.minWidth + "x" + layout.minHeight + " preferred " + layout.preferredWidth + "x" + layout.preferredHeight;
            Debug.Log(
                $"[ProductBattlePrep] {label} Row {i}: " +
                $"size={cardSize}, " +
                $"Layout={layoutInfo}, " +
                $"raycastTargetGraphics={raycastTargets}",
                rows[i]
            );
        }
    }

    private void WriteStatus(string value)
    {
        if (statusText != null)
        {
            statusText.text = value;
        }
        Debug.Log("[ProductBattlePrep] " + value, this);
    }

    private string GetCardId(ThoughtMapBattleCardData card)
    {
        if (card == null)
        {
            return "";
        }
        return !string.IsNullOrWhiteSpace(card.cardId) ? card.cardId : card.docId;
    }

    private void ClearChildren(Transform root)
    {
        if (root == null)
        {
            return;
        }
        for (int i = root.childCount - 1; i >= 0; i--)
        {
            Destroy(root.GetChild(i).gameObject);
        }
    }
}

[System.Serializable]
public class AttributeSpriteMap
{
    public string attribute;
    public Sprite sprite;
}
