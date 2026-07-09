from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OFFICIAL_DB_DIR = BASE_DIR / "data" / "thoughtmap_db" / "official"
FALLBACK_OFFICIAL_DB_DIR = BASE_DIR / "master"
DEFAULT_USERS_DIR = BASE_DIR / "data" / "thoughtmap_db" / "users"
FALLBACK_USERS_DIR = BASE_DIR / "data" / "users"

DOCUMENT_REQUIRED_COLUMNS = {"doc_id"}
EMBEDDING_REQUIRED_COLUMNS = {"doc_id", "embedding"}
MAP_POINT_REQUIRED_COLUMNS = {"doc_id"}
PARAMETER_SCORE_REQUIRED_COLUMNS = {"doc_id"}


def _warn(message: str) -> None:
    print(f"[ThoughtMap storage] {message}")


def _read_csv(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    return pd.read_csv(path, dtype=str).fillna("")


def _warn_missing_columns(name: str, frame: pd.DataFrame, required: Iterable[str]) -> list[str]:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        _warn(f"{name} is missing required column(s): {', '.join(missing)}")
    return missing


def load_documents(path: str | Path) -> pd.DataFrame:
    documents = _read_csv(Path(path))
    _warn_missing_columns("documents", documents, DOCUMENT_REQUIRED_COLUMNS)
    return documents


def load_embeddings(path: str | Path) -> pd.DataFrame:
    embeddings = _read_csv(Path(path))

    if "model_name" not in embeddings.columns and "model" in embeddings.columns:
        embeddings = embeddings.copy()
        embeddings["model_name"] = embeddings["model"]
        _warn("embeddings uses 'model'; normalized it to 'model_name'.")

    if "model_name" not in embeddings.columns:
        embeddings = embeddings.copy()
        embeddings["model_name"] = ""
        _warn("embeddings has no 'model_name' or 'model'; added empty 'model_name'.")

    _warn_missing_columns("embeddings", embeddings, EMBEDDING_REQUIRED_COLUMNS)
    return embeddings


def load_map_points(path: str | Path) -> pd.DataFrame:
    map_points = _read_csv(Path(path))
    _warn_missing_columns("map_points", map_points, MAP_POINT_REQUIRED_COLUMNS)
    return map_points


def load_parameter_scores(path: str | Path) -> pd.DataFrame:
    parameter_scores = _read_csv(Path(path))
    _warn_missing_columns("parameter_scores", parameter_scores, PARAMETER_SCORE_REQUIRED_COLUMNS)
    return parameter_scores


def validate_db_frames(
    documents: pd.DataFrame,
    embeddings: pd.DataFrame,
    map_points: pd.DataFrame | None = None,
) -> list[str]:
    warnings: list[str] = []

    for name, frame, required in [
        ("documents", documents, DOCUMENT_REQUIRED_COLUMNS),
        ("embeddings", embeddings, EMBEDDING_REQUIRED_COLUMNS),
    ]:
        missing = _warn_missing_columns(name, frame, required)
        warnings.extend(f"{name}: missing {column}" for column in missing)

    if map_points is not None:
        missing = _warn_missing_columns("map_points", map_points, MAP_POINT_REQUIRED_COLUMNS)
        warnings.extend(f"map_points: missing {column}" for column in missing)

    if "doc_id" in documents.columns and documents["doc_id"].duplicated().any():
        count = int(documents["doc_id"].duplicated().sum())
        message = f"documents has {count} duplicate doc_id value(s)."
        _warn(message)
        warnings.append(message)

    if "doc_id" in documents.columns and "doc_id" in embeddings.columns:
        document_ids = set(documents["doc_id"].astype(str))
        embedding_ids = set(embeddings["doc_id"].astype(str))
        missing_embeddings = document_ids - embedding_ids
        orphan_embeddings = embedding_ids - document_ids
        if missing_embeddings:
            message = f"{len(missing_embeddings)} document(s) have no embedding row."
            _warn(message)
            warnings.append(message)
        if orphan_embeddings:
            message = f"{len(orphan_embeddings)} embedding row(s) have no matching document."
            _warn(message)
            warnings.append(message)

    if map_points is not None and "doc_id" in documents.columns and "doc_id" in map_points.columns:
        document_ids = set(documents["doc_id"].astype(str))
        map_ids = set(map_points["doc_id"].astype(str))
        orphan_points = map_ids - document_ids
        if orphan_points:
            message = f"{len(orphan_points)} map point row(s) have no matching document."
            _warn(message)
            warnings.append(message)

    return warnings


def _normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def resolve_db_dir(db_dir_text: str) -> Path:
    db_dir = Path(db_dir_text)

    if db_dir.is_absolute() and db_dir.exists():
        return db_dir

    repo_path = BASE_DIR / db_dir
    if repo_path.exists():
        return repo_path

    if DEFAULT_OFFICIAL_DB_DIR.exists():
        return DEFAULT_OFFICIAL_DB_DIR

    if FALLBACK_OFFICIAL_DB_DIR.exists():
        return FALLBACK_OFFICIAL_DB_DIR

    return repo_path




def resolve_users_dir(users_dir_text: str) -> Path:
    users_dir = Path(users_dir_text)

    if users_dir.is_absolute() and users_dir.exists():
        return users_dir

    repo_path = BASE_DIR / users_dir
    if repo_path.exists():
        return repo_path

    if DEFAULT_USERS_DIR.exists():
        return DEFAULT_USERS_DIR

    if FALLBACK_USERS_DIR.exists():
        return FALLBACK_USERS_DIR

    return repo_path


def list_user_libraries(users_dir: Path) -> pd.DataFrame:
    index_path = users_dir / "index.csv"
    if index_path.exists():
        try:
            idx = pd.read_csv(index_path, dtype=str).fillna("")
            if "user_id" in idx.columns:
                rows = []
                for _, r in idx.iterrows():
                    user_id = _normalize_text(r.get("user_id", ""))
                    if not user_id:
                        continue
                    user_dir = users_dir / user_id
                    if user_dir.exists():
                        rows.append({
                            "user_id": user_id,
                            "display_name": _normalize_text(r.get("display_name", "")) or user_id,
                            "email_masked": _normalize_text(r.get("email_masked", "")),
                            "user_dir": str(user_dir),
                        })
                if rows:
                    return pd.DataFrame(rows)
        except Exception:
            pass

    rows = []
    if users_dir.exists():
        for p in sorted(users_dir.iterdir()):
            if not p.is_dir():
                continue
            profile_path = p / "profile.json"
            display_name = p.name
            email_masked = ""
            if profile_path.exists():
                try:
                    profile = json.loads(profile_path.read_text(encoding="utf-8"))
                    display_name = _normalize_text(profile.get("display_name", "")) or display_name
                    email_masked = _normalize_text(profile.get("email_masked", ""))
                except Exception:
                    pass
            rows.append({
                "user_id": p.name,
                "display_name": display_name,
                "email_masked": email_masked,
                "user_dir": str(p),
            })
    return pd.DataFrame(rows)


def resolve_user_db_dir(users_dir_text: str, user_id: str) -> Path:
    users_dir = resolve_users_dir(users_dir_text)
    return users_dir / user_id



def load_official_db(db_dir: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    db_path = Path(db_dir) if db_dir is not None else DEFAULT_OFFICIAL_DB_DIR
    documents = load_documents(db_path / "documents_master.csv")
    embeddings = load_embeddings(db_path / "embeddings_master.csv")

    map_points_path = db_path / "map_points_latest.csv"
    map_points = load_map_points(map_points_path) if map_points_path.exists() else None

    validate_db_frames(documents, embeddings, map_points)
    return documents, embeddings, map_points


def load_official_parameter_scores(db_dir: str | Path | None = None) -> pd.DataFrame | None:
    db_path = Path(db_dir) if db_dir is not None else DEFAULT_OFFICIAL_DB_DIR
    parameter_scores_path = db_path / "parameter_scores.csv"
    if not parameter_scores_path.exists():
        return None
    return load_parameter_scores(parameter_scores_path)


def load_user_db(
    user_id: str,
    users_dir: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    users_path = Path(users_dir) if users_dir is not None else DEFAULT_USERS_DIR
    db_path = users_path / user_id

    documents = load_documents(db_path / "documents.csv")
    embeddings = load_embeddings(db_path / "embeddings.csv")

    map_points_path = db_path / "map_points.csv"
    map_points = load_map_points(map_points_path) if map_points_path.exists() else None

    validate_db_frames(documents, embeddings, map_points)
    return documents, embeddings, map_points
