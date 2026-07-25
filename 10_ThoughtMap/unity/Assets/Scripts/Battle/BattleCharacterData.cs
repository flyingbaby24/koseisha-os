using UnityEngine;

[CreateAssetMenu(menuName = "ThoughtMap/Battle/Character Data", fileName = "CharacterData")]
public sealed class BattleCharacterData : ScriptableObject
{
    [SerializeField] private string characterId = "character_base";
    [SerializeField] private GameObject prefab;
    [SerializeField] private float scale = 1f;
    [SerializeField] private Vector3 offset = Vector3.zero;
    [SerializeField] private Vector3 rotationOffset = new Vector3(-90f, 0f, 0f);
    [SerializeField] private RuntimeAnimatorController animator;

    public string CharacterId => characterId;
    public GameObject Prefab => prefab;
    public float Scale => scale;
    public Vector3 Offset => offset;
    public Vector3 RotationOffset => rotationOffset;
    public RuntimeAnimatorController Animator => animator;

#if UNITY_EDITOR
    public void Configure(string id, GameObject characterPrefab, float characterScale, Vector3 characterOffset, Vector3 characterRotation, RuntimeAnimatorController controller)
    {
        characterId = id; prefab = characterPrefab; scale = characterScale; offset = characterOffset; rotationOffset = characterRotation; animator = controller;
    }
#endif
}
