# ThoughtMap Architecture

This document describes the current architecture of `10_ThoughtMap` after the initial storage and search-helper refactors.

## Current Status

ThoughtMap is still primarily a Streamlit application, but the backend boundary is beginning to separate from the UI.

```text
Streamlit UI pages
  -> storage.py for CSV-backed data access
  -> search_utils.py for pure search/vector helpers
  -> CSV files under data/thoughtmap_db
```

## Main Modules

### web/app.py

The main Streamlit prototype for upload, paste, embedding, clustering, maps, profiles, and export controls. It has not been rewritten.

### web/pages/02_Search.py

Official database search page. It owns Streamlit page setup, caching wrappers, official DB search UI, upload comparison UI, official-specific filtering, and result rendering.

### web/pages/03_Personal_Search.py

Personal works search page. It owns Streamlit page setup, caching wrappers, personal library selection UI, upload comparison UI, personal-specific filtering, and result rendering.

### web/storage.py

Backend-agnostic data access layer. It resolves DB paths, discovers user libraries, loads document/embedding/map point CSVs, normalizes model columns, and validates basic frame relationships.

Rules for `storage.py`:

- no Streamlit imports
- no `st.cache_data`
- no UI labels or rendering
- no sidebar/selectbox/page behavior
- no hidden CSV format changes

### web/search_utils.py

Pure search helper module. It normalizes text, parses embeddings, computes similarity, builds ranked result dataframes, formats similarity values, and creates embedding CSV rows.

Rules for `search_utils.py`:

- no Streamlit rendering
- no filesystem path resolution
- no database loading
- no page-specific filtering unless generalized carefully

## Current Boundaries

Stable boundaries:

- CSV loading and validation belongs in `storage.py`.
- Pure vector/search helpers belong in `search_utils.py`.
- Streamlit caching and rendering stay in the pages.
- CSV upload/export remains compatible with the current workflow.

Still mixed:

- `load_uploaded_embeddings` remains in both search pages.
- `filter_catalog` remains page-local because official and personal behavior differ.
- `render_*` functions remain page-local and UI-bound.
- legacy `src/` scripts are not yet organized into the new backend boundary.

## Future Backend Direction

The backend should eventually serve Streamlit, Unity, Python batch scripts, web apps, and API servers. A future backend API should expose documents, embeddings, map points, users/libraries, similarity search, and import/export.

CSV should remain an import/export format even if SQLite or another runtime store is introduced later.

## What Not To Do Yet

- Do not migrate to SQLite just because the project has grown.
- Do not move generated folders until there is a clear data policy.
- Do not delete legacy scripts before documenting replacement workflows.
- Do not move Streamlit rendering into backend modules.
- Do not make `storage.py` depend on Streamlit.
