using System;

[Serializable]
public class ThoughtMapSearchResponse
{
    public ThoughtMapSearchResult[] results;
}

[Serializable]
public class ThoughtMapSearchResult
{
    public string title;
    public string author;
}
