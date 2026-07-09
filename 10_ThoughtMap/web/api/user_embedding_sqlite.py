from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_user_id_from_email(email: str) -> str:
    normalized = str(email or "").strip().lower()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def default_sqlite_path() -> Path:
    return (
        PROJECT_ROOT
        / "data"
        / "thoughtmap_db"
        / "official"
        / "thoughtmap.sqlite"
    )


def resolve_sqlite_path(db_dir: str | Path | None = None) -> Path:
    raw_value = str(db_dir or os.getenv("THOUGHTMAP_DB_DIR", "")).strip()

    if not raw_value:
        return default_sqlite_path()

    path = Path(raw_value)

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if path.suffix:
        return path

    return path / "thoughtmap.sqlite"


def connect_db(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else resolve_sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def ensure_indexes(con: sqlite3.Connection) -> None:
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_documents_doc_id ON documents(doc_id)")
    con.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_embeddings_doc_id ON embeddings(doc_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_user_id ON embeddings(user_id)")
    con.commit()


def user_doc_id(user_id: str, raw_doc_id: str) -> str:
    raw = str(raw_doc_id or "").strip() or "doc_000000"
    if raw.startswith(f"user:{user_id}:"):
        return raw
    return f"user:{user_id}:{raw}"


def save_user_embeddings(email: str, rows: list[dict]) -> dict:
    user_id = make_user_id_from_email(email)
    if not user_id:
        raise ValueError("email is required")
    if not rows:
        raise ValueError("rows are required")

    now = datetime.now(timezone.utc).isoformat()
    con = connect_db()
    ensure_indexes(con)

    try:
        for i, row in enumerate(rows):
            raw_doc_id = row.get("doc_id") or f"doc_{i:06d}"
            doc_id = user_doc_id(user_id, raw_doc_id)

            title = str(row.get("title", "") or raw_doc_id)
            source = str(row.get("source", "") or "personal")
            category = str(row.get("category", "") or row.get("cluster_label", "") or "")
            text = str(row.get("text", "") or "")
            embedding = str(row.get("embedding", "") or "")

            if not embedding:
                continue

            con.execute(
                """
                INSERT INTO documents (
                    doc_id, author, title, source, source_url,
                    category, subcategory, content_type, status,
                    notes, user_id, text_path, tags, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    author=excluded.author,
                    title=excluded.title,
                    source=excluded.source,
                    source_url=excluded.source_url,
                    category=excluded.category,
                    subcategory=excluded.subcategory,
                    content_type=excluded.content_type,
                    status=excluded.status,
                    notes=excluded.notes,
                    user_id=excluded.user_id,
                    text_path=excluded.text_path,
                    tags=excluded.tags,
                    updated_at=excluded.updated_at
                """,
                (
                    doc_id,
                    str(row.get("author", "") or ""),
                    title,
                    source,
                    str(row.get("source_url", "") or row.get("url", "") or ""),
                    category,
                    str(row.get("subcategory", "") or ""),
                    "personal_embedding",
                    "active",
                    text,
                    user_id,
                    "",
                    str(row.get("tags", "") or ""),
                    now,
                    now,
                ),
            )

            con.execute(
                """
                INSERT INTO embeddings (
                    doc_id, model_name, embedding, user_id, model, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    model_name=excluded.model_name,
                    embedding=excluded.embedding,
                    user_id=excluded.user_id,
                    model=excluded.model,
                    created_at=excluded.created_at
                """,
                (
                    doc_id,
                    str(row.get("model_name", "") or row.get("model", "") or ""),
                    embedding,
                    user_id,
                    str(row.get("model", "") or row.get("model_name", "") or ""),
                    now,
                ),
            )

            con.execute(
                """
                INSERT OR REPLACE INTO map_points (
                    doc_id, cluster, cluster_label, x, y
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    str(row.get("cluster", "") or ""),
                    str(row.get("cluster_label", "") or ""),
                    str(row.get("x", "") or ""),
                    str(row.get("y", "") or ""),
                ),
            )

        con.commit()

    finally:
        con.close()

    return {
        "user_id": user_id,
        "count": len(rows),
    }


def list_user_embeddings(email: str) -> dict:
    user_id = make_user_id_from_email(email)
    con = connect_db()
    ensure_indexes(con)

    try:
        rows = con.execute(
            """
            SELECT
                d.doc_id,
                d.title,
                d.author,
                d.source,
                d.category,
                d.subcategory,
                d.created_at,
                d.updated_at
            FROM documents d
            INNER JOIN embeddings e ON d.doc_id = e.doc_id
            WHERE d.user_id = ?
            ORDER BY d.updated_at DESC, d.created_at DESC, d.title ASC
            """,
            (user_id,),
        ).fetchall()

        works = [dict(r) for r in rows]

    finally:
        con.close()

    return {
        "user_id": user_id,
        "works": works,
    }


def load_user_embedding_frame(email: str) -> pd.DataFrame:
    user_id = make_user_id_from_email(email)
    con = connect_db()
    ensure_indexes(con)

    try:
        df = pd.read_sql_query(
            """
            SELECT
                d.doc_id,
                d.title,
                d.author,
                d.source,
                d.source_url,
                d.category,
                d.subcategory,
                d.user_id,
                d.notes AS text,
                e.embedding,
                e.model_name
            FROM documents d
            INNER JOIN embeddings e ON d.doc_id = e.doc_id
            WHERE d.user_id = ?
            """,
            con,
            params=(user_id,),
        ).fillna("")

    finally:
        con.close()

    return df
