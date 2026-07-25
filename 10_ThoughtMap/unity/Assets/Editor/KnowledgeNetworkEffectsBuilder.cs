#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEngine;

public static class KnowledgeNetworkEffectsBuilder
{
    private const string Folder="Assets/Resources/Effects";
    private const string PrefabPath=Folder+"/KnowledgePacket.prefab";
    [MenuItem("ThoughtMap/Battle/Build Knowledge Network Effects")]
    public static void Build()
    {
        EnsureFolder("Assets/Resources");EnsureFolder(Folder);
        GameObject root=new GameObject("KnowledgePacket",typeof(KnowledgePacketView));PrefabUtility.SaveAsPrefabAsset(root,PrefabPath);Object.DestroyImmediate(root);AssetDatabase.SaveAssets();
        Debug.Log("[KnowledgeNetwork] Shared KnowledgePacket prefab created.");
    }
    private static void EnsureFolder(string path){if(AssetDatabase.IsValidFolder(path))return;string parent=Path.GetDirectoryName(path)?.Replace('\\','/');if(!string.IsNullOrEmpty(parent))EnsureFolder(parent);AssetDatabase.CreateFolder(parent,Path.GetFileName(path));}
}
#endif
