from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from search_utils import parse_embedding
from storage import load_official_db

from .config import DEFAULT_MODEL_NAME
from .repositories import PROJECT_ROOT, _resolve_project_path


WEB_DIR = PROJECT_ROOT / "web"
DEFAULT_OFFICIAL_DIR = PROJECT_ROOT / "data" / "thoughtmap_db" / "official"
DEFAULT_FILTER_PATH = WEB_DIR / "filters" / "general.json"
DEFAULT_OUTPUT_PATH = DEFAULT_OFFICIAL_DIR / "parameter_scores.csv"


def load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        raise RuntimeError(
            "sentence-transformers is required to generate parameter_scores.csv. "
            "Install the web requirements before running this offline generation script."
        ) from exc

    return SentenceTransformer(model_name)


def load_thought_composition_helpers():
    try:
        from thought_composition import make_filter_scores, make_parameter_scores
    except Exception as exc:
        raise RuntimeError(
            "thought_composition dependencies are required to generate parameter_scores.csv. "
            "Install the web requirements before running this offline generation script."
        ) from exc

    return make_filter_scores, make_parameter_scores


def load_filter_categories(filter_path: str | Path) -> dict:
    path = resolve_filter_path(filter_path)
    if not path.exists():
        raise FileNotFoundError(f"Filter JSON not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError(f"Filter JSON must be a non-empty object: {path}")

    return data


def resolve_filter_path(filter_path: str | Path) -> Path:
    path = Path(filter_path)
    if path.is_absolute():
        return path

    web_path = WEB_DIR / path
    if web_path.exists():
        return web_path

    project_path = PROJECT_ROOT / path
    if project_path.exists():
        return project_path

    return web_path


def load_official_embedding_frame(official_dir: str | Path) -> tuple[pd.DataFrame, np.ndarray]:
    documents, embeddings, _map_points = load_official_db(official_dir)
    merged = documents.merge(embeddings, on="doc_id", how="inner")
    merged = merged.copy()
    merged["_embedding_vec"] = merged["embedding"].map(parse_embedding)
    merged = merged[merged["_embedding_vec"].notna()].reset_index(drop=True)

    if merged.empty:
        raise ValueError("No official documents with valid embeddings were found.")

    embedding_matrix = np.stack(merged["_embedding_vec"].to_list())
    return merged, embedding_matrix


def generate_parameter_scores(
    official_dir: str | Path = DEFAULT_OFFICIAL_DIR,
    filter_path: str | Path = DEFAULT_FILTER_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
) -> dict[str, str | int]:
    official_path = _resolve_project_path(official_dir)
    output = _resolve_project_path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    categories = load_filter_categories(filter_path)
    documents, embedding_matrix = load_official_embedding_frame(official_path)
    model = load_model(model_name)
    make_filter_scores, make_parameter_scores = load_thought_composition_helpers()

    filter_score_df = make_filter_scores(embedding_matrix, categories, model)
    parameter_scores = make_parameter_scores(documents, filter_score_df, parameters=categories.keys())
    parameter_scores.to_csv(output, index=False, encoding="utf-8-sig")

    return {
        "official_dir": str(official_path),
        "filter_path": str(resolve_filter_path(filter_path)),
        "output_path": str(output),
        "rows": int(len(parameter_scores)),
        "parameters": len(categories),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate official ThoughtMap parameter_scores.csv from existing document embeddings."
    )
    parser.add_argument(
        "--official-dir",
        default=str(DEFAULT_OFFICIAL_DIR),
        help="Directory containing documents_master.csv and embeddings_master.csv.",
    )
    parser.add_argument(
        "--filter",
        default=str(DEFAULT_FILTER_PATH),
        help="Filter JSON used as the parameter definition, for example filters/general.json.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output parameter_scores.csv path.",
    )
    parser.add_argument(
        "--model-name",
        default=DEFAULT_MODEL_NAME,
        help="SentenceTransformer model used to embed filter labels/descriptions.",
    )
    args = parser.parse_args()

    result = generate_parameter_scores(
        official_dir=args.official_dir,
        filter_path=args.filter,
        output_path=args.output,
        model_name=args.model_name,
    )

    print("Generated ThoughtMap parameter scores")
    print(f"official_dir: {result['official_dir']}")
    print(f"filter_path: {result['filter_path']}")
    print(f"output_path: {result['output_path']}")
    print(f"rows: {result['rows']}")
    print(f"parameters: {result['parameters']}")


if __name__ == "__main__":
    main()
