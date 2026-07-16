using System.Collections.Generic;
using UnityEngine;

public class BattleSceneController : MonoBehaviour
{
    [SerializeField] private BattleHudView hudView;
    [SerializeField] private BattleFieldView fieldView;
    [SerializeField] private BattleLogView battleLogView;
    [SerializeField] private SpeedOrderView speedOrderView;
    [SerializeField] private bool renderPreviewOnStart = true;

    private void Start()
    {
        if (renderPreviewOnStart)
        {
            RenderInitialPreview();
        }
    }

    [ContextMenu("Render Initial Preview")]
    public void RenderInitialPreview()
    {
        if (hudView != null)
        {
            hudView.SetState(1, 1, "Speed x1");
        }

        if (fieldView != null)
        {
            fieldView.RenderStaticPreview();
        }

        if (speedOrderView != null)
        {
            speedOrderView.RenderPreview(new[] { "P1", "E1", "P2", "E2", "P3" });
        }

        if (battleLogView != null)
        {
            battleLogView.SetLines(new List<string>
            {
                "BattleScene initialized.",
                "Deck loading, combat, skills, AI, damage, and animation are intentionally not implemented yet.",
                "PlayerTeam and EnemyTeam preview cards are ready for the next phase."
            });
        }

        Debug.Log("[Battle] BattleScene initial preview rendered.", this);
    }
}
