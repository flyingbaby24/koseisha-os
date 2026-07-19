#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.TextCore.LowLevel;

public static class ThoughtMapTmpFontAssetRepairer
{
    private const string FontFolder = "Assets/Fonts";
    private const string RepairFontPath = "Assets/Fonts/ThoughtMapJapanese SDF.asset";
    private const int SamplingPointSize = 96;
    private const int Padding = 12;
    private const int AtlasSize = 2048;
    private const string WarmupCharacters =
        "+-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,;:!?()[]{}_/\\'\"%" +
        "\u3042\u3044\u3046\u3048\u304a\u304b\u304d\u304f\u3051\u3053\u3055\u3057\u3059\u305b\u305d" +
        "\u305f\u3061\u3064\u3066\u3068\u306a\u306b\u306c\u306d\u306e\u306f\u3072\u3075\u3078\u307b" +
        "\u307e\u307f\u3080\u3081\u3082\u3084\u3086\u3088\u3089\u308a\u308b\u308c\u308d\u308f\u3092\u3093" +
        "\u30a2\u30a4\u30a6\u30a8\u30aa\u30ab\u30ad\u30af\u30b1\u30b3\u30b5\u30b7\u30b9\u30bb\u30bd" +
        "\u30bf\u30c1\u30c4\u30c6\u30c8\u30ca\u30cb\u30cc\u30cd\u30ce\u30cf\u30d2\u30d5\u30d8\u30db" +
        "\u30de\u30df\u30e0\u30e1\u30e2\u30e4\u30e6\u30e8\u30e9\u30ea\u30eb\u30ec\u30ed\u30ef\u30f2\u30f3" +
        "\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e\u5343\u4e07" +
        "\u4e0a\u4e0b\u5de6\u53f3\u524d\u5f8c\u4e2d\u5927\u5c0f\u529b\u77e5\u6027\u5fc3\u7406" +
        "\u79d1\u5b66\u7d4c\u6e08\u54f2\u5b66\u611f\u60c5\u500b\u4eba\u5171\u540c\u4f53" +
        "\u7406\u5ff5\u9053\u5fb3\u653b\u6483\u9632\u5fa1\u901f\u5ea6\u56de\u907f\u547d\u4e2d\u904b";

    private static readonly string[] PreferredOsFonts =
    {
        "Noto Sans JP",
        "Noto Sans CJK JP",
        "BIZ UDPGothic",
        "Yu Gothic UI",
        "Yu Gothic",
        "Meiryo",
        "Microsoft YaHei UI"
    };

    [MenuItem("ThoughtMap/Repair All TMP Font Assets")]
    public static void RepairAllTmpFontAssets()
    {
        TMP_FontAsset repairFont = EnsureRepairFontAsset();
        if (repairFont == null)
        {
            Debug.LogError("[ThoughtMap TMP Repair] Failed to create or load repair TMP FontAsset.");
            return;
        }

        RepairReport report = new RepairReport
        {
            fontPath = AssetDatabase.GetAssetPath(repairFont),
            atlasCount = GetAtlasTextureCount(repairFont),
            atlasMinDimension = GetAtlasMinDimension(repairFont),
            hasMaterial = SafeMaterial(repairFont) != null
        };

        RegisterTmpSettings(repairFont);
        RepairOpenScenes(repairFont, report);
        RepairSceneAssets(repairFont, report);
        RepairPrefabs(repairFont, report);

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();

        Debug.Log(
            "[ThoughtMap TMP Repair] Complete\n" +
            $"FontAsset: {report.fontPath}\n" +
            $"Sampling Point Size: {SamplingPointSize}, Padding: {Padding}, Atlas: {AtlasSize}x{AtlasSize}\n" +
            $"Open scenes checked: {report.scenesChecked}, scenes saved: {report.scenesSaved}\n" +
            $"Scene assets checked: {report.sceneAssetsChecked}, scene assets saved: {report.sceneAssetsSaved}\n" +
            $"Prefabs checked: {report.prefabsChecked}, prefabs saved: {report.prefabsSaved}\n" +
            $"TMP_Text assigned: {report.replacedTextCount}\n" +
            $"atlasTextures: {report.atlasCount}, atlasMinDimension: {report.atlasMinDimension}, material: {(report.hasMaterial ? "yes" : "no")}"
        );
    }

    private static TMP_FontAsset EnsureRepairFontAsset()
    {
        EnsureFolder(FontFolder);

        TMP_FontAsset existing = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(RepairFontPath);
        if (IsHighQualityFontAsset(existing))
        {
            existing.atlasPopulationMode = AtlasPopulationMode.Dynamic;
            existing.isMultiAtlasTexturesEnabled = true;
            WarmUp(existing);
            TuneMaterial(existing);
            EditorUtility.SetDirty(existing);
            return existing;
        }

        if (existing != null)
        {
            Debug.Log("[ThoughtMap TMP Repair] Deleting incomplete or low-resolution FontAsset before regeneration: " + RepairFontPath);
            AssetDatabase.DeleteAsset(RepairFontPath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        TMP_FontAsset generated = CreateFromInstalledFont(out string successFont, out string overload, out string triedFonts);
        if (generated != null)
        {
            generated.name = "ThoughtMapJapanese SDF";
            generated.atlasPopulationMode = AtlasPopulationMode.Dynamic;
            generated.isMultiAtlasTexturesEnabled = true;
            TuneMaterial(generated);

            AssetDatabase.CreateAsset(generated, RepairFontPath);
            AssetDatabase.SaveAssets();
            AssetDatabase.ImportAsset(RepairFontPath, ImportAssetOptions.ForceUpdate);

            TMP_FontAsset saved = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(RepairFontPath);
            WarmUp(saved);
            TuneMaterial(saved);

            if (IsHighQualityFontAsset(saved))
            {
                Debug.Log(
                    "[ThoughtMap TMP Repair] Created persistent TMP FontAsset\n" +
                    $"Path: {RepairFontPath}\n" +
                    $"Tried OS fonts: {triedFonts}\n" +
                    $"Success font: {successFont}\n" +
                    $"CreateFontAsset overload: {overload}\n" +
                    $"atlasTextures: {GetAtlasTextureCount(saved)}, material: {(SafeMaterial(saved) != null ? "yes" : "no")}"
                );
                return saved;
            }

            Debug.LogWarning("[ThoughtMap TMP Repair] Generated FontAsset failed high-quality validation. Deleting and using fallback if available.");
            AssetDatabase.DeleteAsset(RepairFontPath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        TMP_FontAsset fallback = FindExistingUsableFontAsset();
        if (fallback != null)
        {
            Debug.LogWarning("[ThoughtMap TMP Repair] Could not generate high-quality Noto/BIZ FontAsset. Using fallback: " + AssetDatabase.GetAssetPath(fallback));
        }
        else
        {
            Debug.LogError("[ThoughtMap TMP Repair] No usable TMP FontAsset found. Tried OS fonts: " + triedFonts);
        }
        return fallback;
    }

    private static TMP_FontAsset CreateFromInstalledFont(out string successFont, out string overload, out string triedFonts)
    {
        successFont = "";
        overload = "";
        List<string> tried = new List<string>();
        HashSet<string> installed = new HashSet<string>(GetInstalledFontNames(), StringComparer.OrdinalIgnoreCase);

        Debug.Log(
            "[ThoughtMap TMP Repair] Preferred OS font candidates: " + string.Join(", ", PreferredOsFonts) + "\n" +
            "[ThoughtMap TMP Repair] Installed preferred matches: " + string.Join(", ", PreferredOsFonts.Where(installed.Contains))
        );

        foreach (string osFont in PreferredOsFonts.Where(installed.Contains))
        {
            tried.Add(osFont);
            try
            {
                Font sourceFont = Font.CreateDynamicFontFromOSFont(osFont, 18);
                Debug.Log(
                    "[ThoughtMap TMP Repair] OS font candidate " +
                    $"requested='{osFont}' returnedNull={sourceFont == null} " +
                    $"fontName='{(sourceFont == null ? "<null>" : sourceFont.name)}' dynamic={(sourceFont != null && sourceFont.dynamic)}"
                );

                if (sourceFont == null)
                {
                    continue;
                }

                TMP_FontAsset asset = CreateFontAsset(sourceFont, out overload);
                if (asset == null)
                {
                    Debug.LogWarning("[ThoughtMap TMP Repair] TMP_FontAsset.CreateFontAsset returned null for " + osFont);
                    continue;
                }

                asset.name = "ThoughtMapJapanese SDF";
                asset.atlasPopulationMode = AtlasPopulationMode.Dynamic;
                asset.isMultiAtlasTexturesEnabled = true;
                successFont = osFont;
                triedFonts = string.Join(", ", tried);
                return asset;
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[ThoughtMap TMP Repair] Font candidate '{osFont}' failed: {ex.GetType().Name}: {ex.Message}");
            }
        }

        string[] missing = PreferredOsFonts.Where(font => !installed.Contains(font)).ToArray();
        if (missing.Length > 0)
        {
            Debug.Log("[ThoughtMap TMP Repair] Preferred OS fonts not installed: " + string.Join(", ", missing));
        }

        triedFonts = tried.Count == 0 ? "<none>" : string.Join(", ", tried);
        return null;
    }

    private static TMP_FontAsset CreateFontAsset(Font font, out string usedOverload)
    {
        usedOverload = "<none>";

        try
        {
            foreach (System.Reflection.MethodInfo method in typeof(TMP_FontAsset).GetMethods())
            {
                if (method.Name != "CreateFontAsset")
                {
                    continue;
                }

                System.Reflection.ParameterInfo[] parameters = method.GetParameters();
                if (parameters.Length == 8 &&
                    parameters[0].ParameterType == typeof(Font) &&
                    parameters[6].ParameterType == typeof(AtlasPopulationMode) &&
                    parameters[7].ParameterType == typeof(bool))
                {
                    usedOverload = "CreateFontAsset(Font,int,int,GlyphRenderMode,int,int,AtlasPopulationMode,bool)";
                    return method.Invoke(
                        null,
                        new object[]
                        {
                            font,
                            SamplingPointSize,
                            Padding,
                            GlyphRenderMode.SDFAA,
                            AtlasSize,
                            AtlasSize,
                            AtlasPopulationMode.Dynamic,
                            true
                        }
                    ) as TMP_FontAsset;
                }
            }

            foreach (System.Reflection.MethodInfo method in typeof(TMP_FontAsset).GetMethods())
            {
                if (method.Name != "CreateFontAsset")
                {
                    continue;
                }

                System.Reflection.ParameterInfo[] parameters = method.GetParameters();
                if (parameters.Length == 6 && parameters[0].ParameterType == typeof(Font))
                {
                    usedOverload = "CreateFontAsset(Font,int,int,GlyphRenderMode,int,int)";
                    TMP_FontAsset asset = method.Invoke(
                        null,
                        new object[]
                        {
                            font,
                            SamplingPointSize,
                            Padding,
                            GlyphRenderMode.SDFAA,
                            AtlasSize,
                            AtlasSize
                        }
                    ) as TMP_FontAsset;
                    if (asset != null)
                    {
                        asset.atlasPopulationMode = AtlasPopulationMode.Dynamic;
                    }
                    return asset;
                }
            }
        }
        catch (Exception ex)
        {
            Debug.LogWarning("[ThoughtMap TMP Repair] CreateFontAsset reflection call failed: " + ex.GetType().Name + ": " + ex.Message);
        }

        return null;
    }

    private static void RegisterTmpSettings(TMP_FontAsset repairFont)
    {
        TMP_Settings settings = TMP_Settings.instance;
        if (settings == null)
        {
            Debug.LogWarning("[ThoughtMap TMP Repair] TMP Settings asset was not found. Scene and prefab text references were still repaired.");
            return;
        }

        SerializedObject serializedSettings = new SerializedObject(settings);
        SerializedProperty defaultFont = serializedSettings.FindProperty("m_defaultFontAsset");
        if (defaultFont != null)
        {
            defaultFont.objectReferenceValue = repairFont;
        }

        SerializedProperty fallbackFonts = serializedSettings.FindProperty("m_fallbackFontAssets");
        if (fallbackFonts != null && !ContainsObjectReference(fallbackFonts, repairFont))
        {
            int index = fallbackFonts.arraySize;
            fallbackFonts.InsertArrayElementAtIndex(index);
            fallbackFonts.GetArrayElementAtIndex(index).objectReferenceValue = repairFont;
        }

        serializedSettings.ApplyModifiedPropertiesWithoutUndo();
        EditorUtility.SetDirty(settings);
    }

    private static void RepairOpenScenes(TMP_FontAsset repairFont, RepairReport report)
    {
        for (int i = 0; i < SceneManager.sceneCount; i++)
        {
            Scene scene = SceneManager.GetSceneAt(i);
            if (!scene.IsValid() || !scene.isLoaded)
            {
                continue;
            }

            report.scenesChecked++;
            bool changed = false;
            foreach (GameObject root in scene.GetRootGameObjects())
            {
                changed |= RepairTmpTextsInRoot(root, repairFont, report, true);
            }

            if (changed)
            {
                EditorSceneManager.MarkSceneDirty(scene);
                EditorSceneManager.SaveScene(scene);
                report.scenesSaved++;
            }
        }
    }

    private static void RepairSceneAssets(TMP_FontAsset repairFont, RepairReport report)
    {
        SceneSetup[] originalSetup = EditorSceneManager.GetSceneManagerSetup();
        string[] sceneGuids = AssetDatabase.FindAssets("t:Scene", new[] { "Assets" });
        try
        {
            foreach (string guid in sceneGuids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (string.IsNullOrWhiteSpace(path))
                {
                    continue;
                }

                report.sceneAssetsChecked++;
                try
                {
                    Scene scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
                    bool changed = false;
                    foreach (GameObject root in scene.GetRootGameObjects())
                    {
                        changed |= RepairTmpTextsInRoot(root, repairFont, report, true);
                    }

                    if (changed)
                    {
                        EditorSceneManager.MarkSceneDirty(scene);
                        EditorSceneManager.SaveScene(scene);
                        report.sceneAssetsSaved++;
                    }
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"[ThoughtMap TMP Repair] Failed to repair scene '{path}': {ex.GetType().Name}: {ex.Message}");
                }
            }
        }
        finally
        {
            try
            {
                if (originalSetup != null && originalSetup.Length > 0)
                {
                    EditorSceneManager.RestoreSceneManagerSetup(originalSetup);
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning("[ThoughtMap TMP Repair] Could not restore previously open scenes: " + ex.GetType().Name + ": " + ex.Message);
            }
        }
    }

    private static void RepairPrefabs(TMP_FontAsset repairFont, RepairReport report)
    {
        string[] prefabGuids = AssetDatabase.FindAssets("t:Prefab", new[] { "Assets" });
        foreach (string guid in prefabGuids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            if (string.IsNullOrWhiteSpace(path))
            {
                continue;
            }

            report.prefabsChecked++;
            GameObject root = null;
            try
            {
                root = PrefabUtility.LoadPrefabContents(path);
                bool changed = RepairTmpTextsInRoot(root, repairFont, report, false);
                if (changed)
                {
                    PrefabUtility.SaveAsPrefabAsset(root, path);
                    report.prefabsSaved++;
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[ThoughtMap TMP Repair] Failed to repair prefab '{path}': {ex.GetType().Name}: {ex.Message}");
            }
            finally
            {
                if (root != null)
                {
                    PrefabUtility.UnloadPrefabContents(root);
                }
            }
        }
    }

    private static bool RepairTmpTextsInRoot(GameObject root, TMP_FontAsset repairFont, RepairReport report, bool recordPrefabInstance)
    {
        bool changed = false;
        TMP_Text[] texts = root.GetComponentsInChildren<TMP_Text>(true);
        Material repairMaterial = SafeMaterial(repairFont);
        foreach (TMP_Text text in texts)
        {
            if (text == null)
            {
                continue;
            }

            SerializedObject serializedText = new SerializedObject(text);
            SerializedProperty fontProperty = serializedText.FindProperty("m_fontAsset");
            UnityEngine.Object currentFont = fontProperty == null ? null : fontProperty.objectReferenceValue;
            if (currentFont == repairFont && IsUsableFontAsset(repairFont))
            {
                continue;
            }

            if (fontProperty != null)
            {
                fontProperty.objectReferenceValue = repairFont;
            }

            SetMaterialPropertyIfPresent(serializedText, "m_fontSharedMaterial", repairMaterial);
            SetMaterialPropertyIfPresent(serializedText, "m_sharedMaterial", repairMaterial);
            SetMaterialPropertyIfPresent(serializedText, "m_fontMaterial", repairMaterial);
            serializedText.ApplyModifiedPropertiesWithoutUndo();

            try
            {
                text.font = repairFont;
                if (repairMaterial != null)
                {
                    text.fontSharedMaterial = repairMaterial;
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[ThoughtMap TMP Repair] TMP_Text refresh failed on '{text.name}': {ex.GetType().Name}: {ex.Message}");
            }

            EditorUtility.SetDirty(text);
            if (recordPrefabInstance)
            {
                PrefabUtility.RecordPrefabInstancePropertyModifications(text);
            }

            changed = true;
            report.replacedTextCount++;
        }

        return changed;
    }

    private static void SetMaterialPropertyIfPresent(SerializedObject serializedText, string propertyName, Material material)
    {
        if (material == null)
        {
            return;
        }

        SerializedProperty property = serializedText.FindProperty(propertyName);
        if (property != null)
        {
            property.objectReferenceValue = material;
        }
    }

    private static void WarmUp(TMP_FontAsset fontAsset)
    {
        if (fontAsset == null)
        {
            return;
        }

        try
        {
            fontAsset.atlasPopulationMode = AtlasPopulationMode.Dynamic;
            fontAsset.TryAddCharacters(WarmupCharacters, out _);
            EditorUtility.SetDirty(fontAsset);
        }
        catch (Exception ex)
        {
            Debug.LogWarning($"[ThoughtMap TMP Repair] Glyph warmup failed for '{fontAsset.name}': {ex.GetType().Name}: {ex.Message}");
        }
    }

    private static void TuneMaterial(TMP_FontAsset fontAsset)
    {
        Material material = SafeMaterial(fontAsset);
        if (material == null)
        {
            return;
        }

        try
        {
            if (material.HasProperty(ShaderUtilities.ID_OutlineWidth))
            {
                material.SetFloat(ShaderUtilities.ID_OutlineWidth, 0.015f);
            }

            if (material.HasProperty(ShaderUtilities.ID_OutlineSoftness))
            {
                material.SetFloat(ShaderUtilities.ID_OutlineSoftness, 0f);
            }

            if (material.HasProperty(ShaderUtilities.ID_UnderlayOffsetX))
            {
                material.SetFloat(ShaderUtilities.ID_UnderlayOffsetX, 0f);
            }

            if (material.HasProperty(ShaderUtilities.ID_UnderlayOffsetY))
            {
                material.SetFloat(ShaderUtilities.ID_UnderlayOffsetY, 0f);
            }

            if (material.HasProperty(ShaderUtilities.ID_UnderlaySoftness))
            {
                material.SetFloat(ShaderUtilities.ID_UnderlaySoftness, 0f);
            }

            EditorUtility.SetDirty(material);
        }
        catch (Exception ex)
        {
            Debug.LogWarning($"[ThoughtMap TMP Repair] Could not tune TMP material: {ex.GetType().Name}: {ex.Message}");
        }
    }

    private static TMP_FontAsset FindExistingUsableFontAsset()
    {
        string[] guids = AssetDatabase.FindAssets("t:TMP_FontAsset", new[] { "Assets/Fonts", "Assets" });
        foreach (string preferredName in new[] { "Noto Sans JP", "Noto Sans CJK", "BIZ UDPGothic", "BIZ UD", "ThoughtMapJapanese" })
        {
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                TMP_FontAsset asset = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(path);
                if (IsUsableFontAsset(asset) && asset.name.IndexOf(preferredName, StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    WarmUp(asset);
                    return asset;
                }
            }
        }

        foreach (string guid in guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            TMP_FontAsset asset = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(path);
            if (asset != null && asset.name.IndexOf("ARIAL", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                continue;
            }

            if (IsUsableFontAsset(asset))
            {
                WarmUp(asset);
                return asset;
            }
        }

        return null;
    }

    private static bool IsHighQualityFontAsset(TMP_FontAsset fontAsset)
    {
        return IsUsableFontAsset(fontAsset) && GetAtlasMinDimension(fontAsset) >= AtlasSize;
    }

    private static bool IsUsableFontAsset(TMP_FontAsset fontAsset)
    {
        if (fontAsset == null)
        {
            return false;
        }

        try
        {
            if (fontAsset.atlasTextures == null || fontAsset.atlasTextures.Length == 0)
            {
                return false;
            }

            foreach (Texture2D texture in fontAsset.atlasTextures)
            {
                if (texture == null)
                {
                    return false;
                }
            }

            if (fontAsset.material == null)
            {
                return false;
            }

            return fontAsset.atlasPopulationMode == AtlasPopulationMode.Dynamic || fontAsset.characterTable.Count > 0;
        }
        catch
        {
            return false;
        }
    }

    private static int GetAtlasTextureCount(TMP_FontAsset fontAsset)
    {
        try
        {
            return fontAsset == null || fontAsset.atlasTextures == null ? 0 : fontAsset.atlasTextures.Length;
        }
        catch
        {
            return 0;
        }
    }

    private static int GetAtlasMinDimension(TMP_FontAsset fontAsset)
    {
        try
        {
            if (fontAsset == null || fontAsset.atlasTextures == null || fontAsset.atlasTextures.Length == 0 || fontAsset.atlasTextures[0] == null)
            {
                return 0;
            }

            Texture2D texture = fontAsset.atlasTextures[0];
            return Mathf.Min(texture.width, texture.height);
        }
        catch
        {
            return 0;
        }
    }

    private static Material SafeMaterial(TMP_FontAsset fontAsset)
    {
        try
        {
            return fontAsset == null ? null : fontAsset.material;
        }
        catch
        {
            return null;
        }
    }

    private static string[] GetInstalledFontNames()
    {
        try
        {
            return Font.GetOSInstalledFontNames() ?? Array.Empty<string>();
        }
        catch (Exception ex)
        {
            Debug.LogWarning("[ThoughtMap TMP Repair] Font.GetOSInstalledFontNames failed: " + ex.GetType().Name + ": " + ex.Message);
            return Array.Empty<string>();
        }
    }

    private static void EnsureFolder(string path)
    {
        if (AssetDatabase.IsValidFolder(path))
        {
            return;
        }

        string parent = System.IO.Path.GetDirectoryName(path)?.Replace("\\", "/");
        string name = System.IO.Path.GetFileName(path);
        if (!string.IsNullOrEmpty(parent) && !AssetDatabase.IsValidFolder(parent))
        {
            EnsureFolder(parent);
        }

        AssetDatabase.CreateFolder(parent, name);
    }

    private static bool ContainsObjectReference(SerializedProperty arrayProperty, UnityEngine.Object value)
    {
        if (arrayProperty == null || !arrayProperty.isArray || value == null)
        {
            return false;
        }

        for (int i = 0; i < arrayProperty.arraySize; i++)
        {
            if (arrayProperty.GetArrayElementAtIndex(i).objectReferenceValue == value)
            {
                return true;
            }
        }

        return false;
    }

    private struct RepairReport
    {
        public string fontPath;
        public int atlasCount;
        public int atlasMinDimension;
        public bool hasMaterial;
        public int scenesChecked;
        public int scenesSaved;
        public int sceneAssetsChecked;
        public int sceneAssetsSaved;
        public int prefabsChecked;
        public int prefabsSaved;
        public int replacedTextCount;
    }
}
#endif
