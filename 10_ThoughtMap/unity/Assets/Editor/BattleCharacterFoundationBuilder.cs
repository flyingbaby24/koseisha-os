#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

public static class BattleCharacterFoundationBuilder
{
    private const string ModelPath = "Assets/Art/Characters/Character_Base.fbx";
    private const string MaterialFolder = "Assets/Art/Characters/Materials";
    private const string ControllerPath = "Assets/Art/Characters/Character_Base.controller";
    private const string PrefabFolder = "Assets/Prefabs/Characters";
    private const string PrefabPath = PrefabFolder + "/Character_Base.prefab";
    private const string DataFolder = "Assets/Resources/Battle";
    private const string DataPath = DataFolder + "/Character_BaseData.asset";

    [MenuItem("ThoughtMap/Battle/Build Character Foundation")]
    public static void Build()
    {
        EnsureFolder("Assets/Art/Characters"); EnsureFolder(MaterialFolder);
        EnsureFolder("Assets/Prefabs"); EnsureFolder(PrefabFolder);
        EnsureFolder("Assets/Resources"); EnsureFolder(DataFolder);

        AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
        if (AssetImporter.GetAtPath(ModelPath) is ModelImporter importer)
        {
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.importAnimation = true;
            importer.importCameras = false;
            importer.importLights = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            importer.SaveAndReimport();
        }

        Dictionary<string, Material> materials = CreateMaterials();
        AnimationClip[] clips = AssetDatabase.LoadAllAssetsAtPath(ModelPath)
            .OfType<AnimationClip>().Where(clip => !clip.name.StartsWith("__preview__")).ToArray();
        AnimatorController controller = BuildController(clips);

        GameObject modelAsset = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        if (modelAsset == null) throw new FileNotFoundException("Character model import failed.", ModelPath);
        GameObject character = (GameObject)PrefabUtility.InstantiatePrefab(modelAsset);
        character.name = "Character_Base";
        foreach (Renderer renderer in character.GetComponentsInChildren<Renderer>(true))
        {
            Material[] assigned = renderer.sharedMaterials;
            for (int i = 0; i < assigned.Length; i++)
                if (assigned[i] != null && materials.TryGetValue(assigned[i].name, out Material replacement)) assigned[i] = replacement;
            renderer.sharedMaterials = assigned;
        }
        Animator animator = character.GetComponent<Animator>();
        if (animator == null) animator = character.AddComponent<Animator>();
        animator.runtimeAnimatorController = controller;
        animator.applyRootMotion = false;
        if (character.GetComponent<BattleCharacterView>() == null) character.AddComponent<BattleCharacterView>();
        PrefabUtility.SaveAsPrefabAsset(character, PrefabPath);
        Object.DestroyImmediate(character);

        BattleCharacterData data = AssetDatabase.LoadAssetAtPath<BattleCharacterData>(DataPath);
        if (data == null)
        {
            data = ScriptableObject.CreateInstance<BattleCharacterData>();
            AssetDatabase.CreateAsset(data, DataPath);
        }
        data.Configure("character_base", AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath), 0.82f, Vector3.zero, new Vector3(-90f, 0f, 0f), controller);
        EditorUtility.SetDirty(data);
        AssetDatabase.SaveAssets();
        Debug.Log($"[BattleCharacter] Foundation built. Clips: {string.Join(", ", clips.Select(c => c.name))}");
    }

    private static AnimatorController BuildController(AnimationClip[] clips)
    {
        AssetDatabase.DeleteAsset(ControllerPath);
        AnimatorController controller = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
        AnimatorStateMachine machine = controller.layers[0].stateMachine;
        string[] states = { "Idle", "Walk", "Attack", "Hit", "Death" };
        foreach (string stateName in states)
        {
            AnimationClip clip = clips.FirstOrDefault(c => c.name == stateName || c.name.EndsWith("|" + stateName) || c.name.Contains(stateName));
            AnimatorState state = machine.AddState(stateName);
            state.motion = clip;
            if (stateName == "Idle") machine.defaultState = state;
        }
        return controller;
    }

    private static Dictionary<string, Material> CreateMaterials()
    {
        return new Dictionary<string, Material>
        {
            ["M_Character_Cloth"] = CreateMaterial("M_Character_Cloth", new Color(.018f,.10f,.18f), .04f, .25f),
            ["M_Character_Leather"] = CreateMaterial("M_Character_Leather", new Color(.14f,.05f,.02f), 0f, .2f),
            ["M_Character_Metal"] = CreateMaterial("M_Character_Metal", new Color(.045f,.075f,.13f), .78f, .75f),
            ["M_Character_Book"] = CreateMaterial("M_Character_Book", new Color(.055f,.025f,.075f), .18f, .66f, new Color(.04f,.55f,1f)*2.5f)
        };
    }

    private static Material CreateMaterial(string name, Color color, float metallic, float smoothness, Color? emission = null)
    {
        string path = $"{MaterialFolder}/{name}.mat";
        Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null)
        {
            material = new Material(Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard")) { name = name };
            AssetDatabase.CreateAsset(material, path);
        }
        material.SetColor("_BaseColor", color); material.SetFloat("_Metallic", metallic); material.SetFloat("_Smoothness", smoothness);
        if (emission.HasValue) { material.EnableKeyword("_EMISSION"); material.SetColor("_EmissionColor", emission.Value); }
        EditorUtility.SetDirty(material); return material;
    }

    private static void EnsureFolder(string path)
    {
        if (AssetDatabase.IsValidFolder(path)) return;
        string parent = Path.GetDirectoryName(path)?.Replace('\\','/');
        if (!string.IsNullOrEmpty(parent)) EnsureFolder(parent);
        AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
    }
}
#endif
