from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from storage import load_official_db

from .repositories import DEFAULT_SQLITE_PATH, PROJECT_ROOT, _resolve_project_path, _resolve_sqlite_path


DEFAULT_CSV_DIR = (
    PROJECT_ROOT
    / "data"
    / "thoughtmap_db"
    / "official"
)


def _ensure_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    frame = frame.copy()
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame


def migrate_csv_to_sqlite(
    csv_dir: str | Path | None = None,
    sqlite_path: str | Path | None = None,
) -> dict[str, int | str]:
    """Create a SQLite search database from the current official CSV files."""

    csv_path = _resolve_project_path(csv_dir) if csv_dir is not None else DEFAULT_CSV_DIR
    db_path = _resolve_sqlite_path(sqlite_path) if sqlite_path is not None else DEFAULT_SQLITE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    documents, embeddings, map_points = load_official_db(csv_path)
    documents = _ensure_columns(documents, ["doc_id", "title", "author", "source"])
    embeddings = _ensure_columns(embeddings, ["doc_id", "embedding", "model_name"])

    with sqlite3.connect(db_path) as conn:
        documents.to_sql("documents", conn, if_exists="replace", index=False)
        embeddings.to_sql("embeddings", conn, if_exists="replace", index=False)
        if map_points is not None:
            map_points.to_sql("map_points", conn, if_exists="replace", index=False)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_doc_id ON documents(doc_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_doc_id ON embeddings(doc_id)")
        conn.commit()

    return {
        "sqlite_path": str(db_path),
        "documents": int(len(documents)),
        "embeddings": int(len(embeddings)),
        "map_points": int(len(map_points)) if map_points is not None else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a ThoughtMap SQLite search database from official CSV files."
    )
    parser.add_argument(
        "--csv-dir",
        default=str(DEFAULT_CSV_DIR),
        help="Directory containing documents_master.csv and embeddings_master.csv.",
    )
    parser.add_argument(
        "--sqlite-path",
        default=str(DEFAULT_SQLITE_PATH),
        help="Output SQLite file path.",
    )
    args = parser.parse_args()

    result = migrate_csv_to_sqlite(args.csv_dir, args.sqlite_path)
    print("Created ThoughtMap SQLite database")
    print(f"sqlite_path: {result['sqlite_path']}")
    print(f"documents: {result['documents']}")
    print(f"embeddings: {result['embeddings']}")
    print(f"map_points: {result['map_points']}")


if __name__ == "__main__":
    main()
