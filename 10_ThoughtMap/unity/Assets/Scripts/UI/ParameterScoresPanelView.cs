using System.Text;
using TMPro;
using UnityEngine;

public class ParameterScoresPanelView : MonoBehaviour
{
    [SerializeField] private Transform barContainer;
    [SerializeField] private ParameterScoreBarView barPrefab;
    [SerializeField] private TMP_Text outputText;
    [SerializeField] private string emptyMessage = "Parameter scores are not available yet.";

    public void Clear()
    {
        ClearBars();
        SetText(emptyMessage);
    }

    public void Show(ThoughtMapParameterScore[] scores)
    {
        ShowScores(scores);
    }

    public void ShowScores(ThoughtMapParameterScore[] scores)
    {
        ClearBars();

        if (scores == null || scores.Length == 0)
        {
            SetText(emptyMessage);
            return;
        }

        if (barContainer != null && barPrefab != null)
        {
            SetText(string.Empty);
            foreach (ThoughtMapParameterScore score in scores)
            {
                if (score == null || string.IsNullOrWhiteSpace(score.key))
                {
                    continue;
                }

                ParameterScoreBarView row = Instantiate(barPrefab, barContainer);
                row.Bind(score);
            }
            return;
        }

        SetText(BuildRankText(scores));
    }

    private string BuildRankText(ThoughtMapParameterScore[] scores)
    {
        StringBuilder builder = new StringBuilder();
        foreach (ThoughtMapParameterScore score in scores)
        {
            if (score == null || string.IsNullOrWhiteSpace(score.key))
            {
                continue;
            }

            builder.Append(ParameterScoreBarView.FormatLabel(score.key));
            builder.Append("   ");
            builder.Append(ParameterScoreBarView.ToRank(score.value));
            builder.AppendLine();
        }

        string text = builder.ToString().TrimEnd();
        return string.IsNullOrWhiteSpace(text) ? emptyMessage : text;
    }

    private void ClearBars()
    {
        if (barContainer == null)
        {
            return;
        }

        for (int i = barContainer.childCount - 1; i >= 0; i--)
        {
            Destroy(barContainer.GetChild(i).gameObject);
        }
    }

    private void SetText(string value)
    {
        if (outputText != null)
        {
            outputText.text = value;
        }
    }
}
