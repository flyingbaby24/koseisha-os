using TMPro;
using UnityEngine;

public class QueryParameterPanelView : MonoBehaviour
{
    [SerializeField] private ParameterScoresPanelView parameterScoresPanelView;
    [SerializeField] private TMP_Text titleText;
    [SerializeField] private string titlePrefix = "Query Parameters";

    private void Awake()
    {
        Clear();
    }

    public void Clear()
    {
        SetTitle(titlePrefix);
        parameterScoresPanelView?.Clear();
    }

    public void ShowScores(string query, ThoughtMapParameterScore[] scores)
    {
        string label = string.IsNullOrWhiteSpace(query) ? titlePrefix : $"{titlePrefix}: {query}";
        SetTitle(label);
        parameterScoresPanelView?.ShowScores(scores);
    }

    private void SetTitle(string value)
    {
        if (titleText != null)
        {
            titleText.text = value;
        }
    }
}
