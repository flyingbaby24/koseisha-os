using System.Collections;
using UnityEngine;

[DisallowMultipleComponent]
public class ThoughtMapWindowMotion : MonoBehaviour
{
    [Header("Motion")]
    [SerializeField] private bool playOnEnable = true;
    [SerializeField] private float showDuration = 0.22f;
    [SerializeField] private float hideDuration = 0.16f;
    [SerializeField] private float hiddenScale = 0.96f;
    [SerializeField] private float shownScale = 1f;
    [SerializeField] private bool useUnscaledTime = true;

    private CanvasGroup canvasGroup;
    private Coroutine activeRoutine;
    private Vector3 baseScale;

    private void Awake()
    {
        canvasGroup = GetComponent<CanvasGroup>();
        if (canvasGroup == null)
        {
            canvasGroup = gameObject.AddComponent<CanvasGroup>();
        }

        baseScale = transform.localScale == Vector3.zero ? Vector3.one : transform.localScale;
    }

    private void OnEnable()
    {
        if (playOnEnable)
        {
            Show();
        }
    }

    public void Show()
    {
        EnsureReady();
        gameObject.SetActive(true);
        StartMotion(0f, 1f, hiddenScale, shownScale, showDuration, false);
    }

    public void ShowImmediate()
    {
        EnsureReady();
        gameObject.SetActive(true);
        SetVisualState(1f, shownScale);
    }

    public void Hide()
    {
        EnsureReady();
        StartMotion(canvasGroup.alpha, 0f, shownScale, hiddenScale, hideDuration, true);
    }

    public void HideImmediate()
    {
        EnsureReady();
        SetVisualState(0f, hiddenScale);
        gameObject.SetActive(false);
    }

    private void StartMotion(float fromAlpha, float toAlpha, float fromScale, float toScale, float duration, bool deactivateAtEnd)
    {
        if (activeRoutine != null)
        {
            StopCoroutine(activeRoutine);
        }

        activeRoutine = StartCoroutine(PlayMotion(fromAlpha, toAlpha, fromScale, toScale, duration, deactivateAtEnd));
    }

    private IEnumerator PlayMotion(float fromAlpha, float toAlpha, float fromScale, float toScale, float duration, bool deactivateAtEnd)
    {
        float elapsed = 0f;
        float safeDuration = Mathf.Max(0.01f, duration);
        while (elapsed < safeDuration)
        {
            elapsed += useUnscaledTime ? Time.unscaledDeltaTime : Time.deltaTime;
            float t = Mathf.Clamp01(elapsed / safeDuration);
            float eased = 1f - Mathf.Pow(1f - t, 3f);
            SetVisualState(Mathf.Lerp(fromAlpha, toAlpha, eased), Mathf.Lerp(fromScale, toScale, eased));
            yield return null;
        }

        SetVisualState(toAlpha, toScale);
        if (deactivateAtEnd)
        {
            gameObject.SetActive(false);
        }

        activeRoutine = null;
    }

    private void SetVisualState(float alpha, float scale)
    {
        if (canvasGroup != null)
        {
            canvasGroup.alpha = alpha;
            canvasGroup.interactable = alpha > 0.95f;
            canvasGroup.blocksRaycasts = alpha > 0.05f;
        }

        transform.localScale = baseScale * scale;
    }

    private void EnsureReady()
    {
        if (canvasGroup == null)
        {
            canvasGroup = GetComponent<CanvasGroup>();
            if (canvasGroup == null)
            {
                canvasGroup = gameObject.AddComponent<CanvasGroup>();
            }
        }

        if (baseScale == Vector3.zero)
        {
            baseScale = transform.localScale == Vector3.zero ? Vector3.one : transform.localScale;
        }
    }
}
