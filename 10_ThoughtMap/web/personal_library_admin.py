from __future__ import annotations

import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import streamlit as st


DEFAULT_FASTAPI_BASE_URL = "https://koseisha-os.onrender.com"
DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
THOUGHT_PARAMETER_KEYS = [
    "philosophy",
    "psychology",
    "science",
    "economy",
    "karma",
    "emotion",
    "morality",
    "ideology",
    "individual",
    "community",
]
THOUGHT_PARAMETER_PROMPTS = {
    "philosophy": "truth, existence, meaning, reality, wisdom, being, knowledge",
    "psychology": "mind, emotion, memory, desire, behavior, motivation",
    "science": "science, logic, experiment, evidence, observation, theory",
    "economy": "economy, exchange, value, labor, market, resource, wealth",
    "karma": "karma, consequence, fate, cause, responsibility, return",
    "emotion": "emotion, feeling, passion, grief, joy, anger, empathy",
    "morality": "morality, ethics, justice, virtue, duty, good, evil",
    "ideology": "ideal, ideology, belief, vision, principle, hope, purpose",
    "individual": "individual, self, identity, agency, solitude, personal life",
    "community": "community, society, relation, cooperation, family, collective",
}


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
    clean_path = str(path or "").strip()
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path
    return normalize_api_base_url(api_base_url) + clean_path


def render_personal_library_admin(
    *,
    api_base_url: str,
    email: str,
    timeout_seconds: int = 90,
    key_prefix: str = "personal_admin",
) -> None:
    email = str(email or "").strip()
    if not email:
        st.info("Enter a registered email to manage the Personal Library.")
        return

    notice_key = f"{key_prefix}_notice"
    if notice_key in st.session_state:
        notice = st.session_state.pop(notice_key)
        level = notice.get("level", "info")
        message = notice.get("message", "")
        if level == "success":
            st.success(message)
        elif level == "error":
            st.error(message)
        else:
            st.info(message)

    load_result = get_saved_documents_by_email(api_base_url, email, timeout_seconds)
    if not load_result.get("ok"):
        st.warning("Could not load Personal Library management data.")
        with st.expander("Personal Library management debug"):
            st.write({key: value for key, value in load_result.items() if key != "works"})
        return

    works = list(load_result.get("works") or [])
    if not works:
        st.info("Personal Library is empty.")
        return

    rows = []
    work_by_doc_id: dict[str, dict] = {}
    for work in works:
        doc_id = str(work.get("doc_id", "") or "")
        if not doc_id:
            continue
        work_by_doc_id[doc_id] = work
        parameters = work.get("parameters") if isinstance(work.get("parameters"), list) else []
        rows.append({
            "select": False,
            "doc_id": doc_id,
            "title": work.get("title", ""),
            "author": work.get("author", ""),
            "source": work.get("source", ""),
            "category": work.get("category", ""),
            "parameters": len(parameters),
            "has_embedding": parse_embedding_value(work.get("embedding")) is not None,
            "saved_at": work.get("saved_at", ""),
        })

    if not rows:
        st.info("Personal Library has no manageable saved works.")
        return

    editor_df = pd.DataFrame(rows)
    edited = st.data_editor(
        editor_df,
        hide_index=True,
        use_container_width=True,
        key=f"{key_prefix}_editor",
        disabled=[col for col in editor_df.columns if col != "select"],
        column_config={
            "select": st.column_config.CheckboxColumn("Select"),
            "doc_id": st.column_config.TextColumn("doc_id", width="medium"),
            "title": st.column_config.TextColumn("Title", width="large"),
            "parameters": st.column_config.NumberColumn("Parameters"),
            "has_embedding": st.column_config.CheckboxColumn("Embedding"),
        },
    )
    selected_doc_ids = edited.loc[edited["select"], "doc_id"].astype(str).tolist()
    st.caption(f"Selected {len(selected_doc_ids)} work(s).")

    if not selected_doc_ids:
        st.caption("Select one or more rows to enable Delete Selected or Recalculate Parameters.")

    delete_col, recalc_col = st.columns(2)
    with delete_col:
        if st.button("Delete Selected", disabled=not selected_doc_ids, key=f"{key_prefix}_delete"):
            results = [
                delete_saved_document_by_email(api_base_url, email, doc_id, timeout_seconds)
                for doc_id in selected_doc_ids
            ]
            success_count = sum(1 for item in results if item.get("ok"))
            failure_count = len(results) - success_count
            st.session_state[notice_key] = {
                "level": "success" if failure_count == 0 else "error",
                "message": f"Deleted {success_count}, failed {failure_count}.",
            }
            st.session_state[f"{key_prefix}_last_delete_debug"] = results
            st.cache_data.clear()
            rerun_streamlit()

    with recalc_col:
        if st.button("Recalculate Parameters", disabled=not selected_doc_ids, key=f"{key_prefix}_recalc"):
            selected_works = [work_by_doc_id[doc_id] for doc_id in selected_doc_ids if doc_id in work_by_doc_id]
            results, skipped = recalculate_selected_parameters(
                api_base_url=api_base_url,
                email=email,
                works=selected_works,
                timeout_seconds=timeout_seconds,
            )
            success_count = sum(1 for item in results if item.get("ok"))
            failure_count = len(results) - success_count
            st.session_state[notice_key] = {
                "level": "success" if failure_count == 0 else "error",
                "message": f"Recalculated {success_count}, failed {failure_count}, skipped {len(skipped)}.",
            }
            st.session_state[f"{key_prefix}_last_recalculate_debug"] = {
                "updated": results,
                "skipped": skipped,
            }
            st.cache_data.clear()
            rerun_streamlit()

    with st.expander("Personal Library management debug"):
        st.write({
            "request_url": load_result.get("url"),
            "status_code": load_result.get("status_code"),
            "works": len(works),
            "selected": selected_doc_ids,
        })
        if f"{key_prefix}_last_delete_debug" in st.session_state:
            st.write({"last_delete": st.session_state[f"{key_prefix}_last_delete_debug"]})
        if f"{key_prefix}_last_recalculate_debug" in st.session_state:
            st.write({"last_recalculate": st.session_state[f"{key_prefix}_last_recalculate_debug"]})


def recalculate_selected_parameters(
    *,
    api_base_url: str,
    email: str,
    works: list[dict],
    timeout_seconds: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    embeddings = []
    valid_works = []
    skipped = []
    for work in works:
        embedding = parse_embedding_value(work.get("embedding"))
        if embedding is None:
            skipped.append({"doc_id": work.get("doc_id"), "reason": "missing embedding"})
            continue
        embeddings.append(embedding)
        valid_works.append(work)

    if not valid_works:
        return [], skipped

    parameter_rows = score_source_of_thought_parameters_for_embeddings(embeddings)
    results = []
    for work, parameters in zip(valid_works, parameter_rows):
        results.append(
            post_save_document_by_email(
                api_base_url=api_base_url,
                email=email,
                doc_id=str(work.get("doc_id", "")),
                title=str(work.get("title", "")),
                author=str(work.get("author", "")),
                source=str(work.get("source", "")),
                category=str(work.get("category", "")),
                url=str(work.get("url", "") or work.get("source_url", "") or ""),
                source_url=str(work.get("source_url", "") or work.get("url", "") or ""),
                original_doc_id=str(work.get("original_doc_id", "") or work.get("doc_id", "")),
                embedding=work.get("embedding"),
                model_name=str(work.get("model_name", "") or DEFAULT_MODEL_NAME),
                parameters=parameters,
                timeout_seconds=timeout_seconds,
            )
        )
    return results, skipped


def get_saved_documents_by_email(
    api_base_url: str,
    email: str,
    timeout_seconds: int,
) -> dict[str, object]:
    query = urlencode({"email": str(email or "").strip().lower()})
    url = build_api_url(api_base_url, f"/users/by-email/saved?{query}")
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload = json.loads(body) if body.strip() else {}
            works = payload.get("works") if isinstance(payload, dict) else None
            return {
                "ok": 200 <= int(response.status) < 300,
                "url": url,
                "status_code": int(response.status),
                "response_text": body[:2000],
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "works": works if isinstance(works, list) else [],
                "exception_type": "",
                "exception_message": "",
            }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "status_code": getattr(exc, "code", None),
            "response_text": read_error_body(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "works": [],
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }


def delete_saved_document_by_email(
    api_base_url: str,
    email: str,
    doc_id: str,
    timeout_seconds: int,
) -> dict[str, object]:
    query = urlencode({"email": str(email or "").strip().lower()})
    url = build_api_url(api_base_url, f"/users/by-email/saved/{quote(str(doc_id), safe='')}?{query}")
    request = Request(url, headers={"Accept": "application/json"}, method="DELETE")
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= int(response.status) < 300,
                "url": url,
                "doc_id": doc_id,
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
            "doc_id": doc_id,
            "status_code": getattr(exc, "code", None),
            "response_text": read_error_body(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }


def post_save_document_by_email(
    api_base_url: str,
    email: str,
    doc_id: str,
    title: str = "",
    author: str = "",
    source: str = "",
    category: str = "",
    url: str = "",
    source_url: str = "",
    original_doc_id: str = "",
    embedding=None,
    model_name: str = DEFAULT_MODEL_NAME,
    parameters=None,
    timeout_seconds: int = 90,
) -> dict[str, object]:
    request_url = build_api_url(api_base_url, "/users/by-email/save")
    payload = {
        "email": str(email or "").strip().lower(),
        "doc_id": str(doc_id or "").strip(),
        "title": str(title or doc_id or "").strip(),
        "author": str(author or "").strip(),
        "source": str(source or "personal").strip(),
        "category": str(category or "").strip(),
        "url": str(url or source_url or "").strip(),
        "source_url": str(source_url or url or "").strip(),
        "original_doc_id": str(original_doc_id or doc_id or "").strip(),
        "embedding": embedding,
        "model_name": str(model_name or DEFAULT_MODEL_NAME),
        "source_type": "upload",
        "parameters": parameters or [],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        request_url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= int(response.status) < 300,
                "url": request_url,
                "doc_id": doc_id,
                "status_code": int(response.status),
                "response_text": response_body,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "exception_type": "",
                "exception_message": "",
                "request_json": {k: v for k, v in payload.items() if k != "email"},
            }
    except Exception as exc:
        return {
            "ok": False,
            "url": request_url,
            "doc_id": doc_id,
            "status_code": getattr(exc, "code", None),
            "response_text": read_error_body(exc),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_json": {k: v for k, v in payload.items() if k != "email"},
        }


def parse_embedding_value(value: object) -> np.ndarray | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            try:
                value = [float(part) for part in re.split(r"[\s,]+", text) if part]
            except ValueError:
                return None
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if array.ndim != 1 or array.size == 0:
        return None
    return array


def score_source_of_thought_parameters_for_embeddings(
    embeddings: list[np.ndarray],
) -> list[list[dict[str, object]]]:
    model = load_sentence_transformer()
    prompt_embeddings = model.encode(
        [THOUGHT_PARAMETER_PROMPTS[key] for key in THOUGHT_PARAMETER_KEYS],
        show_progress_bar=False,
    )
    prompt_array = np.asarray(prompt_embeddings, dtype=float)
    scored_rows = []
    for embedding in embeddings:
        if prompt_array.ndim != 2 or prompt_array.shape[1] != embedding.size:
            raise ValueError(
                f"Embedding dimension mismatch: document={embedding.size}, prompts={prompt_array.shape}"
            )
        values = []
        for key, prompt_vec in zip(THOUGHT_PARAMETER_KEYS, prompt_array):
            denom = float(np.linalg.norm(embedding) * np.linalg.norm(prompt_vec))
            similarity = float(np.dot(embedding, prompt_vec) / denom) if denom else 0.0
            values.append({"key": key, "value": round(max(0.0, min(1.0, similarity)) * 100.0, 2)})
        scored_rows.append(values)
    return scored_rows


@st.cache_resource(show_spinner=False)
def load_sentence_transformer(model_name: str = DEFAULT_MODEL_NAME):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def read_error_body(exc: BaseException) -> str:
    if isinstance(exc, HTTPError):
        try:
            return exc.read().decode("utf-8", errors="replace")
        except Exception:
            return str(exc)
    if isinstance(exc, URLError):
        return str(getattr(exc, "reason", exc))
    return str(exc)


def rerun_streamlit() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    if hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
