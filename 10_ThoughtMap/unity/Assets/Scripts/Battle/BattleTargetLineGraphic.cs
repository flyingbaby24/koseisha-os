using UnityEngine;
using UnityEngine.UI;

public sealed class BattleTargetLineGraphic : Graphic
{
    private Vector2 start;
    private Vector2 end;
    private float width = 4f;

    public void Show(RectTransform from, RectTransform to, Color lineColor)
    {
        if (from == null || to == null) { Hide(); return; }
        RectTransform rect = transform as RectTransform;
        Canvas canvas = GetComponentInParent<Canvas>();
        Camera camera = canvas != null && canvas.renderMode != RenderMode.ScreenSpaceOverlay ? canvas.worldCamera : null;
        RectTransformUtility.ScreenPointToLocalPointInRectangle(rect, RectTransformUtility.WorldToScreenPoint(camera, from.position), camera, out start);
        RectTransformUtility.ScreenPointToLocalPointInRectangle(rect, RectTransformUtility.WorldToScreenPoint(camera, to.position), camera, out end);
        color = lineColor;
        gameObject.SetActive(true);
        SetVerticesDirty();
    }

    public void Hide() { gameObject.SetActive(false); }

    protected override void OnPopulateMesh(VertexHelper vh)
    {
        vh.Clear();
        Vector2 direction = end - start;
        if (direction.sqrMagnitude < 0.1f) return;
        Vector2 normal = new Vector2(-direction.y, direction.x).normalized * width;
        UIVertex vertex = UIVertex.simpleVert; vertex.color = color;
        vertex.position = start - normal; vh.AddVert(vertex);
        vertex.position = start + normal; vh.AddVert(vertex);
        vertex.position = end + normal; vh.AddVert(vertex);
        vertex.position = end - normal; vh.AddVert(vertex);
        vh.AddTriangle(0, 1, 2); vh.AddTriangle(0, 2, 3);
    }
}
