using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ParameterRadarChartView : MaskableGraphic
{
    private static readonly string[] ParameterOrder =
    {
        "philosophy",
        "psychology",
        "science",
        "economics",
        "karma",
        "emotion",
        "morality",
        "ideal",
        "individual",
        "community"
    };

    [SerializeField] private float maxValue = 100f;
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

    private readonly Dictionary<string, float> valuesByKey = new Dictionary<string, float>();
    private readonly List<TMP_Text> labels = new List<TMP_Text>();

    protected override void Awake()
    {
        base.Awake();
        raycastTarget = false;
        RebuildLabels();
    }

    protected override void OnEnable()
    {
        base.OnEnable();
        RebuildLabels();
    }

#if UNITY_EDITOR
    protected override void OnValidate()
    {
        base.OnValidate();
        maxValue = Mathf.Max(1f, maxValue);
        gridSteps = Mathf.Max(1, gridSteps);
        lineThickness = Mathf.Max(0.5f, lineThickness);
        SetVerticesDirty();
    }
#endif

    public void Clear()
    {
        valuesByKey.Clear();
        SetVerticesDirty();
    }

    public void Show(ThoughtMapParameterScore[] scores)
    {
        ShowScores(scores);
    }

    public void ShowScores(ThoughtMapParameterScore[] scores)
    {
        valuesByKey.Clear();

        if (scores != null)
        {
            foreach (ThoughtMapParameterScore score in scores)
            {
                if (score == null || string.IsNullOrWhiteSpace(score.key))
                {
                    continue;
                }

                valuesByKey[NormalizeKey(score.key)] = Mathf.Clamp(score.value, 0f, maxValue);
            }
        }

        RebuildLabels();
        SetVerticesDirty();
    }

    protected override void OnPopulateMesh(VertexHelper vh)
    {
        vh.Clear();

        Vector2 center = rectTransform.rect.center;
        float radius = Mathf.Min(rectTransform.rect.width, rectTransform.rect.height) * 0.5f - labelRadiusPadding;
        if (radius <= 1f)
        {
            return;
        }

        DrawGrid(vh, center, radius);
        DrawAxes(vh, center, radius);
        DrawData(vh, center, radius);
    }

    private void DrawGrid(VertexHelper vh, Vector2 center, float radius)
    {
        for (int step = 1; step <= gridSteps; step++)
        {
            float stepRadius = radius * step / gridSteps;
            Vector2[] points = BuildRegularPoints(center, stepRadius);
            AddPolyline(vh, points, gridColor, lineThickness * 0.5f, true);
        }
    }

    private void DrawAxes(VertexHelper vh, Vector2 center, float radius)
    {
        for (int i = 0; i < ParameterOrder.Length; i++)
        {
            AddLine(vh, center, GetPoint(center, radius, i), axisColor, lineThickness * 0.5f);
        }
    }

    private void DrawData(VertexHelper vh, Vector2 center, float radius)
    {
        Vector2[] points = new Vector2[ParameterOrder.Length];
        for (int i = 0; i < ParameterOrder.Length; i++)
        {
            float value = valuesByKey.TryGetValue(ParameterOrder[i], out float found) ? found : 0f;
            float normalized = Mathf.Clamp01(value / maxValue);
            points[i] = GetPoint(center, radius * normalized, i);
        }

        AddFilledPolygon(vh, center, points, fillColor);
        AddPolyline(vh, points, lineColor, lineThickness, true);
    }

    private Vector2[] BuildRegularPoints(Vector2 center, float radius)
    {
        Vector2[] points = new Vector2[ParameterOrder.Length];
        for (int i = 0; i < ParameterOrder.Length; i++)
        {
            points[i] = GetPoint(center, radius, i);
        }
        return points;
    }

    private Vector2 GetPoint(Vector2 center, float radius, int index)
    {
        float angle = Mathf.PI * 0.5f - (Mathf.PI * 2f * index / ParameterOrder.Length);
        return center + new Vector2(Mathf.Cos(angle), Mathf.Sin(angle)) * radius;
    }

    private void AddFilledPolygon(VertexHelper vh, Vector2 center, Vector2[] points, Color fill)
    {
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
        if (!showLabels || labelContainer == null || labelPrefab == null)
        {
            return;
        }

        ClearLabels();
        Rect rect = rectTransform.rect;
        Vector2 center = rect.center;
        float radius = Mathf.Min(rect.width, rect.height) * 0.5f;

        for (int i = 0; i < ParameterOrder.Length; i++)
        {
            TMP_Text label = Instantiate(labelPrefab, labelContainer);
            label.text = ParameterScoreBarView.FormatLabel(ParameterOrder[i]);
            label.raycastTarget = false;

            RectTransform labelRect = label.rectTransform;
            labelRect.anchoredPosition = GetPoint(center, radius, i) - center;
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

    private string NormalizeKey(string key)
    {
        return string.IsNullOrWhiteSpace(key) ? string.Empty : key.Trim().ToLowerInvariant();
    }
}
