from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st


APP_TITLE = "ThoughtMap Similarity Search"
DEFAULT_DB_DIR = Path("data") / "thoughtmap_db"
FALLBACK_DB_DIR = Path("master")


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_key(value: object) -> str:
    text = normalize_text(value).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


def resolve_db_dir(db_dir_text: str) -> Path:
    db_dir = Path(db_dir_text)
    if db_dir.exists():
        return db_dir
    if DEFAULT_DB_DIR.exists():
        return DEFAULT_DB_DIR
    return FALLBACK_DB_DIR


@st.cache_data(show_spinner=False)
def load_db_cached(db_dir_text: str) -> pd.DataFrame:
    db_dir = resolve_db_dir(db_dir_text)
    docs_path = db_dir / "documents_master.csv"
    embs_path = db_dir / "embeddings_master.csv"

    if not docs_path.exists():
        raise FileNotFoundError(f"documents_master.csv が見つかりません: {docs_path}")
    if not embs_path.exists():
        raise FileNotFoundError(f"embeddings_master.csv が見つかりません: {embs_path}")

    docs = pd.read_csv(docs_path, dtype=str).fillna("")
    embs = pd.read_csv(embs_path, dtype=str).fillna("")

    if "doc_id" not in docs.columns or "doc_id" not in embs.columns:
        raise ValueError("documents_master.csv / embeddings_master.csv の両方に doc_id 列が必要です。")
    if "embedding" not in embs.columns:
        raise ValueError("embeddings_master.csv に embedding 列がありません。")

    df = docs.merge(embs[["doc_id", "model_name", "embedding"]], on="doc_id", how="inner")
    df["_embedding_vec"] = df["embedding"].map(parse_embedding)
    df = df[df["_embedding_vec"].notna()].copy()
    if df.empty:
        raise ValueError("有効な embedding がありません。")

    df["_dim"] = df["_embedding_vec"].map(lambda x: len(x) if x is not None else 0)
    common_dim = int(df["_dim"].value_counts().idxmax())
    df = df[df["_dim"] == common_dim].copy()

    for col in ["author", "title", "source", "gutenberg_id", "source_url", "status"]:
        if col not in df.columns:
            df[col] = ""

    df["label"] = df.apply(
        lambda r: f"{r.get('title','')} — {r.get('author','')} [{r.get('doc_id','')}]",
        axis=1,
    )
    return df.reset_index(drop=True)


def filter_catalog(df: pd.DataFrame, query: str, source: str) -> pd.DataFrame:
    out = df.copy()
    if source and source != "All":
        out = out[out["source"].map(normalize_text) == source]
    q = normalize_key(query)
    if q:
        mask = (
            out["title"].map(normalize_key).str.contains(re.escape(q), na=False)
            | out["author"].map(normalize_key).str.contains(re.escape(q), na=False)
            | out["gutenberg_id"].map(normalize_key).str.contains(re.escape(q), na=False)
            | out["doc_id"].map(normalize_key).str.contains(re.escape(q), na=False)
        )
        out = out[mask]
    return out


def work_similarity(df: pd.DataFrame, target_doc_id: str, top: int, include_self: bool = False) -> pd.DataFrame:
    target = df[df["doc_id"].map(normalize_text) == normalize_text(target_doc_id)].iloc[0]
    target_vec = target["_embedding_vec"]
    rows = []
    for _, row in df.iterrows():
        if not include_self and normalize_text(row.get("doc_id", "")) == normalize_text(target_doc_id):
            continue
        rows.append({
            "similarity": cosine(target_vec, row["_embedding_vec"]),
            "doc_id": row.get("doc_id", ""),
            "gutenberg_id": row.get("gutenberg_id", ""),
            "author": row.get("author", ""),
            "title": row.get("title", ""),
            "source": row.get("source", ""),
            "source_url": row.get("source_url", ""),
        })
    out = pd.DataFrame(rows).sort_values("similarity", ascending=False).head(top).reset_index(drop=True)
    if not out.empty:
        out.insert(0, "rank", range(1, len(out) + 1))
    return out


def author_similarity(df: pd.DataFrame, target_doc_id: str, top: int, include_same_author: bool = False) -> pd.DataFrame:
    target = df[df["doc_id"].map(normalize_text) == normalize_text(target_doc_id)].iloc[0]
    target_vec = target["_embedding_vec"]
    target_author_key = normalize_key(target.get("author", ""))
    rows = []

    for author, group in df.groupby("author", dropna=False):
        author = normalize_text(author)
        if not author:
            continue
        if not include_same_author and normalize_key(author) == target_author_key:
            continue
        vecs = np.stack(group["_embedding_vec"].to_list())
        avg = vecs.mean(axis=0)
        norm = np.linalg.norm(avg)
        if norm > 0:
            avg = avg / norm
        rows.append({
            "similarity": cosine(target_vec, avg),
            "author": author,
            "works_count": len(group),
            "sample_titles": " | ".join(group["title"].head(3).map(normalize_text).tolist()),
        })

    out = pd.DataFrame(rows).sort_values("similarity", ascending=False).head(top).reset_index(drop=True)
    if not out.empty:
        out.insert(0, "rank", range(1, len(out) + 1))
    return out


def format_similarity(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "similarity" in out.columns:
        out["similarity"] = out["similarity"].map(lambda x: round(float(x), 4))
    return out


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    with st.sidebar:
        st.header("DB")
        db_dir = st.text_input("DB directory", value=str(DEFAULT_DB_DIR))
        top = st.slider("Top results", min_value=5, max_value=50, value=20, step=5)
        include_same_author = st.checkbox("作者ランキングに同一作者を含める", value=False)
        include_self = st.checkbox("作品ランキングに基準作品を含める", value=False)
        if st.button("Reload DB"):
            st.cache_data.clear()

    try:
        df = load_db_cached(db_dir)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    sources = ["All"] + sorted([s for s in df["source"].map(normalize_text).unique().tolist() if s])
    c1, c2, c3 = st.columns(3)
    c1.metric("Works", len(df))
    c2.metric("Authors", df["author"].replace("", pd.NA).dropna().nunique())
    c3.metric("Sources", max(0, len(sources) - 1))

    st.subheader("Select target work")
    q_col, s_col = st.columns([3, 1])
    query = q_col.text_input("Search title / author / Gutenberg ID / doc_id", value="")
    source = s_col.selectbox("Source", sources, index=0)

    catalog = filter_catalog(df, query, source)
    if catalog.empty:
        st.warning("該当作品がありません。")
        st.stop()

    catalog_view = catalog[["doc_id", "gutenberg_id", "author", "title", "source", "status"]].copy()
    st.dataframe(catalog_view.head(200), use_container_width=True, hide_index=True)

    options = catalog["label"].tolist()
    selected_label = st.selectbox("Target", options=options, index=0)
    selected_doc_id = catalog.loc[catalog["label"] == selected_label, "doc_id"].iloc[0]
    target = df[df["doc_id"] == selected_doc_id].iloc[0]

    st.markdown("---")
    st.subheader("Target")
    st.write(f"**{target.get('title','')}**")
    st.write(f"Author: {target.get('author','')}  |  doc_id: `{target.get('doc_id','')}`  |  Gutenberg ID: `{target.get('gutenberg_id','')}`")
    if normalize_text(target.get("source_url", "")):
        st.write(target.get("source_url", ""))

    if st.button("Search similar works / authors", type="primary"):
        work_df = work_similarity(df, selected_doc_id, top=top, include_self=include_self)
        author_df = author_similarity(df, selected_doc_id, top=top, include_same_author=include_same_author)

        left, right = st.columns([3, 2])
        with left:
            st.subheader("Similar works")
            st.dataframe(
                format_similarity(work_df[["rank", "similarity", "doc_id", "gutenberg_id", "author", "title", "source"]]),
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                "Download similar works CSV",
                data=work_df.to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"{selected_doc_id}_similar_works.csv",
                mime="text/csv",
            )
        with right:
            st.subheader("Similar authors")
            st.dataframe(
                format_similarity(author_df[["rank", "similarity", "author", "works_count", "sample_titles"]]),
                use_container_width=True,
                hide_index=True,
            )
            st.download_button(
                "Download similar authors CSV",
                data=author_df.to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"{selected_doc_id}_similar_authors.csv",
                mime="text/csv",
            )

    with st.expander("DB columns"):
        st.write(df.drop(columns=["_embedding_vec"], errors="ignore").columns.tolist())


if __name__ == "__main__":
    main()
