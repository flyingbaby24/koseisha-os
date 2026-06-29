from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from search_utils import (
    cosine,
    normalize_key,
    normalize_text,
    parse_embedding,
    safe_filename,
    vector_to_json,
    make_embedding_download_csv,
)
from storage import load_user_db


APP_TITLE = "ThoughtMap Personal Works Search"
BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_USERS_DIR = BASE_DIR / "data" / "thoughtmap_db" / "users"
FALLBACK_USERS_DIR = BASE_DIR / "data" / "users"
FALLBACK_DB_DIR = BASE_DIR / "master"


def resolve_users_dir(users_dir_text: str) -> Path:
    users_dir = Path(users_dir_text)

    if users_dir.is_absolute() and users_dir.exists():
        return users_dir

    repo_path = BASE_DIR / users_dir
    if repo_path.exists():
        return repo_path

    if DEFAULT_USERS_DIR.exists():
        return DEFAULT_USERS_DIR

    if FALLBACK_USERS_DIR.exists():
        return FALLBACK_USERS_DIR

    return repo_path


def list_user_libraries(users_dir: Path) -> pd.DataFrame:
    index_path = users_dir / "index.csv"
    if index_path.exists():
        try:
            idx = pd.read_csv(index_path, dtype=str).fillna("")
            if "user_id" in idx.columns:
                rows = []
                for _, r in idx.iterrows():
                    user_id = normalize_text(r.get("user_id", ""))
                    if not user_id:
                        continue
                    user_dir = users_dir / user_id
                    if user_dir.exists():
                        rows.append({
                            "user_id": user_id,
                            "display_name": normalize_text(r.get("display_name", "")) or user_id,
                            "email_masked": normalize_text(r.get("email_masked", "")),
                            "user_dir": str(user_dir),
                        })
                if rows:
                    return pd.DataFrame(rows)
        except Exception:
            pass

    rows = []
    if users_dir.exists():
        for p in sorted(users_dir.iterdir()):
            if not p.is_dir():
                continue
            profile_path = p / "profile.json"
            display_name = p.name
            email_masked = ""
            if profile_path.exists():
                try:
                    profile = json.loads(profile_path.read_text(encoding="utf-8"))
                    display_name = normalize_text(profile.get("display_name", "")) or display_name
                    email_masked = normalize_text(profile.get("email_masked", ""))
                except Exception:
                    pass
            rows.append({
                "user_id": p.name,
                "display_name": display_name,
                "email_masked": email_masked,
                "user_dir": str(p),
            })
    return pd.DataFrame(rows)


def resolve_user_db_dir(users_dir_text: str, user_id: str) -> Path:
    users_dir = resolve_users_dir(users_dir_text)
    return users_dir / user_id


@st.cache_data(show_spinner=False)
def load_personal_db_cached(users_dir_text: str, user_id: str) -> pd.DataFrame:
    users_dir = resolve_users_dir(users_dir_text)
    docs, embs, _map_points = load_user_db(user_id, users_dir)

    if "doc_id" not in docs.columns or "doc_id" not in embs.columns:
        raise ValueError("documents.csv / embeddings.csv の両方に doc_id 列が必要です。")
    if "embedding" not in embs.columns:
        raise ValueError("embeddings.csv に embedding 列がありません。")

    if "model_name" not in embs.columns:
        if "model" in embs.columns:
            embs["model_name"] = embs["model"]
        else:
            embs["model_name"] = ""

    df = docs.merge(embs[["doc_id", "model_name", "embedding"]], on="doc_id", how="inner")
    df["_embedding_vec"] = df["embedding"].map(parse_embedding)
    df = df[df["_embedding_vec"].notna()].copy()

    if df.empty:
        raise ValueError("有効な embedding がありません。")

    df["_dim"] = df["_embedding_vec"].map(lambda x: len(x) if x is not None else 0)
    common_dim = int(df["_dim"].value_counts().idxmax())
    df = df[df["_dim"] == common_dim].copy()

    for col in [
        "user_id", "author", "title", "source", "source_url", "status",
        "category", "subcategory", "tags", "notes", "text_path",
        "gutenberg_id",
    ]:
        if col not in df.columns:
            df[col] = ""

    # 個人DBでは category が空の場合、tags を category 代わりに使う
    df["category"] = df.apply(
        lambda r: normalize_text(r.get("category", "")) or normalize_text(r.get("tags", "")) or "unknown",
        axis=1,
    )

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
            | out.get("tags", pd.Series("", index=out.index)).map(normalize_key).str.contains(re.escape(q), na=False)
            | out.get("source", pd.Series("", index=out.index)).map(normalize_key).str.contains(re.escape(q), na=False)
            | out.get("source_url", pd.Series("", index=out.index)).map(normalize_key).str.contains(re.escape(q), na=False)
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
        f"External ID: `{target_gutenberg_id}`"
    )

    if normalize_text(target_source_url):
        st.markdown(f"[Open source]({target_source_url})")

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
    st.subheader("Select personal work")

    q_col, s_col, cat_col = st.columns([3, 1, 1])
    query = q_col.text_input("Search title / author / source / tags / doc_id", value="")
    source = s_col.selectbox("Source", sources, index=0)
    category = cat_col.selectbox("Category", categories, index=0)

    catalog = filter_catalog(df, query, source, category)
    if catalog.empty:
        st.warning("該当作品がありません。")
        st.stop()

    view_cols = ["doc_id", "author", "title", "source", "category", "source_url", "status"]
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
        st.header("Personal DB")
        users_dir = str(DEFAULT_USERS_DIR)
        st.caption(f"Users: {DEFAULT_USERS_DIR}")

        top = st.slider("Top results", min_value=5, max_value=50, value=20, step=5)
        include_same_author = st.checkbox(
            "Include the same author in the author ranking",
            value=True,
        )
        include_self = st.checkbox(
            "Include selected work in the work rankings",
            value=False,
        )

        if st.button("Reload Personal DB"):
            st.cache_data.clear()

    users_base = resolve_users_dir(users_dir)
    user_libraries = list_user_libraries(users_base)

    if user_libraries.empty:
        st.error(f"個人ユーザーDBが見つかりません: {users_base}")
        st.info("先に create_user.py と import_thoughtmap_csv.py を実行してください。")
        st.stop()

    user_options = [
        f"{r.display_name}"
        for r in user_libraries.itertuples(index=False)
    ]

    selected_user_label = st.selectbox("Library", options=user_options, index=0)
    selected_user_index = user_options.index(selected_user_label)
    selected_user = user_libraries.iloc[selected_user_index]
    selected_user_id = selected_user["user_id"]

    try:
        df = load_personal_db_cached(users_dir, selected_user_id)
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    sources = ["All"] + sorted(
        [s for s in df["source"].map(normalize_text).unique().tolist() if s]
    )
    categories = ["All"] + sorted(
        [c for c in df["category"].map(normalize_text).unique().tolist() if c]
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Works", len(df))
    c2.metric("Authors", df["author"].replace("", pd.NA).dropna().nunique())
    c3.metric("Sources", max(0, len(sources) - 1))
    c4.metric("Library", normalize_text(selected_user.get("display_name", "")) or selected_user_id)

    mode = st.radio(
        "Search mode",
        ["Personal work", "Upload embeddings CSV"],
        horizontal=True,
    )

    if mode == "Personal work":
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

    with st.expander("Personal DB columns"):
        st.write(df.drop(columns=["_embedding_vec"], errors="ignore").columns.tolist())


if __name__ == "__main__":
    main()
