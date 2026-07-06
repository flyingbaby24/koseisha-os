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

        st.success(f"{len(results)} result(s) / {elapsed:.2f}s")

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
                })

            df = pd.DataFrame(rows)

            st.subheader("Similar works")
            st.dataframe(df, use_container_width=True)

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
            st.dataframe(author_df, use_container_width=True)

            st.subheader("Query Parameters")
            st.json(data.get("query_parameters", []))

            st.subheader("Top Result Parameters")
            st.json(results[0].get("parameters", []))

        else:
            st.info("No results.")

        with st.expander("Debug"):
            st.write(url)
            st.json(data)

    except Exception as exc:
        st.error(str(exc))
