using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

[DisallowMultipleComponent]
public class NeonHoverGlow : MonoBehaviour, IPointerEnterHandler, IPointerExitHandler, IPointerDownHandler, IPointerUpHandler
{
    [SerializeField] private Image targetImage;
    [SerializeField] private Outline outline;
    [SerializeField] private Color normalColor = new Color(0.018f, 0.05f, 0.11f, 0.96f);
    [SerializeField] private Color hoverColor = new Color(0.03f, 0.16f, 0.30f, 1f);
    [SerializeField] private Color pressedColor = new Color(0.05f, 0.28f, 0.48f, 1f);
    [SerializeField] private Color normalGlow = new Color(0.05f, 0.42f, 0.75f, 0.55f);
    [SerializeField] private Color hoverGlow = new Color(0.05f, 0.82f, 1f, 1f);
    [SerializeField] private float transitionSpeed = 12f;
    [SerializeField] private Vector2 normalDistance = new Vector2(1.1f, -1.1f);
    [SerializeField] private Vector2 hoverDistance = new Vector2(2.2f, -2.2f);

    private Color imageTarget;
    private Color outlineTarget;
    private Vector2 distanceTarget;

    private void Awake()
    {
        if (targetImage == null)
        {
            targetImage = GetComponent<Image>();
        }

        if (outline == null)
        {
            outline = GetComponent<Outline>();
        }

        if (outline == null)
        {
            outline = gameObject.AddComponent<Outline>();
        }

        imageTarget = normalColor;
        outlineTarget = normalGlow;
        distanceTarget = normalDistance;
        ApplyImmediate();
    }

    private void Update()
    {
        float t = 1f - Mathf.Exp(-transitionSpeed * Time.unscaledDeltaTime);
        if (targetImage != null)
        {
            targetImage.color = Color.Lerp(targetImage.color, imageTarget, t);
        }

        if (outline != null)
        {
            outline.effectColor = Color.Lerp(outline.effectColor, outlineTarget, t);
            outline.effectDistance = Vector2.Lerp(outline.effectDistance, distanceTarget, t);
        }
    }

    public void OnPointerEnter(PointerEventData eventData)
    {
        imageTarget = hoverColor;
        outlineTarget = hoverGlow;
        distanceTarget = hoverDistance;
    }

    public void OnPointerExit(PointerEventData eventData)
    {
        imageTarget = normalColor;
        outlineTarget = normalGlow;
        distanceTarget = normalDistance;
    }

    public void OnPointerDown(PointerEventData eventData)
    {
        imageTarget = pressedColor;
        outlineTarget = hoverGlow;
        distanceTarget = hoverDistance * 1.25f;
    }

    public void OnPointerUp(PointerEventData eventData)
    {
        OnPointerEnter(eventData);
    }

    private void ApplyImmediate()
    {
        if (targetImage != null)
        {
            targetImage.color = imageTarget;
        }

        if (outline != null)
        {
            outline.effectColor = outlineTarget;
            outline.effectDistance = distanceTarget;
            outline.useGraphicAlpha = true;
        }
    }
}
