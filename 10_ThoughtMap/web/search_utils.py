from __future__ import annotations

import json
import math
import re
from typing import Optional

import numpy as np
import pandas as pd


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_key(value: object) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


NO_FILTER_VALUES = {"", "all", "general"}


def normalize_filter_value(value: object) -> str:
    """Normalize UI/API filter values without treating NULL as text."""
    return normalize_key(value)


def is_no_filter(value: object) -> bool:
    return normalize_filter_value(value) in NO_FILTER_VALUES


def parse_multi_value(value: object) -> list[str]:
    """Read a scalar, JSON list/dict, or delimiter-separated metadata value."""
    text = normalize_text(value)
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [normalize_text(item) for item in parsed if normalize_text(item)]
        if isinstance(parsed, dict):
            return [normalize_text(key) for key, enabled in parsed.items() if enabled and normalize_text(key)]
        if parsed is not None and not isinstance(parsed, (dict, list)):
            text = normalize_text(parsed)
    except (json.JSONDecodeError, TypeError):
        pass
    return [part.strip() for part in re.split(r"[|;,]", text) if part.strip()]


def filter_options(df: pd.DataFrame, column: str, default: str = "all", multi: bool = False) -> list[str]:
    if df is None or df.empty or column not in df.columns:
        return [default]
    values: dict[str, str] = {}
    for raw in df[column]:
        items = parse_multi_value(raw) if multi else [normalize_text(raw)]
        for item in items:
            key = normalize_key(item)
            if key and key not in values:
                values[key] = item
    return [default, *sorted(values.values(), key=lambda item: normalize_key(item))]


def apply_metadata_filter(df: pd.DataFrame, column: str, selected: object, multi: bool = False) -> pd.DataFrame:
    if df is None or df.empty or is_no_filter(selected) or column not in df.columns:
        return df
    wanted = normalize_filter_value(selected)
    if multi:
        mask = df[column].map(lambda value: wanted in {normalize_key(item) for item in parse_multi_value(value)})
    else:
        mask = df[column].map(normalize_key) == wanted
    return df[mask].copy().reset_index(drop=True)


def parameter_names(df: pd.DataFrame) -> list[str]:
    names: dict[str, str] = {}
    if df is None or df.empty:
        return []
    for column in ["parameter_scores", "parameters", "filter_scores", "composition", "thought_composition", "scores"]:
        if column not in df.columns:
            continue
        for raw in df[column]:
            value = raw
            if isinstance(raw, str):
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError:
                    continue
            if isinstance(value, dict):
                for key in value:
                    if normalize_key(key): names.setdefault(normalize_key(key), normalize_text(key))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        key = item.get("key")
                        if normalize_key(key): names.setdefault(normalize_key(key), normalize_text(key))
    return sorted(names.values(), key=normalize_key)


def _parameter_score_map(row: pd.Series) -> dict[str, float]:
    for column in ["parameter_scores", "parameters", "filter_scores", "composition", "thought_composition", "scores"]:
        if column not in row.index:
            continue
        value = row.get(column)
        if isinstance(value, str):
            try: value = json.loads(value)
            except json.JSONDecodeError: continue
        if isinstance(value, dict):
            return {normalize_key(k): float(v) for k, v in value.items() if normalize_key(k) and pd.notna(v)}
        if isinstance(value, list):
            out = {}
            for item in value:
                if isinstance(item, dict) and "key" in item and "value" in item:
                    try: out[normalize_key(item["key"])] = float(item["value"])
                    except (TypeError, ValueError): pass
            if out: return out
    return {}


def apply_parameter_filter(df: pd.DataFrame, selected: object, corpus=None) -> pd.DataFrame:
    """Keep works whose highest-scoring (representative) parameter is selected.

    With a `corpus`, the dominant axis comes from its parameter matrix in one
    vectorised pass. Without one, the original per-row path runs, so a frame
    that still carries `parameter_scores` dicts - a personal-document frame, or
    a test double - behaves exactly as before.
    """
    if df is None or df.empty or is_no_filter(selected):
        return df
    wanted = normalize_filter_value(selected)

    dominant = getattr(corpus, "dominant_axis", None)
    axes = tuple(getattr(corpus, "parameter_axes", ()) or ())
    if dominant is not None and axes and MATRIX_ROW_COLUMN in df.columns:
        positions = subset_positions(df, len(corpus.parameter_matrix))
        if positions is not None:
            try:
                wanted_index = [normalize_key(a) for a in axes].index(wanted)
            except ValueError:
                # An axis nobody has: no row can be dominated by it.
                return df.iloc[0:0].copy().reset_index(drop=True)
            mask = dominant()[positions] == wanted_index
            return df[mask].copy().reset_index(drop=True)

    def matches(row: pd.Series) -> bool:
        scores = _parameter_score_map(row)
        return bool(scores) and max(scores, key=scores.get) == wanted

    return df[df.apply(matches, axis=1)].copy().reset_index(drop=True)


def safe_filename(value: object, max_len: int = 80) -> str:
    text = normalize_text(value) or "embedding"
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    text = re.sub(r"\s+", "_", text).strip("_")
    return (text[:max_len] or "embedding")


def vector_to_json(vec: np.ndarray) -> str:
    return json.dumps([float(x) for x in vec], ensure_ascii=False)



def make_embedding_download_csv(
    title: str,
    author: str,
    doc_id: str,
    gutenberg_id: str,
    source: str,
    source_url: str,
    embedding: str,
    category: str = "",
    subcategory: str = "",
) -> str:
    row = {
        "doc_id": normalize_text(doc_id),
        "author": normalize_text(author),
        "title": normalize_text(title),
        "source": normalize_text(source),
        "category": normalize_text(category),
        "subcategory": normalize_text(subcategory),
        "gutenberg_id": normalize_text(gutenberg_id),
        "source_url": normalize_text(source_url),
        "embedding": normalize_text(embedding),
    }
    return pd.DataFrame([row]).to_csv(index=False, encoding="utf-8-sig")

def parse_embedding(value: object) -> Optional[np.ndarray]:
    s = normalize_text(value)
    if not s:
        return None

    try:
        arr = np.array(json.loads(s), dtype=np.float32)
        if arr.ndim == 1 and arr.size > 0:
            return arr
    except Exception:
        pass

    try:
        cleaned = s.strip().strip("[]")
        parts = re.split(r"[,\s]+", cleaned)
        nums = [float(x) for x in parts if x]
        arr = np.array(nums, dtype=np.float32)
        if arr.ndim == 1 and arr.size > 0:
            return arr
    except Exception:
        return None

    return None


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0 or math.isnan(denom):
        return 0.0
    return float(np.dot(a, b) / denom)


def normalized_average_vector(vecs: list[np.ndarray]) -> np.ndarray:
    stacked = np.stack(vecs)
    avg = stacked.mean(axis=0)
    norm = np.linalg.norm(avg)
    if norm > 0:
        avg = avg / norm
    return avg


#: Internal columns that must never appear in a search response.
INTERNAL_COLUMNS = ("_embedding_vec", "_matrix_row")

RESULT_COLUMNS = [
    "doc_id",
    "gutenberg_id",
    "author",
    "title",
    "source",
    "category",
    "subcategory",
    "source_url",
    "model_name",
    "embedding",
]

OPTIONAL_PARAMETER_COLUMNS = [
    "parameters",
    "parameter_scores",
    "filter_scores",
    "composition",
    "thought_composition",
    "scores",
]


def cosine_against_matrix(
    vectors: list[np.ndarray],
    target_vec: np.ndarray,
    matrix: np.ndarray | None = None,
    row_norms: np.ndarray | None = None,
) -> np.ndarray:
    """Cosine similarity of `target_vec` against every row, in one pass.

    Numerically the same definition as `cosine()`, including its rule that a
    zero or NaN denominator scores 0.0. BLAS may sum the dot product in a
    different order than a single-vector `np.dot`, so individual values can
    differ in the last few bits; the API rounds similarity to 4 decimals, well
    above that.

    `matrix` and `row_norms`, when given, are an already-prepared form of
    exactly the same rows (T7 #10). Passing them skips rebuilding a 93.6 MB
    block per request. `row_norms` is only ever supplied for the *whole*
    matrix, which is the same array the stacking path would itself have
    measured, so the arithmetic is unchanged rather than merely equivalent.
    """
    if matrix is None:
        matrix = np.stack(vectors).astype(np.float32, copy=False)

    target = np.asarray(target_vec, dtype=np.float32)

    if row_norms is None:
        row_norms = np.linalg.norm(matrix, axis=1)

    denominator = row_norms * float(np.linalg.norm(target))
    similarities = np.zeros(matrix.shape[0], dtype=np.float64)

    usable = (denominator != 0) & ~np.isnan(denominator)
    if not usable.any():
        return similarities

    if usable.all():
        # Every row is usable, which is the normal case for a healthy corpus.
        # Boolean-mask indexing would allocate and copy the whole matrix — 93.6
        # MB at 63,891 documents — to select all of it, before the matmul that
        # actually costs 2 ms. Multiplying the full matrix is the identical
        # arithmetic on identical rows, without the copy.
        similarities[:] = (matrix @ target) / denominator
        return similarities

    similarities[usable] = (matrix[usable] @ target) / denominator[usable]

    return similarities


#: Explicit position of each row in the corpus embedding matrix.
#:
#: Index labels cannot serve this purpose: `apply_metadata_filter` and
#: `apply_parameter_filter` both end with `reset_index(drop=True)`, so after any
#: filter the labels are 0..N-1 of the *subset*. Using them would index the
#: matrix with plausible-looking numbers that point at the wrong documents, and
#: a filtered search would return confidently wrong results. A real column
#: survives filtering, copying and reindexing.
MATRIX_ROW_COLUMN = "_matrix_row"


def subset_positions(frame: pd.DataFrame, row_count: int) -> np.ndarray | None:
    """Row positions of `frame` within a matrix of `row_count` rows, or None.

    Read from `MATRIX_ROW_COLUMN`, which the corpus stamps onto its frame.
    A frame without that column did not come from a prepared corpus, so the
    caller stacks instead - which is always correct, only slower.
    """
    if row_count <= 0 or frame is None or frame.empty:
        return None
    if MATRIX_ROW_COLUMN not in frame.columns:
        return None

    positions = frame[MATRIX_ROW_COLUMN].to_numpy()
    if positions.size == 0 or not np.issubdtype(positions.dtype, np.integer):
        return None
    if positions.min() < 0 or positions.max() >= row_count:
        return None

    return positions


def prepared_vectors(frame: pd.DataFrame, corpus) -> tuple:
    """(matrix, row_norms) for `frame` taken from `corpus`, or (None, None).

    Three cases, and the distinction between the last two is the whole point:

    - No usable corpus: the caller stacks, exactly as before.
    - The frame *is* the whole corpus, in order: use the prepared matrix and
      its precomputed norms. This is the common case - an unfiltered search -
      and both arrays are what the stacking path would itself have produced.
    - The frame is a filtered subset: index the matrix, but recompute the norms
      over that subset. Reusing a slice of the full norm vector would very
      likely give identical numbers, but "very likely" is not a basis for
      changing ranking arithmetic, and a subset is small enough to measure
      cheaply.
    """
    matrix = getattr(corpus, "matrix", None)
    if matrix is None or getattr(matrix, "size", 0) == 0:
        return None, None

    positions = subset_positions(frame, len(matrix))
    if positions is None:
        return None, None

    if len(positions) == len(matrix) and np.array_equal(
        positions, np.arange(len(matrix))
    ):
        # The frame is the corpus itself, unfiltered and in order.
        return matrix, corpus.norms

    subset = matrix[positions]
    return subset, np.linalg.norm(subset, axis=1)


def work_similarity_by_vector(
    df: pd.DataFrame,
    target_vec: np.ndarray,
    top: int,
    exclude_doc_id: str = "",
    include_self: bool = False,
    corpus=None,
) -> pd.DataFrame:
    """Rank documents by cosine similarity to `target_vec`.

    Vectorised in phase T4.6. The row-by-row original cost ~0.5 s at 4,915
    documents, which became several seconds once the corpus reached 63,891.
    Ranking policy is unchanged: same cosine definition, same exclusion rule,
    same sort, same top-N, same columns. Only the arithmetic moved into NumPy.

    `corpus` is an optional object exposing `.matrix` and `.norms` covering
    these rows (T7 #10). It is a pure performance hint: absent, or not lined up
    with `df`, the original stacking path runs and gives the same answer.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    frame = df

    if exclude_doc_id and not include_self and "doc_id" in frame.columns:
        target_key = normalize_text(exclude_doc_id)
        frame = frame[frame["doc_id"].map(normalize_text) != target_key]

    if frame.empty:
        return pd.DataFrame()

    matrix, row_norms = prepared_vectors(frame, corpus)
    vectors = [] if matrix is not None else frame["_embedding_vec"].to_list()

    try:
        similarities = cosine_against_matrix(vectors, target_vec, matrix, row_norms)
    except ValueError:
        # Ragged vectors cannot be stacked. Rather than guess, fall back to the
        # per-row path, which handles mismatched dimensions one at a time.
        similarities = np.array(
            [
                cosine(target_vec, vector)
                for vector in frame["_embedding_vec"].to_list()
            ],
            dtype=np.float64,
        )

    # Rank first, then materialise only the rows that survive.
    #
    # Building a 63,891-row frame to immediately discard all but the top 10 was
    # the dominant cost at full corpus size. A stable descending argsort gives
    # the same order pandas produced while touching a fraction of the data.
    order = np.argsort(-similarities, kind="stable")[: max(0, int(top))]
    if order.size == 0:
        return pd.DataFrame()

    selected = frame.iloc[order]

    # Same column set and order the row-wise version produced. A column absent
    # from the input still appears, filled with "", because `row.get(col, "")`
    # did that.
    data = {"similarity": similarities[order]}
    if MATRIX_ROW_COLUMN in selected.columns:
        # Carried through so the caller can look up this row's Thought
        # Composition without the frame holding 63,891 dicts.
        data[MATRIX_ROW_COLUMN] = selected[MATRIX_ROW_COLUMN].to_numpy()
    for column in RESULT_COLUMNS:
        data[column] = selected[column].to_numpy() if column in selected.columns else ""

    out = pd.DataFrame(data, index=pd.RangeIndex(len(order)))

    for column in OPTIONAL_PARAMETER_COLUMNS:
        if column in selected.columns:
            out[column] = selected[column].to_numpy()

    if out.empty:
        return out

    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def author_similarity_by_vector(
    df: pd.DataFrame,
    target_vec: np.ndarray,
    target_author: str,
    top: int,
    include_same_author: bool = False,
) -> pd.DataFrame:
    target_author_key = normalize_key(target_author)
    rows = []

    for author, group in df.groupby("author", dropna=False):
        author = normalize_text(author)
        if not author:
            continue

        if not include_same_author and target_author_key and normalize_key(author) == target_author_key:
            continue

        avg = normalized_average_vector(group["_embedding_vec"].to_list())
        rows.append({
            "similarity": cosine(target_vec, avg),
            "author": author,
            "works_count": len(group),
            "sample_titles": " | ".join(group["title"].head(3).map(normalize_text).tolist()),
            "source": "author_average",
            "embedding": vector_to_json(avg),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out.sort_values("similarity", ascending=False).head(top).reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


def format_similarity(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "similarity" in out.columns:
        out["similarity"] = out["similarity"].map(lambda x: round(float(x), 4))
    return out
