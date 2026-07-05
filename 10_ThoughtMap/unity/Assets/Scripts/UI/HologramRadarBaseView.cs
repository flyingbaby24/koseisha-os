using UnityEngine;
using UnityEngine.UI;

public class HologramRadarBaseView : MaskableGraphic
{
    [SerializeField] private bool enableBaseRings = true;
    [SerializeField] private int ringCount = 5;
    [SerializeField] private Color ringColor = new Color(0.25f, 0.85f, 1f, 0.28f);
    [SerializeField] private Color glowColor = new Color(0.25f, 0.65f, 1f, 0.08f);
    [SerializeField] private float ringRotationSpeed = 0.15f;
    [SerializeField] private float lineThickness = 1.2f;
    [SerializeField] private float baseYOffset = -0.34f;
    [SerializeField] private float baseWidthScale = 1.45f;
    [SerializeField] private float baseHeightScale = 0.18f;

    private float elapsed;

    protected override void Awake()
    {
        base.Awake();
        raycastTarget = false;
    }

#if UNITY_EDITOR
    protected override void OnValidate()
    {
        base.OnValidate();
        ringCount = Mathf.Max(1, ringCount);
        ringRotationSpeed = Mathf.Max(0f, ringRotationSpeed);
        lineThickness = Mathf.Max(0.25f, lineThickness);
        baseWidthScale = Mathf.Max(0.1f, baseWidthScale);
        baseHeightScale = Mathf.Max(0.01f, baseHeightScale);
        SetVerticesDirty();
    }
#endif

    private void Update()
    {
        if (!enableBaseRings)
        {
            return;
        }

        elapsed += Time.unscaledDeltaTime;
        SetVerticesDirty();
    }

    public void SetColors(Color line, Color fill)
    {
        ringColor = line;
        glowColor = fill;
        SetVerticesDirty();
    }

    protected override void OnPopulateMesh(VertexHelper vh)
    {
        vh.Clear();

        if (!enableBaseRings)
        {
            return;
        }

        Rect rect = rectTransform.rect;
        Vector2 center = rect.center;
        float radius = Mathf.Min(rect.width, rect.height) * 0.5f;
        float baseY = center.y + rect.height * baseYOffset;
        Vector2 baseCenter = new Vector2(center.x, baseY);
        float phase = elapsed * ringRotationSpeed * Mathf.Deg2Rad;

        AddFilledEllipse(vh, baseCenter, radius * 0.38f, radius * 0.06f, WithAlpha(glowColor, glowColor.a), phase);

        for (int i = ringCount - 1; i >= 0; i--)
        {
            float t = ringCount <= 1 ? 0f : i / (float)(ringCount - 1);
            float width = radius * Mathf.Lerp(baseWidthScale, baseWidthScale * 0.42f, t);
            float height = radius * Mathf.Lerp(baseHeightScale, baseHeightScale * 0.34f, t);
            float y = baseY + radius * Mathf.Lerp(-0.01f, 0.10f, t);
            float alpha = Mathf.Lerp(0.06f, ringColor.a, 1f - t);
            float thickness = Mathf.Lerp(lineThickness * 0.45f, lineThickness, 1f - t);
            AddEllipsePolyline(vh, new Vector2(center.x, y), width, height, WithAlpha(ringColor, alpha), thickness, phase * Mathf.Lerp(0.15f, 0.45f, t + 0.1f));
        }
    }

    private void AddEllipsePolyline(VertexHelper vh, Vector2 center, float radiusX, float radiusY, Color stroke, float thickness, float phase)
    {
        const int segments = 72;
        Vector2[] points = new Vector2[segments];
        for (int i = 0; i < segments; i++)
        {
            float angle = phase + Mathf.PI * 2f * i / segments;
            points[i] = center + new Vector2(Mathf.Cos(angle) * radiusX, Mathf.Sin(angle) * radiusY);
        }
        AddPolyline(vh, points, stroke, thickness, true);
    }

    private void AddPolyline(VertexHelper vh, Vector2[] points, Color stroke, float thickness, bool closed)
    {
        for (int i = 0; i < points.Length - 1; i++)
        {
            AddLine(vh, points[i], points[i + 1], stroke, thickness);
        }

        if (closed)
        {
            AddLine(vh, points[points.Length - 1], points[0], stroke, thickness);
        }
    }

    private void AddLine(VertexHelper vh, Vector2 start, Vector2 end, Color stroke, float thickness)
    {
        Vector2 direction = (end - start).normalized;
        if (direction == Vector2.zero)
        {
            return;
        }

        Vector2 normal = new Vector2(-direction.y, direction.x) * (thickness * 0.5f);
        int index = vh.currentVertCount;
        vh.AddVert(start - normal, stroke, Vector2.zero);
        vh.AddVert(start + normal, stroke, Vector2.zero);
        vh.AddVert(end + normal, stroke, Vector2.zero);
        vh.AddVert(end - normal, stroke, Vector2.zero);
        vh.AddTriangle(index, index + 1, index + 2);
        vh.AddTriangle(index, index + 2, index + 3);
    }

    private void AddFilledEllipse(VertexHelper vh, Vector2 center, float radiusX, float radiusY, Color fill, float phase)
    {
        const int segments = 48;
        int centerIndex = vh.currentVertCount;
        vh.AddVert(center, fill, Vector2.zero);

        for (int i = 0; i < segments; i++)
        {
            float angle = phase + Mathf.PI * 2f * i / segments;
            Vector2 point = center + new Vector2(Mathf.Cos(angle) * radiusX, Mathf.Sin(angle) * radiusY);
            vh.AddVert(point, fill, Vector2.zero);
        }

        for (int i = 0; i < segments; i++)
        {
            int next = i == segments - 1 ? 1 : i + 2;
            vh.AddTriangle(centerIndex, i + 1, next);
        }
    }

    private Color WithAlpha(Color source, float alpha)
    {
        source.a = Mathf.Clamp01(alpha);
        return source;
    }
}
