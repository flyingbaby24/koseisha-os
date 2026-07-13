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
$env:THOUGHTMAP_ALLOWED_ORIGINS="*"
$env:THOUGHTMAP_MODEL_NAME="paraphrase-multilingual-MiniLM-L12-v2"
$env:THOUGHTMAP_PERSONAL_BACKEND="local"
$env:DATABASE_URL=""
```

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
