from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OFFICIAL_DIR = PROJECT_ROOT / "data" / "thoughtmap_db" / "official"

DOCUMENT_REQUIRED_COLUMNS = ["doc_id", "title", "source"]
EMBEDDING_REQUIRED_COLUMNS = ["doc_id", "embedding"]
DOCUMENT_MIN_COLUMNS = [
    "doc_id",
    "author",
    "title",
    "source",
    "source_url",
    "category",
    "subcategory",
    "status",
]
EMBEDDING_MIN_COLUMNS = ["doc_id", "embedding", "model_name"]


def _resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _read_csv_or_empty(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    return pd.read_csv(path, dtype=str).fillna("")


def _normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _slugify(value: object, fallback: str) -> str:
    text = _normalize_text(value).lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^0-9a-zA-Z_\-:.]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-_.:")
    return text or fallback


def _ensure_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = ""
    ordered = list(out.columns)
    for column in columns:
        if column not in ordered:
            ordered.append(column)
    return out[ordered]


def _align_for_concat(left: pd.DataFrame, right: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = list(left.columns)
    for column in right.columns:
        if column not in columns:
            columns.append(column)
    return _ensure_columns(left, columns), _ensure_columns(right, columns)


def _backup(path: Path, timestamp: str) -> Path | None:
    if not path.exists():
        return None
    backup_path = path.with_name(f"{path.name}.bak_{timestamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def _missing_columns(frame: pd.DataFrame, required: list[str]) -> list[str]:
    return [column for column in required if column not in frame.columns]


def _prefixed_doc_id(raw_doc_id: object, source: object, row_number: int) -> str:
    base = _slugify(raw_doc_id, fallback=f"row-{row_number}")
    source_slug = _slugify(source, fallback="unknown")
    prefix = f"{source_slug}:"
    if base.startswith(prefix):
        return base
    return f"{prefix}{base}"


def _prepare_source_frames(
    documents: pd.DataFrame,
    embeddings: pd.DataFrame,
    source_override: str = "",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    missing_docs = _missing_columns(documents, DOCUMENT_REQUIRED_COLUMNS)
    missing_embeddings = _missing_columns(embeddings, EMBEDDING_REQUIRED_COLUMNS)
    if missing_docs:
        raise ValueError(f"documents CSV is missing required column(s): {', '.join(missing_docs)}")
    if missing_embeddings:
        raise ValueError(f"embeddings CSV is missing required column(s): {', '.join(missing_embeddings)}")

    docs = _ensure_columns(documents, DOCUMENT_MIN_COLUMNS)
    embs = embeddings.copy()

    if "model_name" not in embs.columns and "model" in embs.columns:
        embs["model_name"] = embs["model"]
    embs = _ensure_columns(embs, EMBEDDING_MIN_COLUMNS)

    docs = docs.copy()
    embs = embs.copy()
    docs["_original_doc_id"] = docs["doc_id"].map(_normalize_text)
    embs["_original_doc_id"] = embs["doc_id"].map(_normalize_text)

    if source_override:
        docs["source"] = source_override
    docs["source"] = docs["source"].map(lambda value: _slugify(value, fallback="unknown"))

    id_map: dict[str, str] = {}
    for index, row in docs.iterrows():
        original_doc_id = _normalize_text(row.get("_original_doc_id", ""))
        if not original_doc_id:
            continue
        id_map[original_doc_id] = _prefixed_doc_id(original_doc_id, row.get("source", ""), int(index) + 1)

    docs["doc_id"] = docs["_original_doc_id"].map(id_map).fillna("")
    embs["doc_id"] = embs["_original_doc_id"].map(id_map).fillna("")

    docs = docs[docs["doc_id"].map(_normalize_text) != ""].reset_index(drop=True)
    embs = embs[embs["doc_id"].map(_normalize_text) != ""].reset_index(drop=True)

    docs = docs.drop(columns=["_original_doc_id"], errors="ignore")
    embs = embs.drop(columns=["_original_doc_id"], errors="ignore")

    return docs, embs


def append_to_official_master(
    documents_csv: str | Path,
    embeddings_csv: str | Path,
    official_dir: str | Path | None = None,
    source: str = "",
    on_duplicate: str = "skip",
) -> dict[str, int | str]:
    official_path = _resolve_project_path(official_dir) if official_dir is not None else DEFAULT_OFFICIAL_DIR
    documents_input_path = _resolve_project_path(documents_csv)
    embeddings_input_path = _resolve_project_path(embeddings_csv)
    documents_path = official_path / "documents_master.csv"
    embeddings_path = official_path / "embeddings_master.csv"

    if on_duplicate not in {"skip", "update"}:
        raise ValueError("on_duplicate must be 'skip' or 'update'.")

    official_path.mkdir(parents=True, exist_ok=True)
    source_documents = pd.read_csv(documents_input_path, dtype=str).fillna("")
    source_embeddings = pd.read_csv(embeddings_input_path, dtype=str).fillna("")
    new_documents, new_embeddings = _prepare_source_frames(
        source_documents,
        source_embeddings,
        source_override=_normalize_text(source),
    )

    if new_documents.empty or new_embeddings.empty:
        raise ValueError("No matching document/embedding rows found to append.")

    documents = _ensure_columns(_read_csv_or_empty(documents_path, DOCUMENT_MIN_COLUMNS), DOCUMENT_MIN_COLUMNS)
    embeddings = _ensure_columns(_read_csv_or_empty(embeddings_path, EMBEDDING_MIN_COLUMNS), EMBEDDING_MIN_COLUMNS)

    keep = "last" if on_duplicate == "update" else "first"
    new_documents = new_documents.drop_duplicates("doc_id", keep=keep).reset_index(drop=True)
    new_embeddings = new_embeddings.drop_duplicates("doc_id", keep=keep).reset_index(drop=True)

    existing_ids = set(documents["doc_id"].astype(str)) | set(embeddings["doc_id"].astype(str))
    new_ids = set(new_documents["doc_id"].astype(str)) & set(new_embeddings["doc_id"].astype(str))
    duplicate_ids = existing_ids & new_ids

    skipped = 0
    updated = 0
    if duplicate_ids and on_duplicate == "skip":
        new_documents = new_documents[~new_documents["doc_id"].astype(str).isin(duplicate_ids)].reset_index(drop=True)
        new_embeddings = new_embeddings[~new_embeddings["doc_id"].astype(str).isin(duplicate_ids)].reset_index(drop=True)
        skipped = len(duplicate_ids)
    elif duplicate_ids and on_duplicate == "update":
        documents = documents[~documents["doc_id"].astype(str).isin(duplicate_ids)].reset_index(drop=True)
        embeddings = embeddings[~embeddings["doc_id"].astype(str).isin(duplicate_ids)].reset_index(drop=True)
        updated = len(duplicate_ids)

    final_new_ids = set(new_documents["doc_id"].astype(str)) & set(new_embeddings["doc_id"].astype(str))
    new_documents = new_documents[new_documents["doc_id"].astype(str).isin(final_new_ids)].reset_index(drop=True)
    new_embeddings = new_embeddings[new_embeddings["doc_id"].astype(str).isin(final_new_ids)].reset_index(drop=True)

    documents, new_documents = _align_for_concat(documents, new_documents)
    embeddings, new_embeddings = _align_for_concat(embeddings, new_embeddings)

    output_documents = pd.concat([documents, new_documents], ignore_index=True)
    output_embeddings = pd.concat([embeddings, new_embeddings], ignore_index=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    documents_backup = _backup(documents_path, timestamp)
    embeddings_backup = _backup(embeddings_path, timestamp)

    output_documents.to_csv(documents_path, index=False, encoding="utf-8-sig")
    output_embeddings.to_csv(embeddings_path, index=False, encoding="utf-8-sig")

    return {
        "official_dir": str(official_path),
        "documents_input_rows": int(len(source_documents)),
        "embeddings_input_rows": int(len(source_embeddings)),
        "matched_new_ids": int(len(new_ids)),
        "added": int(len(new_documents)),
        "skipped": int(skipped),
        "updated": int(updated),
        "documents_total": int(len(output_documents)),
        "embeddings_total": int(len(output_embeddings)),
        "documents_backup": str(documents_backup or ""),
        "embeddings_backup": str(embeddings_backup or ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append a personal ThoughtMap documents/embeddings CSV pair to official master CSV files."
    )
    parser.add_argument("--documents", required=True, help="Source documents.csv path.")
    parser.add_argument("--embeddings", required=True, help="Source embeddings.csv path.")
    parser.add_argument(
        "--official-dir",
        default=str(DEFAULT_OFFICIAL_DIR),
        help="Directory containing official documents_master.csv and embeddings_master.csv.",
    )
    parser.add_argument(
        "--source",
        default="",
        help="Optional source override. If omitted, each documents.csv source value is preserved.",
    )
    parser.add_argument(
        "--on-duplicate",
        choices=["skip", "update"],
        default="skip",
        help="How to handle rows whose source-prefixed doc_id already exists.",
    )
    args = parser.parse_args()

    result = append_to_official_master(
        documents_csv=args.documents,
        embeddings_csv=args.embeddings,
        official_dir=args.official_dir,
        source=args.source,
        on_duplicate=args.on_duplicate,
    )

    print("Updated ThoughtMap official master CSV")
    print(f"official_dir: {result['official_dir']}")
    print(f"documents_input_rows: {result['documents_input_rows']}")
    print(f"embeddings_input_rows: {result['embeddings_input_rows']}")
    print(f"matched_new_ids: {result['matched_new_ids']}")
    print(f"added: {result['added']}")
    print(f"skipped: {result['skipped']}")
    print(f"updated: {result['updated']}")
    print(f"documents_total: {result['documents_total']}")
    print(f"embeddings_total: {result['embeddings_total']}")
    if result["documents_backup"]:
        print(f"documents_backup: {result['documents_backup']}")
    if result["embeddings_backup"]:
        print(f"embeddings_backup: {result['embeddings_backup']}")


if __name__ == "__main__":
    main()
