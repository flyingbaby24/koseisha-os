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
    api_base_url = st.text_input("API Base URL", value="http://127.0.0.1:8000")
    top = st.slider("Top results", 1, 50, 10)
    mode = st.selectbox("Search mode", ["semantic", "keyword", "hybrid"])
    source = st.text_input("Source filter", value="all")
    filter_name = st.selectbox("Parameter filter", ["general"])
    show_debug = st.checkbox("Show debug", value=False)

q = st.text_input("Search query", value="Plato")

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
        st.error(f"Could not connect to FastAPI: {exc}")
