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
    private const bool AllowRuntimeFontGenerationWithoutVerifiedFontData = false;

    private static readonly string[] PreferredOsFonts =
    {
        "Yu Gothic UI", "Yu Gothic", "Meiryo", "Microsoft YaHei UI",
        "Microsoft YaHei", "SimSun", "Noto Sans CJK JP", "Noto Sans JP"
    };

    private static TMP_FontAsset cachedRuntimeFont;
    private static bool warned;
    private static bool loggedFontChoice;
    private static bool runtimeGenerationAttempted;

    public static bool RuntimeGenerationAttempted => runtimeGenerationAttempted;

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

        if (cachedRuntimeFont != null && IsUsable(cachedRuntimeFont))
        {
            LogFontChoice("cached runtime", cachedRuntimeFont, true);
            return cachedRuntimeFont;
        }

        if (AllowRuntimeFontGenerationWithoutVerifiedFontData)
        {
            TMP_FontAsset runtimeFont = CreateRuntimeFontAsset();
            if (IsUsable(runtimeFont))
            {
                cachedRuntimeFont = runtimeFont;
                LogFontChoice("runtime generated", cachedRuntimeFont, true);
                return cachedRuntimeFont;
            }
        }
        else if (!warned)
        {
            warned = true;
            Debug.LogWarning("[SourceOfThought Font] Runtime TMP font generation skipped because OS font Include Font Data cannot be verified. Use Assets/Fonts/ThoughtMapJapanese SDF.asset or TMP Settings fallback.");
        }

        if (!warned)
        {
            warned = true;
            Debug.LogWarning("[SourceOfThought Font] No usable TMP font was found. Run ThoughtMap > Repair All TMP Font Assets and assign Assets/Fonts/ThoughtMapJapanese SDF.asset.");
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

            if (IsUsable(text.font))
            {
                continue;
            }

            text.font = resolved;
        }
    }

    private static TMP_FontAsset LoadPersistentRepairFont()
    {
#if UNITY_EDITOR
        return AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(RepairFontPath);
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

    private static TMP_FontAsset CreateRuntimeFontAsset()
    {
        runtimeGenerationAttempted = true;
        foreach (string osFont in PreferredOsFonts)
        {
            try
            {
                Font font = Font.CreateDynamicFontFromOSFont(osFont, 18);
                if (font == null)
                {
                    continue;
                }

                TMP_FontAsset asset = TMP_FontAsset.CreateFontAsset(font, 90, 9, GlyphRenderMode.SDFAA, 1024, 1024);
                if (asset == null)
                {
                    continue;
                }

                asset.name = "SourceOfThoughtRuntimeCJK SDF";
                asset.atlasPopulationMode = AtlasPopulationMode.Dynamic;
                WarmUpRequiredCharacters(asset);
                return asset;
            }
            catch
            {
                // Try the next installed OS font.
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
        Debug.Log($"[SourceOfThought Font] Using FontAsset='{fontAsset.name}' source='{source}' runtimeGenerated={runtimeGenerated}");
    }
}
