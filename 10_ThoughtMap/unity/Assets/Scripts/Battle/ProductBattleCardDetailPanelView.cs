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
        Show(card, artSprite, attributeSprite, "");
    }

    public void Show(ThoughtMapBattleCardData card, Sprite artSprite, Sprite attributeSprite, string resolvedThoughtAttribute)
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
            DisableOverlappingPlaceholderImages();
            artImage.sprite = artSprite;
            artImage.enabled = true;
            artImage.preserveAspect = true;
            Color artColor = artImage.color;
            artColor.a = 1f;
            artImage.color = artColor;
            artImage.transform.SetAsLastSibling();
            Debug.Log(
                $"[ProductBattlePrep Art] Detail Panel ArtImage: card title='{card.cardName}' resolved thought attribute='{FormatThoughtAttribute(resolvedThoughtAttribute)}' candidate sprite='{SpriteName(artSprite)}' assigned sprite='{SpriteName(artImage.sprite)}'",
                this
            );
        }
        else
        {
            Debug.LogWarning($"[ProductBattlePrep Art] Detail Panel artImage is null card='{card.cardName}'", this);
        }
        if (attributeIconImage != null)
        {
            attributeIconImage.sprite = attributeSprite;
            attributeIconImage.enabled = attributeSprite != null;
            Debug.Log(
                $"[ProductBattlePrep Art] Detail Panel Attribute Image.sprite assigned={(attributeSprite == null ? "null" : attributeSprite.name)} card='{card.cardName}'",
                this
            );
        }
    }

    private void DisableOverlappingPlaceholderImages()
    {
        if (artImage == null)
        {
            return;
        }

        Image[] images = GetComponentsInChildren<Image>(true);
        foreach (Image image in images)
        {
            if (image == null || image == artImage)
            {
                continue;
            }

            string objectName = image.gameObject.name.ToLowerInvariant();
            if (objectName.Contains("placeholder"))
            {
                image.enabled = false;
            }
        }
    }

    private string SpriteName(Sprite sprite)
    {
        return sprite == null ? "null" : sprite.name;
    }

    private string FormatThoughtAttribute(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? "none" : value;
    }

    private void SetText(TMP_Text text, string value)
    {
        if (text != null)
        {
            text.text = value;
        }
    }
}
