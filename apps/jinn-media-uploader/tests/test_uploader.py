import hashlib
import threading

import pytest

from conftest import BUCKET, PUBLIC, write_random
from jinn_uploader.uploader import (
    InjectedFault,
    JobState,
    MiB,
    UploadControl,
    UploadJob,
    choose_part_size,
)


def make_job(path, key, category="mv"):
    return UploadJob(path=path, size=path.stat().st_size, category=category, key=key)


def snapshot(s3):
    out = {}
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
        for o in page.get("Contents", []):
            out[o["Key"]] = (o["ETag"], o["Size"], o["LastModified"])
    return out


def sha256_of(s3, key):
    return hashlib.sha256(s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()).hexdigest()


class PartRecorder:
    def __init__(self):
        self.calls = []
        self.lock = threading.Lock()

    def __call__(self, job, part, attempt):
        with self.lock:
            self.calls.append((part, attempt))


def test_single_upload_sets_metadata_url_and_history(tmp_path, make_engine, s3):
    f = tmp_path / "Theme Song.mp3"
    f.write_bytes(b"x" * 1000)
    engine = make_engine()
    job = make_job(f, "bgm/Theme Song.mp3", "bgm")
    engine.analyze(job)
    assert job.remote == "new"
    engine.run(job, UploadControl())
    assert job.state == JobState.DONE, job.error
    head = s3.head_object(Bucket=BUCKET, Key="bgm/Theme Song.mp3")
    assert head["ContentType"] == "audio/mpeg"
    assert head["Metadata"]["sha256"] == hashlib.sha256(b"x" * 1000).hexdigest()
    assert job.public_url == PUBLIC + "/bgm/Theme%20Song.mp3"
    assert engine.history.find_by_hash(BUCKET, job.sha256)[0]["key"] == "bgm/Theme Song.mp3"


def test_multipart_equal_parts_retry_and_integrity(tmp_path, make_engine, s3):
    f = write_random(tmp_path / "mv.mp4", 23 * MiB + 12345)
    rec = PartRecorder()
    fail_plan = {(2, 1), (4, 1), (4, 2)}

    def injector(job, part, attempt):
        rec(job, part, attempt)
        if (part, attempt) in fail_plan:
            raise InjectedFault(f"simulated network drop on part {part}")

    engine = make_engine(fault_injector=injector)
    job = make_job(f, "mv/mv.mp4")
    engine.run(job, UploadControl())
    assert job.state == JobState.DONE, job.error
    assert job.retries == 3
    assert sha256_of(s3, "mv/mv.mp4") == hashlib.sha256(f.read_bytes()).hexdigest()
    # R2 rule: every part except the last has the same size.
    resp = s3.head_object(Bucket=BUCKET, Key="mv/mv.mp4")
    assert resp["ContentLength"] == f.stat().st_size
    assert resp["ETag"].strip('"').endswith("-5")  # 5 parts of 5 MiB (last is smaller)
    assert job.bytes_done == f.stat().st_size
    assert not engine.resume.all()  # resume state cleaned after completion


def test_choose_part_size_respects_part_limit():
    assert choose_part_size(100 * MiB, 16 * MiB) == 16 * MiB
    size = 200 * 1024 * MiB  # 200 GiB
    p = choose_part_size(size, 16 * MiB)
    assert -(-size // p) <= 10_000
    assert choose_part_size(10, 1) == 5 * MiB


def test_failed_upload_resumes_without_resending_parts(tmp_path, make_engine, s3):
    f = write_random(tmp_path / "big.mov", 30 * MiB, seed=2)
    calls = PartRecorder()

    def always_fail_part5(job, part, attempt):
        calls(job, part, attempt)
        if part == 5:
            raise InjectedFault("part 5 keeps failing")

    engine = make_engine(fault_injector=always_fail_part5)
    job = make_job(f, "mv/big.mov")
    engine.run(job, UploadControl())
    assert job.state == JobState.FAILED
    assert engine.resume.all(), "resume state must survive a failure"
    assert not s3.list_objects_v2(Bucket=BUCKET).get("Contents")  # nothing visible yet

    calls2 = PartRecorder()
    engine2 = make_engine(fault_injector=calls2)
    job2 = make_job(f, "mv/big.mov")
    engine2.run(job2, UploadControl())
    assert job2.state == JobState.DONE, job2.error
    assert job2.resumed
    sent_again = {p for p, _ in calls2.calls}
    assert 5 in sent_again and len(sent_again) < 6, sent_again
    assert sha256_of(s3, "mv/big.mov") == hashlib.sha256(f.read_bytes()).hexdigest()


def test_pause_then_resume(tmp_path, make_engine, s3):
    f = write_random(tmp_path / "p.mp4", 40 * MiB, seed=3)
    control = UploadControl()

    def pause_at_part_3(job, part, attempt):
        if part == 3:
            control.pause.set()

    engine = make_engine(fault_injector=pause_at_part_3)
    engine.config.concurrency = 1
    job = make_job(f, "mv/p.mp4")
    engine.run(job, control)
    assert job.state == JobState.PAUSED
    assert 0 < job.bytes_done < f.stat().st_size

    engine2 = make_engine()
    job2 = make_job(f, "mv/p.mp4")
    engine2.run(job2, UploadControl())
    assert job2.state == JobState.DONE and job2.resumed
    assert sha256_of(s3, "mv/p.mp4") == hashlib.sha256(f.read_bytes()).hexdigest()


def test_cancel_aborts_own_multipart_upload(tmp_path, make_engine, s3):
    f = write_random(tmp_path / "c.mp4", 20 * MiB, seed=4)
    control = UploadControl()

    def cancel_at_2(job, part, attempt):
        if part == 2:
            control.cancel.set()

    engine = make_engine(fault_injector=cancel_at_2)
    engine.config.concurrency = 1
    job = make_job(f, "mv/c.mp4")
    engine.run(job, control)
    assert job.state == JobState.CANCELLED
    assert not s3.list_multipart_uploads(Bucket=BUCKET).get("Uploads")
    assert not engine.resume.all()


def test_existing_object_is_never_overwritten_without_confirmation(tmp_path, make_engine, s3):
    s3.put_object(Bucket=BUCKET, Key="Human.mp4", Body=b"original bytes")
    before = snapshot(s3)
    f = write_random(tmp_path / "Human.mp4", 12 * MiB, seed=5)
    engine = make_engine()
    job = make_job(f, "Human.mp4")
    engine.analyze(job)
    assert job.remote == "conflict"
    engine.run(job, UploadControl())
    assert job.state == JobState.NEEDS_DECISION
    assert snapshot(s3) == before

    job.decision = "upload"  # "upload anyway" is not an overwrite
    engine.run(job, UploadControl())
    assert job.state == JobState.NEEDS_DECISION
    assert snapshot(s3) == before


def test_overwrite_only_after_explicit_decision(tmp_path, make_engine, s3):
    s3.put_object(Bucket=BUCKET, Key="mv/x.mp4", Body=b"old")
    f = tmp_path / "x.mp4"
    f.write_bytes(b"new content")
    engine = make_engine()
    job = make_job(f, "mv/x.mp4")
    engine.analyze(job)
    job.decision = "overwrite"
    engine.run(job, UploadControl())
    assert job.state == JobState.DONE, job.error
    assert s3.get_object(Bucket=BUCKET, Key="mv/x.mp4")["Body"].read() == b"new content"


def test_overwrite_refused_if_remote_changed_after_confirmation(tmp_path, make_engine, s3):
    s3.put_object(Bucket=BUCKET, Key="mv/y.mp4", Body=b"v1")
    f = tmp_path / "y.mp4"
    f.write_bytes(b"mine")
    engine = make_engine()
    job = make_job(f, "mv/y.mp4")
    engine.analyze(job)
    job.decision = "overwrite"
    s3.put_object(Bucket=BUCKET, Key="mv/y.mp4", Body=b"v2 by someone else")
    engine.run(job, UploadControl())
    assert job.state == JobState.NEEDS_DECISION
    assert s3.get_object(Bucket=BUCKET, Key="mv/y.mp4")["Body"].read() == b"v2 by someone else"


def test_object_appearing_mid_upload_is_protected(tmp_path, make_engine, s3):
    f = write_random(tmp_path / "race.mp4", 15 * MiB, seed=6)

    def someone_else_writes(job, part, attempt):
        if part == 2 and attempt == 1:
            s3.put_object(Bucket=BUCKET, Key="mv/race.mp4", Body=b"their file")

    engine = make_engine(fault_injector=someone_else_writes)
    engine.config.concurrency = 1
    job = make_job(f, "mv/race.mp4")
    engine.run(job, UploadControl())
    assert job.state == JobState.NEEDS_DECISION
    assert s3.get_object(Bucket=BUCKET, Key="mv/race.mp4")["Body"].read() == b"their file"
    assert not s3.list_multipart_uploads(Bucket=BUCKET).get("Uploads")


def test_duplicate_detection_identical_and_other_key(tmp_path, make_engine, s3):
    f = tmp_path / "same.mp3"
    f.write_bytes(b"identical")
    engine = make_engine()
    job = make_job(f, "bgm/same.mp3", "bgm")
    engine.run(job, UploadControl())
    assert job.state == JobState.DONE

    again = make_job(f, "bgm/same.mp3", "bgm")
    engine.analyze(again)
    assert again.remote == "identical"

    other_key = make_job(f, "bgm/renamed.mp3", "bgm")
    engine.analyze(other_key)
    assert other_key.remote == "content_dup" and other_key.duplicates == ["bgm/same.mp3"]

    # Objects uploaded by other tools: matched via single-part ETag (MD5) from the listing.
    s3.put_object(Bucket=BUCKET, Key="legacy/old.mp3", Body=b"legacy bytes")
    g = tmp_path / "copy.mp3"
    g.write_bytes(b"legacy bytes")
    engine.history.path.unlink()  # forget local history: detection must work from R2 alone
    fresh = make_engine()
    index = {}
    for o in fresh.service.list_all():
        index.setdefault(o.size, []).append(o)
    j = make_job(g, "bgm/copy.mp3", "bgm")
    fresh.analyze(j, remote_index=index)
    assert j.remote == "content_dup" and "legacy/old.mp3" in j.duplicates


def test_skip_decision(tmp_path, make_engine, s3):
    f = tmp_path / "s.mp3"
    f.write_bytes(b"s")
    engine = make_engine()
    job = make_job(f, "bgm/s.mp3", "bgm")
    job.decision = "skip"
    engine.run(job, UploadControl())
    assert job.state == JobState.SKIPPED
    assert not s3.list_objects_v2(Bucket=BUCKET).get("Contents")


@pytest.mark.large
def test_large_multipart_upload_330mib(tmp_path, make_engine, s3):
    """300MB+ upload through the real multipart path (16 MiB parts, 4 in parallel)."""
    f = write_random(tmp_path / "large-mv.mp4", 330 * MiB, seed=7)
    rec = PartRecorder()

    def injector(job, part, attempt):
        rec(job, part, attempt)
        if part == 7 and attempt == 1:
            raise InjectedFault("simulated drop")

    engine = make_engine(fault_injector=injector)
    engine.config.part_size_mib = 16
    engine.config.multipart_threshold_mib = 32
    job = make_job(f, "mv/large-mv.mp4")
    engine.run(job, UploadControl())
    assert job.state == JobState.DONE, job.error
    head = s3.head_object(Bucket=BUCKET, Key="mv/large-mv.mp4")
    assert head["ContentLength"] == 330 * MiB
    assert head["ETag"].strip('"').endswith("-21")
    assert job.retries == 1
    assert sha256_of(s3, "mv/large-mv.mp4") == hashlib.sha256(f.read_bytes()).hexdigest()
