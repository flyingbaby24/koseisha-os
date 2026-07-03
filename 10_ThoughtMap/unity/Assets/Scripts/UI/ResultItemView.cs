using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ResultItemView : MonoBehaviour
{
    [SerializeField] private TMP_Text titleText;
    [SerializeField] private TMP_Text authorText;
    [SerializeField] private TMP_Text similarityText;
    [SerializeField] private Button selectButton;
    [SerializeField] private Image backgroundImage;
    [SerializeField] private Outline selectionOutline;
    [SerializeField] private Color normalColor = new Color(0.015f, 0.045f, 0.10f, 0.90f);
    [SerializeField] private Color selectedColor = new Color(0.02f, 0.12f, 0.24f, 0.98f);
    [SerializeField] private Color selectedOutlineColor = new Color(0.05f, 0.72f, 1f, 0.95f);
    [SerializeField] private Color titleColor = new Color(0.92f, 0.98f, 1f, 1f);
    [SerializeField] private Color secondaryColor = new Color(0.60f, 0.78f, 0.92f, 1f);

    private ThoughtMapSearchResult boundResult;
    private Action<ThoughtMapSearchResult> onSelected;

    private void Awake()
    {
        if (selectButton == null)
        {
            selectButton = GetComponent<Button>();
        }

        if (backgroundImage == null)
        {
            backgroundImage = GetComponent<Image>();
        }

        if (selectionOutline == null)
        {
            selectionOutline = GetComponent<Outline>();
        }

        if (selectionOutline == null)
        {
            selectionOutline = gameObject.AddComponent<Outline>();
            selectionOutline.effectDistance = new Vector2(1.5f, -1.5f);
        }

        if (selectButton != null)
        {
            selectButton.onClick.AddListener(HandleClicked);
        }

        ApplyTextColors();
        SetSelected(false);
    }

    private void OnDestroy()
    {
        if (selectButton != null)
        {
            selectButton.onClick.RemoveListener(HandleClicked);
        }
    }

    public void Bind(ThoughtMapSearchResult result)
    {
        Bind(result, null);
    }

    public void Bind(ThoughtMapSearchResult result, Action<ThoughtMapSearchResult> selectedCallback)
    {
        boundResult = result;
        onSelected = selectedCallback;

        string title = result == null || string.IsNullOrWhiteSpace(result.title) ? "Untitled" : result.title;
        string author = result == null || string.IsNullOrWhiteSpace(result.author) ? "Unknown" : result.author;

        if (titleText != null)
        {
            titleText.text = title;
        }

        if (authorText != null)
        {
            authorText.text = author;
        }

        if (similarityText != null)
        {
            similarityText.text = result == null ? string.Empty : result.similarity.ToString("0.0000");
        }

        ApplyTextColors();
        SetSelected(false);
    }

    public void SetSelected(bool selected)
    {
        if (backgroundImage != null)
        {
            backgroundImage.color = selected ? selectedColor : normalColor;
        }

        if (selectionOutline != null)
        {
            selectionOutline.enabled = selected;
            selectionOutline.effectColor = selectedOutlineColor;
            selectionOutline.effectDistance = selected ? new Vector2(2.0f, -2.0f) : Vector2.zero;
        }
    }

    private void ApplyTextColors()
    {
        if (titleText != null)
        {
            titleText.color = titleColor;
            titleText.fontStyle |= FontStyles.Bold;
        }

        if (authorText != null)
        {
            authorText.color = secondaryColor;
        }

        if (similarityText != null)
        {
            similarityText.color = titleColor;
        }
    }

    private void HandleClicked()
    {
        if (boundResult != null)
        {
            onSelected?.Invoke(boundResult);
        }
    }
}
