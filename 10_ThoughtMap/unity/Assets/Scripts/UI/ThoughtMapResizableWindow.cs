using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

[DisallowMultipleComponent]
public class ThoughtMapResizableWindow : MonoBehaviour, IBeginDragHandler, IDragHandler
{
    [SerializeField] private RectTransform targetWindow;
    [SerializeField] private Vector2 minSize = new Vector2(320f, 180f);
    [SerializeField] private Vector2 maxSize = new Vector2(1600f, 1200f);
    [SerializeField] private bool clampInsideParent = true;
    [SerializeField] private float clampPadding = 12f;

    private RectTransform parentRect;
    private LayoutElement targetLayoutElement;
    private Vector2 startPointer;
    private Vector2 startSize;
    private Vector2 startPosition;

    private void Awake()
    {
        if (targetWindow == null)
        {
            targetWindow = transform.parent as RectTransform;
        }

        CacheParent();
        EnsureRaycastTarget();
    }

    public void Configure(RectTransform target, Vector2 minimumSize)
    {
        targetWindow = target == null ? transform.parent as RectTransform : target;
        minSize = minimumSize;
        CacheParent();
        EnsureRaycastTarget();
    }

    public void OnBeginDrag(PointerEventData eventData)
    {
        if (targetWindow == null)
        {
            return;
        }

        CacheParent();
        targetLayoutElement = targetWindow == null ? null : targetWindow.GetComponent<LayoutElement>();
        startSize = targetWindow.sizeDelta;
        if (targetLayoutElement != null)
        {
            startSize = new Vector2(
                targetLayoutElement.preferredWidth > 0f ? targetLayoutElement.preferredWidth : startSize.x,
                targetLayoutElement.preferredHeight > 0f ? targetLayoutElement.preferredHeight : startSize.y
            );
        }
        startPosition = targetWindow.anchoredPosition;

        RectTransformUtility.ScreenPointToLocalPointInRectangle(
            parentRect,
            eventData.position,
            eventData.pressEventCamera,
            out startPointer
        );
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
                out Vector2 currentPointer))
        {
            return;
        }

        Vector2 delta = currentPointer - startPointer;
        Vector2 nextSize = new Vector2(
            Mathf.Clamp(startSize.x + delta.x, minSize.x, maxSize.x),
            Mathf.Clamp(startSize.y - delta.y, minSize.y, maxSize.y)
        );

        targetWindow.sizeDelta = nextSize;
        if (targetLayoutElement != null)
        {
            targetLayoutElement.preferredWidth = nextSize.x;
            targetLayoutElement.preferredHeight = nextSize.y;
            targetLayoutElement.minHeight = Mathf.Min(targetLayoutElement.minHeight <= 0f ? minSize.y : targetLayoutElement.minHeight, nextSize.y);
        }

        if (clampInsideParent)
        {
            targetWindow.anchoredPosition = ClampAnchoredPosition(startPosition, nextSize);
        }
    }

    private void CacheParent()
    {
        parentRect = targetWindow == null ? null : targetWindow.parent as RectTransform;
    }

    private void EnsureRaycastTarget()
    {
        Graphic graphic = GetComponent<Graphic>();
        if (graphic != null)
        {
            graphic.raycastTarget = true;
        }
    }

    private Vector2 ClampAnchoredPosition(Vector2 position, Vector2 size)
    {
        if (parentRect == null || targetWindow == null)
        {
            return position;
        }

        Rect parent = parentRect.rect;
        Vector2 pivot = targetWindow.pivot;

        float minX = parent.xMin + size.x * pivot.x + clampPadding;
        float maxX = parent.xMax - size.x * (1f - pivot.x) - clampPadding;
        float minY = parent.yMin + size.y * pivot.y + clampPadding;
        float maxY = parent.yMax - size.y * (1f - pivot.y) - clampPadding;

        if (minX > maxX)
        {
            minX = maxX = parent.center.x;
        }

        if (minY > maxY)
        {
            minY = maxY = parent.center.y;
        }

        return new Vector2(Mathf.Clamp(position.x, minX, maxX), Mathf.Clamp(position.y, minY, maxY));
    }
}
