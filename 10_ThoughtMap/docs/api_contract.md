# ThoughtMap API Contract

This document defines the external API contract used by Unity, future web clients, and backend implementations.

The current public backend is FastAPI. CSV and SQLite are implementation details behind the repository layer, so clients should depend on this contract rather than storage internals.

## SearchIndexRepository Contract

Repository implementations are responsible for loading searchable records from the active backend.

Current implementations:

- CSV backend
- SQLite backend

Future implementations may use other storage engines as long as they preserve the service-level response schema.

## GET /search

Search ThoughtMap documents.

### Query Parameters

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `q` | Yes | none | Search text entered by the user. |
| `top` | No | backend default | Maximum number of results to return. |
| `mode` | No | `semantic` | Search mode. Supported values: `semantic`, `keyword`, `hybrid`. |
| `source` | No | all sources | Optional exact-match source filter, such as `gutendex` or `user_suno`. Omit this parameter to search all sources. |
| `filter` | No | none | Optional JSON parameter filter. `general` loads `filters/general.json` and returns parameter scores for each result. |

### Search Modes

| Mode | Behavior |
| --- | --- |
| `semantic` | Uses embedding similarity. This is the existing default behavior. |
| `keyword` | Uses partial string matching against document metadata such as title, author, source, URL, category, tags, notes, and doc_id. |
| `hybrid` | Prioritizes keyword matches while also using semantic similarity for ranking and fallback results. |

### Response

The response schema must remain stable for Unity and future clients.

```json
{
  "query_parameters": [
    { "key": "philosophy", "value": 74.0 },
    { "key": "psychology", "value": 33.5 }
  ],
  "results": [
    {
      "doc_id": "gutendex:12345",
      "title": "The Republic",
      "author": "Plato",
      "source": "gutendex",
      "similarity": 0.92,
      "url": "https://www.gutenberg.org/ebooks/326",
      "parameters": [
        { "key": "philosophy", "value": 82.0 },
        { "key": "psychology", "value": 21.5 }
      ]
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
| --- | --- | --- |
| `doc_id` | string | Stable document identifier. Source-prefixed IDs are preferred. |
| `title` | string | Display title. |
| `author` | string | Display author or creator. |
| `source` | string | Source namespace, such as `gutendex`, `lyrics`, `note`, or `user_suno`. |
| `similarity` | number | Ranking score returned by the active search mode. Keyword-only results may use a normalized score. |
| `url` | string, optional | Source URL for the document. Uses existing `url`, `source_url`, or `link` metadata when available. Gutendex/Gutenberg URLs may be inferred from doc_id or gutenberg_id. |
| `parameters` | array, optional | Optional key/value parameter scores returned per result only when a supported `filter` is requested. |
| `query_parameters` | array, optional | Optional key/value parameter scores for the search query text itself when a supported `filter` is requested. |

### Examples

```text
/search?q=Plato
/search?q=Plato&top=10
/search?q=Plato&mode=keyword
/search?q=Plato&mode=keyword&source=gutendex
/search?q=Plato&mode=hybrid
/search?q=Burn&mode=semantic&source=user_suno
/search?q=Plato&mode=semantic&source=gutendex&filter=general
```



## Result URLs

Status: implemented as optional `/search` result field.

URL resolution order:

1. `url` column if present
2. `source_url` column if present
3. `link` column if present
4. Gutendex/Gutenberg inference from `gutenberg_id` or numeric `doc_id`

Example inference:

```text
gutendex:doc_000326 -> https://www.gutenberg.org/ebooks/326
```

If no URL can be resolved, `url` is omitted from the response.

## JSON Filter Selection

Status: implemented for `/search` with `filter=general`.

Unity can expose a filter selector backed by `filters/*.json` assets. The selected value is sent as an optional query parameter. When omitted, `/search` keeps the existing response shape.

Current query parameter:

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `filter` | No | all filters | Name of the selected JSON filter, without requiring the client to know backend file paths. |

Example future request:

```text
/search?q=Plato&mode=semantic&source=gutendex&filter=general
```

## Parameter Scores

Status: implemented as optional `/search` response data when `filter=general` is requested.

Search responses may include parameter scores as key/value rows. This remains optional so existing Unity result rendering continues to work when scores are absent. `parameters` describes each result, while `query_parameters` describes the search query text itself.

Optional shape:

```json
{
  "key": "philosophy",
  "value": 82.0
}
```

Current location:

- `/search` when `filter=general` is requested
  - `query_parameters`: scores for the query text
  - `results[].parameters`: scores for each returned document

Recommended future location:

- `/document/{doc_id}` for full detail display when the detail endpoint is added

## Planned: GET /document/{doc_id}

Status: planned, not implemented yet.

This endpoint is reserved for result detail panels in Unity and future web clients. It should fetch one document by stable `doc_id` without changing the `/search` response schema.

Expected future fields:

| Field | Description |
| --- | --- |
| `doc_id` | Stable document identifier. |
| `title` | Full document title. |
| `author` | Author or creator. |
| `source` | Source namespace. |
| `source_url` | Original URL when available. |
| `category` | Optional category metadata. |
| `subcategory` | Optional subcategory metadata. |
| `tags` | Optional tag metadata. |
| `notes` | Optional notes or description. |
| `text_preview` | Optional short excerpt or preview text. |

Current Unity DetailPanel behavior should continue to use the selected search result data until this endpoint is implemented.

## Backend Selection

Backend selection is controlled by environment/configuration, not by Unity.

Current backend values:

- `csv`
- `sqlite`

Unity should call the same `/search` endpoint regardless of backend.

## CSV Backend

The CSV backend reads existing ThoughtMap CSV data. It remains available for manual workflows, local data checks, and migration safety.

## SQLite Backend

The SQLite backend should preserve the same `/search` API response as CSV.

Current MVP storage shape:

- `documents`
- `embeddings`
- `map_points`

Embedding values are currently stored as JSON text.


## Personal Saved Library

Status: MVP implemented for email-based lookup plus legacy `default` compatibility.

Production Personal data is stored in PostgreSQL behind the API when
`THOUGHTMAP_PERSONAL_BACKEND=postgres`. Unity and Streamlit should not depend
on local files, SQLite paths, GitHub, or Zenodo storage locations.

The email-based endpoints are not authentication. The backend normalizes email
with trim/lowercase, hashes it with SHA-256, and uses that hash as the user key.

### POST /users/by-email/save

Save one selected document by `doc_id`.

Request:

```json
{
  "email": "user@example.com",
  "doc_id": "upload_12345678_abcd0001_000000",
  "title": "Uploaded Work",
  "author": "Uploader",
  "source": "upload",
  "category": "",
  "url": "",
  "source_url": "",
  "original_doc_id": "upload_12345678_abcd0001_000000",
  "embedding": [0.1, 0.2, 0.3],
  "source_type": "upload",
  "parameters": [
    { "key": "philosophy", "value": 42.0 }
  ]
}
```

For uploaded or user-generated documents, clients must send the metadata to
save. The server stores the submitted metadata as-is and does not look up the
same `doc_id` in the official database.

Official database lookup is allowed only when the request explicitly sets:

```json
{
  "source_type": "official",
  "doc_id": "gutendex:12345"
}
```

`parameters` may also be sent as an object:

```json
{
  "email": "user@example.com",
  "doc_id": "gutendex:12345",
  "parameters": {
    "philosophy": 42.0
  }
}
```

Duplicate saves are skipped and return `duplicate: true`.

### GET /users/by-email/saved

Query:

```text
/users/by-email/saved?email=user@example.com
```

Response shape is intentionally stable for Unity:

```json
{
  "works": []
}
```

### DELETE /users/by-email/saved/{doc_id}

Query:

```text
/users/by-email/saved/gutendex%3A12345?email=user@example.com
```

### Compatibility Default Routes

The following legacy routes remain available and map to a fixed default user in
the same Personal repository:

- `POST /users/default/save`
- `GET /users/default/saved`
- `DELETE /users/default/saved/{doc_id}`

## Repository Hygiene

The following generated or local files should not become part of the API contract:

- `__pycache__/`
- `*.pyc`
- `.bak_*`
- `thoughtmap.sqlite`
- `output/`

Cleanup policy:

- `__pycache__/` and `*.pyc` can be removed immediately.
- `.bak_*`, `thoughtmap.sqlite`, and `output/` should be handled only after confirming data retention and deployment policy.
- `ToughtMapDemoUI.cs` is a typo-named legacy demo candidate. Delete it only after confirming no Unity scene or prefab references remain.
