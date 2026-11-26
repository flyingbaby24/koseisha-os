"""Headless verification used by CI and for troubleshooting.

``offline_selftest`` checks the packaged app (Qt, credential vault, FFmpeg) and,
given a local S3-compatible endpoint, runs the full upload flow against it.

``r2_verify`` runs the same flow against the real bucket. It only ever writes
under ``_selftest/jmu-<run id>/``; every test object carries the
``jmu-selftest-run`` metadata marker, and ``--cleanup`` deletes exactly those
objects. Before and after, the listing of every pre-existing object (key, ETag,
size, last-modified) is compared so the report proves nothing else changed.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, archive_json, media, pricing
from .config import AppConfig, ConfigStore
from .credentials import CredentialStore, R2Credentials
from .history import History, ResumeStore
from .r2client import R2Service, describe_error, make_client
from .uploader import InjectedFault, JobState, MiB, UploadControl, UploadEngine, UploadJob

SELFTEST_ROOT = "_selftest/"


class Report:
    def __init__(self, title: str):
        self.data = {
            "title": title,
            "app_version": __version__,
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
            "python": sys.version.split()[0],
            "frozen": bool(getattr(sys, "frozen", False)),
            "checks": [],
        }

    @contextlib.contextmanager
    def step(self, name: str, fatal: bool = False):
        entry = {"name": name, "ok": False}
        self.data["checks"].append(entry)
        t0 = time.monotonic()
        try:
            yield entry
            entry["ok"] = True
        except Exception as exc:  # noqa: BLE001
            entry["error"] = describe_error(exc)
            if fatal:
                raise
        finally:
            entry["seconds"] = round(time.monotonic() - t0, 2)

    def finish(self) -> dict:
        self.data["ok"] = all(c["ok"] for c in self.data["checks"]) and bool(self.data["checks"])
        self.data["finished_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return self.data


def _random_file(path: Path, size: int) -> str:
    sha = hashlib.sha256()
    with open(path, "wb") as fh:
        remaining = size
        while remaining:
            chunk = os.urandom(min(MiB, remaining))
            fh.write(chunk)
            sha.update(chunk)
            remaining -= len(chunk)
    return sha.hexdigest()


def _make_test_video(ffmpeg: str, path: Path) -> None:
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=4",
         "-f", "lavfi", "-i", "sine=frequency=330:duration=4",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
        check=True, stdin=subprocess.DEVNULL, capture_output=True, creationflags=media.CREATE_NO_WINDOW,
    )


def _snapshot(service: R2Service) -> dict[str, tuple]:
    return {o.key: (o.etag, o.size, o.last_modified.isoformat() if o.last_modified else None)
            for o in service.list_all()}


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise AssertionError(message)


# ---------------------------------------------------------------------- offline
def offline_selftest(endpoint: str | None = None) -> dict:
    rep = Report("offline self-test")
    import boto3
    import botocore

    rep.data["versions"] = {"boto3": boto3.__version__, "botocore": botocore.__version__}

    with rep.step("Qt (PySide6) widgets load") as e:
        import PySide6
        from PySide6 import QtWidgets

        e["detail"] = f"PySide6 {PySide6.__version__} ({QtWidgets.__name__})"

    with rep.step("Credential vault round trip") as e:
        store = CredentialStore(service=f"JinnMediaUploader/selftest-{uuid.uuid4().hex[:8]}")
        e["backend"] = store.backend_label
        _require(store.secure, f"insecure keyring backend: {store.backend_label}")
        if sys.platform == "win32":
            _require(store.backend_label == "Windows Credential Manager", "expected Windows Credential Manager")
        dummy = R2Credentials("0" * 32, "1" * 32, "2" * 64)
        store.save(dummy)
        try:
            _require(store.load() == dummy, "credential read back differs")
        finally:
            store.delete()
        _require(store.load() is None, "credential not removed")

    ffmpeg, ffprobe = media.find_ffmpeg("")
    with rep.step("FFmpeg probe + thumbnails") as e:
        _require(bool(ffmpeg and ffprobe), "ffmpeg/ffprobe not found next to the EXE or on PATH")
        e["ffmpeg"] = media.ffmpeg_version(ffmpeg)
        with tempfile.TemporaryDirectory() as td:
            v = Path(td) / "probe test.mp4"
            _make_test_video(ffmpeg, v)
            info = media.probe(ffprobe, v)
            _require(info.display_size == (1080, 1920), f"unexpected size {info.display_size}")
            th = media.make_video_thumbnails(ffmpeg, v, Path(td) / "th", "probe-test", info)
            e["thumb"] = th.thumb.suffix if th.thumb else None
            _require(th.poster is not None and th.poster.stat().st_size > 0, "no poster")

    if endpoint:
        _require(endpoint.startswith(("http://127.0.0.1", "http://localhost")),
                 "--endpoint is only for a local S3 test server")
        import boto3 as _b

        admin = _b.client("s3", endpoint_url=endpoint, region_name="us-east-1",
                          aws_access_key_id="local", aws_secret_access_key="local")
        cfg = ConfigStore().load()
        with contextlib.suppress(Exception):
            admin.create_bucket(Bucket=cfg.bucket)
        creds = R2Credentials("0" * 32, "local-test-key", "local-test-secret")
        service = R2Service(make_client(creds, endpoint), cfg.bucket, cfg.public_base_url)
        upload_verification(rep, service, cfg, size_mib=320, ffmpeg=ffmpeg, ffprobe=ffprobe,
                            check_public_url=False, cleanup=True)
    return rep.finish()


# ---------------------------------------------------------------------- live R2
def r2_verify(size_mib: int = 320, cleanup: bool = False, store_env_credentials: bool = False,
              forget_credentials: bool = False) -> dict:
    rep = Report("live Cloudflare R2 verification")
    store = CredentialStore()
    rep.data["credential_store"] = store.backend_label
    try:
        if store_env_credentials:
            with rep.step("Store credentials in the OS vault", fatal=True):
                env = {k: os.environ.get(k, "").strip() for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")}
                _require(all(env.values()), "R2_ACCOUNT_ID / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY are not all set")
                store.save(R2Credentials(env["R2_ACCOUNT_ID"], env["R2_ACCESS_KEY_ID"], env["R2_SECRET_ACCESS_KEY"]))

        with rep.step("Load credentials from the OS vault", fatal=True) as e:
            creds = store.load()
            _require(creds is not None, "no credentials stored — open the app's settings first")
            e["access_key"] = creds.masked_access_key()

        cfg = ConfigStore().load()
        rep.data["bucket"] = cfg.bucket
        rep.data["public_base_url"] = cfg.public_base_url
        service = R2Service(make_client(creds, cfg.endpoint_override), cfg.bucket, cfg.public_base_url)
        with rep.step("Connect (HeadBucket + ListObjectsV2)", fatal=True):
            service.test_connection()

        ffmpeg, ffprobe = media.find_ffmpeg(cfg.ffmpeg_path)
        upload_verification(rep, service, cfg, size_mib=size_mib, ffmpeg=ffmpeg, ffprobe=ffprobe,
                            check_public_url=True, cleanup=cleanup)
    finally:
        if forget_credentials:
            with rep.step("Remove credentials from the OS vault"):
                store.delete()
    return rep.finish()


def upload_verification(rep: Report, service: R2Service, base_cfg: AppConfig, size_mib: int,
                        ffmpeg: str | None, ffprobe: str | None, check_public_url: bool, cleanup: bool) -> None:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    prefix = f"{SELFTEST_ROOT}jmu-{run_id}/"
    rep.data["test_prefix"] = prefix
    marker = {"jmu-selftest-run": run_id}

    cfg = copy.deepcopy(base_cfg)
    cfg.mv_prefix, cfg.bgm_prefix, cfg.thumb_prefix = prefix + "mv/", prefix + "bgm/", prefix + "thumbnails/"
    cfg.part_size_mib, cfg.multipart_threshold_mib, cfg.concurrency, cfg.max_retries = 16, 32, 4, 5
    cfg.compression = "none"
    cfg.generate_thumbnails = bool(ffmpeg)
    cfg.upload_thumbnails = True

    work = Path(tempfile.mkdtemp(prefix="jmu-verify-"))
    cfg.export_dir = str(work / "export")
    history = History(work / "history.sqlite3")
    resume = ResumeStore(work / "resume")

    def engine(**kw) -> UploadEngine:
        return UploadEngine(service, cfg, history, resume, ffmpeg=ffmpeg, ffprobe=ffprobe,
                            extra_metadata=marker, **kw)

    before: dict = {}
    try:
        with rep.step("Snapshot existing objects (read-only)", fatal=True) as e:
            before = _snapshot(service)
            e["objects"] = len(before)
            _require(not any(k.startswith(prefix) for k in before), "test prefix already in use")

        size = size_mib * MiB
        big = work / f"jmu-selftest-{size_mib}MiB.mp4"
        with rep.step(f"Create {size_mib} MiB test file") as e:
            local_sha = _random_file(big, size)
            e["bytes"] = size
        key = cfg.mv_prefix + big.name
        nparts = math.ceil(size / (16 * MiB))

        with rep.step("Multipart upload with injected network failure, pause and resume") as e:
            control = UploadControl()
            state = {"paused": False}
            lock = threading.Lock()

            def faults(job, part, attempt):
                if part == 3 and attempt == 1:
                    raise InjectedFault("simulated connection drop on part 3")
                with lock:
                    if part == 9 and not state["paused"]:
                        state["paused"] = True
                        control.pause.set()

            job = UploadJob(path=big, size=size, category="mv", key=key)
            eng = engine(fault_injector=faults)
            eng.analyze(job)
            _require(job.remote == "new", f"unexpected remote state {job.remote}")
            eng.run(job, control)
            _require(job.state == JobState.PAUSED, f"expected PAUSED, got {job.state.value}: {job.error}")
            e["retries_before_pause"] = job.retries
            _require(job.retries >= 1, "injected failure was not retried")
            e["bytes_before_pause"] = job.bytes_done
            pending = resume.all()
            _require(len(pending) == 1 and pending[0].parts, "resume state missing after pause")
            e["parts_before_pause"] = len(pending[0].parts)

            job2 = UploadJob(path=big, size=size, category="mv", key=key)
            eng2 = engine()
            eng2.analyze(job2)
            t0 = time.monotonic()
            eng2.run(job2, UploadControl())
            dt = time.monotonic() - t0
            _require(job2.state == JobState.DONE, f"resume failed: {job2.state.value} {job2.error}")
            _require(job2.resumed, "upload did not resume from the uploaded parts")
            sent = size - e["bytes_before_pause"]
            e["resumed_bytes"] = sent
            e["resume_seconds"] = round(dt, 2)
            e["throughput_MBps"] = round(sent / dt / 1e6, 2) if dt else None
            e["public_url"] = job2.public_url
            e["conditional_writes"] = eng2.conditional_writes
            _require(not resume.all(), "resume state not cleared after completion")

        with rep.step("Verify object (size, part count, SHA-256 metadata)") as e:
            info = service.head(key)
            _require(info is not None, "object missing")
            _require(info.size == size, f"size {info.size} != {size}")
            _require(info.etag.endswith(f"-{nparts}"), f"ETag {info.etag} does not show {nparts} parts")
            _require(info.sha256 == local_sha, "sha256 metadata mismatch")
            e["etag"] = info.etag

        with rep.step("Download and compare SHA-256") as e:
            t0 = time.monotonic()
            body = service.client.get_object(Bucket=service.bucket, Key=key)["Body"]
            sha = hashlib.sha256()
            for chunk in iter(lambda: body.read(8 * MiB), b""):
                sha.update(chunk)
            dt = time.monotonic() - t0
            _require(sha.hexdigest() == local_sha, "downloaded content differs")
            e["download_MBps"] = round(size / dt / 1e6, 2) if dt else None

        if check_public_url:
            with rep.step("Public URL serves the object") as e:
                url = service.public_url(key)
                req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "jinn-media-uploader-selftest"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    e["status"] = resp.status
                    e["content_length"] = int(resp.headers.get("Content-Length", "0"))
                _require(e["status"] == 200 and e["content_length"] == size, "public URL HEAD mismatch")
                e["url"] = url

        with rep.step("Duplicate detection (same key / other key)") as e:
            eng = engine()
            same = UploadJob(path=big, size=size, category="mv", key=key)
            eng.analyze(same)
            other = UploadJob(path=big, size=size, category="mv", key=cfg.mv_prefix + "copy-of-test.mp4")
            eng.analyze(other)
            e["same_key"] = same.remote
            e["other_key"] = other.remote
            _require(same.remote == "identical", "identical file not detected")
            _require(other.remote == "content_dup" and key in other.duplicates, "content duplicate not detected")

        with rep.step("Overwrite protection (no confirmation → no write)") as e:
            small = work / "different.mp4"
            small.write_bytes(os.urandom(4096))
            before_etag = service.head(key).etag
            job3 = UploadJob(path=small, size=small.stat().st_size, category="mv", key=key)
            eng = engine()
            eng.analyze(job3)
            e["remote"] = job3.remote
            eng.run(job3, UploadControl())
            _require(job3.state == JobState.NEEDS_DECISION, f"expected NEEDS_DECISION, got {job3.state.value}")
            _require(service.head(key).etag == before_etag, "existing object was modified!")

        with rep.step("Server-side guard: If-None-Match on an existing key") as e:
            from botocore.exceptions import ClientError

            try:
                service.client.put_object(Bucket=service.bucket, Key=key, Body=b"must not land", IfNoneMatch="*",
                                          Metadata=marker)
                e["enforced"] = False
            except ClientError as exc:
                e["enforced"] = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 412
                e["code"] = exc.response.get("Error", {}).get("Code")
            # The engine always HEAD-checks first, so a server without enforcement is still safe;
            # this records whether R2 adds a second, race-free layer.
            if e["enforced"]:
                _require(service.head(key).size == size, "object changed despite 412")

        with rep.step("Single PUT upload (BGM)") as e:
            bgm = work / "jmu-selftest-bgm.mp3"
            bgm.write_bytes(os.urandom(3 * MiB))
            job4 = UploadJob(path=bgm, size=bgm.stat().st_size, category="bgm", key=cfg.bgm_prefix + bgm.name)
            eng = engine()
            eng.analyze(job4)
            eng.run(job4, UploadControl())
            _require(job4.state == JobState.DONE, job4.error)
            info = service.head(job4.key)
            e["content_type"] = info.content_type
            _require(info.content_type == "audio/mpeg", "wrong content type")

        if ffmpeg and ffprobe:
            with rep.step("FFmpeg thumbnails + Infinite Archive JSON") as e:
                mvp = work / "Selftest Portrait MV.mp4"
                _make_test_video(ffmpeg, mvp)
                job5 = UploadJob(path=mvp, size=mvp.stat().st_size, category="mv", key=cfg.mv_prefix + mvp.name)
                eng = engine()
                eng.analyze(job5)
                eng.run(job5, UploadControl())
                _require(job5.state == JobState.DONE, job5.error)
                _require(bool(job5.thumb_key and job5.poster_key), f"thumbnails not uploaded: {job5.message}")
                _require(service.head(job5.thumb_key) is not None, "thumbnail missing in bucket")
                rows = [r for r in reversed(history.recent(service.bucket)) if r["category"] in ("mv", "bgm")
                        and r["key"] in (job5.key, job4.key)]
                items = []
                for n, r in enumerate(rows):
                    items.append(archive_json.ArchiveItem.from_history(r, 900 + n, cfg.archive_artist))
                doc = archive_json.build_document(items, cfg.public_base_url, service.bucket)
                problems = archive_json.validate_document(doc)
                _require(not problems, "; ".join(problems))
                w = doc["works"][0]
                _require((w["w"], w["h"]) == (1080, 1920) and w["durationText"] == "0:04", f"bad work entry {w}")
                e["work"] = w
                e["track"] = doc["soundscape"]["tracks"][0] if doc["soundscape"]["tracks"] else None

        with rep.step("Usage and monthly cost estimate") as e:
            usage = R2Service.summarize(service.list_all())
            est = pricing.estimate(usage.total_bytes, pricing=base_cfg.pricing)
            e["objects"] = usage.object_count
            e["total_bytes"] = usage.total_bytes
            e["estimated_usd_per_month"] = round(est.total_usd, 4)

        with rep.step("Pre-existing objects unchanged") as e:
            after = _snapshot(service)
            changed = [k for k, v in before.items() if after.get(k) != v]
            outside = [k for k in after if k not in before and not k.startswith(prefix)]
            e["checked"] = len(before)
            _require(not changed, f"{len(changed)} pre-existing objects changed or missing")
            _require(not outside, f"unexpected new objects outside the test prefix: {outside[:5]}")
    finally:
        if cleanup:
            with rep.step("Clean up this run's test objects only") as e:
                removed = 0
                for o in service.list_all(prefix):
                    head = service.head(o.key)
                    if head is None or (head.metadata or {}).get("jmu-selftest-run") != run_id:
                        continue  # not ours: leave it
                    _require(o.key.startswith(prefix), "refusing to delete outside the test prefix")
                    service.client.delete_object(Bucket=service.bucket, Key=o.key)
                    removed += 1
                uploads = service.client.list_multipart_uploads(Bucket=service.bucket, Prefix=prefix).get("Uploads", [])
                for u in uploads:
                    service.client.abort_multipart_upload(Bucket=service.bucket, Key=u["Key"], UploadId=u["UploadId"])
                e["deleted_test_objects"] = removed
                e["aborted_test_uploads"] = len(uploads)
                _require(not service.list_all(prefix), "test objects remain")
                if before:
                    final = _snapshot(service)
                    _require(final == before, "bucket listing differs from the initial snapshot after cleanup")
                    e["bucket_identical_to_start"] = True
        shutil.rmtree(work, ignore_errors=True)
