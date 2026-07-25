using UnityEngine;

/// <summary>The sole world-space transform for one battle participant.</summary>
public sealed class BattleUnitView : MonoBehaviour
{
    [Header("Synchronization Debug")]
    [SerializeField] private bool showSynchronizationGizmos = true;
    [SerializeField] private float gizmoRadius = 0.12f;
    [Header("Presentation Offsets")]
    [SerializeField] private Vector3 characterOffset = Vector3.zero;
    [SerializeField] private Vector3 cardOffset = new Vector3(0.72f, 0.04f, 0.16f);
    [SerializeField] private Vector3 hpBarOffset = new Vector3(0f, 2.15f, 0f);
    [SerializeField] private Vector3 statusOffset = new Vector3(0f, 2.42f, 0f);
    [SerializeField] private Vector3 knowledgeCoreOffset = new Vector3(0f, 1.15f, 0f);
    [Header("Card Unit Motion")]
    [SerializeField] private float cardFloatHeight = 0.025f;
    [SerializeField] private float floatSpeed = 1.05f;
    [SerializeField] private float rotationSpeed = 2.2f;
    [SerializeField] private float hoverAmount = 1.8f;
    [SerializeField] private Vector3 attackOffset = new Vector3(0f, 0.05f, 0.34f);
    [SerializeField] private float hitShakeStrength = 0.09f;
    public string UnitId { get; private set; }
    public ThoughtMapGridPosition GridPosition { get; private set; }
    public Transform CharacterRoot { get; private set; }
    public Transform CardRoot { get; private set; }
    public Transform HPBarRoot { get; private set; }
    public Transform StatusRoot { get; private set; }
    public Transform EffectRoot { get; private set; }
    public Transform KnowledgeCore { get; private set; }
    public Transform PresentationAnchor { get; private set; }
    public Transform AttackOrigin { get; private set; }
    public Transform EffectTarget { get; private set; }
    public BattleCharacterView CharacterView { get; private set; }
    public BattlePresentationUnitData PresentationData { get; private set; }
    public Card3DView Card3D { get; private set; }

    public void Initialize(
        string unitId,
        ThoughtMapGridPosition gridPosition,
        Transform characterRoot,
        Transform cardRoot,
        Transform hpBarRoot,
        Transform statusRoot,
        Transform effectRoot,
        Transform knowledgeCore,
        Transform presentationAnchor,
        BattleCharacterView characterView,
        BattlePresentationUnitData presentationData,
        Vector3 initialCharacterOffset,
        Vector3 initialCardOffset,
        Vector3 initialHpBarOffset,
        Vector3 initialStatusOffset,
        Vector3 initialKnowledgeCoreOffset,
        Card3DView card3D)
    {
        UnitId = unitId;
        GridPosition = gridPosition;
        CharacterRoot = characterRoot;
        CardRoot = cardRoot;
        HPBarRoot = hpBarRoot;
        StatusRoot = statusRoot;
        EffectRoot = effectRoot;
        KnowledgeCore = knowledgeCore;
        PresentationAnchor = presentationAnchor;
        CharacterView = characterView;
        PresentationData = presentationData;
        Card3D = card3D;
        characterOffset = initialCharacterOffset;
        cardOffset = initialCardOffset;
        hpBarOffset = initialHpBarOffset;
        statusOffset = initialStatusOffset;
        knowledgeCoreOffset = initialKnowledgeCoreOffset;
        ApplyPresentationOffsets();
        ApplyCardMotionSettings();
        EnsureEffectAnchors();
    }

    public void PlayCardAttack(float duration) { if (Card3D != null) Card3D.PlayAttackMotion(attackOffset, duration); }
    public void PlayCardHit() { if (Card3D != null) Card3D.PlayHitMotion(hitShakeStrength); }
    public void SetCardHovered(bool value) { if (Card3D != null) Card3D.SetHovered(value); }
    public void SetCardSelected(bool value) { if (Card3D != null) Card3D.SetSelected(value); }
    public void SetCardTargeted(bool value) { if (Card3D != null) Card3D.SetTargeted(value); }
    public void SetCardDead(bool value) { if (Card3D != null) Card3D.SetDead(value); }

    private void EnsureEffectAnchors()
    {
        Transform parent = PresentationAnchor == null ? transform : PresentationAnchor;
        AttackOrigin = FindOrCreate(parent, "AttackOrigin", new Vector3(0f, .18f, 0f));
        EffectTarget = FindOrCreate(parent, "EffectTarget", new Vector3(0f, .12f, 0f));
    }

    private static Transform FindOrCreate(Transform parent, string childName, Vector3 localPosition)
    {
        Transform child = parent.Find(childName);
        if (child == null) { child = new GameObject(childName).transform; child.SetParent(parent, false); }
        child.localPosition = localPosition; child.localRotation = Quaternion.identity; child.localScale = Vector3.one;
        return child;
    }

    private void ApplyCardMotionSettings()
    {
        if (Card3D != null) Card3D.ConfigureBattleMotion(cardFloatHeight, floatSpeed, rotationSpeed, hoverAmount);
    }

    public void ApplyPresentationOffsets()
    {
        if (CharacterRoot != null) CharacterRoot.localPosition = characterOffset;
        if (CardRoot != null) CardRoot.localPosition = cardOffset;
        if (HPBarRoot != null) HPBarRoot.localPosition = hpBarOffset;
        if (StatusRoot != null) StatusRoot.localPosition = statusOffset;
        if (EffectRoot != null) EffectRoot.localPosition = Vector3.zero;
        if (KnowledgeCore != null) KnowledgeCore.localPosition = knowledgeCoreOffset;
    }

    private void OnValidate()
    {
        ApplyPresentationOffsets();
        ApplyCardMotionSettings();
    }

    private void OnDrawGizmos()
    {
        if (!showSynchronizationGizmos) return;

        DrawAnchor(transform, Color.white, gizmoRadius * 1.35f);
        DrawAnchor(CharacterRoot, new Color(0.15f, 0.75f, 1f), gizmoRadius);
        DrawAnchor(CardRoot, new Color(1f, 0.75f, 0.1f), gizmoRadius);
        DrawAnchor(KnowledgeCore, new Color(0.15f, 1f, 0.45f), gizmoRadius * 1.15f);

        if (CharacterRoot != null) DrawLink(transform.position, CharacterRoot.position, new Color(0.15f, 0.75f, 1f));
        if (CardRoot != null) DrawLink(transform.position, CardRoot.position, new Color(1f, 0.75f, 0.1f));
        if (KnowledgeCore != null) DrawLink(transform.position, KnowledgeCore.position, new Color(0.15f, 1f, 0.45f));
    }

    private static void DrawAnchor(Transform anchor, Color color, float radius)
    {
        if (anchor == null) return;
        Gizmos.color = color;
        Gizmos.DrawWireSphere(anchor.position, radius);
        Gizmos.DrawLine(anchor.position, anchor.position + anchor.right * radius * 2f);
        Gizmos.DrawLine(anchor.position, anchor.position + anchor.up * radius * 2f);
        Gizmos.DrawLine(anchor.position, anchor.position + anchor.forward * radius * 2f);
    }

    private static void DrawLink(Vector3 from, Vector3 to, Color color)
    {
        Gizmos.color = color;
        Gizmos.DrawLine(from, to);
    }
}
