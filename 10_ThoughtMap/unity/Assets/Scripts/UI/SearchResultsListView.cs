using UnityEngine;

public class SearchResultsListView : MonoBehaviour
{
    [SerializeField] private Transform resultsContent;
    [SerializeField] private ResultItemView resultItemPrefab;

    public void ShowResults(ThoughtMapSearchResult[] results)
    {
        Clear();

        if (results == null)
        {
            return;
        }

        foreach (ThoughtMapSearchResult result in results)
        {
            ResultItemView item = Instantiate(resultItemPrefab, resultsContent);
            item.Bind(result);
        }
    }

    public void Clear()
    {
        for (int i = resultsContent.childCount - 1; i >= 0; i--)
        {
            Destroy(resultsContent.GetChild(i).gameObject);
        }
    }
}
