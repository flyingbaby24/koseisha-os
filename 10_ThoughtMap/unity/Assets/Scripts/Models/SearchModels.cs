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
    public string url;
    public ThoughtMapParameterScore[] parameters;
}

[Serializable]
public class ThoughtMapParameterScore
{
    public string key;
    public float value;
}


[Serializable]
public class SaveDocumentRequest
{
    public string doc_id;
    public ThoughtMapParameterScore[] parameters;
}

[Serializable]
public class SaveDocumentResponse
{
    public bool saved;
    public bool duplicate;
    public SavedDocument item;
}

[Serializable]
public class SavedDocument
{
    public string doc_id;
    public string title;
    public string author;
    public string source;
    public string saved_at;
    public string original_doc_id;
    public ThoughtMapParameterScore[] parameters;
}

[Serializable]
public class SavedDocumentsResponse
{
    public SavedDocument[] items;
}

[Serializable]
public class DeleteSavedDocumentResponse
{
    public bool deleted;
    public string doc_id;
}
