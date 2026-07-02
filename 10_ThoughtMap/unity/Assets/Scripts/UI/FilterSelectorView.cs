using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

public class FilterSelectorView : MonoBehaviour
{
    [SerializeField] private TMP_Dropdown filterDropdown;
    [SerializeField] private TextAsset[] filterJsonFiles;
    [SerializeField] private string allFiltersLabel = "all";
    [SerializeField] private string[] defaultFilterNames = { "general" };

    public event Action<string> FilterChanged;

    private readonly List<string> filterNames = new List<string>();

    private void Awake()
    {
        ConfigureOptions();

        if (filterDropdown != null)
        {
            filterDropdown.onValueChanged.AddListener(HandleValueChanged);
        }
    }

    private void OnDestroy()
    {
        if (filterDropdown != null)
        {
            filterDropdown.onValueChanged.RemoveListener(HandleValueChanged);
        }
    }

    public string GetSelectedFilter()
    {
        if (filterNames.Count == 0)
        {
            ConfigureOptions();
        }

        if (filterDropdown == null)
        {
            return allFiltersLabel;
        }

        if (filterDropdown.options != null && filterDropdown.options.Count > 0)
        {
            int dropdownIndex = Mathf.Clamp(filterDropdown.value, 0, filterDropdown.options.Count - 1);
            string optionText = filterDropdown.options[dropdownIndex].text;
            if (!string.IsNullOrWhiteSpace(optionText))
            {
                return optionText.Trim().ToLowerInvariant();
            }
        }

        if (filterNames.Count == 0)
        {
            return allFiltersLabel;
        }

        int index = Mathf.Clamp(filterDropdown.value, 0, filterNames.Count - 1);
        return string.IsNullOrWhiteSpace(filterNames[index]) ? allFiltersLabel : filterNames[index];
    }

    public void ConfigureOptions()
    {
        string selected = GetCurrentDropdownText();
        filterNames.Clear();
        AddFilterName(allFiltersLabel);

        if (filterDropdown != null && filterDropdown.options != null)
        {
            foreach (TMP_Dropdown.OptionData option in filterDropdown.options)
            {
                AddFilterName(option.text);
            }
        }

        if (defaultFilterNames != null)
        {
            foreach (string filterName in defaultFilterNames)
            {
                AddFilterName(filterName);
            }
        }

        if (filterJsonFiles != null)
        {
            foreach (TextAsset filterFile in filterJsonFiles)
            {
                if (filterFile == null)
                {
                    continue;
                }

                AddFilterName(filterFile.name);
            }
        }

        if (filterDropdown == null)
        {
            return;
        }

        filterDropdown.ClearOptions();
        filterDropdown.AddOptions(filterNames);
        filterDropdown.value = Mathf.Max(0, filterNames.IndexOf(NormalizeFilterName(selected)));
        filterDropdown.RefreshShownValue();
    }

    private void AddFilterName(string value)
    {
        string normalized = NormalizeFilterName(value);
        if (!string.IsNullOrWhiteSpace(normalized) && !filterNames.Contains(normalized))
        {
            filterNames.Add(normalized);
        }
    }

    private string GetCurrentDropdownText()
    {
        if (filterDropdown == null || filterDropdown.options == null || filterDropdown.options.Count == 0)
        {
            return allFiltersLabel;
        }

        int index = Mathf.Clamp(filterDropdown.value, 0, filterDropdown.options.Count - 1);
        return filterDropdown.options[index].text;
    }

    private string NormalizeFilterName(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? string.Empty : value.Trim().ToLowerInvariant();
    }

    private void HandleValueChanged(int _)
    {
        FilterChanged?.Invoke(GetSelectedFilter());
    }
}
