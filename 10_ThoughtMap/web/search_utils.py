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

        rows.append({
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
        })

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
