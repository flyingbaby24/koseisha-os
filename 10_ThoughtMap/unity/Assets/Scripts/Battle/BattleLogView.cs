using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class BattleLogView : MonoBehaviour
{
    [SerializeField] private ScrollRect scrollRect;
    [SerializeField] private Transform contentRoot;
    [SerializeField] private TMP_Text rowPrefab;

    public void SetLines(IEnumerable<string> lines)
    {
        Clear();
        if (lines == null)
        {
            return;
        }

        foreach (string line in lines)
        {
            AddLine(line, false);
        }

        ScrollToBottom();
    }

    public void AddLine(string line)
    {
        AddLine(line, true);
    }

    private void AddLine(string line, bool scroll)
    {
        if (contentRoot == null || rowPrefab == null)
        {
            return;
        }

        TMP_Text row = Instantiate(rowPrefab, contentRoot);
        row.name = "BattleLogRow";
        row.text = string.IsNullOrWhiteSpace(line) ? "..." : line;
        row.gameObject.SetActive(true);

        if (scroll)
        {
            ScrollToBottom();
        }
    }

    private void Clear()
    {
        if (contentRoot == null)
        {
            return;
        }

        for (int i = contentRoot.childCount - 1; i >= 0; i--)
        {
            Destroy(contentRoot.GetChild(i).gameObject);
        }
    }

    private void ScrollToBottom()
    {
        Canvas.ForceUpdateCanvases();
        if (scrollRect != null)
        {
            scrollRect.verticalNormalizedPosition = 0f;
        }
    }
}
