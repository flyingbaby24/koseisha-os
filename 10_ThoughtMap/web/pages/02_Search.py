<<<<<<< HEAD
from __future__ import annotations

import json
import hashlib
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

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
    normalized_average_vector,
    work_similarity_by_vector,
    author_similarity_by_vector,
    format_similarity,
)
from storage import load_official_db, resolve_db_dir


APP_TITLE = "ThoughtMap Similarity Search"
BASE_DIR = Path(__file__).resolve().parents[2]

DEFAULT_DB_DIR = BASE_DIR / "data" / "thoughtmap_db" / "official"
FALLBACK_DB_DIR = BASE_DIR / "master"
USER_DATA_DIR = BASE_DIR / "web" / "user_data"
USER_ID_LENGTH = 16
DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
SEARCH_MODES = ["semantic", "keyword", "hybrid"]
DEFAULT_FILTERS = ["general", "basic_thought", "basic_literature", "jinn_os"]


def normalize_registered_email(email: str) -> str:
    return str(email or "").strip().lower()


def make_user_id_from_email(email: str) -> str:
    normalized = normalize_registered_email(email)
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:USER_ID_LENGTH]


def user_embedding_path(user_id: str) -> Path:
    safe_user_id = re.sub(r"[^a-f0-9]", "", str(user_id or "").lower())[:USER_ID_LENGTH]
    return USER_DATA_DIR / safe_user_id / "thoughtmap_embeddings.csv"


def normalize_api_base_url(value: str) -> str:
    text = str(value or "").strip().rstrip("/")
    return text or DEFAULT_API_BASE_URL


def build_search_api_url(
    api_base_url: str,
    query: str,
    top: int,
    mode: str,
    source: str,
    filter_name: str,
) -> str:
    base_url = normalize_api_base_url(api_base_url)
    params = {
        "q": query,
        "top": int(top),
        "mode": mode,
    }
    if source and source != "all":
        params["source"] = source
    if filter_name and filter_name != "none":
        params["filter"] = filter_name

    return f"{base_url}/search?{urlencode(params)}"


def call_search_api(
    api_base_url: str,
    query: str,
    top: int,
    mode: str,
    source: str,
    filter_name: str,
) -> dict:
    base_url = normalize_api_base_url(api_base_url)
    url = build_search_api_url(api_base_url, query, top, mode, source, filter_name)
    request = Request(url, headers={"Accept": "application/json"})
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=30) as response:
            status_code = getattr(response, "status", 200)
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"FastAPI returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not connect to FastAPI at {base_url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"FastAPI request timed out: {base_url}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"FastAPI returned non-JSON response: {raw[:500]}") from exc

    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return {
        "payload": payload,
        "request_url": url,
        "status_code": status_code,
        "response_time_ms": elapsed_ms,
    }


def parameters_to_frame(parameters: list[dict] | None) -> pd.DataFrame:
    rows = []
    for item in parameters or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key", "") or "")
        if not key:
            continue
        value = pd.to_numeric(item.get("value", 0.0), errors="coerce")
        rows.append({"parameter": key, "value": 0.0 if pd.isna(value) else float(value)})
    return pd.DataFrame(rows)


def results_to_frame(results: list[dict] | None) -> pd.DataFrame:
    rows = []
    for result in results or []:
        if not isinstance(result, dict):
            continue
        rows.append(
            {
                "doc_id": result.get("doc_id", ""),
                "title": result.get("title", ""),
                "author": result.get("author", ""),
                "source": result.get("source", ""),
                "similarity": result.get("similarity", 0.0),
                "url": result.get("url", ""),
                "parameter_count": len(result.get("parameters") or []),
            }
        )
    return pd.DataFrame(rows)


def author_summary_from_results(results: list[dict] | None) -> pd.DataFrame:
    frame = results_to_frame(results)
    if frame.empty or "author" not in frame.columns:
        return pd.DataFrame()

    frame["author"] = frame["author"].fillna("").astype(str)
    frame = frame[frame["author"].str.strip() != ""]
    if frame.empty:
        return pd.DataFrame()

    summary = (
        frame.groupby("author", dropna=False)
        .agg(
            works_count=("doc_id", "count"),
            best_similarity=("similarity", "max"),
            sources=("source", lambda x: ", ".join(sorted({str(v) for v in x if str(v)}))),
            sample_titles=("title", lambda x: " / ".join([str(v) for v in list(x)[:3] if str(v)])),
        )
        .reset_index()
        .sort_values(["best_similarity", "works_count", "author"], ascending=[False, False, True])
    )
    summary.insert(0, "rank", range(1, len(summary) + 1))
    summary["best_similarity"] = summary["best_similarity"].map(lambda x: round(float(x or 0), 4))
    return summary


def render_parameter_profile(title: str, parameters: list[dict] | None) -> None:
    st.markdown(f"#### {title}")
    frame = parameters_to_frame(parameters)
    if frame.empty:
        st.info("Parameter scores are not available in this response.")
        return

    frame["rank"] = frame["value"].map(format_parameter_rank)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    render_radar_chart(frame, title)


def format_parameter_rank(value: float) -> str:
    if value >= 40:
        return "S"
    if value >= 30:
        return "A"
    if value >= 20:
        return "B"
    if value >= 10:
        return "C"
    return "D"


def render_radar_chart(frame: pd.DataFrame, title: str) -> None:
    if frame is None or frame.empty or not {"parameter", "value"}.issubset(frame.columns):
        st.caption("Radar chart has no valid parameter data.")
        return

    frame = frame.copy()
    frame["parameter"] = frame["parameter"].fillna("").astype(str)
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce").fillna(0.0)
    frame = frame[frame["parameter"].str.strip() != ""]

    if len(frame) < 3:
        st.caption("Radar chart needs at least 3 parameters.")
        return

    try:
        import matplotlib.pyplot as plt
    except Exception:
        st.caption("matplotlib is not available; showing the parameter table only.")
        return

    labels = frame["parameter"].astype(str).tolist()
    values = frame["value"].astype(float).clip(lower=0, upper=40).tolist()
    values += values[:1]

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig = plt.figure(figsize=(4.8, 4.8))
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.22)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 40)
    ax.set_title(title)
    ax.grid(True, alpha=0.35)
    st.pyplot(fig, use_container_width=True)


def select_result_from_table(display: pd.DataFrame, results: list[dict]) -> dict | None:
    if display.empty or not results:
        return None

    selected_index = 0
    try:
        event = st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key="api_similar_works_table",
        )
        selection = getattr(event, "selection", None)
        if isinstance(selection, dict):
            rows = selection.get("rows", [])
        else:
            rows = getattr(selection, "rows", []) if selection else []
        if rows:
            selected_index = int(rows[0])
    except TypeError:
        st.dataframe(display, use_container_width=True, hide_index=True)
        options = [
            f"{i + 1}. {r.get('title', 'Untitled')} - {r.get('author', '')} [{r.get('doc_id', '')}]"
            for i, r in enumerate(results)
        ]
        selected = st.selectbox("Selected result", options, key="api_selected_result_fallback")
        selected_index = options.index(selected)

    selected_index = max(0, min(selected_index, len(results) - 1))
    return results[selected_index]


def render_selected_result_detail(selected_result: dict | None) -> None:
    st.subheader("Selected work detail")
    if not selected_result:
        st.info("Select a row from Similar works to inspect it.")
        return

    meta_left, meta_right = st.columns([2, 1])
    with meta_left:
        st.markdown(f"### {selected_result.get('title', 'Untitled') or 'Untitled'}")
        st.write(f"Author: {selected_result.get('author', '') or 'Unknown'}")
        st.write(f"Source: `{selected_result.get('source', '')}`")
        st.write(f"doc_id: `{selected_result.get('doc_id', '')}`")
        if selected_result.get("url"):
            st.markdown(f"[Open source]({selected_result['url']})")
    with meta_right:
        st.metric("Similarity", f"{float(selected_result.get('similarity', 0.0) or 0.0):.4f}")
        st.metric("Parameters", len(selected_result.get("parameters") or []))


def render_debug_expander(meta: dict, payload: dict, error: str = "") -> None:
    with st.expander("Debug: API request / response", expanded=False):
        st.write(f"Request URL: `{meta.get('request_url', '')}`")
        st.write(f"Status code: `{meta.get('status_code', 'n/a')}`")
        st.write(f"Response time: `{meta.get('response_time_ms', 'n/a')}` ms")
        if error:
            st.error(error)
        if payload:
            st.download_button(
                "Download API response JSON",
                data=json.dumps(payload, ensure_ascii=False, indent=2),
                file_name="thoughtmap_search_response.json",
                mime="application/json",
                key="api_response_json_download",
            )
        else:
            st.caption("No response JSON is available to download.")
        with st.expander("Raw JSON", expanded=False):
            st.json(payload or {})


def render_api_search_mode() -> None:
    st.caption("FastAPI /search is the source of truth. Streamlit is acting as an API client and review console.")

    with st.sidebar:
        st.header("FastAPI")
        api_base_url = st.text_input("API Base URL", value=DEFAULT_API_BASE_URL)
        top = st.slider("Top results", min_value=1, max_value=50, value=10, step=1)
        mode = st.selectbox("Search mode", SEARCH_MODES, index=0)
        source = st.text_input("Source filter", value="", placeholder="all / gutendex / user_suno")
        filter_name = st.selectbox("Parameter filter", DEFAULT_FILTERS, index=0)

        if st.button("Clear API cache"):
            st.cache_data.clear()

    query = st.text_input("Search query", value="Plato", placeholder="Search title, author, concept, source...")
    submitted = st.button("Search FastAPI", type="primary")

    if not submitted and "api_search_payload" not in st.session_state:
        st.info("Enter a query and call FastAPI. Example: Plato / keyword / gutendex / general.")
        return

    if submitted:
        if not query.strip():
            st.warning("Please enter a search query.")
            return
        try:
            with st.spinner("Calling FastAPI /search..."):
                api_response = call_search_api(
                    api_base_url=api_base_url,
                    query=query,
                    top=top,
                    mode=mode,
                    source=normalize_text(source).lower(),
                    filter_name=filter_name,
                )
                st.session_state["api_search_payload"] = api_response.get("payload", {})
                st.session_state["api_search_meta"] = {
                    "request_url": api_response.get("request_url", ""),
                    "status_code": api_response.get("status_code", ""),
                    "response_time_ms": api_response.get("response_time_ms", ""),
                }
                st.session_state["api_search_error"] = ""
        except Exception as exc:
            error_text = str(exc)
            status_match = re.search(r"HTTP\s+(\d+)", error_text)
            st.session_state["api_search_payload"] = {}
            st.session_state["api_search_meta"] = {
                "request_url": build_search_api_url(
                    api_base_url=api_base_url,
                    query=query,
                    top=top,
                    mode=mode,
                    source=normalize_text(source).lower(),
                    filter_name=filter_name,
                ),
                "status_code": status_match.group(1) if status_match else "error",
                "response_time_ms": "n/a",
            }
            st.session_state["api_search_error"] = error_text
            st.error(error_text)
            render_debug_expander(
                st.session_state["api_search_meta"],
                st.session_state["api_search_payload"],
                st.session_state["api_search_error"],
            )
            return

    payload = st.session_state.get("api_search_payload", {})
    meta = st.session_state.get("api_search_meta", {})
    error = st.session_state.get("api_search_error", "")
    results = payload.get("results", [])
    result_frame = results_to_frame(results)

    if error:
        st.error(error)
        render_debug_expander(meta, payload, error)
        return

    st.success(f"FastAPI response received: {len(results)} result(s)")
    render_debug_expander(meta, payload)

    st.subheader("Similar works")
    selected_result = None
    if result_frame.empty:
        st.info("No results.")
    else:
        display = result_frame.copy()
        if "similarity" in display.columns:
            display["similarity"] = display["similarity"].map(lambda x: round(float(x or 0), 4))
        selected_result = select_result_from_table(display, results)
        st.download_button(
            "Download result table CSV",
            data=result_frame.to_csv(index=False, encoding="utf-8-sig"),
            file_name="thoughtmap_search_results.csv",
            mime="text/csv",
        )

    render_selected_result_detail(selected_result)

    st.subheader("Profiles")
    left, right = st.columns(2)
    with left:
        render_parameter_profile("Query Profile", payload.get("query_parameters"))
    with right:
        render_parameter_profile(
            "Selected Profile",
            selected_result.get("parameters") if selected_result else None,
        )

    st.subheader("Similar authors")
    author_frame = author_summary_from_results(results)
    if author_frame.empty:
        st.info("No author summary is available from the current API results.")
    else:
        st.caption("Grouped from the current /search response only. No separate CSV search is performed.")
        st.dataframe(author_frame, use_container_width=True, hide_index=True)
        chart_frame = author_frame.set_index("author")[["best_similarity"]]
        st.bar_chart(chart_frame, use_container_width=True)


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


@st.cache_data(show_spinner=False)
def load_saved_user_embeddings(path_text: str) -> pd.DataFrame:
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError(f"Saved user embeddings CSV was not found: {path}")

    saved = pd.read_csv(path, dtype=str).fillna("")
    if "embedding" not in saved.columns:
        raise ValueError("Saved thoughtmap_embeddings.csv must contain an embedding column.")

    for col in ["doc_id", "author", "title", "source", "gutenberg_id", "source_url", "status", "category", "subcategory"]:
        if col not in saved.columns:
            saved[col] = ""

    if saved["doc_id"].map(normalize_text).eq("").all():
        saved["doc_id"] = [f"user_saved_{i:06d}" for i in range(len(saved))]

    if saved["title"].map(normalize_text).eq("").all():
        saved["title"] = saved["doc_id"]

    saved["_embedding_vec"] = saved["embedding"].map(parse_embedding)
    saved = saved[saved["_embedding_vec"].notna()].copy()
    if saved.empty:
        raise ValueError("Saved thoughtmap_embeddings.csv has no valid embedding rows.")

    saved["_dim"] = saved["_embedding_vec"].map(lambda x: len(x) if x is not None else 0)
    common_dim = int(saved["_dim"].value_counts().idxmax())
    saved = saved[saved["_dim"] == common_dim].copy()
    saved["label"] = saved.apply(
        lambda r: (
            f"{normalize_text(r.get('title', '')) or normalize_text(r.get('doc_id', ''))}"
            f" - {normalize_text(r.get('author', ''))} [{r.get('doc_id', '')}]"
        ),
        axis=1,
    )
    return saved.reset_index(drop=True)


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
=======
import json
import time
import urllib.parse
import urllib.request

import pandas as pd
import streamlit as st


st.set_page_config(page_title="ThoughtMap Search", layout="wide")
st.title("ThoughtMap Similarity Search")
st.caption("FastAPI /search is the source of truth. Streamlit is an API client.")


def call_search(api_base_url: str, q: str, top: int, mode: str, source: str, filter_name: str):
    params = {
        "q": q,
        "top": top,
        "mode": mode,
        "filter": filter_name,
    }
    if source and source != "all":
        params["source"] = source

    url = api_base_url.rstrip("/") + "/search?" + urllib.parse.urlencode(params)
    start = time.time()

    with urllib.request.urlopen(url, timeout=30) as response:
        body = response.read().decode("utf-8")
        elapsed = time.time() - start
        return url, response.status, elapsed, json.loads(body)


with st.sidebar:
    st.header("FastAPI")
    api_base_url = st.text_input("API Base URL", value="https://koseisha-os.onrender.com")
    top = st.slider("Top results", 1, 50, 10)
    mode = st.selectbox("Search mode", ["semantic", "keyword", "hybrid"])
    source = st.text_input("Source filter", value="all")
    filter_name = st.selectbox("Parameter filter", ["general"])
    show_debug = st.checkbox("Show debug", value=False)

q = st.text_input("Search query", value="Plato")
>>>>>>> 47c2ea85f4138e95a2cd1adbbd12bf1eaac2475b

if st.button("Search FastAPI"):
    try:
        request_url, status_code, elapsed, data = call_search(
            api_base_url, q, top, mode, source, filter_name
        )

        results = data.get("results", [])
        st.success(f"FastAPI response received: {len(results)} result(s)")

        if results:
            rows = []
            for item in results:
                rows.append({
                    "doc_id": item.get("doc_id", ""),
                    "title": item.get("title", ""),
                    "author": item.get("author", ""),
                    "source": item.get("source", ""),
                    "similarity": item.get("similarity", item.get("score", "")),
                    "url": item.get("url", ""),
                    "parameter_count": len(item.get("parameters", []) or []),
                })

            df = pd.DataFrame(rows)
            st.subheader("Similar works")
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.download_button(
                "Download results CSV",
                df.to_csv(index=False).encode("utf-8-sig"),
                file_name="thoughtmap_search_results.csv",
                mime="text/csv",
            )

            st.subheader("Similar authors")
            author_df = (
                df[df["author"] != ""]
                .groupby("author", as_index=False)
                .agg(count=("doc_id", "count"), max_similarity=("similarity", "max"))
                .sort_values(["count", "max_similarity"], ascending=False)
            )
            st.dataframe(author_df, use_container_width=True, hide_index=True)

        else:
            st.info("No results.")

        with st.expander("Debug: API request / response", expanded=show_debug):
            st.write("Request URL:", request_url)
            st.write("Status code:", status_code)
            st.write("Response time:", f"{elapsed:.3f}s")
            st.json(data)
            st.download_button(
                "Download API response JSON",
                json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name="thoughtmap_api_response.json",
                mime="application/json",
            )

    except Exception as exc:
<<<<<<< HEAD
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


def render_saved_user_embeddings_mode(
    df: pd.DataFrame,
    categories: list[str],
    top: int,
    include_same_author: bool,
) -> None:
    st.subheader("Saved user embeddings")
    st.caption(
        "Public mode: load user_data/{user_id}/thoughtmap_embeddings.csv and compare it with the official embedding DB. "
        "No sentence-transformers model is used here."
    )

    email = st.text_input("Registered email", value="", help="Used to derive the same safe user_id/hash as app.py.")
    user_id = make_user_id_from_email(email)
    if not user_id:
        st.info("Enter a registered email to load your saved thoughtmap_embeddings.csv.")
        return

    path = user_embedding_path(user_id)
    st.write(f"user_id: `{user_id}`")
    st.write(f"CSV: `{path}`")

    try:
        user_df = load_saved_user_embeddings(str(path))
    except Exception as exc:
        st.warning(str(exc))
        st.caption("Run Analyze in app.py, enter the same registered email, then save embeddings to the user folder.")
        return

    db_dim = int(df["_dim"].value_counts().idxmax())
    user_df = user_df[user_df["_dim"] == db_dim].copy()
    if user_df.empty:
        st.error(f"Saved embeddings do not match the official DB embedding dimension ({db_dim}).")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Saved works", len(user_df))
    c2.metric("Embedding dim", db_dim)
    c3.metric("User ID", user_id)

    compare_category = st.selectbox("Compare against category", categories, index=0, key="saved_compare_category")
    compare_df = filter_catalog(df, "", "All", compare_category)
    if compare_df.empty:
        st.warning("No official works are available for that comparison category.")
        return

    query = st.text_input("Filter saved title / author / doc_id", value="", key="saved_filter_query")
    filtered = filter_catalog(user_df, query, "All", "All")
    if filtered.empty:
        st.warning("No saved works match that filter.")
        return

    view_cols = ["doc_id", "author", "title", "source", "cluster", "cluster_label"]
    view_cols = [c for c in view_cols if c in filtered.columns]
    st.dataframe(filtered[view_cols].head(200), use_container_width=True, hide_index=True)

    saved_mode = st.radio(
        "Saved search type",
        ["Single saved work", "Saved profile average"],
        horizontal=True,
        key="saved_search_type",
    )

    if saved_mode == "Saved profile average":
        avg_vec = normalized_average_vector(user_df["_embedding_vec"].to_list())
        render_results(
            df=compare_df,
            target_title=f"Saved profile average ({len(user_df)} works)",
            target_author="Saved user embeddings",
            target_doc_id=f"user_average:{user_id}",
            target_gutenberg_id="",
            target_source_url="",
            target_vec=avg_vec,
            target_category=compare_category if compare_category != "All" else "",
            target_subcategory="",
            top=top,
            include_self=False,
            include_same_author=include_same_author,
            source_label="SavedUser",
            button_key="saved_average_search",
        )
        return

    selected_label = st.selectbox(
        "Saved target",
        options=filtered["label"].tolist(),
        index=0,
        key="saved_target",
    )
    target = filtered.loc[filtered["label"] == selected_label].iloc[0]
    render_results(
        df=compare_df,
        target_title=target.get("title", ""),
        target_author=target.get("author", ""),
        target_doc_id=target.get("doc_id", ""),
        target_gutenberg_id=target.get("gutenberg_id", ""),
        target_source_url=target.get("source_url", ""),
        target_vec=target["_embedding_vec"],
        target_category=target.get("category", ""),
        target_subcategory=target.get("subcategory", ""),
        top=top,
        include_self=False,
        include_same_author=include_same_author,
        source_label="SavedUser",
        button_key="saved_single_search",
    )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    search_backend = st.sidebar.radio(
        "Search backend",
        ["FastAPI / shared backend", "Saved user embeddings", "Legacy CSV local mode"],
        index=0,
    )

    if search_backend == "FastAPI / shared backend":
        render_api_search_mode()
        return

    with st.sidebar:
        st.header("Official embedding DB")
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

    if search_backend == "Saved user embeddings":
        render_saved_user_embeddings_mode(
            df=df,
            categories=categories,
            top=top,
            include_same_author=include_same_author,
        )
        return

    st.warning(
        "Legacy CSV local mode is kept for manual CSV workflows only. "
        "Unity and the future shared backend use FastAPI /search as the source of truth."
    )

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
=======
        st.error(f"Could not connect to FastAPI: {exc}")
>>>>>>> 47c2ea85f4138e95a2cd1adbbd12bf1eaac2475b
