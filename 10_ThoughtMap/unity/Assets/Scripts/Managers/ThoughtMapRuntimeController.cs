using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ThoughtMapRuntimeController : MonoBehaviour
{
    [Header("API")]
    [SerializeField] private ThoughtMapApiClient apiClient;

    [Header("V2 Windows")]
    [SerializeField] private SearchHeaderV2View searchHeaderV2;
    [SerializeField] private ResultListV2View resultListV2;

    [Header("Search UI")]
    [SerializeField] private Button searchButton;
    [SerializeField] private TMP_InputField searchInput;
    [SerializeField] private TMP_Dropdown modeDropdown;
    [SerializeField] private TMP_Dropdown sourceDropdown;
    [SerializeField] private TMP_Dropdown filterDropdown;
    [SerializeField] private int topResults = 10;

    [Header("Results")]
    [SerializeField] private SearchResultsListView searchResultsListView;

    [Header("Detail")]
    [SerializeField] private ThoughtMapDetailPanelV2View detailPanelV2;

    [Header("Optional UI")]
    [SerializeField] private LoadingIndicatorView loadingIndicatorView;
    [SerializeField] private QueryParameterPanelView queryParameterPanelView;
    [SerializeField] private bool debugRuntimeFlow = true;

    private bool detailPanelV2SaveSubscribed;
    private ThoughtMapParameterScore[] currentQueryParameters;

    private void Awake()
    {
        ResolveDetailPanelV2();

        if (searchHeaderV2 != null)
        {
            searchHeaderV2.SearchRequested += OnSearchClicked;
            LogRuntime("SearchHeaderV2 subscribed.");
        }

        if (searchButton != null)
        {
            searchButton.onClick.AddListener(OnSearchClicked);
            if (searchButton.GetComponent<NeonHoverGlow>() == null)
            {
                searchButton.gameObject.AddComponent<NeonHoverGlow>();
            }
        }

        if (resultListV2 != null)
        {
            resultListV2.ResultSelected += OnResultSelected;
            LogRuntime("ResultListV2 subscribed.");
        }

        if (searchResultsListView != null)
        {
            searchResultsListView.ResultSelected += OnResultSelected;
        }

        SubscribeDetailPanelV2();

        if (detailPanelV2 == null)
        {
            Debug.LogWarning("[ThoughtMapRuntimeController] ThoughtMapDetailPanelV2 reference is missing. Result selection cannot update DetailPanelV2.", this);
        }
    }

    private void OnDestroy()
    {
        if (searchHeaderV2 != null)
        {
            searchHeaderV2.SearchRequested -= OnSearchClicked;
        }

        if (searchButton != null)
        {
            searchButton.onClick.RemoveListener(OnSearchClicked);
        }

        if (resultListV2 != null)
        {
            resultListV2.ResultSelected -= OnResultSelected;
        }

        if (searchResultsListView != null)
        {
            searchResultsListView.ResultSelected -= OnResultSelected;
        }

        if (detailPanelV2 != null && detailPanelV2SaveSubscribed)
        {
            detailPanelV2.SaveRequested -= OnSaveRequested;
            detailPanelV2SaveSubscribed = false;
        }
    }

    public void OnSearchClicked()
    {
        if (apiClient == null)
        {
            Debug.LogError("ThoughtMapRuntimeController requires Api Client.", this);
            return;
        }

        string query = GetQueryText();
        string mode = GetSelectedMode();
        string source = GetSelectedSource();
        string filter = GetSelectedFilter();
        LogRuntime($"V2 search requested query={query} mode={mode} source={source} filter={filter}");
        if (string.IsNullOrWhiteSpace(query))
        {
            Debug.LogWarning("ThoughtMapRuntimeController search query is empty.", this);
            return;
        }

        SetSearching(true);
        resultListV2?.Clear();
        searchResultsListView?.Clear();
        detailPanelV2?.Clear();
        queryParameterPanelView?.Clear();
        currentQueryParameters = null;

        LogRuntime($"API search started query={query} top={topResults} mode={mode} source={source} filter={filter}");
        StartCoroutine(apiClient.Search(
            query,
            topResults,
            mode,
            source,
            filter,
            HandleSearchSuccess,
            HandleSearchError
        ));
    }

    private void HandleSearchSuccess(ThoughtMapSearchResponse response)
    {
        SetSearching(false);
        ThoughtMapSearchResult[] results = response == null ? null : response.results;
        currentQueryParameters = response == null ? null : response.query_parameters;
        int resultCount = results == null ? 0 : results.Length;
        int queryParameterCount = currentQueryParameters == null ? 0 : currentQueryParameters.Length;
        LogRuntime($"API search success result count={resultCount}");
        LogRuntime($"API search success query_parameter count={queryParameterCount}");
        if (results != null)
        {
            for (int i = 0; i < results.Length; i++)
            {
                ThoughtMapSearchResult result = results[i];
                int parameterCount = result == null || result.parameters == null ? 0 : result.parameters.Length;
                Debug.Log($"[ThoughtMapRuntimeController] SearchSuccess result index={i} doc_id={(result == null ? "(null)" : result.doc_id)} parameter count={parameterCount}", this);
            }
        }

        if (resultListV2 != null)
        {
            if (results != null)
            {
                for (int i = 0; i < results.Length; i++)
                {
                    ThoughtMapSearchResult result = results[i];
                    int parameterCount = result == null || result.parameters == null ? 0 : result.parameters.Length;
                    Debug.Log($"[ThoughtMapRuntimeController] Before ResultListV2.SetResults result index={i} doc_id={(result == null ? "(null)" : result.doc_id)} parameter count={parameterCount}", this);
                }
            }

            resultListV2.SetResults(results);
            if (results != null)
            {
                for (int i = 0; i < results.Length; i++)
                {
                    ThoughtMapSearchResult result = results[i];
                    int parameterCount = result == null || result.parameters == null ? 0 : result.parameters.Length;
                    Debug.Log($"[ThoughtMapRuntimeController] Immediately before ResultListV2 updated count result index={i} doc_id={(result == null ? "(null)" : result.doc_id)} parameter count={parameterCount}", this);
                }
            }

            LogRuntime($"ResultListV2 updated count={resultCount}");
        }
        else
        {
            searchResultsListView?.ShowResults(results);
            LogRuntime($"Legacy SearchResultsListView updated count={resultCount}");
        }

        string queryText = GetQueryText();
        queryParameterPanelView?.ShowScores(queryText, currentQueryParameters);
        ThoughtMapDetailPanelV2View targetDetailPanel = ResolveDetailPanelV2();
        if (targetDetailPanel != null)
        {
            targetDetailPanel.ShowQueryParameters(queryText, currentQueryParameters);
        }
    }

    private void HandleSearchError(string message)
    {
        SetSearching(false);
        currentQueryParameters = null;
        queryParameterPanelView?.Clear();
        LogRuntime($"API search failed message={message}");
        Debug.LogError($"ThoughtMap search failed: {message}", this);
    }

    private void OnResultSelected(ThoughtMapSearchResult result)
    {
        LogRuntime($"Result selected doc_id={(result == null ? "(null)" : result.doc_id)}");
        ThoughtMapDetailPanelV2View targetDetailPanel = ResolveDetailPanelV2();
        if (targetDetailPanel == null)
        {
            Debug.LogWarning("[ThoughtMapRuntimeController] detailPanelV2 is null. Assign ThoughtMapDetailPanelV2View to RuntimeController or place ThoughtMapDetailPanelV2 in the scene.", this);
            return;
        }

        int parameterCount = result == null || result.parameters == null ? 0 : result.parameters.Length;
        LogRuntime($"Calling ThoughtMapDetailPanelV2.ShowResult doc_id={(result == null ? "(null)" : result.doc_id)} parameter count={parameterCount} detailInstance={targetDetailPanel.GetInstanceID()}");
        targetDetailPanel.ShowResult(result);
        targetDetailPanel.ShowQueryParameters(GetQueryText(), currentQueryParameters);
    }

    private void OnSaveRequested(ThoughtMapSearchResult result)
    {
        if (apiClient == null)
        {
            detailPanelV2?.SetSaveError("API Client is not assigned.");
            return;
        }

        detailPanelV2?.SetSaving();
        StartCoroutine(apiClient.SaveDefaultDocument(result, HandleSaveSuccess, HandleSaveError));
    }

    private void HandleSaveSuccess(SaveDocumentResponse response)
    {
        detailPanelV2?.SetSaved(response != null && response.duplicate);
    }

    private void HandleSaveError(string message)
    {
        detailPanelV2?.SetSaveError(message);
        Debug.LogError($"ThoughtMap save failed: {message}", this);
    }

    private void SetSearching(bool value)
    {
        if (searchHeaderV2 != null)
        {
            searchHeaderV2.SetInteractable(!value);
        }

        if (searchButton != null)
        {
            searchButton.interactable = !value;
        }

        if (value)
        {
            loadingIndicatorView?.Show();
        }
        else
        {
            loadingIndicatorView?.Hide();
        }
    }

    private string GetQueryText()
    {
        if (searchHeaderV2 != null && !string.IsNullOrWhiteSpace(searchHeaderV2.QueryText))
        {
            return searchHeaderV2.QueryText;
        }

        return searchInput == null ? string.Empty : searchInput.text;
    }

    private string GetSelectedMode()
    {
        string value = searchHeaderV2 == null ? string.Empty : searchHeaderV2.SelectedMode;
        return string.IsNullOrWhiteSpace(value) ? GetDropdownValue(modeDropdown, "semantic") : value;
    }

    private string GetSelectedSource()
    {
        string value = searchHeaderV2 == null ? string.Empty : searchHeaderV2.SelectedSource;
        return string.IsNullOrWhiteSpace(value) ? GetDropdownValue(sourceDropdown, "all") : value;
    }

    private string GetSelectedFilter()
    {
        string value = searchHeaderV2 == null ? string.Empty : searchHeaderV2.SelectedFilter;
        return string.IsNullOrWhiteSpace(value) ? GetDropdownValue(filterDropdown, "all") : value;
    }

    private string GetDropdownValue(TMP_Dropdown dropdown, string fallback)
    {
        if (dropdown == null || dropdown.options == null || dropdown.options.Count == 0)
        {
            return fallback;
        }

        int index = Mathf.Clamp(dropdown.value, 0, dropdown.options.Count - 1);
        string value = dropdown.options[index].text;
        return string.IsNullOrWhiteSpace(value) ? fallback : value.Trim().ToLowerInvariant();
    }

    private void LogRuntime(string message)
    {
        if (debugRuntimeFlow)
        {
            Debug.Log($"[ThoughtMapRuntimeController] {message}", this);
        }
    }

    private ThoughtMapDetailPanelV2View ResolveDetailPanelV2()
    {
        if (detailPanelV2 != null)
        {
            return detailPanelV2;
        }

        ThoughtMapDetailPanelV2View[] panels = FindObjectsByType<ThoughtMapDetailPanelV2View>(FindObjectsInactive.Include, FindObjectsSortMode.None);
        if (panels == null || panels.Length == 0)
        {
            return null;
        }

        detailPanelV2 = panels[0];
        LogRuntime($"Resolved ThoughtMapDetailPanelV2 automatically instance={detailPanelV2.GetInstanceID()}.");
        SubscribeDetailPanelV2();
        return detailPanelV2;
    }

    private void SubscribeDetailPanelV2()
    {
        if (detailPanelV2 == null || detailPanelV2SaveSubscribed)
        {
            return;
        }

        detailPanelV2.SaveRequested += OnSaveRequested;
        detailPanelV2SaveSubscribed = true;
        LogRuntime($"ThoughtMapDetailPanelV2 subscribed instance={detailPanelV2.GetInstanceID()}.");
    }
}
