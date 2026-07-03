using System;
using UnityEngine;

public class ThoughtMapDetailPanelRouter : MonoBehaviour
{
    [Header("Panel Selection")]
    [SerializeField] private bool useDetailPanelV2 = true;

    [Header("Panels")]
    [SerializeField] private DetailPanelView legacyDetailPanel;
    [SerializeField] private ThoughtMapDetailPanelV2View detailPanelV2;

    public event Action<ThoughtMapSearchResult> SaveRequested;

    private void Awake()
    {
        SubscribeSaveEvents();
    }

    private void OnDestroy()
    {
        UnsubscribeSaveEvents();
    }

    public void ShowResult(ThoughtMapSearchResult result)
    {
        if (useDetailPanelV2 && detailPanelV2 != null)
        {
            detailPanelV2.ShowResult(result);
            return;
        }

        if (legacyDetailPanel != null)
        {
            legacyDetailPanel.ShowResult(result);
        }
    }

    public void Clear()
    {
        if (useDetailPanelV2 && detailPanelV2 != null)
        {
            detailPanelV2.Clear();
            return;
        }

        legacyDetailPanel?.Clear();
    }

    public void SetSaving()
    {
        if (useDetailPanelV2 && detailPanelV2 != null)
        {
            detailPanelV2.SetSaving();
            return;
        }

        legacyDetailPanel?.SetSaving();
    }

    public void SetSaved(bool duplicate)
    {
        if (useDetailPanelV2 && detailPanelV2 != null)
        {
            detailPanelV2.SetSaved(duplicate);
            return;
        }

        legacyDetailPanel?.SetSaved(duplicate);
    }

    public void SetSaveError(string message)
    {
        if (useDetailPanelV2 && detailPanelV2 != null)
        {
            detailPanelV2.SetSaveError(message);
            return;
        }

        legacyDetailPanel?.SetSaveError(message);
    }

    private void SubscribeSaveEvents()
    {
        if (legacyDetailPanel != null)
        {
            legacyDetailPanel.SaveRequested += HandleSaveRequested;
        }

        if (detailPanelV2 != null)
        {
            detailPanelV2.SaveRequested += HandleSaveRequested;
        }
    }

    private void UnsubscribeSaveEvents()
    {
        if (legacyDetailPanel != null)
        {
            legacyDetailPanel.SaveRequested -= HandleSaveRequested;
        }

        if (detailPanelV2 != null)
        {
            detailPanelV2.SaveRequested -= HandleSaveRequested;
        }
    }

    private void HandleSaveRequested(ThoughtMapSearchResult result)
    {
        SaveRequested?.Invoke(result);
    }
}
