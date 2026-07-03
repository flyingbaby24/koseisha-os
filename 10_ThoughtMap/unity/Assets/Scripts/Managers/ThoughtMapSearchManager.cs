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
    [SerializeField] private QueryParameterPanelView queryParameterPanelView;
    [SerializeField] private int topResults = 10;
    [SerializeField] private bool debugSaveFlow = true;

    private void Awake()
    {
        LogSaveFlow($"Awake manager={name} apiClient={(apiClient == null ? "null" : apiClient.name)} detailPanelView={(detailPanelView == null ? "null" : detailPanelView.name)}");
        if (searchButton != null)
        {
            searchButton.onClick.AddListener(OnSearchClicked);
        }

        if (resultsListView != null)
        {
            resultsListView.ResultSelected += OnResultSelected;
        }

        if (detailPanelView != null)
        {
            detailPanelView.SaveRequested += OnSaveRequested;
            LogSaveFlow($"Subscribed SaveRequested detailPanelView={detailPanelView.name} detailInstance={detailPanelView.GetInstanceID()}");
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

        if (detailPanelView != null)
        {
            detailPanelView.SaveRequested -= OnSaveRequested;
            LogSaveFlow($"Unsubscribed SaveRequested detailPanelView={detailPanelView.name} detailInstance={detailPanelView.GetInstanceID()}");
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
        queryParameterPanelView?.Clear();
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
        queryParameterPanelView?.ShowScores(searchInput == null ? "" : searchInput.text, response?.query_parameters);
    }

    private void HandleError(string message)
    {
        if (searchButton != null)
        {
            searchButton.interactable = true;
        }

        queryParameterPanelView?.Clear();
        Debug.LogError($"ThoughtMap search failed: {message}");
    }

    private void OnResultSelected(ThoughtMapSearchResult result)
    {
        LogSaveFlow($"OnResultSelected doc_id={(result == null ? "null" : result.doc_id)} detailPanelView={(detailPanelView == null ? "null" : detailPanelView.name)} detailInstance={(detailPanelView == null ? 0 : detailPanelView.GetInstanceID())}");
        detailPanelView?.ShowResult(result);
        // Future step: call GET /document/{doc_id} here and bind the response to DetailPanelView.
    }

    private void OnSaveRequested(ThoughtMapSearchResult result)
    {
        LogSaveFlow($"OnSaveRequested doc_id={(result == null ? "null" : result.doc_id)} apiClient={(apiClient == null ? "null" : apiClient.name)}");
        if (apiClient == null)
        {
            detailPanelView?.SetSaveError("API Client is not assigned.");
            return;
        }

        detailPanelView?.SetSaving();
        LogSaveFlow($"Starting SaveDefaultDocument coroutine doc_id={result.doc_id}");
        StartCoroutine(apiClient.SaveDefaultDocument(result, HandleSaveSuccess, HandleSaveError));
    }

    private void HandleSaveSuccess(SaveDocumentResponse response)
    {
        LogSaveFlow($"HandleSaveSuccess saved={(response == null ? "null" : response.saved.ToString())} duplicate={(response == null ? "null" : response.duplicate.ToString())}");
        detailPanelView?.SetSaved(response != null && response.duplicate);
    }

    private void HandleSaveError(string message)
    {
        LogSaveFlow($"HandleSaveError message={message}");
        detailPanelView?.SetSaveError(message);
        Debug.LogError($"ThoughtMap save failed: {message}");
    }
    private void LogSaveFlow(string message)
    {
        if (debugSaveFlow)
        {
            Debug.Log($"[ThoughtMap SaveFlow][SearchManager:{GetInstanceID()}] {message}", this);
        }
    }
}
