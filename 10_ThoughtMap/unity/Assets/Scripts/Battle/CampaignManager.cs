using System.Linq;
using UnityEngine;

public sealed class CampaignManager
{
    private const string CurrentStageKey = "thoughtmap.campaign.current_stage";
    private static CampaignManager instance;
    private CampaignData campaign;

    public static CampaignManager Instance => instance ?? (instance = new CampaignManager());

    public CampaignStageData CurrentStage
    {
        get
        {
            EnsureLoaded();
            string stageId = PlayerPrefs.GetString(CurrentStageKey, campaign.defaultStageId);
            return campaign.stages.FirstOrDefault(stage => stage != null && stage.stageId == stageId)
                ?? campaign.stages.FirstOrDefault(stage => stage != null);
        }
    }

    public void SetCurrentStage(string stageId)
    {
        EnsureLoaded();
        if (campaign.stages.Any(stage => stage != null && stage.stageId == stageId))
        {
            PlayerPrefs.SetString(CurrentStageKey, stageId);
            PlayerPrefs.Save();
        }
        else
        {
            Debug.LogError($"[Campaign] Stage not found in campaign.json: {stageId}");
        }
    }

    public void CompleteCurrentStage(bool victory)
    {
        CampaignStageData stage = CurrentStage;
        if (!victory || stage == null || string.IsNullOrWhiteSpace(stage.nextStageId))
        {
            return;
        }
        SetCurrentStage(stage.nextStageId);
    }

    public void Reload()
    {
        campaign = null;
        EnsureLoaded();
    }

    private void EnsureLoaded()
    {
        if (campaign == null)
        {
            campaign = StreamingJsonLoader.Load<CampaignData>("campaign.json");
        }
    }
}
