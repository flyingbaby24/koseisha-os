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
    poster: Path | None = None  # JPEG, up to 1280px on the long side
    thumb: Path | None = None  # WebP (JPEG fallback), up to 640px on the long side


def _seek_point(duration: float | None) -> float:
    if not duration or duration <= 0:
        return 0.0
    if duration < 3:
        return 0.0
    return min(max(1.0, duration * 0.1), duration - 1.0)


def make_video_thumbnails(ffmpeg: str, src: str | Path, out_dir: Path, stem: str, info: MediaInfo) -> Thumbnails:
    """Pick a representative frame ~10% into the video and write a poster + small thumb."""
    out_dir.mkdir(parents=True, exist_ok=True)
    poster = out_dir / f"{stem}-poster.jpg"
    ss = f"{_seek_point(info.duration):.3f}"
    pick = "thumbnail=n=30,"
    scale_big = "scale='min(1280,iw)':'min(1280,ih)':force_original_aspect_ratio=decrease"
    r = _run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", ss, "-i", str(src),
         "-frames:v", "1", "-vf", pick + scale_big, "-q:v", "3", str(poster)],
        timeout=300,
    )
    if r.returncode != 0 or not poster.is_file():
        # Retry from the start without the frame picker (very short / odd files).
        r = _run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
             "-frames:v", "1", "-vf", scale_big, "-q:v", "3", str(poster)],
            timeout=300,
        )
        if r.returncode != 0 or not poster.is_file():
            raise FFmpegError(r.stderr.decode("utf-8", "replace").strip()[-500:] or "サムネイル生成に失敗しました")
    return Thumbnails(poster=poster, thumb=_small_thumb(ffmpeg, poster, out_dir, stem))


def _small_thumb(ffmpeg: str, poster: Path, out_dir: Path, stem: str) -> Path | None:
    scale_small = "scale='min(640,iw)':'min(640,ih)':force_original_aspect_ratio=decrease"
    webp = out_dir / f"{stem}.webp"
    r = _run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(poster),
         "-vf", scale_small, "-c:v", "libwebp", "-quality", "82", str(webp)],
        timeout=120,
    )
    if r.returncode == 0 and webp.is_file():
        return webp
    jpg = out_dir / f"{stem}-thumb.jpg"
    r = _run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(poster),
         "-vf", scale_small, "-q:v", "4", str(jpg)],
        timeout=120,
    )
    return jpg if r.returncode == 0 and jpg.is_file() else None


def make_audio_thumbnails(ffmpeg: str, src: str | Path, out_dir: Path, stem: str, info: MediaInfo) -> Thumbnails:
    """Use embedded cover art when present, otherwise draw a waveform image."""
    out_dir.mkdir(parents=True, exist_ok=True)
    poster = out_dir / f"{stem}-poster.jpg"
    if info.has_cover_art:
        r = _run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-an",
             "-frames:v", "1", "-vf",
             "scale='min(1280,iw)':'min(1280,ih)':force_original_aspect_ratio=decrease",
             "-q:v", "3", str(poster)],
            timeout=120,
        )
        if r.returncode == 0 and poster.is_file():
            return Thumbnails(poster=poster, thumb=_small_thumb(ffmpeg, poster, out_dir, stem))
    png = out_dir / f"{stem}-wave.png"
    r = _run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
         "-filter_complex", "aformat=channel_layouts=mono,showwavespic=s=1280x360:colors=0xE8E1D4",
         "-frames:v", "1", str(png)],
        timeout=300,
    )
    if r.returncode != 0 or not png.is_file():
        raise FFmpegError(r.stderr.decode("utf-8", "replace").strip()[-500:] or "波形画像の生成に失敗しました")
    r = _run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=0x101014:s=1280x360",
         "-i", str(png), "-filter_complex", "[0][1]overlay=format=auto", "-frames:v", "1", "-q:v", "3", str(poster)],
        timeout=120,
    )
    png.unlink(missing_ok=True)
    if r.returncode != 0 or not poster.is_file():
        raise FFmpegError(r.stderr.decode("utf-8", "replace").strip()[-500:] or "波形画像の生成に失敗しました")
    return Thumbnails(poster=poster, thumb=_small_thumb(ffmpeg, poster, out_dir, stem))


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
