using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleGridCellView : MonoBehaviour
{
    [SerializeField] private Image background;
    [SerializeField] private Image cardFrame;
    [SerializeField] private TMP_Text positionText;
    [SerializeField] private TMP_Text unitIdText;
    [SerializeField] private TMP_Text cardNameText;
    [SerializeField] private TMP_Text attributeText;
    [SerializeField] private Button button;

    private int x;
    private int y;
    private ThoughtMapBattleCardData card;
    private UnityAction<ProductBattleGridCellView> clickHandler;

    public int X => x;
    public int Y => y;
    public ThoughtMapBattleCardData Card => card;

    public void BuildIfNeeded()
    {
        RectTransform root = EnsureRectTransform(gameObject);
        background = EnsureImage(gameObject, new Color(0.01f, 0.09f, 0.13f, 0.92f));
        button = EnsureButton(gameObject);

        VerticalLayoutGroup layout = gameObject.GetComponent<VerticalLayoutGroup>();
        if (layout == null)
        {
            layout = gameObject.AddComponent<VerticalLayoutGroup>();
        }
        layout.padding = new RectOffset(6, 6, 6, 6);
        layout.spacing = 3f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        positionText = positionText == null ? CreateText(root, "PositionText", 10, new Color(0.46f, 0.82f, 1f, 1f)) : positionText;
        cardFrame = cardFrame == null ? CreateImage(root, "CardFrame", new Color(0.015f, 0.16f, 0.22f, 1f), 32f) : cardFrame;
        unitIdText = unitIdText == null ? CreateText(root, "UnitIdText", 12, new Color(0.6f, 1f, 1f, 1f)) : unitIdText;
        cardNameText = cardNameText == null ? CreateText(root, "CardNameText", 10, Color.white) : cardNameText;
        attributeText = attributeText == null ? CreateText(root, "AttributeText", 9, new Color(0.74f, 1f, 0.84f, 1f)) : attributeText;
    }

    public void BindEmpty(int gridX, int gridY, bool available)
    {
        BuildIfNeeded();
        x = gridX;
        y = gridY;
        card = null;
        background.color = available
            ? new Color(0.01f, 0.14f, 0.14f, 0.92f)
            : new Color(0.01f, 0.07f, 0.10f, 0.92f);
        positionText.text = $"{x},{y}";
        unitIdText.text = "";
        cardNameText.text = available ? "Deploy" : "";
        attributeText.text = "";
        cardFrame.color = available
            ? new Color(0.0f, 0.24f, 0.28f, 1f)
            : new Color(0.02f, 0.06f, 0.08f, 1f);
    }

    public void BindCard(int gridX, int gridY, ThoughtMapBattleCardData sourceCard, string unitId)
    {
        BuildIfNeeded();
        x = gridX;
        y = gridY;
        card = sourceCard;
        background.color = new Color(0.0f, 0.22f, 0.30f, 0.96f);
        cardFrame.color = new Color(0.0f, 0.42f, 0.52f, 1f);
        positionText.text = $"{x},{y}";
        unitIdText.text = unitId;
        cardNameText.text = Short(sourceCard == null ? "Empty" : sourceCard.cardName, 16);
        attributeText.text = sourceCard == null ? "-" : Short(sourceCard.primaryAttribute, 12);
    }

    public void SetClickHandler(UnityAction<ProductBattleGridCellView> handler)
    {
        BuildIfNeeded();
        button.onClick.RemoveListener(HandleClicked);
        clickHandler = handler;
        if (clickHandler != null)
        {
            button.onClick.AddListener(HandleClicked);
        }
    }

    private void HandleClicked()
    {
        clickHandler?.Invoke(this);
    }

    private Image CreateImage(RectTransform parent, string name, Color color, float height)
    {
        GameObject imageObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Image));
        RectTransform rect = imageObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        Image image = imageObject.GetComponent<Image>();
        image.color = color;
        image.raycastTarget = false;
        LayoutElement element = imageObject.AddComponent<LayoutElement>();
        element.preferredHeight = height;
        element.minHeight = height;
        return image;
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
