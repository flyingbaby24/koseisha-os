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
        StartCoroutine(apiClient.Search(searchInput.text, topResults, GetSelectedMode(), GetSelectedSource(), HandleSuccess, HandleError));
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
        searchButton.interactable = true;
        resultsListView.ShowResults(response?.results);
    }

    private void HandleError(string message)
    {
        searchButton.interactable = true;
        Debug.LogError($"ThoughtMap search failed: {message}");
    }
}
