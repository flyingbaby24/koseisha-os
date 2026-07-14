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
        Debug.Log($"[PersonalLibraryApi] Request URL={url}", this);
        Debug.Log($"[PersonalLibraryApi] Request email={email.Trim()}", this);
        using (UnityWebRequest request = UnityWebRequest.Get(url))
        {
            request.timeout = Mathf.Max(1, timeoutSeconds);
            yield return request.SendWebRequest();
            int statusCode = (int)request.responseCode;
            Debug.Log($"[PersonalLibraryApi] HTTP status code={statusCode}", this);

            if (request.result != UnityWebRequest.Result.Success)
            {
                string body = request.downloadHandler == null ? "" : request.downloadHandler.text;
                Debug.LogWarning($"[PersonalLibraryApi] HTTP failure status={statusCode} body_preview={ShortPreview(body, 2000)}", this);
                onError?.Invoke(string.IsNullOrWhiteSpace(body) ? request.error : body);
                yield break;
            }

            string json = request.downloadHandler == null ? "" : request.downloadHandler.text;
            if (string.IsNullOrWhiteSpace(json))
            {
                Debug.LogWarning("[PersonalLibraryApi] Raw response was empty. actual empty response.", this);
                onSuccess?.Invoke(new PersonalLibraryResponse { works = new SavedDocument[0], parse_status = "actual_empty" });
                yield break;
            }

            try
            {
                Debug.Log(
                    "[PersonalLibraryApi] Raw response length=" + json.Length + 
                    " raw preview=" + ShortPreview(json, 2000),
                    this
                );
                Debug.Log("[PersonalLibraryApi] Raw firstWork=" + PreviewFirstWorkObject(json), this);

                if (json.TrimStart().StartsWith("[", StringComparison.Ordinal))
                {
                    json = "{\"works\":" + json + "}";
                }

                int rawWorksCount = CountArrayItems(json, "works");
                int rawItemsCount = CountArrayItems(json, "items");
                Debug.Log($"[PersonalLibraryApi] JSON works count={FormatJsonCount(rawWorksCount)} items count={FormatJsonCount(rawItemsCount)}", this);

                json = NormalizeParameterObjects(json);
                Debug.Log(
                    "[PersonalLibraryApi] Normalized firstWork=" + PreviewFirstWorkObject(json),
                    this
                );

                PersonalLibraryResponse response = ParsePersonalLibraryResponse(json, rawWorksCount, rawItemsCount);
                if (response == null)
                {
                    onError?.Invoke("JSON parse failure: Personal Library response could not be converted.");
                    yield break;
                }

                SavedDocument[] works = response.WorksOrItems;
                Debug.Log($"[PersonalLibraryApi] DTO works null={response.works == null} items null={response.items == null} DTO works count={works.Length} parse_status={response.parse_status}.", this);
                for (int i = 0; i < works.Length; i++)
                {
                    SavedDocument item = works[i];
                    Debug.Log(
                        $"[PersonalLibraryApi] DTO item index={i} doc_id='{item?.doc_id}' title='{item?.title}' parameters_count={CountParameters(item)} direct_parameters={FormatDirectParameters(item)}",
                        this
                    );
                }

                onSuccess?.Invoke(response);
            }
            catch (Exception ex)
            {
                Debug.LogError($"[PersonalLibraryApi] DTO parse exception {ex.GetType().Name}: {ex.Message}", this);
                onError?.Invoke("JSON parse failure: " + ex.Message);
            }
        }
    }

    private static PersonalLibraryResponse ParsePersonalLibraryResponse(string normalizedJson, int rawWorksCount, int rawItemsCount)
    {
        PersonalLibraryResponse response = null;
        Exception wholeParseException = null;
        try
        {
            response = JsonUtility.FromJson<PersonalLibraryResponse>(normalizedJson);
        }
        catch (Exception ex)
        {
            wholeParseException = ex;
        }

        SavedDocument[] wholeWorks = response == null ? null : response.WorksOrItems;
        if (wholeWorks != null && wholeWorks.Length > 0)
        {
            response.parse_status = "whole_response";
            return response;
        }

        if (wholeParseException != null)
        {
            Debug.LogWarning("[PersonalLibraryApi] Whole response JsonUtility parse failed. Trying per-work parse. " + wholeParseException.GetType().Name + ": " + wholeParseException.Message);
        }
        else
        {
            Debug.LogWarning($"[PersonalLibraryApi] Whole response parse produced zero works. Trying per-work parse. rawWorks={FormatJsonCount(rawWorksCount)} rawItems={FormatJsonCount(rawItemsCount)}");
        }

        string arrayName = rawWorksCount >= 0 ? "works" : rawItemsCount >= 0 ? "items" : "";
        string[] objects = string.IsNullOrWhiteSpace(arrayName)
            ? new string[0]
            : ExtractArrayObjects(normalizedJson, arrayName);

        SavedDocument[] parsed = ParseWorkObjects(objects);
        if (parsed.Length > 0)
        {
            return new PersonalLibraryResponse
            {
                works = parsed,
                parse_status = "per_work"
            };
        }

        int rawCount = rawWorksCount >= 0 ? rawWorksCount : rawItemsCount;
        if (rawCount > 0)
        {
            Debug.LogError($"[PersonalLibraryApi] JSON parse failure. Raw {arrayName} count={rawCount}, but DTO count=0.");
            return null;
        }

        return new PersonalLibraryResponse
        {
            works = new SavedDocument[0],
            parse_status = "actual_empty"
        };
    }

    private static SavedDocument[] ParseWorkObjects(string[] objects)
    {
        if (objects == null || objects.Length == 0)
        {
            return new SavedDocument[0];
        }

        System.Collections.Generic.List<SavedDocument> parsed = new System.Collections.Generic.List<SavedDocument>();
        for (int i = 0; i < objects.Length; i++)
        {
            string wrapper = "{\"works\":[" + NormalizeParameterObjects(objects[i]) + "]}";
            try
            {
                PersonalLibraryResponse one = JsonUtility.FromJson<PersonalLibraryResponse>(wrapper);
                SavedDocument[] items = one == null ? null : one.WorksOrItems;
                if (items != null && items.Length > 0 && items[0] != null)
                {
                    parsed.Add(items[0]);
                }
                else
                {
                    Debug.LogWarning($"[PersonalLibraryApi] Per-work parse returned no item at index={i} object_preview={ShortPreview(objects[i], 600)}");
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[PersonalLibraryApi] Per-work parse failed index={i} {ex.GetType().Name}: {ex.Message} object_preview={ShortPreview(objects[i], 600)}");
            }
        }

        return parsed.ToArray();
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

    private static string PreviewFirstWorkObject(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return "<empty>";
        }

        string trimmed = json.TrimStart();
        int start = -1;
        if (trimmed.StartsWith("[", StringComparison.Ordinal))
        {
            start = json.IndexOf('{');
        }
        else
        {
            int worksIndex = json.IndexOf("\"works\"", StringComparison.Ordinal);
            int itemsIndex = json.IndexOf("\"items\"", StringComparison.Ordinal);
            int arrayIndex = -1;
            if (worksIndex >= 0)
            {
                arrayIndex = json.IndexOf('[', worksIndex);
            }
            if (arrayIndex < 0 && itemsIndex >= 0)
            {
                arrayIndex = json.IndexOf('[', itemsIndex);
            }
            if (arrayIndex >= 0)
            {
                start = json.IndexOf('{', arrayIndex);
            }
        }

        if (start < 0 || !TryFindObjectEnd(json, start, out int end))
        {
            return ShortPreview(json);
        }

        return ShortPreview(json.Substring(start, end - start + 1));
    }

    private static string ShortPreview(string value)
    {
        return ShortPreview(value, 1200);
    }

    private static string ShortPreview(string value, int maxLength)
    {
        if (string.IsNullOrEmpty(value))
        {
            return "<empty>";
        }

        string preview = value
            .Replace("\\r", " ")
            .Replace("\\n", " ")
            .Replace("\r", " ")
            .Replace("\n", " ");
        return preview.Length > maxLength ? preview.Substring(0, maxLength) + "..." : preview;
    }

    private static string FormatJsonCount(int count)
    {
        return count < 0 ? "null" : count.ToString(CultureInfo.InvariantCulture);
    }

    private static int CountArrayItems(string json, string propertyName)
    {
        string[] objects = ExtractArrayObjects(json, propertyName);
        return objects == null ? -1 : objects.Length;
    }

    private static string[] ExtractArrayObjects(string json, string propertyName)
    {
        if (string.IsNullOrWhiteSpace(json) || string.IsNullOrWhiteSpace(propertyName))
        {
            return null;
        }

        int propertyIndex = json.IndexOf("\"" + propertyName + "\"", StringComparison.Ordinal);
        if (propertyIndex < 0)
        {
            return null;
        }

        int colonIndex = json.IndexOf(':', propertyIndex);
        if (colonIndex < 0)
        {
            return null;
        }

        int arrayStart = colonIndex + 1;
        while (arrayStart < json.Length && char.IsWhiteSpace(json[arrayStart]))
        {
            arrayStart++;
        }

        if (arrayStart >= json.Length || json[arrayStart] != '[')
        {
            return null;
        }

        if (!TryFindArrayEnd(json, arrayStart, out int arrayEnd))
        {
            return null;
        }

        System.Collections.Generic.List<string> objects = new System.Collections.Generic.List<string>();
        int cursor = arrayStart + 1;
        while (cursor < arrayEnd)
        {
            while (cursor < arrayEnd && (char.IsWhiteSpace(json[cursor]) || json[cursor] == ','))
            {
                cursor++;
            }

            if (cursor >= arrayEnd)
            {
                break;
            }

            if (json[cursor] != '{')
            {
                cursor++;
                continue;
            }

            if (!TryFindObjectEnd(json, cursor, out int objectEnd))
            {
                break;
            }

            objects.Add(json.Substring(cursor, objectEnd - cursor + 1));
            cursor = objectEnd + 1;
        }

        return objects.ToArray();
    }

    private static bool TryFindArrayEnd(string json, int arrayStart, out int arrayEnd)
    {
        bool inString = false;
        bool escaped = false;
        int depth = 0;
        for (int i = arrayStart; i < json.Length; i++)
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
            else if (ch == '[')
            {
                depth++;
            }
            else if (ch == ']')
            {
                depth--;
                if (depth == 0)
                {
                    arrayEnd = i;
                    return true;
                }
            }
        }

        arrayEnd = -1;
        return false;
    }

    private static int CountParameters(SavedDocument document)
    {
        if (document == null)
        {
            return 0;
        }

        int count = document.parameters == null ? 0 : document.parameters.Length;
        if (Mathf.Abs(document.philosophy) > 0.000001f) count++;
        if (Mathf.Abs(document.psychology) > 0.000001f) count++;
        if (Mathf.Abs(document.science) > 0.000001f) count++;
        if (Mathf.Abs(document.economy) > 0.000001f || Mathf.Abs(document.economics) > 0.000001f) count++;
        if (Mathf.Abs(document.karma) > 0.000001f) count++;
        if (Mathf.Abs(document.emotion) > 0.000001f) count++;
        if (Mathf.Abs(document.morality) > 0.000001f || Mathf.Abs(document.moral) > 0.000001f) count++;
        if (Mathf.Abs(document.ideology) > 0.000001f || Mathf.Abs(document.ideal) > 0.000001f) count++;
        if (Mathf.Abs(document.individual) > 0.000001f) count++;
        if (Mathf.Abs(document.community) > 0.000001f) count++;
        return count;
    }

    private static string FormatDirectParameters(SavedDocument document)
    {
        if (document == null)
        {
            return "<null>";
        }

        return $"philosophy:{document.philosophy:0.###}, psychology:{document.psychology:0.###}, science:{document.science:0.###}, economy:{(document.economy != 0f ? document.economy : document.economics):0.###}, karma:{document.karma:0.###}, emotion:{document.emotion:0.###}, morality:{(document.morality != 0f ? document.morality : document.moral):0.###}, ideology:{(document.ideology != 0f ? document.ideology : document.ideal):0.###}, individual:{document.individual:0.###}, community:{document.community:0.###}";
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
