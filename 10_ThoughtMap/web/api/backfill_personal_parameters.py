from __future__ import annotations

import argparse
import json
import os
from typing import Sequence

import numpy as np
from sqlalchemy import create_engine, select, update

from .config import normalize_database_url
from .personal_repository import THOUGHT_PARAMETER_KEYS, email_hash_for, normalize_parameters
from .postgres_personal_repository import saved_embeddings, saved_works, users


MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
PARAMETER_PROMPTS = {
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill missing Source of Thought parameters for saved personal works."
    )
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--email", default="", help="Optional normalized email to limit the update.")
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--apply", action="store_true", help="Write updates. Default is dry-run.")
    args = parser.parse_args()

    database_url = normalize_database_url(args.database_url)
    if not database_url:
        raise RuntimeError("DATABASE_URL is required.")

    model = _load_model(args.model_name)
    prompt_embeddings = model.encode(
        [PARAMETER_PROMPTS[key] for key in THOUGHT_PARAMETER_KEYS],
        show_progress_bar=False,
    )

    engine = create_engine(database_url, pool_pre_ping=True)
    rows = _load_target_rows(engine, args.email)
    print(f"Found {len(rows)} saved works with embeddings.")

    updates = []
    for row in rows:
        existing = normalize_parameters(row.parameters_json)
        if existing and len([item for item in existing if item["key"] in THOUGHT_PARAMETER_KEYS]) == 10:
            continue
        embedding = _parse_embedding(row.embedding_json)
        if embedding is None:
            print(f"Skip doc_id={row.doc_id}: embedding is missing or invalid.")
            continue
        parameters = _score_parameters(embedding, prompt_embeddings)
        updates.append((row.work_id, row.doc_id, parameters))

    print(f"Backfill candidates: {len(updates)}")
    for _work_id, doc_id, parameters in updates[:10]:
        print(f"  {doc_id}: {parameters}")

    if not args.apply:
        print("Dry run only. Pass --apply to update saved_works.parameters_json.")
        return

    with engine.begin() as conn:
        for work_id, _doc_id, parameters in updates:
            conn.execute(
                update(saved_works)
                .where(saved_works.c.id == work_id)
                .values(parameters_json=parameters)
            )
    print(f"Updated {len(updates)} saved works.")


def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        raise RuntimeError(
            "sentence-transformers is required for local parameter backfill. "
            f"Import failed: {exc}"
        ) from exc
    return SentenceTransformer(model_name)


def _load_target_rows(engine, email: str):
    stmt = (
        select(
            saved_works.c.id.label("work_id"),
            saved_works.c.doc_id,
            saved_works.c.parameters_json,
            saved_embeddings.c.embedding_json,
        )
        .select_from(
            saved_works.join(users, saved_works.c.user_id == users.c.id).join(
                saved_embeddings,
                (saved_embeddings.c.user_id == saved_works.c.user_id)
                & (saved_embeddings.c.doc_id == saved_works.c.doc_id),
            )
        )
        .order_by(saved_works.c.created_at.asc())
    )
    if email:
        stmt = stmt.where(users.c.email_hash == email_hash_for(email))
    with engine.begin() as conn:
        return list(conn.execute(stmt))


def _parse_embedding(value: object) -> np.ndarray | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if array.ndim != 1 or array.size == 0:
        return None
    return array


def _score_parameters(
    embedding: np.ndarray,
    prompt_embeddings: Sequence[Sequence[float]],
) -> list[dict[str, object]]:
    prompt_array = np.asarray(prompt_embeddings, dtype=float)
    if prompt_array.ndim != 2 or prompt_array.shape[1] != embedding.size:
        raise ValueError(
            f"Embedding dimension mismatch: document={embedding.size} prompts={prompt_array.shape}"
        )
    scores = []
    for key, prompt_embedding in zip(THOUGHT_PARAMETER_KEYS, prompt_array):
        score = _cosine(embedding, prompt_embedding)
        scores.append({"key": key, "value": float(max(0.0, score) * 100.0)})
    return scores


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denom = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denom == 0.0:
        return 0.0
    return float(np.dot(left, right) / denom)


if __name__ == "__main__":
    main()
