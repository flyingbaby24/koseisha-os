using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class ThoughtMapApiClient : MonoBehaviour
{
    [SerializeField] private string baseUrl = "http://127.0.0.1:8000";

    public IEnumerator Search(string query, int top, Action<ThoughtMapSearchResponse> onSuccess, Action<string> onError)
    {
        return Search(query, top, "semantic", "all", onSuccess, onError);
    }

    public IEnumerator Search(
        string query,
        int top,
        string mode,
        string source,
        Action<ThoughtMapSearchResponse> onSuccess,
        Action<string> onError)
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            onSuccess?.Invoke(new ThoughtMapSearchResponse { results = new ThoughtMapSearchResult[0] });
            yield break;
        }

        int safeTop = Mathf.Clamp(top, 1, 50);
        string safeMode = string.IsNullOrWhiteSpace(mode) ? "semantic" : mode.Trim().ToLowerInvariant();
        string safeSource = string.IsNullOrWhiteSpace(source) ? "all" : source.Trim();
        string url = $"{baseUrl}/search?q={UnityWebRequest.EscapeURL(query)}&top={safeTop}&mode={UnityWebRequest.EscapeURL(safeMode)}";

        if (!string.Equals(safeSource, "all", StringComparison.OrdinalIgnoreCase))
        {
            url += $"&source={UnityWebRequest.EscapeURL(safeSource)}";
        }

        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                onError?.Invoke(request.error);
                yield break;
            }

            try
            {
                ThoughtMapSearchResponse response = JsonUtility.FromJson<ThoughtMapSearchResponse>(request.downloadHandler.text);
                onSuccess?.Invoke(response ?? new ThoughtMapSearchResponse { results = new ThoughtMapSearchResult[0] });
            }
            catch (Exception ex)
            {
                onError?.Invoke(ex.Message);
            }
        }
    }
}
