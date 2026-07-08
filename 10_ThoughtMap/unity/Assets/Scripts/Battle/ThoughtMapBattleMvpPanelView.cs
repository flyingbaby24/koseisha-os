using System.IO;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ThoughtMapBattleMvpPanelView : MonoBehaviour
{
    [Header("Controller")]
    [SerializeField] private ThoughtMapBattleMvpController controller;

    [Header("Runtime UI")]
    [SerializeField] private bool buildOnAwake = true;
    [SerializeField] private bool showOnStart = false;
    [SerializeField] private RectTransform panelRoot;
    [SerializeField] private Vector2 defaultSize = new Vector2(1680f, 1000f);
    [SerializeField] private Vector2 defaultPosition = new Vector2(0f, 0f);

    [Header("Generated References")]
    [SerializeField] private Button startBattleButton;
    [SerializeField] private Button resetPlacementButton;
    [SerializeField] private Button toggleVisibilityButton;
    [SerializeField] private RectTransform playerDeckRoot;
    [SerializeField] private RectTransform enemyDeckRoot;
    [SerializeField] private TMP_Text battleLogText;
    [SerializeField] private ScrollRect battleLogScrollRect;
    [SerializeField] private TMP_Text battleResultText;
    [SerializeField] private ThoughtMapBattleSummaryView battleSummaryView;
    [SerializeField] private TMP_Text turnText;
    [SerializeField] private TMP_Text warningText;
    [SerializeField] private RectTransform gridRoot;
    [SerializeField] private RectTransform battleLogScrollRoot;
    [SerializeField] private Button collapseLogButton;
    [SerializeField] private LayoutElement battleLogPanelLayout;

    private bool logCollapsed;

    private void Awake()
    {
        if (controller == null)
        {
            controller = GetComponent<ThoughtMapBattleMvpController>();
        }

        if (buildOnAwake)
        {
            BuildBattlePanel();
        }

        BindController();
        SetVisible(showOnStart);
    }

    [ContextMenu("Build Battle MVP Panel")]
    public void BuildBattlePanel()
    {
        if (panelRoot == null)
        {
            panelRoot = CreatePanelRoot();
        }

        ClearChildren(panelRoot);
        Image panelImage = EnsureImage(panelRoot.gameObject, new Color(0.02f, 0.08f, 0.12f, 0.94f));
        panelImage.raycastTarget = true;

        VerticalLayoutGroup rootLayout = EnsureVerticalLayout(panelRoot.gameObject, 10f, 16, 16, 14, 14);
        rootLayout.childForceExpandWidth = true;
        rootLayout.childForceExpandHeight = false;
        rootLayout.childControlWidth = true;
        rootLayout.childControlHeight = true;

        CreateTitle(panelRoot, "Source of Thought - Battle Prep Debug");

        RectTransform controls = CreateBlock(panelRoot, "HeaderPanel", 54f);
        HorizontalLayoutGroup controlsLayout = EnsureHorizontalLayout(controls.gameObject, 12f, 0, 0, 0, 0);
        controlsLayout.childForceExpandWidth = false;
        controlsLayout.childControlWidth = true;
        controlsLayout.childControlHeight = true;

        startBattleButton = CreateButton(controls, "Simulate Battle", new Vector2(190f, 44f));
        startBattleButton.onClick.AddListener(OnStartBattleClicked);

        resetPlacementButton = CreateButton(controls, "Reset / Reposition", new Vector2(210f, 44f));
        resetPlacementButton.onClick.AddListener(OnResetPlacementClicked);

        toggleVisibilityButton = CreateButton(controls, "Hide Battle UI", new Vector2(180f, 44f));
        toggleVisibilityButton.onClick.AddListener(ToggleVisible);

        turnText = CreateText(controls, "TurnText", "Turn 0", 20, new Color(0.78f, 1f, 1f, 1f));
        turnText.alignment = TextAlignmentOptions.Right;
        AddPreferredSize(turnText.gameObject, 180f, 44f);

        warningText = CreateText(panelRoot, "WarningText", "", 16, new Color(1f, 0.75f, 0.18f, 1f));
        AddPreferredHeight(warningText.gameObject, 24f);
        warningText.gameObject.SetActive(false);

        RectTransform decks = CreateBlock(panelRoot, "DeckPanels", 210f);
        HorizontalLayoutGroup decksLayout = EnsureHorizontalLayout(decks.gameObject, 12f, 0, 0, 0, 0);
        decksLayout.childForceExpandWidth = true;
        decksLayout.childControlWidth = true;
        decksLayout.childControlHeight = true;

        playerDeckRoot = CreateDeckPanel(decks, "Player Deck");
        enemyDeckRoot = CreateDeckPanel(decks, "Enemy Deck");

        RectTransform gridPanel = CreateBlock(panelRoot, "BattleGridPanel", 360f);
        EnsureVerticalLayout(gridPanel.gameObject, 8f, 8, 8, 8, 8);
        CreateHeading(gridPanel, "Battle Grid");
        gridRoot = CreateContainer(gridPanel, "BattleGrid");
        AddPreferredHeight(gridRoot.gameObject, 310f);
        GridLayoutGroup gridLayout = gridRoot.gameObject.AddComponent<GridLayoutGroup>();
        gridLayout.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        gridLayout.constraintCount = 5;
        gridLayout.cellSize = new Vector2(140f, 56f);
        gridLayout.spacing = new Vector2(6f, 6f);
        gridLayout.childAlignment = TextAnchor.MiddleCenter;

        battleResultText = CreateText(panelRoot, "BattleResultText", "Battle not started.", 18, new Color(0.64f, 0.94f, 1f, 1f));
        AddPreferredHeight(battleResultText.gameObject, 34f);

        RectTransform summaryBlock = CreateBlock(panelRoot, "SummaryPanel", 104f);
        battleSummaryView = summaryBlock.gameObject.AddComponent<ThoughtMapBattleSummaryView>();
        battleSummaryView.BuildIfNeeded();
        battleSummaryView.ShowPending();

        RectTransform logBlock = CreateBlock(panelRoot, "BattleLogPanel", 190f);
        battleLogPanelLayout = logBlock.GetComponent<LayoutElement>();
        EnsureVerticalLayout(logBlock.gameObject, 8f, 8, 8, 8, 8);
        CreateDebugLogHeader(logBlock);
        battleLogText = CreateBattleLogScrollView(logBlock);

        BindController();
    }

    public void SetVisible(bool visible)
    {
        if (panelRoot != null)
        {
            panelRoot.gameObject.SetActive(visible);
        }
    }

    public void ToggleVisible()
    {
        if (panelRoot == null)
        {
            return;
        }
        SetVisible(!panelRoot.gameObject.activeSelf);
    }

    private void OnStartBattleClicked()
    {
        if (controller == null)
        {
            if (warningText != null)
            {
                warningText.text = "Battle controller is not assigned.";
                warningText.gameObject.SetActive(true);
            }
            Debug.LogWarning("[ThoughtMapBattleUI] Battle controller is not assigned.", this);
            return;
        }

        BindController();
        controller.Run();
    }

    private void OnResetPlacementClicked()
    {
        if (controller == null)
        {
            return;
        }

        BindController();
        controller.ResetPlacementMode();
    }

    private void BindController()
    {
        if (controller == null)
        {
            return;
        }

        controller.SetUiTargets(
            playerDeckRoot,
            enemyDeckRoot,
            battleLogText,
            battleLogScrollRect,
            battleResultText,
            battleSummaryView,
            turnText,
            warningText,
            gridRoot
        );
    }

    private RectTransform CreatePanelRoot()
    {
        GameObject panelObject = new GameObject("ThoughtMapBattlePanel", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        RectTransform rect = panelObject.GetComponent<RectTransform>();
        Transform parent = transform;
        Canvas canvas = GetComponentInParent<Canvas>();
        if (canvas != null)
        {
            parent = canvas.transform;
        }
        rect.SetParent(parent, false);
        rect.anchorMin = new Vector2(0.5f, 0.5f);
        rect.anchorMax = new Vector2(0.5f, 0.5f);
        rect.pivot = new Vector2(0.5f, 0.5f);
        rect.sizeDelta = defaultSize;
        rect.anchoredPosition = defaultPosition;
        return rect;
    }

    private void CreateTitle(RectTransform parent, string title)
    {
        TMP_Text text = CreateText(parent, "Title", title, 24, new Color(0.72f, 0.96f, 1f, 1f));
        text.fontStyle = FontStyles.Bold;
        AddPreferredHeight(text.gameObject, 38f);
    }

    private RectTransform CreateDeckPanel(RectTransform parent, string label)
    {
        RectTransform block = CreateBlock(parent, label.Replace(" ", "") + "Panel", 0f);
        VerticalLayoutGroup layout = EnsureVerticalLayout(block.gameObject, 8f, 8, 8, 8, 8);
        layout.childForceExpandWidth = true;
        layout.childControlWidth = true;
        layout.childControlHeight = true;

        CreateHeading(block, label);
        RectTransform scrollRect = CreateDeckScrollView(block, label.Replace(" ", "") + "ScrollView", out RectTransform content);
        return content;
    }

    private RectTransform CreateDeckScrollView(RectTransform parent, string name, out RectTransform content)
    {
        GameObject scrollObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ScrollRect));
        RectTransform scrollRect = scrollObject.GetComponent<RectTransform>();
        scrollRect.SetParent(parent, false);
        AddPreferredHeight(scrollObject, 158f);
        Image scrollImage = scrollObject.GetComponent<Image>();
        scrollImage.color = new Color(0.01f, 0.07f, 0.10f, 0.9f);

        GameObject viewportObject = new GameObject("Viewport", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Mask));
        RectTransform viewport = viewportObject.GetComponent<RectTransform>();
        viewport.SetParent(scrollRect, false);
        Stretch(viewport, 6f, 6f);
        Image viewportImage = viewportObject.GetComponent<Image>();
        viewportImage.color = new Color(0f, 0f, 0f, 0.04f);
        viewportObject.GetComponent<Mask>().showMaskGraphic = false;

        GameObject contentObject = new GameObject("Content", typeof(RectTransform), typeof(GridLayoutGroup), typeof(ContentSizeFitter));
        content = contentObject.GetComponent<RectTransform>();
        content.SetParent(viewport, false);
        content.anchorMin = new Vector2(0f, 1f);
        content.anchorMax = new Vector2(1f, 1f);
        content.pivot = new Vector2(0.5f, 1f);
        content.offsetMin = new Vector2(0f, 0f);
        content.offsetMax = new Vector2(0f, 0f);

        GridLayoutGroup grid = contentObject.GetComponent<GridLayoutGroup>();
        grid.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
        grid.constraintCount = 5;
        grid.cellSize = new Vector2(128f, 70f);
        grid.spacing = new Vector2(8f, 8f);
        grid.childAlignment = TextAnchor.UpperCenter;

        ContentSizeFitter fitter = contentObject.GetComponent<ContentSizeFitter>();
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        ScrollRect scroll = scrollObject.GetComponent<ScrollRect>();
        scroll.viewport = viewport;
        scroll.content = content;
        scroll.horizontal = false;
        scroll.vertical = true;
        scroll.movementType = ScrollRect.MovementType.Clamped;
        return scrollRect;
    }

    private TMP_Text CreateBattleLogScrollView(RectTransform parent)
    {
        GameObject scrollObject = new GameObject("BattleLogScrollView", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(ScrollRect));
        RectTransform scrollRect = scrollObject.GetComponent<RectTransform>();
        scrollRect.SetParent(parent, false);
        battleLogScrollRoot = scrollRect;
        AddPreferredHeight(scrollObject, 154f);
        Image scrollImage = scrollObject.GetComponent<Image>();
        scrollImage.color = new Color(0.01f, 0.07f, 0.10f, 0.92f);

        GameObject viewportObject = new GameObject("Viewport", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Mask));
        RectTransform viewport = viewportObject.GetComponent<RectTransform>();
        viewport.SetParent(scrollRect, false);
        Stretch(viewport, 10f, 8f);
        Image viewportImage = viewportObject.GetComponent<Image>();
        viewportImage.color = new Color(0f, 0f, 0f, 0.08f);
        viewportObject.GetComponent<Mask>().showMaskGraphic = false;

        GameObject contentObject = new GameObject("Content", typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI), typeof(ContentSizeFitter));
        RectTransform content = contentObject.GetComponent<RectTransform>();
        content.SetParent(viewport, false);
        content.anchorMin = new Vector2(0f, 1f);
        content.anchorMax = new Vector2(1f, 1f);
        content.pivot = new Vector2(0.5f, 1f);
        content.offsetMin = new Vector2(10f, 0f);
        content.offsetMax = new Vector2(-10f, 0f);

        TMP_Text text = contentObject.GetComponent<TMP_Text>();
        text.text = "Press Simulate Battle to run the 5v5 prep preview.";
        text.fontSize = 14;
        text.color = Color.white;
        text.alignment = TextAlignmentOptions.TopLeft;
        text.enableWordWrapping = true;
        ContentSizeFitter fitter = contentObject.GetComponent<ContentSizeFitter>();
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;

        ScrollRect scroll = scrollObject.GetComponent<ScrollRect>();
        battleLogScrollRect = scroll;
        scroll.viewport = viewport;
        scroll.content = content;
        scroll.horizontal = false;
        scroll.vertical = true;
        return text;
    }

    private void CreateDebugLogHeader(RectTransform parent)
    {
        RectTransform header = CreateContainer(parent, "DebugLogHeader");
        AddPreferredHeight(header.gameObject, 34f);
        HorizontalLayoutGroup layout = EnsureHorizontalLayout(header.gameObject, 8f, 0, 0, 0, 0);
        layout.childForceExpandWidth = false;
        layout.childControlWidth = true;
        layout.childControlHeight = true;

        TMP_Text heading = CreateText(header, "DebugLogHeading", "Debug Log", 16, new Color(0.72f, 0.96f, 1f, 1f));
        heading.fontStyle = FontStyles.Bold;
        AddPreferredSize(heading.gameObject, 380f, 30f);

        collapseLogButton = CreateButton(header, "Collapse", new Vector2(112f, 30f));
        collapseLogButton.onClick.AddListener(ToggleLogCollapsed);
        Button clearButton = CreateButton(header, "Clear Log", new Vector2(112f, 30f));
        clearButton.onClick.AddListener(ClearLog);
        Button copyButton = CreateButton(header, "Copy Log", new Vector2(112f, 30f));
        copyButton.onClick.AddListener(CopyLog);
        Button exportButton = CreateButton(header, "Export Log", new Vector2(124f, 30f));
        exportButton.onClick.AddListener(ExportLog);
    }

    private void ToggleLogCollapsed()
    {
        logCollapsed = !logCollapsed;
        if (battleLogScrollRoot != null)
        {
            battleLogScrollRoot.gameObject.SetActive(!logCollapsed);
        }
        if (battleLogPanelLayout != null)
        {
            battleLogPanelLayout.preferredHeight = logCollapsed ? 52f : 190f;
            battleLogPanelLayout.minHeight = logCollapsed ? 52f : 60f;
        }
        if (collapseLogButton != null)
        {
            TMP_Text label = collapseLogButton.GetComponentInChildren<TMP_Text>();
            if (label != null)
            {
                label.text = logCollapsed ? "Expand" : "Collapse";
            }
        }
    }

    private void ClearLog()
    {
        if (battleLogText != null)
        {
            battleLogText.text = "";
        }
    }

    private void CopyLog()
    {
        GUIUtility.systemCopyBuffer = battleLogText == null ? "" : battleLogText.text;
    }

    private void ExportLog()
    {
        string path = Path.Combine(Application.persistentDataPath, "source_of_thought_battle_log.txt");
        File.WriteAllText(path, battleLogText == null ? "" : battleLogText.text);
        Debug.Log("[ThoughtMapBattleUI] Exported battle log: " + path, this);
    }

    private RectTransform CreateBlock(RectTransform parent, string name, float preferredHeight)
    {
        GameObject blockObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        RectTransform rect = blockObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        Image image = blockObject.GetComponent<Image>();
        image.color = new Color(0.0f, 0.18f, 0.26f, 0.72f);
        image.raycastTarget = false;
        if (preferredHeight > 0f)
        {
            AddPreferredHeight(blockObject, preferredHeight);
        }
        return rect;
    }

    private RectTransform CreateContainer(RectTransform parent, string name)
    {
        GameObject containerObject = new GameObject(name, typeof(RectTransform));
        RectTransform rect = containerObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        return rect;
    }

    private TMP_Text CreateHeading(RectTransform parent, string value)
    {
        TMP_Text text = CreateText(parent, value.Replace(" ", "") + "Heading", value, 16, new Color(0.72f, 0.96f, 1f, 1f));
        text.fontStyle = FontStyles.Bold;
        AddPreferredHeight(text.gameObject, 24f);
        return text;
    }

    private Button CreateButton(RectTransform parent, string label, Vector2 size)
    {
        GameObject buttonObject = new GameObject(label.Replace(" ", "") + "Button", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button));
        RectTransform rect = buttonObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        rect.sizeDelta = size;
        Image image = buttonObject.GetComponent<Image>();
        image.color = new Color(0.0f, 0.32f, 0.45f, 0.95f);
        Button button = buttonObject.GetComponent<Button>();
        ColorBlock colors = button.colors;
        colors.normalColor = image.color;
        colors.highlightedColor = new Color(0.0f, 0.56f, 0.78f, 1f);
        colors.pressedColor = new Color(0.0f, 0.76f, 0.92f, 1f);
        button.colors = colors;
        AddPreferredSize(buttonObject, size.x, size.y);

        TMP_Text text = CreateText(rect, "Label", label, 16, Color.white);
        text.alignment = TextAlignmentOptions.Center;
        Stretch(text.rectTransform);
        return button;
    }

    private TMP_Text CreateText(RectTransform parent, string name, string value, int size, Color color)
    {
        GameObject textObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = size;
        text.color = color;
        text.alignment = TextAlignmentOptions.Left;
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
        LayoutElement layout = target.GetComponent<LayoutElement>();
        if (layout == null)
        {
            layout = target.AddComponent<LayoutElement>();
        }
        layout.preferredHeight = height;
        layout.minHeight = Mathf.Min(height, 60f);
    }

    private void AddPreferredSize(GameObject target, float width, float height)
    {
        LayoutElement layout = target.GetComponent<LayoutElement>();
        if (layout == null)
        {
            layout = target.AddComponent<LayoutElement>();
        }
        layout.preferredWidth = width;
        layout.preferredHeight = height;
        layout.minWidth = width;
        layout.minHeight = height;
    }

    private void Stretch(RectTransform rect)
    {
        Stretch(rect, 10f, 8f);
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
