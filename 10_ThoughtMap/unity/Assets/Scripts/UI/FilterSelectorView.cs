using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;

public class FilterSelectorView : MonoBehaviour
{
    [SerializeField] private TMP_Dropdown filterDropdown;
    [SerializeField] private TextAsset[] filterJsonFiles;
    [SerializeField] private string allFiltersLabel = "all";

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

        if (filterNames.Count == 0 || filterDropdown == null)
        {
            return allFiltersLabel;
        }

        int index = Mathf.Clamp(filterDropdown.value, 0, filterNames.Count - 1);
        return string.IsNullOrWhiteSpace(filterNames[index]) ? allFiltersLabel : filterNames[index];
    }

    public void ConfigureOptions()
    {
        filterNames.Clear();
        filterNames.Add(allFiltersLabel);

        if (filterJsonFiles != null)
        {
            foreach (TextAsset filterFile in filterJsonFiles)
            {
                if (filterFile == null || string.IsNullOrWhiteSpace(filterFile.name))
                {
                    continue;
                }

                if (!filterNames.Contains(filterFile.name))
                {
                    filterNames.Add(filterFile.name);
                }
            }
        }

        if (filterDropdown == null)
        {
            return;
        }

        filterDropdown.ClearOptions();
        filterDropdown.AddOptions(filterNames);
        filterDropdown.value = 0;
        filterDropdown.RefreshShownValue();
    }

    private void HandleValueChanged(int _)
    {
        FilterChanged?.Invoke(GetSelectedFilter());
    }
}
