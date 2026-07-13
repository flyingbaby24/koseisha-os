using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleGridCellView : MonoBehaviour
{
    [Header("Images")]
    [SerializeField] private Image backgroundImage;
    [SerializeField] private Image cardFrameImage;
    [SerializeField] private Image artImage;
    [SerializeField] private Image attributeIconImage;
    [SerializeField] private Image placedGlowImage;

    [Header("Texts")]
    [SerializeField] private TMP_Text coordinateText;
    [SerializeField] private TMP_Text unitIdText;
    [SerializeField] private TMP_Text cardNameText;
    [SerializeField] private TMP_Text attributeText;
    [SerializeField] private TMP_Text resonanceText;

    [Header("Interaction")]
    [SerializeField] private Button button;

    private int x;
    private int y;
    private ThoughtMapBattleCardData card;
    private UnityAction<ProductBattleGridCellView> clickHandler;

    public int X => x;
    public int Y => y;
    public ThoughtMapBattleCardData Card => card;

    private void Awake()
    {
        EnsureArtImage();
        EnsureInteractionEnabled();
    }

    [ContextMenu("Auto Wire From Children")]
    public void AutoWireFromChildren()
    {
        TMP_Text[] texts = GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in texts)
        {
            string objectName = text.gameObject.name.ToLowerInvariant();
            if (objectName.Contains("coordinate") || objectName.Contains("position")) coordinateText = text;
            else if (objectName.Contains("unit") || objectName.Contains("id")) unitIdText = text;
            else if (objectName.Contains("name")) cardNameText = text;
            else if (objectName.Contains("attribute")) attributeText = text;
            else if (objectName.Contains("resonance")) resonanceText = text;
        }

        Image[] images = GetComponentsInChildren<Image>(true);
        foreach (Image image in images)
        {
            string objectName = image.gameObject.name.ToLowerInvariant();
            if (objectName.Contains("art")) artImage = image;
            else if (objectName.Contains("attribute") || objectName.Contains("icon")) attributeIconImage = image;
            else if (objectName.Contains("card")) cardFrameImage = image;
            else if (objectName.Contains("glow") || objectName.Contains("placed")) placedGlowImage = image;
            else if (image.gameObject == gameObject || objectName.Contains("background")) backgroundImage = image;
        }

        if (button == null)
        {
            button = GetComponentInChildren<Button>(true);
        }

        EnsureArtImage();
    }

    public void EnsureArtImage()
    {
        if (artImage == null)
        {
            Transform existing = transform.Find("ArtImage");
            if (existing != null)
            {
                artImage = existing.GetComponent<Image>();
            }
        }

        if (artImage == null)
        {
            GameObject artObject = new GameObject("ArtImage", typeof(RectTransform), typeof(Image));
            artObject.transform.SetParent(transform, false);
            artImage = artObject.GetComponent<Image>();
        }

        RectTransform rect = artImage.transform as RectTransform;
        if (rect != null)
        {
            rect.anchorMin = new Vector2(0.08f, 0.18f);
            rect.anchorMax = new Vector2(0.92f, 0.86f);
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;
        }

        artImage.preserveAspect = true;
        artImage.raycastTarget = false;
        artImage.color = Color.white;
        artImage.transform.SetAsFirstSibling();
    }

    public void BindEmpty(int gridX, int gridY, bool available)
    {
        x = gridX;
        y = gridY;
        card = null;
        EnsureArtImage();
        EnsureInteractionEnabled();
        SetText(coordinateText, $"{x + 1},{y + 1}");
        SetText(unitIdText, "");
        SetText(cardNameText, available ? "Deploy" : "");
        SetText(attributeText, "");
        SetResonanceModifier(0f);
        if (placedGlowImage != null)
        {
            placedGlowImage.gameObject.SetActive(false);
        }
        if (artImage != null)
        {
            artImage.enabled = false;
        }
        if (attributeIconImage != null)
        {
            attributeIconImage.enabled = false;
        }
    }

    public void BindCard(int gridX, int gridY, ThoughtMapBattleCardData sourceCard, string unitId)
    {
        BindCard(gridX, gridY, sourceCard, unitId, null, null);
    }

    public void BindCard(int gridX, int gridY, ThoughtMapBattleCardData sourceCard, string unitId, Sprite artSprite, Sprite attributeSprite)
    {
        x = gridX;
        y = gridY;
        card = sourceCard;
        EnsureArtImage();
        EnsureInteractionEnabled();
        SetText(coordinateText, $"{x + 1},{y + 1}");
        SetText(unitIdText, unitId);
        SetText(cardNameText, Short(sourceCard == null ? "Empty" : sourceCard.cardName, 18));
        SetText(attributeText, sourceCard == null ? "-" : Short(sourceCard.primaryAttribute, 14));
        if (placedGlowImage != null)
        {
            placedGlowImage.gameObject.SetActive(true);
        }
        if (artImage != null)
        {
            artImage.sprite = artSprite;
            artImage.enabled = artSprite != null;
            Debug.Log(
                $"[ProductBattlePrep Art] Grid Cell Image.sprite assigned={(artSprite == null ? "null" : artSprite.name)} cell=({x + 1},{y + 1}) card='{(sourceCard == null ? "null" : sourceCard.cardName)}'",
                this
            );
        }
        else
        {
            Debug.LogWarning(
                $"[ProductBattlePrep Art] Grid Cell artImage is null cell=({x + 1},{y + 1}) card='{(sourceCard == null ? "null" : sourceCard.cardName)}'",
                this
            );
        }
        if (attributeIconImage != null)
        {
            attributeIconImage.sprite = attributeSprite;
            attributeIconImage.enabled = attributeSprite != null;
            Debug.Log(
                $"[ProductBattlePrep Art] Grid Cell Attribute Image.sprite assigned={(attributeSprite == null ? "null" : attributeSprite.name)} cell=({x + 1},{y + 1}) card='{(sourceCard == null ? "null" : sourceCard.cardName)}'",
                this
            );
        }
    }

    public void SetResonanceModifier(float modifier)
    {
        EnsureResonanceText();
        if (resonanceText == null)
        {
            return;
        }

        if (Mathf.Abs(modifier) < 0.0001f)
        {
            resonanceText.gameObject.SetActive(false);
            resonanceText.text = "";
            return;
        }

        float percent = modifier * 100f;
        resonanceText.gameObject.SetActive(true);
        resonanceText.text = percent >= 0f ? $"+{percent:0}%" : $"{percent:0}%";
    }

    public void SetClickHandler(UnityAction<ProductBattleGridCellView> handler)
    {
        clickHandler = handler;
        EnsureInteractionEnabled();
    }

    private void EnsureInteractionEnabled()
    {
        CanvasGroup canvasGroup = GetComponent<CanvasGroup>();
        if (canvasGroup != null)
        {
            canvasGroup.alpha = 1f;
            canvasGroup.interactable = true;
            canvasGroup.blocksRaycasts = true;
        }

        if (backgroundImage == null)
        {
            backgroundImage = GetComponent<Image>();
        }
        if (backgroundImage != null)
        {
            backgroundImage.raycastTarget = true;
        }

        if (button == null)
        {
            button = GetComponent<Button>();
        }
        if (button == null)
        {
            button = gameObject.AddComponent<Button>();
        }
        button.interactable = true;
        button.onClick.RemoveListener(HandleClicked);
        button.onClick.AddListener(HandleClicked);
    }

    private void EnsureResonanceText()
    {
        if (resonanceText == null)
        {
            Transform existing = transform.Find("ResonanceText");
            if (existing != null)
            {
                resonanceText = existing.GetComponent<TMP_Text>();
            }
        }

        if (resonanceText == null)
        {
            GameObject textObject = new GameObject("ResonanceText", typeof(RectTransform), typeof(TextMeshProUGUI));
            textObject.transform.SetParent(transform, false);
            resonanceText = textObject.GetComponent<TMP_Text>();
        }

        RectTransform rect = resonanceText.transform as RectTransform;
        if (rect != null)
        {
            rect.anchorMin = new Vector2(0.04f, 0.02f);
            rect.anchorMax = new Vector2(0.96f, 0.18f);
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;
        }

        resonanceText.fontSize = 10f;
        resonanceText.color = new Color(0.5f, 1f, 0.85f, 1f);
        resonanceText.alignment = TextAlignmentOptions.Center;
        resonanceText.enableWordWrapping = false;
        resonanceText.overflowMode = TextOverflowModes.Overflow;
        resonanceText.raycastTarget = false;
        Shadow shadow = resonanceText.GetComponent<Shadow>();
        if (shadow == null)
        {
            shadow = resonanceText.gameObject.AddComponent<Shadow>();
        }
        shadow.effectColor = new Color(0f, 0f, 0f, 0.75f);
        shadow.effectDistance = new Vector2(1f, -1f);
        resonanceText.transform.SetAsLastSibling();
    }

    private void HandleClicked()
    {
        clickHandler?.Invoke(this);
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
