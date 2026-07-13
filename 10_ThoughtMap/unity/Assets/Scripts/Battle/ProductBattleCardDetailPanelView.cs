using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ProductBattleCardDetailPanelView : MonoBehaviour
{
    private const int AbilityRowsPerColumn = 5;

    [SerializeField] private TMP_FontAsset overrideFontAsset;
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
    [SerializeField] private Transform assignedSkillsRoot;
    [SerializeField] private TMP_Text assignedSkillsText;

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
        SetAssignedSkills(null);
        if (artImage != null) artImage.enabled = false;
        if (attributeIconImage != null) attributeIconImage.enabled = false;
        ClearAbilityBars();
        ApplyFontToGeneratedTexts();
    }

    public void SetFontAsset(TMP_FontAsset fontAsset)
    {
        overrideFontAsset = fontAsset;
        ApplyFontToGeneratedTexts();
    }

    public void ApplyFontToGeneratedTexts()
    {
        if (overrideFontAsset == null)
        {
            return;
        }

        TMP_Text[] texts = GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in texts)
        {
            if (text != null)
            {
                text.font = overrideFontAsset;
            }
        }
    }

    public void Show(ThoughtMapBattleCardData card, Sprite artSprite, Sprite attributeSprite)
    {
        Show(card, artSprite, attributeSprite, "");
    }

    public void Show(ThoughtMapBattleCardData card, Sprite artSprite, Sprite attributeSprite, string resolvedThoughtAttribute)
    {
        Show(card, artSprite, attributeSprite, resolvedThoughtAttribute, null);
    }

    public void Show(
        ThoughtMapBattleCardData card,
        Sprite artSprite,
        Sprite attributeSprite,
        string resolvedThoughtAttribute,
        System.Collections.Generic.IReadOnlyList<GeneratedSkillDto> assignedSkills)
    {
        Show(card, artSprite, attributeSprite, resolvedThoughtAttribute, assignedSkills, null);
    }

    public void Show(
        ThoughtMapBattleCardData card,
        Sprite artSprite,
        Sprite attributeSprite,
        string resolvedThoughtAttribute,
        System.Collections.Generic.IReadOnlyList<GeneratedSkillDto> assignedSkills,
        ThoughtMapResonanceResult resonanceResult)
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
            attributeIconImage.sprite = null;
            attributeIconImage.enabled = false;
            Debug.Log(
                $"[ProductBattlePrep Art] Detail Panel AttributeIconImage hidden to keep ability bars readable. candidate sprite={(attributeSprite == null ? "null" : attributeSprite.name)} card='{card.cardName}'",
                this
            );
        }

        RenderAbilityBars(card, resonanceResult);
        SetAssignedSkills(assignedSkills);
        ApplyFontToGeneratedTexts();
    }

    public void SetAssignedSkills(System.Collections.Generic.IReadOnlyList<GeneratedSkillDto> assignedSkills)
    {
        EnsureAssignedSkillsArea();
        if (assignedSkillsText == null)
        {
            return;
        }

        System.Text.StringBuilder builder = new System.Text.StringBuilder();
        GeneratedSkillDto skill = assignedSkills != null && assignedSkills.Count > 0 ? assignedSkills[0] : null;
        if (skill == null)
        {
            builder.AppendLine("Assigned Skill: None");
        }
        else
        {
            builder.AppendLine($"Assigned Skill: {skill.DisplayName}");
            builder.AppendLine($"Trigger: {skill.trigger} / Effect: {FirstEffectType(skill)} / CT: {skill.cooldown}");
        }

        assignedSkillsText.text = builder.ToString();
    }

    private string FirstEffectType(GeneratedSkillDto skill)
    {
        if (skill == null || skill.effects == null || skill.effects.Count == 0 || skill.effects[0] == null)
        {
            return "-";
        }

        return string.IsNullOrWhiteSpace(skill.effects[0].effect_type) ? "-" : skill.effects[0].effect_type;
    }

    [ContextMenu("Rebuild Ability Bars")]
    public void RebuildAbilityBars()
    {
        EnsureAbilityBars();
        ClearAbilityBars();
    }

    private void RenderAbilityBars(ThoughtMapBattleCardData card)
    {
        RenderAbilityBars(card, null);
    }

    private void RenderAbilityBars(ThoughtMapBattleCardData card, ThoughtMapResonanceResult resonanceResult)
    {
        EnsureAbilityBars();
        if (abilityBars == null || abilityBars.Length == 0)
        {
            return;
        }

        ThoughtMapBattleAbilityValue[] values = resonanceResult == null
            ? ThoughtMapBattleAbilityStats.BuildValues(card)
            : ThoughtMapBattleAbilityStats.BuildCombatValues(card, resonanceResult.totalModifier, true);
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
                GameObject root = new GameObject("AbilityBarRoot", typeof(RectTransform), typeof(HorizontalLayoutGroup));
                root.transform.SetParent(transform, false);
                RectTransform rootRect = root.GetComponent<RectTransform>();
                rootRect.anchorMin = new Vector2(0.42f, 0.28f);
                rootRect.anchorMax = new Vector2(0.99f, 0.76f);
                rootRect.offsetMin = Vector2.zero;
                rootRect.offsetMax = Vector2.zero;
                existing = root.transform;
            }

            abilityBarRoot = existing;
        }

        ConfigureAbilityRoot(abilityBarRoot);
        Transform leftColumn = GetOrCreateAbilityColumn("LeftColumn");
        Transform rightColumn = GetOrCreateAbilityColumn("RightColumn");

        int expectedCount = ThoughtMapBattleAbilityStats.DisplayOrder.Length;
        ProductBattleAbilityBarView[] existingBars = abilityBarRoot.GetComponentsInChildren<ProductBattleAbilityBarView>(true);
        if (existingBars.Length < expectedCount)
        {
            for (int i = existingBars.Length; i < expectedCount; i++)
            {
                ProductBattleAbilityBarView bar = CreateAbilityBar(i, GetColumnForIndex(i, leftColumn, rightColumn));
                bar.EnsureVisuals();
            }
            existingBars = abilityBarRoot.GetComponentsInChildren<ProductBattleAbilityBarView>(true);
        }

        abilityBars = new ProductBattleAbilityBarView[expectedCount];
        for (int i = 0; i < expectedCount; i++)
        {
            abilityBars[i] = existingBars[i];
            abilityBars[i].gameObject.name = $"AbilityBar_{i:00}_{ThoughtMapBattleAbilityStats.DisplayOrder[i].shortName}";
            abilityBars[i].transform.SetParent(GetColumnForIndex(i, leftColumn, rightColumn), false);
            abilityBars[i].transform.SetSiblingIndex(i % AbilityRowsPerColumn);
            abilityBars[i].EnsureVisuals();
        }
    }

    [ContextMenu("Ensure Assigned Skills Area")]
    public void EnsureAssignedSkillsArea()
    {
        if (assignedSkillsRoot == null)
        {
            Transform existing = transform.Find("AssignedSkillsRoot");
            if (existing == null)
            {
                GameObject root = new GameObject("AssignedSkillsRoot", typeof(RectTransform), typeof(Image));
                root.transform.SetParent(transform, false);
                RectTransform rootRect = root.GetComponent<RectTransform>();
                rootRect.anchorMin = new Vector2(0.61f, 0.02f);
                rootRect.anchorMax = new Vector2(0.98f, 0.26f);
                rootRect.offsetMin = Vector2.zero;
                rootRect.offsetMax = Vector2.zero;
                Image image = root.GetComponent<Image>();
                image.color = new Color(0f, 0f, 0f, 0.18f);
                image.raycastTarget = false;
                existing = root.transform;
            }
            assignedSkillsRoot = existing;
        }

        RectTransform assignedRootRect = assignedSkillsRoot as RectTransform;
        if (assignedRootRect != null)
        {
            assignedRootRect.anchorMin = new Vector2(0.61f, 0.02f);
            assignedRootRect.anchorMax = new Vector2(0.98f, 0.26f);
            assignedRootRect.offsetMin = Vector2.zero;
            assignedRootRect.offsetMax = Vector2.zero;
        }

        if (assignedSkillsText == null)
        {
            Transform existingText = assignedSkillsRoot.Find("AssignedSkillsText");
            if (existingText == null)
            {
                GameObject textObject = new GameObject("AssignedSkillsText", typeof(RectTransform));
                textObject.transform.SetParent(assignedSkillsRoot, false);
                RectTransform textRect = textObject.GetComponent<RectTransform>();
                textRect.anchorMin = new Vector2(0.02f, 0.02f);
                textRect.anchorMax = new Vector2(0.98f, 0.98f);
                textRect.offsetMin = Vector2.zero;
                textRect.offsetMax = Vector2.zero;
                assignedSkillsText = textObject.AddComponent<TextMeshProUGUI>();
            }
            else
            {
                assignedSkillsText = existingText.GetComponent<TMP_Text>();
            }
        }

        if (assignedSkillsText != null)
        {
            if (overrideFontAsset != null)
            {
                assignedSkillsText.font = overrideFontAsset;
            }
            assignedSkillsText.fontSize = 11f;
            assignedSkillsText.color = new Color(0.86f, 0.96f, 1f, 1f);
            assignedSkillsText.alignment = TextAlignmentOptions.TopLeft;
            assignedSkillsText.enableWordWrapping = true;
            assignedSkillsText.overflowMode = TextOverflowModes.Overflow;
            assignedSkillsText.raycastTarget = false;
        }
    }

    private ProductBattleAbilityBarView CreateAbilityBar(int index, Transform parent)
    {
        ProductBattleAbilityBarView bar = null;
        if (abilityBarPrefab != null)
        {
            bar = Instantiate(abilityBarPrefab, parent);
        }
        else
        {
            GameObject row = new GameObject($"AbilityBar_{index:00}", typeof(RectTransform), typeof(LayoutElement), typeof(ProductBattleAbilityBarView));
            row.transform.SetParent(parent, false);
            bar = row.GetComponent<ProductBattleAbilityBarView>();
        }

        RectTransform rect = bar.GetComponent<RectTransform>();
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(1f, 1f);
        rect.pivot = new Vector2(0.5f, 1f);
        rect.sizeDelta = new Vector2(0f, 26f);

        LayoutElement layout = bar.GetComponent<LayoutElement>();
        if (layout == null)
        {
            layout = bar.gameObject.AddComponent<LayoutElement>();
        }
        layout.minHeight = 26f;
        layout.preferredHeight = 26f;
        layout.flexibleHeight = 0f;
        return bar;
    }

    private void ConfigureAbilityRoot(Transform root)
    {
        if (root == null)
        {
            return;
        }

        RectTransform rect = root as RectTransform;
        if (rect != null)
        {
            rect.anchorMin = new Vector2(0.42f, 0.28f);
            rect.anchorMax = new Vector2(0.99f, 0.76f);
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;
        }

        RemoveLayoutGroupsExcept<HorizontalLayoutGroup>(root.gameObject);
        HorizontalLayoutGroup layout = root.GetComponent<HorizontalLayoutGroup>();
        if (layout == null)
        {
            layout = root.gameObject.AddComponent<HorizontalLayoutGroup>();
        }

        layout.padding = new RectOffset(0, 0, 0, 0);
        layout.spacing = 10f;
        layout.childAlignment = TextAnchor.MiddleCenter;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = true;
    }

    private Transform GetOrCreateAbilityColumn(string columnName)
    {
        Transform existing = abilityBarRoot == null ? null : abilityBarRoot.Find(columnName);
        if (existing != null)
        {
            ConfigureAbilityColumn(existing);
            return existing;
        }

        GameObject column = new GameObject(columnName, typeof(RectTransform), typeof(LayoutElement), typeof(VerticalLayoutGroup));
        column.transform.SetParent(abilityBarRoot, false);
        ConfigureAbilityColumn(column.transform);
        return column.transform;
    }

    private void ConfigureAbilityColumn(Transform column)
    {
        if (column == null)
        {
            return;
        }

        RectTransform rect = column as RectTransform;
        if (rect != null)
        {
            rect.anchorMin = new Vector2(0f, 0f);
            rect.anchorMax = new Vector2(1f, 1f);
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;
        }

        LayoutElement layoutElement = column.GetComponent<LayoutElement>();
        if (layoutElement == null)
        {
            layoutElement = column.gameObject.AddComponent<LayoutElement>();
        }
        layoutElement.flexibleWidth = 1f;
        layoutElement.flexibleHeight = 1f;

        RemoveLayoutGroupsExcept<VerticalLayoutGroup>(column.gameObject);
        VerticalLayoutGroup layout = column.GetComponent<VerticalLayoutGroup>();
        if (layout == null)
        {
            layout = column.gameObject.AddComponent<VerticalLayoutGroup>();
        }
        layout.padding = new RectOffset(0, 0, 0, 0);
        layout.spacing = 4f;
        layout.childAlignment = TextAnchor.UpperCenter;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;
    }

    private Transform GetColumnForIndex(int index, Transform leftColumn, Transform rightColumn)
    {
        return index < AbilityRowsPerColumn ? leftColumn : rightColumn;
    }

    private void RemoveLayoutGroupsExcept<TKeep>(GameObject target) where TKeep : LayoutGroup
    {
        if (target == null)
        {
            return;
        }

        LayoutGroup[] groups = target.GetComponents<LayoutGroup>();
        foreach (LayoutGroup group in groups)
        {
            if (group is TKeep)
            {
                continue;
            }

            if (Application.isPlaying)
            {
                Destroy(group);
            }
            else
            {
                DestroyImmediate(group);
            }
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
