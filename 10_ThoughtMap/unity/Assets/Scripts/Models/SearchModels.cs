using System;

[Serializable]
public class ThoughtMapSearchResponse
{
    public ThoughtMapSearchResult[] results;
}

[Serializable]
public class ThoughtMapSearchResult
{
    public string doc_id;
    public string title;
    public string author;
    public string source;
    public float similarity;
}
