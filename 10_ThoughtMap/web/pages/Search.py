from pathlib import Path
import hashlib
import html
import re
import json
import zipfile
import tempfile
import io
import urllib.request

import numpy as np
import pandas as pd
import streamlit as st


def get_matplotlib_pyplot():
    import matplotlib.pyplot as plt

    plt.rcParams["font.family"] = "Meiryo"
    plt.rcParams["axes.unicode_minus"] = False
    return plt


def require_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        raise RuntimeError(
            "SentenceTransformer is required only for the local Thought Composition app. "
            "The FastAPI shared-backend search page does not need it. "
            f"Import failed: {exc}"
        ) from exc
    return SentenceTransformer


def require_umap():
    try:
        from umap import UMAP
    except Exception as exc:
        raise RuntimeError(
            "umap-learn is required only for the local Thought Composition app. "
            f"Import failed: {exc}"
        ) from exc
    return UMAP


def require_kmeans():
    try:
        from sklearn.cluster import KMeans
    except Exception as exc:
        raise RuntimeError(
            "scikit-learn is required only for the local Thought Composition app. "
            f"Import failed: {exc}"
        ) from exc
    return KMeans


def require_cosine_similarity():
    from sklearn.metrics.pairwise import cosine_similarity

    return cosine_similarity


def require_thought_composition():
    from thought_composition import make_filter_scores, make_parameter_scores

    return make_filter_scores, make_parameter_scores


st.set_page_config(
    page_title="ThoughtMap Web v0.2",
    layout="wide"
)


def inject_custom_css():
    st.markdown(
        """
        <style>
        :root {
            --tm-bg: #050914;
            --tm-panel: rgba(10, 18, 38, 0.78);
            --tm-panel-strong: rgba(14, 26, 56, 0.94);
            --tm-border: rgba(99, 242, 255, 0.26);
            --tm-cyan: #38e8ff;
            --tm-blue: #6da8ff;
            --tm-violet: #9a7cff;
            --tm-pink: #ff4fd8;
            --tm-green: #5dffb3;
            --tm-text: #e9f7ff;
            --tm-muted: #91a4c4;
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 8%, rgba(56, 232, 255, 0.18), transparent 28%),
                radial-gradient(circle at 86% 0%, rgba(154, 124, 255, 0.16), transparent 26%),
                linear-gradient(135deg, #040712 0%, #081123 48%, #090718 100%);
            color: var(--tm-text);
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(99, 242, 255, 0.055) 1px, transparent 1px),
                linear-gradient(90deg, rgba(99, 242, 255, 0.045) 1px, transparent 1px);
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

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
            color: var(--tm-cyan);
            letter-spacing: 0.04em;
            text-transform: uppercase;
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
            padding: 2.1rem 2.2rem;
            border: 1px solid var(--tm-border);
            border-radius: 18px;
            background:
                linear-gradient(135deg, rgba(12, 23, 52, 0.96), rgba(8, 12, 30, 0.86)),
                radial-gradient(circle at 88% 24%, rgba(56,232,255,0.24), transparent 20%);
            box-shadow: 0 18px 60px rgba(0,0,0,0.34), inset 0 0 50px rgba(56,232,255,0.055);
            margin-bottom: 1.15rem;
        }

        .tm-hero::after {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(120deg, transparent 0%, rgba(56,232,255,0.10) 45%, transparent 58%);
            transform: translateX(-35%);
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
            position: relative;
            margin: 0;
            color: var(--tm-text);
            font-size: clamp(2.1rem, 5vw, 4.4rem);
            line-height: 1;
            letter-spacing: 0;
            text-shadow: 0 0 32px rgba(56,232,255,0.42);
            z-index: 1;
        }

        .tm-hero p {
            position: relative;
            max-width: 820px;
            color: #bcd3f4;
            margin: 0.85rem 0 0;
            font-size: 1.04rem;
            z-index: 1;
        }

        .tm-hero-strip {
            position: relative;
            display: flex;
            gap: 0.65rem;
            flex-wrap: wrap;
            margin-top: 1.25rem;
            z-index: 1;
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

        .tm-section-title {
            color: var(--tm-text);
            font-weight: 850;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin: 1.1rem 0 0.7rem;
        }

        .tm-overview-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
            margin-bottom: 1.2rem;
        }

        .tm-card, .tm-stat-card, .tm-search-shell, .tm-doc-shell, .tm-status-frame {
            border: 1px solid var(--tm-border);
            border-radius: 14px;
            background: linear-gradient(180deg, rgba(12, 23, 52, 0.92), rgba(7, 12, 28, 0.86));
            box-shadow: 0 14px 44px rgba(0,0,0,0.28), inset 0 0 28px rgba(56,232,255,0.04);
        }

        .tm-stat-card {
            padding: 1rem;
            min-height: 118px;
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
            font-size: 1.85rem;
            line-height: 1.1;
            font-weight: 850;
            overflow-wrap: anywhere;
        }

        .tm-stat-note {
            color: var(--tm-cyan);
            margin-top: 0.45rem;
            font-size: 0.78rem;
        }

        .tm-status-frame {
            padding: 1.1rem;
            margin-bottom: 1rem;
        }

        .tm-status-title {
            color: var(--tm-green);
            font-size: 0.78rem;
            font-weight: 850;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .tm-status-class {
            color: var(--tm-text);
            font-size: clamp(1.8rem, 4vw, 3.2rem);
            font-weight: 900;
            line-height: 1.05;
            text-shadow: 0 0 28px rgba(93,255,179,0.22);
        }

        .tm-status-desc {
            color: #b7c8e8;
            margin-top: 0.45rem;
        }

        .tm-rank-card {
            padding: 0.85rem;
            border-radius: 12px;
            border: 1px solid rgba(154,124,255,0.28);
            background: rgba(154,124,255,0.09);
            margin-bottom: 0.65rem;
        }

        .tm-rank-name {
            color: var(--tm-muted);
            font-size: 0.78rem;
            overflow-wrap: anywhere;
        }

        .tm-rank-value {
            color: var(--tm-text);
            font-size: 1.55rem;
            font-weight: 850;
        }

        .tm-search-shell, .tm-doc-shell {
            padding: 1rem 1.1rem;
            margin-bottom: 1rem;
        }

        .tm-result-card {
            padding: 0.95rem 1rem;
            border: 1px solid rgba(56,232,255,0.22);
            border-radius: 12px;
            background: rgba(7, 12, 28, 0.78);
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

        div[data-testid="stTabs"] button {
            border-radius: 999px;
            color: #bcd3f4;
            font-weight: 750;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--tm-text);
            background: linear-gradient(90deg, rgba(56,232,255,0.2), rgba(154,124,255,0.18));
            border: 1px solid rgba(56,232,255,0.34);
        }

        [data-testid="stMetric"] {
            border: 1px solid rgba(56,232,255,0.18);
            border-radius: 12px;
            padding: 0.8rem;
            background: rgba(7, 12, 28, 0.58);
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
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .tm-hero {
                padding: 1.45rem;
            }
        }

        @media (max-width: 560px) {
            .tm-overview-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


inject_custom_css()

st.markdown(
    """
    <section class="tm-hero">
        <div class="tm-kicker">Semantic Intelligence Console</div>
        <h1>ThoughtMap Web v0.2</h1>
        <p>Upload texts, visualize thought clusters, search by meaning, and apply JSON thought filters through a cybernetic analysis cockpit.</p>
        <div class="tm-hero-strip">
            <span class="tm-chip">AI Embedding</span>
            <span class="tm-chip">Thought Continent</span>
            <span class="tm-chip">Composition HUD</span>
            <span class="tm-chip">Semantic Search</span>
        </div>
    </section>
    """,
    unsafe_allow_html=True
)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
BASE_DIR = Path(__file__).resolve().parent
FILTER_DIR = BASE_DIR / "filters"
USER_DATA_DIR = BASE_DIR / "user_data"
USER_ID_LENGTH = 16

DEFAULT_FILTERS = {
    "basic_thought": {
        "Society": "society, class, family, reputation, status, community, social order, hierarchy, institution, organization, culture",
        "Cognition": "recognition, perception, cognition, awareness, interpretation, understanding, viewpoint, perspective, observation, information, knowledge",
        "Causality": "cause, effect, consequence, responsibility, reason, result, logic, causality, chain, influence, connection",
        "Introspection": "self, identity, memory, reflection, introspection, inner life, personality, emotion, self-awareness, growth",
        "Experimentation": "trial, experiment, prototype, testing, iteration, challenge, exploration, adaptation, failure, improvement",
        "Technology": "technology, machine, system, code, AI, automation, engineering, infrastructure, network, algorithm",
        "Philosophy": "truth, meaning, ethics, existence, wisdom, value, reality, consciousness, metaphysics, ontology",
        "Questioning": "question, inquiry, curiosity, uncertainty, doubt, search, discovery, investigation, unknown, possibility"
    },
    "basic_literature": {
        "philosophy": "truth, meaning, ethics, existence, consciousness, wisdom",
        "society": "class, family, reputation, marriage, manners, wealth, status, community, social order",
        "religion": "god, faith, sin, salvation, prayer, sacred, soul",
        "love": "romance, affection, marriage, desire, longing, heartbreak",
        "death": "death, grief, mortality, loss, afterlife, decay",
        "nature": "forest, sea, sky, animals, seasons, earth, wilderness",
        "war": "battle, army, soldiers, weapons, invasion, military, battlefield, war",
        "identity": "self, name, memory, personality, inner life, transformation"
    },
    "jinn_os": {
        "社会文明": "community, status, hierarchy, reputation, institution, culture, tradition, authority, social order",
        "認識文明": "recognition, interpretation, perception, awareness, misunderstanding, viewpoint, observer, cognition",
        "因果文明": "cause, consequence, responsibility, incentive, chain, reaction, effect, structure, causality",
        "内省文明": "identity, self, memory, reflection, loneliness, emotion, growth, personality, inner life",
        "試行文明": "prototype, challenge, adaptation, iteration, experiment, attempt, exploration, failure",
        "技術文明": "AI, algorithm, machine, network, code, digital, automation, system, technology",
        "哲学文明": "truth, meaning, existence, value, ethics, reality, wisdom, consciousness",
        "問い文明": "question, doubt, curiosity, possibility, unknown, search, investigation, inquiry"
    }
}


def normalize_registered_email(email: str) -> str:
    return str(email or "").strip().lower()


def make_user_id_from_email(email: str) -> str:
    normalized = normalize_registered_email(email)
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:USER_ID_LENGTH]


def user_embedding_dir(user_id: str) -> Path:
    safe_user_id = re.sub(r"[^a-f0-9]", "", str(user_id or "").lower())[:USER_ID_LENGTH]
    if not safe_user_id:
        raise ValueError("A registered email address is required before saving user embeddings.")
    return USER_DATA_DIR / safe_user_id


def build_embedding_export_frame(
    df: pd.DataFrame,
    embeddings,
    docs: list[dict],
    labels: dict,
) -> pd.DataFrame:
    docs = docs or []
    text_by_index = {
        i: str(doc.get("text", "") or "")
        for i, doc in enumerate(docs)
        if isinstance(doc, dict)
    }

    frame = pd.DataFrame({
        "doc_id": df["doc_id"] if "doc_id" in df.columns else [f"doc_{i:06d}" for i in range(len(df))],
        "title": df["title"],
        "source": df["source"],
        "cluster": df["cluster"],
        "cluster_label": [
            labels.get(str(cluster), f"Cluster {cluster}")
            for cluster in df["cluster"]
        ],
        "x": df["x"],
        "y": df["y"],
        "text": [text_by_index.get(i, "") for i in range(len(df))],
        "embedding": [
            json.dumps(emb.tolist(), ensure_ascii=False)
            for emb in embeddings
        ],
    })
    return frame


def save_user_embedding_csv(user_id: str, embedding_df: pd.DataFrame) -> Path:
    target_dir = user_embedding_dir(user_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "thoughtmap_embeddings.csv"
    embedding_df.to_csv(target_path, index=False, encoding="utf-8-sig")
    return target_path


def ensure_default_filters():
    FILTER_DIR.mkdir(parents=True, exist_ok=True)

    for name, data in DEFAULT_FILTERS.items():
        path = FILTER_DIR / f"{name}.json"

        if not path.exists():
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )


@st.cache_resource
def load_model():
    SentenceTransformer = require_sentence_transformer()
    return SentenceTransformer(MODEL_NAME)


def load_filter_sets():
    ensure_default_filters()

    filters = {}

    for path in sorted(FILTER_DIR.glob("*.json")):
        try:
            filters[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            filters[path.stem] = {"__ERROR__": str(e)}

    return filters


def clean_filename(name: str) -> str:
    name = Path(name).stem
    name = re.sub(r"^\d+_", "", name)
    return name[:120]


def read_uploaded_files(uploaded_files):
    docs = []

    for uploaded in uploaded_files:
        name = uploaded.name

        if name.lower().endswith(".zip"):
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = Path(tmpdir) / name
                zip_path.write_bytes(uploaded.getvalue())

                with zipfile.ZipFile(zip_path, "r") as z:
                    for info in z.infolist():
                        if info.is_dir():
                            continue

                        if not info.filename.lower().endswith((".txt", ".md")):
                            continue

                        raw = z.read(info.filename)
                        text = raw.decode("utf-8", errors="ignore").strip()

                        if text:
                            docs.append({"title": clean_filename(info.filename), "text": text, "source": "zip"})

        elif name.lower().endswith((".txt", ".md")):
            text = uploaded.getvalue().decode("utf-8", errors="ignore").strip()

            if text:
                docs.append({"title": clean_filename(name), "text": text, "source": "file"})

    return docs


def split_pasted_text(text: str, mode: str):
    text = text.strip()

    if not text:
        return []

    if mode == "one_document":
        return [{"title": "Pasted Text", "text": text, "source": "paste"}]

    if mode == "delimiter":
        parts = re.split(r"\n\s*---+\s*\n", text)
    elif mode == "headings":
        parts = re.split(r"\n(?=#{1,3}\s+|第.+?章|【.+?】)", text)
    else:
        parts = re.split(r"\n\s*\n\s*\n+", text)

    docs = []

    for i, part in enumerate(parts, start=1):
        part = part.strip()

        if len(part) < 30:
            continue

        first_line = part.splitlines()[0].strip()
        title = first_line[:60] if first_line else f"Text {i}"

        docs.append({"title": f"{i:04d}_{title}", "text": part, "source": "paste_split"})

    return docs


def merge_selected_filters(filter_sets, selected_filter_names):
    categories = {}

    for name in selected_filter_names:
        data = filter_sets.get(name, {})

        if "__ERROR__" in data:
            continue

        categories.update(data)

    return categories



def auto_label_clusters(df, filter_score_df):
    if filter_score_df is None or filter_score_df.empty:
        return {str(cluster_id): f"Cluster {cluster_id}" for cluster_id in sorted(df["cluster"].unique())}

    labels = {}

    for cluster_id in sorted(df["cluster"].unique()):
        indexes = df.index[df["cluster"] == cluster_id].tolist()
        cluster_scores = filter_score_df.iloc[indexes].mean().sort_values(ascending=False)
        labels[str(cluster_id)] = str(cluster_scores.index[0]) if len(cluster_scores) else f"Cluster {cluster_id}"

    return labels


def analyze(docs, cluster_count: int, n_neighbors: int, min_dist: float, categories):
    UMAP = require_umap()
    KMeans = require_kmeans()
    make_filter_scores, _make_parameter_scores = require_thought_composition()
    model = load_model()
    titles = [d["title"] for d in docs]
    texts = [d["text"] for d in docs]
    embeddings = model.encode(texts, show_progress_bar=False)

    reducer = UMAP(n_neighbors=n_neighbors, min_dist=min_dist, metric="cosine", random_state=42)
    points = reducer.fit_transform(embeddings)

    kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(embeddings)

    df = pd.DataFrame({
        "title": titles,
        "cluster": clusters,
        "x": points[:, 0],
        "y": points[:, 1],
        "source": [d["source"] for d in docs],
    })
    
    df["doc_id"] = [
    f"doc_{i:06d}"
    for i in range(len(df))
    ]

    filter_score_df = make_filter_scores(embeddings, categories, model)

    if filter_score_df is not None:
        df["top_filter"] = filter_score_df.idxmax(axis=1).values
        df["top_filter_score"] = filter_score_df.max(axis=1).values

    labels = auto_label_clusters(df, filter_score_df)
    return df, embeddings, filter_score_df, labels


def plot_map(df, labels):
    plt = get_matplotlib_pyplot()
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.scatter(df["x"], df["y"], s=30, alpha=0.35)

    for cluster_id in sorted(df["cluster"].unique()):
        cdf = df[df["cluster"] == cluster_id]
        center_x = cdf["x"].mean()
        center_y = cdf["y"].mean()
        label = labels.get(str(cluster_id), f"Cluster {cluster_id}")
        count = len(cdf)
        ax.scatter(center_x, center_y, s=700, alpha=0.85)
        ax.text(center_x, center_y, f"{label}\n{count}", ha="center", va="center", fontsize=9)

    ax.set_title("Thought Continent")
    ax.set_xlabel("Axis 1")
    ax.set_ylabel("Axis 2")
    fig.tight_layout()
    return fig


def plot_profile(df, labels):
    plt = get_matplotlib_pyplot()
    counts = df["cluster"].value_counts().sort_index()
    names = [labels.get(str(cluster_id), f"Cluster {cluster_id}") for cluster_id in counts.index]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(names, counts.values)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height, str(int(height)), ha="center", va="bottom")

    ax.set_title("Thought Profile")
    ax.set_ylabel("Number of Documents")
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return fig


def plot_pie(df, labels):
    plt = get_matplotlib_pyplot()
    counts = df["cluster"].value_counts().sort_index()
    names = [labels.get(str(cluster_id), f"Cluster {cluster_id}") for cluster_id in counts.index]

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(counts.values, labels=names, autopct="%1.0f%%")
    ax.set_title("Thought Distribution")
    fig.tight_layout()
    return fig


def plot_filter_profile(filter_score_df):
    plt = get_matplotlib_pyplot()
    summary = filter_score_df.mean().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(12, 5))
    bars = ax.bar(summary.index, summary.values)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height, f"{height:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_title("Average Thought Filter Profile")
    ax.set_ylabel("Normalized score")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    return fig


def plot_single_filter_scores(score_series):
    plt = get_matplotlib_pyplot()
    score_series = score_series.sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(score_series.index, score_series.values)
    ax.set_title("Document Thought Filter Scores")
    ax.set_ylabel("Normalized score")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    return fig


def get_status_order(filter_score_df):
    """
    Keep status parameters in the same order as the selected filter JSON.
    This makes different profiles easier to compare.
    """
    return list(filter_score_df.columns)


def make_status_profile(filter_score_df):
    """
    Convert average filter scores into a 100% composition profile.
    This is not an ability/status score. It shows how the person's
    thought energy is distributed across the selected filter categories.
    """
    status_order = get_status_order(filter_score_df)
    summary = filter_score_df.mean()

    total = float(summary.sum()) if len(summary) else 0.0
    if total <= 0:
        points = summary * 0
    else:
        points = summary / total * 100

    def rank_label(value):
        # Composition-oriented rank thresholds.
        # These ranks mean share/concentration, not superiority.
        if value >= 18:
            return "S"
        if value >= 14:
            return "A"
        if value >= 10:
            return "B"
        if value >= 6:
            return "C"
        if value >= 3:
            return "D"
        return "E"

    status_df = pd.DataFrame({
        "parameter": points.index,
        "share_%": points.round(1).values,
        "rank": [rank_label(v) for v in points.values],
        "raw_score": summary.round(4).values
    })

    status_df["parameter"] = pd.Categorical(
        status_df["parameter"],
        categories=status_order,
        ordered=True
    )

    # Keep JSON/filter order in the table for stable comparison.
    status_df = status_df.sort_values("parameter").reset_index(drop=True)
    return status_df


def get_composition_axis_limit(values):
    """
    Choose a readable chart axis for percentage composition.
    A 100% axis makes every radar/bar look tiny when many categories exist,
    so scale to the actual maximum while preserving enough headroom.
    """
    max_value = float(np.max(values)) if len(values) else 0.0
    if max_value <= 0:
        return 20

    limit = np.ceil((max_value * 1.25) / 5) * 5
    return int(max(15, min(100, limit)))


def get_top_composition_groups(status_df):
    """
    Small summary cards for the left side.
    They group the top six parameters into three readable buckets.
    """
    top = status_df.sort_values("share_%", ascending=False).head(6)
    rows = top.to_dict("records")

    groups = []
    for i in range(0, len(rows), 2):
        chunk = rows[i:i + 2]
        if not chunk:
            continue
        label = "・".join(str(r["parameter"]) for r in chunk)
        share = sum(float(r["share_%"]) for r in chunk)
        groups.append((label, share))

    return groups
def rank_color(rank):
    colors = {
        "S": "#8b5cf6",
        "A": "#f97316",
        "B": "#eab308",
        "C": "#22c55e",
        "D": "#3b82f6",
        "E": "#6b7280",
    }
    return colors.get(rank, "#6b7280")
def plot_status_bar(status_df, title=None):
    plt = get_matplotlib_pyplot()

    ordered = status_df.iloc[::-1].copy()

    colors = [rank_color(rank) for rank in ordered["rank"]]

    x_limit = get_composition_axis_limit(
        ordered["share_%"].values
    )

    fig, ax = plt.subplots(figsize=(11, 6))

    bars = ax.barh(
        ordered["parameter"].astype(str),
        ordered["share_%"],
        color=colors
    )

    for bar, rank, score in zip(
        bars,
        ordered["rank"],
        ordered["share_%"]
    ):
        width = bar.get_width()

        ax.text(
            width + (x_limit * 0.015),
            bar.get_y() + bar.get_height() / 2,
            f"{score:.1f}%   {rank}",
            va="center",
            fontsize=10
        )

    ax.set_xlim(0, x_limit)

    if title:
        chart_title = f"{title} - Thought Composition"
    else:
        chart_title = "Thought Composition"

    ax.set_title(
        chart_title,
        fontsize=16,
        pad=15,
        fontweight="bold"
    )

    ax.set_xlabel("Thought share (%)")

    ax.grid(
        axis="x",
        alpha=0.25
    )

    fig.tight_layout()

    return fig
def plot_status_radar(status_df):
    plt = get_matplotlib_pyplot()
    labels = status_df["parameter"].astype(str).tolist()
    values = status_df["share_%"].tolist()
    y_limit = get_composition_axis_limit(values)

    if len(labels) < 3:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "Radar chart needs at least 3 parameters.", ha="center", va="center")
        ax.axis("off")
        return fig

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111, polar=True)

    ax.plot(angles_closed, values_closed, linewidth=2)
    ax.fill(angles_closed, values_closed, alpha=0.25)

    ax.set_xticks(angles)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, y_limit)

    tick_step = 5 if y_limit <= 30 else 10
    ticks = list(range(0, y_limit + 1, tick_step))
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{t}%" for t in ticks])
    ax.set_title("Thought Composition Radar", pad=20)

    fig.tight_layout()
    return fig
def infer_profile_class(status_df):
    top = status_df.sort_values("share_%", ascending=False).head(3)
    names = top["parameter"].tolist()

    if not names:
        return "Unknown", "No dominant parameter detected."

    primary = names[0]
    secondary = names[1] if len(names) > 1 else None

    class_rules = {
        "philosophy": "Philosopher",
        "psychology": "Mind Reader",
        "science": "Natural Observer",
        "economics": "Market Analyst",
        "karma": "Causal Mapper",
        "emotion": "Emotionalist",
        "morality": "Moralist",
        "ideal": "Idealist",
        "individual": "Individualist",
        "community": "Communitarian",
        "哲学": "Philosopher",
        "心理学": "Mind Reader",
        "自然科学": "Natural Observer",
        "経済": "Market Analyst",
        "カルマ": "Causal Mapper",
        "感情": "Emotionalist",
        "道徳": "Moralist",
        "理念": "Idealist",
        "個人": "Individualist",
        "共同体": "Communitarian",
    }

    profile_class = class_rules.get(primary, str(primary).title())

    if secondary:
        description = f"Most concentrated in {primary}, with strong {secondary} influence."
    else:
        description = f"Most concentrated in {primary}."

    return profile_class, description


st.sidebar.markdown("### Control Deck")
st.sidebar.caption("Load text, tune the analysis field, then launch the scan.")

st.sidebar.markdown("#### 01 Input")

uploaded_files = st.sidebar.file_uploader("Upload .txt / .md / .zip", type=["txt", "md", "zip"], accept_multiple_files=True)
pasted_text = st.sidebar.text_area("Or paste text", height=180)

split_mode_label = st.sidebar.selectbox(
    "Paste split mode",
    ["One document", "Split by delimiter ---", "Split by headings", "Split by blank blocks"]
)

split_mode_map = {
    "One document": "one_document",
    "Split by delimiter ---": "delimiter",
    "Split by headings": "headings",
    "Split by blank blocks": "blank_blocks"
}

st.sidebar.markdown("#### 02 Analysis")
cluster_count = st.sidebar.slider("Cluster count", min_value=2, max_value=20, value=8)
n_neighbors = st.sidebar.slider("UMAP n_neighbors", min_value=3, max_value=50, value=10)
min_dist = st.sidebar.slider("UMAP min_dist", min_value=0.0, max_value=0.9, value=0.2, step=0.05)

st.sidebar.markdown("#### 03 Thought Filters")
filter_sets = load_filter_sets()

if filter_sets:
    selected_filter_names = st.sidebar.multiselect(
        "Select filter sets",
        list(filter_sets.keys()),
        default=list(filter_sets.keys())[:1]
    )
    with st.sidebar.expander("Loaded filter sets"):
        st.write(list(filter_sets.keys()))
else:
    selected_filter_names = []
    st.sidebar.info("No JSON filters found.")

categories = merge_selected_filters(filter_sets, selected_filter_names)
st.sidebar.markdown("---")
run = st.sidebar.button("Analyze", type="primary")

if run:
    docs = []

    if uploaded_files:
        docs.extend(read_uploaded_files(uploaded_files))

    docs.extend(split_pasted_text(
        pasted_text,
        split_mode_map[split_mode_label]
    ))

    # ----------------------------------
    # Minimum document check
    # ----------------------------------
    if len(docs) < 1:
        st.error("At least 1 document is needed.")
        st.stop()

    doc_count = len(docs)

    # ----------------------------------
    # Small dataset handling
    # ----------------------------------
    if doc_count < 3:

        st.warning(
            f"Only {doc_count} document(s) loaded. "
            "Thought Continent and clustering are disabled."
        )

        model = load_model()
        make_filter_scores, _make_parameter_scores = require_thought_composition()

        titles = [d["title"] for d in docs]
        texts = [d["text"] for d in docs]

        embeddings = model.encode(
            texts,
            show_progress_bar=False
        )

        df = pd.DataFrame({
            "title": titles,
            "cluster": [0] * doc_count,
            "x": [0.0] * doc_count,
            "y": [0.0] * doc_count,
            "source": [d["source"] for d in docs],
        })

        df["doc_id"] = [
            f"doc_{i:06d}"
            for i in range(len(df))
        ]

        filter_score_df = make_filter_scores(
            embeddings,
            categories,
            model
        )

        if filter_score_df is not None:
            df["top_filter"] = filter_score_df.idxmax(axis=1).values
            df["top_filter_score"] = filter_score_df.max(axis=1).values

        labels = {"0": "Profile"}

    else:

        if cluster_count >= doc_count:
            cluster_count = max(2, doc_count - 1)

        with st.spinner("Analyzing..."):
            df, embeddings, filter_score_df, labels = analyze(
                docs,
                cluster_count,
                min(n_neighbors, doc_count - 1),
                min_dist,
                categories
            )

    st.session_state["df"] = df
    st.session_state["embeddings"] = embeddings
    st.session_state["docs"] = docs
    st.session_state["labels"] = labels
    st.session_state["filter_score_df"] = filter_score_df
    st.session_state["categories"] = categories
    st.session_state["selected_filter_names"] = selected_filter_names

if "df" not in st.session_state:
    st.info("Upload text files or paste text, then click Analyze.")
    st.stop()

df = st.session_state["df"]
embeddings = st.session_state["embeddings"]
docs = st.session_state["docs"]
labels = st.session_state["labels"]
filter_score_df = st.session_state.get("filter_score_df")
categories = st.session_state.get("categories", {})

st.markdown('<div class="tm-section-title">Overview</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="tm-overview-grid">
        <div class="tm-stat-card">
            <div class="tm-stat-label">Documents</div>
            <div class="tm-stat-value">{len(df)}</div>
            <div class="tm-stat-note">Loaded text units</div>
        </div>
        <div class="tm-stat-card">
            <div class="tm-stat-label">Clusters</div>
            <div class="tm-stat-value">{df["cluster"].nunique()}</div>
            <div class="tm-stat-note">Detected thought zones</div>
        </div>
        <div class="tm-stat-card">
            <div class="tm-stat-label">Filters</div>
            <div class="tm-stat-value">{len(categories)}</div>
            <div class="tm-stat-note">Active lenses</div>
        </div>
        <div class="tm-stat-card">
            <div class="tm-stat-label">Model</div>
            <div class="tm-stat-value" style="font-size:1rem;line-height:1.35;">{MODEL_NAME}</div>
            <div class="tm-stat-note">Embedding engine</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

tab1, tab2, tab_status, tab3, tab4, tab5, tab6 = st.tabs(["Map", "Profile", "Composition", "Search", "Documents", "Filters", "Export"])

with tab1:

    if len(df) < 3:
        st.info(
            "Thought Continent requires at least 3 documents."
        )
    else:
        st.pyplot(
            plot_map(df, labels),
            use_container_width=True
        )

with tab2:
    col_a, col_b = st.columns(2)
    with col_a:
        st.pyplot(plot_profile(df, labels), use_container_width=True)
    with col_b:
        st.pyplot(plot_pie(df, labels), use_container_width=True)
    st.write("Cluster counts")
    st.dataframe(df["cluster"].value_counts().sort_index().rename("count"), use_container_width=True)

with tab_status:
    st.markdown('<div class="tm-section-title">Composition Status</div>', unsafe_allow_html=True)

    if filter_score_df is None:
        st.info("No filters selected or no filters loaded.")

    else:
        status_df = make_status_profile(filter_score_df)
        profile_class, profile_description = infer_profile_class(status_df)
        document_title = (
            docs[0]["title"]
            if len(docs) == 1
            else f"{len(docs)} Documents"
        )

        top3 = (
            status_df
            .sort_values("share_%", ascending=False)
            .head(3)
        )

        top_chips = "".join(
            f"<span class='tm-chip'>{html.escape(str(row['parameter']))} {row['share_%']:.1f}% / Rank {html.escape(str(row['rank']))}</span>"
            for _, row in top3.iterrows()
        )

        st.markdown(
            f"""
            <div class="tm-status-frame">
                <div class="tm-status-title">Player Profile / Thought Composition</div>
                <div class="tm-status-class">{html.escape(str(profile_class))}</div>
                <div class="tm-status-desc">{html.escape(profile_description)}</div>
                <div class="tm-hero-strip">
                    <span class="tm-chip">Source: {html.escape(document_title)}</span>
                    {top_chips}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_s1, col_s2 = st.columns([0.9, 2.1], gap="large")

        with col_s1:

            top_groups = get_top_composition_groups(
                status_df
            )

            if top_groups:

                st.markdown("**Top Slots**")

                for label, share in top_groups:
                    st.markdown(
                        f"""
                        <div class="tm-rank-card">
                            <div class="tm-rank-name">{html.escape(str(label))}</div>
                            <div class="tm-rank-value">{share:.1f}%</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            st.markdown("**Status Matrix**")

            table_df = status_df.copy()

            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True
            )

        with col_s2:
            st.pyplot(
                plot_status_bar(
                    status_df,
                    title=document_title
                ),
                use_container_width=True
            )

        with st.container():
            st.markdown("**Radar Field**")
            st.pyplot(
                plot_status_radar(status_df),
                use_container_width=True
            )

        st.caption(
            "Composition shares add up to 100%. "
            "Ranks show concentration inside this profile, "
            "not ability or superiority. "
            "Raw scores are the original average filter affinities."
        )


with tab3:
    st.markdown(
        """
        <div class="tm-search-shell">
            <div class="tm-status-title">Semantic Search Gateway</div>
            <div class="tm-status-desc">Search across the uploaded corpus by meaning, theme, and conceptual gravity.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    search_col, limit_col = st.columns([3, 1])
    with search_col:
        query = st.text_input(
            "Search by idea / theme",
            placeholder="Example: causality, subjectivity, capitalism criticism"
        )
    with limit_col:
        top_n = st.slider("Top N", 3, 30, 10)

    if query:
        cosine_similarity = require_cosine_similarity()
        model = load_model()
        query_embedding = model.encode([query])
        scores = cosine_similarity(query_embedding, embeddings)[0]
        ranked = np.argsort(scores)[::-1][:top_n]
        results = []

        for rank, idx in enumerate(ranked, start=1):
            cluster_value = int(df.iloc[idx]["cluster"])
            row = {
                "rank": rank,
                "title": df.iloc[idx]["title"],
                "cluster": cluster_value,
                "cluster_label": labels.get(str(cluster_value), f"Cluster {cluster_value}"),
                "similarity": float(scores[idx]),
                "preview": docs[idx]["text"][:300].replace("\n", " ")
            }

            if "top_filter" in df.columns:
                row["top_filter"] = df.iloc[idx]["top_filter"]
                row["top_filter_score"] = float(df.iloc[idx]["top_filter_score"])

            results.append(row)

        st.markdown(f"**Search results for:** `{query}`")

        for row in results:
            extra_filter = ""
            if "top_filter" in row:
                extra_filter = (
                    f" | top filter {html.escape(str(row['top_filter']))}"
                    f" ({row['top_filter_score']:.3f})"
                )

            st.markdown(
                f"""
                <div class="tm-result-card">
                    <div class="tm-result-title">#{row['rank']} {html.escape(str(row['title']))}</div>
                    <div class="tm-result-meta">
                        similarity {row['similarity']:.3f} | cluster {row['cluster']} / {html.escape(str(row['cluster_label']))}{extra_filter}
                    </div>
                    <div class="tm-result-preview">{html.escape(str(row['preview']))}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with st.expander("Raw result table"):
            st.dataframe(pd.DataFrame(results), use_container_width=True)

with tab4:
    st.markdown(
        """
        <div class="tm-doc-shell">
            <div class="tm-status-title">Document Browser</div>
            <div class="tm-status-desc">Select a document, inspect its metadata, and read the full text in a wider viewer.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    browser_col, reader_col = st.columns([0.9, 2.1], gap="large")

    with browser_col:
        selected = st.selectbox("Read document", df["title"].tolist())

    idx = df.index[df["title"] == selected][0]
    selected_cluster = int(df.loc[idx, "cluster"])
    selected_label = labels.get(str(selected_cluster), f"Cluster {selected_cluster}")

    with browser_col:
        st.markdown(
            f"""
            <div class="tm-rank-card">
                <div class="tm-rank-name">Cluster</div>
                <div class="tm-rank-value">{selected_cluster}</div>
            </div>
            <div class="tm-rank-card">
                <div class="tm-rank-name">Label</div>
                <div class="tm-rank-value" style="font-size:1.1rem;">{html.escape(str(selected_label))}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if "top_filter" in df.columns:
            st.markdown(
                f"""
                <div class="tm-rank-card">
                    <div class="tm-rank-name">Top Filter</div>
                    <div class="tm-rank-value" style="font-size:1.1rem;">{html.escape(str(df.loc[idx, "top_filter"]))}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with reader_col:
        st.text_area("Text", docs[idx]["text"], height=520)

    with st.expander("Document index"):
        st.dataframe(df, use_container_width=True)

with tab5:
    st.subheader("Thought Filters")

    if filter_score_df is None:
        st.info("No filters selected or no filters loaded.")
    else:
        st.write("Average profile")
        st.pyplot(plot_filter_profile(filter_score_df), use_container_width=True)

        filter_table = pd.concat([df[["title", "cluster"]], filter_score_df], axis=1)
        st.dataframe(filter_table, use_container_width=True)

        selected_doc = st.selectbox("Inspect document filter scores", df["title"].tolist(), key="filter_doc_select")
        idx = df.index[df["title"] == selected_doc][0]
        st.pyplot(plot_single_filter_scores(filter_score_df.iloc[idx]), use_container_width=True)

with tab6:

    embedding_df = build_embedding_export_frame(
        df=df,
        embeddings=embeddings,
        docs=docs,
        labels=labels,
    )

    embedding_csv = embedding_df.to_csv(
        index=False,
        encoding="utf-8-sig"
    ).encode("utf-8-sig")

    st.download_button(
        "Download document embeddings CSV",
        embedding_csv,
        file_name="thoughtmap_embeddings.csv",
        mime="text/csv"
    )

    st.markdown("---")
    st.subheader("Save to Personal Library")

    save_email = st.text_input(
        "Registered e-mail",
        placeholder="example@example.com",
        help="Only required when saving to your personal library.",
        key="save_email_export",
    )

    if st.button(
        "Save embeddings to Personal Library",
        key="save_embeddings_button",
    ):
        if not save_email.strip():
            st.error("Please enter your registered e-mail.")
        else:
            payload = {
                "email": save_email.strip(),
                "rows": embedding_df.to_dict(orient="records"),
            }

            request = urllib.request.Request(
                "https://koseisha-os.onrender.com/users/by-email/save-embeddings",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    result = json.loads(response.read().decode("utf-8"))

                st.success(f"Saved {result.get('count', 0)} works to Personal Library.")

            except Exception as exc:
                st.error(f"Save failed: {exc}")

    csv_bytes = df.to_csv(
        index=False,
        encoding="utf-8-sig"
    ).encode("utf-8-sig")

    st.download_button(
        "Download clusters CSV",
        csv_bytes,
        file_name="thoughtmap_clusters.csv",
        mime="text/csv"
    )

    label_bytes = json.dumps(
        labels,
        ensure_ascii=False,
        indent=2
    ).encode("utf-8")

    st.download_button(
        "Download cluster labels JSON",
        label_bytes,
        file_name="cluster_labels.json",
        mime="application/json"
    )

    if filter_score_df is not None:
        filter_bytes = filter_score_df.to_csv(
            index=False,
            encoding="utf-8-sig"
        ).encode("utf-8-sig")

        st.download_button(
            "Download filter scores CSV",
            filter_bytes,
            file_name="thoughtmap_filter_scores.csv",
            mime="text/csv"
        )
