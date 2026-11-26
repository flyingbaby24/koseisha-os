"""Registration data for the Jinn Project Portfolio (Infinite Archive).

Targets the portfolio repository's real data files (branch phase-3-1-soundscape):

* ``data/works.json``            ``{"schemaVersion": 1, "works": [...]}`` — validated by
                                  ``src/data/schema.mjs``; unknown fields are rejected.
* ``data/soundscape.json``       ``{"placeholder", "crossfade", "tracks": [{id, key, gain?, start?, end?}]}``
                                  — validated by ``src/data/soundscape.mjs``.
* ``data/thumbnail-sources.json`` slug → poster-frame second used by ``scripts/make-thumbnails.mjs``.
* ``public/<thumbnailKey>`` / ``public/<posterKey>`` — thumbnails are served by the site itself.

The validators below are line-for-line ports of the site's JavaScript ones, so an
export that passes here passes ``npm run build`` there. Existing entries are never
modified: new ones are appended, IDs/slugs are allocated around everything already
in the files (and around IDs this app issued before), and a key that is already
registered is reported instead of being registered twice.
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from . import __version__
from .keys import slugify, title_from_filename

WORK_FIELDS = (
    "id", "slug", "category", "title", "artist", "description", "lyrics", "genre", "themes", "tags",
    "createdDate", "publishedDate", "videoKey", "thumbnailKey", "posterKey", "duration", "width", "height",
    "productionTools", "relatedArticles", "relatedWorks", "language", "status",
)
STATUSES = ("draft", "published", "unlisted", "archived")
MV_CATEGORY = "music-videos"
WORK_ID_PREFIX = "mv"

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
_LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]+)*$")
_SCHEME_RE = re.compile(r"^[a-z]+://", re.I)
AUDIO_KEY_RE = re.compile(r"\.(m4a|mp4|aac|mp3|ogg|opus|wav|flac)$", re.I)


class PortfolioError(Exception):
    pass


# ---------------------------------------------------------------------- validators (ports)
def _is_text(v) -> bool:
    if isinstance(v, str):
        return v.strip() != ""
    return isinstance(v, dict) and all(isinstance(s, str) for s in v.values())


def _is_nullable_text(v) -> bool:
    return v is None or _is_text(v)


def _is_text_list(v) -> bool:
    return isinstance(v, list) and all(_is_text(x) for x in v)


def _is_date(v) -> bool:
    return isinstance(v, str) and bool(_DATE_RE.match(v))


def is_object_key(v) -> bool:
    return (isinstance(v, str) and v != "" and not v.startswith("/") and not _SCHEME_RE.match(v)
            and ".." not in v.split("/"))


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


FIELD_CHECKS = {
    "id": (True, lambda v: isinstance(v, str) and bool(_ID_RE.match(v))),
    "slug": (True, lambda v: isinstance(v, str) and bool(_SLUG_RE.match(v))),
    "category": (True, lambda v: isinstance(v, str) and v != ""),
    "title": (True, _is_text),
    "artist": (False, _is_nullable_text),
    "description": (False, _is_nullable_text),
    "lyrics": (False, _is_nullable_text),
    "genre": (False, _is_nullable_text),
    "themes": (False, _is_text_list),
    "tags": (False, _is_text_list),
    "createdDate": (False, lambda v: v is None or _is_date(v)),
    "publishedDate": (False, lambda v: v is None or _is_date(v)),
    "videoKey": (False, lambda v: v is None or is_object_key(v)),
    "thumbnailKey": (False, lambda v: v is None or is_object_key(v)),
    "posterKey": (False, lambda v: v is None or is_object_key(v)),
    "duration": (False, lambda v: v is None or (_is_number(v) and v > 0)),
    "width": (False, lambda v: v is None or (_is_int(v) and v > 0)),
    "height": (False, lambda v: v is None or (_is_int(v) and v > 0)),
    "productionTools": (False, _is_text_list),
    "relatedArticles": (False, lambda v: isinstance(v, list) and all(
        isinstance(a, dict) and _is_text(a.get("title")) and isinstance(a.get("url"), str)
        and re.match(r"^https?://", a["url"]) for a in v)),
    "relatedWorks": (False, lambda v: isinstance(v, list) and all(isinstance(s, str) for s in v)),
    "language": (False, lambda v: v is None or (isinstance(v, str) and bool(_LANG_RE.match(v)))),
    "status": (True, lambda v: v in STATUSES),
}
assert tuple(FIELD_CHECKS) == WORK_FIELDS


def _js_json(v) -> str:
    """JSON.stringify() formatting, so messages match the site's validator exactly."""
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def validate_works(works: list, categories: list) -> list[str]:
    """Port of validateWorks() in src/data/schema.mjs."""
    problems: list[str] = []
    ids: set = set()
    slugs: set = set()
    category_ids = {c.get("id") for c in categories}
    for i, raw in enumerate(works):
        label = raw.get("id") if isinstance(raw, dict) and raw.get("id") is not None else f"#{i}"
        for k in raw:
            if k not in FIELD_CHECKS:
                problems.append(f'{label}: unknown field "{k}"')
        for name, (required, check) in FIELD_CHECKS.items():
            if name not in raw:
                if required:
                    problems.append(f'{label}: missing "{name}"')
                continue
            if not check(raw[name]):
                problems.append(f'{label}: invalid "{name}": {_js_json(raw[name])}')
        if raw.get("id") in ids:
            problems.append(f"{label}: duplicate id")
        ids.add(raw.get("id"))
        slug_key = f"{raw.get('category')}/{raw.get('slug')}"
        if slug_key in slugs:
            problems.append(f'{label}: duplicate slug "{slug_key}"')
        slugs.add(slug_key)
        if raw.get("category") and raw["category"] not in category_ids:
            problems.append(f'{label}: unknown category "{raw["category"]}"')
        if raw.get("status") == "published" and raw.get("category") == MV_CATEGORY:
            for need in ("videoKey", "thumbnailKey", "duration", "width", "height"):
                if raw.get(need) is None:
                    problems.append(f'{label}: published music video needs "{need}"')
    for raw in works:
        for ref in raw.get("relatedWorks") or []:
            if ref not in ids:
                problems.append(f'{raw.get("id")}: relatedWorks references unknown id "{ref}"')
            if ref == raw.get("id"):
                problems.append(f'{raw.get("id")}: relatedWorks references itself')
    return problems


def validate_soundscape(raw: dict) -> list[str]:
    """Port of validateSoundscape() in src/data/soundscape.mjs."""
    problems: list[str] = []
    if raw.get("placeholder", "none") not in ("synth", "none"):
        problems.append('placeholder must be "synth" or "none"')
    cf = raw.get("crossfade")
    if "crossfade" in raw and not (_is_number(cf) and 0.5 <= cf <= 30):
        problems.append("crossfade must be 0.5–30 seconds")
    if not isinstance(raw.get("tracks"), list):
        problems.append("tracks must be a list")
    ids: set = set()
    for i, t in enumerate(raw.get("tracks") or []):
        t = t if isinstance(t, dict) else {}
        label = t.get("id") if t.get("id") is not None else f"#{i}"
        if not (isinstance(t.get("id"), str) and _ID_RE.match(t["id"])):
            problems.append(f"{label}: invalid id")
        if t.get("id") in ids:
            problems.append(f"{label}: duplicate id")
        ids.add(t.get("id"))
        key = t.get("key")
        if not is_object_key(key):
            problems.append(f"{label}: invalid key")
        elif not AUDIO_KEY_RE.search(key):
            problems.append(f"{label}: key is not an audio file")
        if "gain" in t and not (_is_number(t["gain"]) and 0.1 <= t["gain"] <= 2):
            problems.append(f"{label}: gain must be 0.1–2")
        for f in ("start", "end"):
            if f in t and not (_is_number(t[f]) and t[f] >= 0):
                problems.append(f"{label}: {f} must be seconds")
        if _is_number(t.get("start")) and _is_number(t.get("end")) and t["end"] <= t["start"] + 1:
            problems.append(f"{label}: end must be after start")
    return problems


# ---------------------------------------------------------------------- existing data
def locate_root(path: str | Path) -> Path:
    """Accept the repository root or its data/ folder (or data/works.json itself)."""
    p = Path(path)
    if p.is_file():
        p = p.parent
    if (p / "data" / "works.json").is_file():
        return p
    if p.name == "data" and (p / "works.json").is_file():
        return p.parent
    raise PortfolioError(f"data/works.json が見つかりません: {path}")


DATA_FILES = ("works.json", "soundscape.json", "thumbnail-sources.json", "categories.json")
DEFAULT_SOUNDSCAPE = {"placeholder": "synth", "crossfade": 8, "tracks": []}


@dataclass
class PortfolioData:
    """The portfolio's registration data, read from a local clone or from GitHub."""

    root: Path | None
    works_doc: dict
    soundscape_doc: dict
    thumbnail_sources: dict
    categories: list
    source: str = ""
    # Files already present under public/<thumbnail prefix> (names only); a slug whose
    # thumbnail name is taken is treated as taken even if no work uses it.
    existing_thumbnails: set = field(default_factory=set)
    has_soundscape: bool = True
    raw_texts: dict = field(default_factory=dict)  # data file name → text as read

    @classmethod
    def from_texts(cls, texts: dict[str, str | None], source: str, root: Path | None = None,
                   existing_thumbnails: set | None = None) -> "PortfolioData":
        """Build from the raw text of each data file (None = file absent)."""
        def parse(name: str, default=None):
            text = texts.get(name)
            if text is None:
                if default is not None:
                    return json.loads(json.dumps(default))
                raise PortfolioError(f"{name} がありません（{source}）")
            try:
                return json.loads(text)
            except ValueError as exc:
                raise PortfolioError(f"{name} を読み込めません: {exc}") from exc

        works_doc = parse("works.json")
        if not isinstance(works_doc, dict) or not isinstance(works_doc.get("works"), list):
            raise PortfolioError("works.json の形式が想定と異なります（works 配列がありません）")
        soundscape = parse("soundscape.json", DEFAULT_SOUNDSCAPE)
        sources = parse("thumbnail-sources.json", {})
        categories = parse("categories.json", {"categories": [{"id": MV_CATEGORY}]}).get("categories", [])
        problems = validate_works(works_doc["works"], categories) + validate_soundscape(soundscape)
        if problems:
            raise PortfolioError("既存データが検証を通りません:\n- " + "\n- ".join(problems[:10]))
        return cls(root, works_doc, soundscape, sources, categories, source=source,
                   existing_thumbnails=set(existing_thumbnails or ()),
                   has_soundscape=texts.get("soundscape.json") is not None,
                   raw_texts={k: v for k, v in texts.items() if v is not None})

    @classmethod
    def load(cls, path: str | Path, thumb_prefix: str = "thumbnails/") -> "PortfolioData":
        root = locate_root(path)
        data = root / "data"
        # Bytes, not text mode: keep the files' own line endings so they can be preserved on write.
        texts = {n: (data / n).read_bytes().decode("utf-8") if (data / n).is_file() else None for n in DATA_FILES}
        thumbs_dir = root / "public" / Path(*[p for p in thumb_prefix.split("/") if p])
        existing = {f.name for f in thumbs_dir.iterdir()} if thumbs_dir.is_dir() else set()
        return cls.from_texts(texts, str(root), root=root, existing_thumbnails=existing)

    @property
    def works(self) -> list[dict]:
        return self.works_doc["works"]

    @property
    def tracks(self) -> list[dict]:
        return self.soundscape_doc.get("tracks") or []

    def work_by_video_key(self, key: str) -> dict | None:
        return next((w for w in self.works if w.get("videoKey") == key), None)

    def track_by_key(self, key: str) -> dict | None:
        return next((t for t in self.tracks if t.get("key") == key), None)

    def summary(self) -> str:
        ids = sorted(w["id"] for w in self.works)
        span = f"（{ids[0]}〜{ids[-1]}）" if ids else ""
        return f"作品 {len(self.works)} 件{span} / BGM {len(self.tracks)} 曲"


# ---------------------------------------------------------------------- allocation
def next_numbered_id(prefix: str, taken: set[str]) -> str:
    pat = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    nums = [int(m.group(1)) for t in taken if (m := pat.match(t))]
    n = (max(nums) if nums else 0) + 1
    while f"{prefix}-{n:04d}" in taken:
        n += 1
    return f"{prefix}-{n:04d}"


def unique_name(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def default_thumb_time(duration: float | None) -> float:
    """Same default frame as scripts/make-thumbnails.mjs: 10 % into the video."""
    return round((duration or 0) * 0.1, 2)


@dataclass
class Candidate:
    kind: str  # "work" | "track"
    key: str
    title: str
    local_path: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    sha256: str | None = None
    uploaded_at: str | None = None
    thumb_local: str | None = None
    poster_local: str | None = None
    thumb_time_generated: float | None = None
    # assigned / editable
    id: str = ""
    slug: str = ""
    status: str = "published"
    published_date: str = field(default_factory=lambda: date.today().isoformat())
    thumb_time: float = 0.0
    include: bool = True
    locked: bool = False  # cannot be registered (already registered / unsupported here)
    note: str = ""

    @classmethod
    def from_history(cls, row: dict) -> "Candidate":
        kind = "track" if row.get("category") == "bgm" else "work"
        name = Path(row.get("local_path") or row["key"]).name
        dur = row.get("duration")
        return cls(
            kind=kind, key=row["key"], title=title_from_filename(name), local_path=row.get("local_path"),
            duration=round(float(dur), 2) if dur else None,
            width=row.get("width"), height=row.get("height"), sha256=row.get("sha256"),
            uploaded_at=row.get("uploaded_at"), thumb_local=row.get("thumb_local"),
            poster_local=row.get("poster_local"), thumb_time_generated=row.get("thumb_time"),
            thumb_time=row.get("thumb_time") if row.get("thumb_time") is not None else default_thumb_time(dur),
        )

    @property
    def landscape(self) -> bool:
        return (self.width or 16) > (self.height or 9)


def plan(candidates: list[Candidate], data: PortfolioData, issued: dict[str, str] | None = None) -> None:
    """Assign IDs and slugs that collide with nothing already registered.

    ``issued`` maps object key → ID this app issued in an earlier export; that ID is
    reused for the same key (stable re-exports) as long as nothing else took it.
    """
    issued = issued or {}
    work_ids = {w["id"] for w in data.works}
    track_ids = {t["id"] for t in data.tracks if isinstance(t, dict) and "id" in t}
    reserved_other = {i for k, i in issued.items()}
    slugs = {w["slug"] for w in data.works if w.get("category") == MV_CATEGORY}
    for name in data.existing_thumbnails:  # e.g. "human.webp", "human-poster.jpg"
        stem = name.rsplit(".", 1)[0]
        slugs.add(stem[:-len("-poster")] if stem.endswith("-poster") else stem)
    for c in candidates:
        c.note, c.include, c.locked = "", True, False
        if c.kind == "work":
            existing = data.work_by_video_key(c.key)
            if existing:
                c.include, c.locked, c.id, c.slug = False, True, existing["id"], existing["slug"]
                c.note = f"登録済み（{existing['id']}）"
                continue
            prev = issued.get(c.key)
            if prev and prev not in work_ids and prev.startswith(f"{WORK_ID_PREFIX}-"):
                c.id = prev
            else:
                c.id = next_numbered_id(WORK_ID_PREFIX, work_ids | reserved_other)
            work_ids.add(c.id)
            base = slugify(c.title) or c.id
            c.slug = unique_name(base, slugs)
            slugs.add(c.slug)
            if c.duration is None or not c.width or not c.height:
                c.status = "draft"
                c.note = "尺・解像度が不明のため draft"
        else:
            if not data.has_soundscape:
                c.include, c.locked = False, True
                c.note = "このブランチには data/soundscape.json がありません（BGM 未対応）"
                continue
            existing = data.track_by_key(c.key)
            if existing:
                c.include, c.locked, c.id = False, True, existing.get("id", "")
                c.note = f"登録済み（{c.id}）"
                continue
            if not AUDIO_KEY_RE.search(c.key):
                c.include, c.locked = False, True
                c.note = "サイトが再生できない形式（m4a/mp3/aac/ogg/opus/wav/flac のみ）"
                continue
            prev = issued.get(c.key)
            if prev and prev not in track_ids and _ID_RE.match(prev):
                c.id = prev
            else:
                base = slugify(c.title) or "track"
                c.id = unique_name(base, track_ids | {i for i in reserved_other if i != issued.get(c.key)})
            track_ids.add(c.id)


def work_entry(c: Candidate, thumb_prefix: str, artist: str | None) -> dict:
    thumb_key = f"{thumb_prefix}{c.slug}.webp"
    entry = {
        "id": c.id,
        "slug": c.slug,
        "category": MV_CATEGORY,
        "title": c.title,
        "artist": artist or None,
        "description": None,
        "lyrics": None,
        "genre": None,
        "themes": [],
        "tags": [],
        "createdDate": None,
        "publishedDate": c.published_date or None,
        "videoKey": c.key,
        "thumbnailKey": thumb_key,
        "posterKey": f"{thumb_prefix}{c.slug}-poster.jpg",
        "duration": c.duration,
        "width": c.width,
        "height": c.height,
        "productionTools": [],
        "relatedArticles": [],
        "relatedWorks": [],
        "language": None,
        "status": c.status,
    }
    assert tuple(entry) == WORK_FIELDS
    return entry


def track_entry(c: Candidate) -> dict:
    return {"id": c.id, "key": c.key}


@dataclass
class Registration:
    works_doc: dict
    soundscape_doc: dict
    thumbnail_sources: dict
    new_works: list[dict]
    new_tracks: list[dict]
    problems: list[str]
    newlines: dict = field(default_factory=dict)  # data file name → "\n" or "\r\n" as found

    def encoded(self, name: str) -> bytes:
        doc = {"works.json": self.works_doc, "soundscape.json": self.soundscape_doc,
               "thumbnail-sources.json": self.thumbnail_sources}[name]
        return encode_json(doc, self.newlines.get(name, "\n"))


def build(data: PortfolioData, candidates: list[Candidate], thumb_prefix: str = "thumbnails/",
          artist: str | None = "Jinn Project") -> Registration:
    new_works = [work_entry(c, thumb_prefix, artist) for c in candidates if c.include and c.kind == "work"]
    new_tracks = [track_entry(c) for c in candidates if c.include and c.kind == "track"]
    works_doc = json.loads(json.dumps(data.works_doc))
    works_doc["works"] = works_doc["works"] + new_works
    sound = json.loads(json.dumps(data.soundscape_doc))
    sound["tracks"] = list(sound.get("tracks") or []) + new_tracks
    sources = dict(data.thumbnail_sources)
    for c in candidates:
        if c.include and c.kind == "work":
            sources[c.slug] = c.thumb_time
    problems = validate_works(works_doc["works"], data.categories) + validate_soundscape(sound)
    for c in candidates:
        if c.include and c.kind == "work" and not _SLUG_RE.match(c.slug or ""):
            problems.append(f"{c.id}: slug は英小文字・数字・ハイフンのみ")
    newlines = {name: newline_of(text) for name, text in data.raw_texts.items()}
    return Registration(works_doc, sound, sources, new_works, new_tracks, problems, newlines)


def dump_json(doc) -> str:
    """Same layout as the repository's files (2-space indent, UTF-8, trailing newline)."""
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def newline_of(text: str | None) -> str:
    return "\r\n" if text and "\r\n" in text else "\n"


def encode_json(doc, newline: str = "\n") -> bytes:
    """dump_json with the given line ending, as bytes (never re-translated by text-mode I/O)."""
    return dump_json(doc).replace("\n", newline).encode("utf-8")


def write_bundle(reg: Registration, out_dir: Path, thumbnails: dict[str, Path]) -> Path:
    """Write a folder that mirrors the repository layout (copy it over the repo root).

    thumbnails: thumbnailKey/posterKey → generated local file.
    """
    if reg.problems:
        raise PortfolioError("検証エラーがあるため出力できません:\n- " + "\n- ".join(reg.problems))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle = out_dir / f"jinn-portfolio-registration-{stamp}"
    (bundle / "data").mkdir(parents=True, exist_ok=True)
    for name in ("works.json", "soundscape.json", "thumbnail-sources.json"):
        (bundle / "data" / name).write_bytes(reg.encoded(name))
    for key, src in thumbnails.items():
        dest = bundle / "public" / Path(*key.split("/"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    new_entries = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": f"Jinn Media Uploader {__version__}",
        "works": reg.new_works,
        "soundscapeTracks": reg.new_tracks,
        "thumbnailSources": {w["slug"]: reg.thumbnail_sources[w["slug"]] for w in reg.new_works},
    }
    (bundle / "new-entries.json").write_text(dump_json(new_entries), encoding="utf-8")
    (bundle / "README.txt").write_text(_bundle_readme(reg), encoding="utf-8")
    return bundle


def _bundle_readme(reg: Registration) -> str:
    lines = [
        "Jinn Project Portfolio 登録データ（Jinn Media Uploader 出力）",
        "",
        "このフォルダの data/ と public/ を、jinn-portfolio リポジトリのルートにそのままコピー（上書き）してください。",
        "既存の作品・BGM の記述は変更せず、新しい項目を末尾に追加しています。",
        "",
        f"追加する作品: {', '.join(w['id'] + ' ' + w['slug'] for w in reg.new_works) or 'なし'}",
        f"追加する BGM: {', '.join(t['id'] for t in reg.new_tracks) or 'なし'}",
        "",
        "コピー後の確認:",
        "  npm run build && npm test",
        "  npm run verify:r2",
        "",
        "new-entries.json は今回追加した分だけをまとめたものです（確認用）。",
    ]
    return "\n".join(lines) + "\n"
