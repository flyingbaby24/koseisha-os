from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


WEB_DIR = Path(__file__).resolve().parents[1]
if str(WEB_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_DIR))

from generate_skills import load_skill_input  # noqa: E402
from skill_generation.skill_generation_pipeline import DEFAULT_MODEL_NAME, generate_skill  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify deterministic Source of Thought skill generation."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input-json", type=Path, help="Skill input JSON path.")
    input_group.add_argument("--embeddings", type=Path, help="Embeddings CSV path.")
    parser.add_argument("--parameter-scores", type=Path, help="Parameter scores CSV path.")
    parser.add_argument("--doc-id", default="", help="doc_id to test from CSV inputs.")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--generation-version", type=int, default=1)
    parser.add_argument("--reference-cache", type=Path, default=None)
    return parser.parse_args()


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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

    first = generate_skill(**kwargs).to_dict()
    second = generate_skill(**kwargs).to_dict()

    if canonical(first) != canonical(second):
        print("Determinism test failed: generated JSON differs.")
        print("First:")
        print(json.dumps(first, ensure_ascii=False, indent=2, sort_keys=True))
        print("Second:")
        print(json.dumps(second, ensure_ascii=False, indent=2, sort_keys=True))
        return 1

    print("Determinism test passed.")
    print(f"skill_id={first.get('skill_id')}")
    print(f"doc_id={first.get('doc_id')}")
    print(f"generation_version={first.get('generation_version')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

