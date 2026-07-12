using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

public class ProductBattleGeneratedSkillsPanelView : MonoBehaviour
{
    [SerializeField] private TMP_FontAsset overrideFontAsset;
    [SerializeField] private Transform content;
    [SerializeField] private TMP_Text headingText;
    [SerializeField] private TMP_Text emptyText;
    [SerializeField] private ProductBattleGeneratedSkillRowView rowPrefab;
    [SerializeField] private bool debugLog;

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
    }

    public void SetSelectedSkill(string skillId)
    {
        selectedSkillId = skillId ?? "";
    }

    public void Render(
        IEnumerable<GeneratedSkillDto> skills,
        string selectedCardDocId,
        IEnumerable<string> assignedSkillIds)
    {
        EnsureBuilt();
        ClearRows();

        HashSet<string> assigned = new HashSet<string>(assignedSkillIds ?? Enumerable.Empty<string>());
        List<GeneratedSkillDto> ordered = (skills ?? Enumerable.Empty<GeneratedSkillDto>())
            .Where(skill => skill != null && !string.IsNullOrWhiteSpace(skill.skill_id))
            .OrderByDescending(skill => !string.IsNullOrWhiteSpace(selectedCardDocId) && skill.doc_id == selectedCardDocId)
            .ThenBy(skill => skill.DisplayName)
            .ThenBy(skill => skill.skill_id)
            .ToList();

        if (headingText != null)
        {
            headingText.text = $"Generated Skills ({ordered.Count})";
        }

        if (emptyText != null)
        {
            emptyText.gameObject.SetActive(ordered.Count == 0);
            emptyText.text = "No generated skills";
        }

        foreach (GeneratedSkillDto skill in ordered)
        {
            ProductBattleGeneratedSkillRowView row = CreateRow();
            row.Bind(
                skill,
                skill.skill_id == selectedSkillId,
                assigned.Contains(skill.skill_id),
                !string.IsNullOrWhiteSpace(selectedCardDocId) && skill.doc_id == selectedCardDocId,
                HandleSelected,
                onAssign,
                onRemove
            );
            rows.Add(row);
        }

        if (debugLog)
        {
            Debug.Log($"[GeneratedSkills] Rendered {ordered.Count} skills. selectedCardDocId={selectedCardDocId}", this);
        }

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

        ProductBattleGeneratedSkillRowView[] generatedRows = GetComponentsInChildren<ProductBattleGeneratedSkillRowView>(true);
        foreach (ProductBattleGeneratedSkillRowView row in generatedRows)
        {
            if (row != null)
            {
                row.SetFontAsset(overrideFontAsset);
            }
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

        if (headingText == null)
        {
            headingText = CreateText("HeadingText", new Vector2(0.04f, 0.90f), new Vector2(0.96f, 0.99f), "Generated Skills", 17f, TextAlignmentOptions.Left);
        }

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
            emptyText = CreateText("EmptyText", new Vector2(0.06f, 0.40f), new Vector2(0.94f, 0.56f), "No generated skills", 14f, TextAlignmentOptions.Center);
        }

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
        image.raycastTarget = true;

        Mask mask = viewportObject.GetComponent<Mask>();
        mask.showMaskGraphic = false;
        return viewport;
    }

    private void ConfigureContent(Transform target)
    {
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
        layout.padding = new RectOffset(6, 6, 6, 6);
        layout.spacing = 6f;
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
        return text;
    }

    private void HandleSelected(GeneratedSkillDto skill)
    {
        selectedSkillId = skill == null ? "" : skill.skill_id;
        onSelected?.Invoke(skill);
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
            Destroy(content.GetChild(i).gameObject);
        }
    }
}
