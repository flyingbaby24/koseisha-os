# ThoughtMap Three.js Migration Plan (Phase T0)

Status: **audit and plan only. No existing behavior code was changed by this phase.**

This document records the audited state of `10_ThoughtMap` before a Three.js +
TypeScript frontend is added under `10_ThoughtMap/threejs/`, and defines the
responsibility split, the invariants, the required new API surface, and the
phase plan.

Scope of the first migration phase is the **`Search / Collect` screen only**.
`Input/Register`, `Battle Prep`, and `Battle` are out of scope and their
boundaries stay fixed as defined in `README.md` -> `Fixed Scene Boundaries`.

---

## 1. Baseline

### 1.1 Git baseline

```text
repository : flyingbaby24/koseisha-os
branch     : main
HEAD       : 06693e5ef478e899afa99d3011647c261c735d75
worktree   : clean at audit start
```

### 1.2 Environment

```text
OS      : Windows 11 (win32)
Python  : 3.13.3  (C:/Users/flyin/AppData/Local/Programs/Python/Python313/python.exe)
          fastapi 0.138.2, pandas 3.0.3, numpy 2.4.6, scikit-learn 1.9.0,
          umap-learn present, sentence-transformers present
Node    : v24.18.0
npm     : 11.16.0
```

`pytest` was not installed in the interpreter and was installed for this audit
(`pytest 8.4.2`, matching `requirements-dev.txt` `pytest>=8,<9`). No project
file was modified to do this.

### 1.3 Python test baseline

Both suites require `PYTHONPATH` to contain **both** `10_ThoughtMap` and
`10_ThoughtMap/web`, because `tests/` imports `web.api.repositories` while
`web/api/repositories.py` imports the top-level module `search_utils`. There is
no `conftest.py`, `pytest.ini`, or `pyproject.toml` in the project, so this must
be supplied by the caller.

```powershell
$root = "<repo>\10_ThoughtMap"
$env:PYTHONPATH = "$root;$root\web"
python -m pytest tests -q
python -m pytest api/tests -q   # run from $root\web
```

Result:

| Suite | Result |
| --- | --- |
| `10_ThoughtMap/tests` | **6 passed, 2 failed** |
| `10_ThoughtMap/web/api/tests` | **15 passed** |

The 2 failures are **pre-existing and reproducible on `main` with a clean
worktree**. They are Windows-specific:

```text
FAILED tests/test_search_filters.py::test_database_source_download_is_mockable_and_atomic
FAILED tests/test_search_filters.py::test_database_source_removes_broken_download
PermissionError: [WinError 32] the file is in use by another process
```

Cause: `web/api/db_source.py::validate_sqlite` uses
`with sqlite3.connect(path) as connection:`. On a `sqlite3.Connection` that
context manager commits/rolls back the transaction; it does **not** close the
connection. The open file handle then blocks `os.replace()` and `Path.unlink()`
on Windows. On POSIX the same code passes because unlinking an open file is
allowed.

This is a real defect in existing Python code, but it is **out of scope for the
Three.js migration** and must not be silently "fixed" as part of it. It is
recorded here as a known baseline failure so that later phases can prove they
did not introduce it. See section 10, Open Decisions.

### 1.4 API smoke-test baseline

Server started locally with the CSV backend:

```powershell
cd 10_ThoughtMap\web
$env:THOUGHTMAP_BACKEND = "csv"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

| Request | Result |
| --- | --- |
| `GET /health` | **200** `{"status":"ok","backend":"csv"}` |
| `GET /search?q=Plato&mode=keyword` | **200**, results with `parameters` |
| `GET /search?q=Plato&mode=semantic` | **500** `ValueError: Unsupported search mode: semantic` |
| `GET /search?q=Plato&mode=hybrid` | **500** `ValueError: target_doc_id is required for hybrid mode.` |
| `GET /search?q=Plato&mode=keyword&filter=general` | **200**, identical to no-filter |
| `GET /search?q=Plato&mode=keyword&source=gutendex` | **200** |
| `GET /users/default/saved` | **200** `{"items":[]}` |

**This is the single most important finding of the audit and it changes the plan.**
Details in section 4.

### 1.5 Dataset baseline

```text
data/thoughtmap_db/official/
  documents_master.csv     4915 rows
  embeddings_master.csv    4915 rows   (384-dim, JSON text)
  parameter_scores.csv     4915 rows
  map_points_latest.csv     331 rows   (stale, x/y/cluster are empty)
  thoughtmap.sqlite        present

documents joined to embeddings on doc_id : 4915 (100%)

sources:
  gutendex    3330
  user_suno    992
  user_note    471
  zip          122

category column: empty for all 4915 rows

parameter_scores columns:
  philosophy, psychology, science, economics, karma,
  emotion, morality, ideal, individual, community
  value range 0.0 .. 1.0, each row sums to 1.0
```

Two consequences:

- The corpus is ~5k documents, not tens of thousands. The performance design
  must still target 10k-100k (per the brief), but the *current* dataset will not
  exercise it. Performance work in T6 must be validated with a synthetic
  oversized set, not only with live data.
- `map_points_latest.csv` is **not** a usable map source. It covers 331 of 4915
  documents and its `x`, `y`, `cluster`, `cluster_label` columns are blank. The
  3D projection pipeline in T3 must be generated fresh; it cannot read this file.

---

## 2. Current architecture

```text
                     data/thoughtmap_db/official/*.csv
                     data/thoughtmap_db/official/thoughtmap.sqlite
                                    |
                    web/storage.py  |  web/search_utils.py
                                    |
                     web/api/repositories.py   (CSV | SQLite)
                                    |
                     web/api/search_service.py (keyword | embedding | hybrid)
                     web/api/user_library_service.py
                     web/api/personal_repository.py (local files | PostgreSQL)
                                    |
                          web/api/main.py  (FastAPI routes + CORS)
                                    |
              +---------------------+----------------------+
              |                                            |
     Unity (ThoughtMapApiClient)               Streamlit web/pages/Search.py
     ThoughtMapRuntimeController                (points at the DEPLOYED API,
     SearchHeaderV2 / ResultListV2               not at this repo's main.py)
     ThoughtMapDetailPanelV2
     ParameterRadarChartView
```

### 2.1 Python layer responsibilities (unchanged by this migration)

| Module | Responsibility |
| --- | --- |
| `web/storage.py` | CSV path resolution, document/embedding/map-point/parameter loading, column normalization, frame validation |
| `web/search_utils.py` | text normalization, embedding parse, cosine, metadata filter, parameter filter, ranked result frames, similarity formatting |
| `web/api/repositories.py` | search-index loading (CSV or SQLite), parameter-score join, `_embedding_vec` preparation |
| `web/api/search_service.py` | filter pipeline, keyword scoring, embedding similarity, hybrid blend, result -> schema mapping, URL resolution |
| `web/api/filter_service.py` | JSON filter definitions -> embeddings -> 0..100 parameter scores. **Currently not wired into `search_service.py` at all.** |
| `web/api/user_library_service.py` | official lookup vs request metadata, Personal save orchestration |
| `web/api/personal_repository.py` | local-file Personal repository, email hashing, parameter key canonicalization |
| `web/api/postgres_personal_repository.py` | PostgreSQL Personal repository |
| `web/api/main.py` | HTTP routes and CORS only |

### 2.2 Unity V2 responsibilities (Search / Collect)

| Component | Responsibility |
| --- | --- |
| `ThoughtMapApiClient` | builds `/search?q&top&mode&source&filter`, omits `source=all` and `filter=all`, parses `ThoughtMapSearchResponse`, save/list/delete on `/users/default/*` |
| `ThoughtMapRuntimeController` | owns the search action, clears result/detail/query panels, dispatches the coroutine, routes result selection to the detail panel, routes Save |
| `SearchHeaderV2View` | query input, mode dropdown, source dropdown, filter dropdown, search button |
| `ResultListV2View` | scrollable result list, `ResultSelected` event |
| `ThoughtMapDetailPanelV2View` | selected document fields, Save button + save state (`SetSaving`/`SetSaved`/`SetSaveError`), Open Link, result parameters, `ShowQueryParameters` |
| `ParameterRadarChartView` | flat 2D radar from `ThoughtMapParameterScore[]`, `maxValue = 40`, animated, vertex labels |
| `QueryParameterPanelView` | query-profile parameter rows |
| `LoadingIndicatorView` | loading state |

Unity default mode string is `"semantic"` (`ThoughtMapApiClient.Search` 2-arg
overload and its `safeMode` fallback).

### 2.3 Streamlit responsibilities

`web/app.py` is the local prototype: upload, paste, split, embed, KMeans,
2D UMAP layout, thought profile, export. It calls `UMAP(n_neighbors=<=15,
min_dist=<slider>, metric="cosine", random_state=42)` and
`KMeans(n_clusters, random_state=42, n_init=10)` on freshly-encoded uploads.
It never writes a map projection back into `data/thoughtmap_db/official/`.

`web/pages/Search.py` is a thin API client. It is hard-coded to
`API_BASE_URL = "https://koseisha-os.onrender.com"` and calls:

- `GET /search` with `q`, `top`, `mode`, `source`, `category`, `filter`,
  `target_doc_id`, `user_email`
- `GET /search/filter-options`
- `GET /users/by-email/saved`

**Neither `/search/filter-options` nor the `category` / `target_doc_id` /
`user_email` query parameters exist in this repository's `web/api/main.py`.**
The deployed API is ahead of the committed route layer. The deployed host was
not reachable from this environment (connection failure), so the deployed
contract could not be confirmed directly; it is inferred from the Streamlit
client code.

---

## 3. Data flow

### 3.1 Search flow (official corpus)

```text
client
  -> GET /search?q&top&mode&source&filter
  -> main.search()
  -> ThoughtMapSearchService.search_response()
  -> repository.load_index()                 (cached in-process after first call)
       documents CSV/SQLite
       INNER JOIN embeddings on doc_id
       LEFT JOIN parameter_scores on doc_id -> row dict in "parameter_scores"
       parse_embedding -> "_embedding_vec", rows without a vector dropped
  -> apply_metadata_filter(source)
  -> apply_metadata_filter(category, multi=True)
  -> apply_parameter_filter(filter)
  -> keyword | embedding | hybrid scoring
  -> _to_search_results() -> SearchResult[]
  -> SearchResponse(results=..., query_parameters=None)
```

### 3.2 Save flow (Personal Library)

```text
client
  -> POST /users/by-email/save  { email, doc_id, source_type, ... }
  -> UserLibraryService.save_document_by_email()
       source_type == "official"  -> look the row up in the official index
       otherwise                  -> build the row from the request body
  -> email_hash_for(email) = sha256(trim(lower(email)))
  -> PersonalRepository.save_document(email_hash, row, saved_at, parameters)
       local  -> documents.csv + embeddings.csv + favorites.json under
                 data/thoughtmap_db/users/<hash>/
       postgres -> Personal tables
  -> SaveDocumentResponse { saved, duplicate, item }
```

`POST /users/default/save` is a compatibility alias that maps to the fixed email
`default@example.local`.

### 3.3 Map data pipeline

**There is currently no map data pipeline serving any client.** The projection
code in `web/app.py` is scoped to an in-session Streamlit upload and its output
never reaches the official DB, the API, or Unity. `map_points_latest.csv` is a
stale artifact. Unity has no map view.

The Three.js Thought Map is therefore new capability, not a port. This is the
one place where new Python is genuinely required (section 6).

---

## 4. API contract: documented vs. actual

`docs/api_contract.md` and the code have drifted. The Three.js client must be
written against the **actual** contract, with the documented one as the target
state.

| Aspect | `docs/api_contract.md` says | Code actually does |
| --- | --- | --- |
| `mode` values | `semantic`, `keyword`, `hybrid` | `main.py` accepts `semantic\|keyword\|hybrid`; `search_service.py` accepts `keyword\|embedding\|hybrid`. `semantic` therefore always raises and returns **500**. |
| `hybrid` | keyword + semantic blend on the query text | requires `target_doc_id`, which `main.py` does not accept -> always **500** |
| default `mode` | `semantic` | `main.py` default is `semantic` -> the default request **500s** |
| `filter=general` | selects `filters/general.json` and returns parameter scores | `search_utils.is_no_filter` treats `""`, `"all"`, and `"general"` as *no filter*. `filter=general` is a no-op. |
| `results[].parameters` | present only when a supported `filter` is requested | present **always**, sourced from the `parameter_scores` CSV/table join, independent of `filter` |
| `query_parameters` | scores for the query text | `search_response()` hard-codes `query_parameters=None`; the field is never populated |
| parameter value scale | `74.0`, `82.0` (0..100) | 0.0..1.0, each document's 10 values sum to 1.0 |
| `/search/filter-options` | not documented | not in `main.py`; `ThoughtMapSearchService.filter_options()` exists but is unrouted; Streamlit calls it on the deployed host |
| `category`, `target_doc_id`, `user_email` | not documented as `/search` params | supported by `search_service.search()`, **not exposed** by `main.py`; Streamlit sends them to the deployed host |

Two further latent defects found while reading, neither triggered by the CSV
backend:

- `repositories.create_search_index_repository` reads
  `settings.official_db_path` and `settings.official_db_url`. **Neither field
  exists on `ApiSettings`.** `THOUGHTMAP_BACKEND=sqlite` will raise
  `AttributeError` in this repo state.
- `filter_service.ParameterFilterService` is fully implemented (0..100 scores
  from `filters/*.json` via the embedding model) and is imported by nothing.
  This is the natural implementation for `query_parameters`, currently dead code.

### 4.1 Parameter scale is ambiguous — the frontend must not hard-code it

Three different scales exist in the codebase for the same 10 axes:

| Source | Scale |
| --- | --- |
| `parameter_scores.csv` (what `/search` actually returns) | 0..1, sums to 1.0 |
| `filter_service._score_to_100` | 0..100 |
| `docs/api_contract.md` examples | 0..100 |
| `ParameterRadarChartView.maxValue` | `40` |

The Three.js `ParameterRadar` must therefore **derive its axis maximum from the
data it is given** (e.g. `max(observed, epsilon)` with a documented fallback),
not assume 0..1 or 0..100. It must render correctly under all three scales
without any change to what the API returns.

### 4.2 Parameter key aliasing

`/search` returns `economics`, `ideal`, `morality`.
`personal_repository.THOUGHT_PARAMETER_KEYS` canonicalizes to `economy`,
`ideology`, `morality` via `THOUGHT_PARAMETER_ALIASES`.

The Three.js client must send parameters through on Save **exactly as `/search`
returned them** and let the server canonicalize. It must also tolerate either
spelling when reading a saved item back from `/users/by-email/saved`.

---

## 5. Responsibility split

### Stays in Python — never ported to TypeScript

- sentence-transformers embedding
- keyword scoring and its per-column exact/partial weights
- cosine similarity and ranked result construction
- hybrid blend weights (`0.8 * similarity + 0.2 * keyword_score`)
- UMAP projection and KMeans clustering
- parameter score computation
- source / category / parameter filter semantics
- official DB (CSV + SQLite) access
- Personal Library persistence and email hashing

### FastAPI

- HTTP boundary and CORS only
- new **read-only** endpoints for map projection and filter options (section 6)

### TypeScript

- application state (query, mode, source, filter, top, results, selection, saved set)
- API client and response types mirroring `web/api/schemas.py`
- UI construction and DOM event handling
- loading / empty / error states

### Three.js

- Thought Map scene, node/edge/cluster rendering
- camera, orbit/pan/zoom, focus and fit
- hover and pick
- search-state visual transitions
- selection highlight

---

## 6. Required new API surface

All additions are **new, read-only, additive**. No existing route, schema field,
or response shape is modified.

### 6.1 `GET /map` — 3D projection (Phase T3)

```json
{
  "projection_version": 1,
  "config": {
    "n_components": 3,
    "n_neighbors": 15,
    "min_dist": 0.2,
    "metric": "cosine",
    "random_state": 42,
    "n_clusters": 12,
    "source": ""
  },
  "nodes": [
    {
      "doc_id": "gutendex:doc_000631",
      "title": "Apology",
      "author": "Plato",
      "source": "gutendex",
      "cluster": 3,
      "x": 0.12,
      "y": -0.53,
      "z": 1.02,
      "parameters": [{ "key": "philosophy", "value": 0.152645 }]
    }
  ]
}
```

Query parameters: `source` (optional, same semantics as `/search?source=`).

Determinism requirements:

- `UMAP(n_components=3, metric="cosine", random_state=42)` and
  `KMeans(random_state=42, n_init=10)`, matching the seeds already used in
  `web/app.py` and `src/`.
- Input row order is fixed by sorting on `doc_id` before fitting, so the
  projection does not depend on CSV row order.
- Same dataset + same config + same seed => byte-identical coordinates.

Caching requirements:

- The projection is computed **once** and written to a cache file keyed by a
  hash of (dataset fingerprint, config). It is not recomputed per request.
- The **2D** path in `web/app.py` and `map_points_latest.csv` are untouched.
  The 3D projection is written to a new file (proposed:
  `data/thoughtmap_db/official/map_points_3d_v1.csv`), never over an existing
  one.
- A CLI generator (`python -m api.generate_map_projection`) produces the cache,
  mirroring the existing `api.generate_parameter_scores` /
  `api.migrate_csv_to_sqlite` script conventions. The endpoint serves the cache
  and fails with a clear message if it is absent, rather than fitting UMAP over
  4915 x 384 floats inside a web request.

### 6.2 `GET /search/filter-options` (Phase T2)

Routes the already-implemented and currently unrouted
`ThoughtMapSearchService.filter_options()`:

```json
{ "sources": ["all", "gutendex", "user_note", "user_suno", "zip"],
  "categories": ["all"],
  "parameters": ["general", "..."] }
```

This is what `web/pages/Search.py` already expects from the deployed API, so
adding it aligns this repo with its own client rather than inventing surface.

Until it exists, the Three.js source/filter selectors fall back to a static list
derived from `filters/*.json` plus the four known sources.

---

## 7. Invariants — must not change

- `10_ThoughtMap/web`, `10_ThoughtMap/web/api`, `10_ThoughtMap/unity` are kept.
  Nothing is deleted; the Unity and Streamlit clients keep working.
- `/search` request parameters and response schema are unchanged.
  `results[]` keeps `doc_id`, `title`, `author`, `source`, `similarity`, `url`,
  `parameters`; `query_parameters` stays optional.
- Personal Library endpoints and the `{"works": [...]}` / `{"items": [...]}`
  shapes are unchanged. Neither the SQLite nor the PostgreSQL schema is altered.
- Embeddings are not regenerated. `embeddings_master.csv` is read-only here.
- Parameter score values and the ranking algorithm are unchanged.
- The existing 2D UMAP path and `map_points_latest.csv` are untouched.
- No existing test's expected values are edited to make it pass.
- `.bak_*` files are never treated as a baseline and never restored over current data.
- No Python search logic is reimplemented in TypeScript.

---

## 8. Target frontend layout

```text
10_ThoughtMap/threejs/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.ts                     wiring only
    api/
      types.ts                  mirrors web/api/schemas.py
      ThoughtMapApiClient.ts
    app/
      AppState.ts               single source of truth
      SearchController.ts
      SelectionController.ts    the ONLY selection path
      CollectionController.ts   Personal Library save state
    scene/
      ThoughtMapScene.ts
      CameraController.ts
      NodeRenderer.ts
      EdgeRenderer.ts
      ClusterRenderer.ts
      SelectionRenderer.ts
      BackgroundRenderer.ts
    ui/
      SearchPanel.ts
      ResultPanel.ts
      DetailPanel.ts
      ParameterRadar.ts         2D canvas, not part of the Three.js scene
      LoadingView.ts
      ToastView.ts
    styles/
      main.css
  tests/
```

Stack: Vite + TypeScript + Three.js directly. No React / Vue / Svelte /
react-three-fiber. If a framework ever becomes necessary, the reason is recorded
in this document before it is added.

Rendering decisions (validated in T6, not assumed now):

- nodes as a single `Points` or `InstancedMesh` draw over one `BufferGeometry`,
  never one `Mesh` per document
- search state applied by writing instance/vertex attribute buffers, never by
  rebuilding the scene
- picking via a reduced candidate set (spatial grid or GPU colour-id pass),
  never a naive raycast against every node
- render on demand: no per-frame work while idle and no per-frame DOM writes

---

## 9. Phase plan

Each phase reports: changed files, tests, build result, known limitations, next phase.

| Phase | Deliverable |
| --- | --- |
| **T0** | *(this document)* audit, baseline, architecture record, contract drift analysis |
| **T1** | Vite + TypeScript + Three.js shell. Empty scene, camera, resize, dark background, build green, `npm run build` with 0 TS errors |
| **T2** | API client + types, Search / Result / Detail parity with Unity V2, loading + error + empty states, `GET /search/filter-options` added |
| **T3** | 3D UMAP projection generator + cache + `GET /map`, Thought Map scene renders the corpus |
| **T4** | Result <-> Node synchronized selection through one `SelectionController`, focus / Fit Results / Fit All / Reset Camera, search-state visual transition |
| **T5** | `ParameterRadar` (query profile + result profile) and Personal Library save / saved-node marking |
| **T6** | Performance: instanced rendering, attribute-only updates, reduced picking, idle-quiet render loop, validated against a synthetic 50k-node set |
| **T7** | Regression run of the Python suites, frontend test run, build, and a written human playtest checklist |

Unity and Streamlit remain fully functional at the end of every phase.

---

## 10. Open decisions — needed before T2 completes

These change what T2 can deliver and are **not** decided unilaterally.

### D1. `mode=semantic` and `mode=hybrid` currently return HTTP 500

The brief specifies a UI with `semantic / keyword / hybrid` switching. Today only
`keyword` works against this repository's API.

- **Option A (default, no backend change):** the Three.js client offers all three
  modes and surfaces the 500 as a clean, non-breaking error state. Only
  `keyword` produces results locally. Nothing in Python changes.
- **Option B (repair, needs approval):** add a query-text semantic path to
  `search_service` so `mode=semantic` encodes `q` with the existing
  sentence-transformers model and ranks by cosine, and make `hybrid` fall back
  to that when `target_doc_id` is absent. This restores what
  `docs/api_contract.md` already documents and what Unity already sends by
  default. It is additive and does not alter any existing successful response,
  but it does change an existing endpoint's behavior from 500 to 200.

**Recommendation: Option A for T2, then Option B as a separate, explicitly
approved T2.5** so that the frontend work and the backend repair stay
independently reviewable and revertible.

### D2. `query_parameters` is never populated

The Parameter Radar "Query Profile" required in section 5 of the brief has no
data source today. `filter_service.ParameterFilterService` implements exactly
this and is unwired. Populating it is the same class of change as D1 (additive,
but it changes an existing endpoint's output from `null` to a value).

**Recommendation:** T5 ships the radar reading `query_parameters` and rendering
an explicit "no query profile available" state when it is `null`. Wiring
`filter_service` is proposed separately alongside D1/Option B.

### D3. Pre-existing Windows test failures

The two `db_source` failures in section 1.3 are a genuine unclosed-connection
bug, unrelated to this migration. Options: leave as-is and keep reporting them
as baseline, or fix separately outside the migration branch.

**Recommendation:** leave them out of the migration entirely and track them as
their own change, so that "6 passed, 2 failed" remains a stable, meaningful
regression baseline for T7.

### D4. `THOUGHTMAP_BACKEND=sqlite` is broken in this repo state

`repositories.py` reads `settings.official_db_path` / `settings.official_db_url`,
which `ApiSettings` does not define. Not triggered by the CSV backend used
throughout this plan. Recorded, not fixed.

---

## 11. Files this migration will and will not touch

Will add:

```text
10_ThoughtMap/docs/threejs-migration-plan.md     (this file)
10_ThoughtMap/threejs/**                          (new frontend)
10_ThoughtMap/web/api/map_service.py              (T3, new)
10_ThoughtMap/web/api/generate_map_projection.py  (T3, new CLI)
data/thoughtmap_db/official/map_points_3d_v1.csv  (T3, generated cache)
```

Will modify, additively only:

```text
10_ThoughtMap/web/api/main.py     new read-only routes: GET /map, GET /search/filter-options
```

Will not touch:

```text
10_ThoughtMap/unity/**
10_ThoughtMap/web/app.py
10_ThoughtMap/web/pages/**
10_ThoughtMap/web/search_utils.py
10_ThoughtMap/web/storage.py
10_ThoughtMap/web/api/search_service.py       (unless D1/Option B is approved)
10_ThoughtMap/web/api/schemas.py              (existing models)
10_ThoughtMap/web/api/repositories.py
10_ThoughtMap/web/api/personal_repository.py
10_ThoughtMap/web/api/postgres_personal_repository.py
10_ThoughtMap/tests/**
10_ThoughtMap/web/api/tests/**
data/thoughtmap_db/**                          (except the new 3D cache file)
filters/**
*.bak / *.bak_*
```

---

# Phase T1.5 — Backend Contract Stabilization

Status: **complete and green.**

Everything in sections 1-11 above is the **historical pre-fix audit** and is left
exactly as recorded. This section records what changed and supersedes the T0
findings only where it says so.

## 12. Historical pre-fix baseline (unchanged, for reference)

```text
HEAD          : 06693e5ef478e899afa99d3011647c261c735d75
root tests    : 6 passed / 2 failed
API tests     : 15 passed
GET /search mode=keyword  : 200
GET /search mode=semantic : 500  ValueError: Unsupported search mode: semantic
GET /search mode=hybrid   : 500  ValueError: target_doc_id is required for hybrid mode.
query_parameters          : always null (hard-coded)
```

## 13. Bugs fixed

### 13.1 `mode=semantic` was unreachable (D1)

`main.py` published `semantic|keyword|hybrid`; `search_service.py` implemented
`keyword|embedding|hybrid`. The names never met, so every `semantic` request —
including the route's own default — raised and returned 500.

**Fix.** Translate at the service boundary, as instructed. The HTTP contract
keeps `semantic`; the internal implementation keeps `embedding`.

```python
PUBLIC_MODE_ALIASES = {"semantic": "embedding"}
...
mode = PUBLIC_MODE_ALIASES.get(mode, mode)
```

### 13.2 `embedding` mode only supported a document origin (D1)

The internal `embedding` mode resolved its comparison vector from
`target_doc_id`. There was no path from query **text** to a vector, which is
what the public `semantic` mode means.

**Fix.** `_query_embedding_search()` encodes the query with the configured model
and ranks through the **existing** `work_similarity_by_vector` +
`format_similarity` pipeline. Ranking maths, cosine, and result construction are
untouched. Stored document embeddings are read as-is and never regenerated.

`target_doc_id` still selects the document-origin path when supplied, so that
behaviour is preserved rather than replaced:

```text
mode=semantic + target_doc_id  -> document-origin similarity (existing, excludes the origin doc)
mode=semantic + q              -> query-text similarity (new)
mode=semantic + neither        -> ValueError -> HTTP 400
```

### 13.3 `mode=hybrid` required `target_doc_id` (D1)

`hybrid` inherited the same document-origin requirement and 500'd for ordinary
query-text searches.

**Fix.** `_hybrid_query_search()` mirrors the existing document-origin hybrid
step for step, substituting the query vector for the target document's vector.
**No new constants were invented** — the existing 0.8/0.2 blend was lifted into
named constants and is now shared by both hybrid paths:

```python
HYBRID_SIMILARITY_WEIGHT = 0.8
HYBRID_KEYWORD_WEIGHT = 0.2
similarity = similarity * 0.8 + keyword_score * 0.2
```

Verified against live data: `The Republic of Plato` scores `0.7360` semantic and
`0.97` keyword, and hybrid returns `0.7360 * 0.8 + 0.97 * 0.2 = 0.7828`.

One documented behaviour was added: when the keyword candidate set is empty,
hybrid falls back to pure semantic ranking. `docs/api_contract.md` already
specifies this for the mode — "prioritizes keyword matches while also using
semantic similarity for ranking and **fallback results**" — and without it a
hybrid query whose words appear in no metadata column returns nothing.

### 13.4 `query_parameters` was hard-coded to `None` (D2)

`search_response()` always passed `query_parameters=None`, so the Query Profile
radar in Unity and the planned Three.js panel had no data source.

**Fix.** New `api/query_profile.py` scores the query text through
**`thought_composition.make_filter_scores`** — the same function
`api/generate_parameter_scores.py` used to produce `parameter_scores.csv`. That
is the decisive point: `query_parameters` and `results[].parameters` now come
from one algorithm and are directly comparable.

`filter_service.py` was **not** used and remains unwired. It implements a
*different* algorithm (per-axis cosine clipped and multiplied by 100, not
row-normalised) and reads a *different* filter directory. Wiring it would have
put the query profile on a scale incompatible with the document scores. See 13.6.

Category-description embeddings are memoised (`CachedCategoryEncoder`) so only
the query itself is encoded per request. `thought_composition` is unmodified.

### 13.5 SQLite handles were released only by the cyclic GC (D3)

`validate_sqlite` used `with sqlite3.connect(path) as connection:`. On a
`Connection`, that context manager commits or rolls back — **it does not close**.

The connection is then only reclaimed by the *cyclic* collector, because a
`Connection` and its statement cache form a reference cycle; plain refcounting
never frees it. Measured directly:

```text
create sqlite via `with sqlite3.connect(...)`, then os.replace()  -> LOCKED
same, with gc.collect() first                                     -> OK
gc.collect() freed 11 objects
```

On Windows an open handle makes `os.replace()`/`unlink()` fail, which is exactly
what the two tests hit.

**Fix.** `contextlib.closing()` gives deterministic ownership — the connection
closes on the way out, including when validation raises:

```python
with closing(sqlite3.connect(path)) as connection:
```

No sleeps, no retries, no `gc.collect()`, no weakened assertions.

That fixed `test_database_source_removes_broken_download`. The second test still
failed because **the test's own `downloader` stub** leaked the same way. Its
connection is created inside the fixture, not in production code, so the
production fix could not reach it. The stub was corrected to use `closing()`
too, and `DownloadFunction` now documents the contract it was violating:

> write the URL's bytes to the destination path and release every handle on it
> before returning.

**Every assertion in both tests is unchanged.** Only the stub's resource
handling was fixed, so it behaves like the real `_download`, which already
released its handle correctly.

### 13.6 Two divergent copies of the filter definitions (new finding)

`10_ThoughtMap/filters/general.json` and `web/filters/general.json` have the
**same ten keys but different description texts**:

```text
filters/general.json      "science": "science, experiment, observation, nature, evidence, technology"
web/filters/general.json  "science": "observation, experiment, evidence, nature, law, biology, physics, discovery"
```

`api/generate_parameter_scores.py` reads `web/filters/`, so
`parameter_scores.csv` — and therefore every `results[].parameters` value — is
derived from the `web/filters/` copy. `filter_service.py` reads the
project-root copy.

`query_profile.py` reads **`web/filters/`**, matching the file the document
scores were generated from. Scoring a query against the other copy would have
made the query profile silently incomparable to the document profiles.

Neither file was edited and no scores were regenerated. Reconciling the two
copies is a separate data decision.

## 14. Canonical parameter scale

**Canonical representation: a Thought Composition. Ten axes, each `0.0`-`1.0`,
summing to `1.0` per document and per query.**

Determined from the generation code, not from documentation.
`thought_composition.make_filter_scores` is the single source of every parameter
value in the system:

```python
scores = cosine_similarity(embeddings, category_embeddings)
scores = np.clip(scores, 0, None)                 # negative similarity -> 0
totals = scores.sum(axis=1, keepdims=True)
scores = np.divide(scores, totals, ...)           # row-normalise -> sums to 1
```

The value is a **share of the total**, not an independent per-axis score. An
axis at `0.14` means "14% of this text's affinity", not "14 out of 100".

Confirmed on live data: `parameter_scores.csv` rows sum to `1.0`, and the live
`/search?q=Plato` response returns `query_parameters` summing to `1.000000` with
`philosophy` highest at `0.1392`.

The ten canonical keys, in `general.json` order:

```text
philosophy, psychology, science, economics, karma,
emotion, morality, ideal, individual, community
```

The other two scales in the codebase are **not** canonical:

| Source | Scale | Verdict |
| --- | --- | --- |
| `thought_composition.make_filter_scores` | 0..1, row-sums to 1 | **canonical** |
| `filter_service._score_to_100` | 0..100, independent per axis | unwired dead code, different algorithm |
| `docs/api_contract.md` examples (`74.0`, `82.0`) | 0..100 | stale documentation, never matched the data |
| Unity `ParameterRadarChartView.maxValue = 40` | assumes ~0..40 | stale UI assumption |

Nothing was renormalised to satisfy the stale assumptions, as instructed.

**Consequence for the Three.js radar (T5).** With ten axes summing to 1.0, a
perfectly flat profile sits at `0.1` on every axis and the practical maximum for
a single dominant axis is well below 1.0. A fixed `0..1` axis would render every
profile as a tiny blob near the centre. The radar must scale to the data —
derive the axis maximum from the observed values with a sane floor — which is
what section 4.1 already required. The scale is now *known*, not merely
"ambiguous".

## 15. `filter=general` — intentional, not drift

**Verdict: intentional. Keep it. No contradiction, so nothing was changed.**

`search_utils.is_no_filter` treats `""`, `"all"`, and `"general"` alike, so
`filter=general` does not narrow the result set. This is coherent rather than
accidental:

- `apply_parameter_filter` narrows to works whose *representative* (highest)
  parameter is the selected one, e.g. `filter=philosophy`.
- `general` names the **whole ten-axis definition set**, not one axis. Selecting
  every axis narrows nothing.
- The existing test asserts this explicitly:
  `assert len(apply_parameter_filter(frame, "general")) == 3`.
- `docs/api_contract.md` describes `filter=general` as loading
  `filters/general.json` and *returning parameter scores*. It never claims the
  result set is narrowed.

One genuine, non-breaking divergence remains: the contract says
`results[].parameters` appear *only when* a filter is requested, whereas they
are returned on every response from the `parameter_scores` join. That is a
superset of the documented behaviour and breaks no client. Left as is.

## 16. Deployed-route drift inventory

`web/pages/Search.py` targets the deployed host
`https://koseisha-os.onrender.com`, which was **unreachable from this
environment** (connection failure), so the deployed contract could only be
inferred from the committed client code. Nothing was copied from it blindly.

| Surface | Used by | Required by committed app? | T1.5 action |
| --- | --- | --- | --- |
| `target_doc_id` on `/search` | `web/pages/Search.py`; `search_service` already implements it | Yes — D1 requires preserving the document-origin path | **Exposed** as an optional query param |
| `user_email` on `/search` | `web/pages/Search.py`; needed to resolve personal embeddings for the document-origin path | Yes — `target_doc_id` is useless for personal docs without it | **Exposed** as an optional query param |
| `category` on `/search` | `web/pages/Search.py`; `search_service.search()` implements it | No — the official `category` column is empty for all 4915 rows, so it would filter nothing | **Not added.** Deferred |
| `GET /search/filter-options` | `web/pages/Search.py`; `ThoughtMapSearchService.filter_options()` exists but is unrouted | No — not needed by D1/D2 | **Not added.** Deferred to T2 |

Both additions are optional parameters defaulting to `""`. No existing request
shape changes, and no route was added.

The repository stays the source of truth. `category` and `/search/filter-options`
are recorded as known drift for T2 to decide on, not adopted by default.

## 17. Changed files

Modified (5):

```text
web/api/search_service.py    semantic alias, query-text semantic + hybrid paths,
                             named hybrid weights, query_parameters wiring
web/api/main.py              optional target_doc_id/user_email, ValueError -> 400,
                             EmbeddingModelUnavailableError -> 503
web/api/db_source.py         closing() for deterministic connection ownership,
                             DownloadFunction contract documented
web/requirements-api.txt     sentence-transformers + torch, with a note that they
                             are lazily imported and optional for keyword-only
tests/test_search_filters.py downloader stub releases its handle (assertions
                             unchanged)
```

Added (3):

```text
web/api/embedding_model.py              lazy cached model loader,
                                        EmbeddingModelUnavailableError,
                                        CachedCategoryEncoder
web/api/query_profile.py                QueryProfileService over thought_composition
web/api/tests/test_search_contract.py   35 new contract tests
```

Not touched: `search_utils.py`, `storage.py`, `thought_composition.py`,
`repositories.py`, `schemas.py`, `personal_repository.py`,
`postgres_personal_repository.py`, `user_library_service.py`,
`filter_service.py`, `web/app.py`, `web/pages/**`, `unity/**`, all CSV/SQLite
data, `filters/**`, and the entire `threejs/` frontend.

## 18. New tests

`web/api/tests/test_search_contract.py` — 35 tests over four groups. A
deterministic fake encoder (sha256-seeded, so it is stable across processes)
stands in for sentence-transformers, keeping the suite fast and torch-free. The
real model is covered by the live smoke run in section 19.

- **modes**: keyword; semantic without `target_doc_id`; `semantic` and
  `embedding` produce identical output; semantic ranks the whole index; hybrid
  without `target_doc_id`; hybrid prefers keyword matches; hybrid fallback;
  hybrid blend reproduces `0.8/0.2` arithmetically; `target_doc_id` path
  preserved and still excludes the origin document; unsupported mode; empty
  query per mode
- **filters/schema**: `top` in all three modes; `source` in all three modes;
  no-match source; response schema exactly `{results, query_parameters}` and
  `{doc_id, title, author, source, similarity, url, parameters}`; URL resolution
- **query profile**: populated for a normal query; the ten canonical keys in
  order; finite and within `0..1`; sums to `1.0` (tolerance-based, not exact
  float equality); deterministic across repeated identical queries; empty query
  yields none; missing model degrades to no profile while keyword search keeps
  working
- **HTTP**: all three public modes 200; results ranked and non-empty;
  `query_parameters` present with 10 entries; default mode succeeds;
  unsupported mode 422; missing/empty `q` 422; out-of-range `top` 422;
  whitespace `q` 400; missing model 503; `source`/`top` honoured over HTTP

No existing test's expected values were altered.

## 19. Verification gate results

### Python

| Suite | Before (T0) | After (T1.5) |
| --- | --- | --- |
| `10_ThoughtMap/tests` | 6 passed, **2 failed** | **8 passed, 0 failed** |
| `10_ThoughtMap/web/api/tests` | 15 passed | **50 passed, 0 failed** |

Both previously failing Windows tests now pass.

### Live API smoke

Against a real uvicorn process (`THOUGHTMAP_BACKEND=csv`, 4915 documents, real
`paraphrase-multilingual-MiniLM-L12-v2`):

| Request | Before | After | Top result |
| --- | --- | --- | --- |
| `GET /health` | 200 | **200** | — |
| `/search?q=Plato&mode=keyword` | 200 | **200** | `Apology` / Plato, 0.9700 |
| `/search?q=Plato&mode=semantic` | **500** | **200** | `The Republic of Plato` / Plato, 0.7360 |
| `/search?q=Plato&mode=hybrid` | **500** | **200** | `The Republic of Plato` / Plato, 0.7828 |

Schema and behaviour verified, not just status codes:

```text
top-level keys      : ["query_parameters", "results"]
result keys         : no extra, none missing
results             : 10 per mode, similarity sorted descending
semantic range      : 0.6268 .. 0.7360   (genuine ranking, not placeholders)
hybrid range        : 0.6926 .. 0.7828
hybrid arithmetic   : 0.7360*0.8 + 0.97*0.2 = 0.7828  OK
query_parameters    : 10 keys, sum = 1.000000, range 0.0466 .. 0.1392
                      top axes for "Plato": philosophy 0.1392, ideal 0.1385, science 0.1178
determinism         : identical result order and identical query_parameters on repeat
top=3               : honoured
source=user_suno    : honoured
mode=telepathy      : 422
missing q           : 422
```

### Three.js regression

Unchanged by this phase — no frontend file was edited to accommodate the backend
fixes.

```text
tsc --noEmit   0 errors
vitest         9 passed
npm run build  success (identical bundle hash to T1)
```

## 20. New green baseline

```text
root tests    : 8 passed / 0 failed
API tests     : 50 passed / 0 failed
GET /health                       : 200
GET /search?q=Plato&mode=keyword  : 200
GET /search?q=Plato&mode=semantic : 200
GET /search?q=Plato&mode=hybrid   : 200
query_parameters                  : populated, 10 canonical keys, sums to 1.0
canonical parameter scale         : 0.0-1.0 composition, row-sum 1.0
Windows SQLite handles            : deterministically closed via closing()
Three.js                          : tsc 0 errors, 9 tests, build OK
```

## 21. Remaining contract drift after T1.5

Recorded, deliberately not addressed in this phase.

1. **`docs/api_contract.md` parameter examples are stale.** They show `74.0` /
   `82.0` on a 0..100 scale; the real contract is the 0..1 composition of
   section 14. The document also says `results[].parameters` appear only with a
   filter, but they are always present. Worth a documentation pass.
2. **Unity `ParameterRadarChartView.maxValue = 40`** cannot render 0..1
   compositions meaningfully. Unity now receives a populated `query_parameters`
   for the first time, so its Query Profile radar will draw a near-flat shape
   until that scale is revisited. No Unity file was changed in T1.5.
3. **`filter_service.py` remains unwired dead code** implementing a second,
   non-canonical parameter algorithm against the divergent filter directory. It
   should be deleted or reconciled, not wired.
4. **Two divergent `general.json` copies** (section 13.6).
5. **`THOUGHTMAP_BACKEND=sqlite` is still broken.** `repositories.py` reads
   `settings.official_db_path` / `settings.official_db_url`, neither of which
   exists on `ApiSettings`. Untouched — the CSV backend is what every phase so
   far uses, and fixing it needs a decision about where the official SQLite is
   hosted.
6. **The same unclosed-connection pattern remains in `repositories.py`,
   `user_embedding_sqlite.py`, and `migrate_csv_to_sqlite.py`.** Those paths do
   not currently replace or unlink the file, so no test fails, but the pattern
   is the same latent Windows hazard fixed in `db_source.py`.
7. **First-request latency.** Because `query_parameters` needs the model, the
   first `/search` of any mode now pays the model load — measured **~60 s** cold,
   then **0.3-0.5 s** warm. A startup warm-up or background preload would hide
   this; not added, since it changes startup behaviour.
8. **`sentence-transformers` + `torch` added to `requirements-api.txt`.** This
   substantially increases deployment size. The imports are lazy, so a
   size-constrained deployment can drop those two lines and run keyword-only:
   semantic/hybrid then answer **503** and `query_parameters` is `null`, rather
   than crashing. **This needs a deployment decision before the next deploy.**
9. **Duplicate documents in the corpus.** `Symposium` appears twice in the live
   results with identical scores. A data-hygiene issue, not an API one.
10. **`category` and `GET /search/filter-options`** remain unimplemented
    locally (section 16).

---

# Phase T3 — 3D Thought Space Projection + Map Rendering

Status: complete. T1.5 and T2 records above are unchanged.

## 22. Projection configuration audit

The historical scripts were read before anything was chosen. A canonical
document-level configuration already existed and is reused unchanged.

| Setting | Value | Source |
| --- | --- | --- |
| algorithm | UMAP | `src/Lyrics/00_embed.py`, `01_title_map.py`, `04_cluster_export.py`, and the matching `src/note/` scripts |
| `metric` | `cosine` | same, all six files agree |
| `n_neighbors` | 10 | same, all six files agree |
| `min_dist` | 0.2 | same, all six files agree |
| `random_state` | 42 | same, and every KMeans call in the repo |
| cluster algorithm | KMeans | `src/Lyrics/03_cluster.py`, `04_cluster_export.py`, `src/note/003_cluster.py`, `004_cluster_export.py` |
| `n_clusters` | 8 | same — `cluster_count = 8` and hard-coded `n_clusters=8` |
| `n_init` | 10 | `04_cluster_export.py` (the scripts that actually export labels) |

Only `n_components = 3` is new. Every historical script is 2D.

Two configurations were deliberately **not** adopted:

- `06_cluster_map.py` uses `n_neighbors=3, min_dist=0.3`, but its input is the
  eight cluster centroids, not documents. It does not describe a document
  layout.
- `web/app.py` uses `n_neighbors=min(15, count-1)` with a slider-driven
  `min_dist`. That is the ad-hoc Streamlit upload path, not the official corpus.

Clustering is done in **embedding space**, not projection space, matching
`04_cluster_export.py`.

## 23. Pipeline

```text
documents_master.csv + embeddings_master.csv
        |  create_search_index_repository()   <- the same repository /search uses
ProjectionGenerator
        |  validate -> fingerprint -> UMAP(3D) -> KMeans(8)
        |  validate again
map_projection_3d.json                        <- atomic write
        |  MapService (parse once per file version)
GET /map                                      <- never runs UMAP
        |
NodeRenderer (THREE.Points, one draw call)
```

Reading through the search repository is deliberate: the map and the search
results are guaranteed to describe the same document set, which is what makes
the `doc_id` join in T4 safe.

## 24. Artifact

- Location: `data/thoughtmap_db/official/map_projection_3d.json`
- Schema version: 1
- Size: 926,348 bytes (0.88 MB) for 4,915 documents
- Coordinates rounded to 6 decimals — deterministic, and about a third smaller

The legacy `map_points_latest.csv` is untouched. It was never a valid baseline:
331 of 4,915 rows, with blank `x`, `y` and `cluster`.

Generation, run from `10_ThoughtMap/web`:

```bash
python -m api.generate_map_projection --verbose
```

Flags exist for every config field plus `--dry-run`. This is offline work; the
API never triggers it.

## 25. Dataset fingerprint

`sha256` over, in order: a version tag, the JSON-serialised projection config,
then every `(doc_id, float32 embedding bytes)` pair **sorted by doc_id**.

Detects: document identity changes, embedding changes, added or removed
documents, and any projection-config change.

Deliberately excluded: `title`, `author`, `source` and every other display
field. None of them can move a node. A title correction therefore does not
invalidate the geometry — regenerate to refresh the labels the artifact
carries, but the coordinates are unaffected. Sorting makes the fingerprint
independent of CSV row order.

Current corpus fingerprint:
`8fbea92438ede7a9210df6d610e94ba58f34a0e0b741b2342a58af723ce10182`

## 26. Cache invalidation

`MapService` keys its in-memory copy on `(path, st_mtime_ns, st_size)`.

- Repeated requests against an unchanged file reuse the parsed object; the file
  is read and validated once.
- Regenerating the artifact changes mtime and size, so the next request picks it
  up with **no restart**.
- There is no TTL and no time-based expiry: if the bytes have not changed,
  neither has the answer. This is why there is no hidden staleness.

## 27. `/map` contract

`GET /map` — read-only, additive. `/search` is unchanged.

```json
{
  "schema_version": 1,
  "projection": {
    "generated_at": "...", "dataset_fingerprint": "...",
    "document_count": 4915, "embedding_dimension": 384,
    "dimensions": 3, "algorithm": "umap", "n_components": 3,
    "metric": "cosine", "n_neighbors": 10, "min_dist": 0.2,
    "random_seed": 42, "cluster_algorithm": "kmeans", "cluster_count": 8
  },
  "nodes": [
    { "doc_id": "...", "title": "...", "author": "...", "source": "...",
      "x": 0.0, "y": 0.0, "z": 0.0, "cluster": 0 }
  ]
}
```

`503` when the artifact is absent or unreadable, with a message naming the
generation command. A missing projection never triggers a fit inside a request,
and never affects `/search`.

`MapNode` is intentionally **not** a `SearchResult`: no `similarity`, no
`parameters`, no `url`. They are two representations of one document and they
join on `doc_id`.

## 28. Frontend rendering strategy

`THREE.Points` + `BufferGeometry`, one object for the whole corpus.

Chosen over `InstancedMesh` because:

- Three floats per node. 4,915 documents is ~59 KB of position data; the same
  corpus as instanced meshes needs a 16-float matrix each (~315 KB) plus real
  sphere geometry, for dots a few pixels wide.
- Measured: 50,000 synthetic nodes render in 5.6 ms/frame as **4 scene
  objects**.
- `gl_PointSize` attenuation supplies the depth cue for free.

`InstancedMesh` would only win if nodes needed genuine 3D form, per-node
rotation, or lighting. Its cheap per-instance raycasting is not decisive
either: T4 resolves a pick to a *buffer index* via `NodeIndex`, which works
identically for both.

Point size is computed in real device pixels:
`uPointWorldSize * bufferHeight / (2*tan(fov/2)) / -mvPosition.z`, resynced on
every resize. An earlier constant-based formula produced sub-pixel points that
were drawn, counted by the renderer, and invisible.

Blending is normal with depth writing, not additive: additive saturates dense
regions to flat white and destroys the density structure the map exists to show.

### Coordinate handling

Buffers hold **raw projection coordinates**. The presentation transform — one
uniform scale to `TARGET_WORLD_EXTENT` (100) plus a centre offset — lives on the
object's `scale` and `position`. The three axes are never scaled independently;
doing so would stretch the space and misstate semantic distance.

### Identity mapping

`NodeIndex` holds `nodeIndexToDocId[]` and `docIdToNodeIndex`. Object names are
not usable for this, because the whole cloud is one object. Verified live:
every one of 10 search results joined to a map node by `doc_id`.

## 29. Real generation results

| Measure | Value |
| --- | --- |
| Input documents | 4,915 |
| Embeddings | 4,915 (1:1, validated) |
| Embedding dimension | 384 |
| Projected nodes | **4,915 — no document dropped** |
| Runtime | 92.1 s |
| Artifact size | 0.88 MB |
| x bounds | -4.2915 to 14.9359 (var 12.61) |
| y bounds | -2.6504 to 16.9066 (var 47.33) |
| z bounds | -9.9655 to 15.1324 (var 26.82) |
| Bounding radius | 17.16 |

Axis extents 19.23 / 19.56 / 25.10 — genuinely volumetric, not near-planar.

Cluster populations (k=8): `2:3332, 5:333, 7:287, 0:277, 1:226, 3:198, 4:187, 6:75`.

Cluster 2 holds 3,332 of 4,915. Note that the corpus has 3,330 `gutendex`
documents, so KMeans has essentially separated Gutendex from everything else.
That is a real property of the data, not a bug, and it is why cluster labels are
carried but not yet used for colour — sources are more informative at this
stage. No cluster naming was invented.

Outlier check: median distance from centroid 7.37, p90 14.12, max 17.16
(p90/max = 0.82); only 5 nodes lie beyond 115% of p99. No single outlier
distorts the framing.

## 30. Measured performance

`/map`: 926,348 bytes, **82 ms** cold (read + parse + validate), **~25 ms**
warm.

Frame cost, measured with a GPU sync point (1px `readPixels`), 1440x880:

| Nodes | ms/frame | Geometry build |
| --- | --- | --- |
| 4,915 (real) | 1.68 | 7.1 ms |
| 25,000 (synthetic) | 3.01 | 23.4 ms |
| 50,000 (synthetic) | 5.58 | 36.6 ms |

Scene object count at 50,000 nodes: **4**. Nothing scales with node count.

Render-on-demand preserved: 40 idle ticks produced **0** renders; one
`requestRender()` produced exactly 1.

## 31. Camera semantics

The two controls are now distinct rather than duplicates:

- **Reset Camera** — the default viewing angle *and* the fitted whole-map
  framing, adopted as "home" when the projection loads. Home is
  `[0, 0, 160.26]` for this corpus, replacing the pre-map `[0, 0, 90]`
  placeholder.
- **Fit All** — re-frames the whole map from the current viewing angle
  (verified: direction preserved, dot product 1.0000).

`Fit Results` remains T4.

## 32. Verification

Resize path verified at three widths — buffer matches CSS x DPR, camera aspect
matches, point scale follows buffer height:

| Width | Buffer | Aspect | Point scale |
| --- | --- | --- | --- |
| 1440x880 | 1440x880 | 1.6364 | 943.6 |
| 1000x760 | 1000x760 | 1.3158 | 814.9 |
| 375x760 | 375x760 | 0.4934 | 814.9 |

Rendering confirmed by reading the framebuffer directly: 10,652 lit pixels from
the home view, 12,808 after a ~70 degree orbit — the silhouette changes with the
viewing angle, which is the depth check. All 703 sampled nodes project inside
the viewport, spanning 44.6% of frame height and 27.7% of width. No GL errors.

Legend counts match the corpus exactly: Gutendex 3,330, Suno 992, Note 471,
Zip import 122 = 4,915. No source parsing problem.

### Environment caveat

`ResizeObserver` delivery and `requestAnimationFrame` are both gated on the
browser pane actually painting, and the pane repeatedly stopped painting during
this session (also seen in T2). While starved, the canvas stays at its initial
1x1 and screenshots time out. The resize *code path* was therefore verified by
invoking the exact callback `ResizeObserver` calls. This is a harness condition,
not an application defect — but canvas sizing on a real display is worth one
glance during human playtest.

## 33. Deliberately not implemented (T4)

Hover tooltip, node selection, raycasting/picking, result to node focus, node to
DetailPanel, result glow, dimming non-results, the query node, Fit Results, and
cluster animation. `NodeRenderer.object.raycast` is a no-op until T4 installs
real picking.

## 34. T3 changed files

Python — added:
`web/api/map_projection.py`, `web/api/generate_map_projection.py`,
`web/api/map_service.py`, `web/api/tests/test_map_projection.py`

Python — modified:
`web/api/main.py` (added `GET /map`), `web/api/schemas.py` (added `MapNode`,
`MapProjectionMetadata`, `MapResponse`)

Data — added: `data/thoughtmap_db/official/map_projection_3d.json`

Frontend — added:
`src/api/mapTypes.ts`, `src/app/MapController.ts`, `src/config/sourceStyles.ts`,
`src/scene/NodeRenderer.ts`, `src/scene/nodeIndex.ts`,
`src/scene/projectionBounds.ts`, `src/ui/MapStatusView.ts`,
`tests/mapState.test.ts`, `tests/nodeRenderer.test.ts`,
`tests/projectionGeometry.test.ts`

Frontend — modified:
`src/api/ThoughtMapApiClient.ts` (added `map()`, endpoint-aware error context),
`src/api/errors.ts` (context-aware messages), `src/app/AppState.ts` (map
lifecycle), `src/app/SearchScreen.ts`, `src/main.ts`,
`src/scene/CameraController.ts` (`setHome`, `fitBoxAsHome`),
`src/scene/ThoughtMapScene.ts`, `src/styles/main.css`, `index.html`

Untouched: `map_points_latest.csv`, Unity, Streamlit, `/search`, all existing
CSV/SQLite/PostgreSQL data and schemas.

---

# Phase T4 — Search ↔ Thought Space Interaction

Status: complete except the human visual gate, which is **awaiting confirmation**
(see §45). T0–T3 records above are unchanged.

## 35. Picking architecture

Screen-space nearest-point picking, not `THREE.Raycaster`.

`Raycaster` picks Points with a **world-space** threshold, which cannot mean the
same thing at every zoom level: tuned for a wide view it swallows half the cloud
close up; tuned for close up it is unclickable zoomed out. It also picks the
point nearest *along the ray*, not the point nearest the cursor, so a far node
can win a click that visually belonged to a near one.

`NodeRenderer.projectToScreen()` projects all nodes into a reused
`Float32Array` of `[x, y, depth]` triples, and `pickNearestNode()` (pure, in
`src/scene/picking.ts`) returns the nearest within a **pixel** radius. Tolerance
is stated in the same units as the pointer, is constant across zoom, and touch
simply gets a larger radius. Nodes with NDC depth outside `[-1, 1]` are skipped,
which is what stops off-screen geometry stealing a click; equal-distance ties go
to the nearer node.

Measured full pick (project + scan):

| Nodes | project | scan | total |
| --- | --- | --- | --- |
| 4,915 (real) | 0.403 ms | 0.066 ms | **0.469 ms** |
| 25,000 | 2.965 ms | 0.097 ms | 3.062 ms |
| 50,000 | 2.750 ms | 0.250 ms | 3.000 ms |

Comfortable for a click at every size, and hover is coalesced to one pick per
frame, so even 50k stays inside a frame budget. The projection pass dominates and
is the obvious T6 target if the corpus grows much further.

## 36. Click vs drag

`pointerdown` records the origin. Once travel exceeds `DRAG_THRESHOLD_PX` (5,
compared squared, diagonally) the gesture is a camera drag: hover is cleared and
the release selects nothing. Below the threshold the release picks.

OrbitControls is never globally disabled — it keeps handling the same gestures it
always did. Verified live: a 6-step drag selects nothing; a 2px jitter still
selects; a click on empty space clears the selection.

Touch tolerance is 24px against 12px for a mouse, so the map never demands
pixel-accurate tapping.

## 37. Visual-state model

One `aState` float per node, plus `aEmphasis` for rank. Deterministic
precedence, highest wins:

```text
Selected (5) > Hovered (4) > TopResult (3) > Result (2) > Normal (1) / Dimmed (0)
```

`computeNodeVisualState()` is pure and O(nodes + results). Non-results are
**dimmed, never hidden**, so spatial context survives a search. Rank scales
emphasis from 1.0 down to 0.55, which adjusts brightness and size only —
search changes appearance, never position.

Verified against the live GPU buffer for `Plato` / semantic with one result
selected:

```text
state 0 (dimmed)     4905
state 2 (result)        8
state 3 (top result)    1
state 5 (selected)      1
                     ----
                     4915
```

### No geometry rebuild per search

Positions and colours are written once when the projection loads. A search
copies into the two existing attribute arrays and flags them dirty. Measured
0.148 ms to apply emphasis and 0.124 ms to apply selection across 4,915 nodes.

## 38. Selection semantics — changed in T4

Selection now **survives a search that excludes it**.

Before the thought space existed, "selected" could only mean a row in the
current result list, so a search that dropped that row had to clear it. A
document can now be selected by clicking its node with no search involved, so
selection is a property of the map, not of the result set. A new search re-ranks
the list without discarding what the user is looking at.

Two T2 tests encoded the old rule and were updated to assert the new one, with
the reason recorded in the test body. No assertion was weakened; the expectation
was inverted deliberately.

There is exactly one selection state (`selectedDocId`). A result-row click and a
node click call the same `SelectionController.select()`.

### Hover is separate

`hoveredDocId` is transient state. Hover highlights the node and fills the
tooltip; it never changes the DetailPanel, the selected result, or the camera.
Verified live: hovering a different node leaves both selection and the resolved
DetailPanel document unchanged.

## 39. Search failure and zero results

A failed search clears the stale **result rows** (T2 behaviour, unchanged) but
keeps `emphasisDocIds`, `hasSearchEmphasis` and the selection. The thought space
therefore keeps the last successful emphasis until a new successful search
replaces it — a transient API error never destroys spatial context.

A successful zero-result search dims all 4,915 nodes uniformly, shows the normal
T2 "No results" message, is not an error, and disables Fit Results. Verified
live: histogram `{0: 4915}`, button disabled, no error box.

## 40. Missing map join

A `SearchResult` whose `doc_id` has no node in the loaded projection is normal,
not impossible — the artifact can predate a document. Such a result stays in the
list, stays selectable, renders in the DetailPanel, and is skipped by camera
focus and Fit Results without throwing.

Verified live by injecting `ghost:not_in_projection` alongside a real result:

```text
resultsReturned: 2   mapJoins: 1   missingJoins: 1
rows rendered: 2     ghost selectable: yes     focus/fit threw: no
```

`joinDiagnostics()` exposes these counts, and development builds log missing
joins once per state change.

### Two representations, one identity

`MapNode` and `SearchResult` stay separate types joining on `doc_id`.
`DocumentSelectionResolver` prefers the search result (it carries similarity,
parameters, URL) and falls back to the map node. A map-only document reports
similarity as `null` and the panel renders **"Not in current results"** — never a
fabricated `0.0000`, which would assert maximal dissimilarity.

## 41. Camera focus and Fit Results

`focusPoint(point, mapExtent)` is distinct from Reset, Fit All and Fit Results.
It preserves the current viewing **direction** and changes only target and
distance, so focusing never spins the space to an unfamiliar angle. Distance is
`mapExtent * 0.12` — derived from the map's own scale, not hard-coded for this
corpus. For the real projection that is 12.0 world units, confirmed live.

`Fit Results` frames only results present in `NodeIndex`:

- 0 matching nodes → returns false, control disabled
- 1 node → degenerates to focus rather than a zero-sized box
- multiple → fits their bounds

**A floor was added during verification.** Framing `Plato` / keyword literally
put the camera 1.0 units from its target, because all ten results sit almost on
top of each other — the camera ended up inside the cloud. A group is now never
approached more closely than a single node.

Verified live that the modes frame genuinely different regions:

| Mode | Target | Camera distance |
| --- | --- | --- |
| keyword | `[10.9, -20.3, 6.3]` | floored to focus distance |
| semantic | `[10.0, -20.6, 7.0]` | 3.4 → floored |

## 42. Hover tooltip

One reusable element for the whole map — 4,915 nodes get one tooltip, not 4,915
DOM nodes. Pointer-transparent (`pointer-events: none`), so it can never swallow
a click meant for the node under it. Shows title and author · source, plus
similarity **only** when the hovered node is in the current result set. Clamped
inside the canvas on every edge. Cleared when nothing is hovered.

### A real bug found during verification

Hover was permanently dead after the first pointer move. `queueHover()` guarded
on `hoverFrame !== 0` to coalesce picks to one per frame, but a requested
animation frame is **not guaranteed to be delivered** — the browser stops
servicing rAF while the page is not being painted. The handle stayed set forever
and every later hover returned early.

Fixed with a staleness deadline: past 250 ms an undelivered frame booking is
cancelled and re-scheduled. Verified by simulating dropped frames and then
resuming — hover recovers on the next pointer move.

## 43. Render-on-demand

Preserved. Measured after all T4 wiring:

- 60 idle ticks → **0** renders
- one `requestRender()` → exactly 1
- a hover change → exactly 1
- ten *identical* `syncFromState()` calls → 1 render, not 10 (the visual state
  is memoised on a cheap key)

No animation loop was introduced. Selection and hover are step changes, not
transitions.

## 44. Responsive and mobile

At 375px: single column, no horizontal overflow, touch pick radius 24px, tapping
the results panel reaches the panel rather than the canvas, tooltip stays
pointer-transparent, result list fully usable.

Keyboard access is unregressed: the T2 result list keeps its `listbox`/`option`
roles, tab order, and Enter/Space activation. Map interaction is supplemental.

**Known limitation:** the camera controls — Reset, Fit All and the new Fit
Results — are hidden below 1100px, a layout decision made in T3. Result-click
focus still works there, but Fit Results is unreachable on tablet and phone.
Left as-is rather than redesigning layout late in T4; carried to T5.

## 45. Human visual gate — AWAITING CONFIRMATION

The browser pane in this environment repeatedly stops painting, which starves
both `requestAnimationFrame` and `ResizeObserver` and makes screenshots time
out. Everything above was verified through DOM state, GPU attribute buffers,
direct framebuffer reads, and synthetic pointer events — not by looking at it.

Per §35 of the phase brief, a normal browser on a real display must still
confirm:

1. the point cloud visibly exists
2. real 3D depth is apparent while orbiting
3. search results visibly stand out from dimmed non-results
4. the selected node is obvious
5. the hover tooltip follows the intended node
6. camera focus is not disorienting
7. Fit All works
8. Fit Results works
9. UI stays readable over the map

To run it:

```bash
python -m api.generate_map_projection --verbose   # only if the artifact is absent
python -m uvicorn api.main:app --host 127.0.0.1 --port 8078   # from 10_ThoughtMap/web
```

```bash
THOUGHTMAP_API_URL=http://127.0.0.1:8078 npm run dev   # from 10_ThoughtMap/threejs
```

T4 is not COMPLETE until this passes.

## 46. T4 changed files

Frontend — added:
`src/scene/nodeVisualState.ts`, `src/scene/picking.ts`,
`src/app/DocumentSelectionResolver.ts`,
`src/app/ThoughtMapInteractionController.ts`, `src/ui/MapTooltip.ts`,
`tests/visualState.test.ts`, `tests/picking.test.ts`, `tests/interaction.test.ts`

Frontend — modified:
`src/app/AppState.ts` (hover, emphasis, selection semantics),
`src/app/SearchScreen.ts` (resolver, selection events),
`src/scene/NodeRenderer.ts` (visual attributes, shader states, projection,
world positions), `src/scene/CameraController.ts` (`focusPoint`, `fitPoints`),
`src/scene/ThoughtMapScene.ts` (renderer exposed),
`src/scene/cameraFraming.ts` (`computeFocusDistance`),
`src/ui/DetailPanel.ts` (view model, honest unavailable fields),
`src/ui/ResultPanel.ts` (hover class, scroll into view),
`src/main.ts`, `src/styles/main.css`, `index.html` (Fit Results control),
`tests/appState.test.ts`, `tests/searchController.test.ts`,
`tests/panels.test.ts`

Python: **unchanged**. No backend work was required for T4.

---

# Phase T6 — Production Deployment + Runtime Optimization

T6 makes the completed Search / Collect application deployable as a public
beta. It adds no product features; every change serves deployability,
stability, an explicitly labelled public beta, or operability.

Deployment architecture, environment variables, host selection, corpus-release
procedure and all measurements: **[`deployment.md`](deployment.md)**.
Runtime-optimization detail and the ONNX evaluation: `full-corpus-reconciliation.md`
sections 30–35.

## 47. Responsibility split — unchanged

Python is still the search engine. The frontend still computes no embeddings,
no similarity, no UMAP, no clustering. T6 changed how the corpus is *loaded*
and how responses are *cached*, never how anything is ranked or scored.

## 48. What T6 added to the backend

| module | purpose |
| --- | --- |
| `api/readiness.py` | `/ready` state: what must be true before traffic arrives |
| `api/observability.py` | structured events and per-request stage timings |
| `api/map_response_cache.py` | `/map` encoded and gzipped once per corpus version |
| `api/rate_limit.py` | per-client token bucket for `/search` |
| `api/process_memory.py` | resident/peak memory without a required dependency |
| `api/startup_profile.py` | stage-by-stage startup measurement |
| `api/verify_corpus.py` | deployment integrity gate, incl. load-path equivalence |
| `api/prepare_corpus_artifacts.py` | checksum-verified artifact acquisition |
| `api/benchmark_runtime.py` | latency, concurrency and memory benchmarks |
| `api/smoke.py` | external end-to-end check of a running deployment |

New endpoints: `GET /ready`, `GET /config`. `/health` is unchanged and remains
liveness-only.

## 49. Deployment mode is one switch

`THOUGHTMAP_DEPLOYMENT_MODE` is `development`, `public-demo` or `production`,
and every feature-availability question is answered from it rather than from
environment checks scattered through the code. `ApiSettings.features()` is the
single source of truth, served to the frontend at `GET /config` so the UI
reflects the server it is actually talking to rather than what its build
assumed.

Outside development the configuration fails closed: an unset
`THOUGHTMAP_ALLOWED_ORIGINS` allows *no* cross-origin request and says so in
`/ready`, rather than expanding into `*`.

## 50. Load order — the map no longer blocks the UI

`main.ts` builds the search UI first and imports Three.js, the scene and the
interaction controller dynamically. Only their *types* are imported statically,
which the compiler erases.

```text
 29 ms  entry chunk (14.8 kB gzip) done
 37 ms  DOM ready — search usable
 47 ms  three.js (118.1 kB gzip) loaded
 95 ms  /map request starts
149 ms  /map (3.6 MB gzip) complete
```

The entry chunk fell from 141.8 kB gzip to 14.8 kB. Total bytes are
essentially unchanged; what changed is what has to arrive before the first
interaction.

## 51. Public-demo boundary

The Personal Library authenticates nobody, so it is off by default outside
development, and off means the routes answer 404 — not merely a hidden button.
The UI removes the Save control and the Library tab and states the situation
plainly. The code path is intact for a future authenticated deployment.

## 52. Deliberately not implemented (T6)

- Real authentication, OAuth, accounts.
- Adopting ONNX Runtime. Measured as equivalent and faster; deferred with
  reasons and numbers (reconciliation §33).
- Caching the stacked embedding matrix across requests — the largest remaining
  ranking cost, deferred as a redesign (reconciliation §31).
- Memory-mapping the embedding matrix. Measured as unhelpful at this ratio.
- In-browser embedding. The browser still never receives a model or raw vectors.
- Merging the unmerged 14,072-row Gutenberg batch. That is a corpus release.
- Battle Prep and battle phases, card/deck generation, cluster redesign.
- Actually deploying. T6 prepares and verifies a deployment-like environment;
  nothing was published.

## 53. T6 changed files

Backend — added: `api/readiness.py`, `api/observability.py`,
`api/map_response_cache.py`, `api/rate_limit.py`, `api/process_memory.py`,
`api/startup_profile.py`, `api/verify_corpus.py`,
`api/prepare_corpus_artifacts.py`, `api/benchmark_runtime.py`, `api/smoke.py`,
`api/tests/test_deployment.py`, `api/tests/test_deployment_api.py`,
`api/tests/test_vector_cache.py`, `api/tests/test_rate_limit.py`

Backend — modified: `api/config.py` (deployment modes, CORS policy, warmup,
feature flags, resolved artifact path), `api/main.py` (lifespan warmup,
`/ready`, `/config`, cache headers, library gate, rate limit, error handler),
`api/repositories.py` (checksum-keyed vector cache, artifact-read skip, stage
timings), `api/corpus_manifest.py` (`corpus_version`), `api/search_service.py`
(stage timings, ranking dispatch extracted), `api/query_profile.py` (profile
stage), `search_utils.py` (redundant mask copy removed)

Frontend — added: `src/config/runtime.ts`, `src/app/DeploymentController.ts`,
`src/ui/BackendStatusBanner.ts`, `tests/deployment.test.ts`

Frontend — modified: `src/main.ts` (lazy scene, deployment controller),
`src/app/AppState.ts` (features, backend status), `src/app/SearchScreen.ts`
(feature gating, banner), `src/ui/DetailPanel.ts` (save gate),
`src/api/ThoughtMapApiClient.ts` (`/ready`, `/config`, base URL),
`src/api/types.ts`, `src/styles/main.css`, `vite.config.ts`

Docs: `docs/deployment.md` (new), `docs/full-corpus-reconciliation.md`
(§§30–35), this file, `.env.example` (new), `.gitignore`

---

# Phase T7 — Release Candidate

Release: **`thoughtmap-corpus-20260909-v1`**. T7 hardens the T6 deployment into
a release candidate. No product features were added.

Runtime detail and measurements: `full-corpus-reconciliation.md` §§36–42.
Operator procedure: [`deployment.md`](deployment.md).
Public-facing summary: [`release-notes-public-demo.md`](release-notes-public-demo.md).

## 54. Responsibility split — still unchanged

Python is the search engine. The frontend computes no embeddings, no
similarity, no UMAP, no clustering. T7 replaced the *runtime* that produces a
query embedding and changed *when* the corpus matrix is built. It changed no
ranking, which is asserted rather than assumed: `verify_matrix_equivalence` and
`verify_encoder_equivalence` both compare against the previous implementation
on the real corpus.

## 55. What T7 added

| module | purpose |
| --- | --- |
| `api/search_corpus.py` | the corpus and its embedding matrix, built once |
| `api/query_encoder.py` | the encoder boundary: ONNX or sentence-transformers |
| `api/prepare_query_encoder.py` | export the ONNX encoder with a pinned revision |
| `api/corpus_release.py` | freeze the corpus as a named, checksummed release |
| `api/release_check.py` | the one command that gates a release |
| `api/verify_matrix_equivalence.py` | prove the matrix changed no ranking |
| `api/verify_encoder_equivalence.py` | 56-query encoder equivalence suite |
| `api/verify_failure_modes.py` | start broken, check it fails honestly |
| `api/run_ci_locally.py` | execute the CI workflow from the workflow file |
| `deploy/` | Caddy, nginx and Render configurations + a local proxy |
| `.github/workflows/thoughtmap-ci.yml` | CI for pull requests and main |

## 56. Encoder boundary

Ranking asks a `TextEncoder` for a vector and never learns which runtime
produced it. The provider is a deployment decision made in `query_encoder.py`
and nowhere else, chosen by configuration and never by availability — a
configured-but-broken encoder fails readiness rather than silently becoming a
different one.

## 57. Deliberately not implemented (T7)

- Authentication, OAuth, accounts. The Personal Library therefore stays off in
  public modes, enforced at the route, not only in the UI.
- Merging the unmerged 14,072-row Gutenberg batch. That is a corpus release.
- Keyword-search optimisation. It is now the binding capacity constraint
  (~9 rps) and the obvious next target, but T7 is hardening, not redesign.
- Quantised (int8) ONNX. It would shrink the 466 MB encoder but changes
  numerics, so it needs its own equivalence pass.
- Battle Prep, battle phases, card/deck generation, cluster redesign.
- Actually deploying. T7 prepares and proves a release candidate; nothing was
  published, no infrastructure was purchased, no URL exposed.

## 58. T7 changed files

Backend — added: `api/search_corpus.py`, `api/query_encoder.py`,
`api/prepare_query_encoder.py`, `api/corpus_release.py`, `api/release_check.py`,
`api/verify_matrix_equivalence.py`, `api/verify_encoder_equivalence.py`,
`api/verify_failure_modes.py`, `api/run_ci_locally.py`,
`api/tests/test_search_corpus.py`, `api/tests/test_query_encoder.py`,
`requirements-ci.txt`, `requirements-dev.txt`

Backend — modified: `search_utils.py` (prepared vectors, `_matrix_row`),
`api/repositories.py` (build the corpus once, single frame),
`api/search_service.py` (corpus threaded through ranking, encoder provider),
`api/config.py` (encoder settings, same-origin origins rule),
`api/readiness.py` (encoder check, CORS posture), `api/main.py` (encoder
warmup, access-log redaction), `api/observability.py` (redaction filter),
`api/startup_profile.py`, `api/prepare_corpus_artifacts.py` (encoder fetch),
`api/tests/test_deployment.py`, `requirements-api.txt`

Frontend — modified: `src/scene/CameraController.ts` (reduced motion),
`src/scene/ThoughtMapScene.ts` (canvas accessible name),
`src/ui/ResultPanel.ts` (result count announced), `src/main.ts` (message
wording), `src/styles/main.css` (reduced-motion block)

Repository: `.github/workflows/thoughtmap-ci.yml`, `deploy/*`, `.env.example`,
`docs/deployment.md`, `docs/release-notes-public-demo.md`,
`docs/full-corpus-reconciliation.md`, this file,
`data/thoughtmap_db/official/corpus_manifest.json` (release identity),
`data/thoughtmap_db/official/README-LEGACY-embeddings_master.md`

Removed: `data/thoughtmap_db/official/embeddings_master.csv` (41 MB legacy
snapshot, unusable behind the guard; recoverable from history at `ca5b41d`).
