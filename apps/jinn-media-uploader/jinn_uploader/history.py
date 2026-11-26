"""Local upload history (SQLite) and multipart resume state (JSON files)."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sqlite3
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uploaded_at TEXT NOT NULL,
    bucket TEXT NOT NULL,
    key TEXT NOT NULL,
    public_url TEXT,
    local_path TEXT,
    category TEXT,
    size INTEGER,
    sha256 TEXT,
    source_sha256 TEXT,
    md5 TEXT,
    etag TEXT,
    content_type TEXT,
    duration REAL,
    width INTEGER,
    height INTEGER,
    video_codec TEXT,
    audio_codec TEXT,
    thumb_key TEXT,
    poster_key TEXT,
    thumb_local TEXT,
    poster_local TEXT,
    compression TEXT,
    overwrote INTEGER DEFAULT 0,
    class_a_ops INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_uploads_sha ON uploads(sha256);
CREATE INDEX IF NOT EXISTS idx_uploads_src_sha ON uploads(source_sha256);
CREATE INDEX IF NOT EXISTS idx_uploads_key ON uploads(bucket, key);
"""

COLUMNS = (
    "uploaded_at", "bucket", "key", "public_url", "local_path", "category", "size", "sha256",
    "source_sha256", "md5", "etag", "content_type", "duration", "width", "height", "video_codec",
    "audio_codec", "thumb_key", "poster_key", "thumb_local", "poster_local", "compression", "overwrote",
    "class_a_ops",
)


class History:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(SCHEMA)

    @contextlib.contextmanager
    def _connect(self):
        """Open, commit and always close (an open handle would lock the file on Windows)."""
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def record(self, **values) -> int:
        values.setdefault("uploaded_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        cols = [c for c in COLUMNS if c in values]
        with self._lock, self._connect() as db:
            cur = db.execute(
                f"INSERT INTO uploads ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                [values[c] for c in cols],
            )
            return int(cur.lastrowid)

    def find_by_hash(self, bucket: str, sha256: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM uploads WHERE bucket=? AND (sha256=? OR source_sha256=?) ORDER BY id DESC",
                (bucket, sha256, sha256),
            ).fetchall()
        return [dict(r) for r in rows]

    def latest_for_key(self, bucket: str, key: str) -> dict | None:
        with self._connect() as db:
            r = db.execute(
                "SELECT * FROM uploads WHERE bucket=? AND key=? ORDER BY id DESC LIMIT 1", (bucket, key)
            ).fetchone()
        return dict(r) if r else None

    def recent(self, bucket: str, limit: int = 500) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM uploads WHERE bucket=? ORDER BY id DESC LIMIT ?", (bucket, limit)
            ).fetchall()
        return [dict(r) for r in rows]

    def class_a_ops_this_month(self, bucket: str) -> int:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        with self._connect() as db:
            r = db.execute(
                "SELECT COALESCE(SUM(class_a_ops),0) FROM uploads WHERE bucket=? AND substr(uploaded_at,1,7)=?",
                (bucket, month),
            ).fetchone()
        return int(r[0])


@dataclass
class ResumeState:
    bucket: str
    key: str
    upload_id: str
    source_path: str
    source_size: int
    source_mtime_ns: int
    part_size: int
    sha256: str
    content_type: str
    created_at: str
    parts: dict[str, str]  # part number (str) → ETag

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=1)


class ResumeStore:
    """Remembers in-flight multipart uploads so a pause, crash or failure can resume."""

    def __init__(self, directory: Path):
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _file(self, bucket: str, key: str, source_path: str) -> Path:
        h = hashlib.sha1(f"{bucket}\n{key}\n{os.path.normcase(source_path)}".encode("utf-8")).hexdigest()
        return self.dir / f"{h}.json"

    def load(self, bucket: str, key: str, source_path: str) -> ResumeState | None:
        f = self._file(bucket, key, source_path)
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            return ResumeState(**data)
        except (OSError, ValueError, TypeError):
            return None

    def save(self, state: ResumeState) -> None:
        f = self._file(state.bucket, state.key, state.source_path)
        with self._lock:
            fd, tmp = tempfile.mkstemp(dir=self.dir, prefix=".resume-", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(state.to_json())
            os.replace(tmp, f)

    def delete(self, bucket: str, key: str, source_path: str) -> None:
        with self._lock:
            self._file(bucket, key, source_path).unlink(missing_ok=True)

    def all(self) -> list[ResumeState]:
        out = []
        for f in sorted(self.dir.glob("*.json")):
            try:
                out.append(ResumeState(**json.loads(f.read_text(encoding="utf-8"))))
            except (OSError, ValueError, TypeError):
                continue
        return out
