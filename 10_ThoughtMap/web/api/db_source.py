from __future__ import annotations

import os
import sqlite3
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable


DownloadFunction = Callable[[str, Path], None]


def _download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=300) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)


def validate_sqlite(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        result = connection.execute("PRAGMA quick_check").fetchone()
        if not result or result[0] != "ok":
            raise ValueError(f"Downloaded SQLite failed integrity check: {path}")
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"documents", "embeddings"}.issubset(tables):
            raise ValueError("Downloaded SQLite is missing documents or embeddings table.")


class OfficialDatabaseSource:
    """Place an official SQLite file locally; repository code only reads it."""

    def __init__(self, path: Path, url: str = "", downloader: DownloadFunction = _download) -> None:
        self.path = Path(path)
        self.url = str(url or "").strip()
        self.downloader = downloader

    def ensure_local(self) -> Path:
        if self.path.exists():
            return self.path
        if not self.url:
            raise FileNotFoundError(
                f"Official SQLite not found: {self.path}. Set THOUGHTMAP_OFFICIAL_DB_PATH "
                "or a direct file URL in THOUGHTMAP_OFFICIAL_DB_URL."
            )

        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent)
        os.close(fd)
        temporary = Path(temp_name)
        try:
            self.downloader(self.url, temporary)
            validate_sqlite(temporary)
            os.replace(temporary, self.path)
        except Exception:
            temporary.unlink(missing_ok=True)
            # Another process may have populated a valid cache concurrently.
            if self.path.exists():
                return self.path
            raise
        return self.path
