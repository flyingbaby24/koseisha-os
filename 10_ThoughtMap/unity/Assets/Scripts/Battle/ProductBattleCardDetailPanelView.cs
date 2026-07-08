using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ProductBattleCardDetailPanelView : MonoBehaviour
{
    [SerializeField] private Image artImage;
    [SerializeField] private Image attributeIconImage;
    [SerializeField] private TMP_Text titleText;
    [SerializeField] private TMP_Text descriptionText;
    [SerializeField] private TMP_Text attributeText;
    [SerializeField] private TMP_Text hpText;
    [SerializeField] private TMP_Text atkText;
    [SerializeField] private TMP_Text defenseText;
    [SerializeField] private TMP_Text enText;
    [SerializeField] private TMP_Text skillText;
    [SerializeField] private TMP_Text rarityText;

    public void Clear()
    {
        SetText(titleText, "Select a Card");
        SetText(descriptionText, "Choose a card from the list to inspect its Thought parameters.");
        SetText(attributeText, "");
        SetText(hpText, "");
        SetText(atkText, "");
        SetText(defenseText, "");
        SetText(enText, "");
        SetText(skillText, "");
        SetText(rarityText, "");
        if (artImage != null) artImage.enabled = false;
        if (attributeIconImage != null) attributeIconImage.enabled = false;
    }

    public void Show(ThoughtMapBattleCardData card, Sprite artSprite, Sprite attributeSprite)
    {
        if (card == null)
        {
            Clear();
            return;
        }

        SetText(titleText, card.cardName);
        SetText(descriptionText, string.IsNullOrWhiteSpace(card.sourceTitle) ? card.docId : card.sourceTitle);
        SetText(attributeText, $"{card.primaryAttribute} / {card.secondaryAttribute}");
        SetText(hpText, $"HP {card.MaxHp}");
        SetText(atkText, $"ATK {Mathf.Max(card.statPhysicalAttack, card.statSkillAttack)}");
        SetText(defenseText, $"DEF {Mathf.Max(card.statPhysicalDefense, card.statSkillDefense)}");
        SetText(enText, $"EN {card.MaxSp}");
        SetText(skillText, $"Skill Seed {card.skillSeed}");
        SetText(rarityText, $"R{1 + Mathf.Abs(card.raritySeed % 5)}");

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
    }

    private void SetText(TMP_Text text, string value)
    {
        if (text != null)
        {
            text.text = value;
        }
    }
}
