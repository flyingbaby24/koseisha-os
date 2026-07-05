using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ParameterRadarChartView : MaskableGraphic
{
    [Header("Scale")]
    [SerializeField] private float maxValue = 40f;
    [SerializeField] private int gridSteps = 4;
    [SerializeField] private float labelRadiusPadding = 16f;
    [SerializeField] private bool animateValues = true;
    [SerializeField] private float animationDuration = 0.45f;

    [Header("Style")]
    [SerializeField] private Color gridColor = new Color(1f, 1f, 1f, 0.18f);
    [SerializeField] private Color axisColor = new Color(1f, 1f, 1f, 0.28f);
    [SerializeField] private Color fillColor = new Color(0.25f, 0.65f, 1f, 0.42f);
    [SerializeField] private Color lineColor = new Color(0.25f, 0.85f, 1f, 0.95f);
    [SerializeField] private float lineThickness = 2f;
    [Range(0f, 1f)]
    [SerializeField] private float fillAlpha = 0.46f;
    [SerializeField] private float vertexRadius = 3f;

    [Header("Vertex Labels")]
    [SerializeField] private bool showLabels = true;
    [SerializeField] private bool enableVertexLabels = true;
    [SerializeField] private bool showCategoryLabels = true;
    [SerializeField] private bool showRankLabels = true;
    [SerializeField] private float labelRadiusOffset = 36f;
    [SerializeField] private int labelFontSize = 16;
    [SerializeField] private Transform labelContainer;
    [SerializeField] private TMP_Text labelPrefab;

    private readonly List<AxisValue> axes = new List<AxisValue>();
    private readonly List<TMP_Text> labels = new List<TMP_Text>();
    private float animationProgress = 1f;
    private float animationElapsed;
    private bool animationPlaying;

    protected override void Awake()
    {
        base.Awake();
        raycastTarget = false;
        Sanitize2DState();
    }

    protected override void OnEnable()
    {
        base.OnEnable();
        Sanitize2DState();
    }

#if UNITY_EDITOR
    protected override void OnValidate()
    {
        base.OnValidate();
        maxValue = Mathf.Max(1f, maxValue);
        gridSteps = Mathf.Max(1, gridSteps);
        lineThickness = Mathf.Max(0.5f, lineThickness);
        vertexRadius = Mathf.Max(0f, vertexRadius);
        animationDuration = Mathf.Max(0.01f, animationDuration);
        labelRadiusOffset = Mathf.Max(0f, labelRadiusOffset);
        labelFontSize = Mathf.Max(8, labelFontSize);
        fillAlpha = Mathf.Clamp01(fillAlpha);
        Sanitize2DState();
        SetVerticesDirty();
    }
#endif

    private void Update()
    {
        if (!animationPlaying)
        {
            return;
        }

        animationElapsed += Time.unscaledDeltaTime;
        float t = Mathf.Clamp01(animationElapsed / Mathf.Max(0.01f, animationDuration));
        animationProgress = 1f - Mathf.Pow(1f - t, 3f);
        SetVerticesDirty();

        if (t >= 1f)
        {
            animationPlaying = false;
            animationProgress = 1f;
            SetVerticesDirty();
        }
    }

    public void Set3DMotionEnabled(bool value)
    {
        SetHologramStyleEnabled(value);
    }

    public void SetHologramStyleEnabled(bool value)
    {
        Sanitize2DState();
        SetVerticesDirty();
    }

    public void SetChartColors(Color line, Color fill)
    {
        lineColor = line;
        fillColor = fill;
        RebuildLabels();
        SetVerticesDirty();
    }

    public void Clear()
    {
        animationPlaying = false;
        animationProgress = 1f;
        axes.Clear();
        ClearLabels();
        SetVerticesDirty();
    }

    public void Show(ThoughtMapParameterScore[] scores)
    {
        ShowScores(scores);
    }

    public void ShowScores(ThoughtMapParameterScore[] scores)
    {
        axes.Clear();

        if (scores == null || scores.Length == 0)
        {
            Clear();
            return;
        }

        foreach (ThoughtMapParameterScore score in scores)
        {
            if (score == null || string.IsNullOrWhiteSpace(score.key))
            {
                continue;
            }

            axes.Add(new AxisValue(score.key, Mathf.Max(0f, score.value)));
        }

        if (axes.Count == 0)
        {
            Clear();
            return;
        }

        RebuildLabels();
        StartValueAnimation();
        SetVerticesDirty();
    }

    protected override void OnPopulateMesh(VertexHelper vh)
    {
        vh.Clear();

        int axisCount = axes.Count;
        if (axisCount < 3)
        {
            return;
        }

        Rect rect = rectTransform.rect;
        Vector2 center = rect.center;
        float radius = GetRadarRadius(rect);
        if (radius <= 1f)
        {
            return;
        }

        DrawGrid(vh, center, radius, axisCount);
        DrawAxes(vh, center, radius, axisCount);
        DrawFilledPolygon(vh, center, radius, axisCount);
        DrawOutline(vh, center, radius, axisCount);
        DrawVertices(vh, center, radius, axisCount);
    }

    private void DrawGrid(VertexHelper vh, Vector2 center, float radius, int axisCount)
    {
        for (int step = 1; step <= gridSteps; step++)
        {
            float stepRadius = radius * step / gridSteps;
            AddPolyline(vh, BuildRegularPoints(center, stepRadius, axisCount), gridColor, lineThickness * 0.5f, true);
        }
    }

    private void DrawAxes(VertexHelper vh, Vector2 center, float radius, int axisCount)
    {
        for (int i = 0; i < axisCount; i++)
        {
            AddLine(vh, center, GetPoint(center, radius, i, axisCount), axisColor, lineThickness * 0.5f);
        }
    }

    private void DrawFilledPolygon(VertexHelper vh, Vector2 center, float radius, int axisCount)
    {
        Vector2[] points = BuildDataPoints(center, radius, axisCount);
        AddFilledPolygon(vh, points, GetDataFillColor());
    }

    private void DrawOutline(VertexHelper vh, Vector2 center, float radius, int axisCount)
    {
        Vector2[] points = BuildDataPoints(center, radius, axisCount);
        AddPolyline(vh, points, GetDataLineColor(), lineThickness, true);
    }

    private void DrawVertices(VertexHelper vh, Vector2 center, float radius, int axisCount)
    {
        if (vertexRadius <= 0f)
        {
            return;
        }

        Vector2[] points = BuildDataPoints(center, radius, axisCount);
        Color vertexColor = GetDataLineColor();
        for (int i = 0; i < points.Length; i++)
        {
            AddFilledEllipse(vh, points[i], vertexRadius, vertexRadius, vertexColor, 0f);
        }
    }

    private Vector2[] BuildDataPoints(Vector2 center, float radius, int axisCount)
    {
        Vector2[] points = new Vector2[axisCount];
        for (int i = 0; i < axisCount; i++)
        {
            float normalized = Mathf.Clamp01((axes[i].Value * animationProgress) / maxValue);
            points[i] = GetPoint(center, radius * normalized, i, axisCount);
        }
        return points;
    }

    private Vector2[] BuildRegularPoints(Vector2 center, float radius, int axisCount)
    {
        Vector2[] points = new Vector2[axisCount];
        for (int i = 0; i < axisCount; i++)
        {
            points[i] = GetPoint(center, radius, i, axisCount);
        }
        return points;
    }

    private Vector2 GetPoint(Vector2 center, float radius, int index, int axisCount)
    {
        float angle = Mathf.PI * 0.5f - Mathf.PI * 2f * index / axisCount;
        return center + new Vector2(Mathf.Cos(angle), Mathf.Sin(angle)) * radius;
    }

    private float GetRadarRadius(Rect rect)
    {
        return Mathf.Max(1f, Mathf.Min(rect.width, rect.height) * 0.5f - labelRadiusPadding - labelRadiusOffset * 0.45f);
    }

    private Color GetDataFillColor()
    {
        Color color = fillColor;
        color.a = Mathf.Clamp01(fillAlpha);
        return color;
    }

    private Color GetDataLineColor()
    {
        Color color = lineColor;
        color.a = Mathf.Clamp01(Mathf.Max(color.a, 0.85f));
        return color;
    }

    private void StartValueAnimation()
    {
        if (!animateValues)
        {
            animationPlaying = false;
            animationProgress = 1f;
            return;
        }

        animationElapsed = 0f;
        animationProgress = 0f;
        animationPlaying = true;
    }

    private void AddFilledPolygon(VertexHelper vh, Vector2[] points, Color fill)
    {
        if (points == null || points.Length < 3 || fill.a <= 0f)
        {
            return;
        }

        List<int> triangles = TriangulatePolygon(points);
        if (triangles.Count < 3)
        {
            return;
        }

        int startIndex = vh.currentVertCount;
        for (int i = 0; i < points.Length; i++)
        {
            vh.AddVert(points[i], fill, Vector2.zero);
        }

        for (int i = 0; i < triangles.Count; i += 3)
        {
            vh.AddTriangle(startIndex + triangles[i], startIndex + triangles[i + 1], startIndex + triangles[i + 2]);
        }
    }

    private List<int> TriangulatePolygon(Vector2[] points)
    {
        List<int> triangles = new List<int>();
        if (points == null || points.Length < 3)
        {
            return triangles;
        }

        List<int> indices = new List<int>();
        for (int i = 0; i < points.Length; i++)
        {
            indices.Add(i);
        }

        bool clockwise = SignedArea(points) < 0f;
        int guard = points.Length * points.Length;

        while (indices.Count > 3 && guard-- > 0)
        {
            bool clippedEar = false;
            for (int i = 0; i < indices.Count; i++)
            {
                int previousIndex = indices[(i - 1 + indices.Count) % indices.Count];
                int currentIndex = indices[i];
                int nextIndex = indices[(i + 1) % indices.Count];

                if (!IsConvex(points[previousIndex], points[currentIndex], points[nextIndex], clockwise))
                {
                    continue;
                }

                bool containsPoint = false;
                for (int j = 0; j < indices.Count; j++)
                {
                    int testIndex = indices[j];
                    if (testIndex == previousIndex || testIndex == currentIndex || testIndex == nextIndex)
                    {
                        continue;
                    }

                    if (PointInTriangle(points[testIndex], points[previousIndex], points[currentIndex], points[nextIndex]))
                    {
                        containsPoint = true;
                        break;
                    }
                }

                if (containsPoint)
                {
                    continue;
                }

                triangles.Add(previousIndex);
                triangles.Add(currentIndex);
                triangles.Add(nextIndex);
                indices.RemoveAt(i);
                clippedEar = true;
                break;
            }

            if (!clippedEar)
            {
                triangles.Clear();
                return triangles;
            }
        }

        if (indices.Count == 3)
        {
            triangles.Add(indices[0]);
            triangles.Add(indices[1]);
            triangles.Add(indices[2]);
        }

        return triangles;
    }

    private float SignedArea(Vector2[] points)
    {
        float area = 0f;
        for (int i = 0; i < points.Length; i++)
        {
            Vector2 current = points[i];
            Vector2 next = points[(i + 1) % points.Length];
            area += current.x * next.y - next.x * current.y;
        }
        return area * 0.5f;
    }

    private bool IsConvex(Vector2 a, Vector2 b, Vector2 c, bool clockwise)
    {
        float cross = Cross(b - a, c - b);
        return clockwise ? cross < 0f : cross > 0f;
    }

    private bool PointInTriangle(Vector2 point, Vector2 a, Vector2 b, Vector2 c)
    {
        float d1 = Cross(point - b, a - b);
        float d2 = Cross(point - c, b - c);
        float d3 = Cross(point - a, c - a);
        bool hasNegative = d1 < 0f || d2 < 0f || d3 < 0f;
        bool hasPositive = d1 > 0f || d2 > 0f || d3 > 0f;
        return !(hasNegative && hasPositive);
    }

    private float Cross(Vector2 a, Vector2 b)
    {
        return a.x * b.y - a.y * b.x;
    }

    private void AddPolyline(VertexHelper vh, Vector2[] points, Color stroke, float thickness, bool closed)
    {
        if (points == null || points.Length < 2)
        {
            return;
        }

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
        const int segments = 24;
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

    private string FormatRank(float value)
    {
        if (value >= 40f) return "S";
        if (value >= 30f) return "A";
        if (value >= 20f) return "B";
        if (value >= 10f) return "C";
        return "D";
    }

    private string FormatVertexLabel(AxisValue axis)
    {
        if (showCategoryLabels && showRankLabels)
        {
            return $"{ParameterScoreBarView.FormatLabel(axis.Key)}\n{FormatRank(axis.Value)}";
        }

        if (showCategoryLabels)
        {
            return ParameterScoreBarView.FormatLabel(axis.Key);
        }

        if (showRankLabels)
        {
            return FormatRank(axis.Value);
        }

        return string.Empty;
    }

    private void RebuildLabels()
    {
        ClearLabels();

        if (!showLabels || !enableVertexLabels || axes.Count == 0 || (!showCategoryLabels && !showRankLabels))
        {
            return;
        }

        EnsureLabelContainer();
        Rect rect = rectTransform.rect;
        Vector2 center = rect.center;
        float radius = GetRadarRadius(rect) + labelRadiusOffset;
        int axisCount = axes.Count;

        for (int i = 0; i < axisCount; i++)
        {
            TMP_Text label = CreateLabel();
            label.text = FormatVertexLabel(axes[i]);
            label.raycastTarget = false;
            label.fontSize = labelFontSize;
            label.color = GetLabelColor();
            label.alignment = TextAlignmentOptions.Center;
            label.enableWordWrapping = false;
            label.overflowMode = TextOverflowModes.Overflow;

            RectTransform labelRect = label.rectTransform;
            labelRect.sizeDelta = new Vector2(150f, 54f);
            labelRect.localRotation = Quaternion.identity;
            labelRect.localScale = Vector3.one;
            labelRect.anchoredPosition = GetPoint(center, radius, i, axisCount) - rect.center;
            labels.Add(label);
        }
    }

    private void EnsureLabelContainer()
    {
        if (labelContainer != null)
        {
            return;
        }

        GameObject container = new GameObject("VertexLabelContainer", typeof(RectTransform));
        RectTransform rect = container.GetComponent<RectTransform>();
        rect.SetParent(transform, false);
        rect.anchorMin = Vector2.zero;
        rect.anchorMax = Vector2.one;
        rect.offsetMin = Vector2.zero;
        rect.offsetMax = Vector2.zero;
        labelContainer = rect;
    }

    private TMP_Text CreateLabel()
    {
        if (labelPrefab != null)
        {
            return Instantiate(labelPrefab, labelContainer);
        }

        GameObject labelObject = new GameObject("VertexLabel", typeof(RectTransform), typeof(CanvasRenderer), typeof(TextMeshProUGUI));
        RectTransform rect = labelObject.GetComponent<RectTransform>();
        rect.SetParent(labelContainer, false);
        TMP_Text label = labelObject.GetComponent<TMP_Text>();
        label.raycastTarget = false;
        return label;
    }

    private Color GetLabelColor()
    {
        Color color = lineColor;
        color.a = Mathf.Clamp01(Mathf.Max(color.a, 0.92f));
        return color;
    }

    private void ClearLabels()
    {
        for (int i = labels.Count - 1; i >= 0; i--)
        {
            if (labels[i] != null)
            {
                Destroy(labels[i].gameObject);
            }
        }
        labels.Clear();
    }

    private void Sanitize2DState()
    {
        rectTransform.localRotation = Quaternion.identity;
        transform.localRotation = Quaternion.identity;
    }

    private readonly struct AxisValue
    {
        public AxisValue(string key, float value)
        {
            Key = key;
            Value = value;
        }

        public string Key { get; }
        public float Value { get; }
    }
}
