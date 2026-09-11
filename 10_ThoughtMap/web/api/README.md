# ThoughtMap FastAPI adapter

This API is a thin frontend adapter over the existing ThoughtMap Python search
logic. Unity is the frontend. Python remains the search engine.

## Current architecture

```text
Unity UI
  -> HTTP /search
FastAPI api/main.py
  -> ThoughtMapSearchService
Repository boundary
  -> CSV today
  -> SQLite later
Embedding/vector helpers
  -> search_utils.py
```

## Files

- `main.py`: HTTP routes and CORS only.
- `schemas.py`: API response models.
- `config.py`: environment-driven settings.
- `repositories.py`: CSV repository now, SQLite boundary later.
- `search_service.py`: query embedding and search orchestration.
- `personal_repository.py`: Personal library repository boundary.
- `postgres_personal_repository.py`: PostgreSQL implementation for Personal saved works.
- `user_library_service.py`: coordinates official lookup and Personal persistence.

## Run locally

From `10_ThoughtMap/web`:

```powershell
pip install -r requirements-api.txt
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Smoke test:

```powershell
curl "http://127.0.0.1:8000/search?q=philosophy"
```

## Environment variables

```powershell
$env:THOUGHTMAP_BACKEND="csv"
$env:THOUGHTMAP_DB_DIR="data/thoughtmap_db/official"
$env:THOUGHTMAP_EMBEDDINGS_PATH="D:\ThoughtMap\master\thoughtmap_canonical_embeddings.csv"
$env:THOUGHTMAP_ALLOWED_ORIGINS="*"
$env:THOUGHTMAP_MODEL_NAME="paraphrase-multilingual-MiniLM-L12-v2"
$env:THOUGHTMAP_PERSONAL_BACKEND="local"
$env:DATABASE_URL=""
```

## The embedding artifact

The corpus is 63,891 documents. Their embeddings are ~542 MB as CSV, far past
GitHub's 100 MB limit, so **the embedding master is not in version control**.

In version control (light, canonical):

- `documents_master.csv` — 63,891 rows of metadata, no vectors
- `parameter_scores.csv` — 63,891 rows of 10-axis Thought Composition
- `corpus_manifest.json` — counts, model, dimension, and the artifact's SHA-256

Outside version control (heavy):

- the embedding master itself, located by `THOUGHTMAP_EMBEDDINGS_PATH`

`corpus_manifest.json` identifies the artifact by **content hash**, not by path,
so it can be served from a local disk, a build artifact, or object storage
without changing search behaviour. The local path in the manifest is a
development hint only.

If `THOUGHTMAP_EMBEDDINGS_PATH` is unset the API falls back to
`embeddings_master.csv` beside the documents, which is the historical 4,584-row
file. That is a smaller corpus, not an error, and the repository logs a warning
when documents and embeddings disagree by more than 10% so the situation is
never silent. Nothing scans drives looking for the artifact: a configured path
that does not exist fails immediately, naming the path.

Parsed vectors are cached beside the artifact as `<name>.vectors.npz`, keyed on
its size and mtime. That turns a ~90 s cold parse into a fast load, and a
regenerated artifact invalidates the cache automatically.

### Rebuilding the corpus

```powershell
python -m api.recover_full_corpus --dry-run   # always first
python -m api.recover_full_corpus --apply
python -m api.backfill_parameter_scores --verbose
python -m api.generate_map_projection --verbose
```

See `docs/full-corpus-reconciliation.md` for why the repository corpus was 4,915
until phase T4.6, and `docs/corpus-inventory.md` for the dataset inventory.

## Append Personal DB To Official Master

Use this before SQLite migration when promoting a personal ThoughtMap database
into the official searchable database. This does not regenerate embeddings.
It reuses the existing personal CSV files directly:

```text
documents.csv
embeddings.csv
```

The source documents CSV should contain at least:

```text
doc_id,title,source
```

The source embeddings CSV should contain at least:

```text
doc_id,embedding
```

If embeddings use `model` instead of `model_name`, the append script normalizes
it to `model_name` for official master compatibility.

Append a personal library, preserving each row source value and skipping duplicates:

```powershell
python -m api.append_to_official_master --documents data/thoughtmap_db/users/9caa93032b8ffb30/documents.csv --embeddings data/thoughtmap_db/users/9caa93032b8ffb30/embeddings.csv --official-dir data/thoughtmap_db/official --on-duplicate skip
```

Override all source values while appending:

```powershell
python -m api.append_to_official_master --documents data/thoughtmap_db/users/9caa93032b8ffb30/documents.csv --embeddings data/thoughtmap_db/users/9caa93032b8ffb30/embeddings.csv --source lyrics --official-dir data/thoughtmap_db/official --on-duplicate update
```

The script prefixes `doc_id` with the effective source, for example
`user_suno:doc_000000` or `lyrics:doc_000000`. It writes only
`documents_master.csv` and `embeddings_master.csv`. Before saving, it creates
timestamped backups such as `documents_master.csv.bak_YYYYMMDD_HHMMSS`.

## SQLite MVP

The SQLite backend keeps the `/search` response and Unity unchanged. Embeddings
are stored as TEXT JSON for now.

Create SQLite from the current official CSV files:

```powershell
python -m api.migrate_csv_to_sqlite --csv-dir data/thoughtmap_db/official --sqlite-path data/thoughtmap_db/official/thoughtmap.sqlite
```

Run the API with SQLite:

```powershell
$env:THOUGHTMAP_BACKEND="sqlite"
$env:THOUGHTMAP_DB_DIR="data/thoughtmap_db/official"
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

When `THOUGHTMAP_DB_DIR` points to a directory, the SQLite repository uses
`thoughtmap.sqlite` inside that directory. You can also pass a direct `.sqlite`
file path.

## Personal Saved Library MVP

The API can save selected search results into a Personal library. Production
deployments should use PostgreSQL:

```powershell
$env:THOUGHTMAP_PERSONAL_BACKEND="postgres"
$env:DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME"
```

Render may provide `DATABASE_URL` as `postgresql://...`. The API and Alembic
normalize that to `postgresql+psycopg://...` internally so SQLAlchemy uses the
installed psycopg 3 driver. Do not add `psycopg2-binary` for this API.

The historical local file backend remains available for local development only:

```text
data/thoughtmap_db/users/default/
  documents.csv
  embeddings.csv
  favorites.json
```

The email-based API is a temporary user lookup mechanism, not authentication.
The API normalizes email with trim/lowercase, hashes it with SHA-256, and stores
the hash as the user key. Do not treat possession of an email string as proof of
identity.

Save a selected document by email:

```powershell
curl -X POST "http://127.0.0.1:8000/users/by-email/save" -H "Content-Type: application/json" -d "{\"email\":\"user@example.com\",\"doc_id\":\"gutendex:12345\",\"parameters\":{\"philosophy\":42}}"
```

List saved documents by email. This shape is kept for Unity:

```powershell
curl "http://127.0.0.1:8000/users/by-email/saved?email=user@example.com"
```

Response:

```json
{
  "works": []
}
```

Delete a saved document by email:

```powershell
curl -X DELETE "http://127.0.0.1:8000/users/by-email/saved/gutendex%3A12345?email=user@example.com"
```

Compatibility routes still exist and map to a fixed default user in the same
Personal repository:

```powershell
curl -X POST "http://127.0.0.1:8000/users/default/save" -H "Content-Type: application/json" -d "{"doc_id":"gutendex:12345"}"
```

List saved documents:

```powershell
curl "http://127.0.0.1:8000/users/default/saved"
```

Delete a saved document:

```powershell
curl -X DELETE "http://127.0.0.1:8000/users/default/saved/gutendex%3A12345"
```

## Personal PostgreSQL migration

Install API dependencies:

```powershell
pip install -r requirements-api.txt
```

Run Alembic migration from `10_ThoughtMap/web`:

```powershell
$env:DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME"
python -m alembic -c alembic.ini upgrade head
```

On Render, the build command can use the platform-provided `DATABASE_URL`:

```bash
pip install -r requirements-api.txt && python -m alembic -c alembic.ini upgrade head
```

Render configuration:

```text
THOUGHTMAP_PERSONAL_BACKEND=postgres
DATABASE_URL=<Render PostgreSQL internal database URL>
```

Legacy file import is manual and never runs at API startup. Preview first:

```powershell
python -m api.migrate_personal_files_to_postgres --dry-run
```

Then import:

```powershell
python -m api.migrate_personal_files_to_postgres --database-url $env:DATABASE_URL
```

The script reads:

- `data/thoughtmap_db/users/default/favorites.json`
- `data/thoughtmap_db/users/default/documents.csv`
- `data/thoughtmap_db/users/default/embeddings.csv`
- `web/user_data/*/thoughtmap_embeddings.csv`

## Unity Personal Library check

1. Deploy the API with `THOUGHTMAP_PERSONAL_BACKEND=postgres` and migrated tables.
2. In Unity Battle Prep, set the API base URL to the deployed FastAPI URL.
3. Enter the same email used by save/list.
4. Run Load Personal.
5. Confirm the returned works appear in the Card List and keep `doc_id`.

## Result URLs

`/search` includes optional `url` when metadata has `url`, `source_url`, or `link`. For Gutendex/Gutenberg rows, the API can infer `https://www.gutenberg.org/ebooks/{id}` from `gutenberg_id` or numeric `doc_id`.

## 3D Thought Map projection

`GET /map` serves a cached 3D UMAP projection of the official corpus. It is
read-only and never runs UMAP: it reads an artifact generated offline.

Generate or regenerate the artifact from `10_ThoughtMap/web`:

```powershell
python -m api.generate_map_projection --verbose
```

This writes `data/thoughtmap_db/official/map_projection_3d.json` (~0.88 MB for
4,915 documents, ~92 s). Generation is deterministic: the same corpus and the
same config produce the same coordinates.

Projection config reuses the repository's historical values — UMAP
`n_neighbors=10, min_dist=0.2, metric=cosine, random_state=42`, plus KMeans
`n_clusters=8` on the embeddings. Only `n_components=3` is new.

If the artifact is missing or unreadable, `/map` answers `503` with the
generation command in the message. `/search` is unaffected.

`MapService` caches the parsed artifact keyed on the file's path, mtime and
size, so regenerating it takes effect on the next request without a restart.

The legacy `map_points_latest.csv` is unrelated and unused: it covers 331 of
4,915 documents with blank coordinates.

---

## Deployment (T6)

Full procedure, environment variables, host requirements and measurements:
**[`../../docs/deployment.md`](../../docs/deployment.md)**.

### Endpoints added in T6

```text
GET /ready    Is the canonical corpus usable? 200 when yes, 503 with a body
              explaining which check is missing when not. Reads cached state;
              re-validates nothing, so it is safe to poll.
GET /config   What this deployment offers: mode, library_enabled,
              corpus_version. The frontend configures itself from this.
```

`GET /health` is unchanged and stays liveness-only. A process is legitimately
healthy and not ready for the whole of startup.

### Operational commands

Run from `10_ThoughtMap/web`; each exits non-zero on failure.

```bash
python -m api.prepare_corpus_artifacts --source PATH|URL --build-cache
python -m api.verify_corpus --compare-load-paths
python -m api.startup_profile --json profile.json
python -m api.benchmark_runtime --mode http --concurrency 1,2,5,10
python -m api.smoke --base-url URL --frontend-url URL
```

### Two things to know before changing the load path

- The vector cache is keyed on the artifact's SHA-256 from the manifest. When
  it matches, `load_index` **does not read the 542 MB CSV at all**. That is the
  difference between a 4 s and a 50 s start, and between 337 MB and 1,374 MB
  resident. `verify_corpus --compare-load-paths` proves the two paths agree.
- Run **one worker**. Each is a separate process holding its own copy of the
  corpus and model (~1 GB), and throughput is flat from 2 concurrent requests
  upward.
