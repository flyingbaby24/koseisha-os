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
