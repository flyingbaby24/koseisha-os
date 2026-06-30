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
    [SerializeField] private SearchResultsListView resultsListView;
    [SerializeField] private int topResults = 10;

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
        resultsListView.Clear();
        StartCoroutine(apiClient.Search(searchInput.text, topResults, HandleSuccess, HandleError));
    }

    private void HandleSuccess(ThoughtMapSearchResponse response)
    {
        searchButton.interactable = true;
        resultsListView.ShowResults(response?.results);
    }

    private void HandleError(string message)
    {
        searchButton.interactable = true;
        Debug.LogError($"ThoughtMap search failed: {message}");
    }
}
