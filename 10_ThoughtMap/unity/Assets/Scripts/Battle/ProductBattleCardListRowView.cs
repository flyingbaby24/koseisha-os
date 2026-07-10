using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleCardListRowView : MonoBehaviour
{
    private static readonly Vector2 DefaultRowSize = new Vector2(0f, 38f);

    [SerializeField] private Button button;
    [SerializeField] private Image backgroundImage;
    [SerializeField] private Image templateImage;
    [SerializeField] private TMP_Text slotText;
    [SerializeField] private TMP_Text cardNameText;
    [SerializeField] private TMP_Text attributeText;
    [SerializeField] private TMP_Text stateText;
    [SerializeField] private Color normalColor = new Color(0.02f, 0.11f, 0.16f, 0.9f);
    [SerializeField] private Color selectedColor = new Color(0.0f, 0.44f, 0.58f, 0.95f);
    [SerializeField] private Color markedColor = new Color(0.11f, 0.18f, 0.2f, 0.95f);
    [SerializeField] private Color textColor = new Color(0.88f, 0.96f, 1f, 1f);
    [SerializeField] private Color mutedTextColor = new Color(0.58f, 0.77f, 0.84f, 1f);

    private ThoughtMapBattleCardData card;
    private int index = -1;
    private UnityAction<ProductBattleCardListRowView> clickHandler;

    public ThoughtMapBattleCardData Card => card;
    public int Index => index;

    private void Awake()
    {
        EnsureBuilt();
        ConfigureRaycasts();
        WireButton();
    }

    public void Bind(
        ThoughtMapBattleCardData sourceCard,
        int sourceIndex,
        string slotLabel,
        bool selected,
        bool marked,
        string stateLabel,
        Sprite templateSprite
    )
    {
        EnsureBuilt();

        card = sourceCard;
        index = sourceIndex;

        SetText(slotText, slotLabel);
        SetText(cardNameText, Short(sourceCard == null ? "Empty" : sourceCard.cardName, 42));
        SetText(attributeText, sourceCard == null ? "-" : Short(sourceCard.primaryAttribute, 16));
        SetText(stateText, stateLabel);
        if (templateImage != null)
        {
            templateImage.sprite = templateSprite;
            templateImage.enabled = templateSprite != null;
        }

        if (backgroundImage != null)
        {
            backgroundImage.color = selected ? selectedColor : (marked ? markedColor : normalColor);
        }

        ConfigureRaycasts();
        WireButton();
    }

    public void SetClickHandler(UnityAction<ProductBattleCardListRowView> handler)
    {
        clickHandler = handler;
        WireButton();
    }

    public void NormalizeForList(float height)
    {
        RectTransform rect = GetComponent<RectTransform>();
        if (rect != null)
        {
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(1f, 1f);
            rect.pivot = new Vector2(0.5f, 1f);
            rect.sizeDelta = new Vector2(0f, height);
        }

        LayoutElement layout = GetComponent<LayoutElement>();
        if (layout == null)
        {
            layout = gameObject.AddComponent<LayoutElement>();
        }
        layout.minHeight = height;
        layout.preferredHeight = height;
        layout.flexibleWidth = 1f;
        layout.flexibleHeight = 0f;
    }

    private void HandleClicked()
    {
        clickHandler?.Invoke(this);
    }

    private void WireButton()
    {
        if (button == null)
        {
            button = GetComponent<Button>();
        }
        if (button == null)
        {
            button = gameObject.AddComponent<Button>();
        }
        button.targetGraphic = backgroundImage;
        button.onClick.RemoveListener(HandleClicked);
        button.onClick.AddListener(HandleClicked);
    }

    private void EnsureBuilt()
    {
        RectTransform rect = GetComponent<RectTransform>();
        if (rect == null)
        {
            rect = gameObject.AddComponent<RectTransform>();
        }
        NormalizeForList(DefaultRowSize.y);

        Image rootImage = GetComponent<Image>();
        if (rootImage == null)
        {
            rootImage = gameObject.AddComponent<Image>();
        }
        backgroundImage = rootImage;
        backgroundImage.color = normalColor;
        backgroundImage.raycastTarget = true;

        HorizontalLayoutGroup layout = GetComponent<HorizontalLayoutGroup>();
        if (layout == null)
        {
            layout = gameObject.AddComponent<HorizontalLayoutGroup>();
        }
        layout.padding = new RectOffset(8, 8, 4, 4);
        layout.spacing = 8f;
        layout.childAlignment = TextAnchor.MiddleLeft;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = false;
        layout.childForceExpandHeight = true;

        templateImage = templateImage == null ? CreateTemplateImage() : templateImage;
        slotText = slotText == null ? CreateText("SlotText", 52f, false) : slotText;
        cardNameText = cardNameText == null ? CreateText("CardNameText", 0f, true) : cardNameText;
        attributeText = attributeText == null ? CreateText("AttributeText", 94f, false) : attributeText;
        stateText = stateText == null ? CreateText("StateText", 64f, false) : stateText;

        ConfigureText(slotText, mutedTextColor, TextAlignmentOptions.MidlineLeft);
        ConfigureText(cardNameText, textColor, TextAlignmentOptions.MidlineLeft);
        ConfigureText(attributeText, mutedTextColor, TextAlignmentOptions.MidlineLeft);
        ConfigureText(stateText, mutedTextColor, TextAlignmentOptions.MidlineRight);
    }

    private TMP_Text CreateText(string objectName, float preferredWidth, bool flexible)
    {
        GameObject child = new GameObject(objectName, typeof(RectTransform));
        child.transform.SetParent(transform, false);

        TMP_Text text = child.AddComponent<TextMeshProUGUI>();
        LayoutElement layout = child.AddComponent<LayoutElement>();
        layout.minWidth = preferredWidth;
        layout.preferredWidth = preferredWidth;
        layout.flexibleWidth = flexible ? 1f : 0f;
        layout.flexibleHeight = 0f;
        return text;
    }

    private Image CreateTemplateImage()
    {
        GameObject child = new GameObject("TemplateImage", typeof(RectTransform));
        child.transform.SetParent(transform, false);

        Image image = child.AddComponent<Image>();
        image.preserveAspect = true;
        image.raycastTarget = false;

        LayoutElement layout = child.AddComponent<LayoutElement>();
        layout.minWidth = 30f;
        layout.preferredWidth = 30f;
        layout.minHeight = 30f;
        layout.preferredHeight = 30f;
        layout.flexibleWidth = 0f;
        layout.flexibleHeight = 0f;
        return image;
    }

    private void ConfigureText(TMP_Text text, Color color, TextAlignmentOptions alignment)
    {
        if (text == null)
        {
            return;
        }

        text.fontSize = 13f;
        text.color = color;
        text.alignment = alignment;
        text.enableWordWrapping = false;
        text.overflowMode = TextOverflowModes.Ellipsis;
        text.raycastTarget = false;
    }

    private void ConfigureRaycasts()
    {
        Graphic[] graphics = GetComponentsInChildren<Graphic>(true);
        foreach (Graphic graphic in graphics)
        {
            graphic.raycastTarget = graphic.gameObject == gameObject;
        }
        if (backgroundImage != null)
        {
            backgroundImage.raycastTarget = true;
        }
    }

    private void SetText(TMP_Text text, string value)
    {
        if (text != null)
        {
            text.text = value;
        }
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
