using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

[DisallowMultipleComponent]
public class ResultListV2View : MonoBehaviour
{
    [Header("Runtime Build")]
    [SerializeField] private bool buildOnAwake = true;
    [SerializeField] private Vector2 defaultPosition = new Vector2(-420f, -80f);
    [SerializeField] private Vector2 defaultSize = new Vector2(640f, 620f);
    [SerializeField] private ResultItemV2View resultItemPrefab;

    [Header("Fonts")]
    [SerializeField] private TMP_FontAsset japaneseFontAsset;
    [SerializeField] private TMP_Text fontReferenceText;

    [Header("Style")]
    [SerializeField] private Color panelColor = new Color(0.012f, 0.045f, 0.10f, 0.88f);
    [SerializeField] private Color titleBarColor = new Color(0.015f, 0.075f, 0.16f, 0.92f);
    [SerializeField] private Color textPrimary = new Color(0.92f, 0.98f, 1f, 1f);
    [SerializeField] private Color cyan = new Color(0.05f, 0.82f, 1f, 0.8f);
    [SerializeField] private int padding = 14;
    [SerializeField] private int spacing = 10;
    [SerializeField] private float itemHeight = 92f;

    [Header("Window Interaction")]
    [SerializeField] private bool enableDragging = true;
    [SerializeField] private bool enableWindowMotion = true;
    [SerializeField] private bool enableResizing = true;
    [SerializeField] private Vector2 minWindowSize = new Vector2(360f, 320f);

    [Header("Diagnostics")]
    [SerializeField] private bool debugResultFlow = false;

    private RectTransform contentRoot;
    private RectTransform itemContent;
    private TMP_Text statusText;
    private ResultItemV2View selectedItem;

    public event Action<ThoughtMapSearchResult> ResultSelected;

    private void Awake()
    {
        if (buildOnAwake) BuildIfNeeded();
    }

    public void BuildIfNeeded()
    {
        ApplyDefaultWindowRect();

        if (contentRoot != null || transform.Find("WindowContent") != null)
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

        contentRoot = CreateContainer(transform, "WindowContent", true);
        ConfigureVertical(contentRoot, padding, spacing);
        RectTransform titleBar = CreateBlock(contentRoot, "TitleBar", titleBarColor, 44f);
        CreateText(titleBar, "TitleText", "Source of Thought - Results", 18, FontStyles.Bold, textPrimary);
        RectTransform scrollRoot = CreateContainer(contentRoot, "ContentArea", false);
        AddLayout(scrollRoot.gameObject, 0f, 0f, false, true);
        ScrollRect scrollRect = scrollRoot.gameObject.AddComponent<ScrollRect>();
        Image scrollImage = scrollRoot.gameObject.AddComponent<Image>();
        scrollImage.color = new Color(0f, 0f, 0f, 0.08f);
        RectTransform viewport = CreateContainer(scrollRoot, "Viewport", true);
        Mask mask = viewport.gameObject.AddComponent<Mask>();
        mask.showMaskGraphic = false;
        Image viewportImage = viewport.gameObject.AddComponent<Image>();
        viewportImage.color = new Color(1f, 1f, 1f, 0.01f);
        itemContent = CreateContainer(viewport, "Content", false);
        itemContent.anchorMin = new Vector2(0f, 1f);
        itemContent.anchorMax = new Vector2(1f, 1f);
        itemContent.pivot = new Vector2(0.5f, 1f);
        itemContent.offsetMin = Vector2.zero;
        itemContent.offsetMax = Vector2.zero;
        ConfigureVertical(itemContent, 8, 8);
        ContentSizeFitter fitter = itemContent.gameObject.AddComponent<ContentSizeFitter>();
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
        scrollRect.viewport = viewport;
        scrollRect.content = itemContent;
        scrollRect.horizontal = false;
        scrollRect.vertical = true;
        RectTransform action = CreateBlock(contentRoot, "ActionArea", titleBarColor, 38f);
        statusText = CreateText(action, "StatusText", "No results", 13, FontStyles.Normal, textPrimary);
        EnsureWindowFeatures();
    }

    public void SetResults(ThoughtMapSearchResult[] results)
    {
        int resultCount = results == null ? 0 : results.Length;
        LogResultFlow($"SetResults entry count={resultCount}");
        if (results != null)
        {
            for (int i = 0; i < results.Length; i++)
            {
                ThoughtMapSearchResult result = results[i];
                int parameterCount = result == null || result.parameters == null ? 0 : result.parameters.Length;
                LogResultFlow($"SetResults item index={i} doc_id={(result == null ? "(null)" : result.doc_id)} parameter count={parameterCount}");
            }
        }

        ShowResults(results);
    }

    public void ShowResults(ThoughtMapSearchResult[] results)
    {
        BuildIfNeeded();
        PlayWindowShow();
        int resultCount = results == null ? 0 : results.Length;
        LogResultFlow($"ShowResults count={resultCount}");
        if (results == null || itemContent == null)
        {
            HideExistingItems(0);
            if (itemContent == null)
            {
                Debug.LogWarning("[ResultListV2] itemContent is not assigned. Results cannot be displayed.", this);
            }
            SetText(statusText, "No results");
            return;
        }
        LogResultFlow($"ShowResults entering item generation loop count={results.Length}");
        for (int i = 0; i < results.Length; i++)
        {
            ThoughtMapSearchResult result = results[i];
            int parameterCount = result == null || result.parameters == null ? 0 : result.parameters.Length;
            LogResultFlow($"ShowResults item index={i} doc_id={(result == null ? "(null)" : result.doc_id)} parameter count={parameterCount}");
            ResultItemV2View item = GetOrCreateItem(i);
            item.SetFontAsset(ResolveFont());
            AddLayout(item.gameObject, 0f, itemHeight, false, true);
            int beforeBindParameterCount = result == null || result.parameters == null ? 0 : result.parameters.Length;
            LogResultFlow($"Before ResultItemV2.SetResult index={i} doc_id={(result == null ? "(null)" : result.doc_id)} parameter count={beforeBindParameterCount}");
            item.SetResult(result, selectedResult => HandleSelected(item, selectedResult));
            NeonUIFade fade = item.GetComponent<NeonUIFade>();
            if (fade == null) fade = item.gameObject.AddComponent<NeonUIFade>();
            fade.Play(i * 0.035f);
        }
        HideExistingItems(results.Length);
        SetText(statusText, $"{results.Length} results");
    }

    public void Clear()
    {
        selectedItem = null;
        if (itemContent == null) return;
        for (int i = itemContent.childCount - 1; i >= 0; i--)
        {
            Destroy(itemContent.GetChild(i).gameObject);
        }
        SetText(statusText, "No results");
    }

    private ResultItemV2View CreateItem()
    {
        if (resultItemPrefab != null)
        {
            ResultItemV2View prefabInstance = Instantiate(resultItemPrefab, itemContent);
            prefabInstance.SetFontAsset(ResolveFont());
            return prefabInstance;
        }
        GameObject obj = new GameObject("ResultItemV2", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button), typeof(ResultItemV2View));
        obj.transform.SetParent(itemContent, false);
        ResultItemV2View generatedItem = obj.GetComponent<ResultItemV2View>();
        generatedItem.SetFontAsset(ResolveFont());
        return generatedItem;
    }

    private ResultItemV2View GetOrCreateItem(int index)
    {
        if (itemContent != null && index < itemContent.childCount)
        {
            Transform existing = itemContent.GetChild(index);
            ResultItemV2View existingItem = existing.GetComponent<ResultItemV2View>();
            if (existingItem != null)
            {
                existingItem.gameObject.SetActive(true);
                LogResultFlow($"Reusing existing ResultItemV2 index={index} name={existingItem.name}");
                return existingItem;
            }
        }

        ResultItemV2View createdItem = CreateItem();
        LogResultFlow($"Created ResultItemV2 index={index} name={createdItem.name}");
        return createdItem;
    }

    private void HideExistingItems(int startIndex)
    {
        if (itemContent == null)
        {
            return;
        }

        for (int i = startIndex; i < itemContent.childCount; i++)
        {
            Transform child = itemContent.GetChild(i);
            if (child != null)
            {
                ResultItemV2View item = child.GetComponent<ResultItemV2View>();
                if (item != null)
                {
                    item.SetSelected(false);
                }
                child.gameObject.SetActive(false);
            }
        }
    }

    private void HandleSelected(ResultItemV2View item, ThoughtMapSearchResult result)
    {
        if (selectedItem != null) selectedItem.SetSelected(false);
        selectedItem = item;
        selectedItem?.SetSelected(true);
        int parameterCount = result == null || result.parameters == null ? 0 : result.parameters.Length;
        LogResultFlow($"ResultSelected doc_id={(result == null ? "(null)" : result.doc_id)} parameter count={parameterCount}");
        ResultSelected?.Invoke(result);
    }

    private RectTransform CreateBlock(RectTransform parent, string name, Color color, float height)
    {
        RectTransform rect = CreateContainer(parent, name, false);
        Image image = rect.gameObject.AddComponent<Image>();
        image.color = color;
        AddLayout(rect.gameObject, 0f, height, false, true);
        ConfigureVertical(rect, 10, 4);
        return rect;
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

    private void AddLayout(GameObject obj, float width, float height, bool setWidth, bool flexibleWidth)
    {
        LayoutElement layout = obj.GetComponent<LayoutElement>();
        if (layout == null) layout = obj.AddComponent<LayoutElement>();
        if (setWidth) layout.preferredWidth = width;
        layout.preferredHeight = height;
        layout.minHeight = height;
        layout.flexibleWidth = flexibleWidth ? 1f : 0f;
        layout.flexibleHeight = height <= 0f ? 1f : 0f;
    }

    private TMP_FontAsset ResolveFont()
    {
        return japaneseFontAsset != null ? japaneseFontAsset : fontReferenceText == null ? null : fontReferenceText.font;
    }

    private void ApplyFont(TMP_Text text)
    {
        TMP_FontAsset font = ResolveFont();
        if (font != null) text.font = font;
    }

    [ContextMenu("Apply Font To Generated Items")]
    public void ApplyFontToGeneratedItems()
    {
        ApplyFontToGeneratedTexts();
        ResultItemV2View[] items = GetComponentsInChildren<ResultItemV2View>(true);
        TMP_FontAsset font = ResolveFont();
        foreach (ResultItemV2View item in items)
        {
            if (item != null)
            {
                item.SetFontAsset(font);
                item.ApplyFontToGeneratedTexts();
            }
        }
    }

    private void ApplyFontToGeneratedTexts()
    {
        TMP_Text[] texts = GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in texts)
        {
            ApplyFont(text);
        }
    }

    private void CacheReferences()
    {
        contentRoot = transform.Find("WindowContent") as RectTransform;
        Transform content = transform.Find("WindowContent/ContentArea/Viewport/Content");
        itemContent = content as RectTransform;
        SetText(FindTextByName("TitleText"), "Source of Thought - Results");
    }

    private TMP_Text FindTextByName(string objectName)
    {
        TMP_Text[] texts = GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in texts)
        {
            if (text != null && text.name == objectName)
            {
                return text;
            }
        }
        return null;
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

    private void PlayWindowShow()
    {
        if (!enableWindowMotion)
        {
            return;
        }

        ThoughtMapWindowMotion motion = GetComponent<ThoughtMapWindowMotion>();
        if (motion != null)
        {
            motion.Show();
        }
    }

    private void SetText(TMP_Text text, string value)
    {
        if (text != null) text.text = value;
    }

    private void LogResultFlow(string message)
    {
        if (debugResultFlow)
        {
            Debug.Log($"[ResultListV2] {message}", this);
        }
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
}
