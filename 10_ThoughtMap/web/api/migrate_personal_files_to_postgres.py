from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
from sqlalchemy import create_engine, insert, select

from .personal_repository import DEFAULT_COMPAT_EMAIL, email_hash_for, normalize_parameters
from .postgres_personal_repository import saved_embeddings, saved_works, users
from .repositories import PROJECT_ROOT


@dataclass
class ImportRecord:
    email_hash: str
    doc_id: str
    title: str = ""
    author: str = ""
    source: str = ""
    category: str = ""
    url: str = ""
    source_url: str = ""
    embedding: str = ""
    model_name: str = ""
    saved_at: str = ""
    parameters: object | None = None


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy personal files into PostgreSQL.")
    parser.add_argument("--root", default=str(PROJECT_ROOT), help="10_ThoughtMap project root.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--default-email", default=DEFAULT_COMPAT_EMAIL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    records = list(_collect_records(root, email_hash_for(args.default_email)))
    print(f"Collected {len(records)} personal records from legacy files.")
    for source, count in _summarize(records).items():
        print(f"  {source}: {count}")

    if args.dry_run:
        print("Dry run only. No PostgreSQL writes performed.")
        return

    database_url = str(args.database_url or "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required unless --dry-run is used.")

    engine = create_engine(database_url, pool_pre_ping=True)
    imported = 0
    skipped = 0
    with engine.begin() as conn:
        for record in records:
            user_id = _get_or_create_user_id(conn, record.email_hash)
            existing = conn.execute(
                select(saved_works.c.id).where(
                    saved_works.c.user_id == user_id,
                    saved_works.c.doc_id == record.doc_id,
                )
            ).scalar_one_or_none()
            if existing:
                skipped += 1
                continue

            conn.execute(
                insert(saved_works).values(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    doc_id=record.doc_id,
                    original_doc_id=record.doc_id,
                    title=record.title,
                    author=record.author,
                    source=record.source,
                    category=record.category,
                    url=record.url or None,
                    source_url=record.source_url or record.url or None,
                    parameters_json=normalize_parameters(record.parameters),
                    saved_at=record.saved_at,
                )
            )
            embedding_json = _parse_embedding(record.embedding)
            if embedding_json is not None:
                conn.execute(
                    insert(saved_embeddings).values(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        doc_id=record.doc_id,
                        embedding_json=embedding_json,
                        model_name=record.model_name,
                        saved_at=record.saved_at,
                    )
                )
            imported += 1

    print(f"Imported {imported} records. Skipped {skipped} duplicates.")


def _collect_records(root: Path, default_email_hash: str) -> Iterable[ImportRecord]:
    yield from _collect_default_user_files(root, default_email_hash)
    yield from _collect_streamlit_user_data(root)


def _collect_default_user_files(root: Path, default_email_hash: str) -> Iterable[ImportRecord]:
    user_dir = root / "data" / "thoughtmap_db" / "users" / "default"
    favorites = _read_json_list(user_dir / "favorites.json")
    documents = _read_csv_by_doc_id(user_dir / "documents.csv")
    embeddings = _read_csv_by_doc_id(user_dir / "embeddings.csv")

    doc_ids = set(documents) | set(embeddings) | {str(item.get("doc_id", "")) for item in favorites}
    for doc_id in sorted(item for item in doc_ids if item):
        favorite = next((item for item in favorites if str(item.get("doc_id", "")) == doc_id), {})
        document = documents.get(doc_id, {})
        embedding = embeddings.get(doc_id, {})
        yield ImportRecord(
            email_hash=default_email_hash,
            doc_id=doc_id,
            title=_pick(favorite, document, "title"),
            author=_pick(favorite, document, "author"),
            source=_pick(favorite, document, "source"),
            category=_pick(favorite, document, "category"),
            url=_pick(favorite, document, "url") or _pick(favorite, document, "source_url"),
            source_url=_pick(favorite, document, "source_url") or _pick(favorite, document, "url"),
            embedding=str(embedding.get("embedding", "") or ""),
            model_name=str(embedding.get("model_name", embedding.get("model", "")) or ""),
            saved_at=str(_pick(favorite, document, "saved_at") or embedding.get("saved_at", "")),
            parameters=favorite.get("parameters"),
        )


def _collect_streamlit_user_data(root: Path) -> Iterable[ImportRecord]:
    user_data = root / "web" / "user_data"
    if not user_data.exists():
        return

    for user_dir in user_data.iterdir():
        if not user_dir.is_dir():
            continue
        email_hash = user_dir.name
        csv_path = user_dir / "thoughtmap_embeddings.csv"
        if not csv_path.exists():
            continue
        frame = pd.read_csv(csv_path, dtype=str).fillna("")
        for _, row in frame.iterrows():
            doc_id = str(row.get("doc_id", "") or row.get("id", "") or "").strip()
            if not doc_id:
                continue
            yield ImportRecord(
                email_hash=email_hash,
                doc_id=doc_id,
                title=str(row.get("title", "") or ""),
                author=str(row.get("author", "") or ""),
                source=str(row.get("source", "streamlit_user_data") or "streamlit_user_data"),
                category=str(row.get("category", "") or ""),
                url=str(row.get("url", "") or row.get("source_url", "") or ""),
                source_url=str(row.get("source_url", "") or row.get("url", "") or ""),
                embedding=str(row.get("embedding", "") or ""),
                model_name=str(row.get("model_name", row.get("model", "")) or ""),
                saved_at=str(row.get("saved_at", "") or ""),
                parameters=_parameters_from_row(row),
            )


def _get_or_create_user_id(conn, email_hash: str) -> str:
    existing = conn.execute(select(users.c.id).where(users.c.email_hash == email_hash)).scalar_one_or_none()
    if existing:
        return existing
    user_id = str(uuid.uuid4())
    conn.execute(insert(users).values(id=user_id, email_hash=email_hash))
    return user_id


def _read_json_list(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return raw if isinstance(raw, list) else []


def _read_csv_by_doc_id(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    frame = pd.read_csv(path, dtype=str).fillna("")
    if "doc_id" not in frame.columns:
        return {}
    return {str(row["doc_id"]): dict(row) for _, row in frame.iterrows()}


def _pick(primary: dict[str, object], secondary: dict[str, object], key: str) -> str:
    return str(primary.get(key, "") or secondary.get(key, "") or "")


def _parse_embedding(value: str) -> list[float] | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    return [float(item) for item in parsed]


def _parameters_from_row(row: pd.Series) -> dict[str, float] | None:
    keys = [
        "philosophy",
        "psychology",
        "science",
        "economy",
        "economics",
        "karma",
        "emotion",
        "moral",
        "morality",
        "ideal",
        "individual",
        "community",
    ]
    result = {}
    for key in keys:
        value = row.get(key, "")
        if value == "":
            continue
        try:
            result[key] = float(value)
        except ValueError:
            continue
    return result or None


def _summarize(records: list[ImportRecord]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for record in records:
        source = record.source or "(unknown)"
        summary[source] = summary.get(source, 0) + 1
    return summary


if __name__ == "__main__":
    main()
