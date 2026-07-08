from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

import pandas as pd
import streamlit as st

APP_TITLE = "ThoughtMap Personal Library"
API_BASE_URL = "https://koseisha-os.onrender.com"

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("Manage saved Personal Library works and run embedding similarity search.")


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


with st.sidebar:
    st.header("Personal Library")

    email = st.text_input(
        "Registered e-mail",
        placeholder="example@example.com",
        key="library_email",
    )

    top = st.slider("Top results", 1, 50, 10)
    source = st.text_input("Source filter", value="all")
    category = st.text_input("Category filter", value="all")
    filter_name = st.selectbox("Parameter filter", ["general"])

    reload_clicked = st.button("Reload Library")


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

c1, c2, c3 = st.columns(3)
c1.metric("Works", len(works_df))
c2.metric("Sources", works_df["source"].replace("", pd.NA).dropna().nunique())
c3.metric("Categories", works_df["category"].replace("", pd.NA).dropna().nunique())

st.subheader("Saved works")

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

st.dataframe(
    filtered_df[["title", "author", "source", "category"]],
    use_container_width=True,
    hide_index=True,
)

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

st.success(f"Selected: {selected_row.get('title', 'Untitled')}")

with st.expander("Internal info"):
    st.write(f"doc_id: `{target_doc_id}`")

if st.button("Search similar works", type="primary"):
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
        st.error(f"Search failed: {exc}")


results = st.session_state.get("last_results", [])
data = st.session_state.get("last_data")
elapsed = st.session_state.get("last_elapsed", 0)
url = st.session_state.get("last_url", "")

if data is not None:
    st.markdown("---")
    st.success(f"{len(results)} result(s) / {elapsed:.2f}s")

    if not results:
        st.info("No results.")
    else:
        result_df = make_results_frame(results)

        left, right = st.columns([3, 2])

        with left:
            st.subheader("Similar works")
            st.dataframe(
                result_df[["title", "author", "source", "similarity", "url"]],
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
            st.subheader("Selected result")

            result_options = [
                f"{row['index'] + 1}. {row['title']} / {row['author']} / {row['similarity']:.4f}"
                for _, row in result_df.iterrows()
            ]

            result_label = st.selectbox("Select result", result_options)
            result_index = result_options.index(result_label)
            selected_result = results[result_index]

            st.markdown(f"### {selected_result.get('title', 'Untitled')}")
            st.write(f"Author: {selected_result.get('author', '') or 'Unknown'}")
            st.write(f"Source: `{selected_result.get('source', '')}`")
            st.metric(
                "Similarity",
                f"{float(selected_result.get('similarity', selected_result.get('score', 0))):.4f}",
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

    with st.expander("Debug"):
        st.write(url)
        st.json(data)
