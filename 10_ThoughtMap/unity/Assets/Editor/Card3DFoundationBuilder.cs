#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class Card3DFoundationBuilder
{
    private const string ModelPath = "Assets/Art/Cards/Card_Base.fbx";
    private const string MaterialFolder = "Assets/Art/Cards/Materials";
    private const string PrefabFolder = "Assets/Resources/Cards";
    private const string PrefabPath = PrefabFolder + "/Card3D.prefab";

    [MenuItem("ThoughtMap/Battle/Build Card 3D Foundation")]
    public static void Build()
    {
        EnsureFolder("Assets/Art/Cards"); EnsureFolder(MaterialFolder);
        EnsureFolder("Assets/Resources"); EnsureFolder(PrefabFolder);
        AssetDatabase.ImportAsset(ModelPath, ImportAssetOptions.ForceSynchronousImport | ImportAssetOptions.ForceUpdate);
        if (AssetImporter.GetAtPath(ModelPath) is ModelImporter importer)
        {
            importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
            importer.materialImportMode = ModelImporterMaterialImportMode.None; importer.SaveAndReimport();
        }
        Dictionary<string, Material> materials = CreateMaterials();
        GameObject asset = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        if (asset == null) throw new FileNotFoundException("Card_Base.fbx import failed.", ModelPath);
        GameObject card = (GameObject)PrefabUtility.InstantiatePrefab(asset); card.name = "Card3D";
        foreach (Renderer renderer in card.GetComponentsInChildren<Renderer>(true))
        {
            Material[] assigned = renderer.sharedMaterials;
            for (int i=0;i<assigned.Length;i++) if (assigned[i]!=null && materials.TryGetValue(assigned[i].name,out Material replacement)) assigned[i]=replacement;
            renderer.sharedMaterials=assigned;
        }
        if (card.GetComponent<Card3DView>() == null) card.AddComponent<Card3DView>();
        PrefabUtility.SaveAsPrefabAsset(card, PrefabPath); Object.DestroyImmediate(card);
        AssetDatabase.SaveAssets();
        Debug.Log("[Card3D] Reusable PBR card prefab built at " + PrefabPath);
    }

    private static Dictionary<string,Material> CreateMaterials() => new Dictionary<string, Material>
    {
        ["M_Card_Metal"]=Mat("M_Card_Metal",new Color(.24f,.19f,.08f),.82f,.72f),
        ["M_Card_Paper"]=Mat("M_Card_Paper",new Color(.32f,.29f,.23f),0,.32f),
        ["M_Card_Edge"]=Mat("M_Card_Edge",new Color(.08f,.11f,.15f),.48f,.68f),
        ["M_Card_Artwork"]=Mat("M_Card_Artwork",Color.white,0,.28f,new Color(.025f,.025f,.025f)),
        ["M_Card_Back"]=Mat("M_Card_Back",new Color(.014f,.045f,.11f),.24f,.62f,new Color(.005f,.02f,.06f)),
        ["M_Card_Glow"]=Mat("M_Card_Glow",new Color(.015f,.16f,.26f),.08f,.72f,new Color(.04f,.5f,1f)*2.2f),
        ["M_Card_Shadow"]=Mat("M_Card_Shadow",new Color(.004f,.005f,.008f),0,0)
    };

    private static Material Mat(string name,Color color,float metallic,float smoothness,Color? emission=null)
    {
        string path=$"{MaterialFolder}/{name}.mat"; Material material=AssetDatabase.LoadAssetAtPath<Material>(path);
        if(material==null){material=new Material(Shader.Find("Universal Render Pipeline/Lit")??Shader.Find("Standard")){name=name};AssetDatabase.CreateAsset(material,path);}
        material.SetColor("_BaseColor",color);material.SetFloat("_Metallic",metallic);material.SetFloat("_Smoothness",smoothness);
        if(emission.HasValue){material.EnableKeyword("_EMISSION");material.SetColor("_EmissionColor",emission.Value);}EditorUtility.SetDirty(material);return material;
    }

    private static void EnsureFolder(string path)
    {
        if(AssetDatabase.IsValidFolder(path))return;string parent=Path.GetDirectoryName(path)?.Replace('\\','/');if(!string.IsNullOrEmpty(parent))EnsureFolder(parent);AssetDatabase.CreateFolder(parent,Path.GetFileName(path));
    }
}
#endif
