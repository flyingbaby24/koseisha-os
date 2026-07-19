using TMPro;
using UnityEngine;
using UnityEngine.TextCore.LowLevel;

#if UNITY_EDITOR
using UnityEditor;
#endif

public static class ThoughtMapTmpFontResolver
{
    private const string RepairFontPath = "Assets/Fonts/ThoughtMapJapanese SDF.asset";
    private const string RequiredCharacters =
        "+-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,;:!?()[]{}_/\\'\"%";
    private static bool warned;
    private static bool loggedFontChoice;

    public static bool RuntimeGenerationAttempted => false;

    public static TMP_FontAsset Resolve(TMP_FontAsset preferred)
    {
        if (IsUsable(preferred))
        {
            LogFontChoice("current/preferred", preferred, false);
            return preferred;
        }

        TMP_FontAsset repairAsset = LoadPersistentRepairFont();
        if (IsUsable(repairAsset))
        {
            LogFontChoice(RepairFontPath, repairAsset, false);
            return repairAsset;
        }

        TMP_FontAsset settingsFont = ResolveFromTmpSettings();
        if (IsUsable(settingsFont))
        {
            LogFontChoice("TMP Settings default/fallback", settingsFont, false);
            return settingsFont;
        }

        if (!warned)
        {
            warned = true;
            Debug.LogWarning("[Battle] No usable persistent TMP font was found under Assets/Fonts or TMP Settings. Runtime TMP font generation is disabled.");
        }

        return null;
    }

    public static bool IsUsable(TMP_FontAsset fontAsset)
    {
        if (fontAsset == null)
        {
            return false;
        }

        try
        {
            if (!string.IsNullOrEmpty(fontAsset.name) &&
                fontAsset.name.ToUpperInvariant().Contains("ARIALUNI"))
            {
                return false;
            }

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

    public static void ApplyToChildren(GameObject root, TMP_FontAsset preferred)
    {
        ApplyToChildren(root, preferred, false);
    }

    public static void ApplyToChildren(GameObject root, TMP_FontAsset preferred, bool force)
    {
        if (root == null)
        {
            return;
        }

        TMP_FontAsset resolved = Resolve(preferred);
        if (resolved == null)
        {
            return;
        }

        TMP_Text[] texts = root.GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in texts)
        {
            if (text == null)
            {
                continue;
            }

            if (!force && IsUsable(text.font))
            {
                continue;
            }

            text.font = resolved;
        }
    }

    private static TMP_FontAsset LoadPersistentRepairFont()
    {
#if UNITY_EDITOR
        TMP_FontAsset fixedAsset = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(RepairFontPath);
        if (IsUsable(fixedAsset))
        {
            return fixedAsset;
        }

        string[] guids = AssetDatabase.FindAssets("t:TMP_FontAsset", new[] { "Assets/Fonts" });
        foreach (string preferredName in new[] { "Noto Sans JP", "BIZ UDPGothic", "BIZ UD", "ThoughtMapJapanese" })
        {
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                TMP_FontAsset asset = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(path);
                if (IsUsable(asset) && asset.name.Contains(preferredName))
                {
                    return asset;
                }
            }
        }

        foreach (string guid in guids)
        {
            string path = AssetDatabase.GUIDToAssetPath(guid);
            TMP_FontAsset asset = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(path);
            if (IsUsable(asset))
            {
                return asset;
            }
        }

        return null;
#else
        return null;
#endif
    }

    private static TMP_FontAsset ResolveFromTmpSettings()
    {
        if (IsUsable(TMP_Settings.defaultFontAsset))
        {
            return TMP_Settings.defaultFontAsset;
        }

        if (TMP_Settings.fallbackFontAssets != null)
        {
            foreach (TMP_FontAsset fallback in TMP_Settings.fallbackFontAssets)
            {
                if (IsUsable(fallback))
                {
                    return fallback;
                }
            }
        }

        return null;
    }

    private static void WarmUpRequiredCharacters(TMP_FontAsset fontAsset)
    {
        if (fontAsset == null)
        {
            return;
        }

        try
        {
            fontAsset.TryAddCharacters(RequiredCharacters, out _);
        }
        catch
        {
            // Runtime font creation is best-effort; Editor repair handles persistent refs.
        }
    }

    private static void LogFontChoice(string source, TMP_FontAsset fontAsset, bool runtimeGenerated)
    {
        if (loggedFontChoice || fontAsset == null)
        {
            return;
        }

        loggedFontChoice = true;
    }
}
