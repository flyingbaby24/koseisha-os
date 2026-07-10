using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ProductBattleAbilityBarView : MonoBehaviour
{
    private const float RowHeight = 22f;
    private const float LabelWidth = 46f;
    private const float ValueWidth = 42f;

    [SerializeField] private TMP_Text labelText;
    [SerializeField] private TMP_Text valueText;
    [SerializeField] private Image backgroundImage;
    [SerializeField] private Image fillImage;

    public void Bind(ThoughtMapBattleAbilityValue value)
    {
        EnsureVisuals();
        SetText(labelText, value.definition.shortName);
        SetText(valueText, FormatValue(value.rawValue));

        if (backgroundImage != null)
        {
            backgroundImage.color = new Color(0f, 0f, 0f, 0.42f);
        }

        if (fillImage != null)
        {
            fillImage.type = Image.Type.Filled;
            fillImage.fillMethod = Image.FillMethod.Horizontal;
            fillImage.fillOrigin = (int)Image.OriginHorizontal.Left;
            fillImage.fillAmount = value.fillAmount;
            fillImage.color = value.definition.color;
            fillImage.preserveAspect = false;
        }

        Debug.Log(
            $"[ProductBattlePrep Ability] ability={value.definition.shortName} raw={value.rawValue:0.###} normalized={value.normalizedValue:0.###} fill={value.fillAmount:0.###}",
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

        if (backgroundImage == null)
        {
            backgroundImage = GetOrCreateImage(root, "BarBackground", new Color(0f, 0f, 0f, 0.42f));
        }

        if (fillImage == null)
        {
            fillImage = GetOrCreateImage(backgroundImage.rectTransform, "BarFill", Color.white);
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
        ConfigureLayout(backgroundImage == null ? null : backgroundImage.gameObject, 0f, 12f, 1f);
        ConfigureLayout(valueText == null ? null : valueText.gameObject, ValueWidth, RowHeight, 0f);
        if (labelText != null) labelText.transform.SetSiblingIndex(0);
        if (backgroundImage != null) backgroundImage.transform.SetSiblingIndex(1);
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
            fillImage.type = Image.Type.Filled;
            fillImage.fillMethod = Image.FillMethod.Horizontal;
            fillImage.fillOrigin = (int)Image.OriginHorizontal.Left;
            fillImage.preserveAspect = false;
            fillImage.raycastTarget = false;
            Stretch(fillImage.rectTransform);
        }

        if (backgroundImage != null)
        {
            backgroundImage.raycastTarget = false;
            Stretch(backgroundImage.rectTransform);
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
        image.color = color;
        image.raycastTarget = false;
        return image;
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
