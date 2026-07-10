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
    [SerializeField] private Transform abilityBarRoot;
    [SerializeField] private ProductBattleAbilityBarView abilityBarPrefab;
    [SerializeField] private ProductBattleAbilityBarView[] abilityBars;

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
        ClearAbilityBars();
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
        SetText(attributeText, $"Battle {card.primaryAttribute} / {card.secondaryAttribute}\nThought {FormatThoughtAttribute(resolvedThoughtAttribute)}");
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
            artImage.color = Color.white;
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

        RenderAbilityBars(card);
    }

    [ContextMenu("Rebuild Ability Bars")]
    public void RebuildAbilityBars()
    {
        EnsureAbilityBars();
        ClearAbilityBars();
    }

    private void RenderAbilityBars(ThoughtMapBattleCardData card)
    {
        EnsureAbilityBars();
        if (abilityBars == null || abilityBars.Length == 0)
        {
            return;
        }

        ThoughtMapBattleAbilityValue[] values = ThoughtMapBattleAbilityStats.BuildValues(card);
        int count = Mathf.Min(abilityBars.Length, values.Length);
        for (int i = 0; i < count; i++)
        {
            if (abilityBars[i] != null)
            {
                abilityBars[i].Bind(values[i]);
            }
        }
    }

    private void ClearAbilityBars()
    {
        EnsureAbilityBars();
        if (abilityBars == null)
        {
            return;
        }

        foreach (ProductBattleAbilityBarView bar in abilityBars)
        {
            if (bar != null)
            {
                bar.Clear();
            }
        }
    }

    private void EnsureAbilityBars()
    {
        if (abilityBarRoot == null)
        {
            Transform existing = transform.Find("AbilityBarRoot");
            if (existing == null)
            {
                GameObject root = new GameObject("AbilityBarRoot", typeof(RectTransform), typeof(VerticalLayoutGroup));
                root.transform.SetParent(transform, false);
                RectTransform rootRect = root.GetComponent<RectTransform>();
                rootRect.anchorMin = new Vector2(0.61f, 0.10f);
                rootRect.anchorMax = new Vector2(0.98f, 0.76f);
                rootRect.offsetMin = Vector2.zero;
                rootRect.offsetMax = Vector2.zero;

                VerticalLayoutGroup layout = root.GetComponent<VerticalLayoutGroup>();
                layout.padding = new RectOffset(0, 0, 0, 0);
                layout.spacing = 3f;
                layout.childControlWidth = true;
                layout.childControlHeight = true;
                layout.childForceExpandWidth = true;
                layout.childForceExpandHeight = false;
                existing = root.transform;
            }

            abilityBarRoot = existing;
        }

        int expectedCount = ThoughtMapBattleAbilityStats.DisplayOrder.Length;
        ProductBattleAbilityBarView[] existingBars = abilityBarRoot.GetComponentsInChildren<ProductBattleAbilityBarView>(true);
        if (existingBars.Length < expectedCount)
        {
            for (int i = existingBars.Length; i < expectedCount; i++)
            {
                ProductBattleAbilityBarView bar = CreateAbilityBar(i);
                bar.EnsureVisuals();
            }
            existingBars = abilityBarRoot.GetComponentsInChildren<ProductBattleAbilityBarView>(true);
        }

        abilityBars = new ProductBattleAbilityBarView[expectedCount];
        for (int i = 0; i < expectedCount; i++)
        {
            abilityBars[i] = existingBars[i];
            abilityBars[i].gameObject.name = $"AbilityBar_{i:00}_{ThoughtMapBattleAbilityStats.DisplayOrder[i].shortName}";
            abilityBars[i].EnsureVisuals();
        }
    }

    private ProductBattleAbilityBarView CreateAbilityBar(int index)
    {
        ProductBattleAbilityBarView bar = null;
        if (abilityBarPrefab != null)
        {
            bar = Instantiate(abilityBarPrefab, abilityBarRoot);
        }
        else
        {
            GameObject row = new GameObject($"AbilityBar_{index:00}", typeof(RectTransform), typeof(LayoutElement), typeof(ProductBattleAbilityBarView));
            row.transform.SetParent(abilityBarRoot, false);
            bar = row.GetComponent<ProductBattleAbilityBarView>();
        }

        RectTransform rect = bar.GetComponent<RectTransform>();
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(1f, 1f);
        rect.pivot = new Vector2(0.5f, 1f);
        rect.sizeDelta = new Vector2(0f, 18f);

        LayoutElement layout = bar.GetComponent<LayoutElement>();
        if (layout == null)
        {
            layout = bar.gameObject.AddComponent<LayoutElement>();
        }
        layout.minHeight = 18f;
        layout.preferredHeight = 18f;
        layout.flexibleHeight = 0f;
        return bar;
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
