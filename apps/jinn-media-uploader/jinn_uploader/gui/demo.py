"""Static demo data for screenshots (no network, no real files)."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..media import MediaInfo
from ..r2client import ObjectInfo, R2Service
from ..uploader import JobState, UploadJob

MiB = 1024 * 1024


def populate(win) -> None:
    cfg = win.config
    base = cfg.public_base_url

    def job(name, size, cat, key, state, done=0.0, remote="new", msg="", url=False, rate=None, dups=None):
        j = UploadJob(path=Path("D:/Jinn/Release") / name, size=size, category=cat, key=key)
        j.state = state
        j.remote = remote
        j.message = msg
        j.bytes_done = int(size * done)
        j.sha256 = "0" * 64
        if dups:
            j.duplicates = dups
        if url:
            from ..keys import public_url

            j.public_url = public_url(base, key)
        if rate:
            now = time.monotonic()
            j.meter._samples.extend([(now - 4, j.bytes_done - int(rate * 4)), (now, j.bytes_done)])
        j.media = MediaInfo(duration=213.0, width=1920, height=1080, has_video=cat == "mv", has_audio=True)
        return j

    jobs = [
        job("Neon Requiem (MV Final).mp4", 1_734 * MiB, "mv", "mv/Neon Requiem (MV Final).mp4", JobState.UPLOADING,
            0.62, rate=38.4 * MiB, msg=""),
        job("Glass Orbit.mov", 612 * MiB, "mv", "mv/Glass Orbit.mov", JobState.DONE, 1.0, url=True,
            msg="完了（平均 41.2 MB/s）"),
        job("Ambient Loop 01.wav", 48 * MiB, "bgm", "bgm/Ambient Loop 01.wav", JobState.DONE, 1.0, url=True,
            msg="完了（平均 22.8 MB/s）"),
        job("Human.mp4", 96 * MiB, "mv", "Human.mp4", JobState.NEEDS_DECISION, remote="identical",
            msg="", dups=None),
        job("Ambient Loop 01 copy.wav", 48 * MiB, "bgm", "bgm/Ambient Loop 01 copy.wav", JobState.NEEDS_DECISION,
            remote="content_dup", dups=["bgm/Ambient Loop 01.wav"]),
        job("Night Walk.mp3", 9 * MiB, "bgm", "bgm/Night Walk.mp3", JobState.READY),
        job("Tidal (Director's Cut).mp4", 2_310 * MiB, "mv", "mv/Tidal (Director's Cut).mp4", JobState.READY),
    ]
    with win.manager.lock:
        win.manager.jobs.extend(jobs)
    win.manager.current = jobs[0]

    now = datetime.now(timezone.utc)
    objects = [
        ObjectInfo("Human.mp4", 96 * MiB, "a" * 32, now - timedelta(days=3)),
        ObjectInfo("Meaning Hollow.mp4", 61 * MiB, "b" * 32, now - timedelta(days=3)),
        ObjectInfo("Million consumer full.mp4", 228 * MiB, "c" * 32 + "-15", now - timedelta(days=3)),
        ObjectInfo("Wrapped Too Beautifully.mp4", 118 * MiB, "d" * 32 + "-8", now - timedelta(days=3)),
        ObjectInfo("mv/Glass Orbit.mov", 612 * MiB, "e" * 32 + "-39", now - timedelta(minutes=4)),
        ObjectInfo("bgm/Ambient Loop 01.wav", 48 * MiB, "f" * 32 + "-3", now - timedelta(minutes=2)),
        ObjectInfo("thumbnails/glass-orbit.webp", 41_000, "1" * 32, now - timedelta(minutes=4)),
        ObjectInfo("thumbnails/glass-orbit-poster.jpg", 182_000, "2" * 32, now - timedelta(minutes=4)),
    ]
    win.obj_model.set_objects(objects)
    win.obj_prefix.addItem("bgm/", "bgm/")
    win.obj_prefix.addItem("mv/", "mv/")
    win.obj_prefix.addItem("thumbnails/", "thumbnails/")
    win._apply_obj_filter()
    win._usage = R2Service.summarize(objects)
    win._render_usage()
    win.connection_ok = True
    win._update_status()
    win.log_view.appendPlainText("10:12:03  INFO    R2 に接続しました（バケット jinn-mv-portfolio）")
    win.log_view.appendPlainText("10:12:41  INFO    7 件を追加しました（MV 4件, BGM 3件）")
    win.log_view.appendPlainText("10:13:02  INFO    アップロードを開始しました")
    win.log_view.appendPlainText("10:14:19  WARNING Part 37 of mv/Neon Requiem (MV Final).mp4 failed (RequestTimeout); retry 1/5")
