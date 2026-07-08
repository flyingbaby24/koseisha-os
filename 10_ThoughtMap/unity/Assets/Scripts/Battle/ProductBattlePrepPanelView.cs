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
    [Header("Input")]
    [SerializeField] private TextAsset cardsCsvAsset;
    [SerializeField] private string streamingAssetsCsvPath = "cards.csv";
    [SerializeField] private string battleSceneName = "BattleScene";

    [Header("Sprites")]
    [SerializeField] private Sprite placeholderCardArt;
    [SerializeField] private Sprite placeholderAttributeIcon;

    [Header("Runtime")]
    [SerializeField] private bool buildOnAwake = true;
    [SerializeField] private RectTransform panelRoot;
    [SerializeField] private Vector2 defaultSize = new Vector2(1760f, 980f);
    [SerializeField] private Vector2 defaultPosition = Vector2.zero;
    [SerializeField] private int deployLimit = 5;

    private readonly List<ThoughtMapBattleCardData> loadedCards = new List<ThoughtMapBattleCardData>();
    private readonly List<ThoughtMapBattleCardData> deckCards = new List<ThoughtMapBattleCardData>();
    private readonly Dictionary<int, ThoughtMapBattleCardData> placement = new Dictionary<int, ThoughtMapBattleCardData>();
    private readonly List<ProductBattleCardView> cardViews = new List<ProductBattleCardView>();
    private readonly List<ProductBattleGridCellView> gridCells = new List<ProductBattleGridCellView>();

    private RectTransform cardListRoot;
    private RectTransform deckRoot;
    private RectTransform gridRoot;
    private RectTransform debugScrollRoot;
    private TMP_Text statusText;
    private TMP_Text debugText;
    private Button collapseDebugButton;
    private LayoutElement debugPanelLayout;
    private int selectedDeckIndex = -1;
    private bool debugCollapsed = true;

    private void Awake()
    {
        if (buildOnAwake)
        {
            BuildPanel();
            LoadProductCards();
        }
    }

    [ContextMenu("Build Product Battle Prep Panel")]
    public void BuildPanel()
    {
        if (panelRoot == null)
        {
            panelRoot = CreatePanelRoot();
        }

        ClearChildren(panelRoot);
        EnsureImage(panelRoot.gameObject, new Color(0.005f, 0.018f, 0.04f, 0.98f));

        VerticalLayoutGroup rootLayout = EnsureVerticalLayout(panelRoot.gameObject, 12f, 18, 18, 16, 16);
        rootLayout.childControlWidth = true;
        rootLayout.childControlHeight = true;
        rootLayout.childForceExpandWidth = true;
        rootLayout.childForceExpandHeight = false;

        TMP_Text title = CreateText(panelRoot, "Title", "Source of Thought - Product Battle Prep", 30, new Color(0.76f, 0.98f, 1f, 1f), TextAlignmentOptions.Left);
        title.fontStyle = FontStyles.Bold;
        AddPreferredHeight(title.gameObject, 42f);

        RectTransform controls = CreateBlock(panelRoot, "ControlBar", 54f, new Color(0.0f, 0.12f, 0.18f, 0.88f));
        HorizontalLayoutGroup controlsLayout = EnsureHorizontalLayout(controls.gameObject, 12f, 8, 8, 5, 5);
        controlsLayout.childControlWidth = true;
        controlsLayout.childControlHeight = true;
        controlsLayout.childForceExpandWidth = false;

        CreateButton(controls, "Load Cards", new Vector2(150f, 40f), LoadProductCards);
        CreateButton(controls, "Simulate Battle", new Vector2(170f, 40f), SimulatePreview);
        CreateButton(controls, "Save Deck", new Vector2(150f, 40f), SaveDeckJson);
        CreateButton(controls, "Start Battle", new Vector2(150f, 40f), StartBattleScene);
        statusText = CreateText(controls, "StatusText", "Ready.", 14, new Color(1f, 0.82f, 0.32f, 1f), TextAlignmentOptions.Left);
        AddPreferredSize(statusText.gameObject, 760f, 40f);

        RectTransform mainRow = CreateBlock(panelRoot, "MainContent", 700f, new Color(0f, 0f, 0f, 0f));
        HorizontalLayoutGroup mainLayout = EnsureHorizontalLayout(mainRow.gameObject, 14f, 0, 0, 0, 0);
        mainLayout.childControlWidth = true;
        mainLayout.childControlHeight = true;
        mainLayout.childForceExpandWidth = false;

        RectTransform libraryPanel = CreateNamedPanel(mainRow, "Card Library", 510f, 700f);
        cardListRoot = CreateCardScrollView(libraryPanel, "CardLibraryScroll", 5, new Vector2(150f, 250f), 630f);

        RectTransform centerPanel = CreateNamedPanel(mainRow, "Deck 10", 360f, 700f);
        deckRoot = CreateCardScrollView(centerPanel, "DeckScroll", 2, new Vector2(150f, 250f), 630f);

        RectTransform gridPanel = CreateNamedPanel(mainRow, "5x5 Formation Board", 820f, 700f);
        gridRoot = CreateGridBoard(gridPanel);

        RectTransform debugPanel = CreateBlock(panelRoot, "DebugLogPanel", 128f, new Color(0.0f, 0.10f, 0.14f, 0.9f));
        debugPanelLayout = debugPanel.GetComponent<LayoutElement>();
        EnsureVerticalLayout(debugPanel.gameObject, 8f, 8, 8, 8, 8);
        CreateDebugHeader(debugPanel);
        debugText = CreateDebugScroll(debugPanel);
        SetDebugCollapsed(true);
    }

    private void LoadProductCards()
    {
        loadedCards.Clear();
        deckCards.Clear();
        placement.Clear();
        selectedDeckIndex = -1;

        try
        {
            List<ThoughtMapBattleCardData> cards = cardsCsvAsset != null
                ? ThoughtMapCardsCsvLoader.LoadFromText(cardsCsvAsset.text)
                : ThoughtMapCardsCsvLoader.LoadFromStreamingAssets(streamingAssetsCsvPath);
            loadedCards.AddRange(cards);
            deckCards.AddRange(cards.Take(10));
            WriteStatus($"Loaded {loadedCards.Count} cards. Select a deck card, then click the board.");
        }
        catch (System.Exception exc)
        {
            WriteStatus("Could not load cards.csv: " + exc.Message);
        }

        RenderCards();
        RenderGrid();
    }

    private void RenderCards()
    {
        ClearChildren(cardListRoot);
        ClearChildren(deckRoot);
        cardViews.Clear();

        for (int i = 0; i < loadedCards.Count && i < 30; i++)
        {
            ProductBattleCardView view = CreateCardView(cardListRoot, $"LibraryCard_{i:00}");
            view.Bind(loadedCards[i], i, $"C{i + 1}", false, false, placeholderCardArt, placeholderAttributeIcon);
        }

        for (int i = 0; i < deckCards.Count; i++)
        {
            ProductBattleCardView view = CreateCardView(deckRoot, $"DeckCard_{i:00}");
            view.Bind(deckCards[i], i, $"P{i + 1}", i == selectedDeckIndex, placement.ContainsValue(deckCards[i]), placeholderCardArt, placeholderAttributeIcon);
            view.SetClickHandler(OnDeckCardClicked);
            cardViews.Add(view);
        }
    }

    private void RenderGrid()
    {
        if (gridCells.Count != 25)
        {
            ClearChildren(gridRoot);
            gridCells.Clear();
            for (int i = 0; i < 25; i++)
            {
                ProductBattleGridCellView cell = CreateGridCell(gridRoot, $"ProductGridCell_{i:00}");
                cell.SetClickHandler(OnGridCellClicked);
                gridCells.Add(cell);
            }
        }

        for (int index = 0; index < gridCells.Count; index++)
        {
            int x = index % 5;
            int y = index / 5;
            bool playerSide = y <= 2;
            if (placement.TryGetValue(index, out ThoughtMapBattleCardData card))
            {
                int deckIndex = deckCards.IndexOf(card);
                gridCells[index].BindCard(x, y, card, $"P{deckIndex + 1}");
            }
            else
            {
                gridCells[index].BindEmpty(x, y, playerSide);
            }
        }
    }

    private void OnDeckCardClicked(ProductBattleCardView view)
    {
        selectedDeckIndex = view == null ? -1 : view.Index;
        RenderCards();
        WriteStatus(selectedDeckIndex >= 0 ? $"Selected P{selectedDeckIndex + 1}. Click the formation board." : "No card selected.");
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
            RenderCards();
            RenderGrid();
            WriteStatus("Removed card from board.");
            return;
        }

        if (cell.Y > 2)
        {
            WriteStatus("Player cards can be placed on the lower three rows in this mock.");
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
            WriteStatus($"Deploy limit is {deployLimit} cards. Remove a card before placing another.");
            return;
        }

        placement[index] = selected;
        RenderCards();
        RenderGrid();
        WriteStatus($"Placed P{selectedDeckIndex + 1} at ({cell.X},{cell.Y}).");
    }

    private void SimulatePreview()
    {
        StringBuilder builder = new StringBuilder();
        builder.AppendLine("=== Product Battle Prep Preview ===");
        builder.AppendLine($"Deck Cards: {deckCards.Count}");
        builder.AppendLine($"Placed Cards: {placement.Count}");
        foreach (KeyValuePair<int, ThoughtMapBattleCardData> pair in placement.OrderBy(pair => pair.Key))
        {
            int x = pair.Key % 5;
            int y = pair.Key / 5;
            builder.AppendLine($"P{deckCards.IndexOf(pair.Value) + 1} {pair.Value.cardName} @({x},{y})");
        }
        debugText.text = builder.ToString();
        SetDebugCollapsed(false);
    }

    private void SaveDeckJson()
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

        string path = Path.Combine(Application.persistentDataPath, "deck.json");
        File.WriteAllText(path, JsonUtility.ToJson(config, true), Encoding.UTF8);
        WriteStatus("Saved deck.json: " + path);
    }

    private void StartBattleScene()
    {
        SaveDeckJson();
        WriteStatus("Opening future BattleScene: " + battleSceneName);
        SceneManager.LoadScene(battleSceneName);
    }

    private RectTransform CreatePanelRoot()
    {
        GameObject panelObject = new GameObject("ProductBattlePrepPanel", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        RectTransform rect = panelObject.GetComponent<RectTransform>();
        Canvas canvas = GetComponentInParent<Canvas>();
        rect.SetParent(canvas == null ? transform : canvas.transform, false);
        rect.anchorMin = new Vector2(0.5f, 0.5f);
        rect.anchorMax = new Vector2(0.5f, 0.5f);
        rect.pivot = new Vector2(0.5f, 0.5f);
        rect.sizeDelta = defaultSize;
        rect.anchoredPosition = defaultPosition;
        return rect;
    }

    private RectTransform CreateNamedPanel(RectTransform parent, string title, float width, float height)
    {
        RectTransform panel = CreateBlock(parent, title.Replace(" ", "") + "Panel", 0f, new Color(0.0f, 0.12f, 0.18f, 0.88f));
        AddPreferredSize(panel.gameObject, width, height);
        EnsureVerticalLayout(panel.gameObject, 10f, 10, 10, 10, 10);
        TMP_Text heading = CreateText(panel, title.Replace(" ", "") + "Heading", title, 18, new Color(0.72f, 0.96f, 1f, 1f), TextAlignmentOptions.Left);
        heading.fontStyle = FontStyles.Bold;
        AddPreferredHeight(heading.gameObject, 28f);
        return panel;
    }

    private RectTransform CreateCardScrollView(RectTransform parent, string name, int columns, Vector2 cellSize, float height)
    {
        GameObject scrollObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ScrollRect));
        RectTransform scrollRect = scrollObject.GetComponent<RectTransform>();
        scrollRect.SetParent(parent, false);
        AddPreferredHeight(scrollObject, height);
        scrollObject.GetComponent<Image>().color = new Color(0.0f, 0.05f, 0.08f, 0.9f);

        GameObject viewportObject = new GameObject("Viewport", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Mask));
        RectTransform viewport = viewportObject.GetComponent<RectTransform>();
        viewport.SetParent(scrollRect, false);
        Stretch(viewport, 8f, 8f);
        viewportObject.GetComponent<Image>().color = new Color(0f, 0f, 0f, 0.05f);
        viewportObject.GetComponent<Mask>().showMaskGraphic = false;

        GameObject contentObject = new GameObject("Content", typeof(RectTransform), typeof(GridLayoutGroup), typeof(ContentSizeFitter));
        RectTransform content = contentObject.GetComponent<RectTransform>();
        content.SetParent(viewport, false);
        content.anchorMin = new Vector2(0f, 1f);
        content.anchorMax = new Vector2(1f, 1f);
        content.pivot = new Vector2(0.5f, 1f);
        content.offsetMin = Vector2.zero;
        content.offsetMax = Vector2.zero;
        GridLayoutGroup grid = contentObject.GetComponent<GridLayoutGroup>();
        grid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        grid.constraintCount = columns;
        grid.cellSize = cellSize;
        grid.spacing = new Vector2(10f, 10f);
        grid.childAlignment = TextAnchor.UpperCenter;
        contentObject.GetComponent<ContentSizeFitter>().verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        ScrollRect scroll = scrollObject.GetComponent<ScrollRect>();
        scroll.viewport = viewport;
        scroll.content = content;
        scroll.horizontal = false;
        scroll.vertical = true;
        return content;
    }

    private RectTransform CreateGridBoard(RectTransform parent)
    {
        GameObject gridObject = new GameObject("FormationGrid", typeof(RectTransform), typeof(GridLayoutGroup));
        RectTransform rect = gridObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        AddPreferredHeight(gridObject, 620f);
        GridLayoutGroup grid = gridObject.GetComponent<GridLayoutGroup>();
        grid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        grid.constraintCount = 5;
        grid.cellSize = new Vector2(150f, 112f);
        grid.spacing = new Vector2(8f, 8f);
        grid.childAlignment = TextAnchor.MiddleCenter;
        return rect;
    }

    private ProductBattleCardView CreateCardView(RectTransform parent, string name)
    {
        GameObject cardObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ProductBattleCardView));
        cardObject.transform.SetParent(parent, false);
        ProductBattleCardView view = cardObject.GetComponent<ProductBattleCardView>();
        view.BuildIfNeeded();
        return view;
    }

    private ProductBattleGridCellView CreateGridCell(RectTransform parent, string name)
    {
        GameObject cellObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ProductBattleGridCellView));
        cellObject.transform.SetParent(parent, false);
        ProductBattleGridCellView view = cellObject.GetComponent<ProductBattleGridCellView>();
        view.BuildIfNeeded();
        return view;
    }

    private void CreateDebugHeader(RectTransform parent)
    {
        RectTransform header = CreateBlock(parent, "DebugHeader", 34f, new Color(0f, 0f, 0f, 0f));
        HorizontalLayoutGroup layout = EnsureHorizontalLayout(header.gameObject, 8f, 0, 0, 0, 0);
        layout.childForceExpandWidth = false;
        TMP_Text heading = CreateText(header, "DebugHeading", "Debug / Simulation Preview", 15, Color.white, TextAlignmentOptions.Left);
        AddPreferredSize(heading.gameObject, 420f, 30f);
        collapseDebugButton = CreateButton(header, "Expand Debug", new Vector2(150f, 30f), () => SetDebugCollapsed(!debugCollapsed));
    }

    private TMP_Text CreateDebugScroll(RectTransform parent)
    {
        GameObject textObject = new GameObject("DebugText", typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        debugScrollRoot = rect;
        AddPreferredHeight(textObject, 80f);
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.fontSize = 13;
        text.color = Color.white;
        text.alignment = TextAlignmentOptions.TopLeft;
        text.enableWordWrapping = true;
        return text;
    }

    private void SetDebugCollapsed(bool collapsed)
    {
        debugCollapsed = collapsed;
        if (debugScrollRoot != null)
        {
            debugScrollRoot.gameObject.SetActive(!collapsed);
        }
        if (debugText != null)
        {
            debugText.gameObject.SetActive(!collapsed);
        }
        if (collapseDebugButton != null)
        {
            TMP_Text label = collapseDebugButton.GetComponentInChildren<TMP_Text>();
            if (label != null)
            {
                label.text = collapsed ? "Expand Debug" : "Collapse Debug";
            }
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

    private RectTransform CreateBlock(RectTransform parent, string name, float preferredHeight, Color color)
    {
        GameObject blockObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        RectTransform rect = blockObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        blockObject.GetComponent<Image>().color = color;
        if (preferredHeight > 0f)
        {
            AddPreferredHeight(blockObject, preferredHeight);
        }
        return rect;
    }

    private Button CreateButton(RectTransform parent, string label, Vector2 size, UnityEngine.Events.UnityAction onClick)
    {
        GameObject buttonObject = new GameObject(label.Replace(" ", "") + "Button", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button));
        RectTransform rect = buttonObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        Image image = buttonObject.GetComponent<Image>();
        image.color = new Color(0.0f, 0.32f, 0.45f, 0.96f);
        Button button = buttonObject.GetComponent<Button>();
        button.onClick.AddListener(onClick);
        AddPreferredSize(buttonObject, size.x, size.y);
        TMP_Text text = CreateText(rect, "Label", label, 14, Color.white, TextAlignmentOptions.Center);
        Stretch(text.rectTransform, 6f, 4f);
        return button;
    }

    private TMP_Text CreateText(RectTransform parent, string name, string value, int size, Color color, TextAlignmentOptions alignment)
    {
        GameObject textObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = size;
        text.color = color;
        text.alignment = alignment;
        text.enableWordWrapping = true;
        return text;
    }

    private Image EnsureImage(GameObject target, Color color)
    {
        Image image = target.GetComponent<Image>();
        if (image == null)
        {
            image = target.AddComponent<Image>();
        }
        image.color = color;
        return image;
    }

    private VerticalLayoutGroup EnsureVerticalLayout(GameObject target, float spacing, int left, int right, int top, int bottom)
    {
        VerticalLayoutGroup layout = target.GetComponent<VerticalLayoutGroup>();
        if (layout == null)
        {
            layout = target.AddComponent<VerticalLayoutGroup>();
        }
        layout.spacing = spacing;
        layout.padding = new RectOffset(left, right, top, bottom);
        return layout;
    }

    private HorizontalLayoutGroup EnsureHorizontalLayout(GameObject target, float spacing, int left, int right, int top, int bottom)
    {
        HorizontalLayoutGroup layout = target.GetComponent<HorizontalLayoutGroup>();
        if (layout == null)
        {
            layout = target.AddComponent<HorizontalLayoutGroup>();
        }
        layout.spacing = spacing;
        layout.padding = new RectOffset(left, right, top, bottom);
        return layout;
    }

    private void AddPreferredHeight(GameObject target, float height)
    {
        LayoutElement element = target.GetComponent<LayoutElement>();
        if (element == null)
        {
            element = target.AddComponent<LayoutElement>();
        }
        element.preferredHeight = height;
        element.minHeight = Mathf.Min(height, 60f);
    }

    private void AddPreferredSize(GameObject target, float width, float height)
    {
        LayoutElement element = target.GetComponent<LayoutElement>();
        if (element == null)
        {
            element = target.AddComponent<LayoutElement>();
        }
        element.preferredWidth = width;
        element.preferredHeight = height;
        element.minWidth = width;
        element.minHeight = height;
    }

    private void Stretch(RectTransform rect, float horizontal, float vertical)
    {
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = new Vector2(horizontal, vertical);
        rect.offsetMax = new Vector2(-horizontal, -vertical);
    }

    private void ClearChildren(RectTransform root)
    {
        if (root == null)
        {
            return;
        }
        for (int i = root.childCount - 1; i >= 0; i--)
        {
            GameObject child = root.GetChild(i).gameObject;
            if (Application.isPlaying)
            {
                Destroy(child);
            }
            else
            {
                DestroyImmediate(child);
            }
        }
    }
}
