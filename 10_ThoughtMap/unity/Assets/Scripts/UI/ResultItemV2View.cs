using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

[DisallowMultipleComponent]
public class ResultItemV2View : MonoBehaviour
{
    [Header("Runtime Build")]
    [SerializeField] private bool buildOnAwake = true;

    [Header("Fonts")]
    [SerializeField] private TMP_FontAsset japaneseFontAsset;
    [SerializeField] private TMP_Text fontReferenceText;

    [Header("Style")]
    [SerializeField] private Color normalColor = new Color(0.015f, 0.055f, 0.12f, 0.92f);
    [SerializeField] private Color selectedColor = new Color(0.02f, 0.13f, 0.25f, 0.98f);
    [SerializeField] private Color outlineColor = new Color(0.05f, 0.42f, 0.75f, 0.45f);
    [SerializeField] private Color selectedOutlineColor = new Color(0.05f, 0.82f, 1f, 1f);
    [SerializeField] private Color textPrimary = new Color(0.92f, 0.98f, 1f, 1f);
    [SerializeField] private Color textSecondary = new Color(0.60f, 0.78f, 0.92f, 1f);
    [SerializeField] private int titleFontSize = 18;
    [SerializeField] private int metadataFontSize = 13;
    [SerializeField] private int padding = 12;
    [SerializeField] private int spacing = 4;

    private Image backgroundImage;
    private Outline outline;
    private Button button;
    private TMP_Text titleText;
    private TMP_Text authorText;
    private TMP_Text scoreText;
    private ThoughtMapSearchResult boundResult;
    private Action<ThoughtMapSearchResult> selectedCallback;

    private void Awake()
    {
        if (buildOnAwake)
        {
            BuildIfNeeded();
        }
    }

    public void Bind(ThoughtMapSearchResult result, Action<ThoughtMapSearchResult> onSelected)
    {
        BuildIfNeeded();
        boundResult = result;
        selectedCallback = onSelected;
        SetText(titleText, result == null || string.IsNullOrWhiteSpace(result.title) ? "Untitled" : result.title);
        SetText(authorText, result == null || string.IsNullOrWhiteSpace(result.author) ? "Unknown" : result.author);
        SetText(scoreText, result == null ? string.Empty : result.similarity.ToString("0.0000"));
        SetSelected(false);
    }

    public void SetSelected(bool selected)
    {
        if (backgroundImage != null)
        {
            backgroundImage.color = selected ? selectedColor : normalColor;
        }
        if (outline != null)
        {
            outline.effectColor = selected ? selectedOutlineColor : outlineColor;
            outline.effectDistance = selected ? new Vector2(2.4f, -2.4f) : new Vector2(1.0f, -1.0f);
        }
    }

    public void BuildIfNeeded()
    {
        if (titleText != null)
        {
            return;
        }
        backgroundImage = GetComponent<Image>();
        if (backgroundImage == null) backgroundImage = gameObject.AddComponent<Image>();
        backgroundImage.color = normalColor;
        outline = GetComponent<Outline>();
        if (outline == null) outline = gameObject.AddComponent<Outline>();
        outline.effectColor = outlineColor;
        outline.effectDistance = new Vector2(1f, -1f);
        button = GetComponent<Button>();
        if (button == null) button = gameObject.AddComponent<Button>();
        button.onClick.AddListener(HandleClicked);
        if (GetComponent<NeonHoverGlow>() == null) gameObject.AddComponent<NeonHoverGlow>();

        RectTransform root = transform as RectTransform;
        if (root != null && root.sizeDelta == Vector2.zero) root.sizeDelta = new Vector2(520f, 84f);
        VerticalLayoutGroup layout = gameObject.AddComponent<VerticalLayoutGroup>();
        layout.padding = new RectOffset(padding, padding, padding, padding);
        layout.spacing = spacing;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        titleText = CreateText("TitleText", titleFontSize, FontStyles.Bold, textPrimary);
        authorText = CreateText("AuthorText", metadataFontSize, FontStyles.Normal, textSecondary);
        scoreText = CreateText("ScoreText", metadataFontSize, FontStyles.Normal, textSecondary);
    }

    private TMP_Text CreateText(string name, int size, FontStyles style, Color color)
    {
        GameObject obj = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        obj.transform.SetParent(transform, false);
        TMP_Text text = obj.GetComponent<TMP_Text>();
        ApplyFont(text);
        text.fontSize = size;
        text.fontStyle = style;
        text.color = color;
        text.enableWordWrapping = true;
        text.overflowMode = TextOverflowModes.Ellipsis;
        text.raycastTarget = false;
        return text;
    }

    private void ApplyFont(TMP_Text text)
    {
        TMP_FontAsset font = japaneseFontAsset != null ? japaneseFontAsset : fontReferenceText == null ? null : fontReferenceText.font;
        if (font != null) text.font = font;
    }

    private void HandleClicked()
    {
        if (boundResult != null)
        {
            selectedCallback?.Invoke(boundResult);
        }
    }

    private void SetText(TMP_Text target, string value)
    {
        if (target != null) target.text = value;
    }
}
