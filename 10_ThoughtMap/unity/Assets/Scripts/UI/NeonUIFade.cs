using UnityEngine;

[DisallowMultipleComponent]
public class NeonUIFade : MonoBehaviour
{
    [SerializeField] private CanvasGroup canvasGroup;
    [SerializeField] private float duration = 0.22f;
    [SerializeField] private float delay = 0f;
    [SerializeField] private bool playOnEnable = false;

    private float elapsed;
    private bool playing;

    private void Awake()
    {
        EnsureCanvasGroup();
    }

    private void OnEnable()
    {
        if (playOnEnable)
        {
            Play(delay);
        }
    }

    private void Update()
    {
        if (!playing || canvasGroup == null)
        {
            return;
        }

        elapsed += Time.unscaledDeltaTime;
        float t = Mathf.Clamp01((elapsed - delay) / Mathf.Max(0.01f, duration));
        canvasGroup.alpha = Smooth(t);

        if (t >= 1f)
        {
            playing = false;
            canvasGroup.alpha = 1f;
        }
    }

    public void Play(float startDelay = 0f)
    {
        EnsureCanvasGroup();
        delay = Mathf.Max(0f, startDelay);
        elapsed = 0f;
        playing = true;

        if (canvasGroup != null)
        {
            canvasGroup.alpha = 0f;
        }
    }

    private void EnsureCanvasGroup()
    {
        if (canvasGroup == null)
        {
            canvasGroup = GetComponent<CanvasGroup>();
        }

        if (canvasGroup == null)
        {
            canvasGroup = gameObject.AddComponent<CanvasGroup>();
        }
    }

    private float Smooth(float t)
    {
        return t * t * (3f - 2f * t);
    }
}
