using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ThoughtMapSearchManager : MonoBehaviour
{
    [Header("API")]
    [SerializeField] private ThoughtMapApiClient apiClient;

    [Header("UI")]
    [SerializeField] private TMP_InputField searchInput;
    [SerializeField] private Button searchButton;
    [SerializeField] private Transform resultsContent;
    [SerializeField] private ResultItemView resultItemPrefab;

    private void Awake()
    {
        searchButton.onClick.AddListener(OnSearchClicked);
    }

    private void OnDestroy()
    {
        searchButton.onClick.RemoveListener(OnSearchClicked);
    }

    private void OnSearchClicked()
    {
        searchButton.interactable = false;
        ClearResults();
        StartCoroutine(apiClient.Search(searchInput.text, HandleSuccess, HandleError));
    }

    private void HandleSuccess(ThoughtMapSearchResponse response)
    {
        searchButton.interactable = true;
        ClearResults();

        if (response?.results == null)
        {
            return;
        }

        foreach (ThoughtMapSearchResult result in response.results)
        {
            ResultItemView item = Instantiate(resultItemPrefab, resultsContent);
            item.Bind(result);
        }
    }

    private void HandleError(string message)
    {
        searchButton.interactable = true;
        Debug.LogError($"ThoughtMap search failed: {message}");
    }

    private void ClearResults()
    {
        for (int i = resultsContent.childCount - 1; i >= 0; i--)
        {
            Destroy(resultsContent.GetChild(i).gameObject);
        }
    }
}
