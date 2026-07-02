using TMPro;
using UnityEngine;

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
    [SerializeField] private ParameterScoresPanelView parameterScoresPanelView;

    private void Awake()
    {
        Clear();
    }

    public void Clear()
    {
        SetVisible(false);
        SetText(titleText, "Select a result");
        SetText(authorText, "");
        SetText(sourceText, "");
        SetText(docIdText, "");
        SetText(similarityText, "");
        SetText(bodyText, "Select a search result to preview document details.");
        parameterScoresPanelView?.Clear();
    }

    public void ShowPlaceholder(ThoughtMapSearchResult result)
    {
        if (result == null)
        {
            Clear();
            return;
        }

        SetVisible(true);
        SetText(titleText, string.IsNullOrWhiteSpace(result.title) ? "Untitled" : result.title);
        SetText(authorText, string.IsNullOrWhiteSpace(result.author) ? "Unknown" : result.author);
        SetText(sourceText, string.IsNullOrWhiteSpace(result.source) ? "Source: Unknown" : $"Source: {result.source}");
        SetText(docIdText, string.IsNullOrWhiteSpace(result.doc_id) ? "Doc ID: Unknown" : $"Doc ID: {result.doc_id}");
        SetText(similarityText, $"Score: {result.similarity:0.0000}");
        SetText(
            bodyText,
            "Document detail API is not connected yet. This panel is ready for a future GET /document/{doc_id} response."
        );
        parameterScoresPanelView?.ShowScores(result.parameters);
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

    private void SetText(TMP_Text target, string value)
    {
        if (target != null)
        {
            target.text = value;
        }
    }
}
