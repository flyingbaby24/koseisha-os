using UnityEngine;
using UnityEngine.UI;

[DisallowMultipleComponent]
public class NeonPanelPulse : MonoBehaviour
{
    [SerializeField] private Outline outline;
    [SerializeField] private Color glowColor = new Color(0.05f, 0.78f, 1f, 0.58f);
    [SerializeField] private Color dimColor = new Color(0.05f, 0.32f, 0.58f, 0.25f);
    [SerializeField] private float speed = 1.35f;
    [SerializeField] private Vector2 minDistance = new Vector2(0.8f, -0.8f);
    [SerializeField] private Vector2 maxDistance = new Vector2(1.8f, -1.8f);

    private void Awake()
    {
        if (outline == null)
        {
            outline = GetComponent<Outline>();
        }

        if (outline == null)
        {
            outline = gameObject.AddComponent<Outline>();
        }
    }

    private void Update()
    {
        if (outline == null)
        {
            return;
        }

        float t = (Mathf.Sin(Time.unscaledTime * speed) + 1f) * 0.5f;
        outline.effectColor = Color.Lerp(dimColor, glowColor, t);
        outline.effectDistance = Vector2.Lerp(minDistance, maxDistance, t);
        outline.useGraphicAlpha = true;
    }
}
