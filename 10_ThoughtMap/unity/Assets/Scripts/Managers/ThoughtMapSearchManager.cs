using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ThoughtMapSearchManager : MonoBehaviour
{
    [Header("API")]
    [SerializeField] private ThoughtMapApiClient apiClient;

    [Header("UI")]
    [SerializeField] private TMP_InputField searchInput;
    [SerializeField] private TMP_Dropdown modeDropdown;
    [SerializeField] private TMP_Dropdown sourceDropdown;
    [SerializeField] private FilterSelectorView filterSelectorView;
    [SerializeField] private Button searchButton;
    [SerializeField] private SearchResultsListView resultsListView;
    [SerializeField] private DetailPanelView detailPanelView;
    [SerializeField] private int topResults = 10;

    private void Awake()
    {
        if (searchButton != null)
        {
            searchButton.onClick.AddListener(OnSearchClicked);
        }

        if (resultsListView != null)
        {
            resultsListView.ResultSelected += OnResultSelected;
        }
    }

    private void OnDestroy()
    {
        if (searchButton != null)
        {
            searchButton.onClick.RemoveListener(OnSearchClicked);
        }

        if (resultsListView != null)
        {
            resultsListView.ResultSelected -= OnResultSelected;
        }
    }

    private void OnSearchClicked()
    {
        if (apiClient == null || searchInput == null)
        {
            Debug.LogError("ThoughtMap search cannot start because API Client or Search Input is not assigned.");
            return;
        }

        if (searchButton != null)
        {
            searchButton.interactable = false;
        }

        resultsListView?.Clear();
        detailPanelView?.Clear();
        StartCoroutine(apiClient.Search(searchInput.text, topResults, GetSelectedMode(), GetSelectedSource(), GetSelectedFilter(), HandleSuccess, HandleError));
    }

    private string GetSelectedMode()
    {
        string value = GetDropdownValue(modeDropdown, "semantic");
        if (value == "keyword" || value == "hybrid")
        {
            return value;
        }
        return "semantic";
    }

    private string GetSelectedSource()
    {
        return GetDropdownValue(sourceDropdown, "all");
    }

    private string GetSelectedFilter()
    {
        return filterSelectorView == null ? "all" : filterSelectorView.GetSelectedFilter();
    }

    private string GetDropdownValue(TMP_Dropdown dropdown, string fallback)
    {
        if (dropdown == null || dropdown.options == null || dropdown.options.Count == 0)
        {
            return fallback;
        }

        int index = Mathf.Clamp(dropdown.value, 0, dropdown.options.Count - 1);
        string value = dropdown.options[index].text;
        if (string.IsNullOrWhiteSpace(value))
        {
            return fallback;
        }

        return value.Trim().ToLowerInvariant();
    }

    private void HandleSuccess(ThoughtMapSearchResponse response)
    {
        if (searchButton != null)
        {
            searchButton.interactable = true;
        }

        resultsListView?.ShowResults(response?.results);
    }

    private void HandleError(string message)
    {
        if (searchButton != null)
        {
            searchButton.interactable = true;
        }

        Debug.LogError($"ThoughtMap search failed: {message}");
    }

    private void OnResultSelected(ThoughtMapSearchResult result)
    {
        detailPanelView?.ShowPlaceholder(result);
        // Future step: call GET /document/{doc_id} here and bind the response to DetailPanelView.
    }
}
