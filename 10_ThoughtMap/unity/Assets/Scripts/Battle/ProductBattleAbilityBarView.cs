using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ProductBattleAbilityBarView : MonoBehaviour
{
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
        }
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
            labelText = GetOrCreateText(root, "LabelText", new Vector2(0f, 0f), new Vector2(0.20f, 1f), "HP", 12, TextAlignmentOptions.Left);
        }

        if (backgroundImage == null)
        {
            backgroundImage = GetOrCreateImage(root, "BarBackground", new Vector2(0.22f, 0.22f), new Vector2(0.78f, 0.78f), new Color(0f, 0f, 0f, 0.42f));
        }

        if (fillImage == null)
        {
            fillImage = GetOrCreateImage(backgroundImage.rectTransform, "BarFill", Vector2.zero, Vector2.one, Color.white);
        }

        if (valueText == null)
        {
            valueText = GetOrCreateText(root, "ValueText", new Vector2(0.80f, 0f), new Vector2(1f, 1f), "0", 12, TextAlignmentOptions.Right);
        }

        if (fillImage != null)
        {
            fillImage.type = Image.Type.Filled;
            fillImage.fillMethod = Image.FillMethod.Horizontal;
            fillImage.fillOrigin = (int)Image.OriginHorizontal.Left;
            fillImage.raycastTarget = false;
        }

        if (backgroundImage != null)
        {
            backgroundImage.raycastTarget = false;
        }
    }

    private static TMP_Text GetOrCreateText(RectTransform parent, string name, Vector2 min, Vector2 max, string value, int fontSize, TextAlignmentOptions alignment)
    {
        Transform existing = parent.Find(name);
        GameObject textObject = existing == null ? new GameObject(name, typeof(RectTransform), typeof(TextMeshProUGUI)) : existing.gameObject;
        textObject.transform.SetParent(parent, false);

        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.anchorMin = min;
        rect.anchorMax = max;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;

        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = fontSize;
        text.alignment = alignment;
        text.color = new Color(0.88f, 0.96f, 1f, 1f);
        text.enableWordWrapping = false;
        text.raycastTarget = false;
        return text;
    }

    private static Image GetOrCreateImage(RectTransform parent, string name, Vector2 min, Vector2 max, Color color)
    {
        Transform existing = parent.Find(name);
        GameObject imageObject = existing == null ? new GameObject(name, typeof(RectTransform), typeof(Image)) : existing.gameObject;
        imageObject.transform.SetParent(parent, false);

        RectTransform rect = imageObject.GetComponent<RectTransform>();
        rect.anchorMin = min;
        rect.anchorMax = max;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;

        Image image = imageObject.GetComponent<Image>();
        image.color = color;
        image.raycastTarget = false;
        return image;
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
