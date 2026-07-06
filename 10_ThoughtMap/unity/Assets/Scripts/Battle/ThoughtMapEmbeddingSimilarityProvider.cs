using System.Collections.Generic;

public interface IThoughtMapEmbeddingSimilarityProvider
{
    float GetSimilarity(ThoughtMapBattleCardData a, ThoughtMapBattleCardData b);
}

public class ThoughtMapParameterSimilarityProvider : IThoughtMapEmbeddingSimilarityProvider
{
    private static readonly string[] Parameters =
    {
        "philosophy", "psychology", "science", "economics", "karma",
        "emotion", "morality", "ideal", "individual", "community"
    };

    public float GetSimilarity(ThoughtMapBattleCardData a, ThoughtMapBattleCardData b)
    {
        if (a == null || b == null)
        {
            return 0f;
        }

        float dot = 0f;
        float aNorm = 0f;
        float bNorm = 0f;

        foreach (string parameter in Parameters)
        {
            float av = GetParameter(a.parameterScores, parameter);
            float bv = GetParameter(b.parameterScores, parameter);
            dot += av * bv;
            aNorm += av * av;
            bNorm += bv * bv;
        }

        if (aNorm <= 0f || bNorm <= 0f)
        {
            return 0f;
        }

        return dot / (UnityEngine.Mathf.Sqrt(aNorm) * UnityEngine.Mathf.Sqrt(bNorm));
    }

    private float GetParameter(Dictionary<string, float> scores, string key)
    {
        return scores != null && scores.TryGetValue(key, out float value) ? value : 0f;
    }
}
