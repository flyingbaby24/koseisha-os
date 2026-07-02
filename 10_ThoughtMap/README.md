# ThoughtMap

**Spotify maps music. ThoughtMap maps thought.**

ThoughtMap is an experimental project for mapping recurring patterns of thought across large bodies of writing.

Instead of measuring popularity, engagement, or quality, ThoughtMap asks what repeatedly appears in a person's creative output over time.

The project analyzes text collections with sentence embeddings, similarity search, clustering, and 2D map projection. Current datasets include lyrics, notes, essays, public-domain books, classic texts, and legal/philosophical material.

## Current Features

- Text upload and paste-based analysis in Streamlit
- Sentence embedding generation
- Similarity search across works and authors
- KMeans clustering and UMAP thought maps
- CSV export/import workflow
- Official and personal searchable ThoughtMap databases
- Filter/profile views for conceptual categories

## Current Architecture

ThoughtMap is currently organized around a Streamlit prototype, with a backend-agnostic data/search layer beginning to emerge.

```text
10_ThoughtMap/
  data/
    thoughtmap_db/
      official/
      users/
  filters/
  gutendex_books/
  output/
  src/
  web/
    app.py
    storage.py
    search_utils.py
    pages/
      02_Search.py
      03_Personal_Search.py
```

- `web/app.py` is the Streamlit analysis prototype for upload, paste, embedding, clustering, maps, profiles, and CSV export.
- `web/pages/02_Search.py` is the official database similarity search page.
- `web/pages/03_Personal_Search.py` is the personal library similarity search page.
- `web/storage.py` is the backend-agnostic CSV data access layer.
- `web/search_utils.py` contains pure search, vector, normalization, and CSV export helpers.
- `src/` contains older batch scripts and experiments kept for reference.

See [docs/architecture.md](docs/architecture.md) for more detail.

## CSV-Based Workflow

ThoughtMap intentionally still uses CSV as its working storage and interchange format.

Official DB files:

- `data/thoughtmap_db/official/documents_master.csv`
- `data/thoughtmap_db/official/embeddings_master.csv`
- `data/thoughtmap_db/official/map_points_latest.csv`

Personal DB files:

- `data/thoughtmap_db/users/<user_id>/documents.csv`
- `data/thoughtmap_db/users/<user_id>/embeddings.csv`
- `data/thoughtmap_db/users/<user_id>/map_points.csv`
- `data/thoughtmap_db/users/<user_id>/profile.json`

CSV remains useful because it is easy to inspect, manually upload, export, back up, and exchange between tools.

See [docs/data_flow.md](docs/data_flow.md) for the current data flow.

## Role of storage.py

`web/storage.py` is the start of a shared backend data-access layer. It handles CSV loading, model column normalization, lightweight validation, official/personal DB path resolution, and user-library discovery.

`storage.py` must remain backend-agnostic. Do not add Streamlit UI code, `st.cache_data`, sidebar logic, labels, selectboxes, warnings, or page rendering behavior to this module.

Long term, this module should be usable from Streamlit, Unity tooling, Python batch scripts, a web app, or an API server.

## Role of search_utils.py

`web/search_utils.py` contains pure helper logic shared by search pages: text normalization, embedding parsing, cosine similarity, average vectors, ranked similarity result construction, formatting, and CSV row export helpers.

It should stay UI-independent. Do not move Streamlit rendering functions into this file.

## Future Backend Goals

ThoughtMap is currently a Streamlit app, but the data/search backend should eventually be reusable from:

- Streamlit
- Unity
- Python batch scripts
- web applications
- API servers

Possible future directions:

- keep CSV as import/export format
- strengthen validation for larger CSV databases
- define a stable backend API around documents, embeddings, map points, users, and search results
- optionally add SQLite later as a local runtime store
- keep private or large user data out of GitHub when the project grows

SQLite is not the current migration target. The current priority is to keep the CSV workflow stable while making data access and search logic reusable.

## Development Principles

- Keep UI behavior stable while refactoring.
- Keep CSV import/export compatible.
- Keep `storage.py` backend-agnostic.
- Keep `search_utils.py` pure and UI-independent.
- Do not rewrite working Streamlit pages without a specific reason.
- Do not delete legacy scripts until their role is documented and replaced.

## Original Vision

ThoughtMap attempts to measure persistence: not what people say they believe, but what repeatedly emerges from what they create.

## Unity Search UI Wiring

The Unity frontend is a client for the FastAPI search backend. Search rendering should remain UI-only; search logic stays in Python/FastAPI.

Current required scene wiring:

- `ThoughtMapSearchManager`
  - assign `ThoughtMapApiClient`
  - assign `Search Input`
  - assign `Mode Dropdown` with `semantic`, `keyword`, `hybrid`
  - assign `Source Dropdown` with `all`, `gutendex`, `user_suno` or current source names
  - assign `Filter Selector View` when using JSON filter selection
  - assign `Search Button`
  - assign `SearchResultsListView`
  - assign `DetailPanelView`
- `FilterSelectorView`
  - assign a TMP Dropdown
  - assign JSON filter files as `TextAsset` entries when available
  - the selector uses `all` plus the JSON asset names
- `DetailPanelView`
  - assign the existing title, author, source, doc_id, similarity, and body text fields
  - assign `ParameterScoresPanelView` for key/value parameter output
- `ParameterScoresPanelView`
  - assign one TMP Text field inside the parameter output panel

Filter and parameter-score API support is still a placeholder. Unity can select and display these values, but FastAPI support should be added through the API contract before relying on them in production.

## Unity Frontend Setup

The Unity frontend uses FastAPI as the search backend. Scene wiring instructions for the Filter Dropdown, Detail Panel, and Parameter Scores Panel are documented in [unity/README.md](unity/README.md).
