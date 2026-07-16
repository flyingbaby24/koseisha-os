using System.Collections.Generic;
using UnityEngine;

public class BattleFieldView : MonoBehaviour
{
    [SerializeField] private Transform playerTeamRoot;
    [SerializeField] private Transform enemyTeamRoot;
    [SerializeField] private BattleCardView battleCardPrefab;
    [SerializeField] private int previewUnitCount = 5;

    public Transform PlayerTeamRoot => playerTeamRoot;
    public Transform EnemyTeamRoot => enemyTeamRoot;

    public void RenderStaticPreview()
    {
        RenderTeam(playerTeamRoot, "P", previewUnitCount, false);
        RenderTeam(enemyTeamRoot, "E", previewUnitCount, true);
    }

    public void RenderTeam(Transform root, string prefix, int count, bool markFirstAsTarget)
    {
        if (root == null || battleCardPrefab == null)
        {
            return;
        }

        Clear(root);
        int safeCount = Mathf.Max(0, count);
        for (int i = 0; i < safeCount; i++)
        {
            BattleCardView view = Instantiate(battleCardPrefab, root);
            view.name = $"{prefix}{i + 1}_BattleCard";
            view.Bind($"{prefix}{i + 1} Unit", null, 1f, 1f, markFirstAsTarget && i == 0);
        }
    }

    public IReadOnlyList<BattleCardView> GetPlayerCards()
    {
        return GetCards(playerTeamRoot);
    }

    public IReadOnlyList<BattleCardView> GetEnemyCards()
    {
        return GetCards(enemyTeamRoot);
    }

    private static IReadOnlyList<BattleCardView> GetCards(Transform root)
    {
        List<BattleCardView> cards = new List<BattleCardView>();
        if (root == null)
        {
            return cards;
        }

        root.GetComponentsInChildren(true, cards);
        return cards;
    }

    private static void Clear(Transform root)
    {
        for (int i = root.childCount - 1; i >= 0; i--)
        {
            Destroy(root.GetChild(i).gameObject);
        }
    }
}
