using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

public class ThoughtMapApiClient : MonoBehaviour
{
    [SerializeField] private string baseUrl = "http://127.0.0.1:8000";
    [SerializeField] private bool debugSaveFlow = true;
    [SerializeField] private bool debugSearchJson = true;

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

            TryParseSearchResponse(request.downloadHandler.text, onSuccess, onError);
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

        LogSaveFlow($"SaveDefaultDocument called doc_id={result.doc_id}");

        SaveDocumentRequest body = new SaveDocumentRequest
        {
            doc_id = result.doc_id,
            parameters = result.parameters
        };

        string json = JsonUtility.ToJson(body);
        string url = $"{baseUrl}/users/default/save";
        LogSaveFlow($"POST {url} body={json}");
        using (UnityWebRequest request = new UnityWebRequest(url, "POST"))
        {
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            request.uploadHandler = new UploadHandlerRaw(bytes);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json");

            yield return SendJsonRequest(request, onError);
            LogSaveFlow($"POST completed result={request.result} status={request.responseCode} body={(request.downloadHandler == null ? "" : request.downloadHandler.text)}");

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

    private void TryParseSearchResponse(
        string json,
        Action<ThoughtMapSearchResponse> onSuccess,
        Action<string> onError)
    {
        try
        {
            int rawLength = string.IsNullOrEmpty(json) ? 0 : json.Length;
            bool containsParameters = ContainsJsonField(json, "parameters");
            bool containsQueryParameters = ContainsJsonField(json, "query_parameters");
            LogSearchJson(
                "raw length=" + rawLength
                + " contains parameters=" + containsParameters
                + " contains query_parameters=" + containsQueryParameters
            );

            if (!string.IsNullOrEmpty(json))
            {
                string preview = json;
                if (preview.Length > 1000)
                {
                    preview = preview.Substring(0, 1000);
                }

                preview = preview
                    .Replace("\\r", " ")
                    .Replace("\\n", " ")
                    .Replace("\r", " ")
                    .Replace("\n", " ");

                LogSearchJson("raw preview=" + preview);
            }

            ThoughtMapSearchResponse response = JsonUtility.FromJson<ThoughtMapSearchResponse>(json);
            ThoughtMapSearchResult[] results = response == null ? null : response.results;
            int resultCount = results == null ? 0 : results.Length;
            int queryParameterCount = response == null || response.query_parameters == null ? 0 : response.query_parameters.Length;
            LogSearchJson($"parsed result count={resultCount} query_parameter count={queryParameterCount}");

            if (results != null)
            {
                for (int i = 0; i < results.Length; i++)
                {
                    ThoughtMapSearchResult result = results[i];
                    int parameterCount = result == null || result.parameters == null ? 0 : result.parameters.Length;
                    string docId = result == null ? "(null)" : result.doc_id;
                    LogSearchJson(
                        "parsed result index=" + i
                        + " doc_id=" + docId
                        + " parameter count=" + parameterCount
                    );
                }
            }

            onSuccess?.Invoke(response ?? new ThoughtMapSearchResponse { results = new ThoughtMapSearchResult[0] });
        }
        catch (Exception ex)
        {
            onError?.Invoke(ex.Message);
        }
    }

    private bool ContainsJsonField(string json, string fieldName)
    {
        return !string.IsNullOrEmpty(json) && json.Contains("\"" + fieldName + "\"");
    }

    private void LogSearchJson(string message)
    {
        if (debugSearchJson)
        {
            Debug.Log("[ThoughtMap SearchJson][ApiClient:" + GetInstanceID() + "] " + message, this);
        }
    }

    private void LogSaveFlow(string message)
    {
        if (debugSaveFlow)
        {
            Debug.Log($"[ThoughtMap SaveFlow][ApiClient:{GetInstanceID()}] {message}", this);
        }
    }
}
