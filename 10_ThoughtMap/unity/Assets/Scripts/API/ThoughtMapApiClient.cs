using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class ThoughtMapApiClient : MonoBehaviour
{
    [SerializeField] private string baseUrl = "http://127.0.0.1:8000";

    public IEnumerator Search(string query, Action<ThoughtMapSearchResponse> onSuccess, Action<string> onError)
    {
        if (string.IsNullOrWhiteSpace(query))
        {
            onSuccess?.Invoke(new ThoughtMapSearchResponse { results = new ThoughtMapSearchResult[0] });
            yield break;
        }

        string url = $"{baseUrl}/search?q={UnityWebRequest.EscapeURL(query)}";

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
