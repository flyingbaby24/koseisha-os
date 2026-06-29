from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd


WEB_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = WEB_DIR.parent

if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from card_game import THOUGHTMAP_PARAMETERS, build_cards_from_parameters  # noqa: E402


DEFAULT_DOCUMENTS_PATH = PROJECT_DIR / "data" / "thoughtmap_db" / "official" / "documents_master.csv"
DEFAULT_OUTPUT_PATH = Path(__file__).with_name("cards_preview.csv")


def read_csv_header(path: Path) -> list[str]:
    try:
        return list(pd.read_csv(path, nrows=0).columns)
    except Exception:
        return []


def iter_candidate_score_files(project_dir: Path) -> list[Path]:
    candidate_roots = [
        project_dir / "data",
        project_dir / "output",
        project_dir / "gutendex_books",
    ]

    files: list[Path] = []
    for root_path in candidate_roots:
        if root_path.exists():
            files.extend(sorted(root_path.rglob("*.csv")))
    return files


def inspect_parameter_score_files(project_dir: Path) -> list[dict[str, object]]:
    required = ["doc_id", *THOUGHTMAP_PARAMETERS]
    inspected = []

    for path in iter_candidate_score_files(project_dir):
        columns = read_csv_header(path)
        present = [column for column in required if column in columns]
        if present:
            inspected.append(
                {
                    "path": path,
                    "columns": columns,
                    "present": present,
                    "missing": [column for column in required if column not in columns],
                }
            )

    return sorted(inspected, key=lambda item: len(item["present"]), reverse=True)


def find_parameter_scores_path(project_dir: Path) -> Path | None:
    for item in inspect_parameter_score_files(project_dir):
        if not item["missing"]:
            return item["path"]
    return None


def missing_parameter_score_columns(path: Path) -> list[str]:
    required = ["doc_id", *THOUGHTMAP_PARAMETERS]
    columns = read_csv_header(path)
    return [column for column in required if column not in columns]


def print_missing_parameter_report(inspected: list[dict[str, object]]) -> None:
    required = ["doc_id", *THOUGHTMAP_PARAMETERS]

    print("No card parameter CSV was found with all required columns.")
    print()
    print("Required columns:")
    print(", ".join(required))

    if inspected:
        closest = inspected[0]
        print()
        print("Closest CSV found:")
        print(closest["path"])
        print("Present columns:")
        print(", ".join(closest["present"]))
        print("Missing columns:")
        print(", ".join(closest["missing"]))

    print()
    print("Smallest compatible data-format fix:")
    print(
        "Add a CSV such as data/thoughtmap_db/official/parameter_scores.csv "
        "with doc_id plus the 10 Thought Composition parameter columns. Values may be "
        "0-100 or 0.0-1.0."
    )


def select_document_sample(
    documents: pd.DataFrame,
    parameter_scores: pd.DataFrame,
    sample_size: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    sample_doc_ids = parameter_scores["doc_id"].astype(str).head(sample_size)
    scores_sample = parameter_scores[
        parameter_scores["doc_id"].astype(str).isin(sample_doc_ids)
    ]
    documents_sample = documents[
        documents["doc_id"].astype(str).isin(sample_doc_ids)
    ]

    if documents_sample.empty and {"doc_id", "title", "source"}.issubset(parameter_scores.columns):
        metadata_columns = [
            column for column in ["doc_id", "title", "author", "source"]
            if column in parameter_scores.columns
        ]
        documents_sample = scores_sample[metadata_columns].copy()

    return documents_sample, scores_sample


def build_preview(
    documents_path: Path,
    parameter_scores_path: Path,
    output_path: Path | None,
    sample_size: int,
) -> pd.DataFrame:
    documents = pd.read_csv(documents_path, dtype=str).fillna("")
    parameter_scores = pd.read_csv(parameter_scores_path)

    documents_sample, scores_sample = select_document_sample(
        documents,
        parameter_scores,
        sample_size,
    )

    cards = build_cards_from_parameters(documents_sample, scores_sample)

    print("Parameter columns used:")
    print(", ".join(THOUGHTMAP_PARAMETERS))
    print()
    print("Generated card preview:")
    print(cards.head(10).to_string(index=False))

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cards.to_csv(output_path, index=False, encoding="utf-8-sig")
        print()
        print(f"Saved preview CSV: {output_path}")

    return cards


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a cards.csv-compatible ThoughtMap card preview."
    )
    parser.add_argument(
        "--documents",
        type=Path,
        default=DEFAULT_DOCUMENTS_PATH,
        help="Path to a documents CSV with doc_id, title, author, and source columns.",
    )
    parser.add_argument(
        "--parameter-scores",
        type=Path,
        default=None,
        help="Path to a parameter score CSV with doc_id and the 10 ThoughtMap parameters.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to save cards_preview.csv. Use --no-save to print only.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=50,
        help="Number of source rows to use for the preview.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print the preview without writing cards_preview.csv.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.documents.exists():
        print(f"Documents CSV not found: {args.documents}")
        return 1

    parameter_scores_path = args.parameter_scores or find_parameter_scores_path(PROJECT_DIR)
    if parameter_scores_path is None:
        print_missing_parameter_report(inspect_parameter_score_files(PROJECT_DIR))
        return 1

    if not parameter_scores_path.exists():
        print(f"Parameter score CSV not found: {parameter_scores_path}")
        return 1

    missing_columns = missing_parameter_score_columns(parameter_scores_path)
    if missing_columns:
        print(f"Parameter score CSV is missing required Thought Composition columns: {parameter_scores_path}")
        print(", ".join(missing_columns))
        return 1

    output_path = None if args.no_save else args.output
    build_preview(args.documents, parameter_scores_path, output_path, args.sample_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
