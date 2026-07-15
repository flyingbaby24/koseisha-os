using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ProductBattleAbilityBarView : MonoBehaviour
{
    private const float RowHeight = 26f;
    private const float LabelWidth = 48f;
    private const float BarMinWidth = 72f;
    private const float BaseValueWidth = 34f;
    private const float PositionWidth = 42f;
    private const float ResonanceWidth = 42f;
    private const float ArrowWidth = 20f;
    private const float FinalValueWidth = 36f;
    private static Sprite generatedSolidSprite;

    [SerializeField] private TMP_Text labelText;
    [SerializeField] private TMP_Text baseValueText;
    [SerializeField] private TMP_Text positionText;
    [SerializeField] private TMP_Text resonanceText;
    [SerializeField] private TMP_Text modifierText;
    [SerializeField] private TMP_Text arrowText;
    [SerializeField] private TMP_Text finalValueText;
    [SerializeField] private TMP_Text valueText;
    [SerializeField] private RectTransform barContainer;
    [SerializeField] private Image backgroundImage;
    [SerializeField] private Image fillImage;

    public void Bind(ThoughtMapBattleAbilityValue value)
    {
        EnsureVisuals();
        SetText(labelText, value.definition.shortName);
        SetValueTexts(value);

        if (backgroundImage != null)
        {
            EnsureImageSprite(backgroundImage);
            backgroundImage.color = new Color(0f, 0f, 0f, 0.42f);
        }

        if (fillImage != null)
        {
            EnsureImageSprite(fillImage);
            fillImage.type = Image.Type.Filled;
            fillImage.fillMethod = Image.FillMethod.Horizontal;
            fillImage.fillOrigin = 0;
            fillImage.fillClockwise = true;
            fillImage.fillAmount = value.fillAmount;
            fillImage.color = value.definition.color;
            fillImage.preserveAspect = false;
        }

    }

    public void Clear()
    {
        EnsureVisuals();
        SetText(labelText, "");
        SetText(baseValueText, "");
        SetText(positionText, "");
        SetText(resonanceText, "");
        SetText(modifierText, "");
        SetText(arrowText, "");
        SetText(finalValueText, "");
        SetText(valueText, "");
        if (fillImage != null)
        {
            fillImage.fillAmount = 0f;
        }
    }

    public void EnsureVisuals()
    {
        RectTransform root = transform as RectTransform;
        if (root == null)
        {
            return;
        }

        if (labelText == null)
        {
            labelText = GetOrCreateText(root, "LabelText", "HP", 14, TextAlignmentOptions.MidlineLeft);
        }

        if (baseValueText == null)
        {
            baseValueText = GetOrCreateText(root, "BaseValueText", "0", 13, TextAlignmentOptions.MidlineRight);
        }

        if (barContainer == null)
        {
            barContainer = GetOrCreateRect(root, "BarContainer");
        }
        RemoveLegacyBarObjects(root);

        if (backgroundImage == null || backgroundImage.transform.parent != barContainer)
        {
            backgroundImage = GetOrCreateImage(barContainer, "BackgroundImage", new Color(0f, 0f, 0f, 0.42f));
        }

        if (fillImage == null || fillImage.transform.parent != barContainer || fillImage == backgroundImage)
        {
            fillImage = GetOrCreateImage(barContainer, "FillImage", Color.white);
        }

        if (modifierText == null)
        {
            modifierText = GetOrCreateText(root, "ModifierText", "", 12, TextAlignmentOptions.MidlineRight);
        }

        if (positionText == null)
        {
            Transform existing = root.Find("PositionText");
            positionText = existing == null ? null : existing.GetComponent<TMP_Text>();
            if (positionText == null)
            {
                positionText = GetOrCreateText(root, "PositionText", "", 12, TextAlignmentOptions.MidlineRight);
            }
        }

        if (resonanceText == null)
        {
            Transform existing = root.Find("ResonanceText");
            resonanceText = existing == null ? null : existing.GetComponent<TMP_Text>();
            if (resonanceText == null)
            {
                resonanceText = GetOrCreateText(root, "ResonanceText", "", 12, TextAlignmentOptions.MidlineRight);
            }
        }

        if (arrowText == null)
        {
            arrowText = GetOrCreateText(root, "ArrowText", "", 13, TextAlignmentOptions.Center);
        }

        if (finalValueText == null)
        {
            finalValueText = GetOrCreateText(root, "FinalValueText", "", 13, TextAlignmentOptions.MidlineRight);
        }

        if (valueText == null)
        {
            Transform legacyValue = root.Find("ValueText");
            if (legacyValue != null)
            {
                valueText = legacyValue.GetComponent<TMP_Text>();
            }
        }
        if (valueText != null)
        {
            valueText.text = "";
            valueText.gameObject.SetActive(false);
        }

        HorizontalLayoutGroup rowLayout = root.GetComponent<HorizontalLayoutGroup>();
        if (rowLayout == null)
        {
            rowLayout = root.gameObject.AddComponent<HorizontalLayoutGroup>();
        }
        rowLayout.padding = new RectOffset(0, 0, 0, 0);
        rowLayout.spacing = 2f;
        rowLayout.childAlignment = TextAnchor.MiddleCenter;
        rowLayout.childControlWidth = true;
        rowLayout.childControlHeight = true;
        rowLayout.childForceExpandWidth = false;
        rowLayout.childForceExpandHeight = false;

        ConfigureLayout(labelText == null ? null : labelText.gameObject, LabelWidth, RowHeight, 0f);
        ConfigureLayout(baseValueText == null ? null : baseValueText.gameObject, BaseValueWidth, RowHeight, 0f);
        ConfigureLayout(barContainer == null ? null : barContainer.gameObject, BarMinWidth, RowHeight, 1f);
        ConfigureLayout(positionText == null ? null : positionText.gameObject, PositionWidth, RowHeight, 0f);
        ConfigureLayout(resonanceText == null ? null : resonanceText.gameObject, ResonanceWidth, RowHeight, 0f);
        ConfigureLayout(arrowText == null ? null : arrowText.gameObject, ArrowWidth, RowHeight, 0f);
        ConfigureLayout(finalValueText == null ? null : finalValueText.gameObject, FinalValueWidth, RowHeight, 0f);
        if (labelText != null) labelText.transform.SetSiblingIndex(0);
        if (baseValueText != null) baseValueText.transform.SetSiblingIndex(1);
        if (barContainer != null) barContainer.transform.SetSiblingIndex(2);
        if (positionText != null) positionText.transform.SetSiblingIndex(3);
        if (resonanceText != null) resonanceText.transform.SetSiblingIndex(4);
        if (arrowText != null) arrowText.transform.SetSiblingIndex(5);
        if (finalValueText != null) finalValueText.transform.SetSiblingIndex(6);

        ConfigureText(labelText, 14);
        ConfigureText(baseValueText, 13);
        ConfigureText(positionText, 12);
        ConfigureText(resonanceText, 12);
        ConfigureText(modifierText, 12);
        ConfigureText(arrowText, 13);
        ConfigureText(finalValueText, 13);
        if (modifierText != null && modifierText != resonanceText)
        {
            modifierText.text = "";
            modifierText.gameObject.SetActive(false);
        }

        if (fillImage != null)
        {
            EnsureImageSprite(fillImage);
            fillImage.type = Image.Type.Filled;
            fillImage.fillMethod = Image.FillMethod.Horizontal;
            fillImage.fillOrigin = 0;
            fillImage.fillClockwise = true;
            fillImage.preserveAspect = false;
            fillImage.raycastTarget = false;
            fillImage.color = new Color(fillImage.color.r, fillImage.color.g, fillImage.color.b, 0.95f);
            Stretch(fillImage.rectTransform);
            fillImage.transform.SetAsLastSibling();
            RemoveLayoutComponents(fillImage.gameObject);
        }

        if (backgroundImage != null)
        {
            EnsureImageSprite(backgroundImage);
            backgroundImage.color = new Color(0f, 0f, 0f, 0.50f);
            backgroundImage.raycastTarget = false;
            Stretch(backgroundImage.rectTransform);
            backgroundImage.transform.SetAsFirstSibling();
            RemoveLayoutComponents(backgroundImage.gameObject);
        }

        if (barContainer != null)
        {
            Stretch(barContainer);
            barContainer.gameObject.SetActive(true);
        }
    }

    private void SetValueTexts(ThoughtMapBattleAbilityValue value)
    {
        SetText(baseValueText, FormatValue(value.rawValue));
        bool hasPosition = value.positionApplies && Mathf.Abs(value.positionDelta) >= 0.01f;
        bool hasResonance = value.resonanceApplies && Mathf.Abs(value.resonanceDelta) >= 0.01f;
        bool hasFinalChange = Mathf.Abs(value.finalValue - value.rawValue) >= 0.01f;
        SetText(positionText, hasPosition ? FormatDelta(value.positionDelta) : "");
        SetText(resonanceText, hasResonance ? FormatDelta(value.resonanceDelta) : "");
        if (modifierText != null && modifierText != resonanceText)
        {
            SetText(modifierText, "");
        }
        SetText(arrowText, hasFinalChange ? "->" : "");
        SetText(finalValueText, FormatValue(value.finalValue));

        SetText(valueText, "");
    }

    private static void ConfigureText(TMP_Text text, int fontSize)
    {
        if (text == null)
        {
            return;
        }

        text.overflowMode = TextOverflowModes.Overflow;
        text.enableAutoSizing = false;
        text.fontSize = fontSize;
        text.enableWordWrapping = false;
        text.raycastTarget = false;
        text.gameObject.SetActive(true);
    }

    private static TMP_Text GetOrCreateText(RectTransform parent, string name, string value, int fontSize, TextAlignmentOptions alignment)
    {
        Transform existing = parent.Find(name);
        GameObject textObject = existing == null ? new GameObject(name, typeof(RectTransform), typeof(TextMeshProUGUI)) : existing.gameObject;
        textObject.transform.SetParent(parent, false);

        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = fontSize;
        text.alignment = alignment;
        text.color = new Color(0.88f, 0.96f, 1f, 1f);
        text.enableWordWrapping = false;
        text.overflowMode = TextOverflowModes.Overflow;
        text.raycastTarget = false;
        Shadow shadow = text.GetComponent<Shadow>();
        if (shadow == null)
        {
            shadow = text.gameObject.AddComponent<Shadow>();
        }
        shadow.effectColor = new Color(0f, 0f, 0f, 0.72f);
        shadow.effectDistance = new Vector2(1f, -1f);
        return text;
    }

    private static Image GetOrCreateImage(RectTransform parent, string name, Color color)
    {
        Transform existing = parent.Find(name);
        GameObject imageObject = existing == null ? new GameObject(name, typeof(RectTransform), typeof(Image)) : existing.gameObject;
        imageObject.transform.SetParent(parent, false);

        Image image = imageObject.GetComponent<Image>();
        EnsureImageSprite(image);
        image.color = color;
        image.raycastTarget = false;
        return image;
    }

    private static void EnsureImageSprite(Image image)
    {
        if (image == null || image.sprite != null)
        {
            return;
        }

        if (generatedSolidSprite == null)
        {
            Texture2D texture = new Texture2D(1, 1, TextureFormat.RGBA32, false);
            texture.SetPixel(0, 0, Color.white);
            texture.Apply();
            generatedSolidSprite = Sprite.Create(texture, new Rect(0f, 0f, 1f, 1f), new Vector2(0.5f, 0.5f));
            generatedSolidSprite.name = "GeneratedAbilityBarSolidSprite";
        }

        image.sprite = generatedSolidSprite;
    }

    private static RectTransform GetOrCreateRect(RectTransform parent, string name)
    {
        Transform existing = parent.Find(name);
        GameObject rectObject = existing == null ? new GameObject(name, typeof(RectTransform)) : existing.gameObject;
        rectObject.transform.SetParent(parent, false);
        return rectObject.GetComponent<RectTransform>();
    }

    private static void ConfigureLayout(GameObject target, float width, float height, float flexibleWidth)
    {
        if (target == null)
        {
            return;
        }

        LayoutElement layout = target.GetComponent<LayoutElement>();
        if (layout == null)
        {
            layout = target.AddComponent<LayoutElement>();
        }

        layout.minWidth = width;
        layout.preferredWidth = width;
        layout.minHeight = height;
        layout.preferredHeight = height;
        layout.flexibleWidth = flexibleWidth;
        layout.flexibleHeight = 0f;
    }

    private static void Stretch(RectTransform rect)
    {
        if (rect == null)
        {
            return;
        }

        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
    }

    private static void RemoveLayoutComponents(GameObject target)
    {
        if (target == null)
        {
            return;
        }

        LayoutElement layout = target.GetComponent<LayoutElement>();
        if (layout != null)
        {
            DestroyObject(layout);
        }

        ContentSizeFitter fitter = target.GetComponent<ContentSizeFitter>();
        if (fitter != null)
        {
            DestroyObject(fitter);
        }
    }

    private void RemoveLegacyBarObjects(RectTransform root)
    {
        RemoveLegacyBarObject(root, "BarBackground");
        RemoveLegacyBarObject(root, "BarFill");
    }

    private void RemoveLegacyBarObject(RectTransform root, string objectName)
    {
        Transform legacy = root.Find(objectName);
        if (legacy == null || legacy == barContainer)
        {
            return;
        }

        if (backgroundImage != null && legacy == backgroundImage.transform)
        {
            backgroundImage = null;
        }

        if (fillImage != null && legacy == fillImage.transform)
        {
            fillImage = null;
        }

        legacy.gameObject.SetActive(false);
    }

    private static void DestroyObject(Object target)
    {
        if (target == null)
        {
            return;
        }

        if (Application.isPlaying)
        {
            Destroy(target);
        }
        else
        {
            DestroyImmediate(target);
        }
    }

    private static string FormatValue(float value)
    {
        return Mathf.Abs(value - Mathf.Round(value)) < 0.01f ? Mathf.RoundToInt(value).ToString() : value.ToString("0.##");
    }

    private static string FormatAbilityValue(ThoughtMapBattleAbilityValue value)
    {
        if (!value.resonanceApplies || Mathf.Abs(value.resonanceModifier) < 0.0001f)
        {
            return FormatValue(value.rawValue);
        }

        string modifier = FormatModifier(value.resonanceModifier);
        return $"{FormatValue(value.rawValue)} {modifier} -> {FormatValue(value.finalValue)}";
    }

    private static string FormatModifier(float modifier)
    {
        float percent = modifier * 100f;
        return percent >= 0f ? $"+{percent:0}%" : $"{percent:0}%";
    }

    private static string FormatDelta(float value)
    {
        string formatted = FormatValue(Mathf.Abs(value));
        return value >= 0f ? $"+{formatted}" : $"-{formatted}";
    }

    private static void SetText(TMP_Text text, string value)
    {
        if (text != null)
        {
            text.text = value;
        }
    }
}
