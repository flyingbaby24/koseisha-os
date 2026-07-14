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
    private const string RequiredWarmupCharacters =
        "+-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,;:!?()[]{}_/\\'\"%→" +
        "探求封印孤立回復浸食発動率効果時間味方敵思想共鳴";
    private static readonly string[] PreferredOsFonts =
    {
        "Yu Gothic UI",
        "Meiryo",
        "Noto Sans CJK JP",
        "Yu Gothic",
        "Noto Sans JP",
        "Microsoft YaHei UI",
        "Arial",
        "Liberation Sans"
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
            fontPath = RepairFontPath,
            atlasCount = GetAtlasTextureCountSafe(repairFont),
            hasMaterial = GetMaterialSafe(repairFont) != null
        };

        RegisterTmpSettings(repairFont);
        RepairOpenScenes(repairFont, report);
        RepairAllSceneAssets(repairFont, report);
        RepairAllPrefabs(repairFont, report);

        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();

        Debug.Log(
            "[ThoughtMap TMP Repair] Complete\n" +
            $"FontAsset: {report.fontPath}\n" +
            $"Open scenes checked: {report.scenesChecked}, scenes saved: {report.scenesSaved}\n" +
            $"Scene assets checked: {report.sceneAssetsChecked}, scene assets saved: {report.sceneAssetsSaved}\n" +
            $"Prefabs checked: {report.prefabsChecked}, prefabs saved: {report.prefabsSaved}\n" +
            $"TMP_Text replaced: {report.replacedTextCount}\n" +
            $"atlasTextures: {report.atlasCount}, material: {(report.hasMaterial ? "yes" : "no")}"
        );
    }

    private static TMP_FontAsset EnsureRepairFontAsset()
    {
        EnsureFolder(FontFolder);

        TMP_FontAsset existing = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(RepairFontPath);
        if (IsUsableFontAssetSerialized(existing))
        {
            existing.atlasPopulationMode = AtlasPopulationMode.Dynamic;
            TryWarmUpRequiredGlyphs(existing);
            EditorUtility.SetDirty(existing);
            return existing;
        }

        if (existing != null)
        {
            Debug.Log("[ThoughtMap TMP Repair] Deleting incomplete repair FontAsset before regeneration: " + RepairFontPath);
            AssetDatabase.DeleteAsset(RepairFontPath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        TMP_FontAsset generated = CreateRepairFontAssetFromInstalledFonts(out string successFontName, out string overloadName, out string triedFontsLog);
        if (generated != null)
        {
            AssetDatabase.CreateAsset(generated, RepairFontPath);
            AssetDatabase.SaveAssets();
            AssetDatabase.ImportAsset(RepairFontPath, ImportAssetOptions.ForceUpdate);

            TMP_FontAsset saved = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(RepairFontPath);
            TryWarmUpRequiredGlyphs(saved);
            if (ValidateCreatedRepairFont(saved))
            {
                Debug.Log(
                    "[ThoughtMap TMP Repair] Created persistent TMP FontAsset\n" +
                    $"Path: {RepairFontPath}\n" +
                    $"Tried OS fonts: {triedFontsLog}\n" +
                    $"Success font: {successFontName}\n" +
                    $"CreateFontAsset overload: {overloadName}\n" +
                    $"atlasTextures: {GetAtlasTextureCountSafe(saved)}, material: {(GetMaterialSafe(saved) != null ? "yes" : "no")}"
                );
                return saved;
            }

            Debug.LogWarning("[ThoughtMap TMP Repair] Created asset failed validation. Deleting and trying existing TMP FontAsset fallback.");
            AssetDatabase.DeleteAsset(RepairFontPath);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
        }

        TMP_FontAsset fallback = FindExistingUsableTmpFontAsset();
        if (fallback != null)
        {
            Debug.LogWarning(
                "[ThoughtMap TMP Repair] Could not generate ThoughtMapJapanese SDF. " +
                $"Using existing TMP FontAsset fallback: {AssetDatabase.GetAssetPath(fallback)}"
            );
            return fallback;
        }

        Debug.LogError(
            "[ThoughtMap TMP Repair] All CreateFontAsset attempts failed and no usable existing TMP FontAsset was found.\n" +
            $"Tried OS fonts: {triedFontsLog}"
        );
        return null;
    }

    private static TMP_FontAsset CreateRepairFontAssetFromInstalledFonts(
        out string successFontName,
        out string overloadName,
        out string triedFontsLog)
    {
        successFontName = "";
        overloadName = "";
        List<string> triedFonts = new List<string>();
        string[] installedFontNames = GetInstalledFontNamesSafe();
        HashSet<string> installed = new HashSet<string>(installedFontNames, StringComparer.OrdinalIgnoreCase);

        Debug.Log(
            "[ThoughtMap TMP Repair] Installed OS font count: " + installedFontNames.Length + "\n" +
            "[ThoughtMap TMP Repair] Preferred candidates: " + string.Join(", ", PreferredOsFonts)
        );

        foreach (string osFont in PreferredOsFonts.Where(name => installed.Contains(name)))
        {
            triedFonts.Add(osFont);
            try
            {
                Font font = Font.CreateDynamicFontFromOSFont(osFont, 18);
                Debug.Log(
                    "[ThoughtMap TMP Repair] OS font candidate\n" +
                    $"requested='{osFont}' returnedNull={font == null} " +
                    $"fontName='{(font == null ? "<null>" : font.name)}' dynamic={(font != null && font.dynamic)}"
                );

                if (font != null)
                {
                    TMP_FontAsset asset = CreateFontAssetWithBestAvailableOverload(
                        font,
                        out string usedOverload
                    );
                    overloadName = usedOverload;

                    if (asset == null)
                    {
                        Debug.LogWarning($"[ThoughtMap TMP Repair] TMP_FontAsset.CreateFontAsset returned null for '{osFont}'. Trying next font.");
                        continue;
                    }

                    asset.name = "ThoughtMapJapanese SDF";
                    asset.atlasPopulationMode = AtlasPopulationMode.Dynamic;
                    asset.isMultiAtlasTexturesEnabled = true;

                    if (!ValidateCreatedRepairFont(asset))
                    {
                        Debug.LogWarning(
                            "[ThoughtMap TMP Repair] Generated TMP FontAsset failed validation for " +
                            $"'{osFont}'. atlasTextures={GetAtlasTextureCountDirect(asset)} material={(GetMaterialSafe(asset) != null ? "yes" : "no")}"
                        );
                        continue;
                    }

                    successFontName = osFont;
                    triedFontsLog = string.Join(", ", triedFonts);
                    return asset;
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[ThoughtMap TMP Repair] Font candidate '{osFont}' failed: {ex.GetType().Name}: {ex.Message}");
            }
        }

        string[] missing = PreferredOsFonts.Where(name => !installed.Contains(name)).ToArray();
        if (missing.Length > 0)
        {
            Debug.Log("[ThoughtMap TMP Repair] Preferred OS fonts not installed: " + string.Join(", ", missing));
        }

        triedFontsLog = triedFonts.Count == 0 ? "<none: no preferred exact matches installed>" : string.Join(", ", triedFonts);
        return null;
    }

    private static TMP_FontAsset CreateFontAssetWithBestAvailableOverload(Font font, out string usedOverload)
    {
        usedOverload = "";
        if (font == null)
        {
            return null;
        }

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
                    usedOverload = "TMP_FontAsset.CreateFontAsset(Font, int, int, GlyphRenderMode, int, int, AtlasPopulationMode, bool)";
                    return method.Invoke(
                        null,
                        new object[]
                        {
                            font,
                            90,
                            9,
                            GlyphRenderMode.SDFAA,
                            1024,
                            1024,
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
                if (parameters.Length == 6 &&
                    parameters[0].ParameterType == typeof(Font))
                {
                    usedOverload = "TMP_FontAsset.CreateFontAsset(Font, int, int, GlyphRenderMode, int, int)";
                    TMP_FontAsset asset = method.Invoke(
                        null,
                        new object[]
                        {
                            font,
                            90,
                            9,
                            GlyphRenderMode.SDFAA,
                            1024,
                            1024
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
            Debug.LogWarning($"[ThoughtMap TMP Repair] CreateFontAsset reflection call failed: {ex.GetType().Name}: {ex.Message}");
            return null;
        }

        usedOverload = "<no compatible TMP_FontAsset.CreateFontAsset overload found>";
        return null;
    }

    private static string[] GetInstalledFontNamesSafe()
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

    private static TMP_FontAsset FindExistingUsableTmpFontAsset()
    {
        string[] guids = AssetDatabase.FindAssets("t:TMP_FontAsset", new[] { "Assets" });
        foreach (string guid in guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            if (string.IsNullOrWhiteSpace(path) || path == RepairFontPath)
            {
                continue;
            }

            TMP_FontAsset asset = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(path);
            if (asset != null && asset.name.IndexOf("ARIALUNI", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                continue;
            }

            if (IsUsableFontAssetSerialized(asset))
            {
                TryWarmUpRequiredGlyphs(asset);
                return asset;
            }
        }

        return null;
    }

    private static void RegisterTmpSettings(TMP_FontAsset repairFont)
    {
        TMP_Settings settings = TMP_Settings.instance;
        if (settings == null)
        {
            Debug.LogWarning("[ThoughtMap TMP Repair] TMP_Settings.instance is null. Font references were repaired, but default TMP settings were not updated.");
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
            bool sceneChanged = false;
            foreach (GameObject root in scene.GetRootGameObjects())
            {
                sceneChanged |= RepairTmpTextsInRoot(root, repairFont, report, true);
            }

            if (sceneChanged)
            {
                EditorSceneManager.MarkSceneDirty(scene);
                EditorSceneManager.SaveScene(scene);
                report.scenesSaved++;
            }
        }
    }

    private static void RepairAllSceneAssets(TMP_FontAsset repairFont, RepairReport report)
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
                    bool sceneChanged = false;
                    foreach (GameObject root in scene.GetRootGameObjects())
                    {
                        sceneChanged |= RepairTmpTextsInRoot(root, repairFont, report, true);
                    }

                    if (sceneChanged)
                    {
                        EditorSceneManager.MarkSceneDirty(scene);
                        EditorSceneManager.SaveScene(scene);
                        report.sceneAssetsSaved++;
                    }
                }
                catch (Exception ex)
                {
                    Debug.LogWarning($"[ThoughtMap TMP Repair] Failed to repair scene asset '{path}': {ex.GetType().Name}: {ex.Message}");
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
                Debug.LogWarning("[ThoughtMap TMP Repair] Could not restore previous open scene setup: " + ex.GetType().Name + ": " + ex.Message);
            }
        }
    }

    private static void RepairAllPrefabs(TMP_FontAsset repairFont, RepairReport report)
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
        foreach (TMP_Text text in texts)
        {
            if (text == null)
            {
                continue;
            }

            SerializedObject serializedText = new SerializedObject(text);
            SerializedProperty fontProperty = serializedText.FindProperty("m_fontAsset");
            UnityEngine.Object currentFont = fontProperty == null ? null : fontProperty.objectReferenceValue;

            if (!ShouldReplaceFont(currentFont))
            {
                continue;
            }

            if (fontProperty != null)
            {
                fontProperty.objectReferenceValue = repairFont;
            }

            Material repairMaterial = GetMaterialSafe(repairFont);
            SetMaterialPropertyIfPresent(serializedText, "m_fontSharedMaterial", repairMaterial);
            SetMaterialPropertyIfPresent(serializedText, "m_sharedMaterial", repairMaterial);
            SetMaterialPropertyIfPresent(serializedText, "m_fontMaterial", repairMaterial);

            serializedText.ApplyModifiedPropertiesWithoutUndo();
            ApplyFontPropertySafe(text, repairFont, repairMaterial);
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
        if (serializedText == null || material == null)
        {
            return;
        }

        SerializedProperty property = serializedText.FindProperty(propertyName);
        if (property != null)
        {
            property.objectReferenceValue = material;
        }
    }

    private static void ApplyFontPropertySafe(TMP_Text text, TMP_FontAsset repairFont, Material repairMaterial)
    {
        if (text == null || repairFont == null)
        {
            return;
        }

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
            Debug.LogWarning($"[ThoughtMap TMP Repair] TMP_Text property refresh failed on '{text.name}': {ex.GetType().Name}: {ex.Message}");
        }
    }

    private static bool ShouldReplaceFont(UnityEngine.Object fontObject)
    {
        TMP_FontAsset fontAsset = fontObject as TMP_FontAsset;
        TMP_FontAsset repairFont = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(RepairFontPath);
        if (fontAsset != null && repairFont != null && fontAsset == repairFont && IsUsableFontAssetSerialized(fontAsset))
        {
            return false;
        }

        // Normalize every scene/prefab TMP_Text onto the persistent repair asset.
        // This avoids scene restore failures from broken assets and avoids CJK glyph gaps
        // from otherwise-valid but non-Japanese TMP font assets.
        return true;
    }

    private static bool ValidateCreatedRepairFont(TMP_FontAsset fontAsset)
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

            if (fontAsset.atlasTextures[0] == null)
            {
                return false;
            }

            if (fontAsset.material == null)
            {
                return false;
            }

            if (fontAsset.atlasPopulationMode != AtlasPopulationMode.Dynamic)
            {
                return false;
            }
        }
        catch
        {
            return false;
        }

        return true;
    }

    private static void TryWarmUpRequiredGlyphs(TMP_FontAsset fontAsset)
    {
        if (fontAsset == null)
        {
            return;
        }

        try
        {
            fontAsset.atlasPopulationMode = AtlasPopulationMode.Dynamic;
            bool success = fontAsset.TryAddCharacters(RequiredWarmupCharacters, out string missingCharacters);
            if (!success && !string.IsNullOrEmpty(missingCharacters))
            {
                Debug.LogWarning(
                    "[ThoughtMap TMP Repair] Repair font could not preload some glyphs. " +
                    "The font is still assigned, but these characters may need another OS font: " + missingCharacters
                );
            }
            EditorUtility.SetDirty(fontAsset);
        }
        catch (Exception ex)
        {
            Debug.LogWarning($"[ThoughtMap TMP Repair] Required glyph warmup failed for '{fontAsset.name}': {ex.GetType().Name}: {ex.Message}");
        }
    }

    private static bool IsUsableFontAssetSerialized(TMP_FontAsset fontAsset)
    {
        if (fontAsset == null)
        {
            return false;
        }

        string assetPath = AssetDatabase.GetAssetPath(fontAsset);
        if (string.IsNullOrWhiteSpace(assetPath))
        {
            return false;
        }

        try
        {
            SerializedObject serializedFont = new SerializedObject(fontAsset);
            SerializedProperty atlasTextures = serializedFont.FindProperty("m_AtlasTextures");
            if (atlasTextures == null || !atlasTextures.isArray || atlasTextures.arraySize == 0)
            {
                return false;
            }

            for (int i = 0; i < atlasTextures.arraySize; i++)
            {
                if (atlasTextures.GetArrayElementAtIndex(i).objectReferenceValue == null)
                {
                    return false;
                }
            }

            SerializedProperty material = serializedFont.FindProperty("m_Material");
            if (material != null && material.objectReferenceValue == null)
            {
                return false;
            }
        }
        catch
        {
            return false;
        }

        try
        {
            if (fontAsset.material == null)
            {
                return false;
            }
        }
        catch
        {
            return false;
        }

        return true;
    }

    private static int GetAtlasTextureCountDirect(TMP_FontAsset fontAsset)
    {
        if (fontAsset == null)
        {
            return 0;
        }

        try
        {
            return fontAsset.atlasTextures == null ? 0 : fontAsset.atlasTextures.Length;
        }
        catch
        {
            return 0;
        }
    }

    private static int GetAtlasTextureCountSafe(TMP_FontAsset fontAsset)
    {
        if (fontAsset == null)
        {
            return 0;
        }

        try
        {
            SerializedObject serializedFont = new SerializedObject(fontAsset);
            SerializedProperty atlasTextures = serializedFont.FindProperty("m_AtlasTextures");
            return atlasTextures == null || !atlasTextures.isArray ? 0 : atlasTextures.arraySize;
        }
        catch
        {
            return 0;
        }
    }

    private static Material GetMaterialSafe(TMP_FontAsset fontAsset)
    {
        if (fontAsset == null)
        {
            return null;
        }

        try
        {
            return fontAsset.material;
        }
        catch
        {
            return null;
        }
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

    private static void EnsureFolder(string folderPath)
    {
        string normalized = folderPath.Replace("\\", "/");
        if (AssetDatabase.IsValidFolder(normalized))
        {
            return;
        }

        string[] parts = normalized.Split('/');
        string current = parts[0];
        for (int i = 1; i < parts.Length; i++)
        {
            string next = current + "/" + parts[i];
            if (!AssetDatabase.IsValidFolder(next))
            {
                AssetDatabase.CreateFolder(current, parts[i]);
            }

            current = next;
        }
    }

    private class RepairReport
    {
        public string fontPath;
        public int scenesChecked;
        public int scenesSaved;
        public int sceneAssetsChecked;
        public int sceneAssetsSaved;
        public int prefabsChecked;
        public int prefabsSaved;
        public int replacedTextCount;
        public int atlasCount;
        public bool hasMaterial;
    }
}
#endif
