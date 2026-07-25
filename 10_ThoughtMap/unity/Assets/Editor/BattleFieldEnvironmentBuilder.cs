#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using TMPro;

public static class BattleFieldEnvironmentBuilder
{
    private const string ModelPath = "Assets/Art/BattleField/BattleField.fbx";
    private const string MaterialFolder = "Assets/Art/BattleField/Materials";
    private const string PrefabFolder = "Assets/Prefabs/Battle";
    private const string PrefabPath = PrefabFolder + "/BattleFieldRoot.prefab";
    private const string ScenePath = "Assets/Scenes/BattleScene.unity";

    [MenuItem("ThoughtMap/Battle/Build 3D Battle Field")]
    public static void Build()
    {
        EnsureFolder("Assets/Art/BattleField");
        EnsureFolder(MaterialFolder);
        EnsureFolder("Assets/Prefabs");
        EnsureFolder(PrefabFolder);
        AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);

        Dictionary<string, Material> materials = CreateMaterials();
        GameObject modelAsset = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        if (modelAsset == null) throw new FileNotFoundException("BattleField model was not imported.", ModelPath);

        GameObject root = new GameObject("BattleFieldRoot");
        GameObject model = (GameObject)PrefabUtility.InstantiatePrefab(modelAsset, root.transform);
        model.name = "BattleFieldModel";
        model.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);
        model.transform.localScale = Vector3.one;

        foreach (Renderer renderer in model.GetComponentsInChildren<Renderer>(true))
        {
            Material[] assigned = renderer.sharedMaterials;
            for (int i = 0; i < assigned.Length; i++)
            {
                if (assigned[i] != null && materials.TryGetValue(assigned[i].name, out Material replacement))
                    assigned[i] = replacement;
            }
            renderer.sharedMaterials = assigned;
            renderer.shadowCastingMode = ShadowCastingMode.On;
            renderer.receiveShadows = true;
        }
        foreach (Camera importedCamera in model.GetComponentsInChildren<Camera>(true))
            Object.DestroyImmediate(importedCamera.gameObject);
        foreach (Light importedLight in model.GetComponentsInChildren<Light>(true))
            Object.DestroyImmediate(importedLight.gameObject);

        root.AddComponent<CyberArchiveEnvironmentView>();
        root.AddComponent<KnowledgeNetworkView>();

        Transform lights = new GameObject("RealtimeLights").transform;
        lights.SetParent(root.transform, false);
        AddDirectional(lights, "ArchiveAmbient", new Color(0.12f, 0.32f, 1f), 0.055f, new Vector3(52f, -24f, 0f));
        AddPoint(lights, "ThoughtMapLight", new Vector3(0, 1.5f, 1f), new Color(0.02f, 0.38f, 1f), 1.1f, 15f);
        AddPoint(lights, "KnowledgeNexusLight", new Vector3(0, 6f, 11f), new Color(0.01f, 0.24f, 1f), 1.4f, 18f);
        AddPoint(lights, "LeftArchiveFill", new Vector3(-6.4f, 4f, 3f), new Color(0.01f, 0.16f, 0.7f), 0.55f, 11f);
        AddPoint(lights, "RightArchiveFill", new Vector3(6.4f, 4f, 3f), new Color(0.01f, 0.16f, 0.7f), 0.55f, 11f);
        BuildHologramLabels(root.transform);
        BuildParticles(root.transform);

        Transform anchors = new GameObject("FutureCharacterAnchors_5x5").transform;
        anchors.SetParent(root.transform, false);
        for (int row = 0; row < 5; row++)
        for (int column = 0; column < 5; column++)
        {
            GameObject anchor = new GameObject($"Slot_{column}_{row}");
            anchor.transform.SetParent(anchors, false);
            anchor.transform.localPosition = new Vector3((column - 2) * 2.25f, 0.42f, (row - 2) * 2.35f + 0.5f);
        }

        PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
        Object.DestroyImmediate(root);

        var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        GameObject existing = GameObject.Find("BattleFieldRoot");
        if (existing != null) Object.DestroyImmediate(existing);
        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
        GameObject instance = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
        instance.transform.SetLocalPositionAndRotation(Vector3.zero, Quaternion.identity);

        RenderSettings.ambientMode = AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.008f, 0.035f, 0.09f);
        RenderSettings.ambientEquatorColor = new Color(0.003f, 0.012f, 0.035f);
        RenderSettings.ambientGroundColor = new Color(0.001f, 0.004f, 0.012f);
        RenderSettings.ambientIntensity = 0.08f;
        RenderSettings.fog = true;
        RenderSettings.fogMode = FogMode.ExponentialSquared;
        RenderSettings.fogColor = new Color(0.004f, 0.02f, 0.06f);
        RenderSettings.fogDensity = 0.006f;

        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);
        AssetDatabase.SaveAssets();
        Debug.Log("[BattleField] Cyber Archive environment, ThoughtMap floor, Infinite Library, holograms and ambient FX completed.");
    }

    private static Dictionary<string, Material> CreateMaterials()
    {
        var result = new Dictionary<string, Material>();
        result["M_GlassFloor"] = Material("M_GlassFloor", new Color(.01f,.07f,.11f,.46f), .18f, .88f, new Color(.015f,.18f,.32f), 1.2f, true);
        result["M_ArchiveMetal"] = Material("M_ArchiveMetal", new Color(.025f,.055f,.085f), .82f, .72f);
        result["M_DarkStructure"] = Material("M_DarkStructure", new Color(.006f,.012f,.026f), .35f, .5f);
        result["M_Circuit"] = Material("M_Circuit", new Color(.005f,.12f,.20f), .25f, .76f, new Color(.02f,.58f,1f), 4f);
        result["M_Hologram"] = Material("M_Hologram", new Color(.01f,.16f,.25f,.62f), .08f, .85f, new Color(.03f,.72f,1f), 5f, true);
        result["M_ArchiveBook"] = Material("M_ArchiveBook", new Color(.10f,.025f,.12f), .08f, .48f, new Color(.05f,.2f,.5f), .8f);
        result["M_ThoughtNode"] = Material("M_ThoughtNode", new Color(.015f,.22f,.34f), .2f, .84f, new Color(.04f,.78f,1f), 6f);
        result["M_DataPage"] = Material("M_DataPage", new Color(.10f,.18f,.22f,.78f), .05f, .54f, new Color(.02f,.25f,.42f), 1.3f, true);
        return result;
    }

    private static void BuildHologramLabels(Transform root)
    {
        Transform labels = new GameObject("HologramLabels").transform; labels.SetParent(root, false);
        AddHologram(labels, "KNOWLEDGE ARCHIVE", new Vector3(0, 8.7f, 12.62f), 0.58f);
        AddHologram(labels, "PHILOSOPHY", new Vector3(-5f, 6.6f, 10.72f), 0.34f);
        AddHologram(labels, "SCIENCE", new Vector3(5f, 6.3f, 9.42f), 0.34f);
        AddHologram(labels, "PSYCHOLOGY", new Vector3(-5.1f, 4.1f, 5.72f), 0.34f);
        AddHologram(labels, "ECONOMICS", new Vector3(5.1f, 4.3f, 4.72f), 0.34f);
    }

    private static void AddHologram(Transform parent, string value, Vector3 position, float size)
    {
        GameObject go = new GameObject("Label_" + value.Replace(' ', '_'), typeof(TextMeshPro)); go.transform.SetParent(parent, false);
        go.transform.localPosition = position; go.transform.localRotation = Quaternion.identity;
        TextMeshPro text = go.GetComponent<TextMeshPro>(); text.text = value; text.fontSize = size * 10f; text.alignment = TextAlignmentOptions.Center;
        text.color = new Color(.16f,.78f,1f,.9f); text.enableWordWrapping = false; text.rectTransform.sizeDelta = new Vector2(7f, 1.2f);
    }

    private static void BuildParticles(Transform root)
    {
        Material particleMaterial = AssetDatabase.LoadAssetAtPath<Material>(MaterialFolder + "/M_DataParticle.mat");
        if (particleMaterial == null)
        {
            particleMaterial = new Material(Shader.Find("Universal Render Pipeline/Particles/Unlit") ?? Shader.Find("Sprites/Default")) { name="M_DataParticle" };
            AssetDatabase.CreateAsset(particleMaterial, MaterialFolder + "/M_DataParticle.mat");
        }
        particleMaterial.SetColor("_BaseColor", new Color(.02f,.35f,1f,.62f));
        Material fogMaterial = AssetDatabase.LoadAssetAtPath<Material>(MaterialFolder + "/M_BlueFog.mat");
        if (fogMaterial == null) { fogMaterial = new Material(particleMaterial) { name="M_BlueFog" }; AssetDatabase.CreateAsset(fogMaterial, MaterialFolder + "/M_BlueFog.mat"); }
        fogMaterial.SetColor("_BaseColor", new Color(.002f,.025f,.10f,.018f));
        AddParticles(root,"DataParticle",particleMaterial,new Vector3(13f,2f,17f),40f,5f,.035f,new Color(.08f,.65f,1f,.85f));
        AddParticles(root,"BlueFog",fogMaterial,new Vector3(14f,.7f,18f),1.2f,7f,.75f,new Color(.005f,.04f,.16f,.018f));
    }

    private static void AddParticles(Transform parent,string name,Material material,Vector3 box,float rate,float lifetime,float size,Color color)
    {
        GameObject go=new GameObject(name,typeof(ParticleSystem));go.transform.SetParent(parent,false);go.transform.localPosition=new Vector3(0,.2f,2f);
        ParticleSystem ps=go.GetComponent<ParticleSystem>();var main=ps.main;main.loop=true;main.playOnAwake=true;main.startLifetime=lifetime;main.startSpeed=.22f;main.startSize=size;main.startColor=color;main.maxParticles=450;main.simulationSpace=ParticleSystemSimulationSpace.Local;
        var emission=ps.emission;emission.rateOverTime=rate;var shape=ps.shape;shape.shapeType=ParticleSystemShapeType.Box;shape.scale=box;
        var velocity=ps.velocityOverLifetime;velocity.enabled=true;velocity.x=0f;velocity.y=.24f;velocity.z=0f;
        ParticleSystemRenderer renderer=go.GetComponent<ParticleSystemRenderer>();renderer.renderMode=ParticleSystemRenderMode.Billboard;renderer.material=material;
    }

    private static Material Material(string name, Color color, float metallic, float smoothness, Color? emission = null, float emissionStrength = 0f, bool transparent = false)
    {
        string path = $"{MaterialFolder}/{name}.mat";
        Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (material == null)
        {
            Shader shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            material = new Material(shader) { name = name };
            AssetDatabase.CreateAsset(material, path);
        }
        material.SetColor("_BaseColor", color);
        material.SetFloat("_Metallic", metallic);
        material.SetFloat("_Smoothness", smoothness);
        if (emission.HasValue)
        {
            material.EnableKeyword("_EMISSION");
            material.SetColor("_EmissionColor", emission.Value * emissionStrength);
        }
        if (transparent)
        {
            material.SetFloat("_Surface", 1f);
            material.SetFloat("_Blend", 0f);
            material.SetFloat("_ZWrite", 0f);
            material.SetFloat("_SrcBlend", (float)UnityEngine.Rendering.BlendMode.SrcAlpha);
            material.SetFloat("_DstBlend", (float)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            material.SetOverrideTag("RenderType", "Transparent");
            material.renderQueue = (int)RenderQueue.Transparent;
        }
        EditorUtility.SetDirty(material);
        return material;
    }

    private static void AddDirectional(Transform parent, string name, Color color, float intensity, Vector3 rotation)
    {
        Light light = new GameObject(name, typeof(Light)).GetComponent<Light>(); light.transform.SetParent(parent, false);
        light.type = LightType.Directional; light.color = color; light.intensity = intensity; light.shadows = LightShadows.Soft;
        light.transform.localEulerAngles = rotation;
    }

    private static void AddPoint(Transform parent, string name, Vector3 position, Color color, float intensity, float range)
    {
        Light light = new GameObject(name, typeof(Light)).GetComponent<Light>(); light.transform.SetParent(parent, false);
        light.type = LightType.Point; light.color = color; light.intensity = intensity; light.range = range; light.shadows = LightShadows.Soft;
        light.transform.localPosition = position;
    }

    private static void EnsureFolder(string path)
    {
        if (AssetDatabase.IsValidFolder(path)) return;
        string parent = Path.GetDirectoryName(path)?.Replace('\\', '/');
        string name = Path.GetFileName(path);
        if (!string.IsNullOrEmpty(parent)) EnsureFolder(parent);
        AssetDatabase.CreateFolder(parent, name);
    }
}
#endif
