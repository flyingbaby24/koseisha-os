using UnityEngine;

[DisallowMultipleComponent]
public class NeonSlideIn : MonoBehaviour
{
    [SerializeField] private RectTransform target;
    [SerializeField] private CanvasGroup canvasGroup;
    [SerializeField] private Vector2 offset = new Vector2(32f, 0f);
    [SerializeField] private float duration = 0.24f;
    [SerializeField] private bool fade = true;

    private Vector2 basePosition;
    private float elapsed;
    private bool initialized;
    private bool playing;

    private void Awake()
    {
        Initialize();
    }

    private void OnEnable()
    {
        Initialize();
    }

    private void Update()
    {
        if (!playing || target == null)
        {
            return;
        }

        elapsed += Time.unscaledDeltaTime;
        float t = Mathf.Clamp01(elapsed / Mathf.Max(0.01f, duration));
        float eased = 1f - Mathf.Pow(1f - t, 3f);
        target.anchoredPosition = Vector2.LerpUnclamped(basePosition + offset, basePosition, eased);

        if (fade && canvasGroup != null)
        {
            canvasGroup.alpha = eased;
        }

        if (t >= 1f)
        {
            playing = false;
            target.anchoredPosition = basePosition;
            if (canvasGroup != null)
            {
                canvasGroup.alpha = 1f;
            }
        }
    }

    public void Play()
    {
        Initialize();
        if (target == null)
        {
            return;
        }

        elapsed = 0f;
        playing = true;
        target.anchoredPosition = basePosition + offset;
        if (fade && canvasGroup != null)
        {
            canvasGroup.alpha = 0f;
        }
    }

    private void Initialize()
    {
        if (initialized)
        {
            return;
        }

        if (target == null)
        {
            target = transform as RectTransform;
        }

        if (canvasGroup == null)
        {
            canvasGroup = GetComponent<CanvasGroup>();
        }

        if (fade && canvasGroup == null)
        {
            canvasGroup = gameObject.AddComponent<CanvasGroup>();
        }

        if (target != null)
        {
            basePosition = target.anchoredPosition;
        }

        initialized = true;
    }
}
