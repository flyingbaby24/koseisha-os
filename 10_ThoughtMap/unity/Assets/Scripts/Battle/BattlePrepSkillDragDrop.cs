using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

public sealed class BattlePrepSkillDragSource : MonoBehaviour, IBeginDragHandler, IDragHandler, IEndDragHandler
{
    public static GeneratedSkillDto Current { get; private set; }
    private static BattlePrepSkillDragSource activeSource;
    private GeneratedSkillDto skill;
    private Canvas rootCanvas;
    private CanvasGroup group;
    private RectTransform ghost;
    private bool dragging;

    public void Configure(GeneratedSkillDto value)
    {
        skill = value;
        rootCanvas = GetComponentInParent<Canvas>()?.rootCanvas;
    }

    public void OnBeginDrag(PointerEventData eventData)
    {
        if (skill == null) return;
        Current = skill;
        activeSource = this;
        group = GetComponent<CanvasGroup>();
        if (group == null) group = gameObject.AddComponent<CanvasGroup>();
        dragging = true;
        group.alpha = 0.45f; group.blocksRaycasts = false;
        CreateGhost(eventData.position);
        BattlePrepSkillDropTarget.ShowEligible(skill);
        Debug.Log($"[BattlePrepSkillDragDrop] BeginDrag skill={skill.skill_id} blocksRaycasts={group.blocksRaycasts}", this);
    }

    public void OnDrag(PointerEventData eventData) { if (ghost != null) ghost.position = eventData.position; }

    public void OnEndDrag(PointerEventData eventData) => Complete();

    public void Complete()
    {
        if (!dragging) return;
        dragging = false;
        if (group) { group.alpha = 1f; group.blocksRaycasts = true; }
        if (ghost != null) Destroy(ghost.gameObject);
        ghost = null; Current = null;
        activeSource = null;
        BattlePrepSkillDropTarget.ClearHighlights();
        Debug.Log($"[BattlePrepSkillDragDrop] EndDrag skill={(skill == null ? "null" : skill.skill_id)}", this);
    }
    public static void CompleteBeforeDrop() { if (activeSource != null) activeSource.Complete(); }

    private void CreateGhost(Vector2 position)
    {
        if (rootCanvas == null) return;
        GameObject target = new GameObject("SkillDragGhost", typeof(RectTransform), typeof(Image), typeof(CanvasGroup));
        target.transform.SetParent(rootCanvas.transform, false);
        ghost = target.GetComponent<RectTransform>(); ghost.sizeDelta = new Vector2(250f, 54f); ghost.position = position; ghost.SetAsLastSibling();
        target.GetComponent<Image>().color = new Color(0.18f, 0.52f, 0.72f, 0.84f);
        CanvasGroup cg = target.GetComponent<CanvasGroup>(); cg.blocksRaycasts = false; cg.alpha = 0.82f;
        GameObject labelObject = new GameObject("Label", typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI)); labelObject.transform.SetParent(target.transform, false);
        TMP_Text label = labelObject.GetComponent<TMP_Text>(); label.text = skill.DisplayName; label.font = GetComponentInChildren<TMP_Text>()?.font; label.fontSize = 16f; label.alignment = TextAlignmentOptions.Center; label.color = Color.white; label.raycastTarget = false;
        label.rectTransform.anchorMin = Vector2.zero; label.rectTransform.anchorMax = Vector2.one; label.rectTransform.offsetMin = label.rectTransform.offsetMax = Vector2.zero;
    }
}

public sealed class BattlePrepSkillDropTarget : MonoBehaviour, IDropHandler, IPointerEnterHandler, IPointerExitHandler
{
    private static readonly List<BattlePrepSkillDropTarget> Instances = new List<BattlePrepSkillDropTarget>();
    private Action<GeneratedSkillDto> dropped;
    private Func<GeneratedSkillDto, bool> accepts;
    private Graphic graphic;
    private Color normal;

    private void OnEnable() { if (!Instances.Contains(this)) Instances.Add(this); }
    private void OnDisable() { Instances.Remove(this); SetHighlight(false); }

    public void Configure(Action<GeneratedSkillDto> action, Func<GeneratedSkillDto, bool> predicate, Graphic targetGraphic)
    {
        dropped = action; accepts = predicate; graphic = targetGraphic;
        if (graphic != null) normal = graphic.color;
    }

    public void OnDrop(PointerEventData eventData)
    {
        GeneratedSkillDto skill = BattlePrepSkillDragSource.Current;
        bool accepted = skill != null && (accepts == null || accepts(skill));
        Debug.Log($"[BattlePrepSkillDragDrop] Drop target={name} skill={(skill == null ? "none" : skill.skill_id)} accepted={accepted}", this);
        if (accepted)
        {
            BattlePrepSkillDragSource.CompleteBeforeDrop();
            dropped?.Invoke(skill);
        }
    }
    public void OnPointerEnter(PointerEventData eventData) { if (BattlePrepSkillDragSource.Current != null) SetHighlight(accepts == null || accepts(BattlePrepSkillDragSource.Current)); }
    public void OnPointerExit(PointerEventData eventData) { if (BattlePrepSkillDragSource.Current == null) SetHighlight(false); }
    private void SetHighlight(bool value) { if (graphic != null) graphic.color = value ? Color.Lerp(normal, new Color(0.2f, 0.95f, 0.7f, normal.a), 0.62f) : normal; }
    public static void ShowEligible(GeneratedSkillDto skill) { foreach (BattlePrepSkillDropTarget target in Instances.ToArray()) if (target != null) target.SetHighlight(target.accepts == null || target.accepts(skill)); }
    public static void ClearHighlights() { foreach (BattlePrepSkillDropTarget target in Instances.ToArray()) if (target != null) target.SetHighlight(false); }
}
