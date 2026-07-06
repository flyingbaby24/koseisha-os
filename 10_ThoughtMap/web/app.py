import streamlit as st

APP_TITLE = "ThoughtMap"

def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("ThoughtMap Streamlit frontend")

    st.page_link("pages/02_Search.py", label="Search", icon="🔎")

    st.info(
        "Use the Search page for FastAPI / shared backend mode. "
        "This entrypoint avoids loading heavy ML dependencies."
    )

if __name__ == "__main__":
    main()
