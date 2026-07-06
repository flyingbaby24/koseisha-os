using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

[DisallowMultipleComponent]
public class SearchHeaderV2View : MonoBehaviour
{
    [Header("Runtime Build")]
    [SerializeField] private bool buildOnAwake = true;
    [SerializeField] private Vector2 defaultPosition = new Vector2(-310f, 320f);
    [SerializeField] private Vector2 defaultSize = new Vector2(820f, 260f);

    [Header("Fonts")]
    [SerializeField] private TMP_FontAsset japaneseFontAsset;
    [SerializeField] private TMP_Text fontReferenceText;

    [Header("Options")]
    [SerializeField] private string[] modeOptions = { "semantic", "keyword", "hybrid" };
    [SerializeField] private string[] sourceOptions = { "all", "gutendex", "user_suno" };
    [SerializeField] private string[] filterOptions = { "all", "general", "basic_thought", "basic_literature", "jinn_os" };
    [SerializeField] private string defaultQuery = "";
    [SerializeField] private int defaultLimit = 10;
    [SerializeField] private bool showFileDropArea = true;
    [TextArea(2, 3)]
    [SerializeField] private string fileDropMessage = "Drop text / CSV / JSON file here\nor click to select file";

    [Header("Style")]
    [SerializeField] private Color panelColor = new Color(0.012f, 0.045f, 0.10f, 0.88f);
    [SerializeField] private Color titleBarColor = new Color(0.015f, 0.075f, 0.16f, 0.92f);
    [SerializeField] private Color controlColor = new Color(0.018f, 0.05f, 0.11f, 0.96f);
    [SerializeField] private Color textPrimary = new Color(0.92f, 0.98f, 1f, 1f);
    [SerializeField] private Color textSecondary = new Color(0.60f, 0.78f, 0.92f, 1f);
    [SerializeField] private Color cyan = new Color(0.05f, 0.82f, 1f, 0.8f);
    [SerializeField] private int padding = 14;
    [SerializeField] private int spacing = 10;
    [SerializeField] private float modeWidth = 128f;
    [SerializeField] private float sourceWidth = 138f;
    [SerializeField] private float filterWidth = 150f;
    [SerializeField] private float keywordMinWidth = 260f;
    [SerializeField] private float limitWidth = 86f;
    [SerializeField] private float searchButtonWidth = 110f;

    [Header("Window Interaction")]
    [SerializeField] private bool enableDragging = true;
    [SerializeField] private bool enableWindowMotion = true;
    [SerializeField] private bool enableResizing = true;
    [SerializeField] private Vector2 minWindowSize = new Vector2(680f, 220f);

    private TMP_InputField searchInput;
    private TMP_InputField limitInput;
    private TMP_Dropdown modeDropdown;
    private TMP_Dropdown sourceDropdown;
    private TMP_Dropdown filterDropdown;
    private Button searchButton;
    private TMP_Text fileDropText;

    public event Action SearchRequested;

    public string QueryText => searchInput == null ? string.Empty : searchInput.text;
    public string SelectedMode => GetDropdownValue(modeDropdown, "semantic");
    public string SelectedSource => GetDropdownValue(sourceDropdown, "all");
    public string SelectedFilter => GetDropdownValue(filterDropdown, "all");
    public int SelectedLimit => GetLimitValue();

    private void Awake()
    {
        if (buildOnAwake) BuildIfNeeded();
    }

    private void OnDestroy()
    {
        if (searchButton != null) searchButton.onClick.RemoveListener(HandleSearchClicked);
    }

    public void BuildIfNeeded()
    {
        ApplyDefaultWindowRect();

        if (searchInput != null || transform.Find("WindowContent") != null)
        {
            if (!HasCurrentLayout())
            {
                RemoveGeneratedLayout();
            }
            else
            {
                CacheReferences();
                EnsureWindowFeatures();
                return;
            }
        }

        if (searchInput != null || transform.Find("WindowContent") != null)
        {
            CacheReferences();
            EnsureWindowFeatures();
            return;
        }
        Image panel = GetComponent<Image>();
        if (panel == null) panel = gameObject.AddComponent<Image>();
        panel.color = panelColor;
        Outline outline = GetComponent<Outline>();
        if (outline == null) outline = gameObject.AddComponent<Outline>();
        outline.effectColor = cyan;
        outline.effectDistance = new Vector2(1.2f, -1.2f);
        RectTransform content = CreateContainer(transform, "WindowContent", true);
        ConfigureVertical(content, padding, spacing);
        RectTransform titleBar = CreateBlock(content, "TitleBar", titleBarColor, 42f);
        CreateText(titleBar, "TitleText", "ThoughtMap Search", 18, FontStyles.Bold, textPrimary);

        RectTransform topRow = CreateContainer(content, "SearchTopRow", false);
        ConfigureHorizontal(topRow, padding, spacing);
        AddLayout(topRow.gameObject, 0f, 66f, false);

        RectTransform modeField = CreateLabeledField(topRow, "ModeField", "Mode", modeWidth, false);
        modeDropdown = CreateDropdown(modeField, "ModeDropdown", modeOptions, 0f);

        RectTransform sourceField = CreateLabeledField(topRow, "SourceField", "Source", sourceWidth, false);
        sourceDropdown = CreateDropdown(sourceField, "SourceDropdown", sourceOptions, 0f);

        RectTransform filterField = CreateLabeledField(topRow, "FilterField", "Filter", filterWidth, false);
        filterDropdown = CreateDropdown(filterField, "FilterDropdown", filterOptions, 0f);

        RectTransform spacer = CreateContainer(topRow, "TopRowSpacer", false);
        AddLayout(spacer.gameObject, 0f, 64f, false);

        RectTransform limitField = CreateLabeledField(topRow, "LimitField", "Limit", limitWidth, false);
        limitInput = CreateInput(limitField, "LimitInput", Mathf.Max(1, defaultLimit).ToString(), 0f);
        if (limitInput != null)
        {
            limitInput.contentType = TMP_InputField.ContentType.IntegerNumber;
        }

        RectTransform actionField = CreateLabeledField(topRow, "ActionField", " ", searchButtonWidth, false);
        searchButton = CreateButton(actionField, "SearchButton", "Search", new Vector2(0f, 42f));
        searchButton.onClick.AddListener(HandleSearchClicked);

        RectTransform keywordRow = CreateContainer(content, "KeywordRow", false);
        ConfigureHorizontal(keywordRow, padding, spacing);
        AddLayout(keywordRow.gameObject, 0f, 74f, false);
        RectTransform keywordField = CreateLabeledField(keywordRow, "KeywordField", "Search Keyword", keywordMinWidth, true);
        searchInput = CreateInput(keywordField, "SearchInput", defaultQuery, 0f);

        if (showFileDropArea)
        {
            RectTransform fileDrop = CreateBlock(content, "FileDropArea", titleBarColor, 58f);
            Outline fileOutline = fileDrop.GetComponent<Outline>();
            if (fileOutline == null) fileOutline = fileDrop.gameObject.AddComponent<Outline>();
            fileOutline.effectColor = new Color(cyan.r, cyan.g, cyan.b, 0.75f);
            fileOutline.effectDistance = new Vector2(1.5f, -1.5f);
            Button fileButton = fileDrop.gameObject.AddComponent<Button>();
            fileButton.onClick.AddListener(HandleFileDropClicked);
            fileDropText = CreateText(fileDrop, "FileDropText", fileDropMessage + "\nFile input: placeholder", 13, FontStyles.Normal, textSecondary);
            fileDropText.alignment = TextAlignmentOptions.Center;
        }

        EnsureWindowFeatures();
    }

    public void SetInteractable(bool value)
    {
        if (searchButton != null) searchButton.interactable = value;
        if (searchInput != null) searchInput.interactable = value;
        if (modeDropdown != null) modeDropdown.interactable = value;
        if (sourceDropdown != null) sourceDropdown.interactable = value;
        if (filterDropdown != null) filterDropdown.interactable = value;
        if (limitInput != null) limitInput.interactable = value;
    }

    private TMP_InputField CreateInput(Transform parent, string name, string value, float width)
    {
        GameObject root = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(TMP_InputField));
        root.transform.SetParent(parent, false);
        AddLayout(root, width, 42f, width > 0f);
        Image image = root.GetComponent<Image>();
        image.color = controlColor;
        Outline outline = root.AddComponent<Outline>();
        outline.effectColor = cyan;
        outline.effectDistance = new Vector2(1f, -1f);
        TMP_InputField input = root.GetComponent<TMP_InputField>();
        RectTransform textArea = CreateContainer(root.transform, "Text Area", true);
        textArea.offsetMin = new Vector2(10f, 4f);
        textArea.offsetMax = new Vector2(-10f, -4f);
        TMP_Text text = CreateText(textArea, "Text", value, 16, FontStyles.Normal, textPrimary);
        TMP_Text placeholder = CreateText(textArea, "Placeholder", "keyword", 16, FontStyles.Normal, new Color(textSecondary.r, textSecondary.g, textSecondary.b, 0.55f));
        input.textViewport = textArea;
        input.textComponent = text;
        input.placeholder = placeholder;
        input.text = value;
        return input;
    }

    private TMP_Dropdown CreateDropdown(Transform parent, string name, string[] options, float width)
    {
        GameObject root = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(TMP_Dropdown));
        root.transform.SetParent(parent, false);
        AddLayout(root, width, 42f, width > 0f);
        Image image = root.GetComponent<Image>();
        image.color = controlColor;
        Outline outline = root.AddComponent<Outline>();
        outline.effectColor = cyan;
        outline.effectDistance = new Vector2(1f, -1f);
        TMP_Dropdown dropdown = root.GetComponent<TMP_Dropdown>();
        TMP_Text label = CreateText(root.transform, "Label", string.Empty, 15, FontStyles.Normal, textPrimary);
        RectTransform labelRect = label.rectTransform;
        labelRect.anchorMin = Vector2.zero;
        labelRect.anchorMax = Vector2.one;
        labelRect.offsetMin = new Vector2(10f, 0f);
        labelRect.offsetMax = new Vector2(-10f, 0f);
        label.alignment = TextAlignmentOptions.MidlineLeft;
        dropdown.captionText = label;
        BuildDropdownTemplate(root.transform, dropdown);
        dropdown.ClearOptions();
        dropdown.AddOptions(new List<string>(options));
        dropdown.value = 0;
        dropdown.RefreshShownValue();
        return dropdown;
    }

    private void BuildDropdownTemplate(Transform parent, TMP_Dropdown dropdown)
    {
        RectTransform template = CreateContainer(parent, "Template", false);
        template.anchorMin = new Vector2(0f, 0f);
        template.anchorMax = new Vector2(1f, 0f);
        template.pivot = new Vector2(0.5f, 1f);
        template.anchoredPosition = new Vector2(0f, -4f);
        template.sizeDelta = new Vector2(0f, 180f);
        Image templateImage = template.gameObject.AddComponent<Image>();
        templateImage.color = panelColor;
        ScrollRect scroll = template.gameObject.AddComponent<ScrollRect>();
        RectTransform viewport = CreateContainer(template, "Viewport", true);
        Mask mask = viewport.gameObject.AddComponent<Mask>();
        mask.showMaskGraphic = false;
        Image viewportImage = viewport.gameObject.AddComponent<Image>();
        viewportImage.color = new Color(1f, 1f, 1f, 0.02f);
        RectTransform content = CreateContainer(viewport, "Content", false);
        content.anchorMin = new Vector2(0f, 1f);
        content.anchorMax = new Vector2(1f, 1f);
        content.pivot = new Vector2(0.5f, 1f);
        content.offsetMin = Vector2.zero;
        content.offsetMax = Vector2.zero;
        ConfigureVertical(content, 4, 2);
        ContentSizeFitter fitter = content.gameObject.AddComponent<ContentSizeFitter>();
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        RectTransform item = CreateContainer(content, "Item", false);
        AddLayout(item.gameObject, 0f, 32f, false);
        Toggle toggle = item.gameObject.AddComponent<Toggle>();
        Image itemImage = item.gameObject.AddComponent<Image>();
        itemImage.color = controlColor;
        toggle.targetGraphic = itemImage;
        TMP_Text itemText = CreateText(item, "Item Label", "Option", 14, FontStyles.Normal, textPrimary);
        RectTransform itemTextRect = itemText.rectTransform;
        itemTextRect.anchorMin = Vector2.zero;
        itemTextRect.anchorMax = Vector2.one;
        itemTextRect.offsetMin = new Vector2(8f, 0f);
        itemTextRect.offsetMax = new Vector2(-8f, 0f);
        itemText.alignment = TextAlignmentOptions.MidlineLeft;
        scroll.viewport = viewport;
        scroll.content = content;
        scroll.horizontal = false;
        dropdown.template = template;
        dropdown.itemText = itemText;
        template.gameObject.SetActive(false);
    }

    private Button CreateButton(Transform parent, string name, string label, Vector2 size)
    {
        GameObject root = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button), typeof(NeonHoverGlow));
        root.transform.SetParent(parent, false);
        AddLayout(root, size.x, size.y, size.x > 0f);
        Image image = root.GetComponent<Image>();
        image.color = controlColor;
        TMP_Text text = CreateText(root.transform, "Label", label, 15, FontStyles.Normal, textPrimary);
        RectTransform textRect = text.rectTransform;
        textRect.anchorMin = Vector2.zero;
        textRect.anchorMax = Vector2.one;
        textRect.offsetMin = Vector2.zero;
        textRect.offsetMax = Vector2.zero;
        text.alignment = TextAlignmentOptions.Center;
        return root.GetComponent<Button>();
    }

    private RectTransform CreateBlock(RectTransform parent, string name, Color color, float height)
    {
        RectTransform rect = CreateContainer(parent, name, false);
        Image image = rect.gameObject.AddComponent<Image>();
        image.color = color;
        AddLayout(rect.gameObject, 0f, height, false);
        ConfigureVertical(rect, 10, 4);
        return rect;
    }

    private RectTransform CreateLabeledField(RectTransform parent, string name, string label, float width, bool flexibleWidth)
    {
        RectTransform field = CreateContainer(parent, name, false);
        AddLayout(field.gameObject, width, 64f, !flexibleWidth);
        LayoutElement layout = field.GetComponent<LayoutElement>();
        if (layout != null)
        {
            layout.minWidth = flexibleWidth ? width : layout.minWidth;
            layout.flexibleWidth = flexibleWidth ? 1f : 0f;
        }

        ConfigureVertical(field, 0, 4);
        TMP_Text labelText = CreateText(field, "Label", label, 12, FontStyles.Normal, textSecondary);
        labelText.alignment = TextAlignmentOptions.Left;
        AddLayout(labelText.gameObject, 0f, 18f, false);
        return field;
    }

    private RectTransform CreateContainer(Transform parent, string name, bool stretch)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform));
        RectTransform rect = obj.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        if (stretch)
        {
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;
        }
        return rect;
    }

    private TMP_Text CreateText(Transform parent, string name, string value, int size, FontStyles style, Color color)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        obj.transform.SetParent(parent, false);
        TMP_Text text = obj.GetComponent<TMP_Text>();
        ApplyFont(text);
        text.text = value;
        text.fontSize = size;
        text.fontStyle = style;
        text.color = color;
        text.enableWordWrapping = true;
        text.overflowMode = TextOverflowModes.Ellipsis;
        text.raycastTarget = false;
        return text;
    }

    private void ConfigureVertical(RectTransform target, int pad, int gap)
    {
        VerticalLayoutGroup layout = target.gameObject.AddComponent<VerticalLayoutGroup>();
        layout.padding = new RectOffset(pad, pad, pad, pad);
        layout.spacing = gap;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;
    }

    private void ConfigureHorizontal(RectTransform target, int pad, int gap)
    {
        HorizontalLayoutGroup layout = target.gameObject.AddComponent<HorizontalLayoutGroup>();
        layout.padding = new RectOffset(pad, pad, pad, pad);
        layout.spacing = gap;
        layout.childAlignment = TextAnchor.MiddleLeft;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = false;
        layout.childForceExpandHeight = false;
    }

    private void AddLayout(GameObject obj, float width, float height, bool setWidth)
    {
        LayoutElement layout = obj.GetComponent<LayoutElement>();
        if (layout == null) layout = obj.AddComponent<LayoutElement>();
        if (setWidth)
        {
            layout.preferredWidth = width;
            layout.minWidth = width;
        }
        else
        {
            layout.flexibleWidth = 1f;
        }
        layout.preferredHeight = height;
        layout.minHeight = height;
    }

    private void HandleSearchClicked()
    {
        Debug.Log($"[SearchHeaderV2] V2 search requested query={QueryText} mode={SelectedMode} source={SelectedSource} filter={SelectedFilter}", this);
        SearchRequested?.Invoke();
    }

    private void HandleFileDropClicked()
    {
        Debug.Log("[SearchHeaderV2] File Drop Area clicked. File selection is a future extension point.", this);
        SetText(fileDropText, fileDropMessage + "\nFile input: placeholder only");
    }

    private string GetDropdownValue(TMP_Dropdown dropdown, string fallback)
    {
        if (dropdown == null || dropdown.options == null || dropdown.options.Count == 0) return fallback;
        int index = Mathf.Clamp(dropdown.value, 0, dropdown.options.Count - 1);
        string value = dropdown.options[index].text;
        return string.IsNullOrWhiteSpace(value) ? fallback : value.Trim().ToLowerInvariant();
    }

    private int GetLimitValue()
    {
        if (limitInput == null || string.IsNullOrWhiteSpace(limitInput.text))
        {
            return Mathf.Max(1, defaultLimit);
        }

        return int.TryParse(limitInput.text, out int value) ? Mathf.Clamp(value, 1, 100) : Mathf.Max(1, defaultLimit);
    }

    private void ApplyFont(TMP_Text text)
    {
        TMP_FontAsset font = japaneseFontAsset != null ? japaneseFontAsset : fontReferenceText == null ? null : fontReferenceText.font;
        if (font != null) text.font = font;
    }

    private void CacheReferences()
    {
        modeDropdown = FindComponentByName<TMP_Dropdown>("ModeDropdown");
        sourceDropdown = FindComponentByName<TMP_Dropdown>("SourceDropdown");
        filterDropdown = FindComponentByName<TMP_Dropdown>("FilterDropdown");
        searchInput = FindComponentByName<TMP_InputField>("SearchInput");
        limitInput = FindComponentByName<TMP_InputField>("LimitInput");
        fileDropText = FindComponentByName<TMP_Text>("FileDropText");
        searchButton = FindComponentByName<Button>("SearchButton");
        if (searchButton != null)
        {
            searchButton.onClick.RemoveListener(HandleSearchClicked);
            searchButton.onClick.AddListener(HandleSearchClicked);
        }
    }

    private T FindComponentByName<T>(string objectName) where T : Component
    {
        T[] components = GetComponentsInChildren<T>(true);
        foreach (T component in components)
        {
            if (component != null && component.name == objectName)
            {
                return component;
            }
        }

        return null;
    }

    private bool HasCurrentLayout()
    {
        Transform content = transform.Find("WindowContent");
        return content != null && content.Find("SearchTopRow") != null && content.Find("KeywordRow") != null;
    }

    private void RemoveGeneratedLayout()
    {
        searchInput = null;
        limitInput = null;
        modeDropdown = null;
        sourceDropdown = null;
        filterDropdown = null;
        searchButton = null;
        fileDropText = null;

        DestroyChildIfExists("WindowContent");
        DestroyChildIfExists("ResizeHandle");
    }

    private void DestroyChildIfExists(string childName)
    {
        Transform child = transform.Find(childName);
        if (child == null)
        {
            return;
        }

        if (Application.isPlaying)
        {
            child.SetParent(null, false);
            Destroy(child.gameObject);
        }
        else
        {
            DestroyImmediate(child.gameObject);
        }
    }

    private void EnsureWindowFeatures()
    {
        if (enableWindowMotion)
        {
            ThoughtMapWindowMotion motion = GetComponent<ThoughtMapWindowMotion>();
            if (motion == null)
            {
                motion = gameObject.AddComponent<ThoughtMapWindowMotion>();
            }
            motion.Show();
        }

        if (!enableDragging)
        {
            EnsureResizeHandle();
            return;
        }

        RectTransform titleBar = transform.Find("WindowContent/TitleBar") as RectTransform;
        if (titleBar == null)
        {
            return;
        }

        ThoughtMapDraggableWindow drag = titleBar.GetComponent<ThoughtMapDraggableWindow>();
        if (drag == null)
        {
            drag = titleBar.gameObject.AddComponent<ThoughtMapDraggableWindow>();
        }
        drag.Configure(transform as RectTransform, false);
        EnsureResizeHandle();
    }

    private void EnsureResizeHandle()
    {
        if (!enableResizing)
        {
            return;
        }

        RectTransform root = transform as RectTransform;
        if (root == null)
        {
            return;
        }

        RectTransform handle = transform.Find("ResizeHandle") as RectTransform;
        if (handle == null)
        {
            GameObject handleObject = new GameObject("ResizeHandle", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
            handle = handleObject.GetComponent<RectTransform>();
            handle.SetParent(transform, false);
            handle.anchorMin = new Vector2(1f, 0f);
            handle.anchorMax = new Vector2(1f, 0f);
            handle.pivot = new Vector2(1f, 0f);
            handle.anchoredPosition = new Vector2(-8f, 8f);
            handle.sizeDelta = new Vector2(28f, 28f);
            Image image = handleObject.GetComponent<Image>();
            image.color = new Color(cyan.r, cyan.g, cyan.b, 0.35f);
        }

        ThoughtMapResizableWindow resize = handle.GetComponent<ThoughtMapResizableWindow>();
        if (resize == null)
        {
            resize = handle.gameObject.AddComponent<ThoughtMapResizableWindow>();
        }

        resize.Configure(root, minWindowSize);
    }

    private void ApplyDefaultWindowRect()
    {
        RectTransform rect = transform as RectTransform;
        if (rect == null) return;

        rect.anchorMin = new Vector2(0.5f, 0.5f);
        rect.anchorMax = new Vector2(0.5f, 0.5f);
        rect.pivot = new Vector2(0.5f, 0.5f);
        rect.anchoredPosition = defaultPosition;
        rect.sizeDelta = defaultSize;
    }

    private void SetText(TMP_Text target, string value)
    {
        if (target != null)
        {
            target.text = value;
        }
    }
}
