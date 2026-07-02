using System.Text;
using TMPro;
using UnityEngine;

public class ParameterScoresPanelView : MonoBehaviour
{
    [SerializeField] private TMP_Text outputText;
    [SerializeField] private string emptyMessage = "Parameter scores are not available yet.";

    public void Clear()
    {
        SetText(emptyMessage);
    }

    public void ShowScores(ThoughtMapParameterScore[] scores)
    {
        if (scores == null || scores.Length == 0)
        {
            Clear();
            return;
        }

        StringBuilder builder = new StringBuilder();
        foreach (ThoughtMapParameterScore score in scores)
        {
            if (score == null || string.IsNullOrWhiteSpace(score.key))
            {
                continue;
            }

            builder.Append(score.key);
            builder.Append(": ");
            builder.Append(score.value.ToString("0.###"));
            builder.AppendLine();
        }

        string text = builder.ToString().TrimEnd();
        SetText(string.IsNullOrWhiteSpace(text) ? emptyMessage : text);
    }

    private void SetText(string value)
    {
        if (outputText != null)
        {
            outputText.text = value;
        }
    }
}
