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

Later SQLite migration should add a real `SqliteSearchIndexRepository` while
keeping `/search` and Unity unchanged.
