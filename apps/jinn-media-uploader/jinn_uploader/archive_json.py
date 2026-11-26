"""Infinite Archive registration JSON.

``works`` entries mirror the objects the archive embeds in its ``#x-data`` script
(id, slug, title, artist, w, h, durationText, thumb, poster, video, page,
description, lyrics) and add the fields its VideoObject JSON-LD and library cards
use (uploadDate, duration, encodingFormat, category, genre, themes, year).
BGM goes to ``tracks`` for the soundscape playlist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .keys import format_duration, iso8601_duration, public_url, slugify, title_from_filename


@dataclass
class ArchiveItem:
    category: str  # "mv" | "bgm"
    key: str
    title: str
    slug: str
    number: int
    artist: str = "Jinn Project"
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    content_type: str | None = None
    size: int | None = None
    sha256: str | None = None
    thumb_key: str | None = None
    poster_key: str | None = None
    thumb_local: str | None = None
    poster_local: str | None = None
    uploaded_at: str | None = None
    description: str | None = None
    lyrics: str | None = None
    genre: str = ""
    themes: list[str] = field(default_factory=list)
    year: str = ""

    @classmethod
    def from_history(cls, row: dict, number: int, artist: str) -> "ArchiveItem":
        title = title_from_filename(Path(row.get("local_path") or row["key"]).name)
        return cls(
            category="bgm" if row.get("category") == "bgm" else "mv",
            key=row["key"],
            title=title,
            slug=slugify(title, fallback=f"{'bgm' if row.get('category') == 'bgm' else 'mv'}-{number:04d}"),
            number=number,
            artist=artist,
            width=row.get("width"),
            height=row.get("height"),
            duration=row.get("duration"),
            content_type=row.get("content_type"),
            size=row.get("size"),
            sha256=row.get("sha256"),
            thumb_key=row.get("thumb_key"),
            poster_key=row.get("poster_key"),
            thumb_local=row.get("thumb_local"),
            poster_local=row.get("poster_local"),
            uploaded_at=row.get("uploaded_at"),
            year=(row.get("uploaded_at") or "")[:4],
        )


def _asset_url(base_url: str, key: str | None, local: str | None, slug: str, suffix: str) -> str | None:
    if key:
        return public_url(base_url, key)
    if local:
        # Not uploaded: point at the site's own /thumbnails/ folder, where the file can be copied.
        return f"/thumbnails/{Path(local).name}"
    return None


def work_entry(item: ArchiveItem, base_url: str) -> dict:
    upload_date = (item.uploaded_at or datetime.now(timezone.utc).isoformat())[:10]
    return {
        "id": f"mv-{item.number:04d}",
        "slug": item.slug,
        "title": item.title,
        "artist": item.artist,
        "w": item.width,
        "h": item.height,
        "durationText": format_duration(item.duration) if item.duration is not None else None,
        "thumb": _asset_url(base_url, item.thumb_key, item.thumb_local, item.slug, ""),
        "poster": _asset_url(base_url, item.poster_key, item.poster_local, item.slug, "-poster"),
        "video": public_url(base_url, item.key),
        "page": f"/music-videos/{item.slug}/",
        "description": item.description,
        "lyrics": item.lyrics,
        "uploadDate": upload_date,
        "duration": iso8601_duration(item.duration),
        "encodingFormat": item.content_type or "video/mp4",
        "category": "music-videos",
        "genre": item.genre,
        "themes": item.themes,
        "year": item.year,
    }


def track_entry(item: ArchiveItem, base_url: str) -> dict:
    return {
        "id": f"bgm-{item.number:04d}",
        "slug": item.slug,
        "title": item.title,
        "artist": item.artist,
        "src": public_url(base_url, item.key),
        "durationText": format_duration(item.duration) if item.duration is not None else None,
        "duration": iso8601_duration(item.duration),
        "encodingFormat": item.content_type or "audio/mpeg",
        "cover": _asset_url(base_url, item.poster_key, item.poster_local, item.slug, "-poster"),
    }


def asset_entry(item: ArchiveItem, base_url: str) -> dict:
    return {
        "key": item.key,
        "url": public_url(base_url, item.key),
        "category": item.category,
        "sizeBytes": item.size,
        "sha256": item.sha256,
        "durationSeconds": round(item.duration, 3) if item.duration is not None else None,
        "width": item.width,
        "height": item.height,
        "contentType": item.content_type,
        "thumbnailKey": item.thumb_key,
        "posterKey": item.poster_key,
        "thumbnailLocal": item.thumb_local,
        "posterLocal": item.poster_local,
        "uploadedAt": item.uploaded_at,
    }


def build_document(items: list[ArchiveItem], base_url: str, bucket: str) -> dict:
    works = [work_entry(i, base_url) for i in items if i.category == "mv"]
    tracks = [track_entry(i, base_url) for i in items if i.category == "bgm"]
    return {
        "$schema": "jinn-infinite-archive-registration/1",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": f"Jinn Media Uploader {__version__}",
        "bucket": bucket,
        "publicBaseUrl": base_url,
        "works": works,
        "soundscape": {"tracks": tracks},
        "assets": [asset_entry(i, base_url) for i in items],
    }


def write_document(doc: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"infinite-archive-{stamp}.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


REQUIRED_WORK_KEYS = (
    "id", "slug", "title", "artist", "w", "h", "durationText", "thumb", "poster", "video", "page",
    "description", "lyrics",
)


def validate_document(doc: dict) -> list[str]:
    problems = []
    seen_ids, seen_slugs = set(), set()
    for w in doc.get("works", []):
        for k in REQUIRED_WORK_KEYS:
            if k not in w:
                problems.append(f"{w.get('id')}: '{k}' がありません")
        if w.get("id") in seen_ids:
            problems.append(f"ID が重複しています: {w.get('id')}")
        if w.get("slug") in seen_slugs:
            problems.append(f"slug が重複しています: {w.get('slug')}")
        seen_ids.add(w.get("id"))
        seen_slugs.add(w.get("slug"))
        if not str(w.get("video", "")).startswith("https://"):
            problems.append(f"{w.get('id')}: video URL が https ではありません")
        if not w.get("slug"):
            problems.append(f"{w.get('id')}: slug が空です")
    return problems
