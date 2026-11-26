import subprocess
import time

import pytest

from conftest import BUCKET
from jinn_uploader import media
from jinn_uploader.jobs import JobManager
from jinn_uploader.uploader import JobState


def wait_until(pred, timeout=30):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.05)
    return False


def test_job_manager_folder_drop_duplicates_and_upload(tmp_path, make_engine, config, s3):
    drop = tmp_path / "Release"
    drop.mkdir()
    (drop / "Song.mp4").write_bytes(b"video-bytes")
    (drop / "Theme.mp3").write_bytes(b"audio-bytes")
    (drop / "Theme copy.mp3").write_bytes(b"audio-bytes")  # same content as Theme.mp3
    s3.put_object(Bucket=BUCKET, Key="mv/Song.mp4", Body=b"someone else's MV")

    mgr = JobManager(config, make_engine)
    added, skipped = mgr.add_paths([drop])
    assert skipped == 0 and len(added) == 3
    assert mgr.add_paths([drop / "Song.mp4"]) == ([], 1)  # already queued
    assert mgr.wait_analysis(30)

    by_name = {j.name: j for j in mgr.jobs}
    assert by_name["Song.mp4"].key == "mv/Song.mp4"
    assert by_name["Theme.mp3"].key == "audio/Theme.mp3"
    assert by_name["Song.mp4"].state == JobState.NEEDS_DECISION and by_name["Song.mp4"].remote == "conflict"
    dup = by_name["Theme copy.mp3"] if by_name["Theme copy.mp3"].remote == "queue_dup" else by_name["Theme.mp3"]
    assert dup.state == JobState.NEEDS_DECISION and dup.remote == "queue_dup"

    assert {j.name for j in mgr.undecided()} == {"Song.mp4", dup.name}
    mgr.apply_decision(by_name["Song.mp4"], "rename")
    assert by_name["Song.mp4"].key == "mv/Song (2).mp4"
    mgr.apply_decision(dup, "skip")

    mgr.start()
    mgr.wait(60)
    states = {j.name: j.state for j in mgr.jobs}
    assert states["Song.mp4"] == JobState.DONE
    assert states[dup.name] == JobState.SKIPPED
    keys = {o["Key"] for o in s3.list_objects_v2(Bucket=BUCKET)["Contents"]}
    assert keys == {"mv/Song.mp4", "mv/Song (2).mp4", "audio/Theme.mp3"} or keys == {
        "mv/Song.mp4", "mv/Song (2).mp4", "audio/Theme copy.mp3"}
    assert s3.get_object(Bucket=BUCKET, Key="mv/Song.mp4")["Body"].read() == b"someone else's MV"
    totals = mgr.totals()
    assert totals["completed"] == 2 and totals["failed"] == 0
    mgr.shutdown()


def test_category_change_and_prefix_update(tmp_path, make_engine, config, s3):
    f = tmp_path / "loop.wav"
    f.write_bytes(b"wav")
    mgr = JobManager(config, make_engine)
    (job,), _ = mgr.add_paths([f])
    assert mgr.wait_analysis(30)
    assert job.key == "audio/loop.wav"
    mgr.set_category(job, "other")
    assert job.key == "misc/loop.wav"
    config.other_prefix = "extras/2026/"
    mgr.apply_prefixes()
    assert job.key == "extras/2026/loop.wav"
    mgr.set_key(job, "custom/dir/loop.wav")
    config.other_prefix = "ignored/"
    mgr.apply_prefixes()
    assert job.key == "custom/dir/loop.wav"  # manual keys are kept
    mgr.shutdown()


def test_manager_works_offline_then_checks_at_start(tmp_path, config):
    def no_engine():
        raise RuntimeError("not configured")

    f = tmp_path / "a.mp4"
    f.write_bytes(b"a")
    mgr = JobManager(config, no_engine)
    (job,), _ = mgr.add_paths([f])
    assert mgr.wait_analysis(30)
    assert job.state == JobState.READY and job.remote == "unknown" and job.sha256
    with pytest.raises(RuntimeError):
        mgr.start()
    mgr.shutdown()


def _make_video(ffmpeg, path, w, h, seconds=3, rotate=None):
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
           f"testsrc2=size={w}x{h}:rate=25:duration={seconds}", "-f", "lavfi", "-i",
           f"sine=frequency=440:duration={seconds}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest"]
    if rotate is not None:
        cmd += ["-metadata:s:v:0", f"rotate={rotate}"]
    subprocess.run(cmd + [str(path)], check=True)
    return path


def test_probe_thumbnails_and_compression(tmp_path, ffmpeg_bins):
    ffmpeg, ffprobe = ffmpeg_bins
    src = _make_video(ffmpeg, tmp_path / "Portrait MV.mp4", 1080, 1920)
    info = media.probe(ffprobe, src)
    assert info.has_video and info.has_audio
    assert info.display_size == (1080, 1920)
    assert 2.5 < info.duration < 3.5

    th = media.make_site_thumbnails(ffmpeg, src, tmp_path / "t" / "portrait-mv.webp",
                                    tmp_path / "t" / "portrait-mv-poster.jpg", 0.3, landscape=False)
    t, p = media.probe(ffprobe, th.thumb), media.probe(ffprobe, th.poster)
    # Same derivatives as the portfolio's scripts/make-thumbnails.mjs (480/720 px wide when vertical).
    assert (t.video_codec, t.width, t.height) == ("webp", 480, 854)
    assert (p.video_codec, p.width, p.height) == ("mjpeg", 720, 1280)
    land = _make_video(ffmpeg, tmp_path / "land.mp4", 1920, 1080, seconds=2)
    th2 = media.make_site_thumbnails(ffmpeg, land, tmp_path / "t" / "l.webp", tmp_path / "t" / "l-poster.jpg",
                                     0.2, landscape=True)
    assert (media.probe(ffprobe, th2.thumb).width, media.probe(ffprobe, th2.poster).width) == (800, 1280)

    progress = []
    out = media.transcode(ffmpeg, src, "h264", crf=30, duration=info.duration, progress=progress.append)
    try:
        assert out.stat().st_size > 0 and progress[-1] == 1.0
        assert media.probe(ffprobe, out).video_codec == "h264"
    finally:
        out.unlink(missing_ok=True)

    fast = media.transcode(ffmpeg, src, "faststart")
    try:
        head = fast.read_bytes()[:4096]
        assert head.find(b"moov") != -1 and (head.find(b"mdat") == -1 or head.find(b"moov") < head.find(b"mdat"))
    finally:
        fast.unlink(missing_ok=True)


def test_engine_generates_and_uploads_thumbnails(tmp_path, make_engine, ffmpeg_bins, s3):
    ffmpeg, ffprobe = ffmpeg_bins
    src = _make_video(ffmpeg, tmp_path / "Night Drive.mp4", 1280, 720)
    engine = make_engine()
    engine.ffmpeg, engine.ffprobe = ffmpeg, ffprobe
    engine.config.generate_thumbnails = True
    engine.config.upload_thumbnails = True
    from jinn_uploader.uploader import UploadControl, UploadJob

    job = UploadJob(path=src, size=src.stat().st_size, category="mv", key="mv/Night Drive.mp4")
    engine.analyze(job)
    assert job.media.duration and job.media.display_size == (1280, 720)
    engine.run(job, UploadControl())
    assert job.state == JobState.DONE, job.error
    assert job.poster_key == "thumbnails/night-drive-poster.jpg"
    assert job.thumb_key == "thumbnails/night-drive.webp"
    assert job.thumb_time == 0.3  # 10 % of the 3 s clip, like make-thumbnails.mjs
    s3.head_object(Bucket=BUCKET, Key=job.poster_key)
    row = engine.history.latest_for_key(BUCKET, job.key)
    assert row["thumb_time"] == 0.3 and row["thumb_local"].endswith("night-drive.webp")

    # Another MV with the same title: its R2 copy would need the same key, so it is skipped,
    # never renamed and never written over the first one.
    first = s3.get_object(Bucket=BUCKET, Key="thumbnails/night-drive.webp")["Body"].read()
    (tmp_path / "other").mkdir()
    src2 = _make_video(ffmpeg, tmp_path / "other" / "Night Drive.mp4", 640, 360)
    job2 = UploadJob(path=src2, size=src2.stat().st_size, category="mv", key="mv/Night Drive v2.mp4")
    job2.media = media.probe(ffprobe, src2)
    engine.run(job2, UploadControl())
    assert job2.state == JobState.DONE, job2.error
    assert job2.thumb_key is None and job2.thumb_local != job.thumb_local
    assert s3.get_object(Bucket=BUCKET, Key="thumbnails/night-drive.webp")["Body"].read() == first

    # BGM gets no thumbnail (the soundscape has no image field).
    wav = tmp_path / "loop.wav"
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=220:duration=2", str(wav)], check=True)
    job3 = UploadJob(path=wav, size=wav.stat().st_size, category="bgm", key="audio/loop.wav")
    engine.run(job3, UploadControl())
    assert job3.state == JobState.DONE and job3.thumb_local is None
