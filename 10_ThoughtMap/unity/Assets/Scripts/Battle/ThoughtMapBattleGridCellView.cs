using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ThoughtMapBattleGridCellView : MonoBehaviour
{
    [SerializeField] private TMP_Text positionText;
    [SerializeField] private TMP_Text teamText;
    [SerializeField] private TMP_Text cardNameText;
    [SerializeField] private TMP_Text attributeText;
    [SerializeField] private TMP_Text hpText;
    [SerializeField] private Image background;
    [SerializeField] private Button button;

    private int gridX;
    private int gridY;
    private ThoughtMapBattleUnit boundUnit;
    private UnityAction<ThoughtMapBattleGridCellView> clickHandler;

    public int X => gridX;
    public int Y => gridY;
    public ThoughtMapBattleUnit Unit => boundUnit;

    public void BuildIfNeeded()
    {
        RectTransform root = EnsureRectTransform(gameObject);
        background = EnsureImage(gameObject, new Color(0.012f, 0.09f, 0.13f, 0.9f));
        button = EnsureButton(gameObject);

        VerticalLayoutGroup layout = gameObject.GetComponent<VerticalLayoutGroup>();
        if (layout == null)
        {
            layout = gameObject.AddComponent<VerticalLayoutGroup>();
        }
        layout.padding = new RectOffset(4, 4, 4, 4);
        layout.spacing = 1f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        positionText = positionText == null ? CreateText(root, "PositionText", 8, new Color(0.45f, 0.8f, 1f, 1f)) : positionText;
        teamText = teamText == null ? CreateText(root, "TeamText", 9, Color.white) : teamText;
        cardNameText = cardNameText == null ? CreateText(root, "CardNameText", 9, Color.white) : cardNameText;
        attributeText = attributeText == null ? CreateText(root, "AttributeText", 8, new Color(0.74f, 1f, 0.82f, 1f)) : attributeText;
        hpText = hpText == null ? CreateText(root, "HpText", 8, new Color(1f, 0.84f, 0.58f, 1f)) : hpText;
    }

    public void BindEmpty(int x, int y)
    {
        BuildIfNeeded();
        gridX = x;
        gridY = y;
        boundUnit = null;
        background.color = new Color(0.012f, 0.09f, 0.13f, 0.9f);
        positionText.text = $"{x},{y}";
        teamText.text = "";
        cardNameText.text = "\u25A1";
        attributeText.text = "";
        hpText.text = "";
    }

    public void BindUnit(ThoughtMapBattleUnit unit)
    {
        BuildIfNeeded();
        if (unit == null || unit.card == null)
        {
            BindEmpty(0, 0);
            return;
        }

        gridX = unit.position.x;
        gridY = unit.position.y;
        boundUnit = unit;
        bool player = unit.team == "Player";
        background.color = player
            ? new Color(0.0f, 0.24f, 0.34f, 0.96f)
            : new Color(0.26f, 0.06f, 0.12f, 0.96f);
        positionText.text = $"{unit.position.x},{unit.position.y}";
        teamText.text = player ? "PLAYER" : "ENEMY";
        cardNameText.text = Short(unit.card.cardName, 12);
        attributeText.text = unit.card.primaryAttribute;
        hpText.text = $"HP {unit.hp}";
    }

    public void SetClickHandler(UnityAction<ThoughtMapBattleGridCellView> handler)
    {
        BuildIfNeeded();
        if (clickHandler != null)
        {
            button.onClick.RemoveListener(HandleClicked);
        }

        clickHandler = handler;
        if (clickHandler != null)
        {
            button.onClick.AddListener(HandleClicked);
        }
    }

    public void SetPlacementHint(bool available)
    {
        if (boundUnit != null)
        {
            return;
        }

        background.color = available
            ? new Color(0.0f, 0.24f, 0.23f, 0.96f)
            : new Color(0.012f, 0.09f, 0.13f, 0.9f);
    }

    public void SetInteractable(bool interactable)
    {
        BuildIfNeeded();
        button.interactable = interactable;
    }

    private void HandleClicked()
    {
        clickHandler?.Invoke(this);
    }

    private TMP_Text CreateText(RectTransform parent, string name, int fontSize, Color color)
    {
        GameObject textObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.fontSize = fontSize;
        text.color = color;
        text.alignment = TextAlignmentOptions.Center;
        text.enableWordWrapping = false;
        text.overflowMode = TextOverflowModes.Ellipsis;
        text.raycastTarget = false;
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
        image.raycastTarget = true;
        return image;
    }

    private Button EnsureButton(GameObject target)
    {
        Button existingButton = target.GetComponent<Button>();
        if (existingButton == null)
        {
            existingButton = target.AddComponent<Button>();
        }
        existingButton.targetGraphic = target.GetComponent<Graphic>();
        return existingButton;
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

    private string Short(string value, int maxLength)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "Card";
        }

        return value.Length <= maxLength ? value : value.Substring(0, maxLength) + "...";
    }
}
