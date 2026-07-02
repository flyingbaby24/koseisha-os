using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ParameterScoreBarView : MonoBehaviour
{
    [SerializeField] private TMP_Text labelText;
    [SerializeField] private RectTransform barFill;
    [SerializeField] private TMP_Text valueText;
    [SerializeField] private Image barFillImage;
    [SerializeField] private Color rankSColor = new Color(0.95f, 0.75f, 0.18f);
    [SerializeField] private Color rankAColor = new Color(0.32f, 0.72f, 1.0f);
    [SerializeField] private Color rankBColor = new Color(0.40f, 0.85f, 0.50f);
    [SerializeField] private Color rankCColor = new Color(0.85f, 0.70f, 0.35f);
    [SerializeField] private Color rankDColor = new Color(0.65f, 0.65f, 0.65f);

    public float RawValue { get; private set; }
    public string ParameterKey { get; private set; }
    public string Rank { get; private set; }

    public void Bind(ThoughtMapParameterScore score)
    {
        if (score == null)
        {
            Bind(string.Empty, 0f);
            return;
        }

        Bind(score.key, score.value);
    }

    public void Bind(string key, float value)
    {
        ParameterKey = key ?? string.Empty;
        RawValue = Mathf.Clamp(value, 0f, 100f);
        Rank = ToRank(RawValue);

        if (labelText != null)
        {
            labelText.text = FormatLabel(ParameterKey);
        }

        if (valueText != null)
        {
            valueText.text = Rank;
        }

        if (barFill != null)
        {
            Vector3 scale = barFill.localScale;
            scale.x = RawValue / 100f;
            barFill.localScale = scale;
        }

        if (barFillImage != null)
        {
            barFillImage.color = GetRankColor(Rank);
        }
    }

    public static string ToRank(float value)
    {
        if (value >= 40f)
        {
            return "S";
        }

        if (value >= 30f)
        {
            return "A";
        }

        if (value >= 20f)
        {
            return "B";
        }

        if (value >= 10f)
        {
            return "C";
        }

        return "D";
    }

    public static string FormatLabel(string key)
    {
        if (string.IsNullOrWhiteSpace(key))
        {
            return "Unknown";
        }

        string trimmed = key.Trim().Replace("_", " ");
        return char.ToUpperInvariant(trimmed[0]) + trimmed.Substring(1);
    }

    private Color GetRankColor(string rank)
    {
        switch (rank)
        {
            case "S":
                return rankSColor;
            case "A":
                return rankAColor;
            case "B":
                return rankBColor;
            case "C":
                return rankCColor;
            default:
                return rankDColor;
        }
    }
}
