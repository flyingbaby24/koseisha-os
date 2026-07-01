from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class ApiSettings:
    backend: str = "csv"
    db_dir: Path | None = None
    model_name: str = DEFAULT_MODEL_NAME
    allowed_origins: tuple[str, ...] = ("*",)


def get_settings() -> ApiSettings:
    db_dir_text = os.getenv("THOUGHTMAP_DB_DIR", "").strip()
    origins_text = os.getenv("THOUGHTMAP_ALLOWED_ORIGINS", "*")

    return ApiSettings(
        backend=os.getenv("THOUGHTMAP_BACKEND", "csv").strip().lower() or "csv",
        db_dir=Path(db_dir_text) if db_dir_text else None,
        model_name=os.getenv("THOUGHTMAP_MODEL_NAME", DEFAULT_MODEL_NAME),
        allowed_origins=tuple(_split_csv(origins_text) or ["*"]),
    )
