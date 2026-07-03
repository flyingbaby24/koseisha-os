using System;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class DetailPanelView : MonoBehaviour
{
    [SerializeField] private GameObject emptyStateRoot;
    [SerializeField] private GameObject contentRoot;
    [SerializeField] private TMP_Text titleText;
    [SerializeField] private TMP_Text authorText;
    [SerializeField] private TMP_Text sourceText;
    [SerializeField] private TMP_Text docIdText;
    [SerializeField] private TMP_Text similarityText;
    [SerializeField] private TMP_Text bodyText;
    [SerializeField] private TMP_Text saveStatusText;
    [SerializeField] private Button saveButton;
    [SerializeField] private ParameterScoresPanelView parameterScoresPanelView;
    [SerializeField] private ParameterRadarChartView radarChartView;

    private ThoughtMapSearchResult currentResult;

    public event Action<ThoughtMapSearchResult> SaveRequested;

    private void Awake()
    {
        if (saveButton != null)
        {
            saveButton.onClick.AddListener(HandleSaveClicked);
        }

        Clear();
    }

    private void OnDestroy()
    {
        if (saveButton != null)
        {
            saveButton.onClick.RemoveListener(HandleSaveClicked);
        }
    }

    public void Clear()
    {
        currentResult = null;
        SetVisible(false);
        SetText(titleText, "Select a result");
        SetText(authorText, "");
        SetText(sourceText, "");
        SetText(docIdText, "");
        SetText(similarityText, "");
        SetText(bodyText, "Select a search result to preview document details.");
        SetSaveStatus("");
        SetSaveInteractable(false);
        parameterScoresPanelView?.Clear();
        radarChartView?.Clear();
    }

    public void ShowResult(ThoughtMapSearchResult result)
    {
        if (result == null)
        {
            Clear();
            return;
        }

        currentResult = result;
        SetVisible(true);
        SetText(titleText, string.IsNullOrWhiteSpace(result.title) ? "Untitled" : result.title);
        SetText(authorText, string.IsNullOrWhiteSpace(result.author) ? "Unknown" : result.author);
        SetText(sourceText, string.IsNullOrWhiteSpace(result.source) ? "Source: Unknown" : $"Source: {result.source}");
        SetText(docIdText, string.IsNullOrWhiteSpace(result.doc_id) ? "Doc ID: Unknown" : $"Doc ID: {result.doc_id}");
        SetText(similarityText, $"Score: {result.similarity:0.0000}");
        SetText(
            bodyText,
            "Document detail API is not connected yet. This panel is showing the selected search result."
        );
        SetSaveStatus("");
        SetSaveInteractable(!string.IsNullOrWhiteSpace(result.doc_id));
        parameterScoresPanelView?.ShowScores(result.parameters);
        radarChartView?.ShowScores(result.parameters);
    }

    public void ShowPlaceholder(ThoughtMapSearchResult result)
    {
        ShowResult(result);
    }

    public void SetSaving()
    {
        SetSaveStatus("Saving...");
        SetSaveInteractable(false);
    }

    public void SetSaved(bool duplicate)
    {
        SetSaveStatus(duplicate ? "Already saved" : "Saved");
        SetSaveInteractable(false);
    }

    public void SetSaveError(string message)
    {
        SetSaveStatus(string.IsNullOrWhiteSpace(message) ? "Save failed" : $"Save failed: {message}");
        SetSaveInteractable(currentResult != null && !string.IsNullOrWhiteSpace(currentResult.doc_id));
    }

    private void HandleSaveClicked()
    {
        if (currentResult == null)
        {
            return;
        }

        SaveRequested?.Invoke(currentResult);
    }

    private void SetVisible(bool hasContent)
    {
        if (emptyStateRoot != null)
        {
            emptyStateRoot.SetActive(!hasContent);
        }

        if (contentRoot != null)
        {
            contentRoot.SetActive(hasContent);
        }
    }

    private void SetSaveInteractable(bool value)
    {
        if (saveButton != null)
        {
            saveButton.interactable = value;
        }
    }

    private void SetSaveStatus(string value)
    {
        SetText(saveStatusText, value);
    }

    private void SetText(TMP_Text target, string value)
    {
        if (target != null)
        {
            target.text = value;
        }
    }
}
