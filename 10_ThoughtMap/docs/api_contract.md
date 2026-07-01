# ThoughtMap API Contract

## SearchIndexRepository Contract

Repository must return:

| Field | Type | Required |
|------|------|----------|
| doc_id | str | ✓ |
| title | str | ✓ |
| author | str | ✓ |
| source | str | ✓ |
| embedding | str | ✓ |
| _embedding_vec | np.ndarray | ✓ |

---

## /search Response

```json
{
  "results": [
    {
      "doc_id": "...",
      "title": "...",
      "author": "...",
      "source": "...",
      "similarity": 0.91
    }
  ]
}
```

---

## CSV Backend

Current backend:

- CSV
- Embedding stored as JSON string
- Repository converts to vector

---

## SQLite Migration

Repository implementation changes only.

Unity API and JSON response should remain unchanged.
