using System;
using System.Collections;
using System.Text;
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
        return Search(query, top, mode, source, "all", onSuccess, onError);
    }

    public IEnumerator Search(
        string query,
        int top,
        string mode,
        string source,
        string filter,
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
        string safeFilter = string.IsNullOrWhiteSpace(filter) ? "all" : filter.Trim();
        string url = $"{baseUrl}/search?q={UnityWebRequest.EscapeURL(query)}&top={safeTop}&mode={UnityWebRequest.EscapeURL(safeMode)}";

        if (!string.Equals(safeSource, "all", StringComparison.OrdinalIgnoreCase))
        {
            url += $"&source={UnityWebRequest.EscapeURL(safeSource)}";
        }

        if (!string.Equals(safeFilter, "all", StringComparison.OrdinalIgnoreCase))
        {
            url += $"&filter={UnityWebRequest.EscapeURL(safeFilter)}";
        }

        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            yield return SendJsonRequest(request, onError);

            if (request.result != UnityWebRequest.Result.Success)
            {
                yield break;
            }

            TryParse(request.downloadHandler.text, onSuccess, onError, new ThoughtMapSearchResponse { results = new ThoughtMapSearchResult[0] });
        }
    }

    public IEnumerator SaveDefaultDocument(
        ThoughtMapSearchResult result,
        Action<SaveDocumentResponse> onSuccess,
        Action<string> onError)
    {
        if (result == null || string.IsNullOrWhiteSpace(result.doc_id))
        {
            onError?.Invoke("No document is selected.");
            yield break;
        }

        SaveDocumentRequest body = new SaveDocumentRequest
        {
            doc_id = result.doc_id,
            parameters = result.parameters
        };

        string json = JsonUtility.ToJson(body);
        using (UnityWebRequest request = new UnityWebRequest($"{baseUrl}/users/default/save", "POST"))
        {
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bytes);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");

            yield return SendJsonRequest(request, onError);

            if (request.result != UnityWebRequest.Result.Success)
            {
                yield break;
            }

            TryParse(request.downloadHandler.text, onSuccess, onError, null);
        }
    }

    public IEnumerator GetDefaultSaved(
        Action<SavedDocumentsResponse> onSuccess,
        Action<string> onError)
    {
        using (UnityWebRequest request = UnityWebRequest.Get($"{baseUrl}/users/default/saved"))
        {
            yield return SendJsonRequest(request, onError);

            if (request.result != UnityWebRequest.Result.Success)
            {
                yield break;
            }

            TryParse(request.downloadHandler.text, onSuccess, onError, new SavedDocumentsResponse { items = new SavedDocument[0] });
        }
    }

    public IEnumerator DeleteDefaultSaved(
        string docId,
        Action<DeleteSavedDocumentResponse> onSuccess,
        Action<string> onError)
    {
        if (string.IsNullOrWhiteSpace(docId))
        {
            onError?.Invoke("doc_id is required.");
            yield break;
        }

        string url = $"{baseUrl}/users/default/saved/{UnityWebRequest.EscapeURL(docId)}";
        using (UnityWebRequest request = UnityWebRequest.Delete(url))
        {
            request.downloadHandler = new DownloadHandlerBuffer();
            yield return SendJsonRequest(request, onError);

            if (request.result != UnityWebRequest.Result.Success)
            {
                yield break;
            }

            TryParse(request.downloadHandler.text, onSuccess, onError, null);
        }
    }

    private IEnumerator SendJsonRequest(UnityWebRequest request, Action<string> onError)
    {
        yield return request.SendWebRequest();

        if (request.result != UnityWebRequest.Result.Success)
        {
            string body = request.downloadHandler == null ? string.Empty : request.downloadHandler.text;
            onError?.Invoke(string.IsNullOrWhiteSpace(body) ? request.error : body);
        }
    }

    private void TryParse<T>(string json, Action<T> onSuccess, Action<string> onError, T fallback) where T : class
    {
        try
        {
            T response = JsonUtility.FromJson<T>(json);
            onSuccess?.Invoke(response ?? fallback);
        }
        catch (Exception ex)
        {
            onError?.Invoke(ex.Message);
        }
    }
}
