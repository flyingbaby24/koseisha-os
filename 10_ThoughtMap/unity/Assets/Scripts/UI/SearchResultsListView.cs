using System;
using UnityEngine;

public class SearchResultsListView : MonoBehaviour
{
    [SerializeField] private Transform resultsContent;
    [SerializeField] private ResultItemView resultItemPrefab;
    [SerializeField] private bool animateItems = true;
    [SerializeField] private float itemFadeDelayStep = 0.035f;

    private ResultItemView selectedItem;

    public event Action<ThoughtMapSearchResult> ResultSelected;

    public void ShowResults(ThoughtMapSearchResult[] results)
    {
        Clear();

        if (results == null || resultsContent == null || resultItemPrefab == null)
        {
            return;
        }

        for (int i = 0; i < results.Length; i++)
        {
            ThoughtMapSearchResult result = results[i];
            ResultItemView item = Instantiate(resultItemPrefab, resultsContent);
            item.Bind(result, selectedResult => HandleResultSelected(item, selectedResult));

            if (animateItems)
            {
                NeonUIFade fade = item.GetComponent<NeonUIFade>();
                if (fade == null)
                {
                    fade = item.gameObject.AddComponent<NeonUIFade>();
                }
                fade.Play(i * itemFadeDelayStep);
            }
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
