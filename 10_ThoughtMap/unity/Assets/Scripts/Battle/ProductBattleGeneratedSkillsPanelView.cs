using System.Collections.Generic;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleGeneratedSkillsPanelView : MonoBehaviour, IPointerDownHandler
{
    private enum InventoryFilter { Available, Equipped, All }
    [SerializeField] private TMP_FontAsset overrideFontAsset;
    [SerializeField] private Transform content;
    [SerializeField] private TMP_Text headingText;
    [SerializeField] private TMP_Text emptyText;
    [SerializeField] private ProductBattleGeneratedSkillRowView rowPrefab;
    [SerializeField] private bool debugLog;
    private InventoryFilter inventoryFilter = InventoryFilter.Available;
    private Button availableFilterButton;
    private Button equippedFilterButton;
    private Button allFilterButton;
    private List<GeneratedSkillDto> cachedSkills = new List<GeneratedSkillDto>();
    private string cachedSelectedCardDocId = "";
    private List<string> cachedAssignedSkillIds = new List<string>();
    private Dictionary<string, string> cachedAssignedLabels = new Dictionary<string, string>();
    private bool cachedSelectedCardIsDeckCard;
    private bool cachedSelectedCardCanReceiveSkill;

    private readonly List<ProductBattleGeneratedSkillRowView> rows = new List<ProductBattleGeneratedSkillRowView>();
    private string selectedSkillId = "";
    private UnityAction<GeneratedSkillDto> onSelected;
    private UnityAction<GeneratedSkillDto> onAssign;
    private UnityAction<GeneratedSkillDto> onRemove;

    public string SelectedSkillId => selectedSkillId;

    private void Awake()
    {
        EnsureBuilt();
    }

    public void SetHandlers(
        UnityAction<GeneratedSkillDto> selectedHandler,
        UnityAction<GeneratedSkillDto> assignHandler,
        UnityAction<GeneratedSkillDto> removeHandler)
    {
        onSelected = selectedHandler;
        onAssign = assignHandler;
        onRemove = removeHandler;
        if (debugLog)
        {
            Debug.Log($"[GeneratedSkill] Panel.SetHandlers selectedNull={onSelected == null} assignNull={onAssign == null} removeNull={onRemove == null}", this);
        }
    }

    public void SetSelectedSkill(string skillId)
    {
        selectedSkillId = skillId ?? "";
    }

    public void Render(
        IEnumerable<GeneratedSkillDto> skills,
        string selectedCardDocId,
        IEnumerable<string> assignedSkillIds,
        Dictionary<string, string> assignedSkillLabels,
        bool selectedCardIsDeckCard,
        bool selectedCardCanReceiveSkill)
    {
        EnsureBuilt();
        cachedSkills = (skills ?? Enumerable.Empty<GeneratedSkillDto>()).Where(item => item != null).ToList();
        cachedSelectedCardDocId = selectedCardDocId ?? "";
        cachedAssignedSkillIds = (assignedSkillIds ?? Enumerable.Empty<string>()).ToList();
        cachedAssignedLabels = assignedSkillLabels == null ? new Dictionary<string, string>() : new Dictionary<string, string>(assignedSkillLabels);
        cachedSelectedCardIsDeckCard = selectedCardIsDeckCard;
        cachedSelectedCardCanReceiveSkill = selectedCardCanReceiveSkill;
        ScrollRect scrollRect = GetComponent<ScrollRect>();
        float scrollPosition = scrollRect == null ? 1f : scrollRect.verticalNormalizedPosition;
        ClearRows();

        HashSet<string> assigned = new HashSet<string>(assignedSkillIds ?? Enumerable.Empty<string>());
        Dictionary<string, string> assignmentLabels = assignedSkillLabels ?? new Dictionary<string, string>();
        List<GeneratedSkillDto> allOrdered = cachedSkills
            .Where(skill => skill != null && !string.IsNullOrWhiteSpace(skill.skill_id))
            .OrderByDescending(skill => !string.IsNullOrWhiteSpace(selectedCardDocId) && skill.doc_id == selectedCardDocId)
            .ThenBy(skill => skill.DisplayName)
            .ThenBy(skill => skill.skill_id)
            .ToList();
        List<GeneratedSkillDto> ordered = allOrdered.Where(skill =>
            inventoryFilter == InventoryFilter.All ||
            (inventoryFilter == InventoryFilter.Equipped) == assignmentLabels.ContainsKey(skill.skill_id)).ToList();

        if (headingText != null)
        {
            headingText.text = $"Generated Skills ({ordered.Count}/{allOrdered.Count})";
        }

        if (emptyText != null)
        {
            emptyText.gameObject.SetActive(ordered.Count == 0);
            emptyText.text = inventoryFilter == InventoryFilter.Available ? "No Available Skills" : inventoryFilter == InventoryFilter.Equipped ? "No Equipped Skills" : "No Generated Skills";
        }

        foreach (GeneratedSkillDto skill in ordered)
        {
            bool assignedAnywhere = assignmentLabels.TryGetValue(skill.skill_id, out string assignedLabel);
            bool assignedToSelected = assigned.Contains(skill.skill_id);
            bool canAssign = selectedCardIsDeckCard && selectedCardCanReceiveSkill && !assignedAnywhere;
            bool canRemove = assignedToSelected;
            string unavailableReason = BuildUnavailableReason(selectedCardIsDeckCard, selectedCardCanReceiveSkill, assignedAnywhere, assignedToSelected);
            ProductBattleGeneratedSkillRowView row = CreateRow();
            row.Bind(
                skill,
                skill.skill_id == selectedSkillId,
                assignedAnywhere,
                assignedAnywhere ? assignedLabel : "",
                !string.IsNullOrWhiteSpace(selectedCardDocId) && skill.doc_id == selectedCardDocId,
                canAssign,
                canRemove,
                unavailableReason,
                HandleSelected,
                HandleAssign,
                HandleRemove
            );
            if (debugLog)
            {
                Debug.Log($"[GeneratedSkill] Panel.RenderRow skill_id={skill.skill_id} selected={skill.skill_id == selectedSkillId}", this);
            }
            rows.Add(row);
        }

        Canvas.ForceUpdateCanvases();
        if (content is RectTransform contentRect)
        {
            LayoutRebuilder.ForceRebuildLayoutImmediate(contentRect);
        }
        Canvas.ForceUpdateCanvases();

        LogScrollState(ordered.Count);
        if (scrollRect != null)
        {
            scrollRect.verticalNormalizedPosition = Mathf.Clamp01(scrollPosition);
        }

        if (debugLog)
        {
            Debug.Log($"[GeneratedSkill] rendered={ordered.Count} selectedCardDocId={selectedCardDocId}", this);
        }

        ApplyFontToGeneratedTexts();
        RefreshFilterButtons();
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
                ConfigureReadableText(text, text.fontSize);
            }
        }

        ProductBattleGeneratedSkillRowView[] generatedRows = GetComponentsInChildren<ProductBattleGeneratedSkillRowView>(true);
        foreach (ProductBattleGeneratedSkillRowView row in generatedRows)
        {
            if (row != null)
            {
                row.SetFontAsset(overrideFontAsset);
            }
        }
    }

    private void Update()
    {
        if (debugLog && Input.GetMouseButtonDown(0))
        {
            LogPointerRaycast("MouseDown");
        }
    }

    [ContextMenu("Ensure Generated Skills Panel")]
    public void EnsureBuilt()
    {
        RectTransform rect = GetComponent<RectTransform>();
        if (rect == null)
        {
            rect = gameObject.AddComponent<RectTransform>();
        }

        Image image = GetComponent<Image>();
        if (image == null)
        {
            image = gameObject.AddComponent<Image>();
        }
        image.color = new Color(0.015f, 0.03f, 0.04f, 0.68f);
        image.raycastTarget = true;

        EnsureCanvasRaycaster();

        if (headingText == null)
        {
            headingText = CreateText("HeadingText", new Vector2(0.04f, 0.90f), new Vector2(0.43f, 0.99f), "Generated Skills", 19f, TextAlignmentOptions.Left);
        }
        ConfigureReadableText(headingText, 19f);
        availableFilterButton = EnsureFilterButton(availableFilterButton, "AvailableFilter", "Available", new Vector2(0.44f, 0.91f), new Vector2(0.61f, 0.985f), InventoryFilter.Available);
        equippedFilterButton = EnsureFilterButton(equippedFilterButton, "EquippedFilter", "Equipped", new Vector2(0.62f, 0.91f), new Vector2(0.78f, 0.985f), InventoryFilter.Equipped);
        allFilterButton = EnsureFilterButton(allFilterButton, "AllFilter", "All", new Vector2(0.79f, 0.91f), new Vector2(0.95f, 0.985f), InventoryFilter.All);
        RefreshFilterButtons();

        RectTransform viewport = EnsureViewport();
        if (content == null)
        {
            Transform existing = viewport.Find("Content");
            if (existing == null)
            {
                GameObject contentObject = new GameObject("Content", typeof(RectTransform), typeof(VerticalLayoutGroup), typeof(ContentSizeFitter));
                contentObject.transform.SetParent(viewport, false);
                content = contentObject.transform;
            }
            else
            {
                content = existing;
            }
        }

        ConfigureContent(content);
        ConfigureScrollRect(viewport);

        if (emptyText == null)
        {
            emptyText = CreateText("EmptyText", new Vector2(0.06f, 0.40f), new Vector2(0.94f, 0.56f), "No generated skills", 15f, TextAlignmentOptions.Center);
        }
        ConfigureReadableText(emptyText, 15f);

        ApplyFontToGeneratedTexts();
    }

    private RectTransform EnsureViewport()
    {
        Transform existing = transform.Find("Viewport");
        GameObject viewportObject = existing == null
            ? new GameObject("Viewport", typeof(RectTransform), typeof(Image), typeof(Mask))
            : existing.gameObject;
        viewportObject.transform.SetParent(transform, false);
        RectTransform viewport = viewportObject.GetComponent<RectTransform>();
        viewport.anchorMin = new Vector2(0.04f, 0.04f);
        viewport.anchorMax = new Vector2(0.96f, 0.88f);
        viewport.offsetMin = Vector2.zero;
        viewport.offsetMax = Vector2.zero;

        Image image = viewportObject.GetComponent<Image>();
        image.color = new Color(0f, 0f, 0f, 0.08f);
        image.raycastTarget = false;

        Mask mask = viewportObject.GetComponent<Mask>();
        mask.showMaskGraphic = false;
        return viewport;
    }

    private void ConfigureContent(Transform target)
    {
        DisableConflictingLayoutGroups(target);
        RectTransform rect = target as RectTransform;
        if (rect != null)
        {
            rect.anchorMin = new Vector2(0f, 1f);
            rect.anchorMax = new Vector2(1f, 1f);
            rect.pivot = new Vector2(0.5f, 1f);
            rect.anchoredPosition = Vector2.zero;
            rect.sizeDelta = Vector2.zero;
        }

        VerticalLayoutGroup layout = target.GetComponent<VerticalLayoutGroup>();
        if (layout == null) layout = target.gameObject.AddComponent<VerticalLayoutGroup>();
        layout.padding = new RectOffset(8, 8, 8, 8);
        layout.spacing = 8f;
        layout.childAlignment = TextAnchor.UpperCenter;
        layout.childControlWidth = true;
        layout.childControlHeight = true;
        layout.childForceExpandWidth = true;
        layout.childForceExpandHeight = false;

        ContentSizeFitter fitter = target.GetComponent<ContentSizeFitter>();
        if (fitter == null) fitter = target.gameObject.AddComponent<ContentSizeFitter>();
        fitter.horizontalFit = ContentSizeFitter.FitMode.Unconstrained;
        fitter.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
    }

    private void ConfigureScrollRect(RectTransform viewport)
    {
        ScrollRect scrollRect = GetComponent<ScrollRect>();
        if (scrollRect == null) scrollRect = gameObject.AddComponent<ScrollRect>();
        scrollRect.viewport = viewport;
        scrollRect.content = content as RectTransform;
        scrollRect.horizontal = false;
        scrollRect.vertical = true;
        scrollRect.movementType = ScrollRect.MovementType.Clamped;
    }

    public void OnPointerDown(PointerEventData eventData)
    {
        if (!debugLog)
        {
            return;
        }

        Debug.Log(
            $"[GeneratedSkill] Panel.PointerDown currentSelected={(EventSystem.current == null || EventSystem.current.currentSelectedGameObject == null ? "" : EventSystem.current.currentSelectedGameObject.name)} currentRaycast={(eventData == null || eventData.pointerCurrentRaycast.gameObject == null ? "" : eventData.pointerCurrentRaycast.gameObject.name)} pointerPress={(eventData == null || eventData.pointerPress == null ? "" : eventData.pointerPress.name)}",
            this
        );
    }

    private void LogPointerRaycast(string reason)
    {
        if (!debugLog)
        {
            return;
        }

        if (EventSystem.current == null)
        {
            Debug.LogWarning($"[GeneratedSkill] Raycast {reason} EventSystem missing.", this);
            return;
        }

        PointerEventData pointer = new PointerEventData(EventSystem.current)
        {
            position = Input.mousePosition
        };
        List<RaycastResult> results = new List<RaycastResult>();
        EventSystem.current.RaycastAll(pointer, results);

        StringBuilder builder = new StringBuilder();
        int limit = Mathf.Min(results.Count, 12);
        for (int i = 0; i < limit; i++)
        {
            RaycastResult result = results[i];
            if (i > 0)
            {
                builder.Append(" > ");
            }
            builder.Append(result.gameObject == null ? "null" : result.gameObject.name);
        }

        Debug.Log(
            $"[GeneratedSkill] EventSystemRaycast reason={reason} CurrentSelected={(EventSystem.current.currentSelectedGameObject == null ? "" : EventSystem.current.currentSelectedGameObject.name)} " +
            $"first={(results.Count == 0 || results[0].gameObject == null ? "" : results[0].gameObject.name)} count={results.Count} path={builder}",
            this
        );
    }

    private ProductBattleGeneratedSkillRowView CreateRow()
    {
        ProductBattleGeneratedSkillRowView row;
        if (rowPrefab != null)
        {
            row = Instantiate(rowPrefab, content);
        }
        else
        {
            GameObject rowObject = new GameObject("GeneratedSkillRow", typeof(RectTransform), typeof(Image), typeof(Button), typeof(ProductBattleGeneratedSkillRowView));
            rowObject.transform.SetParent(content, false);
            row = rowObject.GetComponent<ProductBattleGeneratedSkillRowView>();
        }
        row.SetFontAsset(overrideFontAsset);
        return row;
    }

    private void EnsureCanvasRaycaster()
    {
        Canvas canvas = GetComponentInParent<Canvas>();
        if (canvas == null)
        {
            Debug.LogWarning("[GeneratedSkill] Canvas missing for Generated Skills Panel.", this);
            return;
        }

        GraphicRaycaster raycaster = canvas.GetComponent<GraphicRaycaster>();
        if (raycaster == null)
        {
            raycaster = canvas.gameObject.AddComponent<GraphicRaycaster>();
            if (debugLog)
            {
                Debug.LogWarning($"[GeneratedSkill] GraphicRaycaster was missing and has been added to Canvas={canvas.gameObject.name}.", canvas);
            }
        }
        else if (debugLog)
        {
            Debug.Log($"[GeneratedSkill] GraphicRaycaster present Canvas={canvas.gameObject.name} enabled={raycaster.enabled}", canvas);
        }
    }

    private void LogScrollState(int generatedSkillCount)
    {
        if (!debugLog)
        {
            return;
        }

        RectTransform contentRect = content as RectTransform;
        ScrollRect scrollRect = GetComponent<ScrollRect>();
        RectTransform viewport = scrollRect == null ? null : scrollRect.viewport;
        Debug.Log(
            $"[GeneratedSkill] Layout generatedSkillCount={generatedSkillCount} renderedRowCount={rows.Count} " +
            $"contentHeight={(contentRect == null ? -1f : contentRect.rect.height):0.##} " +
            $"viewportHeight={(viewport == null ? -1f : viewport.rect.height):0.##} " +
            $"scrollVertical={(scrollRect != null && scrollRect.vertical)} content={(contentRect == null ? "null" : contentRect.name)} viewport={(viewport == null ? "null" : viewport.name)}",
            this
        );
    }

    private static void DisableConflictingLayoutGroups(Transform target)
    {
        if (target == null)
        {
            return;
        }

        LayoutGroup[] groups = target.GetComponents<LayoutGroup>();
        foreach (LayoutGroup group in groups)
        {
            if (group != null && !(group is VerticalLayoutGroup))
            {
                group.enabled = false;
            }
        }
    }

    private TMP_Text CreateText(string objectName, Vector2 min, Vector2 max, string textValue, float fontSize, TextAlignmentOptions alignment)
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
        text.text = textValue;
        text.fontSize = fontSize;
        text.color = new Color(0.86f, 0.96f, 1f, 1f);
        text.alignment = alignment;
        text.raycastTarget = false;
        ConfigureReadableText(text, fontSize);
        return text;
    }

    private Button EnsureFilterButton(Button current, string objectName, string label, Vector2 min, Vector2 max, InventoryFilter filter)
    {
        if (current == null)
        {
            Transform existing = transform.Find(objectName);
            if (existing != null) current = existing.GetComponent<Button>();
        }
        if (current == null)
        {
            GameObject target = new GameObject(objectName, typeof(RectTransform), typeof(Image), typeof(Button));
            target.transform.SetParent(transform, false);
            current = target.GetComponent<Button>();
            TMP_Text text = CreateText("Label", Vector2.zero, Vector2.one, label, 11f, TextAlignmentOptions.Center);
            text.transform.SetParent(target.transform, false);
        }
        RectTransform rect = current.transform as RectTransform;
        rect.anchorMin = min; rect.anchorMax = max; rect.offsetMin = rect.offsetMax = Vector2.zero;
        current.onClick.RemoveAllListeners(); current.onClick.AddListener(() => SetInventoryFilter(filter));
        return current;
    }

    private void SetInventoryFilter(InventoryFilter filter)
    {
        inventoryFilter = filter;
        Render(cachedSkills, cachedSelectedCardDocId, cachedAssignedSkillIds, cachedAssignedLabels, cachedSelectedCardIsDeckCard, cachedSelectedCardCanReceiveSkill);
    }

    private void RefreshFilterButtons()
    {
        SetFilterColor(availableFilterButton, inventoryFilter == InventoryFilter.Available);
        SetFilterColor(equippedFilterButton, inventoryFilter == InventoryFilter.Equipped);
        SetFilterColor(allFilterButton, inventoryFilter == InventoryFilter.All);
    }

    private static void SetFilterColor(Button button, bool selected)
    {
        Image image = button == null ? null : button.GetComponent<Image>();
        if (image != null) image.color = selected ? new Color(0.0f, 0.48f, 0.62f, 0.96f) : new Color(0.03f, 0.16f, 0.22f, 0.92f);
    }

    private static void ConfigureReadableText(TMP_Text text, float fontSize)
    {
        if (text == null)
        {
            return;
        }

        text.fontSize = fontSize;
        text.enableWordWrapping = true;
        text.overflowMode = TextOverflowModes.Overflow;
        Shadow shadow = text.GetComponent<Shadow>();
        if (shadow == null)
        {
            shadow = text.gameObject.AddComponent<Shadow>();
        }
        shadow.effectColor = new Color(0f, 0f, 0f, 0.72f);
        shadow.effectDistance = new Vector2(1f, -1f);
    }

    private void HandleSelected(GeneratedSkillDto skill)
    {
        selectedSkillId = skill == null ? "" : skill.skill_id;
        if (debugLog)
        {
            Debug.Log($"[GeneratedSkill] Panel.Select skill_id={selectedSkillId} onSelectedNull={onSelected == null}", this);
        }
        onSelected?.Invoke(skill);
    }

    private void HandleAssign(GeneratedSkillDto skill)
    {
        if (debugLog)
        {
            Debug.Log($"[GeneratedSkill] Panel.Assign skill_id={(skill == null ? "" : skill.skill_id)} onAssignNull={onAssign == null}", this);
        }
        onAssign?.Invoke(skill);
    }

    private void HandleRemove(GeneratedSkillDto skill)
    {
        if (debugLog)
        {
            Debug.Log($"[GeneratedSkill] Panel.Remove skill_id={(skill == null ? "" : skill.skill_id)} onRemoveNull={onRemove == null}", this);
        }
        onRemove?.Invoke(skill);
    }

    private static string BuildUnavailableReason(bool selectedCardIsDeckCard, bool selectedCardCanReceiveSkill, bool assignedAnywhere, bool assignedToSelected)
    {
        if (assignedToSelected)
        {
            return "";
        }

        if (assignedAnywhere)
        {
            return "Used by another card";
        }

        if (!selectedCardIsDeckCard)
        {
            return "Select deck card";
        }

        if (!selectedCardCanReceiveSkill)
        {
            return "Card already has a skill";
        }

        return "";
    }

    private void ClearRows()
    {
        rows.Clear();
        if (content == null)
        {
            return;
        }
        for (int i = content.childCount - 1; i >= 0; i--)
        {
            GameObject child = content.GetChild(i).gameObject;
            child.SetActive(false);
            Destroy(child);
        }
    }
}
