using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleGeneratedSkillRowView : MonoBehaviour
{
    [SerializeField] private TMP_Text nameText;
    [SerializeField] private TMP_Text metaText;
    [SerializeField] private TMP_Text effectText;
    [SerializeField] private TMP_Text stateText;
    [SerializeField] private Button selectButton;
    [SerializeField] private Button assignButton;
    [SerializeField] private Button removeButton;
    [SerializeField] private Image backgroundImage;

    private GeneratedSkillDto skill;
    private UnityAction<GeneratedSkillDto> onSelected;
    private UnityAction<GeneratedSkillDto> onAssign;
    private UnityAction<GeneratedSkillDto> onRemove;

    public GeneratedSkillDto Skill => skill;

    public void Bind(
        GeneratedSkillDto sourceSkill,
        bool selected,
        bool assigned,
        bool matchingDoc,
        UnityAction<GeneratedSkillDto> selectedHandler,
        UnityAction<GeneratedSkillDto> assignHandler,
        UnityAction<GeneratedSkillDto> removeHandler)
    {
        EnsureBuilt();
        skill = sourceSkill;
        onSelected = selectedHandler;
        onAssign = assignHandler;
        onRemove = removeHandler;

        SetText(nameText, sourceSkill == null ? "No generated skill" : sourceSkill.DisplayName);
        SetText(metaText, sourceSkill == null ? "" : $"Trigger: {sourceSkill.trigger}  {GeneratedSkillLibrary.CostSummary(sourceSkill)}  Cooldown: {sourceSkill.cooldown}");
        SetText(effectText, sourceSkill == null ? "" : GeneratedSkillLibrary.EffectSummary(sourceSkill));
        SetText(stateText, assigned ? "Assigned" : (matchingDoc ? "Matched" : ""));

        if (backgroundImage != null)
        {
            backgroundImage.color = selected
                ? new Color(0.0f, 0.42f, 0.58f, 0.94f)
                : matchingDoc
                    ? new Color(0.08f, 0.20f, 0.18f, 0.90f)
                    : new Color(0.02f, 0.10f, 0.14f, 0.88f);
        }

        WireButtons();
    }

    private void HandleSelect()
    {
        onSelected?.Invoke(skill);
    }

    private void HandleAssign()
    {
        onAssign?.Invoke(skill);
    }

    private void HandleRemove()
    {
        onRemove?.Invoke(skill);
    }

    private void EnsureBuilt()
    {
        RectTransform rect = GetComponent<RectTransform>();
        if (rect == null) rect = gameObject.AddComponent<RectTransform>();
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(1f, 1f);
        rect.pivot = new Vector2(0.5f, 1f);
        rect.sizeDelta = new Vector2(0f, 92f);

        LayoutElement layoutElement = GetComponent<LayoutElement>();
        if (layoutElement == null) layoutElement = gameObject.AddComponent<LayoutElement>();
        layoutElement.minHeight = 92f;
        layoutElement.preferredHeight = 92f;
        layoutElement.flexibleWidth = 1f;

        backgroundImage = backgroundImage == null ? GetComponent<Image>() : backgroundImage;
        if (backgroundImage == null) backgroundImage = gameObject.AddComponent<Image>();
        backgroundImage.raycastTarget = true;

        selectButton = selectButton == null ? GetComponent<Button>() : selectButton;
        if (selectButton == null) selectButton = gameObject.AddComponent<Button>();
        selectButton.targetGraphic = backgroundImage;

        nameText = nameText == null ? CreateText("NameText", new Vector2(0.03f, 0.68f), new Vector2(0.66f, 0.96f), 14f, TextAlignmentOptions.Left) : nameText;
        metaText = metaText == null ? CreateText("MetaText", new Vector2(0.03f, 0.42f), new Vector2(0.74f, 0.68f), 11f, TextAlignmentOptions.Left) : metaText;
        effectText = effectText == null ? CreateText("EffectText", new Vector2(0.03f, 0.08f), new Vector2(0.74f, 0.42f), 11f, TextAlignmentOptions.Left) : effectText;
        stateText = stateText == null ? CreateText("StateText", new Vector2(0.66f, 0.70f), new Vector2(0.97f, 0.95f), 11f, TextAlignmentOptions.Right) : stateText;
        assignButton = assignButton == null ? CreateButton("AssignButton", "Assign", new Vector2(0.75f, 0.12f), new Vector2(0.86f, 0.42f)) : assignButton;
        removeButton = removeButton == null ? CreateButton("RemoveButton", "Remove", new Vector2(0.87f, 0.12f), new Vector2(0.98f, 0.42f)) : removeButton;
    }

    private TMP_Text CreateText(string objectName, Vector2 min, Vector2 max, float fontSize, TextAlignmentOptions alignment)
    {
        GameObject child = new GameObject(objectName, typeof(RectTransform));
        child.transform.SetParent(transform, false);
        RectTransform rect = child.GetComponent<RectTransform>();
        rect.anchorMin = min;
        rect.anchorMax = max;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
        TMP_Text text = child.AddComponent<TextMeshProUGUI>();
        text.fontSize = fontSize;
        text.color = new Color(0.86f, 0.96f, 1f, 1f);
        text.alignment = alignment;
        text.enableWordWrapping = true;
        text.overflowMode = TextOverflowModes.Ellipsis;
        text.raycastTarget = false;
        return text;
    }

    private Button CreateButton(string objectName, string label, Vector2 min, Vector2 max)
    {
        GameObject child = new GameObject(objectName, typeof(RectTransform), typeof(Image), typeof(Button));
        child.transform.SetParent(transform, false);
        RectTransform rect = child.GetComponent<RectTransform>();
        rect.anchorMin = min;
        rect.anchorMax = max;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
        Image image = child.GetComponent<Image>();
        image.color = new Color(0.015f, 0.035f, 0.055f, 0.95f);
        TMP_Text text = CreateText("Text", Vector2.zero, Vector2.one, 10f, TextAlignmentOptions.Center);
        text.transform.SetParent(child.transform, false);
        text.text = label;
        return child.GetComponent<Button>();
    }

    private void WireButtons()
    {
        if (selectButton != null)
        {
            selectButton.onClick.RemoveListener(HandleSelect);
            selectButton.onClick.AddListener(HandleSelect);
        }
        if (assignButton != null)
        {
            assignButton.onClick.RemoveListener(HandleAssign);
            assignButton.onClick.AddListener(HandleAssign);
        }
        if (removeButton != null)
        {
            removeButton.onClick.RemoveListener(HandleRemove);
            removeButton.onClick.AddListener(HandleRemove);
        }
    }

    private void SetText(TMP_Text target, string value)
    {
        if (target != null)
        {
            target.text = value;
        }
    }
}

