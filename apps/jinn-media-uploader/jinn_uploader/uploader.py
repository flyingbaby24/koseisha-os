"""Upload engine: duplicate checks, single/multipart uploads with retry and resume.

Safety rules enforced here (not only in the GUI):

* An object that already exists is never replaced unless the job carries an explicit
  ``overwrite`` decision, and then only the exact version the user confirmed
  (``If-Match`` on its ETag). New objects are written with ``If-None-Match: *`` so a
  file that appears between the check and the write is not clobbered either.
* The engine has no delete call for user objects. The only abort it issues is for
  multipart uploads it created itself (their parts are not visible objects).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import math
import os
import random
import threading
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable
from urllib.parse import quote
from uuid import uuid4

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)

from . import media
from .config import AppConfig
from .history import History, ResumeState, ResumeStore
from .keys import build_key, content_type_for, slugify, title_from_filename
from .portfolio import default_thumb_time
from .pricing import upload_class_a_ops
from .r2client import ObjectInfo, R2Service, describe_error, error_code, http_status
from .scanner import Cancelled, hash_file

log = logging.getLogger("jinn_uploader")

MiB = 1024 * 1024
MAX_PARTS = 10_000


class JobState(str, Enum):
    PENDING = "待機"
    ANALYZING = "解析中"
    READY = "準備完了"
    NEEDS_DECISION = "要確認"
    TRANSCODING = "変換中"
    UPLOADING = "アップロード中"
    VERIFYING = "検証中"
    THUMBNAILS = "サムネイル生成中"
    PAUSED = "一時停止"
    DONE = "完了"
    SKIPPED = "スキップ"
    FAILED = "失敗"
    CANCELLED = "キャンセル"


ACTIVE_STATES = {JobState.ANALYZING, JobState.TRANSCODING, JobState.UPLOADING, JobState.VERIFYING, JobState.THUMBNAILS}
TERMINAL_STATES = {JobState.DONE, JobState.SKIPPED, JobState.CANCELLED}

REMOTE_LABELS = {
    "unknown": "未確認",
    "new": "新規",
    "identical": "同一ファイルあり",
    "conflict": "同名ファイルあり",
    "content_dup": "同一内容が別名で存在",
    "queue_dup": "キュー内で重複",
    "queue_key": "キュー内で同じ保存先",
}

DECISIONS = ("upload", "rename", "overwrite", "skip")


class TransferMeter:
    """Sliding-window throughput for speed and ETA."""

    def __init__(self, window: float = 6.0):
        self.window = window
        self._samples: deque[tuple[float, int]] = deque()
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._samples.clear()

    def update(self, total_done: int) -> None:
        now = time.monotonic()
        with self._lock:
            self._samples.append((now, total_done))
            while len(self._samples) > 2 and now - self._samples[0][0] > self.window:
                self._samples.popleft()

    def rate(self) -> float | None:
        with self._lock:
            if len(self._samples) < 2:
                return None
            (t0, b0), (t1, b1) = self._samples[0], self._samples[-1]
        if t1 - t0 < 0.5:
            return None
        if time.monotonic() - t1 > self.window:
            return 0.0
        return max(0.0, (b1 - b0) / (t1 - t0))


@dataclass
class UploadJob:
    path: Path
    size: int
    category: str
    key: str
    subdirs: tuple[str, ...] = ()
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    key_edited: bool = False
    state: JobState = JobState.PENDING
    message: str = ""
    error: str = ""
    md5: str | None = None
    sha256: str | None = None
    media: media.MediaInfo | None = None
    remote: str = "unknown"
    remote_info: ObjectInfo | None = None
    duplicates: list[str] = field(default_factory=list)
    decision: str | None = None
    upload_size: int = 0
    bytes_done: int = 0
    retries: int = 0
    resumed: bool = False
    public_url: str = ""
    etag: str = ""
    thumb_key: str | None = None
    poster_key: str | None = None
    thumb_local: str | None = None
    poster_local: str | None = None
    thumb_time: float | None = None
    compression: str = "none"
    started_at: float | None = None
    finished_at: float | None = None
    history_id: int | None = None
    meter: TransferMeter = field(default_factory=TransferMeter, repr=False)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def total(self) -> int:
        return self.upload_size or self.size

    @property
    def fraction(self) -> float:
        return min(1.0, self.bytes_done / self.total) if self.total else (1.0 if self.state == JobState.DONE else 0.0)

    def rate(self) -> float | None:
        return self.meter.rate() if self.state in (JobState.UPLOADING,) else None

    def eta(self) -> float | None:
        r = self.rate()
        if not r:
            return None
        return max(0.0, (self.total - self.bytes_done) / r)

    @property
    def title(self) -> str:
        return title_from_filename(self.name)


class UploadControl:
    def __init__(self):
        self.pause = threading.Event()
        self.cancel = threading.Event()

    def reset(self) -> None:
        self.pause.clear()
        self.cancel.clear()

    @property
    def stopping(self) -> bool:
        return self.pause.is_set() or self.cancel.is_set()


class UploadPaused(Exception):
    pass


class UploadCancelled(Exception):
    pass


class ConflictDetected(Exception):
    """The destination key exists (or appeared) and no overwrite was confirmed."""


class InjectedFault(ConnectionError):
    """Raised by self-test fault injection to exercise the retry path."""


class _ProgressBody:
    """File-like body that reports bytes as botocore/urllib3 read them (seekable for retries)."""

    def __init__(self, data: bytes, on_delta: Callable[[int], None]):
        self._data = memoryview(data)
        self._pos = 0
        self._on_delta = on_delta

    def read(self, n: int = -1) -> bytes:
        if self._pos >= len(self._data):
            return b""
        end = len(self._data) if n is None or n < 0 else min(len(self._data), self._pos + n)
        chunk = self._data[self._pos:end].tobytes()
        self._pos = end
        self._on_delta(len(chunk))
        return chunk

    def seek(self, pos: int, whence: int = 0) -> int:
        new = {0: pos, 1: self._pos + pos, 2: len(self._data) + pos}[whence]
        new = max(0, min(len(self._data), new))
        if new != self._pos:
            self._on_delta(new - self._pos)
        self._pos = new
        return new

    def tell(self) -> int:
        return self._pos

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def __len__(self) -> int:
        return len(self._data)


class _Progress:
    def __init__(self, job: UploadJob):
        self.job = job
        self._lock = threading.Lock()
        self._parts: dict[int, int] = {}
        self._total = 0

    def set_base(self, done: int) -> None:
        with self._lock:
            self._total = done
            self._publish()

    def add(self, part: int, delta: int) -> None:
        with self._lock:
            self._parts[part] = self._parts.get(part, 0) + delta
            self._total += delta
            self._publish()

    def rollback(self, part: int) -> None:
        with self._lock:
            self._total -= self._parts.pop(part, 0)
            self._publish()

    def finish(self, part: int, length: int) -> None:
        with self._lock:
            self._total += length - self._parts.get(part, 0)
            self._parts[part] = length
            self._publish()

    def _publish(self) -> None:
        self.job.bytes_done = max(0, self._total)
        self.job.meter.update(self.job.bytes_done)


def choose_part_size(size: int, preferred: int) -> int:
    part = max(5 * MiB, preferred)
    while math.ceil(size / part) > MAX_PARTS:
        part *= 2
    return part


def _md5_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.md5(data).digest()).decode("ascii")


RETRYABLE_CODES = {
    "RequestTimeout", "RequestTimeTooSkewed", "SlowDown", "InternalError", "ServiceUnavailable",
    "BadDigest", "Throttling", "TooManyRequests", "IncompleteBody", "500", "502", "503", "504",
}


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (InjectedFault, ConnectionError, TimeoutError)):
        return True
    if isinstance(exc, (EndpointConnectionError, ConnectionClosedError, ReadTimeoutError, ConnectTimeoutError)):
        return True
    if isinstance(exc, ClientError):
        status = http_status(exc) or 0
        return status >= 500 or status == 429 or error_code(exc) in RETRYABLE_CODES
    if isinstance(exc, BotoCoreError):
        return True  # transport-level problems (SSL, proxy, incomplete read …)
    try:
        import urllib3.exceptions as u3

        if isinstance(exc, (u3.ProtocolError, u3.HTTPError)):
            return True
    except ImportError:  # pragma: no cover
        pass
    return False


def _unsupported_conditional(exc: BaseException) -> bool:
    return isinstance(exc, ClientError) and (
        error_code(exc) in ("NotImplemented", "501") or http_status(exc) == 501
    )


def _precondition_failed(exc: BaseException) -> bool:
    return isinstance(exc, ClientError) and (
        error_code(exc) in ("PreconditionFailed", "412", "ConditionalRequestConflict") or http_status(exc) in (409, 412)
    )


def same_content(info: ObjectInfo, size: int, sha256: str | None, md5: str | None) -> bool | None:
    """True/False when it can be decided, None when the remote object carries no usable hash."""
    if info.size != size:
        return False
    if sha256 and (info.sha256 or info.source_sha256):
        return sha256.lower() in (info.sha256, info.source_sha256)
    if md5 and info.md5_etag:
        return info.md5_etag == md5.lower()
    return None


class UploadEngine:
    def __init__(
        self,
        service: R2Service,
        config: AppConfig,
        history: History,
        resume: ResumeStore,
        ffmpeg: str | None = None,
        ffprobe: str | None = None,
        fault_injector: Callable[[UploadJob, int, int], None] | None = None,
        extra_metadata: dict[str, str] | None = None,
        retry_base_delay: float = 1.0,
    ):
        self.service = service
        self.config = config
        self.history = history
        self.resume = resume
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.fault_injector = fault_injector
        self.extra_metadata = dict(extra_metadata or {})
        self.retry_base_delay = retry_base_delay
        # None = not probed yet; False = endpoint rejected conditional headers.
        self.conditional_writes: bool | None = None

    @property
    def client(self):
        return self.service.client

    @property
    def bucket(self) -> str:
        return self.service.bucket

    # ------------------------------------------------------------------ analysis
    def analyze(self, job: UploadJob, cancel: threading.Event | None = None, remote_index=None) -> None:
        """Hash + probe the local file, then check the bucket for duplicates/conflicts."""
        job.state = JobState.ANALYZING
        job.error = ""
        done = [0]

        def on_hash(n: int) -> None:
            done[0] += n
            if job.size:
                job.message = f"ハッシュ計算 {done[0] * 100 // job.size}%"

        if job.sha256 is None:
            job.md5, job.sha256 = hash_file(job.path, on_hash, cancel)
        if job.media is None and self.ffprobe and job.category in ("mv", "bgm"):
            try:
                job.media = media.probe(self.ffprobe, job.path)
            except media.FFmpegError as exc:
                log.warning("ffprobe failed for %s: %s", job.name, exc)
        job.message = ""
        self.check_remote(job, remote_index)

    def check_remote(self, job: UploadJob, remote_index=None) -> None:
        info = self.service.head(job.key)
        job.remote_info = info
        job.duplicates = []
        if info is not None:
            same = same_content(info, job.size, job.sha256, job.md5)
            job.remote = "identical" if same else "conflict"
            if same is None:
                job.message = "同名ファイルあり（内容は未確認）"
            return
        dups: list[str] = []
        if job.sha256:
            for row in self.history.find_by_hash(self.bucket, job.sha256):
                k = row["key"]
                if k != job.key and k not in dups:
                    other = self.service.head(k)
                    if other is not None and same_content(other, other.size, job.sha256, job.md5) is not False:
                        dups.append(k)
            if remote_index is not None and not dups:
                for cand in remote_index.get(job.size, [])[:20]:
                    if cand.key == job.key or cand.key in dups:
                        continue
                    if cand.md5_etag and job.md5 and cand.md5_etag == job.md5:
                        dups.append(cand.key)
                        continue
                    if cand.is_multipart_etag:
                        full = self.service.head(cand.key)
                        if full is not None and same_content(full, job.size, job.sha256, None):
                            dups.append(cand.key)
        job.duplicates = dups
        job.remote = "content_dup" if dups else "new"

    @staticmethod
    def needs_decision(job: UploadJob) -> bool:
        return job.remote in ("identical", "conflict", "content_dup", "queue_dup", "queue_key")

    # ------------------------------------------------------------------ upload
    def run(self, job: UploadJob, control: UploadControl) -> None:
        """Upload one job end to end. Sets job.state; raises nothing for expected outcomes."""
        job.error = ""
        job.started_at = job.started_at or time.time()
        tmp: Path | None = None
        try:
            if job.decision == "skip":
                job.state = JobState.SKIPPED
                job.message = "スキップしました"
                return
            if job.sha256 is None:
                self.analyze(job)

            src, upload_sha, upload_md5 = job.path, job.sha256, job.md5
            job.compression = "none"
            mode = self.config.compression
            if mode != "none" and job.category == "mv" and self.ffmpeg:
                if mode == "faststart" and job.path.suffix.lower() not in (".mp4", ".m4v", ".mov"):
                    log.info("faststart skipped for %s (not MP4/MOV)", job.name)
                else:
                    job.state = JobState.TRANSCODING
                    job.message = "変換中 0%"
                    dur = job.media.duration if job.media else None
                    tmp = media.transcode(
                        self.ffmpeg, job.path, mode, self.config.h264_crf, dur,
                        progress=lambda f: setattr(job, "message", f"変換中 {int(f * 100)}%"),
                        cancel=control.cancel,
                    )
                    src = tmp
                    upload_md5, upload_sha = hash_file(tmp, cancel=control.cancel)
                    job.compression = mode
                    if not job.key.lower().endswith(".mp4"):
                        job.key = os.path.splitext(job.key)[0] + ".mp4"

            # Final safety check right before writing.
            existing = self.service.head(job.key)
            conditions = self._conditions_for(job, existing)

            size = src.stat().st_size
            job.upload_size = size
            job.state = JobState.UPLOADING
            job.message = ""
            job.meter.reset()
            content_type = content_type_for(job.key)
            metadata = {
                "sha256": upload_sha or "",
                "original-filename": quote(job.name, safe=""),
                "uploader": "jinn-media-uploader",
                **self.extra_metadata,
            }
            if upload_sha != job.sha256 and job.sha256:
                metadata["source-sha256"] = job.sha256

            if size >= self.config.multipart_threshold_mib * MiB:
                etag = self._upload_multipart(job, src, size, upload_sha or "", content_type, metadata, conditions, control)
            else:
                etag = self._upload_single(job, src, size, upload_md5, content_type, metadata, conditions, control)
            job.etag = etag

            job.state = JobState.VERIFYING
            info = self.service.head(job.key)
            if info is None or info.size != size:
                raise RuntimeError(f"アップロード後の検証に失敗しました（サイズ不一致: {info.size if info else 'なし'} != {size}）")
            if upload_sha and info.sha256 and info.sha256 != upload_sha:
                raise RuntimeError("アップロード後の検証に失敗しました（SHA-256 メタデータ不一致）")
            job.public_url = self.service.public_url(job.key)
            job.bytes_done = size

            self._thumbnails(job, src)

            part = choose_part_size(size, self.config.part_size_mib * MiB)
            job.history_id = self.history.record(
                bucket=self.bucket, key=job.key, public_url=job.public_url, local_path=str(job.path),
                category=job.category, size=size, sha256=upload_sha, source_sha256=job.sha256, md5=upload_md5,
                etag=job.etag, content_type=content_type,
                duration=job.media.duration if job.media else None,
                width=(job.media.display_size[0] if job.media else None),
                height=(job.media.display_size[1] if job.media else None),
                video_codec=job.media.video_codec if job.media else None,
                audio_codec=job.media.audio_codec if job.media else None,
                thumb_key=job.thumb_key, poster_key=job.poster_key,
                thumb_local=job.thumb_local, poster_local=job.poster_local, thumb_time=job.thumb_time,
                compression=job.compression, overwrote=1 if job.decision == "overwrite" else 0,
                class_a_ops=upload_class_a_ops(size, self.config.multipart_threshold_mib * MiB, part),
            )
            job.state = JobState.DONE
            job.finished_at = time.time()
            elapsed = max(0.001, job.finished_at - job.started_at)
            job.message = job.message or f"完了（平均 {size / elapsed / MiB:.1f} MB/s）"
            log.info("Uploaded %s → %s (%d bytes, %d retries)", job.name, job.key, size, job.retries)
        except UploadPaused:
            job.state = JobState.PAUSED
            job.message = "一時停止（再開できます）"
        except (UploadCancelled, Cancelled, media.FFmpegCancelled):
            job.state = JobState.CANCELLED
            job.message = "キャンセルしました"
        except ConflictDetected as exc:
            job.state = JobState.NEEDS_DECISION
            job.decision = None
            job.message = str(exc)
            try:
                self.check_remote(job)
            except Exception:  # noqa: BLE001 - best effort refresh
                pass
        except Exception as exc:  # noqa: BLE001
            job.state = JobState.FAILED
            job.error = describe_error(exc)
            job.message = "失敗: " + job.error
            log.error("Upload failed for %s: %s", job.name, job.error)
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)

    def _conditions_for(self, job: UploadJob, existing: ObjectInfo | None) -> dict:
        if existing is None:
            return {"IfNoneMatch": "*"}
        if job.decision != "overwrite":
            job.remote_info = existing
            raise ConflictDetected("同じキーのファイルが存在します。上書き・別名・スキップを選んでください。")
        confirmed = job.remote_info
        if confirmed is not None and confirmed.etag and confirmed.etag != existing.etag:
            raise ConflictDetected("確認後にリモートのファイルが変更されました。もう一度確認してください。")
        return {"IfMatch": f'"{existing.etag}"'} if existing.etag else {}

    def _call_conditional(self, fn, kwargs: dict, conditions: dict, recheck: Callable[[], None]):
        if conditions and self.conditional_writes is not False:
            try:
                resp = fn(**kwargs, **conditions)
                self.conditional_writes = True
                return resp
            except ClientError as exc:
                if _precondition_failed(exc):
                    raise ConflictDetected("書き込み直前に同じキーのファイルが見つかったため中止しました（既存ファイルは変更していません）。") from exc
                if not _unsupported_conditional(exc):
                    raise
                log.warning("Endpoint rejected conditional write headers; falling back to HEAD checks")
                self.conditional_writes = False
        recheck()
        return fn(**kwargs)

    def _recheck_for(self, job: UploadJob, conditions: dict) -> Callable[[], None]:
        def recheck() -> None:
            current = self.service.head(job.key)
            if "IfNoneMatch" in conditions and current is not None:
                raise ConflictDetected("書き込み直前に同じキーのファイルが見つかったため中止しました。")
            if "IfMatch" in conditions and current is not None and f'"{current.etag}"' != conditions["IfMatch"]:
                raise ConflictDetected("確認後にリモートのファイルが変更されました。")
        return recheck

    def _sleep_backoff(self, attempt: int, control: UploadControl) -> None:
        delay = min(30.0, self.retry_base_delay * (2 ** (attempt - 1))) * (0.5 + random.random())
        control.cancel.wait(delay)

    def _upload_single(self, job, src: Path, size: int, md5_hex: str | None, content_type: str,
                       metadata: dict, conditions: dict, control: UploadControl) -> str:
        data = src.read_bytes()
        progress = _Progress(job)
        md5_b64 = _md5_b64(data)
        attempt = 0
        while True:
            attempt += 1
            if control.cancel.is_set():
                raise UploadCancelled()
            body = _ProgressBody(data, lambda d: progress.add(1, d))
            kwargs = dict(Bucket=self.bucket, Key=job.key, Body=body, ContentLength=size,
                          ContentType=content_type, ContentMD5=md5_b64, Metadata=metadata)
            try:
                if self.fault_injector:
                    self.fault_injector(job, 1, attempt)
                resp = self._call_conditional(self.client.put_object, kwargs, conditions,
                                              self._recheck_for(job, conditions))
                self.service.count("A")
                progress.finish(1, size)
                return str(resp.get("ETag", "")).strip('"')
            except ConflictDetected:
                raise
            except Exception as exc:  # noqa: BLE001
                progress.rollback(1)
                if not is_retryable(exc) or attempt > self.config.max_retries:
                    raise
                job.retries += 1
                job.message = f"再試行 {attempt}/{self.config.max_retries}: {error_code(exc)}"
                log.warning("PUT %s failed (%s), retrying (%d/%d)", job.key, error_code(exc), attempt, self.config.max_retries)
                self._sleep_backoff(attempt, control)

    def _list_parts(self, key: str, upload_id: str) -> dict[int, tuple[str, int]]:
        out: dict[int, tuple[str, int]] = {}
        marker = 0
        while True:
            resp = self.client.list_parts(Bucket=self.bucket, Key=key, UploadId=upload_id, PartNumberMarker=marker)
            self.service.count("A")
            for p in resp.get("Parts", []):
                out[int(p["PartNumber"])] = (str(p["ETag"]).strip('"'), int(p["Size"]))
            if not resp.get("IsTruncated"):
                return out
            marker = int(resp.get("NextPartNumberMarker") or 0)
            if not marker:
                return out

    def _abort_own_upload(self, key: str, upload_id: str) -> None:
        """Abort a multipart upload this app created (never touches stored objects)."""
        try:
            self.client.abort_multipart_upload(Bucket=self.bucket, Key=key, UploadId=upload_id)
            self.service.count("A")
        except ClientError as exc:
            if error_code(exc) not in ("NoSuchUpload", "404"):
                log.warning("Could not abort multipart upload %s: %s", upload_id, describe_error(exc))

    def _upload_multipart(self, job, src: Path, size: int, sha256: str, content_type: str, metadata: dict,
                          conditions: dict, control: UploadControl) -> str:
        part_size = choose_part_size(size, self.config.part_size_mib * MiB)
        nparts = math.ceil(size / part_size)
        st = src.stat()
        is_original = src == job.path
        done: dict[int, str] = {}
        upload_id: str | None = None
        state = self.resume.load(self.bucket, job.key, str(src)) if is_original else None

        def expected_len(n: int) -> int:
            return part_size if n < nparts else size - part_size * (nparts - 1)

        if state is not None:
            fresh = (state.source_size == size and state.source_mtime_ns == st.st_mtime_ns
                     and state.part_size == part_size and state.sha256 == sha256)
            if fresh:
                try:
                    for n, (etag, psize) in self._list_parts(job.key, state.upload_id).items():
                        if 1 <= n <= nparts and psize == expected_len(n):
                            done[n] = etag
                    upload_id = state.upload_id
                    job.resumed = bool(done)
                    log.info("Resuming %s: %d/%d parts already uploaded", job.key, len(done), nparts)
                except ClientError as exc:
                    if error_code(exc) not in ("NoSuchUpload", "404"):
                        raise
                    self.resume.delete(self.bucket, job.key, str(src))
                    state = None
            else:
                self._abort_own_upload(job.key, state.upload_id)
                self.resume.delete(self.bucket, job.key, str(src))
                state = None

        if upload_id is None:
            resp = self.client.create_multipart_upload(
                Bucket=self.bucket, Key=job.key, ContentType=content_type, Metadata=metadata
            )
            self.service.count("A")
            upload_id = resp["UploadId"]
            state = ResumeState(
                bucket=self.bucket, key=job.key, upload_id=upload_id, source_path=str(src), source_size=size,
                source_mtime_ns=st.st_mtime_ns, part_size=part_size, sha256=sha256, content_type=content_type,
                created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), parts={},
            )
            if is_original:
                self.resume.save(state)
        assert state is not None
        state.parts = {str(n): e for n, e in done.items()}
        if is_original:
            self.resume.save(state)

        progress = _Progress(job)
        progress.set_base(sum(expected_len(n) for n in done))
        job.meter.reset()
        pending = iter([n for n in range(1, nparts + 1) if n not in done])
        errors: list[BaseException] = []
        stop_parts = threading.Event()

        with ThreadPoolExecutor(max_workers=self.config.concurrency, thread_name_prefix="part") as pool:
            inflight = {}

            def submit_next() -> bool:
                n = next(pending, None)
                if n is None:
                    return False
                fut = pool.submit(self._upload_part, job, src, upload_id, n, (n - 1) * part_size,
                                  expected_len(n), progress, control, stop_parts)
                inflight[fut] = n
                return True

            for _ in range(self.config.concurrency):
                if not submit_next():
                    break
            while inflight:
                finished, _ = wait(list(inflight), return_when=FIRST_COMPLETED)
                for fut in finished:
                    n = inflight.pop(fut)
                    try:
                        etag = fut.result()
                    except (UploadPaused, UploadCancelled):
                        continue
                    except Exception as exc:  # noqa: BLE001
                        errors.append(exc)
                        stop_parts.set()
                        continue
                    done[n] = etag
                    state.parts[str(n)] = etag
                    if is_original:
                        self.resume.save(state)
                    if not errors and not control.stopping:
                        submit_next()

        if control.cancel.is_set():
            self._abort_own_upload(job.key, upload_id)
            self.resume.delete(self.bucket, job.key, str(src))
            raise UploadCancelled()
        if errors:
            if not is_original:
                self._abort_own_upload(job.key, upload_id)
            raise errors[0]
        if len(done) < nparts:
            if control.pause.is_set():
                if not is_original:  # temp transcodes cannot be resumed
                    self._abort_own_upload(job.key, upload_id)
                raise UploadPaused()
            raise RuntimeError(f"一部のパートが未送信です（{len(done)}/{nparts}）")

        job.state = JobState.VERIFYING
        job.message = "結合中…"
        parts = [{"PartNumber": n, "ETag": f'"{done[n]}"'} for n in sorted(done)]
        kwargs = dict(Bucket=self.bucket, Key=job.key, UploadId=upload_id, MultipartUpload={"Parts": parts})
        try:
            resp = self._call_conditional(self.client.complete_multipart_upload, kwargs, conditions,
                                          self._recheck_for(job, conditions))
        except ConflictDetected:
            self._abort_own_upload(job.key, upload_id)
            self.resume.delete(self.bucket, job.key, str(src))
            raise
        self.service.count("A")
        self.resume.delete(self.bucket, job.key, str(src))
        return str(resp.get("ETag", "")).strip('"')

    def _upload_part(self, job, src: Path, upload_id: str, n: int, offset: int, length: int,
                     progress: _Progress, control: UploadControl, stop_parts: threading.Event) -> str:
        attempt = 0
        while True:
            attempt += 1
            if control.cancel.is_set():
                raise UploadCancelled()
            if control.pause.is_set() or stop_parts.is_set():
                raise UploadPaused()
            with open(src, "rb") as fh:
                fh.seek(offset)
                data = fh.read(length)
            if len(data) != length:
                raise RuntimeError(f"ファイルの読み込みに失敗しました（パート {n}）。ファイルが変更された可能性があります。")
            body = _ProgressBody(data, lambda d: progress.add(n, d))
            try:
                if self.fault_injector:
                    self.fault_injector(job, n, attempt)
                resp = self.client.upload_part(
                    Bucket=self.bucket, Key=job.key, UploadId=upload_id, PartNumber=n,
                    Body=body, ContentLength=length, ContentMD5=_md5_b64(data),
                )
                self.service.count("A")
                progress.finish(n, length)
                return str(resp["ETag"]).strip('"')
            except Exception as exc:  # noqa: BLE001
                progress.rollback(n)
                if not is_retryable(exc) or attempt > self.config.max_retries:
                    raise
                job.retries += 1
                job.message = f"パート{n} 再試行 {attempt}/{self.config.max_retries}: {error_code(exc)}"
                log.warning("Part %d of %s failed (%s); retry %d/%d", n, job.key, error_code(exc), attempt,
                            self.config.max_retries)
                self._sleep_backoff(attempt, control)

    # ------------------------------------------------------------------ thumbnails
    def _thumbnails(self, job: UploadJob, src: Path) -> None:
        """Make the portfolio's card thumbnail (WebP) and poster (JPEG) for an MV.

        Same sizes, codecs and default frame (10 %) as the portfolio's
        scripts/make-thumbnails.mjs. Files are cached per source file; the export
        copies them to public/thumbnails/<slug>… (or regenerates them if the slug or
        frame was changed there).
        """
        if not (self.config.generate_thumbnails and self.ffmpeg and job.category == "mv"):
            return
        job.state = JobState.THUMBNAILS
        try:
            info = job.media or media.MediaInfo()
            w, h = info.display_size
            at = default_thumb_time(info.duration)
            slug = slugify(job.title) or f"work-{(job.sha256 or job.id)[:8]}"
            cache = self.config.export_path() / "thumbnail-cache" / (job.sha256 or job.id)[:16]
            th = media.make_site_thumbnails(self.ffmpeg, src, cache / f"{slug}.webp", cache / f"{slug}-poster.jpg",
                                            at, landscape=(w or 16) > (h or 9))
            job.thumb_local, job.poster_local, job.thumb_time = str(th.thumb), str(th.poster), th.at
            if self.config.upload_thumbnails:
                job.thumb_key = self._upload_aux(th.thumb)
                job.poster_key = self._upload_aux(th.poster)
        except Exception as exc:  # noqa: BLE001 - thumbnails must not fail the main upload
            job.message = f"サムネイル生成をスキップ: {exc}"
            log.warning("Thumbnail step failed for %s: %s", job.name, exc)

    def _upload_aux(self, local: Path) -> str | None:
        """Copy a generated thumbnail to R2 under the thumbnail prefix.

        The key must equal the portfolio's thumbnailKey/posterKey, so it is never
        renamed: an existing identical object is reused, a different one is left
        untouched and the upload is skipped (returns None).
        """
        data = local.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        key = build_key(self.config.thumb_prefix, local.name)
        existing = self.service.head(key)
        if existing is not None:
            if same_content(existing, len(data), sha, hashlib.md5(data).hexdigest()):
                return key
            log.warning("%s already exists in R2 with different content; thumbnail not uploaded", key)
            return None
        kwargs = dict(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type_for(local),
                      ContentMD5=_md5_b64(data),
                      Metadata={"sha256": sha, "uploader": "jinn-media-uploader", **self.extra_metadata})

        def recheck() -> None:
            if self.service.head(key) is not None:
                raise ConflictDetected("thumbnail key appeared")

        try:
            self._call_conditional(self.client.put_object, kwargs, {"IfNoneMatch": "*"}, recheck)
        except ConflictDetected:
            log.warning("%s appeared during upload; left untouched", key)
            return None
        self.service.count("A")
        return key
