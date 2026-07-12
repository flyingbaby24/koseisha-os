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


def apply_parameter_filter(df: pd.DataFrame, selected: object) -> pd.DataFrame:
    """Keep works whose highest-scoring (representative) parameter is selected."""
    if df is None or df.empty or is_no_filter(selected):
        return df
    wanted = normalize_filter_value(selected)
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


def work_similarity_by_vector(
    df: pd.DataFrame,
    target_vec: np.ndarray,
    top: int,
    exclude_doc_id: str = "",
    include_self: bool = False,
) -> pd.DataFrame:
    rows = []

    for _, row in df.iterrows():
        if exclude_doc_id and not include_self:
            if normalize_text(row.get("doc_id", "")) == normalize_text(exclude_doc_id):
                continue

        result_row = {
            "similarity": cosine(target_vec, row["_embedding_vec"]),
            "doc_id": row.get("doc_id", ""),
            "gutenberg_id": row.get("gutenberg_id", ""),
            "author": row.get("author", ""),
            "title": row.get("title", ""),
            "source": row.get("source", ""),
            "category": row.get("category", ""),
            "subcategory": row.get("subcategory", ""),
            "source_url": row.get("source_url", ""),
            "model_name": row.get("model_name", ""),
            "embedding": row.get("embedding", ""),
        }

        for column in ["parameters", "parameter_scores", "filter_scores", "composition", "thought_composition", "scores"]:
            if column in row.index:
                result_row[column] = row.get(column)

        rows.append(result_row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out.sort_values("similarity", ascending=False).head(top).reset_index(drop=True)
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
