# ThoughtMap Data Flow

This document describes the current CSV-based data flow for `10_ThoughtMap`.

## High-Level Flow

```text
Text files / pasted text / uploaded ZIP
  -> embedding model
  -> document embeddings
  -> clustering / UMAP projection
  -> maps, profiles, search results
  -> CSV and JSON exports
```

For searchable databases:

```text
documents CSV + embeddings CSV + optional map points CSV
  -> storage.py loaders
  -> search page cache wrapper
  -> parsed embedding vectors
  -> similarity search helpers
  -> Streamlit result UI and CSV downloads
```

## Official Database

Location: `data/thoughtmap_db/official/`

Expected files:

- `documents_master.csv`
- `embeddings_master.csv`
- `map_points_latest.csv`

`02_Search.py` resolves the official DB directory through `storage.py`, keeps Streamlit caching in the page, and uses `search_utils.py` for embedding parsing and similarity result construction.

## Personal Database

Location: `data/thoughtmap_db/users/<user_id>/`

Expected files:

- `documents.csv`
- `embeddings.csv`
- `map_points.csv`
- `profile.json`

`03_Personal_Search.py` asks `storage.py` to discover available user libraries. The page keeps Streamlit library selection and rendering behavior.

## Uploaded Embedding CSVs

Search pages still support manual upload of embedding CSV files. Uploaded CSVs are compared against the selected database and are not automatically imported.

This workflow is important and should remain available even if a database backend is added later.

## CSV Column Normalization

`storage.py` normalizes embedding model naming: `model_name` is used when present, `model` is copied to `model_name` when needed, and an empty `model_name` column is added if neither exists.

## Validation

`storage.py` performs lightweight validation for required columns, duplicate document IDs, missing embeddings, orphan embeddings, and orphan map points. Validation prints readable warnings and does not modify CSV files.

## Current CSV Policy

CSV is still the working data format because it is inspectable, easy to export and upload, friendly to batch scripts, easy to back up, and usable across tools.

Future SQLite support should not remove CSV import/export.

## Generated Data

The repository currently contains generated outputs such as maps, reports, cluster CSVs, graph images, and downloaded/public-domain corpus artifacts. These folders are not reorganized yet.
