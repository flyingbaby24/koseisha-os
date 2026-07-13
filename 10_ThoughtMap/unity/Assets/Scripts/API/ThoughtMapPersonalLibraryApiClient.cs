using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class ThoughtMapPersonalLibraryApiClient : MonoBehaviour
{
    private const string DefaultBaseUrl = "https://koseisha-os.onrender.com";

    [SerializeField] private string baseUrl = DefaultBaseUrl;
    [SerializeField] private int timeoutSeconds = 20;
    [SerializeField] private bool debugResponses;

    public string BaseUrl
    {
        get => string.IsNullOrWhiteSpace(baseUrl) ? DefaultBaseUrl : baseUrl.TrimEnd('/');
        set => baseUrl = string.IsNullOrWhiteSpace(value) ? DefaultBaseUrl : value.TrimEnd('/');
    }

    public IEnumerator GetSavedByEmail(
        string email,
        Action<PersonalLibraryResponse> onSuccess,
        Action<string> onError)
    {
        if (string.IsNullOrWhiteSpace(email))
        {
            onError?.Invoke("Email is required.");
            yield break;
        }

        string url = $"{BaseUrl}/users/by-email/saved?email={UnityWebRequest.EscapeURL(email.Trim())}";
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            request.timeout = Mathf.Max(1, timeoutSeconds);
            yield return request.SendWebRequest();

            if (request.result != UnityWebRequest.Result.Success)
            {
                string body = request.downloadHandler == null ? "" : request.downloadHandler.text;
                onError?.Invoke(string.IsNullOrWhiteSpace(body) ? request.error : body);
                yield break;
            }

            string json = request.downloadHandler == null ? "" : request.downloadHandler.text;
            if (string.IsNullOrWhiteSpace(json))
            {
                onSuccess?.Invoke(new PersonalLibraryResponse { works = new SavedDocument[0] });
                yield break;
            }

            try
            {
                if (json.TrimStart().StartsWith("[", StringComparison.Ordinal))
                {
                    json = "{\"works\":" + json + "}";
                }

                PersonalLibraryResponse response = JsonUtility.FromJson<PersonalLibraryResponse>(json);
                if (response == null)
                {
                    response = new PersonalLibraryResponse { works = new SavedDocument[0] };
                }

                if (debugResponses)
                {
                    Debug.Log($"[PersonalLibraryApi] Loaded works={response.WorksOrItems.Length}.", this);
                }

                onSuccess?.Invoke(response);
            }
            catch (Exception ex)
            {
                onError?.Invoke("Could not parse Personal Library response: " + ex.Message);
            }
        }
    }
}
