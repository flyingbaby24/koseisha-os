import json
import time
import urllib.parse
import urllib.request

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ThoughtMap Search", layout="wide")

API_BASE_URL = "https://koseisha-os.onrender.com"

st.title("ThoughtMap Similarity Search")
st.caption("Official / Personal search client for ThoughtMap FastAPI")


def call_api(url: str) -> tuple[dict, float]:
    start = time.time()
    with urllib.request.urlopen(url, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data, time.time() - start


def make_result_frame(results: list[dict]) -> pd.DataFrame:
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
        df["similarity"] = pd.to_numeric(df["similarity"], errors="coerce").fillna(0.0)

    return df


def make_param_frame(parameters: list[dict]) -> pd.DataFrame:
    rows = []
    for p in parameters or []:
        rows.append({
            "parameter": p.get("key", ""),
            "value": p.get("value", 0),
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0.0)

    return df


def make_author_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "author" not in df.columns:
        return pd.DataFrame()

    author_df = df[df["author"].astype(str).str.strip() != ""].copy()

    if author_df.empty:
        return pd.DataFrame()

    return (
        author_df
        .groupby("author", as_index=False)
        .agg(
            works=("doc_id", "count"),
            best_similarity=("similarity", "max"),
        )
        .sort_values(["best_similarity", "works"], ascending=False)
    )


with st.sidebar:
    search_backend = st.radio(
        "Search backend",
        ["Official DB", "Personal Search"],
        index=0,
    )

    top = st.slider("Top results", 1, 50, 10)

    mode = st.selectbox(
        "Search mode",
        ["keyword", "hybrid", "semantic"],
        index=0,
    )

    source = st.text_input("Source filter", value="all")

    category = st.text_input(
        "Category filter",
        value="all",
        help="例: gutendex / lyric / literature / philosophy / all",
    )

    filter_name = st.selectbox("Parameter filter", ["general"])

q = st.text_input("Search query", value="Plato")

email = ""
if search_backend == "Personal Search":
    email = st.text_input(
        "Registered e-mail",
        placeholder="example@example.com",
    )

if st.button("Search FastAPI", type="primary"):
    if search_backend == "Personal Search" and not email.strip():
        st.error("Please enter your registered e-mail.")
        st.stop()

    params = {
        "q": q,
        "top": top,
        "mode": mode,
        "filter": filter_name,
    }

    if source and source != "all":
        params["source"] = source

    if category and category != "all":
        params["category"] = category

    if search_backend == "Personal Search":
        params["user_email"] = email.strip()

    url = API_BASE_URL + "/search?" + urllib.parse.urlencode(params)

    try:
        data, elapsed = call_api(url)
        results = data.get("results", [])

        st.session_state["last_data"] = data
        st.session_state["last_results"] = results
        st.session_state["last_url"] = url
        st.session_state["last_elapsed"] = elapsed
        st.session_state["last_backend"] = search_backend

    except Exception as exc:
        st.error(str(exc))

data = st.session_state.get("last_data")
results = st.session_state.get("last_results", [])
url = st.session_state.get("last_url", "")
elapsed = st.session_state.get("last_elapsed", 0)
last_backend = st.session_state.get("last_backend", "")

if data is not None:
    st.success(f"{last_backend}: {len(results)} result(s) / {elapsed:.2f}s")

    if results:
        df = make_result_frame(results)

        left, right = st.columns([3, 2])

        with left:
            st.subheader("Similar works")
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.download_button(
                "Download similar works CSV",
                df.to_csv(index=False).encode("utf-8-sig"),
                file_name="thoughtmap_search_results.csv",
                mime="text/csv",
            )

            st.subheader("Similar authors")
            author_df = make_author_frame(df)

            if author_df.empty:
                st.info("No author summary.")
            else:
                st.dataframe(author_df, use_container_width=True, hide_index=True)

                st.download_button(
                    "Download similar authors CSV",
                    author_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="thoughtmap_similar_authors.csv",
                    mime="text/csv",
                )

        with right:
            st.subheader("Selected work detail")

            options = [
                f"{row['index'] + 1}. {row['title']} / {row['author']} / {row['similarity']:.4f}"
                for _, row in df.iterrows()
            ]

            selected_label = st.selectbox("Select result", options)
            selected_index = options.index(selected_label)
            selected = results[selected_index]

            st.markdown(f"### {selected.get('title', 'Untitled')}")
            st.write(f"Author: {selected.get('author', '') or 'Unknown'}")
            st.write(f"Source: `{selected.get('source', '')}`")
            st.write(f"doc_id: `{selected.get('doc_id', '')}`")
            st.metric("Similarity", f"{float(selected.get('similarity', selected.get('score', 0))):.4f}")

            if selected.get("url"):
                st.markdown(f"[Open source]({selected.get('url')})")

            st.subheader("Selected Parameters")
            param_df = make_param_frame(selected.get("parameters", []))

            if param_df.empty:
                st.info("No selected parameters.")
            else:
                st.dataframe(param_df, use_container_width=True, hide_index=True)
                st.bar_chart(param_df.set_index("parameter"))

            st.subheader("Query Parameters")
            qdf = make_param_frame(data.get("query_parameters", []))

            if qdf.empty:
                st.info("No query parameters.")
            else:
                st.dataframe(qdf, use_container_width=True, hide_index=True)
                st.bar_chart(qdf.set_index("parameter"))

    else:
        st.info("No results.")

    with st.expander("Debug"):
        st.write(url)
        st.json(data)
