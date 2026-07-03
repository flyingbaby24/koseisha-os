using System;
using UnityEngine;

public class SearchResultsListView : MonoBehaviour
{
    [SerializeField] private Transform resultsContent;
    [SerializeField] private ResultItemView resultItemPrefab;

    private ResultItemView selectedItem;

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
            item.Bind(result, selectedResult => HandleResultSelected(item, selectedResult));
        }
    }

    public void Clear()
    {
        selectedItem = null;

        if (resultsContent == null)
        {
            return;
        }

        for (int i = resultsContent.childCount - 1; i >= 0; i--)
        {
            Destroy(resultsContent.GetChild(i).gameObject);
        }
    }

    private void HandleResultSelected(ResultItemView item, ThoughtMapSearchResult result)
    {
        if (selectedItem != null)
        {
            selectedItem.SetSelected(false);
        }

        selectedItem = item;
        selectedItem?.SetSelected(true);
        ResultSelected?.Invoke(result);
    }
}
