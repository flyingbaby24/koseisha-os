"""Non-secret application settings, stored as JSON in the per-user app data folder.

Secrets (Access Key ID / Secret Access Key / Account ID) never go here: they live in
the OS credential vault, see :mod:`jinn_uploader.credentials`.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import APP_ID

DEFAULT_ACCOUNT_LABEL = "Jinn Project Media"
DEFAULT_BUCKET = "jinn-mv-portfolio"
DEFAULT_PUBLIC_BASE_URL = "https://pub-14a29b5d61e944bfa82071f29c1817f1.r2.dev"

COMPRESSION_MODES = ("none", "faststart", "h264")


def app_data_dir() -> Path:
    """Per-user folder for settings, history, resume state and logs.

    Windows: %APPDATA%\\JinnMediaUploader. ``JINN_UPLOADER_HOME`` overrides it (tests, CI).
    """
    override = os.environ.get("JINN_UPLOADER_HOME")
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(base) / APP_ID
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
        path = Path(base) / "jinn-media-uploader"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class Pricing:
    """Cloudflare R2 Standard storage list prices (USD). Editable in the app."""

    storage_per_gb_month: float = 0.015
    class_a_per_million: float = 4.50
    class_b_per_million: float = 0.36
    free_storage_gb: float = 10.0
    free_class_a_million: float = 1.0
    free_class_b_million: float = 10.0
    usd_jpy: float = 150.0


@dataclass
class AppConfig:
    account_label: str = DEFAULT_ACCOUNT_LABEL
    bucket: str = DEFAULT_BUCKET
    public_base_url: str = DEFAULT_PUBLIC_BASE_URL
    # Empty → https://<account_id>.r2.cloudflarestorage.com
    endpoint_override: str = ""

    # Destination prefixes ("folders") inside the bucket.
    mv_prefix: str = "mv/"
    # The portfolio's soundscape expects ambient audio under audio/ (docs/soundscape.md).
    bgm_prefix: str = "audio/"
    thumb_prefix: str = "thumbnails/"
    other_prefix: str = "misc/"
    keep_folder_structure: bool = False
    recent_prefixes: list[str] = field(default_factory=list)

    # Transfer tuning. R2 requires every part except the last to be the same size.
    part_size_mib: int = 16
    multipart_threshold_mib: int = 32
    concurrency: int = 4
    max_retries: int = 5

    # Media handling. Compression is opt-in: "none" uploads the original bytes.
    compression: str = "none"
    h264_crf: int = 23
    generate_thumbnails: bool = True
    # The portfolio serves thumbnails from its own public/ folder (THUMBNAIL_BASE_URL empty),
    # so copying them to R2 is optional.
    upload_thumbnails: bool = False
    ffmpeg_path: str = ""

    # Portfolio (Infinite Archive) registration.
    portfolio_source: str = "github"  # "github" (direct, no local clone needed) | "local"
    github_repo: str = "flyingbaby24/Jinn-Portfolio"
    github_api: str = "https://api.github.com"  # not shown in the UI (self-test / GitHub Enterprise)
    github_branch: str = ""  # last branch used; empty → the repository's default branch
    github_mode: str = "commit"  # "commit" (fast-forward the branch) | "pr" (new branch + pull request)
    pages_project: str = "jinn-portfolio"  # Cloudflare Pages project (→ <branch>.jinn-portfolio.pages.dev)
    portfolio_dir: str = ""  # local clone of flyingbaby24/Jinn-Portfolio (or its data/ folder)
    archive_artist: str = "Jinn Project"
    export_dir: str = ""

    config_version: int = 2

    pricing: Pricing = field(default_factory=Pricing)

    # ------------------------------------------------------------------
    def normalized(self) -> "AppConfig":
        if self.compression not in COMPRESSION_MODES:
            self.compression = "none"
        if self.portfolio_source not in ("github", "local"):
            self.portfolio_source = "github"
        if self.github_mode not in ("commit", "pr"):
            self.github_mode = "commit"
        self.github_repo = self.github_repo.strip().strip("/")
        self.part_size_mib = max(5, min(int(self.part_size_mib), 5 * 1024))
        self.multipart_threshold_mib = max(5, int(self.multipart_threshold_mib))
        self.concurrency = max(1, min(int(self.concurrency), 16))
        self.max_retries = max(0, min(int(self.max_retries), 20))
        self.public_base_url = self.public_base_url.strip().rstrip("/")
        self.endpoint_override = self.endpoint_override.strip().rstrip("/")
        self.recent_prefixes = [p for p in dict.fromkeys(self.recent_prefixes) if isinstance(p, str)][:20]
        return self

    def prefix_for(self, category: str) -> str:
        return {
            "mv": self.mv_prefix,
            "bgm": self.bgm_prefix,
            "thumbnail": self.thumb_prefix,
        }.get(category, self.other_prefix)

    def remember_prefix(self, prefix: str) -> None:
        if prefix and prefix not in self.recent_prefixes:
            self.recent_prefixes.insert(0, prefix)
            del self.recent_prefixes[20:]

    def export_path(self) -> Path:
        if self.export_dir:
            return Path(self.export_dir)
        docs = Path.home() / "Documents"
        return (docs if docs.is_dir() else Path.home()) / "JinnMediaUploader"


def _from_dict(cls, data: dict):
    known = {f.name: f for f in fields(cls)}
    kwargs = {}
    for name, value in (data or {}).items():
        if name not in known:
            continue
        if name == "pricing" and isinstance(value, dict):
            value = _from_dict(Pricing, value)
        kwargs[name] = value
    return cls(**kwargs)


def migrate(data: dict) -> dict:
    """Bring settings saved by older versions up to date."""
    data = dict(data or {})
    if int(data.get("config_version", 1)) < 2:
        if data.get("bgm_prefix") == "bgm/":
            data["bgm_prefix"] = "audio/"
        if "upload_thumbnails" in data:
            data["upload_thumbnails"] = False
        data["config_version"] = 2
    return data


class ConfigStore:
    def __init__(self, path: Path | None = None):
        self.path = path or (app_data_dir() / "config.json")

    def load(self) -> AppConfig:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return _from_dict(AppConfig, migrate(data)).normalized()
        except FileNotFoundError:
            return AppConfig().normalized()
        except (OSError, ValueError, TypeError):
            # A damaged config must never block the app; fall back to defaults.
            return AppConfig().normalized()

    def save(self, config: AppConfig) -> None:
        config.normalized()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(asdict(config), ensure_ascii=False, indent=2)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".config-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, self.path)
