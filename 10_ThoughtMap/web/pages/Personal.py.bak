from __future__ import annotations

import html
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd
import streamlit as st

APP_TITLE = "ThoughtMap Personal Library"
API_BASE_URL = "https://koseisha-os.onrender.com"

LAST_SEARCH_KEYS = [
    "last_results",
    "last_data",
    "last_elapsed",
    "last_url",
]

DEBUG_KEYS = [
    "last_error",
    "last_error_body",
    "last_debug_url",
]

st.set_page_config(page_title=APP_TITLE, layout="wide")


def inject_custom_css():
    st.markdown(
        """
        <style>
        :root {
            --tm-bg: #050914;
            --tm-panel: rgba(10, 18, 38, 0.78);
            --tm-border: rgba(99, 242, 255, 0.26);
            --tm-cyan: #38e8ff;
            --tm-blue: #6da8ff;
            --tm-violet: #9a7cff;
            --tm-green: #5dffb3;
            --tm-text: #e9f7ff;
            --tm-muted: #91a4c4;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 8%, rgba(56, 232, 255, 0.16), transparent 28%),
                radial-gradient(circle at 86% 0%, rgba(154, 124, 255, 0.14), transparent 26%),
                linear-gradient(135deg, #040712 0%, #081123 48%, #090718 100%);
            color: var(--tm-text);
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(99, 242, 255, 0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(99, 242, 255, 0.04) 1px, transparent 1px);
            background-size: 42px 42px;
            mask-image: linear-gradient(to bottom, rgba(0,0,0,0.8), rgba(0,0,0,0.12));
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 1440px;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(5, 10, 24, 0.98), rgba(10, 18, 38, 0.95)),
                linear-gradient(90deg, rgba(56,232,255,0.13), transparent);
            border-right: 1px solid var(--tm-border);
        }

        [data-testid="stSidebar"] .stButton > button {
            width: 100%;
            border: 1px solid rgba(56, 232, 255, 0.72);
            background: linear-gradient(90deg, #09a8ff, #8f5dff);
            color: white;
            font-weight: 800;
            letter-spacing: 0.06em;
            box-shadow: 0 0 24px rgba(56, 232, 255, 0.28);
        }

        .tm-hero {
            position: relative;
            overflow: hidden;
            padding: 2rem 2.15rem;
            border: 1px solid var(--tm-border);
            border-radius: 18px;
            background:
                linear-gradient(135deg, rgba(12, 23, 52, 0.96), rgba(8, 12, 30, 0.86)),
                radial-gradient(circle at 88% 24%, rgba(56,232,255,0.24), transparent 20%);
            box-shadow: 0 18px 60px rgba(0,0,0,0.34), inset 0 0 50px rgba(56,232,255,0.055);
            margin-bottom: 1rem;
        }

        .tm-kicker {
            color: var(--tm-green);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }

        .tm-hero h1 {
            margin: 0;
            color: var(--tm-text);
            font-size: clamp(2.1rem, 5vw, 4.2rem);
            line-height: 1;
            letter-spacing: 0;
            text-shadow: 0 0 32px rgba(56,232,255,0.42);
        }

        .tm-hero p {
            max-width: 820px;
            color: #bcd3f4;
            margin: 0.85rem 0 0;
            font-size: 1.04rem;
        }

        .tm-chip-row {
            display: flex;
            gap: 0.65rem;
            flex-wrap: wrap;
            margin-top: 1.2rem;
        }

        .tm-chip {
            border: 1px solid rgba(56, 232, 255, 0.36);
            color: #dffbff;
            background: rgba(56, 232, 255, 0.08);
            border-radius: 999px;
            padding: 0.35rem 0.72rem;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .tm-shell, .tm-stat-card, .tm-result-card, .tm-work-card, .tm-detail-card {
            border: 1px solid var(--tm-border);
            border-radius: 14px;
            background: linear-gradient(180deg, rgba(12, 23, 52, 0.92), rgba(7, 12, 28, 0.86));
            box-shadow: 0 14px 44px rgba(0,0,0,0.28), inset 0 0 28px rgba(56,232,255,0.04);
        }

        .tm-shell {
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }

        .tm-title {
            color: var(--tm-green);
            font-size: 0.78rem;
            font-weight: 850;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .tm-desc {
            color: #b7c8e8;
            margin-top: 0.45rem;
        }

        .tm-overview-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.9rem;
            margin-bottom: 1rem;
        }

        .tm-stat-card {
            padding: 1rem;
            min-height: 104px;
        }

        .tm-stat-label {
            color: var(--tm-muted);
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 0.45rem;
        }

        .tm-stat-value {
            color: var(--tm-text);
            font-size: 1.7rem;
            line-height: 1.1;
            font-weight: 850;
            overflow-wrap: anywhere;
        }

        .tm-result-card, .tm-work-card, .tm-detail-card {
            padding: 0.95rem 1rem;
            margin: 0.7rem 0;
        }

        .tm-result-title {
            color: var(--tm-text);
            font-weight: 850;
            font-size: 1rem;
            overflow-wrap: anywhere;
        }

        .tm-result-meta {
            color: var(--tm-cyan);
            font-size: 0.78rem;
            font-weight: 750;
            margin: 0.28rem 0;
        }

        .tm-result-preview {
            color: #b9c7df;
            font-size: 0.9rem;
            line-height: 1.55;
            overflow-wrap: anywhere;
        }

        .stDataFrame, [data-testid="stTable"] {
            border: 1px solid rgba(56,232,255,0.16);
            border-radius: 12px;
            overflow: hidden;
        }

        textarea, input, .stTextInput input {
            border-color: rgba(56,232,255,0.34) !important;
        }

        @media (max-width: 900px) {
            .tm-overview-grid {
                grid-template-columns: 1fr;
            }
            .tm-hero {
                padding: 1.45rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def api_get(path: str, params: dict) -> tuple[dict, float, str]:
    url = API_BASE_URL + path + "?" + urllib.parse.urlencode(params)
    start = time.time()

    with urllib.request.urlopen(url, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data, time.time() - start, url


def load_saved_works(email: str) -> list[dict]:
    data, _elapsed, _url = api_get(
        "/users/by-email/saved",
        {"email": email.strip()},
    )
    return data.get("works", [])


def search_similar(
    email: str,
    target_doc_id: str,
    top: int,
    source: str,
    category: str,
    filter_name: str,
) -> tuple[dict, float, str]:
    params = {
        "mode": "embedding",
        "target_doc_id": target_doc_id,
        "user_email": email.strip(),
        "top": top,
        "filter": filter_name,
    }

    if source and source != "all":
        params["source"] = source

    if category and category != "all":
        params["category"] = category

    return api_get("/search", params)


def make_works_frame(works: list[dict]) -> pd.DataFrame:
    rows = []

    for i, w in enumerate(works):
        rows.append({
            "index": i,
            "title": w.get("title", ""),
            "author": w.get("author", ""),
            "source": w.get("source", ""),
            "category": w.get("category", ""),
            "doc_id": w.get("doc_id", ""),
        })

    return pd.DataFrame(rows)


def make_results_frame(results: list[dict]) -> pd.DataFrame:
    rows = []

    for i, r in enumerate(results):
        rows.append({
            "index": i,
            "title": r.get("title", ""),
            "author": r.get("author", ""),
            "source": r.get("source", ""),
            "similarity": r.get("similarity", r.get("score", 0)),
            "url": r.get("url", ""),
            "doc_id": r.get("doc_id", ""),
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df["similarity"] = pd.to_numeric(df["similarity"], errors="coerce").fillna(0)

    return df


def clear_last_search():
    for key in LAST_SEARCH_KEYS:
        st.session_state.pop(key, None)


def clear_debug():
    for key in DEBUG_KEYS:
        st.session_state.pop(key, None)


def read_http_error_body(exc: Exception) -> str:
    if not isinstance(exc, urllib.error.HTTPError):
        return ""

    try:
        return exc.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def build_search_debug_url(
    email: str,
    target_doc_id: str,
    top: int,
    source: str,
    category: str,
    filter_name: str,
) -> str:
    params = {
        "mode": "embedding",
        "target_doc_id": target_doc_id,
        "user_email": email.strip(),
        "top": top,
        "filter": filter_name,
    }

    if source and source != "all":
        params["source"] = source

    if category and category != "all":
        params["category"] = category

    return API_BASE_URL + "/search?" + urllib.parse.urlencode(params)


inject_custom_css()

st.markdown(
    """
    <section class="tm-hero">
        <div class="tm-kicker">Personal Vector Library</div>
        <h1>ThoughtMap Personal Library</h1>
        <p>Manage saved works, select a target document, and launch embedding similarity search from your private thought archive.</p>
        <div class="tm-chip-row">
            <span class="tm-chip">Saved Works</span>
            <span class="tm-chip">Target Vector</span>
            <span class="tm-chip">Similarity Search</span>
            <span class="tm-chip">FastAPI Debug</span>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown("### Control Deck")
    st.caption("Load your library, tune filters, then search similar works.")

    st.markdown("#### 01 Library")
    email = st.text_input(
        "Registered e-mail",
        placeholder="example@example.com",
        key="library_email",
    )

    reload_clicked = st.button("Reload Library")

    st.markdown("#### 02 Similarity Search")
    top = st.slider("Top results", 1, 50, 10)
    source = st.text_input("Source filter", value="all")
    category = st.text_input("Category filter", value="all")
    filter_name = st.selectbox("Parameter filter", ["general"])


if "saved_works" not in st.session_state:
    st.session_state["saved_works"] = []

if "selected_target_doc_id" not in st.session_state:
    st.session_state["selected_target_doc_id"] = ""

if email.strip() and (reload_clicked or not st.session_state["saved_works"]):
    try:
        works = load_saved_works(email)
        st.session_state["saved_works"] = works
    except Exception as exc:
        st.error(f"Failed to load Personal Library: {exc}")


works = st.session_state.get("saved_works", [])

if not email.strip():
    st.info("Enter your registered e-mail to load your Personal Library.")
    st.stop()

if not works:
    st.warning("No saved works were found for this e-mail.")
    st.stop()


works_df = make_works_frame(works)
works_count = len(works_df)
source_count = works_df["source"].replace("", pd.NA).dropna().nunique()
category_count = works_df["category"].replace("", pd.NA).dropna().nunique()

st.markdown(
    f"""
    <div class="tm-overview-grid">
        <div class="tm-stat-card">
            <div class="tm-stat-label">Works</div>
            <div class="tm-stat-value">{works_count}</div>
        </div>
        <div class="tm-stat-card">
            <div class="tm-stat-label">Sources</div>
            <div class="tm-stat-value">{source_count}</div>
        </div>
        <div class="tm-stat-card">
            <div class="tm-stat-label">Categories</div>
            <div class="tm-stat-value">{category_count}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.35, 1], gap="large")

with left:
    st.markdown(
        """
        <div class="tm-shell">
            <div class="tm-title">Saved Works Browser</div>
            <div class="tm-desc">Filter saved works, then choose one as the target vector for similarity search.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    search_text = st.text_input(
        "Filter saved works",
        placeholder="title / author / source / category",
    )

    filtered_df = works_df.copy()

    if search_text.strip():
        q = search_text.strip().lower()
        mask = (
            filtered_df["title"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["author"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["source"].astype(str).str.lower().str.contains(q, na=False)
            | filtered_df["category"].astype(str).str.lower().str.contains(q, na=False)
        )
        filtered_df = filtered_df[mask].copy()

    if filtered_df.empty:
        st.warning("No matching works.")
        st.stop()

    for _, row in filtered_df.head(8).iterrows():
        title = row.get("title", "") or "Untitled"
        author = row.get("author", "") or "Unknown"
        source_value = row.get("source", "") or "unknown"
        category_value = row.get("category", "") or "uncategorized"
        st.markdown(
            f"""
            <div class="tm-work-card">
                <div class="tm-result-title">{html.escape(str(title))}</div>
                <div class="tm-result-meta">{html.escape(str(author))} | {html.escape(str(source_value))} | {html.escape(str(category_value))}</div>
                <div class="tm-result-preview">doc_id: {html.escape(str(row.get('doc_id', '')))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Raw saved works table"):
        st.dataframe(
            filtered_df[["title", "author", "source", "category", "doc_id"]],
            use_container_width=True,
            hide_index=True,
        )

with right:
    options = []

    for _, row in filtered_df.iterrows():
        title = row.get("title", "") or "Untitled"
        author = row.get("author", "") or "Unknown"
        source_value = row.get("source", "") or "unknown"
        options.append(f"{title} / {author} / {source_value}")

    selected_label = st.selectbox(
        "Select target work",
        options,
        key="personal_library_target",
    )

    selected_index = options.index(selected_label)
    selected_row = filtered_df.iloc[selected_index]
    target_doc_id = selected_row.get("doc_id", "")
    st.session_state["selected_target_doc_id"] = target_doc_id

    st.markdown(
        f"""
        <div class="tm-detail-card">
            <div class="tm-title">Selected Target Work</div>
            <div class="tm-result-title">{html.escape(str(selected_row.get('title', 'Untitled')))}</div>
            <div class="tm-result-meta">target_doc_id: {html.escape(str(target_doc_id))}</div>
            <div class="tm-result-preview">
                author: {html.escape(str(selected_row.get('author', '') or 'Unknown'))}<br>
                source: {html.escape(str(selected_row.get('source', '') or 'unknown'))}<br>
                user_email: {html.escape(email.strip())}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Internal info"):
        st.write(f"doc_id: `{target_doc_id}`")
        st.write(f"user_email: `{email.strip()}`")

    search_clicked = st.button("Search similar works", type="primary")


if search_clicked:
    clear_last_search()
    clear_debug()

    debug_url = build_search_debug_url(
        email=email,
        target_doc_id=target_doc_id,
        top=top,
        source=source,
        category=category,
        filter_name=filter_name,
    )
    st.session_state["last_debug_url"] = debug_url

    try:
        data, elapsed, url = search_similar(
            email=email,
            target_doc_id=target_doc_id,
            top=top,
            source=source,
            category=category,
            filter_name=filter_name,
        )

        st.session_state["last_results"] = data.get("results", [])
        st.session_state["last_data"] = data
        st.session_state["last_elapsed"] = elapsed
        st.session_state["last_url"] = url

    except Exception as exc:
        clear_last_search()
        st.session_state["last_error"] = str(exc)
        st.session_state["last_error_body"] = read_http_error_body(exc)
        st.error("Search failed. Results were cleared so stale data is not shown.")


results = st.session_state.get("last_results", [])
data = st.session_state.get("last_data")
elapsed = st.session_state.get("last_elapsed", 0)
url = st.session_state.get("last_url", "")
last_error = st.session_state.get("last_error", "")

if last_error:
    st.error(last_error)

if data is not None and not last_error:
    st.success(f"{len(results)} result(s) / {elapsed:.2f}s")

    if not results:
        st.info("No results.")
    else:
        result_df = make_results_frame(results)

        left, right = st.columns([3, 2], gap="large")

        with left:
            st.markdown("### Similar works")

            for _, row in result_df.head(8).iterrows():
                title = row.get("title", "") or "Untitled"
                author = row.get("author", "") or "Unknown"
                source_value = row.get("source", "") or "unknown"
                st.markdown(
                    f"""
                    <div class="tm-result-card">
                        <div class="tm-result-title">{int(row['index']) + 1}. {html.escape(str(title))}</div>
                        <div class="tm-result-meta">similarity {float(row['similarity']):.4f} | {html.escape(str(author))} | {html.escape(str(source_value))}</div>
                        <div class="tm-result-preview">doc_id: {html.escape(str(row.get('doc_id', '')))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("Raw similar works table"):
                st.dataframe(
                    result_df[["title", "author", "source", "similarity", "url", "doc_id"]],
                    use_container_width=True,
                    hide_index=True,
                )

            st.download_button(
                "Download similar works CSV",
                result_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="personal_library_similar_works.csv",
                mime="text/csv",
            )

        with right:
            st.markdown("### Selected result")

            result_options = [
                f"{row['index'] + 1}. {row['title']} / {row['author']} / {row['similarity']:.4f}"
                for _, row in result_df.iterrows()
            ]

            result_label = st.selectbox("Select result", result_options)
            result_index = result_options.index(result_label)
            selected_result = results[result_index]

            st.markdown(
                f"""
                <div class="tm-detail-card">
                    <div class="tm-title">Result Detail</div>
                    <div class="tm-result-title">{html.escape(str(selected_result.get('title', 'Untitled')))}</div>
                    <div class="tm-result-meta">similarity {float(selected_result.get('similarity', selected_result.get('score', 0))):.4f}</div>
                    <div class="tm-result-preview">
                        author: {html.escape(str(selected_result.get('author', '') or 'Unknown'))}<br>
                        source: {html.escape(str(selected_result.get('source', '')))}<br>
                        doc_id: {html.escape(str(selected_result.get('doc_id', '')))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if selected_result.get("url"):
                st.markdown(f"[Open source]({selected_result.get('url')})")

            params = selected_result.get("parameters", [])

            if params:
                param_df = pd.DataFrame([
                    {
                        "parameter": p.get("key", ""),
                        "value": p.get("value", 0),
                    }
                    for p in params
                ])
                param_df["value"] = pd.to_numeric(param_df["value"], errors="coerce").fillna(0)
                st.subheader("Parameters")
                st.dataframe(param_df, use_container_width=True, hide_index=True)
                st.bar_chart(param_df.set_index("parameter"))


if st.session_state.get("last_debug_url") or data is not None:
    with st.expander("Debug"):
        st.write("URL")
        st.code(st.session_state.get("last_debug_url") or url)

        if st.session_state.get("last_error_body"):
            st.write("Error response body")
            st.code(st.session_state["last_error_body"])

        if data is not None and not last_error:
            st.write("Response")
            st.json(data)
