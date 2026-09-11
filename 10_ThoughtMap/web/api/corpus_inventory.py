"""Inventory every candidate ThoughtMap corpus, in-repo and external.

Read-only. Nothing here writes to a dataset; it only measures them, so it is
safe to run against the live external pipeline directory.

    python -m api.corpus_inventory --json docs/corpus-inventory.json \
                                   --markdown docs/corpus-inventory.md

Written for phase T4.5, to reconcile the 4,915-document repository corpus
against the much larger corpus maintained outside git.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

# The external pipeline directory. Referenced by src/compare_gutendex_with_*.py
# and by D:/ThoughtMap/run_import.bat. Absent on machines other than the
# author's, which is not an error — it is recorded as "not present".
EXTERNAL_ROOT = Path("D:/ThoughtMap")

# Columns that identify a document, in order of preference.
IDENTITY_COLUMNS = ("doc_id", "gutenberg_id", "text_hash", "canonical_work_id")


@dataclass
class DatasetInfo:
    path: str
    present: bool
    format: str = ""
    size_bytes: int = 0
    row_count: int = 0
    columns: list[str] = field(default_factory=list)
    unique_doc_id_count: int | None = None
    duplicate_doc_id_count: int | None = None
    unique_gutenberg_id_count: int | None = None
    duplicate_gutenberg_id_count: int | None = None
    unique_text_hash_count: int | None = None
    has_embedding: bool = False
    embedding_dimension: int | None = None
    embedding_model: str | None = None
    has_parameters: bool = False
    has_title: bool = False
    has_author: bool = False
    has_source: bool = False
    source_distribution: dict[str, int] = field(default_factory=dict)
    likely_role: str = ""
    canonical_or_derived: str = ""
    notes: str = ""


def _embedding_probe(frame: pd.DataFrame) -> tuple[bool, int | None, str | None]:
    """Dimension and model of the first parseable embedding, if any."""
    if "embedding" not in frame.columns:
        return False, None, None

    dimension = None
    for value in frame["embedding"].head(50):
        text = str(value or "").strip()
        if not text.startswith("["):
            continue
        try:
            dimension = len(json.loads(text))
            break
        except json.JSONDecodeError:
            continue

    model = None
    for column in ("model_name", "model"):
        if column in frame.columns:
            values = frame[column].dropna().astype(str)
            values = values[values.str.strip() != ""]
            if not values.empty:
                model = values.iloc[0]
                break

    return True, dimension, model


def inspect_csv(path: Path, role: str, kind: str, sample_rows: int | None = None) -> DatasetInfo:
    info = DatasetInfo(path=str(path), present=path.exists(), format="csv")
    info.likely_role = role
    info.canonical_or_derived = kind

    if not info.present:
        info.notes = "referenced but not present on this machine"
        return info

    info.size_bytes = path.stat().st_size

    # Embeddings files are hundreds of MB; the identity columns are cheap to
    # read on their own, and a small sample is enough to probe the vectors.
    try:
        header = pd.read_csv(path, dtype=str, encoding="utf-8-sig", nrows=0)
    except Exception as exc:  # unreadable is a finding, not a crash
        info.notes = f"unreadable: {type(exc).__name__}: {exc}"
        return info

    info.columns = list(header.columns)
    identity = [c for c in IDENTITY_COLUMNS if c in header.columns]
    meta = [c for c in ("title", "author", "source", "model_name", "model") if c in header.columns]

    usecols = identity + meta
    frame = (
        pd.read_csv(path, dtype=str, encoding="utf-8-sig", usecols=usecols).fillna("")
        if usecols
        else pd.read_csv(path, dtype=str, encoding="utf-8-sig", nrows=sample_rows or 5000).fillna("")
    )
    info.row_count = len(frame)

    if "doc_id" in frame.columns:
        info.unique_doc_id_count = int(frame["doc_id"].nunique())
        info.duplicate_doc_id_count = int(frame["doc_id"].duplicated().sum())
    if "gutenberg_id" in frame.columns:
        present = frame["gutenberg_id"][frame["gutenberg_id"] != ""]
        info.unique_gutenberg_id_count = int(present.nunique())
        info.duplicate_gutenberg_id_count = int(present.duplicated().sum())
    if "text_hash" in frame.columns:
        present = frame["text_hash"][frame["text_hash"] != ""]
        info.unique_text_hash_count = int(present.nunique())

    info.has_title = "title" in header.columns
    info.has_author = "author" in header.columns
    info.has_source = "source" in header.columns
    info.has_parameters = any(
        c in header.columns for c in ("philosophy", "parameters", "parameter_scores")
    )

    if "source" in frame.columns:
        info.source_distribution = {
            str(k): int(v) for k, v in frame["source"].value_counts().items()
        }

    if "embedding" in header.columns:
        probe = pd.read_csv(
            path, dtype=str, encoding="utf-8-sig", usecols=["embedding"], nrows=50
        ).fillna("")
        for column in ("model_name", "model"):
            if column in header.columns:
                probe[column] = pd.read_csv(
                    path, dtype=str, encoding="utf-8-sig", usecols=[column], nrows=50
                ).fillna("")[column]
                break
        info.has_embedding, info.embedding_dimension, info.embedding_model = _embedding_probe(probe)

    return info


def build_inventory() -> dict[str, Any]:
    datasets: list[DatasetInfo] = []

    official = PROJECT_ROOT / "data" / "thoughtmap_db" / "official"
    users = PROJECT_ROOT / "data" / "thoughtmap_db" / "users" / "9caa93032b8ffb30"

    datasets.append(inspect_csv(official / "documents_master.csv", "repo official documents", "canonical"))
    datasets.append(inspect_csv(official / "embeddings_master.csv", "repo official embeddings", "canonical"))
    datasets.append(inspect_csv(official / "parameter_scores.csv", "repo official parameters", "derived"))
    datasets.append(inspect_csv(official / "map_points_latest.csv", "legacy 2D map stub", "derived"))
    datasets.append(inspect_csv(users / "documents.csv", "repo personal documents", "canonical"))
    datasets.append(inspect_csv(users / "embeddings.csv", "repo personal embeddings", "canonical"))

    datasets.append(
        inspect_csv(EXTERNAL_ROOT / "master" / "documents_master.csv", "external live documents master", "canonical")
    )
    datasets.append(
        inspect_csv(EXTERNAL_ROOT / "master" / "embeddings_master.csv", "external live embeddings master", "canonical")
    )
    datasets.append(
        inspect_csv(EXTERNAL_ROOT / "master" / "import_report.csv", "external import audit log", "derived")
    )
    datasets.append(
        inspect_csv(
            EXTERNAL_ROOT / "thoughtmap_embeddings_from_gutendex.csv",
            "external accumulated gutendex embeddings (snapshot)",
            "canonical",
        )
    )
    datasets.append(
        inspect_csv(
            EXTERNAL_ROOT / "ThoughtMap_DB" / "exports" / "thoughtmap_embeddings_from_gutendex.csv",
            "external accumulated gutendex embeddings (newer batch)",
            "canonical",
        )
    )
    datasets.append(
        inspect_csv(
            EXTERNAL_ROOT / "ThoughtMap_DB" / "imports" / "gutendex_books_master.csv",
            "gutenberg catalog (metadata only)",
            "catalog",
        )
    )
    datasets.append(
        inspect_csv(
            EXTERNAL_ROOT / "ThoughtMap_DB" / "imports" / "missing_candidates.csv",
            "pending download/embed queue",
            "derived",
        )
    )

    # Game content, explicitly not ThoughtMap documents.
    datasets.append(
        inspect_csv(
            PROJECT_ROOT / "unity" / "Assets" / "StreamingAssets" / "cards.csv",
            "Source of Thought card records",
            "derived (game layer)",
        )
    )

    return {
        "generated_for": "phase T4.5 corpus reconciliation",
        "project_root": str(PROJECT_ROOT),
        "external_root": str(EXTERNAL_ROOT),
        "external_root_present": EXTERNAL_ROOT.exists(),
        "datasets": [asdict(d) for d in datasets],
    }


def to_markdown(inventory: dict[str, Any]) -> str:
    lines = [
        "# ThoughtMap corpus inventory",
        "",
        "Generated by `python -m api.corpus_inventory`. Read-only measurement;",
        "no dataset is modified. See `full-corpus-reconciliation.md` for what it means.",
        "",
        f"- project root: `{inventory['project_root']}`",
        f"- external root: `{inventory['external_root']}` "
        f"({'present' if inventory['external_root_present'] else 'NOT present'})",
        "",
        "| dataset | present | rows | unique doc_id | dup doc_id | unique gutenberg_id | embedding | dim | model | role | kind |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- | --- | --- |",
    ]

    for d in inventory["datasets"]:
        name = Path(d["path"]).name
        parent = Path(d["path"]).parent.name
        lines.append(
            "| `{parent}/{name}` | {present} | {rows} | {udi} | {ddi} | {ugi} | {emb} | {dim} | {model} | {role} | {kind} |".format(
                parent=parent,
                name=name,
                present="yes" if d["present"] else "**no**",
                rows=d["row_count"] or "",
                udi=d["unique_doc_id_count"] if d["unique_doc_id_count"] is not None else "",
                ddi=d["duplicate_doc_id_count"] if d["duplicate_doc_id_count"] is not None else "",
                ugi=d["unique_gutenberg_id_count"] if d["unique_gutenberg_id_count"] is not None else "",
                emb="yes" if d["has_embedding"] else "no",
                dim=d["embedding_dimension"] or "",
                model=d["embedding_model"] or "",
                role=d["likely_role"],
                kind=d["canonical_or_derived"],
            )
        )

    lines.append("")
    lines.append("## Source distribution")
    lines.append("")
    for d in inventory["datasets"]:
        if d["source_distribution"]:
            lines.append(f"- `{Path(d['path']).parent.name}/{Path(d['path']).name}`: {d['source_distribution']}")

    notes = [d for d in inventory["datasets"] if d["notes"]]
    if notes:
        lines.extend(["", "## Notes", ""])
        for d in notes:
            lines.append(f"- `{d['path']}`: {d['notes']}")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inventory ThoughtMap corpora (read-only).")
    parser.add_argument("--json", default="", help="Write JSON inventory here.")
    parser.add_argument("--markdown", default="", help="Write Markdown inventory here.")
    args = parser.parse_args(argv)

    inventory = build_inventory()

    if args.json:
        path = Path(args.json)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {path}")

    if args.markdown:
        path = Path(args.markdown)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(to_markdown(inventory), encoding="utf-8")
        print(f"wrote {path}")

    if not args.json and not args.markdown:
        print(json.dumps(inventory, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
