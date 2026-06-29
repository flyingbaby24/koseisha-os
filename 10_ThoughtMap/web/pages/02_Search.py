from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import streamlit as st

from storage import load_official_db


APP_TITLE = "ThoughtMap Similarity Search"
BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_DB_DIR = BASE_DIR / "data" / "thoughtmap_db" / "official"
FALLBACK_DB_DIR = BASE_DIR / "master"


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


def resolve_db_dir(db_dir_text: str) -> Path:
    db_dir = Path(db_dir_text)

    if db_dir.is_absolute() and db_dir.exists():
        return db_dir

    repo_path = BASE_DIR / db_dir
    if repo_path.exists():
        return repo_path

    if DEFAULT_DB_DIR.exists():
        return DEFAULT_DB_DIR

    if FALLBACK_DB_DIR.exists():
        return FALLBACK_DB_DIR

    return repo_path


@st.cache_data(show_spinner=False)
def load_db_cached(db_dir_text: str) -> pd.DataFrame:
    db_dir = resolve_db_dir(db_dir_text)
    docs, embs, _map_points = load_official_db(db_dir)

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

    for col in ["author", "title", "source", "gutenberg_id", "source_url", "status", "category", "subcategory"]:
        if col not in df.columns:
            df[col] = ""

    df["category"] = df["category"].map(lambda x: normalize_text(x) or "unknown")

    df["label"] = df.apply(
        lambda r: f"{r.get('title', '')} — {r.get('author', '')} [{r.get('doc_id', '')}]",
        axis=1,
    )

    return df.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_uploaded_embeddings(uploaded_file) -> pd.DataFrame:
    up = pd.read_csv(uploaded_file, dtype=str).fillna("")

    if "embedding" not in up.columns:
        raise ValueError("アップロードCSVに embedding 列がありません。")

    for col in ["doc_id", "author", "title", "source", "gutenberg_id", "source_url", "status", "category", "subcategory"]:
        if col not in up.columns:
            up[col] = ""

    if up["doc_id"].map(normalize_text).eq("").all():
        for alt in ["document_id", "id", "file_id"]:
            if alt in up.columns:
                up["doc_id"] = up[alt]
                break

    if up["title"].map(normalize_text).eq("").all():
        for alt in ["filename", "name", "work_title"]:
            if alt in up.columns:
                up["title"] = up[alt]
                break

    up["_embedding_vec"] = up["embedding"].map(parse_embedding)
    up = up[up["_embedding_vec"].notna()].copy()

    if up.empty:
        raise ValueError("アップロードCSV内に有効な embedding がありません。")

    up["_dim"] = up["_embedding_vec"].map(lambda x: len(x) if x is not None else 0)
    common_dim = int(up["_dim"].value_counts().idxmax())
    up = up[up["_dim"] == common_dim].copy()

    up["_row_id"] = [f"upload_{i:06d}" for i in range(len(up))]
    up["label"] = up.apply(
        lambda r: (
            f"{normalize_text(r.get('title', '')) or normalize_text(r.get('doc_id', '')) or r.get('_row_id', '')}"
            f" — {normalize_text(r.get('author', ''))} [{r.get('_row_id', '')}]"
        ),
        axis=1,
    )

    return up.reset_index(drop=True)


def filter_catalog(df: pd.DataFrame, query: str, source: str, category: str = "All") -> pd.DataFrame:
    out = df.copy()

    if source and source != "All" and "source" in out.columns:
        out = out[out["source"].map(normalize_text) == source]

    if category and category != "All" and "category" in out.columns:
        out = out[out["category"].map(normalize_text) == category]

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


def render_results(
    df: pd.DataFrame,
    target_title: str,
    target_author: str,
    target_doc_id: str,
    target_gutenberg_id: str,
    target_source_url: str,
    target_vec: np.ndarray,
    top: int,
    include_self: bool,
    include_same_author: bool,
    source_label: str,
    button_key: str,
    target_category: str = "",
    target_subcategory: str = "",
) -> None:
    st.markdown("---")
    st.subheader("Target")
    st.write(f"**{target_title}**")
    st.write(
        f"Author: {target_author}  |  "
        f"doc_id: `{target_doc_id}`  |  "
        f"Gutenberg ID: `{target_gutenberg_id}`"
    )

    if normalize_text(target_source_url):
        st.write(target_source_url)

    target_embedding_csv = make_embedding_download_csv(
        title=target_title,
        author=target_author,
        doc_id=target_doc_id,
        gutenberg_id=target_gutenberg_id,
        source=source_label,
        source_url=target_source_url,
        embedding=vector_to_json(target_vec),
        category=target_category,
        subcategory=target_subcategory,
    )
    st.download_button(
        "Download target embedding CSV",
        data=target_embedding_csv,
        file_name=f"{safe_filename(target_doc_id or target_title)}_embedding.csv",
        mime="text/csv",
        key=f"{button_key}_target_embedding_download",
    )

    if not st.button("Search similar works / authors", type="primary", key=button_key):
        return

    work_df = work_similarity_by_vector(
        df,
        target_vec=target_vec,
        top=top,
        exclude_doc_id=target_doc_id if source_label == "DB" else "",
        include_self=include_self,
    )
    author_df = author_similarity_by_vector(
        df,
        target_vec=target_vec,
        target_author=target_author,
        top=top,
        include_same_author=include_same_author,
    )

    left, right = st.columns([3, 2])

    with left:
        st.subheader("Similar works")
        if work_df.empty:
            st.info("No similar works found.")
        else:
            view_cols = ["rank", "similarity", "doc_id", "gutenberg_id", "author", "title", "source", "category"]
            view_cols = [c for c in view_cols if c in work_df.columns]
            view = format_similarity(work_df[view_cols])
            st.dataframe(view, use_container_width=True, hide_index=True)
            st.download_button(
                "Download similar works CSV",
                data=work_df.to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"{safe_filename(target_doc_id or 'uploaded')}_similar_works.csv",
                mime="text/csv",
                key=f"{button_key}_works_download",
            )

            embedding_cols = [
                "doc_id", "author", "title", "source", "category", "subcategory", "gutenberg_id",
                "source_url", "model_name", "embedding",
            ]
            available_cols = [c for c in embedding_cols if c in work_df.columns]
            st.download_button(
                "Download Top works embeddings CSV",
                data=work_df[available_cols].to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"{safe_filename(target_doc_id or 'uploaded')}_top_work_embeddings.csv",
                mime="text/csv",
                key=f"{button_key}_top_work_embeddings_download",
            )

            work_options = [
                f"{r.rank}. {r.title} — {r.author} [{r.doc_id}]"
                for r in work_df.itertuples(index=False)
            ]
            selected_work = st.selectbox(
                "Download one work embedding",
                options=work_options,
                key=f"{button_key}_selected_work_embedding",
            )
            selected_index = work_options.index(selected_work)
            selected_row = work_df.iloc[selected_index]
            st.download_button(
                "Download selected work embedding CSV",
                data=make_embedding_download_csv(
                    title=selected_row.get("title", ""),
                    author=selected_row.get("author", ""),
                    doc_id=selected_row.get("doc_id", ""),
                    gutenberg_id=selected_row.get("gutenberg_id", ""),
                    source=selected_row.get("source", ""),
                    source_url=selected_row.get("source_url", ""),
                    embedding=selected_row.get("embedding", ""),
                    category=selected_row.get("category", ""),
                    subcategory=selected_row.get("subcategory", ""),
                ),
                file_name=f"{safe_filename(selected_row.get('doc_id', '') or selected_row.get('title', ''))}_embedding.csv",
                mime="text/csv",
                key=f"{button_key}_selected_work_embedding_download",
            )

    with right:
        st.subheader("Similar authors")
        if author_df.empty:
            st.info("No similar authors found.")
        else:
            view = format_similarity(
                author_df[["rank", "similarity", "author", "works_count", "sample_titles"]]
            )
            st.dataframe(view, use_container_width=True, hide_index=True)
            st.download_button(
                "Download similar authors CSV",
                data=author_df.to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"{safe_filename(target_doc_id or 'uploaded')}_similar_authors.csv",
                mime="text/csv",
                key=f"{button_key}_authors_download",
            )

            author_embedding_cols = ["author", "works_count", "source", "embedding"]
            available_author_cols = [c for c in author_embedding_cols if c in author_df.columns]
            st.download_button(
                "Download Top author embeddings CSV",
                data=author_df[available_author_cols].to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"{safe_filename(target_doc_id or 'uploaded')}_top_author_embeddings.csv",
                mime="text/csv",
                key=f"{button_key}_top_author_embeddings_download",
            )

            author_options = [
                f"{r.rank}. {r.author} ({r.works_count} works)"
                for r in author_df.itertuples(index=False)
            ]
            selected_author = st.selectbox(
                "Download one author embedding",
                options=author_options,
                key=f"{button_key}_selected_author_embedding",
            )
            selected_author_index = author_options.index(selected_author)
            selected_author_row = author_df.iloc[selected_author_index]
            st.download_button(
                "Download selected author embedding CSV",
                data=make_embedding_download_csv(
                    title=f"{selected_author_row.get('author', '')} author average",
                    author=selected_author_row.get("author", ""),
                    doc_id=f"author_average:{selected_author_row.get('author', '')}",
                    gutenberg_id="",
                    source="author_average",
                    source_url="",
                    embedding=selected_author_row.get("embedding", ""),
                ),
                file_name=f"{safe_filename(selected_author_row.get('author', 'author'))}_author_average_embedding.csv",
                mime="text/csv",
                key=f"{button_key}_selected_author_embedding_download",
            )


def render_db_work_mode(
    df: pd.DataFrame,
    sources: list[str],
    categories: list[str],
    top: int,
    include_self: bool,
    include_same_author: bool,
) -> None:
    st.subheader("Select target work")

    q_col, s_col, cat_col = st.columns([3, 1, 1])
    query = q_col.text_input("Search title / author / Gutenberg ID / doc_id", value="")
    source = s_col.selectbox("Source", sources, index=0)
    category = cat_col.selectbox("Category", categories, index=0)

    catalog = filter_catalog(df, query, source, category)
    if catalog.empty:
        st.warning("該当作品がありません。")
        st.stop()

    view_cols = ["doc_id", "gutenberg_id", "author", "title", "source", "category", "status"]
    view_cols = [c for c in view_cols if c in catalog.columns]
    catalog_view = catalog[view_cols].copy()
    st.dataframe(catalog_view.head(200), use_container_width=True, hide_index=True)

    selected_label = st.selectbox("Target", options=catalog["label"].tolist(), index=0)
    selected_doc_id = catalog.loc[catalog["label"] == selected_label, "doc_id"].iloc[0]
    target = df[df["doc_id"] == selected_doc_id].iloc[0]

    render_results(
        df=df,
        target_title=target.get("title", ""),
        target_author=target.get("author", ""),
        target_doc_id=target.get("doc_id", ""),
        target_gutenberg_id=target.get("gutenberg_id", ""),
        target_source_url=target.get("source_url", ""),
        target_vec=target["_embedding_vec"],
        target_category=target.get("category", ""),
        target_subcategory=target.get("subcategory", ""),
        top=top,
        include_self=include_self,
        include_same_author=include_same_author,
        source_label="DB",
        button_key="db_search",
    )


def render_upload_mode(
    df: pd.DataFrame,
    categories: list[str],
    top: int,
    include_same_author: bool,
) -> None:
    st.subheader("Upload embeddings CSV")
    st.caption(
        "既存ThoughtMapの Export > Download document embeddings CSV をアップロードして、"
        "DB登録せずに近い作品・作者を検索します。"
    )

    uploaded = st.file_uploader("Embedding CSV", type=["csv"])
    if uploaded is None:
        st.info("embedding列を含むCSVをアップロードしてください。")
        st.stop()

    try:
        upload_df = load_uploaded_embeddings(uploaded)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    db_dim = int(df["_dim"].value_counts().idxmax())
    upload_df = upload_df[upload_df["_dim"] == db_dim].copy()

    if upload_df.empty:
        st.error(f"DB側のembedding次元({db_dim})と一致する行がありません。")
        st.stop()

    c1, c2 = st.columns(2)
    c1.metric("Uploaded works", len(upload_df))
    c2.metric("Embedding dim", db_dim)

    compare_category = st.selectbox("Compare against category", categories, index=0)
    compare_df = filter_catalog(df, "", "All", compare_category)
    if compare_df.empty:
        st.warning("比較対象カテゴリに作品がありません。")
        st.stop()

    query = st.text_input("Filter uploaded title / author / doc_id", value="")
    filtered = filter_catalog(upload_df, query, "All", "All")

    if filtered.empty:
        st.warning("該当作品がありません。")
        st.stop()

    view_cols = ["_row_id", "doc_id", "author", "title", "source"]
    st.dataframe(filtered[view_cols].head(200), use_container_width=True, hide_index=True)

    upload_mode = st.radio(
        "Uploaded search type",
        ["Single uploaded work", "Uploaded personality average"],
        horizontal=True,
    )

    if upload_mode == "Uploaded personality average":
        avg_vec = normalized_average_vector(upload_df["_embedding_vec"].to_list())

        render_results(
            df=compare_df,
            target_title=f"Uploaded personality average ({len(upload_df)} works)",
            target_author="Uploaded CSV",
            target_doc_id="uploaded_personality_average",
            target_gutenberg_id="",
            target_source_url="",
            target_vec=avg_vec,
            target_category=compare_category if compare_category != "All" else "",
            target_subcategory="",
            top=top,
            include_self=False,
            include_same_author=include_same_author,
            source_label="Upload",
            button_key="upload_average_search",
        )
        return

    selected_label = st.selectbox(
        "Uploaded target",
        options=filtered["label"].tolist(),
        index=0,
    )
    target = filtered.loc[filtered["label"] == selected_label].iloc[0]

    render_results(
        df=compare_df,
        target_title=target.get("title", ""),
        target_author=target.get("author", ""),
        target_doc_id=target.get("doc_id", "") or target.get("_row_id", ""),
        target_gutenberg_id=target.get("gutenberg_id", ""),
        target_source_url=target.get("source_url", ""),
        target_vec=target["_embedding_vec"],
        target_category=target.get("category", ""),
        target_subcategory=target.get("subcategory", ""),
        top=top,
        include_self=False,
        include_same_author=include_same_author,
        source_label="Upload",
        button_key="upload_single_search",
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    with st.sidebar:
        st.header("DB")
        db_dir = str(DEFAULT_DB_DIR)
        st.caption(f"DB: {DEFAULT_DB_DIR.name}")

        top = st.slider("Top results", min_value=5, max_value=50, value=20, step=5)
        include_same_author = st.checkbox(
            "Include the same author in the author ranking",
            value=False,
        )
        include_self = st.checkbox(
            "Include benchmark works in the work rankings",
            value=False,
        )

        if st.button("Reload DB"):
            st.cache_data.clear()

    try:
        df = load_db_cached(db_dir)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    sources = ["All"] + sorted(
        [s for s in df["source"].map(normalize_text).unique().tolist() if s]
    )
    categories = ["All"] + sorted(
        [c for c in df["category"].map(normalize_text).unique().tolist() if c]
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Works", len(df))
    c2.metric("Authors", df["author"].replace("", pd.NA).dropna().nunique())
    c3.metric("Sources", max(0, len(sources) - 1))

    mode = st.radio(
        "Search mode",
        ["DB work", "Upload embeddings CSV"],
        horizontal=True,
    )

    if mode == "DB work":
        render_db_work_mode(
            df=df,
            sources=sources,
            categories=categories,
            top=top,
            include_self=include_self,
            include_same_author=include_same_author,
        )
    else:
        render_upload_mode(
            df=df,
            categories=categories,
            top=top,
            include_same_author=include_same_author,
        )

    with st.expander("DB columns"):
        st.write(df.drop(columns=["_embedding_vec"], errors="ignore").columns.tolist())


if __name__ == "__main__":
    main()
