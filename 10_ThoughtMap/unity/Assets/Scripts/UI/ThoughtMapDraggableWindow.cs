using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

[DisallowMultipleComponent]
public class ThoughtMapDraggableWindow : MonoBehaviour, IBeginDragHandler, IDragHandler, IEndDragHandler
{
    [Header("Drag Target")]
    [SerializeField] private RectTransform targetWindow;
    [SerializeField] private bool clampInsideParent = true;
    [SerializeField] private float clampPadding = 12f;
    [SerializeField] private bool ignoreLayoutWhileDragging;
    [SerializeField] private bool keepDetachedFromLayout;

    private RectTransform handleRect;
    private RectTransform parentRect;
    private LayoutElement targetLayoutElement;
    private bool previousIgnoreLayout;
    private Vector2 pointerOffset;

    private void Awake()
    {
        handleRect = transform as RectTransform;
        if (targetWindow == null)
        {
            targetWindow = handleRect;
        }

        CacheParent();
    }

    public void Configure(RectTransform target, bool detachFromLayoutOnDrag)
    {
        Configure(target, detachFromLayoutOnDrag, false);
    }

    public void Configure(RectTransform target, bool detachFromLayoutOnDrag, bool keepDetached)
    {
        targetWindow = target == null ? transform as RectTransform : target;
        ignoreLayoutWhileDragging = detachFromLayoutOnDrag;
        keepDetachedFromLayout = keepDetached;
        handleRect = transform as RectTransform;
        CacheParent();
    }

    public void OnBeginDrag(PointerEventData eventData)
    {
        if (targetWindow == null)
        {
            return;
        }

        CacheParent();
        targetWindow.SetAsLastSibling();

        if (ignoreLayoutWhileDragging)
        {
            targetLayoutElement = targetWindow.GetComponent<LayoutElement>();
            if (targetLayoutElement != null)
            {
                previousIgnoreLayout = targetLayoutElement.ignoreLayout;
                targetLayoutElement.ignoreLayout = true;
            }
        }

        if (RectTransformUtility.ScreenPointToLocalPointInRectangle(
                parentRect,
                eventData.position,
                eventData.pressEventCamera,
                out Vector2 localPointer))
        {
            pointerOffset = targetWindow.anchoredPosition - localPointer;
        }
    }

    public void OnDrag(PointerEventData eventData)
    {
        if (targetWindow == null || parentRect == null)
        {
            return;
        }

        if (!RectTransformUtility.ScreenPointToLocalPointInRectangle(
                parentRect,
                eventData.position,
                eventData.pressEventCamera,
                out Vector2 localPointer))
        {
            return;
        }

        Vector2 nextPosition = localPointer + pointerOffset;
        targetWindow.anchoredPosition = clampInsideParent ? ClampAnchoredPosition(nextPosition) : nextPosition;
    }

    public void OnEndDrag(PointerEventData eventData)
    {
        if (targetWindow != null && clampInsideParent)
        {
            targetWindow.anchoredPosition = ClampAnchoredPosition(targetWindow.anchoredPosition);
        }

        if (targetLayoutElement != null && !keepDetachedFromLayout)
        {
            targetLayoutElement.ignoreLayout = previousIgnoreLayout;
            targetLayoutElement = null;
        }
    }

    private void CacheParent()
    {
        if (targetWindow == null)
        {
            return;
        }

        parentRect = targetWindow.parent as RectTransform;
    }

    private Vector2 ClampAnchoredPosition(Vector2 position)
    {
        if (parentRect == null || targetWindow == null)
        {
            return position;
        }

        Rect parent = parentRect.rect;
        Vector2 size = targetWindow.rect.size;
        Vector2 pivot = targetWindow.pivot;

        float minX = parent.xMin + size.x * pivot.x + clampPadding;
        float maxX = parent.xMax - size.x * (1f - pivot.x) - clampPadding;
        float minY = parent.yMin + size.y * pivot.y + clampPadding;
        float maxY = parent.yMax - size.y * (1f - pivot.y) - clampPadding;

        if (minX > maxX)
        {
            float centerX = (parent.xMin + parent.xMax) * 0.5f;
            minX = centerX;
            maxX = centerX;
        }

        if (minY > maxY)
        {
            float centerY = (parent.yMin + parent.yMax) * 0.5f;
            minY = centerY;
            maxY = centerY;
        }

        return new Vector2(
            Mathf.Clamp(position.x, minX, maxX),
            Mathf.Clamp(position.y, minY, maxY)
        );
    }
}
