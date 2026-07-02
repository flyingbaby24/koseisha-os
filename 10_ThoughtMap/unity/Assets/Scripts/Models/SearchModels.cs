using System;

[Serializable]
public class ThoughtMapSearchResponse
{
    public ThoughtMapSearchResult[] results;
    public ThoughtMapParameterScore[] query_parameters;
}

[Serializable]
public class ThoughtMapSearchResult
{
    public string doc_id;
    public string title;
    public string author;
    public string source;
    public float similarity;
    public ThoughtMapParameterScore[] parameters;
}

[Serializable]
public class ThoughtMapParameterScore
{
    public string key;
    public float value;
}
