"""Object key naming, media classification, content types and public URLs."""

from __future__ import annotations

import posixpath
import re
import unicodedata
from pathlib import Path, PurePosixPath
from urllib.parse import quote

VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".wmv", ".mpg", ".mpeg", ".ts", ".m2ts"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".aif", ".aiff", ".wma"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}

CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/x-m4v",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
    ".avi": "video/x-msvideo",
    ".wmv": "video/x-ms-wmv",
    ".mpg": "video/mpeg",
    ".mpeg": "video/mpeg",
    ".ts": "video/mp2t",
    ".m2ts": "video/mp2t",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/opus",
    ".aif": "audio/aiff",
    ".aiff": "audio/aiff",
    ".wma": "audio/x-ms-wma",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".json": "application/json",
    ".zip": "application/zip",
}

CATEGORY_LABELS = {"mv": "MV", "bgm": "BGM", "thumbnail": "サムネイル", "other": "その他"}

IGNORED_NAMES = {"desktop.ini", "thumbs.db", ".ds_store", "ehthumbs.db"}

MAX_KEY_BYTES = 1024


def classify(path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    if ext in VIDEO_EXTS:
        return "mv"
    if ext in AUDIO_EXTS:
        return "bgm"
    return "other"


def content_type_for(path: str | Path) -> str:
    return CONTENT_TYPES.get(Path(path).suffix.lower(), "application/octet-stream")


def normalize_prefix(prefix: str) -> str:
    """'\\MV\\2026' → 'MV/2026/', '' → '' (bucket root)."""
    p = unicodedata.normalize("NFC", (prefix or "").strip()).replace("\\", "/")
    parts = [seg for seg in p.split("/") if seg not in ("", ".")]
    if any(seg == ".." for seg in parts):
        raise ValueError("保存先に '..' は使えません")
    return ("/".join(parts) + "/") if parts else ""


def _clean_segment(seg: str) -> str:
    seg = unicodedata.normalize("NFC", seg)
    seg = "".join(ch for ch in seg if unicodedata.category(ch)[0] != "C")
    return seg.strip()


def build_key(prefix: str, filename: str, subdirs: tuple[str, ...] = ()) -> str:
    parts = [_clean_segment(s) for s in (*subdirs, filename)]
    parts = [p for p in parts if p and p not in (".", "..")]
    if not parts:
        raise ValueError("ファイル名が空です")
    key = normalize_prefix(prefix) + "/".join(parts)
    validate_key(key)
    return key


def validate_key(key: str) -> None:
    if not key or key.endswith("/"):
        raise ValueError("キーが空、またはフォルダ名で終わっています")
    if key.startswith("/"):
        raise ValueError("キーは '/' で始められません")
    if len(key.encode("utf-8")) > MAX_KEY_BYTES:
        raise ValueError("キーが長すぎます（1024バイト以内）")
    if any(seg in ("..", ".") for seg in key.split("/")):
        raise ValueError("キーに '.' や '..' のフォルダは使えません")


def rename_candidate(key: str, taken) -> str:
    """'mv/Song.mp4' → 'mv/Song (2).mp4', skipping anything in *taken* (a container or callable)."""
    exists = taken if callable(taken) else (lambda k: k in taken)
    head, tail = posixpath.split(key)
    stem, ext = posixpath.splitext(tail)
    m = re.match(r"^(.*) \((\d+)\)$", stem)
    base, n = (m.group(1), int(m.group(2))) if m else (stem, 1)
    while True:
        n += 1
        cand = posixpath.join(head, f"{base} ({n}){ext}") if head else f"{base} ({n}){ext}"
        if not exists(cand):
            return cand


def public_url(base_url: str, key: str) -> str:
    return base_url.rstrip("/") + "/" + quote(key, safe="/")


def slugify(text: str, fallback: str = "") -> str:
    norm = unicodedata.normalize("NFKD", text)
    ascii_only = norm.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or fallback


def title_from_filename(name: str) -> str:
    stem = PurePosixPath(name.replace("\\", "/")).stem
    return re.sub(r"[_]+", " ", stem).strip() or stem


def format_bytes(n: float | int | None) -> str:
    if n is None:
        return "—"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} TB"


def format_duration(seconds: float | None) -> str:
    """Seconds → 'm:ss' (or 'h:mm:ss'), the style used by the archive's durationText."""
    if seconds is None:
        return "—"
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def iso8601_duration(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    out = "PT"
    if h:
        out += f"{h}H"
    if m:
        out += f"{m}M"
    if s or out == "PT":
        out += f"{s}S"
    return out


def format_eta(seconds: float | None) -> str:
    if seconds is None or seconds != seconds or seconds == float("inf"):
        return "—"
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}時間{m:02d}分"
    if m:
        return f"{m}分{s:02d}秒"
    return f"{s}秒"


def format_rate(bps: float | None) -> str:
    if not bps:
        return "—"
    return format_bytes(bps) + "/s"
