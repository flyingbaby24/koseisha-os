using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleCardView : MonoBehaviour
{
    private static readonly Vector2 DefaultCardSize = new Vector2(176f, 272f);

    [Header("Images")]
    [SerializeField] private Image frameImage;
    [SerializeField] private Image artImage;
    [SerializeField] private Image attributeIconImage;
    [SerializeField] private Image selectionImage;

    [Header("Texts")]
    [SerializeField] private TMP_Text unitIdText;
    [SerializeField] private TMP_Text cardNameText;
    [SerializeField] private TMP_Text attributeText;
    [SerializeField] private TMP_Text hpText;
    [SerializeField] private TMP_Text atkText;
    [SerializeField] private TMP_Text defText;
    [SerializeField] private TMP_Text enText;
    [SerializeField] private TMP_Text skillText;
    [SerializeField] private TMP_Text rarityText;
    [SerializeField] private TMP_Text statusText;

    [Header("Interaction")]
    [SerializeField] private Button button;

    private ThoughtMapBattleCardData card;
    private int index = -1;
    private UnityAction<ProductBattleCardView> clickHandler;

    public ThoughtMapBattleCardData Card => card;
    public int Index => index;

    private void Awake()
    {
        NormalizeForGrid(DefaultCardSize);
        ConfigureRaycasts();
        if (button != null)
        {
            button.onClick.RemoveListener(HandleClicked);
            button.onClick.AddListener(HandleClicked);
        }
    }

    [ContextMenu("Auto Wire From Children")]
    public void AutoWireFromChildren()
    {
        TMP_Text[] texts = GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in texts)
        {
            string objectName = text.gameObject.name.ToLowerInvariant();
            if (objectName.Contains("unit") || objectName.Contains("id")) unitIdText = text;
            else if (objectName.Contains("name")) cardNameText = text;
            else if (objectName.Contains("attribute")) attributeText = text;
            else if (objectName.Contains("hp")) hpText = text;
            else if (objectName.Contains("atk") || objectName.Contains("attack")) atkText = text;
            else if (objectName.Contains("def") || objectName.Contains("defense")) defText = text;
            else if (objectName.Contains("en") || objectName.Contains("sp")) enText = text;
            else if (objectName.Contains("skill")) skillText = text;
            else if (objectName.Contains("rarity")) rarityText = text;
            else if (objectName.Contains("status")) statusText = text;
        }

        Image[] images = GetComponentsInChildren<Image>(true);
        foreach (Image image in images)
        {
            string objectName = image.gameObject.name.ToLowerInvariant();
            if (objectName.Contains("art")) artImage = image;
            else if (objectName.Contains("attribute") || objectName.Contains("icon")) attributeIconImage = image;
            else if (objectName.Contains("select") || objectName.Contains("glow")) selectionImage = image;
            else if (image.gameObject == gameObject || objectName.Contains("frame")) frameImage = image;
        }

        if (button == null)
        {
            button = GetComponentInChildren<Button>(true);
        }
    }

    public void Bind(
        ThoughtMapBattleCardData sourceCard,
        int sourceIndex,
        string unitId,
        bool selected,
        bool placed,
        Sprite artSprite,
        Sprite attributeSprite
    )
    {
        card = sourceCard;
        index = sourceIndex;

        SetText(unitIdText, unitId);
        SetText(cardNameText, Short(sourceCard == null ? "Empty" : sourceCard.cardName, 24));
        SetText(attributeText, sourceCard == null ? "-" : Short(sourceCard.primaryAttribute, 18));
        SetText(hpText, sourceCard == null ? "HP -" : $"HP {sourceCard.MaxHp}");
        SetText(atkText, sourceCard == null ? "ATK -" : $"ATK {Mathf.Max(sourceCard.statPhysicalAttack, sourceCard.statSkillAttack)}");
        SetText(defText, sourceCard == null ? "DEF -" : $"DEF {Mathf.Max(sourceCard.statPhysicalDefense, sourceCard.statSkillDefense)}");
        SetText(enText, sourceCard == null ? "EN -" : $"EN {sourceCard.MaxSp}");
        SetText(skillText, sourceCard == null ? "Skill -" : $"Skill {Mathf.Abs(sourceCard.skillSeed % 100):00}");
        SetText(rarityText, sourceCard == null ? "-" : $"R{1 + Mathf.Abs(sourceCard.raritySeed % 5)}");
        SetText(statusText, placed ? "Placed" : "Ready");

        if (artImage != null)
        {
            artImage.sprite = artSprite;
            artImage.enabled = artSprite != null;
        }

        if (attributeIconImage != null)
        {
            attributeIconImage.sprite = attributeSprite;
            attributeIconImage.enabled = attributeSprite != null;
        }

        if (selectionImage != null)
        {
            selectionImage.gameObject.SetActive(selected);
        }

        ConfigureRaycasts();
    }

    public void NormalizeForGrid(Vector2 size)
    {
        RectTransform rect = GetComponent<RectTransform>();
        if (rect != null)
        {
            rect.sizeDelta = size;
        }

        Graphic rootGraphic = GetComponent<Graphic>();
        if (rootGraphic == null)
        {
            Image rootImage = gameObject.AddComponent<Image>();
            rootImage.color = new Color(1f, 1f, 1f, 0f);
            rootGraphic = rootImage;
        }
        rootGraphic.raycastTarget = true;

        RectMask2D clipMask = GetComponent<RectMask2D>();
        if (clipMask == null)
        {
            gameObject.AddComponent<RectMask2D>();
        }

        LayoutElement layout = GetComponent<LayoutElement>();
        if (layout == null)
        {
            layout = gameObject.AddComponent<LayoutElement>();
        }
        layout.minWidth = size.x;
        layout.minHeight = size.y;
        layout.preferredWidth = size.x;
        layout.preferredHeight = size.y;
        layout.flexibleWidth = 0f;
        layout.flexibleHeight = 0f;

        if (button == null)
        {
            button = GetComponent<Button>();
        }
        if (button == null)
        {
            button = gameObject.AddComponent<Button>();
        }
        button.targetGraphic = rootGraphic;
    }

    public void SetClickHandler(UnityAction<ProductBattleCardView> handler)
    {
        clickHandler = handler;
        if (button == null)
        {
            button = GetComponent<Button>();
        }
        if (button != null)
        {
            button.onClick.RemoveListener(HandleClicked);
            button.onClick.AddListener(HandleClicked);
        }
    }

    private void HandleClicked()
    {
        clickHandler?.Invoke(this);
    }

    private void ConfigureRaycasts()
    {
        Graphic[] graphics = GetComponentsInChildren<Graphic>(true);
        foreach (Graphic graphic in graphics)
        {
            graphic.raycastTarget = graphic.gameObject == gameObject;
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
