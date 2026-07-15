using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleGeneratedSkillRowView : MonoBehaviour, IPointerDownHandler, IPointerClickHandler
{
    [SerializeField] private TMP_FontAsset overrideFontAsset;
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
    private int lastSelectFrame = -1;

    public GeneratedSkillDto Skill => skill;

    public void Bind(
        GeneratedSkillDto sourceSkill,
        bool selected,
        bool assigned,
        string assignedLabel,
        bool matchingDoc,
        bool canAssign,
        bool canRemove,
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
        SetText(stateText, assigned
            ? $"Assigned to: {assignedLabel}"
            : "Available");

        if (backgroundImage != null)
        {
            backgroundImage.color = selected
                ? new Color(0.0f, 0.42f, 0.58f, 0.94f)
                : matchingDoc
                    ? new Color(0.08f, 0.20f, 0.18f, 0.90f)
                    : new Color(0.02f, 0.10f, 0.14f, 0.88f);
        }

        WireButtons();
        if (assignButton != null)
        {
            assignButton.interactable = true;
        }
        if (removeButton != null)
        {
            removeButton.interactable = true;
        }
        Debug.Log(
            $"[GeneratedSkill] Row.Bind skill_id={(sourceSkill == null ? "" : sourceSkill.skill_id)} canAssign={canAssign} canRemove={canRemove} assigned={assigned} selected={selected} {DescribeRaycastState()}",
            this
        );
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

    private void HandleSelect()
    {
        SelectSkillOnce("Button");
    }

    private void SelectSkillOnce(string source)
    {
        if (lastSelectFrame == Time.frameCount)
        {
            return;
        }

        lastSelectFrame = Time.frameCount;
        Debug.Log($"[GeneratedSkill] Row.SelectClick source={source} skill_id={(skill == null ? "" : skill.skill_id)} onSelectedNull={onSelected == null}", this);
        onSelected?.Invoke(skill);
    }

    public void OnPointerDown(PointerEventData eventData)
    {
        Debug.Log(
            $"[GeneratedSkill] Row.PointerDown skill_id={(skill == null ? "" : skill.skill_id)} currentRaycast={RaycastName(eventData)} pointerPress={(eventData == null || eventData.pointerPress == null ? "" : eventData.pointerPress.name)}",
            this
        );
    }

    public void OnPointerClick(PointerEventData eventData)
    {
        Debug.Log(
            $"[GeneratedSkill] Row.PointerClick skill_id={(skill == null ? "" : skill.skill_id)} currentRaycast={RaycastName(eventData)} pointerPress={(eventData == null || eventData.pointerPress == null ? "" : eventData.pointerPress.name)}",
            this
        );
        if (eventData != null && eventData.pointerPress == gameObject)
        {
            SelectSkillOnce("PointerClick");
        }
    }

    private void HandleAssign()
    {
        Debug.Log($"[GeneratedSkill] Row.AssignClick skill_id={(skill == null ? "" : skill.skill_id)} onAssignNull={onAssign == null}", this);
        onAssign?.Invoke(skill);
    }

    private void HandleRemove()
    {
        Debug.Log($"[GeneratedSkill] Row.RemoveClick skill_id={(skill == null ? "" : skill.skill_id)} onRemoveNull={onRemove == null}", this);
        onRemove?.Invoke(skill);
    }

    private void EnsureBuilt()
    {
        RectTransform rect = GetComponent<RectTransform>();
        if (rect == null) rect = gameObject.AddComponent<RectTransform>();
        rect.anchorMin = new Vector2(0f, 1f);
        rect.anchorMax = new Vector2(1f, 1f);
        rect.pivot = new Vector2(0.5f, 1f);
        rect.sizeDelta = new Vector2(0f, 128f);

        LayoutElement layoutElement = GetComponent<LayoutElement>();
        if (layoutElement == null) layoutElement = gameObject.AddComponent<LayoutElement>();
        layoutElement.minHeight = 128f;
        layoutElement.preferredHeight = 128f;
        layoutElement.flexibleWidth = 1f;

        backgroundImage = backgroundImage == null ? GetComponent<Image>() : backgroundImage;
        if (backgroundImage == null) backgroundImage = gameObject.AddComponent<Image>();
        backgroundImage.raycastTarget = true;

        selectButton = selectButton == null || selectButton.gameObject != gameObject ? GetComponent<Button>() : selectButton;
        if (selectButton == null) selectButton = gameObject.AddComponent<Button>();
        selectButton.targetGraphic = backgroundImage;

        nameText = nameText == null ? CreateText("NameText", new Vector2(0.03f, 0.74f), new Vector2(0.70f, 0.96f), 15f, TextAlignmentOptions.Left) : nameText;
        metaText = metaText == null ? CreateText("MetaText", new Vector2(0.03f, 0.50f), new Vector2(0.70f, 0.74f), 12f, TextAlignmentOptions.Left) : metaText;
        effectText = effectText == null ? CreateText("EffectText", new Vector2(0.03f, 0.12f), new Vector2(0.70f, 0.50f), 12f, TextAlignmentOptions.Left) : effectText;
        stateText = stateText == null ? CreateText("StateText", new Vector2(0.72f, 0.66f), new Vector2(0.97f, 0.95f), 11f, TextAlignmentOptions.Right) : stateText;
        assignButton = ResolveChildButton(assignButton, "AssignButton", "Assign", new Vector2(0.72f, 0.34f), new Vector2(0.845f, 0.58f));
        removeButton = ResolveChildButton(removeButton, "RemoveButton", "Remove", new Vector2(0.855f, 0.34f), new Vector2(0.98f, 0.58f));
        if (assignButton != null) assignButton.transform.SetAsLastSibling();
        if (removeButton != null) removeButton.transform.SetAsLastSibling();
        AnchorText(nameText, new Vector2(0.03f, 0.74f), new Vector2(0.70f, 0.96f));
        AnchorText(metaText, new Vector2(0.03f, 0.50f), new Vector2(0.70f, 0.74f));
        AnchorText(effectText, new Vector2(0.03f, 0.12f), new Vector2(0.70f, 0.50f));
        AnchorText(stateText, new Vector2(0.72f, 0.66f), new Vector2(0.97f, 0.95f));
        AnchorButton(assignButton, new Vector2(0.72f, 0.34f), new Vector2(0.845f, 0.58f));
        AnchorButton(removeButton, new Vector2(0.855f, 0.34f), new Vector2(0.98f, 0.58f));
        ConfigureExistingText(nameText, 15f, TextOverflowModes.Ellipsis);
        ConfigureExistingText(metaText, 12f, TextOverflowModes.Overflow);
        ConfigureExistingText(effectText, 12f, TextOverflowModes.Overflow);
        ConfigureExistingText(stateText, 11f, TextOverflowModes.Overflow);
        ConfigureButtonLabel(assignButton, 11f);
        ConfigureButtonLabel(removeButton, 11f);
    }

    private Button ResolveChildButton(Button current, string objectName, string label, Vector2 min, Vector2 max)
    {
        bool invalidReference = current == null
            || current.gameObject == gameObject
            || current.transform.parent != transform
            || current.gameObject.name != objectName;

        if (invalidReference)
        {
            Transform existing = transform.Find(objectName);
            current = existing == null ? null : existing.GetComponent<Button>();
        }

        if (current == null)
        {
            current = CreateButton(objectName, label, min, max);
            Debug.Log($"[GeneratedSkill] Row.RepairButton created={objectName}", this);
        }

        current.gameObject.name = objectName;
        return current;
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
        if (overrideFontAsset != null)
        {
            text.font = overrideFontAsset;
        }
        text.fontSize = fontSize;
        text.color = new Color(0.86f, 0.96f, 1f, 1f);
        text.alignment = alignment;
        text.enableWordWrapping = true;
        text.overflowMode = TextOverflowModes.Overflow;
        text.raycastTarget = false;
        AddReadableShadow(text.gameObject);
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
        TMP_Text text = CreateText("Text", Vector2.zero, Vector2.one, 11f, TextAlignmentOptions.Center);
        text.transform.SetParent(child.transform, false);
        text.text = label;
        return child.GetComponent<Button>();
    }

    private void ConfigureExistingText(TMP_Text text, float fontSize, TextOverflowModes overflow)
    {
        if (text == null)
        {
            return;
        }

        text.fontSize = fontSize;
        text.enableWordWrapping = true;
        text.overflowMode = overflow;
        AddReadableShadow(text.gameObject);
    }

    private void ConfigureButtonLabel(Button button, float fontSize)
    {
        if (button == null)
        {
            return;
        }

        TMP_Text text = button.GetComponentInChildren<TMP_Text>(true);
        if (text != null)
        {
            text.fontSize = fontSize;
            text.enableWordWrapping = false;
            text.overflowMode = TextOverflowModes.Overflow;
            AddReadableShadow(text.gameObject);
        }
    }

    private static void AnchorText(TMP_Text text, Vector2 min, Vector2 max)
    {
        if (text == null)
        {
            return;
        }

        RectTransform rect = text.transform as RectTransform;
        AnchorRect(rect, min, max);
    }

    private static void AnchorButton(Button button, Vector2 min, Vector2 max)
    {
        if (button == null)
        {
            return;
        }

        RectTransform rect = button.transform as RectTransform;
        AnchorRect(rect, min, max);
    }

    private static void AnchorRect(RectTransform rect, Vector2 min, Vector2 max)
    {
        if (rect == null)
        {
            return;
        }

        rect.anchorMin = min;
        rect.anchorMax = max;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
    }

    private static void AddReadableShadow(GameObject target)
    {
        if (target == null)
        {
            return;
        }

        Shadow shadow = target.GetComponent<Shadow>();
        if (shadow == null)
        {
            shadow = target.AddComponent<Shadow>();
        }
        shadow.effectColor = new Color(0f, 0f, 0f, 0.72f);
        shadow.effectDistance = new Vector2(1f, -1f);
    }

    private void WireButtons()
    {
        if (selectButton != null)
        {
            selectButton.interactable = true;
            selectButton.targetGraphic = backgroundImage;
            selectButton.onClick.RemoveAllListeners();
            selectButton.onClick.AddListener(HandleSelect);
            Debug.Log($"[GeneratedSkill] Row.WireSelect button={selectButton.gameObject.name} skill_id={(skill == null ? "" : skill.skill_id)} interactable={selectButton.interactable} targetGraphic={(selectButton.targetGraphic == null ? "" : selectButton.targetGraphic.name)}", this);
        }
        if (assignButton != null)
        {
            Image image = assignButton.GetComponent<Image>();
            if (image != null)
            {
                image.raycastTarget = true;
                assignButton.targetGraphic = image;
            }
            assignButton.onClick.RemoveAllListeners();
            assignButton.onClick.AddListener(HandleAssign);
            Debug.Log($"[GeneratedSkill] Row.WireAssign button={assignButton.gameObject.name} skill_id={(skill == null ? "" : skill.skill_id)}", this);
        }
        if (removeButton != null)
        {
            Image image = removeButton.GetComponent<Image>();
            if (image != null)
            {
                image.raycastTarget = true;
                removeButton.targetGraphic = image;
            }
            removeButton.onClick.RemoveAllListeners();
            removeButton.onClick.AddListener(HandleRemove);
            Debug.Log($"[GeneratedSkill] Row.WireRemove button={removeButton.gameObject.name} skill_id={(skill == null ? "" : skill.skill_id)}", this);
        }
    }

    private void SetText(TMP_Text target, string value)
    {
        if (target != null)
        {
            target.text = value;
        }
    }

    private string DescribeRaycastState()
    {
        string rootRaycast = backgroundImage == null ? "rootRaycast=null" : $"rootRaycast={backgroundImage.raycastTarget}";
        string selectState = selectButton == null ? "selectButton=null" : $"selectButton={selectButton.gameObject.name},interactable={selectButton.interactable}";
        CanvasGroup[] groups = GetComponentsInParent<CanvasGroup>(true);
        if (groups == null || groups.Length == 0)
        {
            return $"{rootRaycast} {selectState} canvasGroups=none";
        }

        string groupState = "";
        foreach (CanvasGroup group in groups)
        {
            if (group == null)
            {
                continue;
            }
            if (groupState.Length > 0)
            {
                groupState += "|";
            }
            groupState += $"{group.gameObject.name}:blocks={group.blocksRaycasts},interactable={group.interactable},alpha={group.alpha:0.##}";
        }
        return $"{rootRaycast} {selectState} canvasGroups={groupState}";
    }

    private static string RaycastName(PointerEventData eventData)
    {
        if (eventData == null || eventData.pointerCurrentRaycast.gameObject == null)
        {
            return "";
        }
        return eventData.pointerCurrentRaycast.gameObject.name;
    }
}
