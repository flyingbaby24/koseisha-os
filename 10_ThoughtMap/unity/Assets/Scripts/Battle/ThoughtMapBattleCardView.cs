using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ThoughtMapBattleCardView : MonoBehaviour
{
    [SerializeField] private TMP_Text slotText;
    [SerializeField] private TMP_Text nameText;
    [SerializeField] private TMP_Text attributeText;
    [SerializeField] private TMP_Text hpText;
    [SerializeField] private TMP_Text attackText;
    [SerializeField] private Image background;
    [SerializeField] private Button button;

    private ThoughtMapBattleCardData boundCard;
    private int boundSlotIndex;
    private UnityAction<ThoughtMapBattleCardView> clickHandler;

    public ThoughtMapBattleCardData Card => boundCard;
    public int SlotIndex => boundSlotIndex;

    public void BuildIfNeeded()
    {
        RectTransform root = EnsureRectTransform(gameObject);
        background = EnsureImage(gameObject, new Color(0.015f, 0.12f, 0.18f, 0.96f));
        button = EnsureButton(gameObject);

        VerticalLayoutGroup layout = gameObject.GetComponent<VerticalLayoutGroup>();
        if (layout == null)
        {
            layout = gameObject.AddComponent<VerticalLayoutGroup>();
        }
        layout.padding = new RectOffset(8, 8, 8, 8);
        layout.spacing = 3f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        slotText = slotText == null ? CreateText(root, "SlotText", 9, new Color(0.58f, 0.9f, 1f, 1f)) : slotText;
        nameText = nameText == null ? CreateText(root, "NameText", 11, Color.white) : nameText;
        attributeText = attributeText == null ? CreateText(root, "AttributeText", 9, new Color(0.76f, 1f, 0.88f, 1f)) : attributeText;
        hpText = hpText == null ? CreateText(root, "HpText", 9, new Color(1f, 0.86f, 0.62f, 1f)) : hpText;
        attackText = attackText == null ? CreateText(root, "AttackText", 9, new Color(1f, 0.68f, 0.68f, 1f)) : attackText;

        LayoutElement element = gameObject.GetComponent<LayoutElement>();
        if (element == null)
        {
            element = gameObject.AddComponent<LayoutElement>();
        }
        element.preferredWidth = 70f;
        element.preferredHeight = 96f;
        element.minWidth = 64f;
        element.minHeight = 88f;
    }

    public void Bind(ThoughtMapBattleCardData card, int slotIndex, string team)
    {
        BuildIfNeeded();
        boundCard = card;
        boundSlotIndex = slotIndex;

        if (card == null)
        {
            slotText.text = $"{team} {slotIndex + 1}";
            nameText.text = "Empty";
            attributeText.text = "-";
            hpText.text = "HP -";
            attackText.text = "ATK -";
            return;
        }

        slotText.text = $"{team} {slotIndex + 1}";
        nameText.text = Short(card.cardName, 16);
        attributeText.text = $"{card.primaryAttribute} / {card.secondaryAttribute}";
        hpText.text = $"HP {card.MaxHp}";
        attackText.text = $"ATK {Mathf.Max(card.statPhysicalAttack, card.statSkillAttack)}";
    }

    public void SetClickHandler(UnityAction<ThoughtMapBattleCardView> handler)
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

    public void SetSelected(bool selected)
    {
        BuildIfNeeded();
        background.color = selected
            ? new Color(0.0f, 0.44f, 0.62f, 1f)
            : new Color(0.015f, 0.12f, 0.18f, 0.96f);
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
        text.alignment = TextAlignmentOptions.Left;
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
