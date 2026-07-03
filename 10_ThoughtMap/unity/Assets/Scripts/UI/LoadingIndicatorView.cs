using TMPro;
using UnityEngine;

public class LoadingIndicatorView : MonoBehaviour
{
    [SerializeField] private CanvasGroup canvasGroup;
    [SerializeField] private RectTransform spinner;
    [SerializeField] private TMP_Text statusText;
    [SerializeField] private string loadingText = "Searching...";
    [SerializeField] private float fadeSpeed = 12f;
    [SerializeField] private float rotationSpeed = 180f;

    private bool visible;

    private void Awake()
    {
        if (canvasGroup == null)
        {
            canvasGroup = GetComponent<CanvasGroup>();
        }

        if (canvasGroup == null)
        {
            canvasGroup = gameObject.AddComponent<CanvasGroup>();
        }

        HideImmediate();
    }

    private void Update()
    {
        if (spinner != null && visible)
        {
            spinner.Rotate(0f, 0f, -rotationSpeed * Time.unscaledDeltaTime);
        }

        if (canvasGroup != null)
        {
            float target = visible ? 1f : 0f;
            float t = 1f - Mathf.Exp(-fadeSpeed * Time.unscaledDeltaTime);
            canvasGroup.alpha = Mathf.Lerp(canvasGroup.alpha, target, t);
            canvasGroup.blocksRaycasts = visible;
            canvasGroup.interactable = visible;
        }
    }

    public void Show(string message = null)
    {
        visible = true;
        gameObject.SetActive(true);
        if (statusText != null)
        {
            statusText.text = string.IsNullOrWhiteSpace(message) ? loadingText : message;
        }
    }

    public void Hide()
    {
        visible = false;
    }

    public void HideImmediate()
    {
        visible = false;
        if (canvasGroup != null)
        {
            canvasGroup.alpha = 0f;
            canvasGroup.blocksRaycasts = false;
            canvasGroup.interactable = false;
        }
    }
}
