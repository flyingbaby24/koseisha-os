using UnityEngine;

public sealed class BattleCharacterView : MonoBehaviour
{
    [SerializeField] private Animator animator;
    [SerializeField] private Renderer[] renderers;
    public string UnitId { get; private set; }
    public ProductBattleUnitCardView CardView { get; private set; }

    public void Initialize(string unitId, ProductBattleUnitCardView cardView, RuntimeAnimatorController controller, bool enemySide)
    {
        UnitId = unitId;
        CardView = cardView;
        animator = animator != null ? animator : GetComponentInChildren<Animator>(true);
        renderers = renderers != null && renderers.Length > 0 ? renderers : GetComponentsInChildren<Renderer>(true);
        if (animator != null && controller != null) animator.runtimeAnimatorController = controller;
        ApplyTeamTint(enemySide);
        PlayIdle();
    }

    public void PlayIdle() => Play("Idle");
    public void PlayWalk() => Play("Walk");
    public void PlayAttack() => Play("Attack");
    public void PlayHit() => Play("Hit");
    public void PlayDeath() => Play("Death");

    private void Play(string state)
    {
        if (animator != null && animator.runtimeAnimatorController != null)
            animator.CrossFadeInFixedTime(state, 0.12f, 0);
    }

    private void ApplyTeamTint(bool enemySide)
    {
        Color tint = enemySide ? new Color(1f, 0.62f, 0.58f, 1f) : new Color(0.62f, 0.86f, 1f, 1f);
        var block = new MaterialPropertyBlock();
        foreach (Renderer target in renderers)
        {
            target.GetPropertyBlock(block);
            block.SetColor("_TeamTint", tint);
            target.SetPropertyBlock(block);
        }
    }
}
