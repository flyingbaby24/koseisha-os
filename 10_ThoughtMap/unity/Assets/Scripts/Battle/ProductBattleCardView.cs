using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleCardView : MonoBehaviour
{
    [SerializeField] private Image background;
    [SerializeField] private Image artImage;
    [SerializeField] private Image attributeIconImage;
    [SerializeField] private TMP_Text idText;
    [SerializeField] private TMP_Text nameText;
    [SerializeField] private TMP_Text attributeText;
    [SerializeField] private TMP_Text hpText;
    [SerializeField] private TMP_Text atkText;
    [SerializeField] private TMP_Text skillText;
    [SerializeField] private TMP_Text rarityText;
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private Button button;

    private ThoughtMapBattleCardData card;
    private int index;
    private UnityAction<ProductBattleCardView> clickHandler;

    public ThoughtMapBattleCardData Card => card;
    public int Index => index;

    public void BuildIfNeeded()
    {
        RectTransform root = EnsureRectTransform(gameObject);
        background = EnsureImage(gameObject, new Color(0.025f, 0.07f, 0.12f, 0.98f));
        button = EnsureButton(gameObject);

        VerticalLayoutGroup layout = gameObject.GetComponent<VerticalLayoutGroup>();
        if (layout == null)
        {
            layout = gameObject.AddComponent<VerticalLayoutGroup>();
        }
        layout.padding = new RectOffset(8, 8, 8, 8);
        layout.spacing = 4f;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        idText = idText == null ? CreateText(root, "UnitIdText", 13, new Color(0.56f, 0.95f, 1f, 1f), TextAlignmentOptions.Center) : idText;
        artImage = artImage == null ? CreatePanelImage(root, "ArtFrame", new Color(0.08f, 0.18f, 0.25f, 1f), 72f) : artImage;
        nameText = nameText == null ? CreateText(root, "NameText", 12, Color.white, TextAlignmentOptions.Center) : nameText;
        attributeIconImage = attributeIconImage == null ? CreatePanelImage(root, "AttributeIcon", new Color(0.0f, 0.54f, 0.72f, 1f), 18f) : attributeIconImage;
        attributeText = attributeText == null ? CreateText(root, "AttributeText", 10, new Color(0.74f, 1f, 0.86f, 1f), TextAlignmentOptions.Center) : attributeText;
        hpText = hpText == null ? CreateText(root, "HpText", 10, new Color(1f, 0.86f, 0.56f, 1f), TextAlignmentOptions.Center) : hpText;
        atkText = atkText == null ? CreateText(root, "AtkText", 10, new Color(1f, 0.66f, 0.66f, 1f), TextAlignmentOptions.Center) : atkText;
        skillText = skillText == null ? CreateText(root, "SkillText", 10, new Color(0.76f, 0.84f, 1f, 1f), TextAlignmentOptions.Center) : skillText;
        rarityText = rarityText == null ? CreateText(root, "RarityText", 10, new Color(1f, 0.9f, 0.42f, 1f), TextAlignmentOptions.Center) : rarityText;
        statusText = statusText == null ? CreateText(root, "StatusText", 10, new Color(0.8f, 0.9f, 0.96f, 1f), TextAlignmentOptions.Center) : statusText;

        LayoutElement element = gameObject.GetComponent<LayoutElement>();
        if (element == null)
        {
            element = gameObject.AddComponent<LayoutElement>();
        }
        element.preferredWidth = 150f;
        element.preferredHeight = 250f;
        element.minWidth = 132f;
        element.minHeight = 220f;
    }

    public void Bind(ThoughtMapBattleCardData sourceCard, int sourceIndex, string unitId, bool selected, bool placed, Sprite artSprite, Sprite attributeSprite)
    {
        BuildIfNeeded();
        card = sourceCard;
        index = sourceIndex;
        idText.text = unitId;
        nameText.text = Short(sourceCard == null ? "Empty" : sourceCard.cardName, 20);
        attributeText.text = sourceCard == null ? "-" : Short(sourceCard.primaryAttribute, 16);
        hpText.text = sourceCard == null ? "HP -" : $"HP {sourceCard.MaxHp}";
        atkText.text = sourceCard == null ? "ATK -" : $"ATK {Mathf.Max(sourceCard.statPhysicalAttack, sourceCard.statSkillAttack)}";
        skillText.text = sourceCard == null ? "Skill -" : $"Skill {sourceCard.skillSeed % 100:00}";
        rarityText.text = sourceCard == null ? "Rarity -" : $"Rarity {1 + Mathf.Abs(sourceCard.raritySeed % 5)}";
        statusText.text = placed ? "Placed" : "Ready";
        artImage.sprite = artSprite;
        attributeIconImage.sprite = attributeSprite;
        background.color = selected
            ? new Color(0.0f, 0.36f, 0.52f, 1f)
            : placed
                ? new Color(0.02f, 0.16f, 0.18f, 1f)
                : new Color(0.025f, 0.07f, 0.12f, 0.98f);
    }

    public void SetClickHandler(UnityAction<ProductBattleCardView> handler)
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

    private Image CreatePanelImage(RectTransform parent, string name, Color color, float height)
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

    private TMP_Text CreateText(RectTransform parent, string name, int fontSize, Color color, TextAlignmentOptions alignment)
    {
        GameObject textObject = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = textObject.GetComponent<RectTransform>();
        rect.SetParent(parent, false);
        TMP_Text text = textObject.GetComponent<TMP_Text>();
        text.fontSize = fontSize;
        text.color = color;
        text.alignment = alignment;
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
