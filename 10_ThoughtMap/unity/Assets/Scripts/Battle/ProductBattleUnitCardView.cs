using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ProductBattleUnitCardView : MonoBehaviour
{
    [SerializeField] private Image frameImage;
    [SerializeField] private Image artImage;
    [SerializeField] private Image attributeIconImage;
    [SerializeField] private Slider hpSlider;
    [SerializeField] private TMP_Text unitIdText;
    [SerializeField] private TMP_Text cardNameText;
    [SerializeField] private TMP_Text hpText;
    [SerializeField] private TMP_Text attributeText;

    public void Bind(string unitId, ThoughtMapBattleCardData card, Sprite artSprite, Sprite attributeSprite, bool enemySide)
    {
        SetText(unitIdText, unitId);
        SetText(cardNameText, card == null ? "Empty" : card.cardName);
        SetText(hpText, card == null ? "HP -" : $"{card.MaxHp}/{card.MaxHp}");
        SetText(attributeText, card == null ? "-" : card.primaryAttribute);

        if (hpSlider != null)
        {
            hpSlider.minValue = 0;
            hpSlider.maxValue = card == null ? 1 : card.MaxHp;
            hpSlider.value = card == null ? 0 : card.MaxHp;
        }

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

        if (frameImage != null)
        {
            frameImage.color = enemySide
                ? new Color(0.42f, 0.06f, 0.07f, 0.95f)
                : new Color(0.02f, 0.20f, 0.36f, 0.95f);
        }
    }

    private void SetText(TMP_Text text, string value)
    {
        if (text != null)
        {
            text.text = value;
        }
    }
}
