from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd


WEB_DIR = Path(__file__).resolve().parents[1]
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from search_utils import parse_embedding  # noqa: E402
from skill_generation.skill_generation_pipeline import DEFAULT_MODEL_NAME, generate_skill  # noqa: E402
from skill_generation.models import SkillInput  # noqa: E402
from skill_generation.skill_parameter_mapper import PARAMETER_ORDER  # noqa: E402


def _read_input_json(path: Path) -> SkillInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SkillInput(
        doc_id=str(payload.get("doc_id", "") or ""),
        embedding=[float(x) for x in payload.get("embedding", [])],
        parameter_scores=dict(payload.get("parameter_scores", {}) or {}),
        title=str(payload.get("title", "") or ""),
        author=str(payload.get("author", "") or ""),
        source_type=str(payload.get("source_type", "") or ""),
        text_excerpt=str(payload.get("text_excerpt", "") or ""),
        user_id=payload.get("user_id"),
    )


def _first_existing_column(row: pd.Series, names: list[str]) -> str:
    for name in names:
        if name in row and str(row.get(name, "") or "").strip():
            return str(row.get(name, "") or "").strip()
    return ""


def _read_csv_input(embeddings_path: Path, parameter_scores_path: Path, doc_id: str) -> SkillInput:
    embeddings = pd.read_csv(embeddings_path, dtype=str).fillna("")
    parameter_scores = pd.read_csv(parameter_scores_path).fillna("")

    if "doc_id" not in embeddings.columns or "embedding" not in embeddings.columns:
        raise ValueError("embeddings CSV must contain doc_id and embedding columns.")
    if "doc_id" not in parameter_scores.columns:
        raise ValueError("parameter score CSV must contain a doc_id column.")

    if doc_id:
        emb_rows = embeddings[embeddings["doc_id"].astype(str) == doc_id]
        score_rows = parameter_scores[parameter_scores["doc_id"].astype(str) == doc_id]
    else:
        first_doc_id = str(parameter_scores["doc_id"].iloc[0])
        emb_rows = embeddings[embeddings["doc_id"].astype(str) == first_doc_id]
        score_rows = parameter_scores[parameter_scores["doc_id"].astype(str) == first_doc_id]

    if emb_rows.empty:
        raise ValueError(f"No embedding row found for doc_id: {doc_id or '<first parameter row>'}")
    if score_rows.empty:
        raise ValueError(f"No parameter score row found for doc_id: {doc_id or '<first parameter row>'}")

    emb_row = emb_rows.iloc[0]
    score_row = score_rows.iloc[0]
    embedding = parse_embedding(emb_row.get("embedding", ""))
    if embedding is None:
        raise ValueError(f"Could not parse embedding for doc_id: {emb_row.get('doc_id', '')}")

    parameter_scores_dict = {}
    for parameter in PARAMETER_ORDER:
        aliases = [parameter]
        if parameter == "economics":
            aliases.append("economy")
        if parameter == "morality":
            aliases.append("moral")
        value = _first_existing_column(score_row, aliases)
        parameter_scores_dict[parameter] = float(value) if value else 0.0

    return SkillInput(
        doc_id=str(emb_row.get("doc_id", "") or score_row.get("doc_id", "")),
        embedding=[float(x) for x in embedding],
        parameter_scores=parameter_scores_dict,
        title=_first_existing_column(score_row, ["title", "card_name", "source_title"]),
        author=_first_existing_column(score_row, ["author"]),
        source_type=_first_existing_column(score_row, ["source", "source_type"]),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run Source of Thought skill generation from existing ThoughtMap embeddings."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input-json", type=Path, help="Skill input JSON path.")
    input_group.add_argument("--embeddings", type=Path, help="Embeddings CSV path.")
    parser.add_argument(
        "--parameter-scores",
        type=Path,
        help="Parameter scores CSV path. Required when --embeddings is used.",
    )
    parser.add_argument("--doc-id", default="", help="doc_id to generate from CSV inputs.")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="SentenceTransformer model name.")
    parser.add_argument("--generation-version", type=int, default=1)
    parser.add_argument("--reference-cache", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON without DB writes.")
    return parser.parse_args()


def load_skill_input(args: argparse.Namespace) -> SkillInput:
    if args.input_json:
        return _read_input_json(args.input_json)
    if not args.parameter_scores:
        raise ValueError("--parameter-scores is required when --embeddings is used.")
    return _read_csv_input(args.embeddings, args.parameter_scores, args.doc_id)


def main() -> int:
    args = parse_args()
    skill_input = load_skill_input(args)
    kwargs: dict[str, Any] = {
        "skill_input": skill_input,
        "generation_version": args.generation_version,
        "model_name": args.model_name,
    }
    if args.reference_cache:
        kwargs["reference_cache_path"] = args.reference_cache

    skill = generate_skill(**kwargs)
    payload = skill.to_dict()
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")

    print(text)
    if not args.dry_run:
        print()
        print("Note: this MVP currently performs dry-run JSON generation only; no DB write was attempted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

