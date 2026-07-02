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
  "results": [
    {
      "doc_id": "gutendex:12345",
      "title": "The Republic",
      "author": "Plato",
      "source": "gutendex",
      "similarity": 0.92
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

### Examples

```text
/search?q=Plato
/search?q=Plato&top=10
/search?q=Plato&mode=keyword
/search?q=Plato&mode=keyword&source=gutendex
/search?q=Plato&mode=hybrid
/search?q=Burn&mode=semantic&source=user_suno
```


## Planned: JSON Filter Selection

Status: Unity placeholder implemented, FastAPI support not implemented yet.

Unity can expose a filter selector backed by `filters/*.json` assets. Until FastAPI support is added, this value is treated as an optional future query parameter and should not change existing `/search` behavior.

Proposed future query parameter:

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `filter` | No | all filters | Name of the selected JSON filter, without requiring the client to know backend file paths. |

Example future request:

```text
/search?q=Plato&mode=semantic&source=gutendex&filter=general
```

## Planned: Parameter Scores

Status: Unity placeholder implemented, FastAPI response support not implemented yet.

Future search or document-detail responses may include parameter scores as key/value rows. This should remain optional so existing Unity result rendering continues to work when scores are absent.

Proposed optional shape:

```json
{
  "key": "philosophy",
  "value": 82.0
}
```

Recommended future location:

- `/document/{doc_id}` for full detail display
- optionally `/search` only if lightweight summary scores are needed in result rows

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
