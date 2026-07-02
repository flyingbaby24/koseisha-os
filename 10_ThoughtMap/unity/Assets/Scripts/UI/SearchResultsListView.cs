using System;
using UnityEngine;

public class SearchResultsListView : MonoBehaviour
{
    [SerializeField] private Transform resultsContent;
    [SerializeField] private ResultItemView resultItemPrefab;

    public event Action<ThoughtMapSearchResult> ResultSelected;

    public void ShowResults(ThoughtMapSearchResult[] results)
    {
        Clear();

        if (results == null || resultsContent == null || resultItemPrefab == null)
        {
            return;
        }

        foreach (ThoughtMapSearchResult result in results)
        {
            ResultItemView item = Instantiate(resultItemPrefab, resultsContent);
            item.Bind(result, HandleResultSelected);
        }
    }

    public void Clear()
    {
        if (resultsContent == null)
        {
            return;
        }

        for (int i = resultsContent.childCount - 1; i >= 0; i--)
        {
            Destroy(resultsContent.GetChild(i).gameObject);
        }
    }

    private void HandleResultSelected(ThoughtMapSearchResult result)
    {
        ResultSelected?.Invoke(result);
    }
}
