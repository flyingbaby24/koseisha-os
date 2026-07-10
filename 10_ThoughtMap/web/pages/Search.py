import html
import json
import math
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
    "selected_result_index",
]

DEBUG_KEYS = [
    "last_error",
    "last_error_body",
    "last_debug_mode",
    "last_debug_params",
    "last_debug_url",
]

PARAMETER_KEYS = [
    "parameters",
    "parameter_scores",
    "filter_scores",
    "composition",
    "thought_composition",
    "scores",
]

CYBER_BG = "#050914"
CYBER_PANEL = "#081123"
CYBER_TEXT = "#e9f7ff"
CYBER_MUTED = "#91a4c4"
CYBER_GRID = "#245a73"
CYBER_CYAN = "#38e8ff"
CYBER_BLUE = "#6da8ff"
CYBER_VIOLET = "#9a7cff"
CYBER_GREEN = "#5dffb3"


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

        [data-testid="stSidebar"] * {
            color: var(--tm-text) !important;
        }

        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] p {
            color: #c3d4ed !important;
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

        .tm-console {
            padding: 1.15rem;
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

        .tm-best-card {
            border: 1px solid rgba(93,255,179,0.42);
            border-radius: 16px;
            background:
                linear-gradient(135deg, rgba(12, 30, 50, 0.96), rgba(10, 18, 38, 0.88)),
                radial-gradient(circle at 92% 12%, rgba(93,255,179,0.16), transparent 24%);
            padding: 1.15rem;
            margin: 1rem 0;
            box-shadow: 0 16px 44px rgba(0,0,0,0.28), inset 0 0 30px rgba(93,255,179,0.06);
        }

        .tm-section-heading {
            color: var(--tm-text);
            font-size: 1.25rem;
            font-weight: 850;
            margin: 1.2rem 0 0.55rem;
        }

        .tm-match-label {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.32rem 0.65rem;
            background: rgba(93,255,179,0.12);
            border: 1px solid rgba(93,255,179,0.36);
            color: var(--tm-green);
            font-size: 0.76rem;
            font-weight: 850;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.55rem;
        }

        .tm-result-title {
            color: var(--tm-text);
            font-weight: 850;
            font-size: 1.05rem;
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

        .stDataFrame, [data-testid="stTable"] {
            border: 1px solid rgba(56,232,255,0.16);
            border-radius: 12px;
            overflow: hidden;
        }

        textarea, input, .stTextInput input {
            border-color: rgba(56,232,255,0.34) !important;
            color: var(--tm-text) !important;
            background: rgba(5, 9, 20, 0.74) !important;
        }

        .stTextInput input {
            min-height: 3rem;
            font-size: 1rem;
        }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stLinkButton"] a {
            border: 1px solid rgba(56, 232, 255, 0.58) !important;
            background: linear-gradient(90deg, rgba(9,168,255,0.95), rgba(143,93,255,0.95)) !important;
            color: #ffffff !important;
            font-weight: 850 !important;
            border-radius: 12px !important;
        }

        .stDownloadButton > button:disabled,
        .stButton > button:disabled {
            background: rgba(78, 91, 120, 0.36) !important;
            color: rgba(233,247,255,0.42) !important;
            border-color: rgba(145,164,196,0.18) !important;
        }

        [data-testid="stExpander"] {
            border: 1px solid rgba(56,232,255,0.22);
            border-radius: 12px;
            background: rgba(5, 9, 20, 0.32);
        }

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary * {
            color: var(--tm-text) !important;
            font-weight: 800 !important;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: 0.85rem;
                padding-right: 0.85rem;
                padding-top: 0.85rem;
            }
            .tm-overview-grid {
                grid-template-columns: 1fr;
            }
            .tm-hero {
                padding: 1.45rem;
            }
            .tm-hero h1 {
                font-size: 2.35rem;
            }
            .tm-chip-row {
                gap: 0.45rem;
            }
            .tm-best-card,
            .tm-shell,
            .tm-console,
            .tm-result-card,
            .tm-work-card {
                padding: 0.9rem;
                border-radius: 12px;
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


def match_label(value) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "Possible Match"

    if score >= 0.75:
        return "Strong Match"
    if score >= 0.45:
        return "Good Match"
    return "Possible Match"


def display_parameter_name(name: str) -> str:
    text = str(name or "").strip().replace("_", " ")
    if not text:
        return ""
    return " ".join(part.capitalize() for part in text.split())


def display_slot_name(name: str) -> str:
    parts = [display_parameter_name(part) for part in str(name).replace("/", "×").split("×")]
    parts = [part for part in parts if part]
    return " × ".join(parts)


def get_result_index() -> int:
    try:
        return int(st.session_state.get("selected_result_index", 0))
    except (TypeError, ValueError):
        return 0


def clamp_result_index(results: list[dict]) -> int:
    if not results:
        return 0
    index = get_result_index()
    return max(0, min(index, len(results) - 1))


def rerun_app():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def render_open_link(label: str, url: str):
    if hasattr(st, "link_button"):
        st.link_button(label, url)
    else:
        st.markdown(f"[{html.escape(label)}]({url})")


def normalize_parameter_rows(item: dict) -> list[dict]:
    for key in PARAMETER_KEYS:
        if key not in item:
            continue

        rows = parse_parameter_value(item.get(key))
        if rows:
            return rows

    return []


def parse_parameter_value(value) -> list[dict]:
    if value is None:
        return []

    if isinstance(value, float) and math.isnan(value):
        return []

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return []

    if isinstance(value, dict):
        if "key" in value and "value" in value:
            row = make_parameter_row(value.get("key"), value.get("value"))
            return [row] if row else []

        for nested_key in PARAMETER_KEYS:
            nested_rows = parse_parameter_value(value.get(nested_key))
            if nested_rows:
                return nested_rows

        rows = []
        for key, score in value.items():
            row = make_parameter_row(key, score)
            if row:
                rows.append(row)
        return rows

    if isinstance(value, list):
        rows = []
        for entry in value:
            if isinstance(entry, dict):
                if "key" in entry and "value" in entry:
                    row = make_parameter_row(entry.get("key"), entry.get("value"))
                    if row:
                        rows.append(row)
                else:
                    rows.extend(parse_parameter_value(entry))
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                row = make_parameter_row(entry[0], entry[1])
                if row:
                    rows.append(row)
        return rows

    return []


def make_parameter_row(key, value) -> dict | None:
    key_text = str(key or "").strip()
    if not key_text:
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(numeric_value) or math.isinf(numeric_value):
        return None

    return {
        "parameter": key_text,
        "value": numeric_value,
    }


def rank_label(value: float) -> str:
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


def rank_color(rank: str) -> str:
    colors = {
        "S": "#8b5cf6",
        "A": "#f97316",
        "B": "#eab308",
        "C": "#22c55e",
        "D": "#3b82f6",
        "E": "#6b7280",
    }
    return colors.get(rank, "#6b7280")


def make_status_profile_from_parameters(parameter_rows: list[dict]) -> pd.DataFrame:
    param_df = pd.DataFrame(parameter_rows)
    if param_df.empty:
        return pd.DataFrame(columns=["parameter", "share_%", "rank", "raw_score"])

    param_df["value"] = pd.to_numeric(param_df["value"], errors="coerce").fillna(0)
    param_df = param_df[param_df["parameter"].astype(str).str.strip() != ""].copy()
    if param_df.empty:
        return pd.DataFrame(columns=["parameter", "share_%", "rank", "raw_score"])

    total = float(param_df["value"].sum())
    if total > 0:
        shares = param_df["value"] / total * 100
    else:
        shares = param_df["value"] * 0

    status_df = pd.DataFrame({
        "parameter": param_df["parameter"].astype(str).values,
        "share_%": shares.round(1).values,
        "rank": [rank_label(v) for v in shares.values],
        "raw_score": param_df["value"].round(4).values,
    })

    return status_df.reset_index(drop=True)


def get_composition_axis_limit(values) -> int:
    values = list(values)
    max_value = max(values) if values else 0
    if max_value <= 0:
        return 20

    limit = math.ceil((max_value * 1.25) / 5) * 5
    return int(max(15, min(100, limit)))


def get_top_composition_groups(status_df: pd.DataFrame) -> list[tuple[str, float]]:
    top = status_df.sort_values("share_%", ascending=False).head(3)
    return [
        (display_slot_name(str(row["parameter"])), float(row["share_%"]))
        for _, row in top.iterrows()
    ]


def plot_status_bar(status_df: pd.DataFrame, title: str | None = None):
    import matplotlib.pyplot as plt

    ordered = status_df.iloc[::-1].copy()
    colors = [rank_color(rank) for rank in ordered["rank"]]
    x_limit = get_composition_axis_limit(ordered["share_%"].values)

    fig, ax = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor(CYBER_BG)
    ax.set_facecolor(CYBER_PANEL)

    bars = ax.barh(
        ordered["parameter"].astype(str),
        ordered["share_%"],
        color=colors,
    )

    for bar, rank, score in zip(bars, ordered["rank"], ordered["share_%"]):
        width = bar.get_width()
        ax.text(
            width + (x_limit * 0.015),
            bar.get_y() + bar.get_height() / 2,
            f"{score:.1f}%   {rank}",
            va="center",
            fontsize=10,
            color=CYBER_TEXT,
            fontweight="bold",
        )

    ax.set_xlim(0, x_limit)
    chart_title = f"{title} - Thought Composition" if title else "Thought Composition"
    ax.set_title(chart_title, fontsize=16, pad=15, fontweight="bold", color=CYBER_TEXT)
    ax.set_xlabel("Thought share (%)", color=CYBER_MUTED)
    ax.tick_params(colors=CYBER_MUTED)
    ax.grid(axis="x", color=CYBER_GRID, alpha=0.38)
    for spine in ax.spines.values():
        spine.set_color(CYBER_GRID)
        spine.set_alpha(0.65)
    fig.tight_layout()
    return fig


def plot_status_pie(status_df: pd.DataFrame):
    import matplotlib.pyplot as plt

    positive = status_df[status_df["share_%"] > 0].sort_values("share_%", ascending=False).copy()
    if positive.empty:
        return None

    colors = [rank_color(rank) for rank in positive["rank"]]

    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor(CYBER_BG)
    ax.set_facecolor(CYBER_PANEL)
    wedges, texts, autotexts = ax.pie(
        positive["share_%"],
        labels=positive["parameter"].astype(str),
        colors=colors,
        startangle=90,
        counterclock=False,
        autopct="%1.1f%%",
        pctdistance=0.72,
        labeldistance=1.08,
        wedgeprops={
            "edgecolor": CYBER_BG,
            "linewidth": 1.2,
            "alpha": 0.92,
        },
        textprops={"color": CYBER_TEXT, "fontsize": 9},
    )

    for text in texts:
        text.set_color(CYBER_MUTED)
    for text in autotexts:
        text.set_color(CYBER_BG)
        text.set_fontweight("bold")

    ax.set_title("Thought Composition Pie", color=CYBER_TEXT, fontweight="bold")
    ax.axis("equal")
    fig.tight_layout()
    return fig


def plot_status_radar(status_df: pd.DataFrame):
    import matplotlib.pyplot as plt

    labels = status_df["parameter"].astype(str).tolist()
    values = status_df["share_%"].tolist()
    y_limit = get_composition_axis_limit(values)

    if len(labels) < 3:
        fig, ax = plt.subplots(figsize=(8, 4))
        fig.patch.set_facecolor(CYBER_BG)
        ax.set_facecolor(CYBER_PANEL)
        ax.text(0.5, 0.5, "Radar chart needs at least 3 parameters.", ha="center", va="center", color=CYBER_TEXT)
        ax.axis("off")
        return fig

    angles = [2 * math.pi * i / len(labels) for i in range(len(labels))]
    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    fig = plt.figure(figsize=(7, 7))
    fig.patch.set_facecolor(CYBER_BG)
    ax = fig.add_subplot(111, polar=True)
    ax.set_facecolor(CYBER_PANEL)

    ax.plot(angles_closed, values_closed, linewidth=2.4, color=CYBER_CYAN)
    ax.fill(angles_closed, values_closed, alpha=0.24, color=CYBER_VIOLET)

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color=CYBER_TEXT)
    ax.set_ylim(0, y_limit)

    tick_step = 5 if y_limit <= 30 else 10
    ticks = list(range(0, y_limit + 1, tick_step))
    ax.set_yticks(ticks)
    ax.set_yticklabels([f"{tick}%" for tick in ticks], color=CYBER_MUTED)
    ax.tick_params(colors=CYBER_MUTED)
    ax.grid(color=CYBER_GRID, alpha=0.45)
    ax.spines["polar"].set_color(CYBER_GRID)
    ax.set_title("Thought Composition Radar", pad=20, color=CYBER_TEXT, fontweight="bold")

    fig.tight_layout()
    return fig


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
    st.caption("Start with a query. Open Advanced Search Settings only when you need embedding or filter controls.")
    st.markdown("---")
    st.markdown("**Flow**")
    st.caption("Search -> Best Match -> Detail -> Thought Profile")


if "search_mode_choice" not in st.session_state:
    st.session_state["search_mode_choice"] = "Keyword search"


q = ""
email = ""
target_doc_id = ""
works = []
selected = {}
search_mode = st.session_state["search_mode_choice"]
top = 10
source = "all"
category = "all"
filter_name = "general"

st.markdown(
    """
    <div class="tm-shell tm-console">
        <div class="tm-title">Search Console</div>
        <div class="tm-desc">Enter a thought, author, title, or theme. Advanced controls stay tucked away until you need them.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if search_mode == "Keyword search":
    q = st.text_input(
        "Search ThoughtMap",
        value="Plato",
        help="Searches author, title, source, category, tags, and notes.",
    )
elif search_mode == "Hybrid":
    q = st.text_input(
        "Search ThoughtMap",
        value="",
        placeholder="Optional keyword filter: Plato / love / war / technology",
    )
else:
    st.info("Embedding similarity searches from a selected Personal Library work. Open Advanced Search Settings to choose the target.")

with st.expander("Advanced Search Settings", expanded=False):
    search_mode = st.radio(
        "Search mode",
        ["Keyword search", "Embedding similarity", "Hybrid"],
        index=["Keyword search", "Embedding similarity", "Hybrid"].index(search_mode),
        key="search_mode_choice",
    )

    top = st.slider("Top results", 1, 50, 10)
    source = st.text_input("Source filter", value="all")
    category = st.text_input("Category filter", value="all")
    filter_name = st.selectbox("Parameter filter", ["general"])

    if search_mode != "Keyword search":
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

search_clicked = st.button("Search", type="primary")


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
        with st.spinner("Searching ThoughtMap..."):
            data, elapsed, url = call_api(params)

        st.session_state["last_data"] = data
        st.session_state["last_results"] = data.get("results", [])
        st.session_state["last_url"] = url
        st.session_state["last_elapsed"] = elapsed
        st.session_state["last_mode"] = search_mode
        st.session_state["selected_result_index"] = 0

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
    st.success(f"{len(results)} result(s) found / {elapsed:.2f}s")

    if not results:
        st.info("No results.")

    else:
        df = result_frame(results)
        selected_index = clamp_result_index(results)
        st.session_state["selected_result_index"] = selected_index
        selected_result = results[selected_index]
        best_result = results[0]
        best_match_text = match_label(best_result.get("similarity", best_result.get("score", 0)))
        selected_match_text = match_label(selected_result.get("similarity", selected_result.get("score", 0)))

        st.markdown('<div class="tm-section-heading">Best Match</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="tm-best-card">
                <div class="tm-match-label">{html.escape(best_match_text)}</div>
                <div class="tm-result-title" style="font-size:1.35rem;">{html.escape(str(best_result.get('title') or 'Untitled'))}</div>
                <div class="tm-result-meta">{html.escape(str(best_result.get('author') or 'Unknown'))} | {html.escape(str(best_result.get('source') or 'unknown'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if best_result.get("url"):
            render_open_link("Open source", str(best_result.get("url")))

        if selected_index != 0:
            if st.button("Return to Best Match"):
                st.session_state["selected_result_index"] = 0
                rerun_app()

        st.markdown('<div class="tm-section-heading">Selected Work Detail</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="tm-shell">
                <div class="tm-match-label">{html.escape(selected_match_text)}</div>
                <div class="tm-result-title" style="font-size:1.25rem;">{html.escape(str(selected_result.get('title') or 'Untitled'))}</div>
                <div class="tm-result-meta">{html.escape(str(selected_result.get('author') or 'Unknown'))} | {html.escape(str(selected_result.get('source') or 'unknown'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if selected_result.get("url"):
            render_open_link("Open selected source", str(selected_result.get("url")))

        with st.expander("Advanced Details", expanded=False):
            st.write(f"doc_id: `{selected_result.get('doc_id', '')}`")
            st.write(
                "raw similarity:",
                f"{float(selected_result.get('similarity', selected_result.get('score', 0))):.6f}",
            )
            st.json(selected_result)

        st.markdown('<div class="tm-section-heading">Thought Profile</div>', unsafe_allow_html=True)
        result_params = parse_parameter_value(selected_result.get("parameters"))
        if not result_params:
            result_params = normalize_parameter_rows(selected_result)

        status_df = pd.DataFrame()
        if result_params:
            status_df = make_status_profile_from_parameters(result_params)

            st.markdown("**Top Slots**")
            for label, share in get_top_composition_groups(status_df):
                st.markdown(
                    f"""
                    <div class="tm-rank-card">
                        <div class="tm-rank-name">{html.escape(str(label))}</div>
                        <div class="tm-rank-value">{share:.1f}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with st.expander("Detailed Parameter Data", expanded=False):
                detailed_df = status_df.copy()
                detailed_df["parameter"] = detailed_df["parameter"].map(display_parameter_name)
                st.dataframe(detailed_df, use_container_width=True, hide_index=True)

            st.markdown('<div class="tm-section-heading">Main Graph</div>', unsafe_allow_html=True)
            st.pyplot(
                plot_status_bar(
                    status_df,
                    title=str(selected_result.get("title", "Selected Work")),
                ),
                use_container_width=True,
            )
        else:
            st.info("No Thought Profile data was returned for this result.")
            available_keys = [key for key in PARAMETER_KEYS if key in selected_result]
            if available_keys:
                st.caption(f"Parameter-like keys exist but had no numeric values: {', '.join(available_keys)}")
            else:
                st.caption("API response has no parameter-like keys for this result.")

        with st.expander("Similar Works", expanded=False):
            similar_df = df.iloc[1:].copy()
            if similar_df.empty:
                st.info("No additional similar works.")
            else:
                show_all = st.checkbox("Show all similar works", value=False)
                visible_df = similar_df if show_all else similar_df.head(3)

                for _, row in visible_df.iterrows():
                    source_text = row.get("source", "") or "unknown"
                    author_text = row.get("author", "") or "Unknown"
                    result_index = int(row["index"])
                    st.markdown(
                        f"""
                        <div class="tm-result-card">
                            <div class="tm-result-title">{result_index + 1}. {html.escape(str(row['title'] or 'Untitled'))}</div>
                            <div class="tm-result-meta">{html.escape(str(author_text))} | {html.escape(str(source_text))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button("View Details", key=f"view_result_{result_index}"):
                        st.session_state["selected_result_index"] = result_index
                        rerun_app()

                with st.expander("Raw Similar Works Table", expanded=False):
                    st.dataframe(df, use_container_width=True, hide_index=True)

        adf = author_frame(df)
        with st.expander("Similar Authors", expanded=False):
            if adf.empty:
                st.info("No author summary.")
            else:
                top_authors = adf.head(3)
                for _, row in top_authors.iterrows():
                    st.markdown(
                        f"""
                        <div class="tm-result-card">
                            <div class="tm-result-title">{html.escape(str(row['author']))}</div>
                            <div class="tm-result-meta">{int(row['works'])} related work(s)</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with st.expander("Raw Similar Authors Table", expanded=False):
                    st.dataframe(adf, use_container_width=True, hide_index=True)

        with st.expander("Advanced Analysis", expanded=False):
            if status_df.empty:
                st.info("No additional Thought Profile charts.")
            else:
                st.markdown("**Composition Pie**")
                pie_fig = plot_status_pie(status_df)
                if pie_fig is not None:
                    st.pyplot(pie_fig, use_container_width=True)
                else:
                    st.caption("Pie chart needs at least one parameter share above 0.")

                st.markdown("**Radar Field**")
                st.pyplot(plot_status_radar(status_df), use_container_width=True)

        with st.expander("Export Data", expanded=False):
            st.download_button(
                "Download similar works CSV",
                df.to_csv(index=False).encode("utf-8-sig"),
                file_name="thoughtmap_search_results.csv",
                mime="text/csv",
            )

            if adf.empty:
                st.caption("Similar authors CSV is unavailable because no author summary was found.")
            else:
                st.download_button(
                    "Download similar authors CSV",
                    adf.to_csv(index=False).encode("utf-8-sig"),
                    file_name="thoughtmap_similar_authors.csv",
                    mime="text/csv",
                )


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
