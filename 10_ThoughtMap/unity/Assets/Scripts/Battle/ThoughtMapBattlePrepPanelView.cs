using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ThoughtMapBattlePrepPanelView : MonoBehaviour
{
    [Header("Controller")]
    [SerializeField] private ThoughtMapBattlePrepController controller;

    [Header("Runtime UI")]
    [SerializeField] private bool buildOnAwake = true;
    [SerializeField] private RectTransform panelRoot;
    [SerializeField] private Vector2 defaultSize = new Vector2(1180f, 900f);
    [SerializeField] private Vector2 defaultPosition = Vector2.zero;

    [Header("Generated References")]
    [SerializeField] private TMP_Text savedWorksListText;
    [SerializeField] private TMP_Text cardPreviewText;
    [SerializeField] private TMP_Text deckSlotsText;
    [SerializeField] private TMP_Text deploySlotsText;
    [SerializeField] private TMP_Text placementPreviewText;
    [SerializeField] private TMP_Text statusText;

    private void Awake()
    {
        if (controller == null)
        {
            controller = GetComponent<ThoughtMapBattlePrepController>();
        }

        if (buildOnAwake)
        {
            BuildPanel();
        }

        BindController();
    }

    [ContextMenu("Build Battle Prep Panel")]
    public void BuildPanel()
    {
        if (panelRoot == null)
        {
            panelRoot = CreatePanelRoot();
        }

        ClearChildren(panelRoot);
        EnsureImage(panelRoot.gameObject, new Color(0.015f, 0.07f, 0.11f, 0.96f));

        VerticalLayoutGroup rootLayout = EnsureVerticalLayout(panelRoot.gameObject, 14f, 18, 18, 18, 18);
        rootLayout.childForceExpandWidth = true;
        rootLayout.childForceExpandHeight = false;
        rootLayout.childControlWidth = true;
        rootLayout.childControlHeight = true;

        TMP_Text title = CreateText(panelRoot, "Title", "Source of Thought - Battle Prep", 28, new Color(0.72f, 0.96f, 1f, 1f));
        title.fontStyle = FontStyles.Bold;
        AddPreferredHeight(title.gameObject, 44f);

        RectTransform controls = CreateBlock(panelRoot, "Controls", 58f);
        HorizontalLayoutGroup controlsLayout = EnsureHorizontalLayout(controls.gameObject, 12f, 0, 0, 0, 0);
        controlsLayout.childForceExpandWidth = false;
        controlsLayout.childControlWidth = true;
        controlsLayout.childControlHeight = true;

        CreateButton(controls, "Generate Cards", new Vector2(180f, 44f), () => controller?.GenerateCards());
        CreateButton(controls, "Save Deck", new Vector2(160f, 44f), () => controller?.SaveDeck());
        CreateButton(controls, "Start Battle", new Vector2(160f, 44f), () => controller?.StartBattle());

        RectTransform topRow = CreateBlock(panelRoot, "TopRow", 220f);
        HorizontalLayoutGroup topLayout = EnsureHorizontalLayout(topRow.gameObject, 12f, 0, 0, 0, 0);
        topLayout.childForceExpandWidth = true;
        topLayout.childControlWidth = true;
        topLayout.childControlHeight = true;

        savedWorksListText = CreatePanelText(topRow, "SavedWorksList", "Saved Works List\nPress Generate Cards.");
        cardPreviewText = CreatePanelText(topRow, "CardPreview", "Card Preview\nNo cards loaded.");

        RectTransform middleRow = CreateBlock(panelRoot, "MiddleRow", 280f);
        HorizontalLayoutGroup middleLayout = EnsureHorizontalLayout(middleRow.gameObject, 12f, 0, 0, 0, 0);
        middleLayout.childForceExpandWidth = true;
        middleLayout.childControlWidth = true;
        middleLayout.childControlHeight = true;

        deckSlotsText = CreatePanelText(middleRow, "DeckSlots10", "Deck Slots 10\nNo cards loaded.");
        deploySlotsText = CreatePanelText(middleRow, "DeploySlots5", "Deploy Slots 5\nNo cards loaded.");

        RectTransform bottomRow = CreateBlock(panelRoot, "BottomRow", 210f);
        HorizontalLayoutGroup bottomLayout = EnsureHorizontalLayout(bottomRow.gameObject, 12f, 0, 0, 0, 0);
        bottomLayout.childForceExpandWidth = true;
        bottomLayout.childControlWidth = true;
        bottomLayout.childControlHeight = true;

        placementPreviewText = CreatePanelText(bottomRow, "PlacementPreview", "5x5 Placement Preview\nNo cards loaded.");
        statusText = CreatePanelText(bottomRow, "StatusWarningText", "Status / Warning Text\nReady.");

        BindController();
    }

    private void BindController()
    {
        if (controller == null)
        {
            return;
        }

        controller.SetUiTargets(
            savedWorksListText,
            cardPreviewText,
            deckSlotsText,
            deploySlotsText,
            placementPreviewText,
            statusText
        );
    }

    private RectTransform CreatePanelRoot()
    {
        GameObject panelObject = new GameObject("BattlePrepPanel", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
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

    private TMP_Text CreatePanelText(RectTransform parent, string name, string value)
    {
        RectTransform block = CreateBlock(parent, name + "Block", 0f);
        TMP_Text text = CreateText(block, name + "Text", value, 14, Color.white);
        text.alignment = TextAlignmentOptions.TopLeft;
        text.enableWordWrapping = true;
        Stretch(text.rectTransform);
        return text;
    }

    private Button CreateButton(RectTransform parent, string label, Vector2 size, UnityEngine.Events.UnityAction onClick)
    {
        GameObject buttonObject = new GameObject(label.Replace(" ", "") + "Button", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button));
        RectTransform rect = buttonObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        Image image = buttonObject.GetComponent<Image>();
        image.color = new Color(0.0f, 0.32f, 0.45f, 0.95f);
        Button button = buttonObject.GetComponent<Button>();
        button.onClick.AddListener(onClick);
        AddPreferredSize(buttonObject, size.x, size.y);

        TMP_Text text = CreateText(rect, "Label", label, 16, Color.white);
        text.alignment = TextAlignmentOptions.Center;
        Stretch(text.rectTransform);
        return button;
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
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = new Vector2(10f, 8f);
        rect.offsetMax = new Vector2(-10f, -8f);
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
