"""Merge the external full corpus into the official master, without data loss.

    python -m api.recover_full_corpus --dry-run          # always run this first
    python -m api.recover_full_corpus --apply

Phase T4.5. The repository master is a 2026-07-02 snapshot holding 4,915 rows;
the live pipeline outside git has grown to 62,306 gutendex works. This merges
them into one corpus while preserving every existing identifier.

Identity rules
--------------
- **gutendex** documents are keyed on `gutenberg_id`, the source-native stable
  identity. Titles are not used: different works share titles, and the same
  work appears under several Gutenberg editions.
- **Personal** documents (`user_suno`, `user_note`, `zip`) exist only in the
  repository and are carried across unchanged.
- Canonical `doc_id` is `"<source>:<bare id>"`. The repository already uses this
  for 4,584 of its rows, so existing Personal Library references and result URLs
  keep working. The external master's bare `doc_000000` ids are prefixed on the
  way in; that mapping was verified 3,330/3,330 during the T4.5 audit.
- The 331 rows the repository holds under a *bare* gutendex id are exact
  duplicates of prefixed rows (same `gutenberg_id`, same content) and are
  dropped.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OFFICIAL_DIR = PROJECT_ROOT / "data" / "thoughtmap_db" / "official"
EXTERNAL_MASTER = Path("D:/ThoughtMap/master")

CANONICAL_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EXPECTED_DIMENSION = 384

PERSONAL_SOURCES = ("user_suno", "user_note", "zip")


def normalise_model(name: str) -> str:
    """`sentence-transformers/x` and `x` name the same model."""
    text = str(name or "").strip()
    return text.split("/")[-1]


def prefixed_doc_id(source: str, doc_id: str) -> str:
    """Canonical `source:bare` id, idempotent for already-prefixed ids."""
    doc_id = str(doc_id or "").strip()
    source = str(source or "").strip()
    if not doc_id:
        return ""
    if ":" in doc_id:
        return doc_id
    return f"{source}:{doc_id}" if source else doc_id


@dataclass
class MergePlan:
    current_documents: int = 0
    current_unique_documents: int = 0
    candidate_documents: int = 0
    new_unique_documents: int = 0
    duplicates_within_current: int = 0
    duplicates_skipped: int = 0
    updates: int = 0
    carried_personal: int = 0
    embedding_compatible_rows: int = 0
    missing_embeddings: int = 0
    incompatible_embeddings: int = 0
    missing_parameters: int = 0
    projected_final_documents: int = 0
    projected_final_embeddings: int = 0
    duplicate_analysis: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


def load_repo_documents() -> pd.DataFrame:
    return pd.read_csv(
        OFFICIAL_DIR / "documents_master.csv", dtype=str, encoding="utf-8-sig"
    ).fillna("")


def load_external_documents() -> pd.DataFrame:
    return pd.read_csv(
        EXTERNAL_MASTER / "documents_master.csv", dtype=str, encoding="utf-8-sig"
    ).fillna("")


def classify_current_duplicates(repo: pd.DataFrame) -> dict[str, int]:
    """Duplicate statistics for the *existing* master, before any merge.

    Reported by every identity rule separately, because they disagree: title
    collisions are common and legitimate, while a repeated `gutenberg_id` is a
    genuine duplicate import.
    """
    gutendex = repo[repo["source"] == "gutendex"]
    stats = {
        "exact_doc_id": int(repo["doc_id"].duplicated().sum()),
        "source_plus_gutenberg_id": int(
            gutendex[gutendex["gutenberg_id"] != ""]["gutenberg_id"].duplicated().sum()
        ),
        "source_title_author": int(
            repo.duplicated(subset=["source", "title", "author"]).sum()
        ),
        "text_hash": int(repo[repo["text_hash"] != ""]["text_hash"].duplicated().sum()),
    }
    return stats


def build_plan() -> tuple[MergePlan, pd.DataFrame]:
    plan = MergePlan()

    repo = load_repo_documents()
    plan.current_documents = len(repo)
    plan.duplicate_analysis = classify_current_duplicates(repo)

    # --- resolve the existing master's own duplicates -----------------------
    repo = repo.copy()
    repo["_canonical_id"] = [
        prefixed_doc_id(s, d) for s, d in zip(repo["source"], repo["doc_id"])
    ]

    # Among rows that now collapse onto one canonical id, keep the row that was
    # already stored prefixed: that is the id everything else references.
    repo["_was_prefixed"] = repo["doc_id"].str.contains(":")
    repo = repo.sort_values("_was_prefixed", ascending=False)
    before = len(repo)
    repo = repo.drop_duplicates("_canonical_id", keep="first")
    plan.duplicates_within_current = before - len(repo)
    plan.current_unique_documents = len(repo)

    personal = repo[repo["source"].isin(PERSONAL_SOURCES)]
    plan.carried_personal = len(personal)

    repo_gutendex = repo[repo["source"] == "gutendex"]
    known_gutenberg_ids = set(repo_gutendex["gutenberg_id"]) - {""}

    # --- candidates ---------------------------------------------------------
    if not (EXTERNAL_MASTER / "documents_master.csv").exists():
        plan.warnings.append(
            f"external master not present at {EXTERNAL_MASTER}; nothing to merge"
        )
        return plan, repo

    external = load_external_documents()
    plan.candidate_documents = len(external)

    external = external.copy()
    external["_canonical_id"] = [
        prefixed_doc_id(s, d) for s, d in zip(external["source"], external["doc_id"])
    ]

    blank_gid = int((external["gutenberg_id"] == "").sum())
    if blank_gid:
        plan.warnings.append(f"{blank_gid} external rows have no gutenberg_id")

    incoming_new = external[~external["gutenberg_id"].isin(known_gutenberg_ids)]
    incoming_known = external[external["gutenberg_id"].isin(known_gutenberg_ids)]

    plan.new_unique_documents = len(incoming_new)
    plan.duplicates_skipped = len(incoming_known)
    plan.updates = 0  # existing rows are never rewritten by this merge

    merged = pd.concat([repo, incoming_new], ignore_index=True, sort=False).fillna("")
    merged["doc_id"] = merged["_canonical_id"]
    merged = merged.drop(columns=["_canonical_id", "_was_prefixed"], errors="ignore")
    merged = merged.drop_duplicates("doc_id", keep="first").reset_index(drop=True)

    plan.projected_final_documents = len(merged)
    return plan, merged


def audit_embeddings(plan: MergePlan, merged: pd.DataFrame) -> None:
    """Confirm every merged document has a usable, compatible vector."""
    repo_emb = pd.read_csv(
        OFFICIAL_DIR / "embeddings_master.csv",
        dtype=str,
        encoding="utf-8-sig",
        usecols=["doc_id", "model_name"],
    ).fillna("")
    repo_docs = load_repo_documents()
    source_by_id = dict(zip(repo_docs["doc_id"], repo_docs["source"]))
    repo_ids = {
        prefixed_doc_id(source_by_id.get(d, ""), d) for d in repo_emb["doc_id"]
    }

    external_ids: set[str] = set()
    models: set[str] = set()
    if (EXTERNAL_MASTER / "embeddings_master.csv").exists():
        ext_emb = pd.read_csv(
            EXTERNAL_MASTER / "embeddings_master.csv",
            dtype=str,
            encoding="utf-8-sig",
            usecols=["doc_id", "model_name"],
        ).fillna("")
        external_ids = {prefixed_doc_id("gutendex", d) for d in ext_emb["doc_id"]}
        models |= set(ext_emb["model_name"].map(normalise_model).unique())

    models |= set(repo_emb["model_name"].map(normalise_model).unique())
    models.discard("")

    foreign = sorted(m for m in models if m != CANONICAL_MODEL)
    if foreign:
        plan.incompatible_embeddings = 1
        plan.warnings.append(
            f"embedding model mismatch, refusing to mix cosine spaces: {foreign}"
        )

    available = repo_ids | external_ids
    have = merged["doc_id"].isin(available)
    plan.embedding_compatible_rows = int(have.sum())
    plan.missing_embeddings = int((~have).sum())
    plan.projected_final_embeddings = plan.embedding_compatible_rows

    # Parameters exist only for the current 4,915 rows.
    params = pd.read_csv(
        OFFICIAL_DIR / "parameter_scores.csv", dtype=str, encoding="utf-8-sig", usecols=["doc_id"]
    ).fillna("")
    param_ids = {prefixed_doc_id(source_by_id.get(d, ""), d) for d in params["doc_id"]}
    plan.missing_parameters = int((~merged["doc_id"].isin(param_ids)).sum())


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_official(stamp: str) -> list[str]:
    """Timestamped copies of everything the merge could overwrite."""
    made: list[str] = []
    for name in (
        "documents_master.csv",
        "embeddings_master.csv",
        "parameter_scores.csv",
        "map_projection_3d.json",
    ):
        source = OFFICIAL_DIR / name
        if not source.exists():
            continue
        target = source.with_name(f"{name}.t45bak_{stamp}")
        shutil.copy2(source, target)
        made.append(f"{target.name}  sha256={file_digest(target)[:16]}")
    return made


def print_report(plan: MergePlan, applied: bool) -> None:
    # The Windows console defaults to cp932 here; keep the report ASCII so it
    # is readable in a plain terminal as well as a UTF-8 one.
    print("ThoughtMap full corpus recovery - " + ("APPLIED" if applied else "DRY RUN"))
    print()
    print(f"  current documents            : {plan.current_documents}")
    print(f"  duplicates within current    : {plan.duplicates_within_current}")
    print(f"  current unique documents     : {plan.current_unique_documents}")
    print(f"    of which personal (carried): {plan.carried_personal}")
    print(f"  candidate documents          : {plan.candidate_documents}")
    print(f"  new unique documents         : {plan.new_unique_documents}")
    print(f"  duplicates skipped           : {plan.duplicates_skipped}")
    print(f"  updates to existing rows     : {plan.updates}")
    print()
    print(f"  embedding-compatible rows    : {plan.embedding_compatible_rows}")
    print(f"  missing embeddings           : {plan.missing_embeddings}")
    print(f"  missing parameters           : {plan.missing_parameters}")
    print()
    print(f"  projected final documents    : {plan.projected_final_documents}")
    print(f"  projected final embeddings   : {plan.projected_final_embeddings}")
    print()
    print("  duplicate analysis of the current master, by identity rule:")
    for rule, count in plan.duplicate_analysis.items():
        print(f"    {rule:26s}: {count}")

    consistent = (
        plan.projected_final_documents
        == plan.current_unique_documents + plan.new_unique_documents
        and plan.missing_embeddings == 0
        and plan.incompatible_embeddings == 0
    )
    print()
    print(f"  internally consistent        : {'yes' if consistent else 'NO'}")

    for warning in plan.warnings:
        print(f"  WARNING: {warning}")


def write_merged_embeddings(merged: pd.DataFrame, out_path: Path) -> dict[str, Any]:
    """Stream the merged embedding artifact to `out_path`.

    Streamed in chunks rather than concatenated in memory: the result is ~542 MB
    of text and the two inputs together are larger than is comfortable to hold.

    doc_ids are rewritten to the canonical `source:bare` form on the way
    through, so the artifact aligns with the documents master by construction.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wanted = set(merged["doc_id"])
    temporary = out_path.with_suffix(out_path.suffix + ".tmp")

    written = 0
    seen: set[str] = set()
    header_done = False

    def emit(frame: pd.DataFrame, mode: str) -> int:
        nonlocal header_done
        frame.to_csv(
            temporary,
            mode=mode,
            header=not header_done,
            index=False,
            encoding="utf-8-sig" if not header_done else "utf-8",
        )
        header_done = True
        return len(frame)

    if temporary.exists():
        temporary.unlink()

    # External gutendex embeddings, bare ids -> gutendex: prefix.
    external = EXTERNAL_MASTER / "embeddings_master.csv"
    if external.exists():
        for chunk in pd.read_csv(
            external, dtype=str, encoding="utf-8-sig", chunksize=5000
        ):
            chunk = chunk.fillna("")
            chunk["doc_id"] = [prefixed_doc_id("gutendex", d) for d in chunk["doc_id"]]
            chunk = chunk[chunk["doc_id"].isin(wanted) & ~chunk["doc_id"].isin(seen)]
            if chunk.empty:
                continue
            seen.update(chunk["doc_id"])
            written += emit(chunk[["doc_id", "model_name", "embedding"]], "a" if header_done else "w")

    # Repository embeddings supply the personal works, and any gutendex rows the
    # external master somehow lacks.
    repo_docs = load_repo_documents()
    source_by_id = dict(zip(repo_docs["doc_id"], repo_docs["source"]))
    for chunk in pd.read_csv(
        OFFICIAL_DIR / "embeddings_master.csv", dtype=str, encoding="utf-8-sig", chunksize=5000
    ):
        chunk = chunk.fillna("")
        chunk["doc_id"] = [
            prefixed_doc_id(source_by_id.get(d, ""), d) for d in chunk["doc_id"]
        ]
        chunk = chunk[chunk["doc_id"].isin(wanted) & ~chunk["doc_id"].isin(seen)]
        if chunk.empty:
            continue
        seen.update(chunk["doc_id"])
        written += emit(chunk[["doc_id", "model_name", "embedding"]], "a" if header_done else "w")

    temporary.replace(out_path)
    return {"rows": written, "unique_doc_ids": len(seen), "path": str(out_path)}


def write_manifest(
    documents: pd.DataFrame,
    documents_path: Path,
    embeddings_info: dict[str, Any],
    embeddings_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    """Corpus manifest: identity of the artifacts, not their location.

    The embedding artifact is identified by its content hash and row count. A
    local path is recorded only as a development hint, because the artifact is
    expected to be resolved through THOUGHTMAP_EMBEDDINGS_PATH and may live
    anywhere.
    """
    manifest = {
        "schema_version": 1,
        "corpus_version": datetime.now(timezone.utc).strftime("%Y%m%d"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "document_count": int(len(documents)),
        "embedding_count": int(embeddings_info["unique_doc_ids"]),
        "embedding_dimension": EXPECTED_DIMENSION,
        "embedding_model": CANONICAL_MODEL,
        "documents_sha256": file_digest(documents_path),
        "embedding_artifact_sha256": file_digest(embeddings_path),
        "embedding_artifact_bytes": embeddings_path.stat().st_size,
        "embedding_artifact_filename": embeddings_path.name,
        "embedding_artifact_local_hint": str(embeddings_path),
        "parameters_sha256": "",
        "sources": {
            str(k): int(v) for k, v in documents["source"].value_counts().items()
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recover the full ThoughtMap corpus.")
    parser.add_argument("--dry-run", action="store_true", help="Report only. Default.")
    parser.add_argument("--apply", action="store_true", help="Write the merged master.")
    parser.add_argument("--json", default="", help="Write the plan as JSON here.")
    parser.add_argument(
        "--embeddings-out",
        default=str(EXTERNAL_MASTER / "thoughtmap_canonical_embeddings.csv"),
        help="Where to write the merged embedding artifact. Kept out of git.",
    )
    args = parser.parse_args(argv)

    plan, merged = build_plan()
    audit_embeddings(plan, merged)

    print_report(plan, applied=False)

    if args.json:
        Path(args.json).write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to write.")
        return 0

    if plan.missing_embeddings or plan.incompatible_embeddings:
        print("\nRefusing to apply: the plan is not internally consistent.", file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print("\nBacking up:")
    for line in backup_official(stamp):
        print(f"  {line}")

    embeddings_out = Path(args.embeddings_out)
    print(f"\nWriting embedding artifact to {embeddings_out} ...")
    info = write_merged_embeddings(merged, embeddings_out)
    print(f"  rows written: {info['rows']}  unique doc_ids: {info['unique_doc_ids']}")

    if info["unique_doc_ids"] != plan.projected_final_documents:
        print(
            f"\nRefusing to continue: embedding artifact has {info['unique_doc_ids']} "
            f"rows but the documents master has {plan.projected_final_documents}.",
            file=sys.stderr,
        )
        return 1

    documents_path = OFFICIAL_DIR / "documents_master.csv"
    print(f"Writing documents master to {documents_path} ...")
    merged.to_csv(documents_path, index=False, encoding="utf-8-sig")

    manifest_path = OFFICIAL_DIR / "corpus_manifest.json"
    manifest = write_manifest(merged, documents_path, info, embeddings_out, manifest_path)
    print(f"Wrote manifest {manifest_path}")
    print(f"  documents        : {manifest['document_count']}")
    print(f"  embeddings       : {manifest['embedding_count']}")
    print(f"  sources          : {manifest['sources']}")
    print(f"  artifact sha256  : {manifest['embedding_artifact_sha256'][:16]}...")
    print()
    print("Point the API at the artifact with:")
    print(f'  THOUGHTMAP_EMBEDDINGS_PATH="{embeddings_out}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
