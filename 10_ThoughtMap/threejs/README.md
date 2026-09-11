# ThoughtMap Three.js frontend

Three.js + TypeScript frontend for the **Search / Collect** screen.

This is an additional client, not a replacement. The Unity client under
`10_ThoughtMap/unity` and the Streamlit app under `10_ThoughtMap/web` keep
working unchanged.

Python stays the search engine. This frontend does no embedding, no similarity
computation, no UMAP, and no clustering. See
[`../docs/threejs-migration-plan.md`](../docs/threejs-migration-plan.md) for the
full responsibility split, the audited API contract, and the phase plan.

## Status

Phase **T6** — deployment-ready.

Search the 63,891-document corpus, explore it in 3D, compare the query and a
selected document on one Thought Composition radar, and save documents to a
Personal Library that is reflected in the results list and in the map. T6 made
that deployable: separate health and readiness, a corpus-version gate, cached
`/map` responses, a chunked bundle, and an explicitly labelled public-demo mode.

**Deploying this? Read [`../docs/deployment.md`](../docs/deployment.md).** It
has the environment variables, the artifact procedure, the host requirements
and the measurements behind every choice.

### Running it locally

The embedding artifact is not in version control. Point the API at it:

```bash
export THOUGHTMAP_EMBEDDINGS_PATH="D:/ThoughtMap/master/thoughtmap_canonical_embeddings.csv"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8078
```

Without that, startup stays alive but `/ready` fails, naming the artifact
rather than silently serving the 4,584-document legacy snapshot.

### Build output

The entry chunk is 14.8 kB gzipped. Three.js (118.1 kB gzipped) is a separate
vendor chunk loaded *after* the search UI is interactive, and the 3.7 MB map
starts downloading later still — so search is usable long before the thought
space appears. Nothing here waits for the map.

`VITE_THOUGHTMAP_API_BASE_URL` points a build at its API; unset, it uses
same-origin `/api`. Deployment never requires editing a source file.

### Earlier phases

T5 added the Thought Composition radar and the Personal Library.

T4 connected search to the thought space. All documents render as one
`THREE.Points` cloud from a cached 3D UMAP projection. Search results illuminate in the map and non-results dim; clicking a
result focuses its node; clicking a node selects the same document; hover reveals
a tooltip; Fit Results frames the current result set.

`doc_id` is the only cross-layer identity, and there is exactly one selection
state — a result-row click and a node click take the same path.

The Personal Library and the radar arrived in T5. In a public deployment the library is switched off and its routes answer 404; the Save control and Library tab are removed rather than disabled.

### Camera controls

- **Reset Camera** — default angle *and* whole-map framing
- **Fit All** — re-frame the whole map from the current angle
- **Fit Results** — frame the current search results (disabled when none are in
  the map)

Below 1100px these are replaced by compact circular controls (T5); result-click
focus works at every width.

## The map

The projection is generated offline and cached; the browser never runs UMAP and
never receives raw embeddings. To (re)generate it, from `10_ThoughtMap/web`:

```bash
python -m api.generate_map_projection --verbose
```

That writes `data/thoughtmap_db/official/map_projection_3d.json`, which
`GET /map` serves. Without it the API answers `503` and the UI says the thought
space is unavailable — text search keeps working. See
`docs/threejs-migration-plan.md` for the projection config, the dataset
fingerprint rule, and cache invalidation.

## Requirements

- Node.js 20+ (developed on v24.18.0)
- The FastAPI adapter running locally for phases T2 and later

## Install

```powershell
cd 10_ThoughtMap\threejs
npm install
```

## Run

```powershell
npm run dev
```

Opens on <http://localhost:5273>.

`/api/*` is proxied to `http://127.0.0.1:8000` so the browser talks to a single
origin and the API's CORS configuration does not have to change. Point it
elsewhere with `THOUGHTMAP_API_URL`:

```powershell
$env:THOUGHTMAP_API_URL = "http://127.0.0.1:8080"
npm run dev
```

Start the backend separately (from `10_ThoughtMap/web`):

```powershell
$env:THOUGHTMAP_BACKEND = "csv"
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

## Verify

```powershell
npm run typecheck   # tsc --noEmit, must report 0 errors
npm run test        # vitest
npm run build       # typecheck + production bundle
```

## Layout

```text
src/
  main.ts          composition root — wiring only, no logic
  api/             HTTP client, error translation, types mirroring web/api/schemas.py
  app/             AppState + Search/Selection controllers + screen composition
  config/          search option values and the canonical parameter axis order
  scene/           Three.js: renderer, camera, background, document cloud
  ui/              DOM panels (search, results, detail, radar, library) + formatting
  styles/
tests/
```

## Search options

`src/config/searchOptions.ts` is the only place option values are defined.

Sources are the four namespaces that actually exist in the corpus
(`gutendex`, `user_suno`, `user_note`, `zip`) plus an all-sources choice that
omits the parameter.

Filters are `general` plus the ten Thought Composition axes, matching the
backend's own `filter_options()`. `general` is intentionally a no-narrowing
choice: it names the whole axis set rather than one axis. Unity additionally
offers `basic_thought`, `basic_literature`, and `jinn_os`; those are filter
*definition file* names, not axis names, and each matches 0 documents,
so they are not offered here.

Rules:

- `main.ts` stays a composition root. Logic belongs in `app/`, `scene/`, or `ui/`.
- The parameter radar is 2D (canvas/SVG) and lives in `ui/`. It is not part of
  the Three.js scene.
- Selection has exactly one path: `SelectionController`. The result list and the
  3D scene both read and write that, never their own copies.
- The scene renders on demand. Nothing runs while the user is idle, and nothing
  writes to the DOM per frame.

## Dev handle

In `npm run dev` only, the scene is exposed as `window.__thoughtmap` so camera
state and scene contents can be inspected from the console. `import.meta.env.DEV`
is statically false in a production build, so the bundler drops it.
