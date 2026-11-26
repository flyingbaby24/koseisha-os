"""Queue of upload jobs with background analysis and a sequential upload worker.

GUI-independent so it can be unit-tested; the GUI polls job fields for display.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
from pathlib import Path
from typing import Callable, Iterable

from .config import AppConfig
from .keys import build_key, classify, rename_candidate, validate_key
from .r2client import ObjectInfo, describe_error
from .scanner import Cancelled, scan_paths
from .uploader import (
    ACTIVE_STATES,
    TERMINAL_STATES,
    JobState,
    UploadControl,
    UploadEngine,
    UploadJob,
)

log = logging.getLogger("jinn_uploader")


class NotConnected(Exception):
    pass


class JobManager:
    def __init__(self, config: AppConfig, engine_factory: Callable[[], UploadEngine]):
        self.config = config
        self._engine_factory = engine_factory
        self._engine: UploadEngine | None = None
        self.jobs: list[UploadJob] = []
        self.lock = threading.RLock()
        self.control = UploadControl()
        self._analysis_q: queue.Queue[UploadJob | None] = queue.Queue()
        self._analysis_cancel = threading.Event()
        self._analysis_thread = threading.Thread(target=self._analysis_loop, name="analysis", daemon=True)
        self._analysis_thread.start()
        self._upload_thread: threading.Thread | None = None
        self._remote_index: dict[int, list[ObjectInfo]] | None = None
        self.current: UploadJob | None = None
        self.on_finished: Callable[[], None] | None = None

    # ------------------------------------------------------------------ engine
    def engine(self) -> UploadEngine:
        if self._engine is None:
            self._engine = self._engine_factory()
        return self._engine

    def reset_engine(self) -> None:
        """Call after credentials/settings change."""
        self._engine = None
        self._remote_index = None

    def try_engine(self) -> UploadEngine | None:
        try:
            return self.engine()
        except Exception as exc:  # noqa: BLE001
            log.info("R2 not connected: %s", exc)
            return None

    def set_remote_objects(self, objects: list[ObjectInfo]) -> None:
        index: dict[int, list[ObjectInfo]] = {}
        for o in objects:
            index.setdefault(o.size, []).append(o)
        self._remote_index = index

    # ------------------------------------------------------------------ queue
    def default_key(self, job_or_name, category: str, subdirs: tuple[str, ...] = ()) -> str:
        name = job_or_name.name if isinstance(job_or_name, UploadJob) else str(job_or_name)
        if isinstance(job_or_name, UploadJob):
            subdirs = job_or_name.subdirs
        return build_key(
            self.config.prefix_for(category), name, subdirs if self.config.keep_folder_structure else ()
        )

    def add_paths(self, paths: Iterable[str | Path]) -> tuple[list[UploadJob], int]:
        scanned = scan_paths(paths)
        added: list[UploadJob] = []
        skipped = 0
        with self.lock:
            existing = {os.path.normcase(str(j.path.resolve())) for j in self.jobs if j.state not in TERMINAL_STATES}
            for f in scanned:
                norm = os.path.normcase(str(f.path.resolve()))
                if norm in existing:
                    skipped += 1
                    continue
                category = classify(f.path)
                try:
                    key = build_key(
                        self.config.prefix_for(category), f.path.name,
                        f.subdirs if self.config.keep_folder_structure else (),
                    )
                except ValueError as exc:
                    log.warning("Skipped %s: %s", f.path, exc)
                    skipped += 1
                    continue
                job = UploadJob(path=f.path, size=f.size, category=category, key=key, subdirs=f.subdirs)
                self.jobs.append(job)
                existing.add(norm)
                added.append(job)
        for job in added:
            self._analysis_q.put(job)
        return added, skipped

    def remove(self, jobs: Iterable[UploadJob]) -> int:
        n = 0
        with self.lock:
            for job in list(jobs):
                if job is self.current or job.state in ACTIVE_STATES:
                    continue
                if job in self.jobs:
                    self.jobs.remove(job)
                    n += 1
        return n

    def clear_finished(self) -> int:
        with self.lock:
            before = len(self.jobs)
            self.jobs = [j for j in self.jobs if j.state not in TERMINAL_STATES]
            return before - len(self.jobs)

    def set_category(self, job: UploadJob, category: str) -> None:
        if job.state in ACTIVE_STATES or job.state == JobState.DONE:
            return
        job.category = category
        if not job.key_edited:
            job.key = self.default_key(job, category)
        self.recheck(job)

    def set_key(self, job: UploadJob, key: str) -> None:
        validate_key(key)
        if job.state in ACTIVE_STATES or job.state == JobState.DONE:
            return
        job.key = key
        job.key_edited = True
        self.recheck(job)

    def apply_prefixes(self) -> None:
        """Re-derive keys after the MV/BGM destination changed (manually edited keys are kept)."""
        with self.lock:
            for job in self.jobs:
                if job.state in (JobState.PENDING, JobState.READY, JobState.NEEDS_DECISION, JobState.FAILED) and not job.key_edited:
                    new = self.default_key(job, job.category)
                    if new != job.key:
                        job.key = new
                        self.recheck(job)

    def recheck(self, job: UploadJob) -> None:
        job.decision = None
        if job.state not in ACTIVE_STATES and job.state != JobState.DONE:
            job.state = JobState.PENDING
            job.remote = "unknown"
            self._analysis_q.put(job)

    def reanalyze_all(self) -> None:
        with self.lock:
            for job in self.jobs:
                if job.state in (JobState.PENDING, JobState.READY, JobState.NEEDS_DECISION, JobState.FAILED):
                    self.recheck(job)

    # ------------------------------------------------------------------ analysis
    def _queue_conflicts(self, job: UploadJob) -> None:
        """Flag a job whose key or content repeats an earlier job in the queue."""
        with self.lock:
            if job not in self.jobs:
                return
            mine = self.jobs.index(job)
            earlier = [
                j for j in self.jobs[:mine]
                if j.state not in (JobState.SKIPPED, JobState.CANCELLED, JobState.FAILED)
            ]
        if job.remote not in ("new", "unknown"):
            return
        for other in earlier:
            if other.key == job.key:
                job.remote = "queue_key"
                job.duplicates = [f"{other.name}（キュー内・同じ保存先）"]
                return
            if job.sha256 and other.sha256 == job.sha256:
                job.remote = "queue_dup"
                job.duplicates = [f"{other.name}（キュー内・同一内容）"]
                return

    def _analysis_loop(self) -> None:
        while True:
            job = self._analysis_q.get()
            if job is None:
                return
            with self.lock:
                if job not in self.jobs or job.state in ACTIVE_STATES or job.state in TERMINAL_STATES:
                    continue
            engine = self.try_engine()
            try:
                if engine is None:
                    from .scanner import hash_file

                    job.state = JobState.ANALYZING
                    if job.sha256 is None:
                        job.md5, job.sha256 = hash_file(job.path, cancel=self._analysis_cancel)
                    job.remote = "unknown"
                    job.message = "R2未接続（開始時に確認します）"
                else:
                    if self._remote_index is None:
                        try:
                            self.set_remote_objects(engine.service.list_all())
                        except Exception as exc:  # noqa: BLE001
                            log.warning("Listing bucket for duplicate detection failed: %s", describe_error(exc))
                            self._remote_index = {}
                    engine.analyze(job, cancel=self._analysis_cancel, remote_index=self._remote_index)
                self._queue_conflicts(job)
                if job.remote in ("identical", "conflict", "content_dup", "queue_dup", "queue_key"):
                    job.state = JobState.NEEDS_DECISION
                else:
                    job.state = JobState.READY
            except Cancelled:
                job.state = JobState.PENDING
            except Exception as exc:  # noqa: BLE001
                job.state = JobState.FAILED
                job.error = describe_error(exc)
                job.message = "解析失敗: " + job.error
                log.error("Analysis failed for %s: %s", job.name, job.error)

    def analysis_pending(self) -> bool:
        with self.lock:
            return any(j.state in (JobState.PENDING, JobState.ANALYZING) for j in self.jobs)

    def wait_analysis(self, timeout: float = 600) -> bool:
        import time

        end = time.monotonic() + timeout
        while self.analysis_pending():
            if time.monotonic() > end:
                return False
            time.sleep(0.05)
        return True

    # ------------------------------------------------------------------ decisions
    def undecided(self) -> list[UploadJob]:
        with self.lock:
            return [j for j in self.jobs if j.state == JobState.NEEDS_DECISION and j.decision is None]

    def apply_decision(self, job: UploadJob, decision: str) -> None:
        if decision not in ("upload", "rename", "overwrite", "skip"):
            raise ValueError(decision)
        if decision == "rename":
            engine = self.try_engine()
            with self.lock:
                taken = {j.key for j in self.jobs if j is not job}

            def exists(k: str) -> bool:
                return k in taken or (engine is not None and engine.service.head(k) is not None)

            job.key = rename_candidate(job.key, exists)
            job.key_edited = True
            job.remote = "new"
            job.remote_info = None
            job.decision = "upload"
        else:
            job.decision = decision
        job.state = JobState.SKIPPED if decision == "skip" else JobState.READY
        if decision == "skip":
            job.message = "スキップ（重複/既存）"

    # ------------------------------------------------------------------ upload worker
    @property
    def running(self) -> bool:
        return self._upload_thread is not None and self._upload_thread.is_alive()

    def start(self) -> bool:
        if self.running:
            return False
        self.engine()  # raise early if not connected
        self.control.reset()
        with self.lock:
            for j in self.jobs:
                if j.state == JobState.PAUSED:
                    j.state = JobState.READY
        self._upload_thread = threading.Thread(target=self._upload_loop, name="uploader", daemon=True)
        self._upload_thread.start()
        return True

    def _next_ready(self) -> UploadJob | None:
        with self.lock:
            for j in self.jobs:
                if j.state == JobState.READY:
                    return j
        return None

    def _upload_loop(self) -> None:
        import time

        engine = self.engine()
        try:
            while not self.control.stopping:
                job = self._next_ready()
                if job is None:
                    if self.analysis_pending():
                        time.sleep(0.1)
                        continue
                    break
                self.current = job
                engine.run(job, self.control)
                self.current = None
                if job.state == JobState.CANCELLED and not self.control.pause.is_set():
                    # Cancelling one job stops only that job.
                    self.control.cancel.clear()
        finally:
            self.current = None
            if self.on_finished:
                try:
                    self.on_finished()
                except Exception:  # noqa: BLE001
                    pass

    def pause(self) -> None:
        self.control.pause.set()

    def cancel_current(self) -> None:
        if self.current is not None:
            self.control.cancel.set()

    def cancel(self, jobs: Iterable[UploadJob]) -> None:
        for job in jobs:
            if job is self.current:
                self.control.cancel.set()
            elif job.state not in TERMINAL_STATES and job.state not in ACTIVE_STATES:
                job.state = JobState.CANCELLED
                job.message = "キャンセルしました"
                self._abort_resume_state(job)

    def _abort_resume_state(self, job: UploadJob) -> None:
        engine = self.try_engine()
        if engine is None:
            return
        state = engine.resume.load(engine.bucket, job.key, str(job.path))
        if state is not None:
            engine._abort_own_upload(state.key, state.upload_id)
            engine.resume.delete(engine.bucket, job.key, str(job.path))

    def retry_failed(self) -> int:
        n = 0
        with self.lock:
            for j in self.jobs:
                if j.state in (JobState.FAILED, JobState.PAUSED, JobState.CANCELLED):
                    if j.sha256 is None or j.remote == "unknown":
                        self.recheck(j)
                    else:
                        j.state = JobState.READY
                        j.error = ""
                        j.message = "再試行待ち"
                    n += 1
        return n

    def wait(self, timeout: float | None = None) -> None:
        if self._upload_thread is not None:
            self._upload_thread.join(timeout)

    def shutdown(self) -> None:
        self._analysis_cancel.set()
        self.control.pause.set()
        self._analysis_q.put(None)
        self.wait(timeout=60)

    # ------------------------------------------------------------------ totals
    def totals(self) -> dict:
        with self.lock:
            jobs = [j for j in self.jobs if j.state not in (JobState.SKIPPED, JobState.CANCELLED)]
            total = sum(j.total for j in jobs)
            done = sum(j.total if j.state == JobState.DONE else j.bytes_done for j in jobs)
            current = self.current
        rate = current.rate() if current else None
        remaining = max(0, total - done)
        return {
            "total": total,
            "done": done,
            "rate": rate,
            "eta": (remaining / rate) if rate else None,
            "count": len(jobs),
            "completed": sum(1 for j in jobs if j.state == JobState.DONE),
            "failed": sum(1 for j in jobs if j.state == JobState.FAILED),
        }
