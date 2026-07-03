using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ParameterRadarChartView : MaskableGraphic
{
    [SerializeField] private float maxValue = 40f;
    [SerializeField] private int gridSteps = 4;
    [SerializeField] private Color gridColor = new Color(1f, 1f, 1f, 0.18f);
    [SerializeField] private Color axisColor = new Color(1f, 1f, 1f, 0.28f);
    [SerializeField] private Color fillColor = new Color(0.25f, 0.65f, 1f, 0.35f);
    [SerializeField] private Color lineColor = new Color(0.25f, 0.85f, 1f, 0.95f);
    [SerializeField] private float lineThickness = 2f;
    [SerializeField] private float labelRadiusPadding = 16f;
    [SerializeField] private Transform labelContainer;
    [SerializeField] private TMP_Text labelPrefab;
    [SerializeField] private bool showLabels = true;
    [SerializeField] private bool animateValues = true;
    [SerializeField] private float animationDuration = 0.45f;

    private readonly List<AxisValue> axes = new List<AxisValue>();
    private readonly List<TMP_Text> labels = new List<TMP_Text>();
    private float animationProgress = 1f;
    private float animationElapsed;
    private bool animationPlaying;

    protected override void Awake()
    {
        base.Awake();
        raycastTarget = false;
    }

#if UNITY_EDITOR
    protected override void OnValidate()
    {
        base.OnValidate();
        maxValue = Mathf.Max(1f, maxValue);
        gridSteps = Mathf.Max(1, gridSteps);
        lineThickness = Mathf.Max(0.5f, lineThickness);
        animationDuration = Mathf.Max(0.01f, animationDuration);
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

        Vector2 center = rectTransform.rect.center;
        float radius = Mathf.Min(rectTransform.rect.width, rectTransform.rect.height) * 0.5f - labelRadiusPadding;
        if (radius <= 1f)
        {
            return;
        }

        DrawGrid(vh, center, radius, axisCount);
        DrawAxes(vh, center, radius, axisCount);
        DrawData(vh, center, radius, axisCount);
    }

    private void DrawGrid(VertexHelper vh, Vector2 center, float radius, int axisCount)
    {
        for (int step = 1; step <= gridSteps; step++)
        {
            float stepRadius = radius * step / gridSteps;
            Vector2[] points = BuildRegularPoints(center, stepRadius, axisCount);
            AddPolyline(vh, points, gridColor, lineThickness * 0.5f, true);
        }
    }

    private void DrawAxes(VertexHelper vh, Vector2 center, float radius, int axisCount)
    {
        for (int i = 0; i < axisCount; i++)
        {
            AddLine(vh, center, GetPoint(center, radius, i, axisCount), axisColor, lineThickness * 0.5f);
        }
    }

    private void DrawData(VertexHelper vh, Vector2 center, float radius, int axisCount)
    {
        Vector2[] points = new Vector2[axisCount];
        for (int i = 0; i < axisCount; i++)
        {
            float normalized = Mathf.Clamp01((axes[i].Value * animationProgress) / maxValue);
            points[i] = GetPoint(center, radius * normalized, i, axisCount);
        }

        AddFilledPolygon(vh, center, points, fillColor);
        AddPolyline(vh, points, lineColor, lineThickness, true);
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
        float angle = Mathf.PI * 0.5f - (Mathf.PI * 2f * index / axisCount);
        return center + new Vector2(Mathf.Cos(angle), Mathf.Sin(angle)) * radius;
    }

    private void AddFilledPolygon(VertexHelper vh, Vector2 center, Vector2[] points, Color fill)
    {
        if (points.Length < 3)
        {
            return;
        }

        int centerIndex = vh.currentVertCount;
        vh.AddVert(center, fill, Vector2.zero);

        for (int i = 0; i < points.Length; i++)
        {
            vh.AddVert(points[i], fill, Vector2.zero);
        }

        for (int i = 0; i < points.Length; i++)
        {
            int next = i == points.Length - 1 ? 1 : i + 2;
            vh.AddTriangle(centerIndex, i + 1, next);
        }
    }

    private void AddPolyline(VertexHelper vh, Vector2[] points, Color stroke, float thickness, bool closed)
    {
        for (int i = 0; i < points.Length - 1; i++)
        {
            AddLine(vh, points[i], points[i + 1], stroke, thickness);
        }

        if (closed && points.Length > 1)
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

    private void RebuildLabels()
    {
        ClearLabels();

        if (!showLabels || labelContainer == null || labelPrefab == null || axes.Count == 0)
        {
            return;
        }

        Rect rect = rectTransform.rect;
        Vector2 center = rect.center;
        float radius = Mathf.Min(rect.width, rect.height) * 0.5f;
        int axisCount = axes.Count;

        for (int i = 0; i < axisCount; i++)
        {
            TMP_Text label = Instantiate(labelPrefab, labelContainer);
            label.text = ParameterScoreBarView.FormatLabel(axes[i].Key);
            label.raycastTarget = false;

            RectTransform labelRect = label.rectTransform;
            labelRect.anchoredPosition = GetPoint(center, radius, i, axisCount) - center;
            labels.Add(label);
        }
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
