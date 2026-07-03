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

## User Saved Library MVP

The API can save selected search results into the local default user library:

```text
data/thoughtmap_db/users/default/
  documents.csv
  embeddings.csv
  favorites.json
```

Save a selected document:

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

The MVP uses `default` only. It intentionally does not add authentication yet.
