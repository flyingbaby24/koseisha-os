"""Backfill 10-axis Thought Composition scores for the full corpus.

    python -m api.backfill_parameter_scores --verbose

Uses the canonical T1.5 algorithm: cosine of each document embedding against
each filter-category embedding, clipped at zero, then row-normalised so the ten
axes sum to 1.0. That is exactly what `thought_composition.make_filter_scores`
does, and the numbers this produces are checked against the existing
parameter_scores.csv rows before anything is written.

`filter_service.py` implements a *different* scoring rule (per-axis cosine x100,
not normalised) and is deliberately not used here.

The only model work is embedding the ten short category descriptions.
Document vectors already exist and are reused, so nothing is re-embedded.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from search_utils import parse_embedding

from .config import DEFAULT_MODEL_NAME, get_settings
from .repositories import PROJECT_ROOT, create_search_index_repository


WEB_DIR = PROJECT_ROOT / "web"
DEFAULT_FILTER_PATH = WEB_DIR / "filters" / "general.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "thoughtmap_db" / "official" / "parameter_scores.csv"

METADATA_COLUMNS = ["doc_id", "title", "author", "source"]


def load_categories(path: Path) -> dict[str, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError(f"Filter JSON must be a non-empty object: {path}")
    return data


def category_matrix(categories: dict[str, str], model_name: str) -> tuple[list[str], np.ndarray]:
    """Embed the ten axis descriptions. The only model call in this script."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    keys = list(categories.keys())
    vectors = model.encode([categories[k] for k in keys], show_progress_bar=False)
    return keys, np.asarray(vectors, dtype=np.float32)


def compute_scores(documents: np.ndarray, axes: np.ndarray) -> np.ndarray:
    """Thought Composition for every document, in one matrix product.

    Identical arithmetic to `thought_composition.make_filter_scores`:
    `cosine_similarity(documents, axes)` -> clip at 0 -> divide each row by its
    own sum. Done as one (N x 384) @ (384 x 10) product rather than per
    document.
    """
    document_norms = np.linalg.norm(documents, axis=1, keepdims=True)
    axis_norms = np.linalg.norm(axes, axis=1, keepdims=True)

    # Guard the degenerate case the same way cosine_similarity does.
    document_norms[document_norms == 0] = 1.0
    axis_norms[axis_norms == 0] = 1.0

    scores = (documents / document_norms) @ (axes / axis_norms).T
    scores = np.clip(scores, 0, None)

    totals = scores.sum(axis=1, keepdims=True)
    return np.divide(scores, totals, out=np.zeros_like(scores), where=totals != 0)


def verify_against_existing(
    frame: pd.DataFrame,
    keys: list[str],
    scores: np.ndarray,
    existing_path: Path,
    tolerance: float = 5e-3,
) -> dict[str, float | int]:
    """Compare against the parameter rows already in the repository.

    The existing file was produced by the canonical generator, so agreement
    confirms this vectorised path did not change the definition.
    """
    if not existing_path.exists():
        return {"compared": 0}

    existing = pd.read_csv(existing_path, dtype=str, encoding="utf-8-sig").fillna("")
    axis_columns = [k for k in keys if k in existing.columns]
    if not axis_columns:
        return {"compared": 0}

    # Existing rows predate the T4.6 id normalisation, so join on the bare id.
    #
    # Both sides must be restricted to one source first. A bare `doc_000000`
    # exists in the gutendex *and* the personal id space and refers to
    # different documents, so joining across sources silently compares
    # unrelated works — which is exactly the ambiguity that made the original
    # duplicate bug possible.
    if "source" not in existing.columns:
        return {"compared": 0, "note": "existing file has no source column"}

    existing = existing[existing["source"] == "gutendex"].copy()
    existing["_bare"] = existing["doc_id"].str.split(":").str[-1]
    existing = existing.drop_duplicates("_bare", keep="first")

    computed = pd.DataFrame(scores, columns=keys)
    computed["_bare"] = frame["doc_id"].str.split(":").str[-1].to_numpy()
    computed["_source"] = frame["source"].to_numpy()
    computed = computed[computed["_source"] == "gutendex"]

    merged = computed.merge(existing, on="_bare", how="inner", suffixes=("_new", "_old"))
    if merged.empty:
        return {"compared": 0}

    deltas = []
    for axis in axis_columns:
        new = pd.to_numeric(merged[f"{axis}_new"], errors="coerce").to_numpy(dtype=float)
        old = pd.to_numeric(merged[f"{axis}_old"], errors="coerce").to_numpy(dtype=float)
        usable = np.isfinite(new) & np.isfinite(old)
        if usable.any():
            deltas.append(np.abs(new[usable] - old[usable]))

    if not deltas:
        return {"compared": 0}

    stacked = np.concatenate(deltas)
    return {
        "compared": int(len(merged)),
        "max_abs_delta": float(stacked.max()),
        "mean_abs_delta": float(stacked.mean()),
        "within_tolerance": bool(stacked.max() <= tolerance),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill Thought Composition scores.")
    parser.add_argument("--filter", default=str(DEFAULT_FILTER_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    started = time.perf_counter()

    settings = get_settings()
    repository = create_search_index_repository(settings)
    frame = repository.load_index()
    loaded = time.perf_counter() - started
    if args.verbose:
        print(f"loaded index: {len(frame)} rows in {loaded:.1f}s")

    documents = np.stack(frame["_embedding_vec"].to_list()).astype(np.float32)

    categories = load_categories(Path(args.filter))
    keys, axes = category_matrix(categories, args.model_name)
    if args.verbose:
        print(f"embedded {len(keys)} axes: {keys}")

    compute_started = time.perf_counter()
    scores = compute_scores(documents, axes)
    compute_seconds = time.perf_counter() - compute_started

    sums = scores.sum(axis=1)
    # A document whose cosine against all ten axes is <= 0 clips to all zeros,
    # and `make_filter_scores` leaves that row at zero rather than dividing by
    # zero. Canonical behaviour, so those rows are counted, not rejected.
    zero_rows = int((sums == 0).sum())
    scored = sums[sums > 0]

    print(f"documents            : {len(frame)}")
    print(f"axes                 : {len(keys)}")
    print(f"compute time         : {compute_seconds:.2f}s")
    print(f"rows with no affinity: {zero_rows}")
    if scored.size:
        print(f"scored row sums      : {scored.min():.6f} .. {scored.max():.6f}")
    print(f"value range          : {scores.min():.6f} .. {scores.max():.6f}")
    print(f"all finite           : {bool(np.isfinite(scores).all())}")

    verification = verify_against_existing(frame, keys, scores, Path(args.output))
    print(f"verified against existing rows: {verification}")

    if not np.isfinite(scores).all():
        print("Refusing to write: non-finite scores.", file=sys.stderr)
        return 1
    if scored.size and not np.allclose(scored, 1.0, atol=1e-5):
        print("Refusing to write: scored rows do not sum to 1.0.", file=sys.stderr)
        return 1
    if verification.get("compared") and not verification.get("within_tolerance", True):
        print(
            "Refusing to write: recomputed scores disagree with the existing "
            f"canonical rows (max delta {verification.get('max_abs_delta')}).",
            file=sys.stderr,
        )
        return 1

    out = pd.DataFrame(
        {column: frame[column].to_numpy() for column in METADATA_COLUMNS if column in frame.columns}
    )
    for index, key in enumerate(keys):
        out[key] = scores[:, index]

    if args.dry_run:
        print("\nDry run; nothing written.")
        return 0

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"\nwrote {output}  rows={len(out)}  total={time.perf_counter() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
