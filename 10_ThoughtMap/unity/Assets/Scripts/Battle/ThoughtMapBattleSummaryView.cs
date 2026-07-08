using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ThoughtMapBattleSummaryView : MonoBehaviour
{
    [SerializeField] private TMP_Text titleText;
    [SerializeField] private TMP_Text resultText;
    [SerializeField] private TMP_Text damageDoneText;
    [SerializeField] private TMP_Text damageTakenText;
    [SerializeField] private TMP_Text survivedText;
    [SerializeField] private TMP_Text lostText;

    public void BuildIfNeeded()
    {
        RectTransform root = EnsureRectTransform(gameObject);
        EnsureImage(gameObject, new Color(0.01f, 0.12f, 0.15f, 0.92f));

        VerticalLayoutGroup layout = gameObject.GetComponent<VerticalLayoutGroup>();
        if (layout == null)
        {
            layout = gameObject.AddComponent<VerticalLayoutGroup>();
        }
        layout.padding = new RectOffset(12, 12, 10, 10);
        layout.spacing = 4f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;

        titleText = titleText == null ? CreateText(root, "TitleText", "Battle Summary", 16, new Color(0.78f, 1f, 1f, 1f)) : titleText;
        resultText = resultText == null ? CreateText(root, "ResultText", "Result: -", 15, Color.white) : resultText;
        damageDoneText = damageDoneText == null ? CreateText(root, "DamageDoneText", "Damage Done: -", 13, Color.white) : damageDoneText;
        damageTakenText = damageTakenText == null ? CreateText(root, "DamageTakenText", "Damage Taken: -", 13, Color.white) : damageTakenText;
        survivedText = survivedText == null ? CreateText(root, "SurvivedText", "Cards Survived: -", 13, Color.white) : survivedText;
        lostText = lostText == null ? CreateText(root, "LostText", "Cards Lost: -", 13, Color.white) : lostText;
    }

    public void ShowPending()
    {
        BuildIfNeeded();
        resultText.text = "Result: Battle not started";
        damageDoneText.text = "Damage Done: -";
        damageTakenText.text = "Damage Taken: -";
        survivedText.text = "Cards Survived: -";
        lostText.text = "Cards Lost: -";
        gameObject.SetActive(false);
    }

    public void ShowReport(string resultLabel, ThoughtMapBattleReport report)
    {
        gameObject.SetActive(true);
        BuildIfNeeded();
        if (report == null)
        {
            ShowPending();
            return;
        }

        resultText.text = $"Result: {resultLabel}";
        damageDoneText.text = $"Damage Done: {report.playerDamageDone}";
        damageTakenText.text = $"Damage Taken: {report.playerDamageTaken}";
        survivedText.text = $"Cards Survived: {report.playerCardsSurvived}";
        lostText.text = $"Cards Lost: {report.playerCardsLost}";
    }

    private TMP_Text CreateText(RectTransform parent, string name, string value, int fontSize, Color color)
    {
        GameObject textObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.text = value;
        text.fontSize = fontSize;
        text.color = color;
        text.alignment = TextAlignmentOptions.Left;
        text.enableWordWrapping = false;
        text.overflowMode = TextOverflowModes.Ellipsis;
        return text;
    }

    private Image EnsureImage(GameObject target, Color color)
    {
        Image image = target.GetComponent<Image>();
        if (image == null)
        {
            image = target.AddComponent<Image>();
        }
        image.color = color;
        image.raycastTarget = false;
        return image;
    }

    private RectTransform EnsureRectTransform(GameObject target)
    {
        RectTransform rect = target.GetComponent<RectTransform>();
        if (rect == null)
        {
            rect = target.AddComponent<RectTransform>();
        }
        return rect;
    }
}
