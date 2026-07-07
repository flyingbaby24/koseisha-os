import json
import time
import urllib.parse
import urllib.request

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ThoughtMap Search", layout="wide")

API_BASE_URL = "https://koseisha-os.onrender.com"

st.title("ThoughtMap Similarity Search")
st.caption("Keyword search or embedding-to-embedding similarity search.")


def call_api(params: dict) -> tuple[dict, float, str]:
    url = API_BASE_URL + "/search?" + urllib.parse.urlencode(params)
    start = time.time()

    with urllib.request.urlopen(url, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data, time.time() - start, url


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


with st.sidebar:
    search_mode = st.radio(
        "Search type",
        [
            "Keyword search",
            "Embedding similarity",
            "Hybrid",
        ],
        index=0,
    )

    top = st.slider("Top results", 1, 50, 10)

    source = st.text_input("Source filter", value="all")
    category = st.text_input("Category filter", value="all")
    filter_name = st.selectbox("Parameter filter", ["general"])


q = ""
target_doc_id = ""
email = ""

if search_mode == "Keyword search":
    q = st.text_input(
        "Keyword",
        value="Plato",
        help="author / title / doc_id / source を検索します。",
    )

elif search_mode == "Embedding similarity":
    st.info(
        "Embedding similarity は、既存のembeddingをtargetにして公式DBのembeddingと比較する検索です。"
    )

    target_doc_id = st.text_input(
        "Target doc_id",
        placeholder="例: user_suno:doc_000400 / gutendex:doc_000631",
        help="既存DB内のdoc_idをtarget embeddingとして使います。",
    )

    email = st.text_input(
        "Registered e-mail",
        placeholder="Personal Searchを使う場合のみ入力",
    )

else:
    st.info(
        "Hybrid は keywordで候補を絞り、target embeddingとの近さで並べます。"
    )

    q = st.text_input(
        "Keyword filter",
        value="",
        placeholder="例: Plato / Jinn Project / love / war",
    )

    target_doc_id = st.text_input(
        "Target doc_id",
        placeholder="例: user_suno:doc_000400",
    )

    email = st.text_input(
        "Registered e-mail",
        placeholder="Personal Searchを使う場合のみ入力",
    )


if st.button("Search FastAPI", type="primary"):
    params = {
        "top": top,
        "filter": filter_name,
    }

    if source and source != "all":
        params["source"] = source

    if category and category != "all":
        params["category"] = category

    if search_mode == "Keyword search":
        if not q.strip():
            st.error("Please enter a keyword.")
            st.stop()

        params["mode"] = "keyword"
        params["q"] = q.strip()

    elif search_mode == "Embedding similarity":
        if not target_doc_id.strip():
            st.error("Please enter target doc_id.")
            st.stop()

        params["mode"] = "embedding"
        params["target_doc_id"] = target_doc_id.strip()

        if email.strip():
            params["user_email"] = email.strip()

    else:
        if not target_doc_id.strip():
            st.error("Please enter target doc_id.")
            st.stop()

        params["mode"] = "hybrid"
        params["target_doc_id"] = target_doc_id.strip()

        if q.strip():
            params["q"] = q.strip()

        if email.strip():
            params["user_email"] = email.strip()

    try:
        data, elapsed, url = call_api(params)
        results = data.get("results", [])

        st.session_state["last_data"] = data
        st.session_state["last_results"] = results
        st.session_state["last_elapsed"] = elapsed
        st.session_state["last_url"] = url
        st.session_state["last_mode"] = search_mode

    except Exception as exc:
        st.error(str(exc))


data = st.session_state.get("last_data")
results = st.session_state.get("last_results", [])
elapsed = st.session_state.get("last_elapsed", 0)
url = st.session_state.get("last_url", "")
last_mode = st.session_state.get("last_mode", "")

if data is not None:
    st.success(f"{last_mode}: {len(results)} result(s) / {elapsed:.2f}s")

    if not results:
        st.info("No results.")

    else:
        df = result_frame(results)

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
            st.metric(
                "Similarity",
                f"{float(selected.get('similarity', selected.get('score', 0))):.4f}",
            )

            if selected.get("url"):
                st.markdown(f"[Open source]({selected.get('url')})")

            st.subheader("Parameters")
            params = selected.get("parameters", [])

            if params:
                pdf = pd.DataFrame([
                    {
                        "parameter": p.get("key", ""),
                        "value": p.get("value", 0),
                    }
                    for p in params
                ])
                pdf["value"] = pd.to_numeric(pdf["value"], errors="coerce").fillna(0)
                st.dataframe(pdf, use_container_width=True, hide_index=True)
                st.bar_chart(pdf.set_index("parameter"))
            else:
                st.info("No parameters.")

    with st.expander("Debug"):
        st.write(url)
        st.json(data)
