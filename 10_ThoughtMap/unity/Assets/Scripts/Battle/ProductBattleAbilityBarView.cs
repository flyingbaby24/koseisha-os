using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ProductBattleAbilityBarView : MonoBehaviour
{
    private const float RowHeight = 22f;
    private const float LabelWidth = 46f;
    private const float ValueWidth = 42f;
    private static Sprite generatedSolidSprite;

    [SerializeField] private TMP_Text labelText;
    [SerializeField] private TMP_Text valueText;
    [SerializeField] private RectTransform barContainer;
    [SerializeField] private Image backgroundImage;
    [SerializeField] private Image fillImage;

    public void Bind(ThoughtMapBattleAbilityValue value)
    {
        EnsureVisuals();
        SetText(labelText, value.definition.shortName);
        SetText(valueText, FormatValue(value.rawValue));

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

        RectTransform fillRect = fillImage == null ? null : fillImage.rectTransform;
        RectTransform backgroundRect = backgroundImage == null ? null : backgroundImage.rectTransform;
        Debug.Log(
            $"[ProductBattlePrep Ability] ability={value.definition.shortName} raw={value.rawValue:0.###} normalized={value.normalizedValue:0.###} fill={value.fillAmount:0.###} fillImageName={value.definition.shortName}_Fill actualFillObject={(fillImage == null ? "null" : fillImage.name)} imageType={(fillImage == null ? "null" : fillImage.type.ToString())} fillAmountAfterAssign={(fillImage == null ? 0f : fillImage.fillAmount):0.###} fillRectWidth={(fillRect == null ? 0f : fillRect.rect.width):0.##} backgroundRectWidth={(backgroundRect == null ? 0f : backgroundRect.rect.width):0.##}",
            this
        );
    }

    public void Clear()
    {
        EnsureVisuals();
        SetText(labelText, "");
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
            labelText = GetOrCreateText(root, "LabelText", "HP", 12, TextAlignmentOptions.MidlineLeft);
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

        if (valueText == null)
        {
            valueText = GetOrCreateText(root, "ValueText", "0", 12, TextAlignmentOptions.MidlineRight);
        }

        HorizontalLayoutGroup rowLayout = root.GetComponent<HorizontalLayoutGroup>();
        if (rowLayout == null)
        {
            rowLayout = root.gameObject.AddComponent<HorizontalLayoutGroup>();
        }
        rowLayout.padding = new RectOffset(0, 0, 0, 0);
        rowLayout.spacing = 5f;
        rowLayout.childAlignment = TextAnchor.MiddleCenter;
        rowLayout.childControlWidth = true;
        rowLayout.childControlHeight = true;
        rowLayout.childForceExpandWidth = false;
        rowLayout.childForceExpandHeight = false;

        ConfigureLayout(labelText == null ? null : labelText.gameObject, LabelWidth, RowHeight, 0f);
        ConfigureLayout(barContainer == null ? null : barContainer.gameObject, 0f, 12f, 1f);
        ConfigureLayout(valueText == null ? null : valueText.gameObject, ValueWidth, RowHeight, 0f);
        if (labelText != null) labelText.transform.SetSiblingIndex(0);
        if (barContainer != null) barContainer.transform.SetSiblingIndex(1);
        if (valueText != null) valueText.transform.SetSiblingIndex(2);

        if (labelText != null)
        {
            labelText.overflowMode = TextOverflowModes.Overflow;
            labelText.enableAutoSizing = false;
            labelText.fontSize = 12;
            labelText.enableWordWrapping = false;
        }

        if (valueText != null)
        {
            valueText.overflowMode = TextOverflowModes.Overflow;
            valueText.enableAutoSizing = false;
            valueText.fontSize = 12;
            valueText.enableWordWrapping = false;
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
            Stretch(fillImage.rectTransform);
            RemoveLayoutComponents(fillImage.gameObject);
        }

        if (backgroundImage != null)
        {
            EnsureImageSprite(backgroundImage);
            backgroundImage.raycastTarget = false;
            Stretch(backgroundImage.rectTransform);
            RemoveLayoutComponents(backgroundImage.gameObject);
        }

        if (barContainer != null)
        {
            Stretch(barContainer);
        }
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

        DestroyObject(legacy.gameObject);
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

    private static void SetText(TMP_Text text, string value)
    {
        if (text != null)
        {
            text.text = value;
        }
    }
}
