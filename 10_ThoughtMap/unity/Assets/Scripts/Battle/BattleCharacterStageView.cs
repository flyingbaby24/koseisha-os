using System.Collections.Generic;
using UnityEngine;

public sealed class BattleCharacterStageView : MonoBehaviour
{
    [SerializeField] private BattleCharacterData defaultCharacter;
    [SerializeField] private GameObject card3DPrefab;
    [SerializeField] private float slotSpacingX = 1.90f;
    [SerializeField] private float slotSpacingZ = 4.20f;
    [SerializeField] private Vector2 playerGridCenter = new Vector2(-5.3f, 0f);
    [SerializeField] private Vector2 enemyGridCenter = new Vector2(5.3f, 0f);
    [Header("BattleUnit Presentation")]
    [SerializeField] private Vector3 characterLocalOffset = Vector3.zero;
    [SerializeField] private Vector3 cardLocalOffsetPlayer = Vector3.zero;
    [SerializeField] private Vector3 cardLocalOffsetEnemy = Vector3.zero;
    [SerializeField] private Vector3 hpBarLocalOffset = new Vector3(0f, 2.15f, 0f);
    [SerializeField] private Vector3 statusLocalOffset = new Vector3(0f, 2.42f, 0f);
    [SerializeField] private Vector3 knowledgeCoreLocalOffset = new Vector3(0f, 1.15f, 0f);
    private Transform unitsRoot;
    private readonly Dictionary<string, BattleUnitView> units = new Dictionary<string, BattleUnitView>();

    public IReadOnlyDictionary<string, BattleUnitView> Units => units;

    public void Spawn(
        IReadOnlyList<ThoughtMapGridPosition> playerPositions,
        IReadOnlyList<ThoughtMapGridPosition> enemyPositions,
        IReadOnlyDictionary<string, BattlePresentationUnitData> presentationData)
    {
        if (defaultCharacter == null) defaultCharacter = Resources.Load<BattleCharacterData>("Battle/Character_BaseData");
        if (card3DPrefab == null) card3DPrefab = Resources.Load<GameObject>("Cards/Card3D");
        if (defaultCharacter == null || defaultCharacter.Prefab == null)
        {
            Debug.LogWarning("[BattleCharacter] Character_BaseData or prefab is missing; card battle continues normally.");
            return;
        }
        Clear();
        unitsRoot = new GameObject("BattleUnits").transform;
        unitsRoot.SetParent(transform, false);
        SpawnTeam("P", false, playerPositions, presentationData);
        SpawnTeam("E", true, enemyPositions, presentationData);
        BattlefieldGridPresentationView grid=GetComponent<BattlefieldGridPresentationView>()??gameObject.AddComponent<BattlefieldGridPresentationView>();
        grid.Build(slotSpacingX,slotSpacingZ,playerGridCenter,enemyGridCenter,.43f);
    }

    private void SpawnTeam(string prefix, bool enemySide, IReadOnlyList<ThoughtMapGridPosition> positions, IReadOnlyDictionary<string, BattlePresentationUnitData> presentationData)
    {
        int count = positions == null ? 0 : Mathf.Min(5, positions.Count);
        for (int i = 0; i < count; i++)
        {
            string unitId = prefix + (i + 1);
            ThoughtMapGridPosition grid = positions[i];
            GameObject battleUnit = new GameObject("BattleUnit_" + unitId);
            battleUnit.transform.SetParent(unitsRoot, false);
            Vector2 teamCenter=enemySide?enemyGridCenter:playerGridCenter;
            battleUnit.transform.localPosition = new Vector3(teamCenter.x+(grid.x - 2) * slotSpacingX, 0.42f, teamCenter.y+(grid.y - 2) * slotSpacingZ);
            battleUnit.transform.localRotation = Quaternion.Euler(0f, enemySide ? 180f : 0f, 0f);
            battleUnit.transform.localScale = Vector3.one;

            Transform presentationAnchor = new GameObject("PresentationAnchor").transform;
            presentationAnchor.SetParent(battleUnit.transform, false);

            Transform characterRoot = new GameObject("CharacterRoot").transform;
            characterRoot.SetParent(battleUnit.transform, false);
            GameObject character = Instantiate(defaultCharacter.Prefab, characterRoot);
            character.name = defaultCharacter.CharacterId;
            character.transform.localPosition = defaultCharacter.Offset;
            character.transform.localRotation = Quaternion.Euler(defaultCharacter.RotationOffset);
            character.transform.localScale = Vector3.one * defaultCharacter.Scale;
            presentationData.TryGetValue(unitId, out BattlePresentationUnitData data);

            GameObject cardLink = new GameObject("CardRoot"); cardLink.transform.SetParent(presentationAnchor, false);
            cardLink.transform.localPosition = enemySide ? cardLocalOffsetEnemy : cardLocalOffsetPlayer;
            cardLink.transform.localRotation = Quaternion.Euler(0f, enemySide ? 180f : 0f, 0f);
            Card3DView card3D = null;
            if (card3DPrefab != null)
            {
                GameObject card3DObject = Instantiate(card3DPrefab, cardLink.transform);
                card3DObject.name = "Card3D";
                card3DObject.transform.localPosition = Vector3.zero;
                card3DObject.transform.localRotation = Quaternion.Euler(102f, 180f, enemySide ? -2f : 2f);
                card3DObject.transform.localScale = Vector3.one * 1.30f;
                card3D = card3DObject.GetComponent<Card3DView>();
                if (card3D != null)
                {
                    card3D.SetPresentationAnchor(presentationAnchor);
                    card3D.CapturePresentationPose();
                    card3D.AlignVisualCenterToAnchor();
                    card3D.ConfigureTeam(enemySide);
                    if (data != null) card3D.SetCardSprite(data.CardSprite);
                }
            }
            GameObject hpAnchor = new GameObject("HPBarRoot"); hpAnchor.transform.SetParent(presentationAnchor, false); hpAnchor.transform.localPosition = hpBarLocalOffset;
            GameObject statusAnchor = new GameObject("StatusRoot"); statusAnchor.transform.SetParent(presentationAnchor, false); statusAnchor.transform.localPosition = statusLocalOffset;
            GameObject effectAnchor = new GameObject("EffectRoot"); effectAnchor.transform.SetParent(presentationAnchor, false);
            GameObject knowledgeCore = new GameObject("KnowledgeCore"); knowledgeCore.transform.SetParent(presentationAnchor, false); knowledgeCore.transform.localPosition = knowledgeCoreLocalOffset;

            BattleCharacterView view = character.GetComponent<BattleCharacterView>() ?? character.AddComponent<BattleCharacterView>();
            view.Initialize(unitId, null, defaultCharacter.Animator, enemySide);
            characterRoot.gameObject.SetActive(false);
            BattleUnitView unitView = battleUnit.AddComponent<BattleUnitView>();
            unitView.Initialize(unitId, grid, characterRoot, cardLink.transform, hpAnchor.transform, statusAnchor.transform, effectAnchor.transform, knowledgeCore.transform, presentationAnchor, view, data,
                characterLocalOffset, enemySide ? cardLocalOffsetEnemy : cardLocalOffsetPlayer, hpBarLocalOffset, statusLocalOffset, knowledgeCoreLocalOffset, card3D);
            units[unitId] = unitView;
        }
    }

    private void Clear()
    {
        units.Clear();
        if (unitsRoot != null) Destroy(unitsRoot.gameObject);
        Transform old = transform.Find("BattleUnits");
        if (old != null) Destroy(old.gameObject);
    }
}
