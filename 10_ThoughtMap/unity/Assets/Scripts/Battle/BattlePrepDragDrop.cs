using System;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

public enum BattlePrepDragSourceKind { CardList, Deck, Formation }

public sealed class BattlePrepDragPayload
{
    public ThoughtMapBattleCardData card;
    public BattlePrepDragSourceKind source;
    public int sourceIndex;
}

public sealed class BattlePrepDragSource : MonoBehaviour, IBeginDragHandler, IDragHandler, IEndDragHandler
{
    public static BattlePrepDragPayload Current { get; private set; }
    private static BattlePrepDragSource activeSource;
    private ThoughtMapBattleCardData card;
    private BattlePrepDragSourceKind source;
    private int sourceIndex;
    private Canvas rootCanvas;
    private CanvasGroup canvasGroup;
    private RectTransform ghost;

    public void Configure(ThoughtMapBattleCardData value, BattlePrepDragSourceKind kind, int index)
    {
        card = value; source = kind; sourceIndex = index;
        rootCanvas = GetComponentInParent<Canvas>()?.rootCanvas;
    }

    public void OnBeginDrag(PointerEventData eventData)
    {
        if (card == null) return;
        canvasGroup = GetComponent<CanvasGroup>();
        if (canvasGroup == null) canvasGroup = gameObject.AddComponent<CanvasGroup>();
        Current = new BattlePrepDragPayload { card = card, source = source, sourceIndex = sourceIndex };
        activeSource = this;
        canvasGroup.alpha = 0.45f;
        canvasGroup.blocksRaycasts = false;
        CreateGhost(eventData.position);
        Debug.Log($"[BattlePrepDragDrop] BeginDrag source={source} index={sourceIndex} card={card.cardName} blocksRaycasts={canvasGroup.blocksRaycasts}", this);
    }

    public void OnDrag(PointerEventData eventData)
    {
        if (ghost != null) ghost.position = eventData.position;
    }

    public void OnEndDrag(PointerEventData eventData)
    {
        CompleteDrag("PointerEnd");
    }

    private void CompleteDrag(string reason)
    {
        if (activeSource != this && Current == null) return;
        canvasGroup.alpha = 1f;
        canvasGroup.blocksRaycasts = true;
        if (ghost != null) Destroy(ghost.gameObject);
        ghost = null;
        Current = null;
        activeSource = null;
        BattlePrepDropZone.ClearAllHighlights();
        Debug.Log($"[BattlePrepDragDrop] EndDrag reason={reason} source={source} index={sourceIndex} card={(card == null ? "null" : card.cardName)}", this);
    }

    public static void CompleteBeforeDrop()
    {
        if (activeSource != null) activeSource.CompleteDrag("DropComplete");
    }

    private void CreateGhost(Vector2 position)
    {
        if (rootCanvas == null) return;
        GameObject target = new GameObject("DragCardGhost", typeof(RectTransform), typeof(CanvasGroup), typeof(Image));
        target.transform.SetParent(rootCanvas.transform, false);
        ghost = target.GetComponent<RectTransform>(); ghost.sizeDelta = new Vector2(210f, 48f); ghost.position = position; ghost.SetAsLastSibling();
        target.GetComponent<Image>().color = new Color(0.02f, 0.42f, 0.58f, 0.78f);
        CanvasGroup group = target.GetComponent<CanvasGroup>(); group.alpha = 0.75f; group.blocksRaycasts = false;
        GameObject labelObject = new GameObject("Label", typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        labelObject.transform.SetParent(target.transform, false);
        TMP_Text label = labelObject.GetComponent<TMP_Text>(); label.text = card.cardName; label.font = GetComponentInChildren<TMP_Text>()?.font; label.fontSize = 16f; label.color = Color.white; label.alignment = TextAlignmentOptions.Center; label.raycastTarget = false;
        RectTransform labelRect = label.rectTransform; labelRect.anchorMin = Vector2.zero; labelRect.anchorMax = Vector2.one; labelRect.offsetMin = labelRect.offsetMax = Vector2.zero;
    }
}

public sealed class BattlePrepDropZone : MonoBehaviour, IDropHandler, IPointerEnterHandler, IPointerExitHandler
{
    private static readonly System.Collections.Generic.List<BattlePrepDropZone> Instances = new System.Collections.Generic.List<BattlePrepDropZone>();
    private Action<BattlePrepDragPayload> dropped;
    private Func<BattlePrepDragPayload, bool> accepts;
    private Graphic highlightGraphic;
    private Color normalColor;

    private void OnEnable() { if (!Instances.Contains(this)) Instances.Add(this); }
    private void OnDisable() { Instances.Remove(this); SetHighlight(false); }

    public void Configure(Action<BattlePrepDragPayload> onDropped, Func<BattlePrepDragPayload, bool> canAccept, Graphic graphic = null)
    {
        dropped = onDropped; accepts = canAccept; highlightGraphic = graphic ?? GetComponent<Graphic>();
        if (highlightGraphic != null) normalColor = highlightGraphic.color;
    }

    public void OnPointerEnter(PointerEventData eventData)
    {
        SetHighlight(BattlePrepDragSource.Current != null && (accepts == null || accepts(BattlePrepDragSource.Current)));
    }

    public void OnPointerExit(PointerEventData eventData) => SetHighlight(false);

    public void OnDrop(PointerEventData eventData)
    {
        BattlePrepDragPayload payload = BattlePrepDragSource.Current;
        SetHighlight(false);
        bool accepted = payload != null && (accepts == null || accepts(payload));
        Debug.Log($"[BattlePrepDragDrop] Drop target={name} source={(payload == null ? "none" : payload.source.ToString())} accepted={accepted}", this);
        if (accepted)
        {
            BattlePrepDragSource.CompleteBeforeDrop();
            dropped?.Invoke(payload);
        }
    }

    private void SetHighlight(bool active)
    {
        if (highlightGraphic == null) return;
        highlightGraphic.color = active ? Color.Lerp(normalColor, new Color(0.1f, 0.9f, 0.65f, normalColor.a), 0.58f) : normalColor;
    }

    public static void ClearAllHighlights()
    {
        foreach (BattlePrepDropZone zone in Instances.ToArray()) if (zone != null) zone.SetHighlight(false);
    }
}
