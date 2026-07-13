from pathlib import Path
import hashlib
import logging
import os
import re
import json
import socket
import time
import zipfile
import tempfile
import io
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import streamlit as st


logger = logging.getLogger(__name__)


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
        logger.exception("Failed to import umap-learn for ThoughtMap layout.")
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

st.title("ThoughtMap Web v0.2")
st.caption("Upload texts, visualize thought clusters, search by meaning, and apply JSON thought filters.")

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
BASE_DIR = Path(__file__).resolve().parent
FILTER_DIR = BASE_DIR / "filters"
USER_DATA_DIR = BASE_DIR / "user_data"
USER_ID_LENGTH = 16
DEFAULT_FASTAPI_BASE_URL = "https://koseisha-os.onrender.com"

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


def get_secret_or_env(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, default) or "")


def normalize_api_base_url(value: str) -> str:
    text = str(value or "").strip().rstrip("/")
    return text or DEFAULT_FASTAPI_BASE_URL


def build_api_url(api_base_url: str, path: str) -> str:
    base = normalize_api_base_url(api_base_url)
    clean_path = str(path or "").strip()
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path
    return base + clean_path


def parameter_rows_from_embedding_row(row: pd.Series) -> list[dict[str, object]] | None:
    parameter_keys = [
        "philosophy",
        "psychology",
        "science",
        "economy",
        "economics",
        "karma",
        "emotion",
        "moral",
        "morality",
        "ideal",
        "individual",
        "community",
    ]
    out = []
    for key in parameter_keys:
        if key not in row:
            continue
        value = row.get(key)
        if value is None or str(value).strip() == "":
            continue
        try:
            out.append({"key": key, "value": float(value)})
        except (TypeError, ValueError):
            continue
    return out or None


def call_health_api(api_base_url: str, timeout_seconds: int) -> dict[str, object]:
    url = build_api_url(api_base_url, "/health")
    started = time.perf_counter()
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= int(response.status) < 300,
                "url": url,
                "status_code": int(response.status),
                "response_text": body,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "exception_type": "",
                "exception_message": "",
            }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "status_code": getattr(exc, "code", None),
            "response_text": _read_error_body(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }


def post_save_document_by_email(
    api_base_url: str,
    email: str,
    doc_id: str,
    parameters=None,
    timeout_seconds: int = 90,
) -> dict[str, object]:
    url = build_api_url(api_base_url, "/users/by-email/save")
    payload = {
        "email": normalize_registered_email(email),
        "doc_id": str(doc_id or "").strip(),
    }
    if parameters:
        payload["parameters"] = parameters

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    logger.info("Posting personal save request to %s", url)
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            logger.info("Personal save response status=%s body=%s", response.status, response_body[:1000])
            parsed_json_error = _json_decode_error(response_body)
            return {
                "ok": 200 <= int(response.status) < 300 and parsed_json_error == "",
                "doc_id": payload["doc_id"],
                "url": url,
                "status_code": int(response.status),
                "response_text": response_body,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "exception_type": "JSONDecodeError" if parsed_json_error else "",
                "exception_message": parsed_json_error,
                "request_json": payload,
            }
    except HTTPError as exc:
        response_body = _read_error_body(exc)
        logger.warning("Personal save HTTP error url=%s status=%s body=%s", url, exc.code, response_body[:1000])
        return {
            "ok": False,
            "doc_id": payload["doc_id"],
            "url": url,
            "status_code": int(exc.code),
            "response_text": response_body,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_json": payload,
        }
    except (TimeoutError, socket.timeout, URLError) as exc:
        logger.warning("Personal save network error url=%s type=%s message=%s", url, type(exc).__name__, exc)
        return {
            "ok": False,
            "doc_id": payload["doc_id"],
            "url": url,
            "status_code": None,
            "response_text": _read_error_body(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_json": payload,
        }
    except Exception as exc:
        logger.exception("Personal save unexpected communication error.")
        return {
            "ok": False,
            "doc_id": payload["doc_id"],
            "url": url,
            "status_code": None,
            "response_text": _read_error_body(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_json": payload,
        }


def _read_error_body(exc: BaseException) -> str:
    if isinstance(exc, HTTPError):
        try:
            return exc.read().decode("utf-8", errors="replace")
        except Exception:
            return str(exc)
    if isinstance(exc, URLError):
        return str(getattr(exc, "reason", exc))
    return str(exc)


def _json_decode_error(text: str) -> str:
    if not str(text or "").strip():
        return ""
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return str(exc)
    return ""


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
            try:
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
            except zipfile.BadZipFile:
                st.warning(f"Could not read ZIP file: {name}")
            except Exception as exc:
                logger.exception("Failed to read uploaded ZIP file.")
                st.warning(f"Could not read ZIP file: {name}. {exc}")

        elif name.lower().endswith((".txt", ".md")):
            text = uploaded.getvalue().decode("utf-8", errors="ignore").strip()

            if text:
                docs.append({"title": clean_filename(name), "text": text, "source": "file"})

    return docs


def make_layout_points(embeddings, min_dist: float):
    document_count = len(embeddings)

    if document_count <= 0:
        return np.empty((0, 2))

    if document_count == 1:
        return np.array([[0.0, 0.0]])

    if document_count == 2:
        return np.array([[-0.5, 0.0], [0.5, 0.0]])

    UMAP = require_umap()
    safe_n_neighbors = min(15, max(2, document_count - 1))
    reducer = UMAP(
        n_neighbors=safe_n_neighbors,
        min_dist=min_dist,
        metric="cosine",
        random_state=42,
    )
    return reducer.fit_transform(embeddings)


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
    KMeans = require_kmeans()
    make_filter_scores, _make_parameter_scores = require_thought_composition()
    model = load_model()
    titles = [d["title"] for d in docs]
    texts = [d["text"] for d in docs]
    embeddings = model.encode(texts, show_progress_bar=False)

    points = make_layout_points(embeddings, min_dist)

    document_count = len(docs)
    cluster_count = min(max(1, cluster_count), document_count)
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


st.sidebar.header("Input")

uploaded_files = st.sidebar.file_uploader("Upload .txt / .md / .zip", type=["txt", "md", "zip"], accept_multiple_files=True)
pasted_text = st.sidebar.text_area("Or paste text", height=180)

st.sidebar.header("Public User Storage")
registered_email = st.sidebar.text_input(
    "Registered email",
    value="",
    help="Used only to create a stable private folder hash. The email itself is not used as a folder name.",
)
personal_api_base_url = st.sidebar.text_input(
    "Personal API Base URL",
    value=normalize_api_base_url(
        get_secret_or_env(
            "THOUGHTMAP_API_BASE_URL",
            get_secret_or_env("API_BASE_URL", DEFAULT_FASTAPI_BASE_URL),
        )
    ),
    help="FastAPI endpoint for saving Personal Library data.",
)
personal_api_timeout_seconds = st.sidebar.number_input(
    "Personal API timeout seconds",
    min_value=10,
    max_value=180,
    value=90,
    step=10,
)
user_id = make_user_id_from_email(registered_email)
if user_id:
    st.sidebar.caption(f"user_id: `{user_id}`")
else:
    st.sidebar.caption("Enter an email to enable saving thoughtmap_embeddings.csv after Analyze.")

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

st.sidebar.header("Analysis Settings")
cluster_count = st.sidebar.slider("Cluster count", min_value=2, max_value=20, value=8)
n_neighbors = st.sidebar.slider("UMAP n_neighbors", min_value=3, max_value=50, value=10)
min_dist = st.sidebar.slider("UMAP min_dist", min_value=0.0, max_value=0.9, value=0.2, step=0.05)

st.sidebar.header("Thought Filters")
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
run = st.sidebar.button("Analyze")

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

st.subheader("Overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Documents", len(df))
col2.metric("Clusters", df["cluster"].nunique())
col3.metric("Filters", len(categories))
col4.metric("Model", MODEL_NAME)

tab1, tab2, tab_status, tab3, tab4, tab5, tab6 = st.tabs(["Thought Continent", "Profile", "Composition", "Search", "Documents", "Filters", "Export"])

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
    st.subheader("Thought Composition")

    if filter_score_df is None:
        st.info("No filters selected or no filters loaded.")

    else:
        status_df = make_status_profile(filter_score_df)
        profile_class, profile_description = infer_profile_class(status_df)

        # =====================================================
        # Document Information
        # =====================================================
        if len(docs) == 1:

            st.markdown(
                f"## 📄 {docs[0]['title']}"
            )

            top3 = (
                status_df
                .sort_values("share_%", ascending=False)
                .head(3)
            )

            st.caption(
                " | ".join(
                    f"{row['parameter']} {row['share_%']:.1f}%"
                    for _, row in top3.iterrows()
                )
            )

        else:

            st.markdown(
                f"## 📚 {len(docs)} Documents"
            )

        col_s1, col_s2 = st.columns([1, 2])

        with col_s1:

            if len(docs) == 1:
                st.caption(
                    f"Source: {docs[0]['title']}"
                )

            st.metric(
                "Primary class",
                profile_class
            )

            st.caption(
                profile_description
            )

            top_groups = get_top_composition_groups(
                status_df
            )

            if top_groups:

                st.write(
                    "Top composition groups"
                )

                card_cols = st.columns(
                    min(3, len(top_groups))
                )

                for card_col, (label, share) in zip(
                    card_cols,
                    top_groups
                ):
                    card_col.metric(
                        label,
                        f"{share:.1f}%"
                    )

            st.write("Composition table")

            table_df = status_df.copy()

            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True
            )

        with col_s2:

            document_title = (
                docs[0]["title"]
                if len(docs) == 1
                else f"{len(docs)} Documents"
            )

            st.pyplot(
                plot_status_bar(
                    status_df,
                    title=document_title
                ),
                use_container_width=True
            )

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
    query = st.text_input("Search by idea / theme", placeholder="例: 因果, subjectivity, capitalism criticism")
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

        st.dataframe(pd.DataFrame(results), use_container_width=True)

with tab4:
    st.dataframe(df, use_container_width=True)
    selected = st.selectbox("Read document", df["title"].tolist())
    idx = df.index[df["title"] == selected][0]
    st.text_area("Text", docs[idx]["text"], height=350)

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

        # -------------------------
    # Embeddings CSV
    # -------------------------

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

    if user_id:
        if st.button("Save embeddings to Personal Library"):
            save_url = build_api_url(personal_api_base_url, "/users/by-email/save")
            st.caption(f"POST URL: `{save_url}`")

            health_result = call_health_api(
                personal_api_base_url,
                timeout_seconds=int(personal_api_timeout_seconds),
            )
            if not health_result.get("ok"):
                st.warning("Personal API health check failed. Save was not started.")
                with st.expander("Personal API health debug", expanded=True):
                    st.write(health_result)
                st.stop()

            results = []
            total_rows = len(embedding_df)
            progress_text = st.empty()
            progress_bar = st.progress(0)
            for index, (_, row) in enumerate(embedding_df.iterrows(), start=1):
                progress_text.info(f"Saving {index} / {total_rows}")
                progress_bar.progress(index / max(1, total_rows))
                doc_id = str(row.get("doc_id", "") or "").strip()
                if not doc_id:
                    continue
                result = post_save_document_by_email(
                    api_base_url=personal_api_base_url,
                    email=registered_email,
                    doc_id=doc_id,
                    parameters=parameter_rows_from_embedding_row(row),
                    timeout_seconds=int(personal_api_timeout_seconds),
                )
                results.append(result)
            progress_text.success(f"Save requests finished: {len(results)} document(s).")

            success_count = sum(1 for item in results if item.get("ok"))
            failure_count = len(results) - success_count
            if failure_count == 0:
                st.success(f"Saved {success_count} document(s) to Personal Library.")
            else:
                st.error(f"Saved {success_count} document(s), failed {failure_count}.")

            debug_rows = [
                {
                    "doc_id": item.get("doc_id"),
                    "url": item.get("url"),
                    "status_code": item.get("status_code"),
                    "response_text": item.get("response_text"),
                    "elapsed_seconds": item.get("elapsed_seconds"),
                    "exception_type": item.get("exception_type"),
                    "exception_message": item.get("exception_message"),
                    "request_json": {
                        key: value
                        for key, value in dict(item.get("request_json") or {}).items()
                        if key != "email"
                    },
                }
                for item in results
            ]
            with st.expander("Personal save debug"):
                st.write(debug_rows)
    else:
        st.info("Enter a registered email in the sidebar to save to the Personal Library.")

    # -------------------------
    # Cluster CSV
    # -------------------------
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

    # -------------------------
    # Cluster Labels
    # -------------------------
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

    # -------------------------
    # Filter Scores
    # -------------------------
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

        try:
            _make_filter_scores, make_parameter_scores = require_thought_composition()
            parameter_score_df = make_parameter_scores(df, filter_score_df)
        except ValueError:
            parameter_score_df = None

        if parameter_score_df is not None:
            parameter_score_bytes = parameter_score_df.to_csv(
                index=False,
                encoding="utf-8-sig"
            ).encode("utf-8-sig")

            st.download_button(
                "Download parameter scores CSV",
                parameter_score_bytes,
                file_name="parameter_scores.csv",
                mime="text/csv"
            )

    # -------------------------
    # Selected Filters
    # -------------------------
    category_bytes = json.dumps(
        categories,
        ensure_ascii=False,
        indent=2
    ).encode("utf-8")

    st.download_button(
        "Download selected filters JSON",
        category_bytes,
        file_name="selected_filters.json",
        mime="application/json"
    )

    # ==========================================================
    # Thought Composition Export
    # ==========================================================
    if filter_score_df is not None:

        status_df = make_status_profile(filter_score_df)

        st.markdown("---")
        st.subheader("Thought Composition Export")

        # -------------------------
        # Composition PNG
        # -------------------------
        document_title = (
            docs[0]["title"]
            if len(docs) == 1
            else f"{len(docs)} Documents"
        )

        fig = plot_status_bar(
            status_df,
            title=document_title
        )

        png_buffer = io.BytesIO()

        fig.savefig(
            png_buffer,
            format="png",
            dpi=300,
            bbox_inches="tight"
        )

        png_buffer.seek(0)

        safe_title = (
            docs[0]["title"]
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            if len(docs) == 1
            else "multi_document"
        )

        st.download_button(
            "Download Composition Chart PNG",
            png_buffer,
            file_name=f"{safe_title}_thought_composition.png",
            mime="image/png"
        )

        # -------------------------
        # Composition Profile CSV
        # -------------------------
        profile_df = pd.DataFrame([
            {
                "profile_class": infer_profile_class(status_df)[0],
                **{
                    row["parameter"]: row["share_%"]
                    for _, row in status_df.iterrows()
                }
            }
        ])

        profile_csv = profile_df.to_csv(
            index=False,
            encoding="utf-8-sig"
        ).encode("utf-8-sig")

        st.download_button(
            "Download Composition Profile CSV",
            profile_csv,
            file_name=f"{safe_title}_thought_composition_profile.csv",
            mime="text/csv"
        )
