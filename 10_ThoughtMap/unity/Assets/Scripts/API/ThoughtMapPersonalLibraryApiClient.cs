using System;
using System.Collections;
using System.Globalization;
using System.Text;
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

                json = NormalizeParameterObjects(json);
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

    private static string NormalizeParameterObjects(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return json;
        }

        const string marker = "\"parameters\"";
        StringBuilder builder = new StringBuilder(json.Length + 256);
        int cursor = 0;
        while (cursor < json.Length)
        {
            int markerIndex = json.IndexOf(marker, cursor, StringComparison.Ordinal);
            if (markerIndex < 0)
            {
                builder.Append(json, cursor, json.Length - cursor);
                break;
            }

            int colonIndex = json.IndexOf(':', markerIndex + marker.Length);
            if (colonIndex < 0)
            {
                builder.Append(json, cursor, json.Length - cursor);
                break;
            }

            int valueStart = colonIndex + 1;
            while (valueStart < json.Length && char.IsWhiteSpace(json[valueStart]))
            {
                valueStart++;
            }

            if (valueStart >= json.Length || json[valueStart] != '{')
            {
                builder.Append(json, cursor, valueStart - cursor);
                cursor = valueStart;
                continue;
            }

            if (!TryFindObjectEnd(json, valueStart, out int objectEnd))
            {
                builder.Append(json, cursor, json.Length - cursor);
                break;
            }

            string objectBody = json.Substring(valueStart + 1, objectEnd - valueStart - 1);
            string parameterArray = ConvertParameterObjectToArray(objectBody);
            builder.Append(json, cursor, valueStart - cursor);
            builder.Append(parameterArray);
            cursor = objectEnd + 1;
        }

        return builder.ToString();
    }

    private static bool TryFindObjectEnd(string json, int objectStart, out int objectEnd)
    {
        bool inString = false;
        bool escaped = false;
        int depth = 0;
        for (int i = objectStart; i < json.Length; i++)
        {
            char ch = json[i];
            if (inString)
            {
                if (escaped)
                {
                    escaped = false;
                }
                else if (ch == '\\')
                {
                    escaped = true;
                }
                else if (ch == '"')
                {
                    inString = false;
                }
                continue;
            }

            if (ch == '"')
            {
                inString = true;
            }
            else if (ch == '{')
            {
                depth++;
            }
            else if (ch == '}')
            {
                depth--;
                if (depth == 0)
                {
                    objectEnd = i;
                    return true;
                }
            }
        }

        objectEnd = -1;
        return false;
    }

    private static string ConvertParameterObjectToArray(string objectBody)
    {
        StringBuilder array = new StringBuilder();
        array.Append('[');
        bool first = true;
        foreach (string pair in SplitTopLevelPairs(objectBody))
        {
            int colon = pair.IndexOf(':');
            if (colon <= 0)
            {
                continue;
            }

            string key = Unquote(pair.Substring(0, colon).Trim());
            string valueText = pair.Substring(colon + 1).Trim();
            if (!float.TryParse(valueText, NumberStyles.Float, CultureInfo.InvariantCulture, out float value))
            {
                continue;
            }

            if (!first)
            {
                array.Append(',');
            }
            first = false;
            array.Append("{\"key\":\"");
            array.Append(EscapeJson(key));
            array.Append("\",\"value\":");
            array.Append(value.ToString(CultureInfo.InvariantCulture));
            array.Append('}');
        }
        array.Append(']');
        return array.ToString();
    }

    private static string[] SplitTopLevelPairs(string value)
    {
        return value.Split(new[] { ',' }, StringSplitOptions.RemoveEmptyEntries);
    }

    private static string Unquote(string value)
    {
        if (value.Length >= 2 && value[0] == '"' && value[value.Length - 1] == '"')
        {
            return value.Substring(1, value.Length - 2);
        }

        return value;
    }

    private static string EscapeJson(string value)
    {
        return (value ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"");
    }
}
