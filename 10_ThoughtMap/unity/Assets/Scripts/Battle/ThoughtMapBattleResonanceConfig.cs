using System;
using System.Collections.Generic;
using UnityEngine;

[CreateAssetMenu(fileName = "BattleResonanceConfig", menuName = "Source of Thought/Battle Resonance Config")]
public class ThoughtMapBattleResonanceConfig : ScriptableObject
{
    [Header("Friendly Resonance")]
    [SerializeField] private List<ThoughtMapResonanceModifierBand> statModifierBands = new List<ThoughtMapResonanceModifierBand>
    {
        new ThoughtMapResonanceModifierBand(0.10f, 0.12f),
        new ThoughtMapResonanceModifierBand(0.25f, 0.08f),
        new ThoughtMapResonanceModifierBand(0.50f, 0.04f),
        new ThoughtMapResonanceModifierBand(1.00f, -0.08f),
    };
    [SerializeField] private float minimumTotalStatModifier = -0.20f;
    [SerializeField] private float maximumTotalStatModifier = 0.30f;

    [Header("Hate: Resonance")]
    [SerializeField] private List<ThoughtMapResonanceHateBand> resonanceHateBands = new List<ThoughtMapResonanceHateBand>
    {
        new ThoughtMapResonanceHateBand(0.10f, 1.00f),
        new ThoughtMapResonanceHateBand(0.25f, 1.08f),
        new ThoughtMapResonanceHateBand(0.50f, 1.18f),
        new ThoughtMapResonanceHateBand(1.00f, 1.30f),
    };

    [Header("Hate: Position")]
    [SerializeField] private float sameColumnWeight = 1.30f;
    [SerializeField] private float adjacentColumnWeight = 1.05f;
    [SerializeField] private float farColumnWeight = 0.85f;
    [SerializeField] private float frontDepthWeight = 1.25f;
    [SerializeField] private float backDepthWeight = 0.75f;

    [Header("Hate: Modifiers")]
    [SerializeField] private float randomModifierMin = 0.95f;
    [SerializeField] private float randomModifierMax = 1.05f;
    [SerializeField] private bool debugLogging;

    private static ThoughtMapBattleResonanceConfig runtimeDefault;

    public IReadOnlyList<ThoughtMapResonanceModifierBand> StatModifierBands => statModifierBands;
    public IReadOnlyList<ThoughtMapResonanceHateBand> ResonanceHateBands => resonanceHateBands;
    public float MinimumTotalStatModifier => minimumTotalStatModifier;
    public float MaximumTotalStatModifier => maximumTotalStatModifier;
    public float SameColumnWeight => sameColumnWeight;
    public float AdjacentColumnWeight => adjacentColumnWeight;
    public float FarColumnWeight => farColumnWeight;
    public float FrontDepthWeight => frontDepthWeight;
    public float BackDepthWeight => backDepthWeight;
    public float RandomModifierMin => randomModifierMin;
    public float RandomModifierMax => randomModifierMax;
    public bool DebugLogging => debugLogging;

    public static ThoughtMapBattleResonanceConfig RuntimeDefault
    {
        get
        {
            if (runtimeDefault == null)
            {
                runtimeDefault = CreateInstance<ThoughtMapBattleResonanceConfig>();
            }

            return runtimeDefault;
        }
    }

    public float GetStatModifierForDifference(float difference)
    {
        return GetBandValue(statModifierBands, Mathf.Abs(difference), 0f);
    }

    public float GetHateMultiplierForDifference(float difference)
    {
        return GetBandValue(resonanceHateBands, Mathf.Abs(difference), 1f);
    }

    private static float GetBandValue<TBand>(IEnumerable<TBand> bands, float difference, float fallback)
        where TBand : IThoughtMapResonanceBand
    {
        if (bands == null)
        {
            return fallback;
        }

        float bestMax = float.MaxValue;
        float bestValue = fallback;
        foreach (TBand band in bands)
        {
            if (difference <= band.MaxDifference && band.MaxDifference < bestMax)
            {
                bestMax = band.MaxDifference;
                bestValue = band.Value;
            }
        }

        return bestValue;
    }

    private void OnValidate()
    {
        minimumTotalStatModifier = Mathf.Clamp(minimumTotalStatModifier, -1f, 1f);
        maximumTotalStatModifier = Mathf.Clamp(maximumTotalStatModifier, minimumTotalStatModifier, 2f);
        randomModifierMin = Mathf.Max(0f, randomModifierMin);
        randomModifierMax = Mathf.Max(randomModifierMin, randomModifierMax);
    }
}

public interface IThoughtMapResonanceBand
{
    float MaxDifference { get; }
    float Value { get; }
}

[Serializable]
public struct ThoughtMapResonanceModifierBand : IThoughtMapResonanceBand
{
    [Range(0f, 1f)] public float maxDifference;
    public float statModifier;

    public float MaxDifference => maxDifference;
    public float Value => statModifier;

    public ThoughtMapResonanceModifierBand(float maxDifference, float statModifier)
    {
        this.maxDifference = maxDifference;
        this.statModifier = statModifier;
    }
}

[Serializable]
public struct ThoughtMapResonanceHateBand : IThoughtMapResonanceBand
{
    [Range(0f, 1f)] public float maxDifference;
    public float multiplier;

    public float MaxDifference => maxDifference;
    public float Value => multiplier;

    public ThoughtMapResonanceHateBand(float maxDifference, float multiplier)
    {
        this.maxDifference = maxDifference;
        this.multiplier = multiplier;
    }
}
