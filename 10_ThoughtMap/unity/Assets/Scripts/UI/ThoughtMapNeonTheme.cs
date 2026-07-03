using TMPro;
using UnityEngine;
using UnityEngine.UI;

[ExecuteAlways]
public class ThoughtMapNeonTheme : MonoBehaviour
{
    [Header("Scope")]
    [SerializeField] private Transform themeRoot;
    [SerializeField] private Camera targetCamera;
    [SerializeField] private bool applyOnEnable = true;

    [Header("Palette")]
    [SerializeField] private Color backgroundColor = new Color(0.005f, 0.018f, 0.05f, 1f);
    [SerializeField] private Color panelColor = new Color(0.012f, 0.045f, 0.10f, 0.82f);
    [SerializeField] private Color cardColor = new Color(0.015f, 0.055f, 0.12f, 0.90f);
    [SerializeField] private Color controlColor = new Color(0.018f, 0.05f, 0.11f, 0.96f);
    [SerializeField] private Color cyan = new Color(0.05f, 0.72f, 1f, 1f);
    [SerializeField] private Color cyanDim = new Color(0.05f, 0.42f, 0.75f, 0.72f);
    [SerializeField] private Color textPrimary = new Color(0.90f, 0.97f, 1f, 1f);
    [SerializeField] private Color textSecondary = new Color(0.58f, 0.76f, 0.90f, 1f);

    private void OnEnable()
    {
        if (applyOnEnable)
        {
            ApplyTheme();
        }
    }

    [ContextMenu("Apply Neon Theme")]
    public void ApplyTheme()
    {
        Transform root = themeRoot == null ? transform : themeRoot;
        ApplyCamera();
        ApplyImages(root);
        ApplyText(root);
        ApplyButtons(root);
        ApplyDropdowns(root);
        ApplyInputFields(root);
    }

    private void ApplyCamera()
    {
        Camera camera = targetCamera == null ? Camera.main : targetCamera;
        if (camera == null)
        {
            return;
        }

        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = backgroundColor;
    }

    private void ApplyImages(Transform root)
    {
        foreach (Image image in root.GetComponentsInChildren<Image>(true))
        {
            string lowerName = image.name.ToLowerInvariant();
            if (lowerName.Contains("background") || lowerName.Contains("canvas"))
            {
                image.color = backgroundColor;
                continue;
            }

            if (lowerName.Contains("button") || lowerName.Contains("dropdown") || lowerName.Contains("input") || lowerName.Contains("search"))
            {
                image.color = controlColor;
                EnsureOutline(image.gameObject, cyanDim, new Vector2(1.2f, -1.2f));
                continue;
            }

            if (lowerName.Contains("item") || lowerName.Contains("result"))
            {
                image.color = cardColor;
                EnsureOutline(image.gameObject, cyanDim, new Vector2(1.0f, -1.0f));
                continue;
            }

            if (lowerName.Contains("panel") || lowerName.Contains("scroll") || lowerName.Contains("viewport") || lowerName.Contains("content"))
            {
                image.color = panelColor;
                EnsureOutline(image.gameObject, new Color(cyan.r, cyan.g, cyan.b, 0.32f), new Vector2(1.0f, -1.0f));
            }
        }
    }

    private void ApplyText(Transform root)
    {
        foreach (TMP_Text text in root.GetComponentsInChildren<TMP_Text>(true))
        {
            string lowerName = text.name.ToLowerInvariant();
            if (lowerName.Contains("title") || lowerName.Contains("thoughtmap"))
            {
                text.color = textPrimary;
                text.fontStyle |= FontStyles.Bold;
                continue;
            }

            if (lowerName.Contains("label") || lowerName.Contains("source") || lowerName.Contains("doc") || lowerName.Contains("score") || lowerName.Contains("status"))
            {
                text.color = textSecondary;
                continue;
            }

            text.color = textPrimary;
        }
    }

    private void ApplyButtons(Transform root)
    {
        foreach (Button button in root.GetComponentsInChildren<Button>(true))
        {
            ColorBlock colors = button.colors;
            colors.normalColor = controlColor;
            colors.highlightedColor = new Color(0.03f, 0.16f, 0.30f, 1f);
            colors.pressedColor = new Color(0.05f, 0.32f, 0.56f, 1f);
            colors.selectedColor = new Color(0.03f, 0.20f, 0.38f, 1f);
            colors.disabledColor = new Color(0.04f, 0.06f, 0.09f, 0.45f);
            colors.colorMultiplier = 1f;
            button.colors = colors;

            Image image = button.GetComponent<Image>();
            if (image != null)
            {
                image.color = controlColor;
                EnsureOutline(button.gameObject, cyan, new Vector2(1.4f, -1.4f));
            }

            TMP_Text label = button.GetComponentInChildren<TMP_Text>(true);
            if (label != null)
            {
                label.color = textPrimary;
            }
        }
    }

    private void ApplyDropdowns(Transform root)
    {
        foreach (TMP_Dropdown dropdown in root.GetComponentsInChildren<TMP_Dropdown>(true))
        {
            Image image = dropdown.GetComponent<Image>();
            if (image != null)
            {
                image.color = controlColor;
                EnsureOutline(dropdown.gameObject, cyanDim, new Vector2(1.2f, -1.2f));
            }

            if (dropdown.captionText != null)
            {
                dropdown.captionText.color = textPrimary;
            }

            if (dropdown.itemText != null)
            {
                dropdown.itemText.color = textPrimary;
            }
        }
    }

    private void ApplyInputFields(Transform root)
    {
        foreach (TMP_InputField input in root.GetComponentsInChildren<TMP_InputField>(true))
        {
            Image image = input.GetComponent<Image>();
            if (image != null)
            {
                image.color = controlColor;
                EnsureOutline(input.gameObject, cyanDim, new Vector2(1.2f, -1.2f));
            }

            if (input.textComponent != null)
            {
                input.textComponent.color = textPrimary;
            }

            if (input.placeholder is TMP_Text placeholder)
            {
                placeholder.color = new Color(textSecondary.r, textSecondary.g, textSecondary.b, 0.58f);
            }
        }
    }

    private void EnsureOutline(GameObject target, Color color, Vector2 distance)
    {
        Outline outline = target.GetComponent<Outline>();
        if (outline == null)
        {
            outline = target.AddComponent<Outline>();
        }

        outline.effectColor = color;
        outline.effectDistance = distance;
        outline.useGraphicAlpha = true;
    }
}
