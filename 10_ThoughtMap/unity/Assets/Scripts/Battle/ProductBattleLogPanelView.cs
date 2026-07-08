using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ProductBattleLogPanelView : MonoBehaviour
{
    [SerializeField] private GameObject contentRoot;
    [SerializeField] private TMP_Text logText;
    [SerializeField] private ScrollRect scrollRect;
    [SerializeField] private Button toggleButton;
    [SerializeField] private TMP_Text toggleButtonText;
    [SerializeField] private bool collapsed = true;

    private readonly StringBuilder builder = new StringBuilder();

    private void Awake()
    {
        if (toggleButton != null)
        {
            toggleButton.onClick.RemoveListener(Toggle);
            toggleButton.onClick.AddListener(Toggle);
        }
        ApplyCollapsed();
    }

    public void SetLog(string value)
    {
        builder.Clear();
        builder.Append(value);
        Render();
    }

    public void AppendLine(string value)
    {
        builder.AppendLine(value);
        Render();
    }

    public void Clear()
    {
        builder.Clear();
        Render();
    }

    public void SetCollapsed(bool value)
    {
        collapsed = value;
        ApplyCollapsed();
    }

    private void Toggle()
    {
        SetCollapsed(!collapsed);
    }

    private void Render()
    {
        if (logText != null)
        {
            logText.text = builder.ToString();
        }
        if (scrollRect != null)
        {
            Canvas.ForceUpdateCanvases();
            scrollRect.verticalNormalizedPosition = 0f;
        }
    }

    private void ApplyCollapsed()
    {
        if (contentRoot != null)
        {
            contentRoot.SetActive(!collapsed);
        }
        if (toggleButtonText != null)
        {
            toggleButtonText.text = collapsed ? "Show Debug" : "Hide Debug";
        }
    }
}
