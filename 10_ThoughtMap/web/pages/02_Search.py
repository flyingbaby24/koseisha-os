import json
import time
import urllib.parse
import urllib.request

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ThoughtMap Search", layout="wide")

API_BASE_URL = "https://koseisha-os.onrender.com"

st.title("ThoughtMap Similarity Search")
st.caption("FastAPI /search client")

with st.sidebar:
    top = st.slider("Top results", 1, 50, 10)
    mode = st.selectbox("Search mode", ["keyword", "hybrid", "semantic"], index=0)
    source = st.text_input("Source filter", value="all")
    filter_name = st.selectbox("Parameter filter", ["general"])

q = st.text_input("Search query", value="Plato")

if st.button("Search FastAPI", type="primary"):
    params = {
        "q": q,
        "top": top,
        "mode": mode,
        "filter": filter_name,
    }

    if source and source != "all":
        params["source"] = source

    url = API_BASE_URL + "/search?" + urllib.parse.urlencode(params)

    try:
        start = time.time()
        with urllib.request.urlopen(url, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))

        elapsed = time.time() - start
        results = data.get("results", [])

        st.session_state["last_data"] = data
        st.session_state["last_results"] = results
        st.session_state["last_url"] = url
        st.session_state["last_elapsed"] = elapsed

    except Exception as exc:
        st.error(str(exc))

data = st.session_state.get("last_data")
results = st.session_state.get("last_results", [])
url = st.session_state.get("last_url", "")
elapsed = st.session_state.get("last_elapsed", 0)

if data is not None:
    st.success(f"{len(results)} result(s) / {elapsed:.2f}s")

    if results:
        rows = []
        for i, item in enumerate(results):
            rows.append({
                "index": i,
                "doc_id": item.get("doc_id", ""),
                "title": item.get("title", ""),
                "author": item.get("author", ""),
                "source": item.get("source", ""),
                "similarity": item.get("similarity", item.get("score", "")),
                "url": item.get("url", ""),
            })

        df = pd.DataFrame(rows)

        left, right = st.columns([3, 2])

        with left:
            st.subheader("Similar works")
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.subheader("Similar authors")
            author_df = (
                df[df["author"] != ""]
                .groupby("author", as_index=False)
                .agg(
                    works=("doc_id", "count"),
                    best_similarity=("similarity", "max"),
                )
                .sort_values(["best_similarity", "works"], ascending=False)
            )
            st.dataframe(author_df, use_container_width=True, hide_index=True)

        with right:
            st.subheader("Selected work detail")

            options = [
                f"{row['index'] + 1}. {row['title']} / {row['author']} / {row['similarity']}"
                for _, row in df.iterrows()
            ]

            selected_label = st.selectbox("Select result", options)
            selected_index = options.index(selected_label)
            selected = results[selected_index]

            st.markdown(f"### {selected.get('title', 'Untitled')}")
            st.write(f"Author: {selected.get('author', '') or 'Unknown'}")
            st.write(f"Source: `{selected.get('source', '')}`")
            st.write(f"doc_id: `{selected.get('doc_id', '')}`")
            st.metric("Similarity", selected.get("similarity", selected.get("score", 0)))

            if selected.get("url"):
                st.markdown(f"[Open source]({selected.get('url')})")

            st.subheader("Selected Parameters")
            params = selected.get("parameters", [])
            if params:
                param_rows = []
                for p in params:
                    param_rows.append({
                        "parameter": p.get("key", ""),
                        "value": p.get("value", 0),
                    })
                param_df = pd.DataFrame(param_rows)
                st.dataframe(param_df, use_container_width=True, hide_index=True)
                st.bar_chart(param_df.set_index("parameter"))
            else:
                st.info("No selected parameters.")

            st.subheader("Query Parameters")
            query_params = data.get("query_parameters", [])
            if query_params:
                q_rows = []
                for p in query_params:
                    q_rows.append({
                        "parameter": p.get("key", ""),
                        "value": p.get("value", 0),
                    })
                qdf = pd.DataFrame(q_rows)
                st.dataframe(qdf, use_container_width=True, hide_index=True)
                st.bar_chart(qdf.set_index("parameter"))
            else:
                st.info("No query parameters.")

    else:
        st.info("No results.")

    with st.expander("Debug"):
        st.write(url)
        st.json(data)
