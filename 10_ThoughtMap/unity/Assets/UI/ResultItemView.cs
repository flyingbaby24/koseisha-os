using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ResultItemView : MonoBehaviour
{
    [SerializeField] private TMP_Text titleText;
    [SerializeField] private TMP_Text authorText;
    [SerializeField] private Button selectButton;

    private ThoughtMapSearchResult boundResult;
    private Action<ThoughtMapSearchResult> onSelected;

    private void Awake()
    {
        if (selectButton == null)
        {
            selectButton = GetComponent<Button>();
        }

        if (selectButton != null)
        {
            selectButton.onClick.AddListener(HandleClicked);
        }
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
    }

    private void HandleClicked()
    {
        if (boundResult != null)
        {
            onSelected?.Invoke(boundResult);
        }
    }
}
