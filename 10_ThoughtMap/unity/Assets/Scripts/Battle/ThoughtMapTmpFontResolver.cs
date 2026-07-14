using TMPro;
using UnityEngine;
using UnityEngine.TextCore.LowLevel;

public static class ThoughtMapTmpFontResolver
{
    private const string RequiredCharacters =
        "+-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,;:!?()[]{}_/\\'\"%→" +
        "探求封印孤立回復浸食発動率効果時間味方敵思想共鳴";

    private static readonly string[] PreferredOsFonts =
    {
        "Yu Gothic UI", "Yu Gothic", "Meiryo", "Microsoft YaHei UI",
        "Microsoft YaHei", "SimSun", "Noto Sans CJK JP", "Noto Sans JP"
    };

    private static TMP_FontAsset cachedRuntimeFont;
    private static bool warned;

    public static TMP_FontAsset Resolve(TMP_FontAsset preferred)
    {
        if (IsUsable(preferred))
        {
            return preferred;
        }

        if (cachedRuntimeFont != null && IsUsable(cachedRuntimeFont))
        {
            return cachedRuntimeFont;
        }

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
                cachedRuntimeFont = asset;
                return cachedRuntimeFont;
            }
            catch
            {
                // Try the next installed OS font.
            }
        }

        if (!warned)
        {
            warned = true;
            Debug.Log("[SourceOfThought Font] No usable CJK TMP font was found. Assign a Dynamic TMP FontAsset or install Yu Gothic/Meiryo/Noto Sans CJK.");
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

            return fontAsset.atlasPopulationMode == AtlasPopulationMode.Dynamic || fontAsset.characterTable.Count > 0;
        }
        catch
        {
            return false;
        }
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

    public static void ApplyToChildren(GameObject root, TMP_FontAsset preferred)
    {
        TMP_FontAsset resolved = Resolve(preferred);
        if (root == null || resolved == null)
        {
            return;
        }

        TMP_Text[] texts = root.GetComponentsInChildren<TMP_Text>(true);
        foreach (TMP_Text text in texts)
        {
            if (text != null)
            {
                text.font = resolved;
            }
        }
    }
}
