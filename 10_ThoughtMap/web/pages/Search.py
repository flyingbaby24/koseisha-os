import html
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd
import streamlit as st


APP_TITLE = "ThoughtMap Search"
API_BASE_URL = "https://koseisha-os.onrender.com"

LAST_SEARCH_KEYS = [
    "last_data",
    "last_results",
    "last_url",
    "last_elapsed",
    "last_mode",
]

DEBUG_KEYS = [
    "last_error",
    "last_error_body",
    "last_debug_mode",
    "last_debug_params",
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

        .tm-shell, .tm-stat-card, .tm-result-card, .tm-work-card {
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

        .tm-result-card, .tm-work-card {
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


def build_search_url(params: dict) -> str:
    return API_BASE_URL + "/search?" + urllib.parse.urlencode(params)


def call_api(params: dict) -> tuple[dict, float, str]:
    url = build_search_url(params)
    start = time.time()

    with urllib.request.urlopen(url, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data, time.time() - start, url


def load_personal_works(email: str) -> list[dict]:
    url = API_BASE_URL + "/users/by-email/saved?" + urllib.parse.urlencode(
        {"email": email.strip()}
    )

    with urllib.request.urlopen(url, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("works", [])


def result_frame(results: list[dict]) -> pd.DataFrame:
    rows = []
    for i, item in enumerate(results):
        rows.append({
            "index": i,
            "doc_id": item.get("doc_id", ""),
            "title": item.get("title", ""),
            "author": item.get("author", ""),
            "source": item.get("source", ""),
            "similarity": item.get("similarity", item.get("score", 0)),
            "url": item.get("url", ""),
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df["similarity"] = pd.to_numeric(df["similarity"], errors="coerce").fillna(0)

    return df


def author_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    out = df[df["author"].astype(str).str.strip() != ""].copy()

    if out.empty:
        return pd.DataFrame()

    return (
        out.groupby("author", as_index=False)
        .agg(
            works=("doc_id", "count"),
            best_similarity=("similarity", "max"),
        )
        .sort_values(["best_similarity", "works"], ascending=False)
    )


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


def mode_to_api(search_mode: str) -> str:
    if search_mode == "Keyword search":
        return "keyword"
    if search_mode == "Embedding similarity":
        return "embedding"
    return "hybrid"


inject_custom_css()

st.markdown(
    """
    <section class="tm-hero">
        <div class="tm-kicker">Semantic Search Gateway</div>
        <h1>ThoughtMap Search</h1>
        <p>Search the official corpus by keyword, personal-library embedding similarity, or a hybrid of both.</p>
        <div class="tm-chip-row">
            <span class="tm-chip">Keyword Search</span>
            <span class="tm-chip">Embedding Similarity</span>
            <span class="tm-chip">Personal Library</span>
            <span class="tm-chip">FastAPI Debug</span>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown("### Control Deck")
    st.caption("Choose a search mode, connect your library, then launch.")

    st.markdown("#### 01 Search Mode")
    search_mode = st.radio(
        "Search type",
        ["Keyword search", "Embedding similarity", "Hybrid"],
        index=0,
    )

    st.markdown("#### 02 Limits")
    top = st.slider("Top results", 1, 50, 10)
    source = st.text_input("Source filter", value="all")
    category = st.text_input("Category filter", value="all")
    filter_name = st.selectbox("Parameter filter", ["general"])


q = ""
email = ""
target_doc_id = ""
works = []
selected = {}

left, right = st.columns([1.05, 1.65], gap="large")

with left:
    st.markdown(
        """
        <div class="tm-shell">
            <div class="tm-title">Search Console</div>
            <div class="tm-desc">Set the query. Embedding and Hybrid modes use a selected work from Personal Library as the target vector.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if search_mode == "Keyword search":
        q = st.text_input(
            "Keyword",
            value="Plato",
            help="Searches author, title, doc_id, source, category, tags, and notes.",
        )

    else:
        q = ""
        if search_mode == "Hybrid":
            q = st.text_input(
                "Keyword filter",
                value="",
                placeholder="Example: Plato / love / war / technology",
            )

        email = st.text_input(
            "Registered e-mail",
            placeholder="example@example.com",
            key=f"{mode_to_api(search_mode)}_email",
        )

        if email.strip():
            try:
                works = load_personal_works(email)

                if not works:
                    st.warning("No saved works were found for this e-mail.")
                else:
                    options = [
                        f"{w.get('title', 'Untitled')} / {w.get('source', '')} / {w.get('doc_id', '')}"
                        for w in works
                    ]

                    selected_label = st.selectbox(
                        "Select target work",
                        options,
                        key=f"{mode_to_api(search_mode)}_target_work",
                    )

                    selected = works[options.index(selected_label)]
                    target_doc_id = selected.get("doc_id", "")

                    st.markdown(
                        f"""
                        <div class="tm-work-card">
                            <div class="tm-result-title">{html.escape(str(selected.get('title', 'Untitled')))}</div>
                            <div class="tm-result-meta">target_doc_id: {html.escape(str(target_doc_id))}</div>
                            <div class="tm-result-preview">user_email will be sent as: {html.escape(email.strip())}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            except Exception as exc:
                st.error(f"Failed to load Personal Library: {exc}")

with right:
    works_count = len(works)
    mode_label = mode_to_api(search_mode)
    st.markdown(
        f"""
        <div class="tm-overview-grid">
            <div class="tm-stat-card">
                <div class="tm-stat-label">Mode</div>
                <div class="tm-stat-value" style="font-size:1.2rem;">{html.escape(mode_label)}</div>
            </div>
            <div class="tm-stat-card">
                <div class="tm-stat-label">Top</div>
                <div class="tm-stat-value">{top}</div>
            </div>
            <div class="tm-stat-card">
                <div class="tm-stat-label">Library Works</div>
                <div class="tm-stat-value">{works_count}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="tm-shell">
            <div class="tm-title">Personal Library + Search</div>
            <div class="tm-desc">The selected Personal Library work is passed to the API as target_doc_id, together with user_email.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    search_clicked = st.button("Search FastAPI", type="primary")


if search_clicked:
    clear_last_search()
    clear_debug()

    params = {
        "top": top,
        "filter": filter_name,
    }

    if source and source != "all":
        params["source"] = source

    if category and category != "all":
        params["category"] = category

    api_mode = mode_to_api(search_mode)
    params["mode"] = api_mode

    if api_mode == "keyword":
        if not q.strip():
            st.error("Please enter a keyword.")
            st.stop()

        params["q"] = q.strip()

    elif api_mode == "embedding":
        if not email.strip():
            st.error("Please enter your registered e-mail.")
            st.stop()

        if not target_doc_id:
            st.error("Please select a work from your Personal Library.")
            st.stop()

        params["target_doc_id"] = target_doc_id
        params["user_email"] = email.strip()

    else:
        if not email.strip():
            st.error("Please enter your registered e-mail.")
            st.stop()

        if not target_doc_id:
            st.error("Please select a work from your Personal Library.")
            st.stop()

        params["target_doc_id"] = target_doc_id
        params["user_email"] = email.strip()

        if q.strip():
            params["q"] = q.strip()

    attempted_url = build_search_url(params)
    st.session_state["last_debug_mode"] = api_mode
    st.session_state["last_debug_params"] = params.copy()
    st.session_state["last_debug_url"] = attempted_url

    try:
        data, elapsed, url = call_api(params)

        st.session_state["last_data"] = data
        st.session_state["last_results"] = data.get("results", [])
        st.session_state["last_url"] = url
        st.session_state["last_elapsed"] = elapsed
        st.session_state["last_mode"] = search_mode

    except Exception as exc:
        clear_last_search()
        st.session_state["last_error"] = str(exc)
        st.session_state["last_error_body"] = read_http_error_body(exc)
        st.error("Search failed. Results were cleared so stale data is not shown.")


data = st.session_state.get("last_data")
results = st.session_state.get("last_results", [])
elapsed = st.session_state.get("last_elapsed", 0)
url = st.session_state.get("last_url", "")
last_mode = st.session_state.get("last_mode", "")
last_error = st.session_state.get("last_error", "")

if last_error:
    st.error(last_error)

if data is not None and not last_error:
    st.success(f"{last_mode}: {len(results)} result(s) / {elapsed:.2f}s")

    if not results:
        st.info("No results.")

    else:
        df = result_frame(results)

        left, right = st.columns([3, 2], gap="large")

        with left:
            st.markdown("### Similar works")

            for _, row in df.head(8).iterrows():
                source_text = row.get("source", "") or "unknown"
                author_text = row.get("author", "") or "Unknown"
                st.markdown(
                    f"""
                    <div class="tm-result-card">
                        <div class="tm-result-title">{int(row['index']) + 1}. {html.escape(str(row['title'] or 'Untitled'))}</div>
                        <div class="tm-result-meta">similarity {float(row['similarity']):.4f} | {html.escape(str(author_text))} | {html.escape(str(source_text))}</div>
                        <div class="tm-result-preview">doc_id: {html.escape(str(row['doc_id']))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("Raw similar works table"):
                st.dataframe(df, use_container_width=True, hide_index=True)

            st.download_button(
                "Download similar works CSV",
                df.to_csv(index=False).encode("utf-8-sig"),
                file_name="thoughtmap_search_results.csv",
                mime="text/csv",
            )

            st.markdown("### Similar authors")
            adf = author_frame(df)

            if adf.empty:
                st.info("No author summary.")
            else:
                st.dataframe(adf, use_container_width=True, hide_index=True)

                st.download_button(
                    "Download similar authors CSV",
                    adf.to_csv(index=False).encode("utf-8-sig"),
                    file_name="thoughtmap_similar_authors.csv",
                    mime="text/csv",
                )

        with right:
            st.markdown("### Selected work detail")

            options = [
                f"{row['index'] + 1}. {row['title']} / {row['author']} / {row['similarity']:.4f}"
                for _, row in df.iterrows()
            ]

            selected_label = st.selectbox("Select result", options)
            selected_index = options.index(selected_label)
            selected_result = results[selected_index]

            st.markdown(f"### {selected_result.get('title', 'Untitled')}")
            st.write(f"Author: {selected_result.get('author', '') or 'Unknown'}")
            st.write(f"Source: `{selected_result.get('source', '')}`")
            st.write(f"doc_id: `{selected_result.get('doc_id', '')}`")
            st.metric(
                "Similarity",
                f"{float(selected_result.get('similarity', selected_result.get('score', 0))):.4f}",
            )

            if selected_result.get("url"):
                st.markdown(f"[Open source]({selected_result.get('url')})")

            st.subheader("Parameters")
            result_params = selected_result.get("parameters", [])

            if result_params:
                pdf = pd.DataFrame([
                    {
                        "parameter": p.get("key", ""),
                        "value": p.get("value", 0),
                    }
                    for p in result_params
                ])
                pdf["value"] = pd.to_numeric(pdf["value"], errors="coerce").fillna(0)
                st.dataframe(pdf, use_container_width=True, hide_index=True)
                st.bar_chart(pdf.set_index("parameter"))
            else:
                st.info("No parameters.")


if st.session_state.get("last_debug_mode") or data is not None:
    with st.expander("Debug"):
        st.write("Mode")
        st.code(str(st.session_state.get("last_debug_mode") or mode_to_api(last_mode)))

        st.write("Params")
        st.json(st.session_state.get("last_debug_params", {}))

        st.write("URL")
        st.code(st.session_state.get("last_debug_url") or url)

        if st.session_state.get("last_error_body"):
            st.write("Error response body")
            st.code(st.session_state["last_error_body"])

        if data is not None and not last_error:
            st.write("Response")
            st.json(data)
