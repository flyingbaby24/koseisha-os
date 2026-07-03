using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

[DisallowMultipleComponent]
public class ResultListV2View : MonoBehaviour
{
    [Header("Runtime Build")]
    [SerializeField] private bool buildOnAwake = true;
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
        if (contentRoot != null || transform.Find("WindowContent") != null)
        {
            CacheReferences();
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
        CreateText(titleBar, "TitleText", "Results", 18, FontStyles.Bold, textPrimary);
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
    }

    public void SetResults(ThoughtMapSearchResult[] results)
    {
        ShowResults(results);
    }

    public void ShowResults(ThoughtMapSearchResult[] results)
    {
        BuildIfNeeded();
        Clear();
        int resultCount = results == null ? 0 : results.Length;
        Debug.Log($"[ResultListV2] SetResults count={resultCount}", this);
        if (results == null || itemContent == null)
        {
            if (itemContent == null)
            {
                Debug.LogWarning("[ResultListV2] itemContent is not assigned. Results cannot be displayed.", this);
            }
            SetText(statusText, "No results");
            return;
        }
        for (int i = 0; i < results.Length; i++)
        {
            ResultItemV2View item = CreateItem();
            AddLayout(item.gameObject, 0f, itemHeight, false, true);
            item.Bind(results[i], result => HandleSelected(item, result));
            NeonUIFade fade = item.GetComponent<NeonUIFade>();
            if (fade == null) fade = item.gameObject.AddComponent<NeonUIFade>();
            fade.Play(i * 0.035f);
        }
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
            return Instantiate(resultItemPrefab, itemContent);
        }
        GameObject obj = new GameObject("ResultItemV2", typeof(RectTransform), typeof(CanvasRenderer), typeof(Image), typeof(Button), typeof(ResultItemV2View));
        obj.transform.SetParent(itemContent, false);
        return obj.GetComponent<ResultItemV2View>();
    }

    private void HandleSelected(ResultItemV2View item, ThoughtMapSearchResult result)
    {
        if (selectedItem != null) selectedItem.SetSelected(false);
        selectedItem = item;
        selectedItem?.SetSelected(true);
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

    private void ApplyFont(TMP_Text text)
    {
        TMP_FontAsset font = japaneseFontAsset != null ? japaneseFontAsset : fontReferenceText == null ? null : fontReferenceText.font;
        if (font != null) text.font = font;
    }

    private void CacheReferences()
    {
        contentRoot = transform.Find("WindowContent") as RectTransform;
        Transform content = transform.Find("WindowContent/ContentArea/Viewport/Content");
        itemContent = content as RectTransform;
    }

    private void SetText(TMP_Text text, string value)
    {
        if (text != null) text.text = value;
    }
}
