"""FFmpeg / FFprobe helpers: probing, thumbnails and the optional compression step."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class FFmpegError(Exception):
    pass


class FFmpegCancelled(FFmpegError):
    pass


def _exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def find_ffmpeg(configured: str = "") -> tuple[str | None, str | None]:
    """Locate ffmpeg/ffprobe: configured path → next to the EXE → PATH."""
    exe = ".exe" if os.name == "nt" else ""
    candidates: list[Path] = []
    if configured:
        c = Path(configured)
        candidates.append(c.parent if c.is_file() else c)
    base = _exe_dir()
    candidates += [base / "ffmpeg", base / "ffmpeg" / "bin", base]
    for d in candidates:
        f, p = d / f"ffmpeg{exe}", d / f"ffprobe{exe}"
        if f.is_file():
            return str(f), (str(p) if p.is_file() else shutil.which("ffprobe"))
    return shutil.which("ffmpeg"), shutil.which("ffprobe")


def _run(cmd: list[str], timeout: float | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise FFmpegError(f"実行ファイルが見つかりません: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError(f"タイムアウトしました: {Path(cmd[0]).name}") from exc


def ffmpeg_version(ffmpeg: str) -> str:
    r = _run([ffmpeg, "-hide_banner", "-version"], timeout=20)
    return r.stdout.decode("utf-8", "replace").splitlines()[0] if r.returncode == 0 else ""


@dataclass
class MediaInfo:
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    rotation: int = 0
    video_codec: str | None = None
    audio_codec: str | None = None
    format_name: str | None = None
    bit_rate: int | None = None
    has_video: bool = False
    has_audio: bool = False
    has_cover_art: bool = False

    @property
    def display_size(self) -> tuple[int | None, int | None]:
        if self.rotation % 180 == 90:
            return self.height, self.width
        return self.width, self.height

    def to_dict(self) -> dict:
        d = asdict(self)
        d["display_width"], d["display_height"] = self.display_size
        return d


def _rotation(stream: dict) -> int:
    for sd in stream.get("side_data_list") or []:
        if "rotation" in sd:
            try:
                return int(round(float(sd["rotation"]))) % 360
            except (TypeError, ValueError):
                pass
    try:
        return int((stream.get("tags") or {}).get("rotate", 0)) % 360
    except (TypeError, ValueError):
        return 0


def probe(ffprobe: str, path: str | Path) -> MediaInfo:
    r = _run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        timeout=120,
    )
    if r.returncode != 0:
        raise FFmpegError(r.stderr.decode("utf-8", "replace").strip()[-500:] or "ffprobe failed")
    data = json.loads(r.stdout.decode("utf-8", "replace") or "{}")
    info = MediaInfo()
    fmt = data.get("format") or {}
    info.format_name = fmt.get("format_name")
    try:
        info.duration = float(fmt["duration"]) if fmt.get("duration") not in (None, "N/A") else None
    except (TypeError, ValueError):
        info.duration = None
    try:
        info.bit_rate = int(fmt["bit_rate"]) if fmt.get("bit_rate") else None
    except (TypeError, ValueError):
        pass
    for s in data.get("streams") or []:
        kind = s.get("codec_type")
        if kind == "video":
            if (s.get("disposition") or {}).get("attached_pic"):
                info.has_cover_art = True
                continue
            if not info.has_video:
                info.has_video = True
                info.video_codec = s.get("codec_name")
                info.width = s.get("width")
                info.height = s.get("height")
                info.rotation = _rotation(s)
                if info.duration is None and s.get("duration") not in (None, "N/A"):
                    try:
                        info.duration = float(s["duration"])
                    except (TypeError, ValueError):
                        pass
        elif kind == "audio" and not info.has_audio:
            info.has_audio = True
            info.audio_codec = s.get("codec_name")
    return info


@dataclass
class Thumbnails:
    thumb: Path | None = None  # WebP for cards
    poster: Path | None = None  # JPEG for the player poster and Open Graph
    at: float = 0.0  # second the frame was taken from


# Same derivatives as the portfolio's scripts/make-thumbnails.mjs, so a thumbnail made
# here is interchangeable with one the site regenerates from data/thumbnail-sources.json.
THUMB_WIDTH = {"portrait": 480, "landscape": 800}
POSTER_WIDTH = {"portrait": 720, "landscape": 1280}
THUMB_CODEC = ["-c:v", "libwebp", "-quality", "62", "-compression_level", "6"]
POSTER_CODEC = ["-q:v", "4"]


def make_site_thumbnails(ffmpeg: str, src: str | Path, thumb_path: Path, poster_path: Path, at: float,
                         landscape: bool) -> Thumbnails:
    """Grab the frame at *at* seconds; *src* may be a local file or the public https URL."""
    orient = "landscape" if landscape else "portrait"
    outputs = [(thumb_path, THUMB_WIDTH[orient], THUMB_CODEC), (poster_path, POSTER_WIDTH[orient], POSTER_CODEC)]
    for out, width, codec in outputs:
        out.parent.mkdir(parents=True, exist_ok=True)
        r = _run(
            [ffmpeg, "-v", "error", "-y", "-ss", f"{max(0.0, at):g}", "-i", str(src), "-frames:v", "1",
             "-vf", f"scale={width}:-2:flags=lanczos", *codec, str(out)],
            timeout=300,
        )
        if r.returncode != 0 or not out.is_file() or out.stat().st_size == 0:
            raise FFmpegError(r.stderr.decode("utf-8", "replace").strip()[-500:] or f"{out.name} を作成できません")
    return Thumbnails(thumb=thumb_path, poster=poster_path, at=at)


def transcode(
    ffmpeg: str,
    src: str | Path,
    mode: str,
    crf: int = 23,
    duration: float | None = None,
    progress: Callable[[float], None] | None = None,
    cancel: threading.Event | None = None,
) -> Path:
    """Optional pre-upload processing. Returns a temp file the caller must delete.

    faststart: lossless remux that moves the MP4 index to the front (better web playback).
    h264:      re-encode to H.264/AAC MP4 with the given CRF.
    """
    if mode not in ("faststart", "h264"):
        raise ValueError(mode)
    fd, tmp = tempfile.mkstemp(prefix="jmu-", suffix=".mp4")
    os.close(fd)
    if mode == "faststart":
        codec = ["-map", "0", "-c", "copy", "-movflags", "+faststart"]
    else:
        codec = ["-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "medium", "-crf", str(int(crf)),
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostats", "-y", "-i", str(src), *codec,
           "-progress", "pipe:1", tmp]
    stderr_chunks: list[bytes] = []
    try:
        with subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
        ) as proc:
            reader = threading.Thread(target=lambda: stderr_chunks.append(proc.stderr.read()), daemon=True)
            reader.start()
            try:
                assert proc.stdout is not None
                for raw in proc.stdout:
                    if cancel is not None and cancel.is_set():
                        raise FFmpegCancelled("キャンセルされました")
                    line = raw.decode("ascii", "replace").strip()
                    if line.startswith("out_time_us=") and duration and progress:
                        try:
                            progress(min(1.0, int(line.split("=", 1)[1]) / 1e6 / duration))
                        except ValueError:
                            pass
                proc.wait()
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                reader.join(timeout=5)
        if proc.returncode != 0:
            raise FFmpegError(b"".join(stderr_chunks).decode("utf-8", "replace").strip()[-500:] or "変換に失敗しました")
        if progress:
            progress(1.0)
        return Path(tmp)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
