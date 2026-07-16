using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class BattleCardView : MonoBehaviour
{
    [SerializeField] private Image cardImage;
    [SerializeField] private TMP_Text nameText;
    [SerializeField] private Image hpFillImage;
    [SerializeField] private Image spFillImage;
    [SerializeField] private Transform statusIconRoot;
    [SerializeField] private GameObject targetMarker;

    public void Bind(string displayName, Sprite sprite, float hp01, float sp01, bool isTarget)
    {
        EnsureReferences();

        if (cardImage != null)
        {
            cardImage.sprite = sprite;
            cardImage.enabled = sprite != null;
            cardImage.preserveAspect = true;
        }

        if (nameText != null)
        {
            nameText.text = string.IsNullOrWhiteSpace(displayName) ? "Unit" : displayName;
        }

        if (hpFillImage != null)
        {
            hpFillImage.fillAmount = Mathf.Clamp01(hp01);
        }

        if (spFillImage != null)
        {
            spFillImage.fillAmount = Mathf.Clamp01(sp01);
        }

        if (targetMarker != null)
        {
            targetMarker.SetActive(isTarget);
        }
    }

    public void SetTargetMarker(bool visible)
    {
        EnsureReferences();
        if (targetMarker != null)
        {
            targetMarker.SetActive(visible);
        }
    }

    public Transform StatusIconRoot
    {
        get
        {
            EnsureReferences();
            return statusIconRoot;
        }
    }

    private void Awake()
    {
        EnsureReferences();
    }

    private void EnsureReferences()
    {
        if (cardImage == null)
        {
            Transform found = transform.Find("Card Image");
            cardImage = found != null ? found.GetComponent<Image>() : null;
        }

        if (nameText == null)
        {
            Transform found = transform.Find("Name");
            nameText = found != null ? found.GetComponent<TMP_Text>() : null;
        }

        if (hpFillImage == null)
        {
            Transform found = transform.Find("HP Bar/Fill");
            hpFillImage = found != null ? found.GetComponent<Image>() : null;
        }

        if (spFillImage == null)
        {
            Transform found = transform.Find("SP Bar/Fill");
            spFillImage = found != null ? found.GetComponent<Image>() : null;
        }

        if (statusIconRoot == null)
        {
            Transform found = transform.Find("Status Icons");
            statusIconRoot = found;
        }

        if (targetMarker == null)
        {
            Transform found = transform.Find("Target Marker");
            targetMarker = found != null ? found.gameObject : null;
        }
    }
}
