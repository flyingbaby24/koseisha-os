using System.Collections.Generic;
using TMPro;
using UnityEngine;

public class SpeedOrderView : MonoBehaviour
{
    [SerializeField] private Transform contentRoot;
    [SerializeField] private GameObject turnIconPrefab;

    public void RenderPreview(IEnumerable<string> unitLabels)
    {
        if (contentRoot == null || turnIconPrefab == null)
        {
            return;
        }

        Clear();
        if (unitLabels == null)
        {
            return;
        }

        foreach (string label in unitLabels)
        {
            GameObject icon = Instantiate(turnIconPrefab, contentRoot);
            icon.name = "TurnIcon";
            TMP_Text text = icon.GetComponentInChildren<TMP_Text>(true);
            if (text != null)
            {
                text.text = string.IsNullOrWhiteSpace(label) ? "?" : label;
            }
            icon.SetActive(true);
        }
    }

    private void Clear()
    {
        for (int i = contentRoot.childCount - 1; i >= 0; i--)
        {
            Destroy(contentRoot.GetChild(i).gameObject);
        }
    }
}
