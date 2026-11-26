"""Run blocking calls (network, ffmpeg) off the GUI thread and deliver results back to it."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from ..r2client import describe_error


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(str)


class _Task(QRunnable):
    def __init__(self, fn, args, kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs
        self.signals = _Signals()

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as exc:  # noqa: BLE001
            # Windowed EXEs have no stderr; log instead of printing the traceback.
            logging.getLogger("jinn_uploader").debug("background task failed", exc_info=True)
            self.signals.failed.emit(describe_error(exc))
        else:
            self.signals.done.emit(result)


_keep: set[_Task] = set()


def run_async(fn, *args, on_done=None, on_error=None, **kwargs) -> None:
    task = _Task(fn, args, kwargs)
    _keep.add(task)

    def finished_ok(result):
        _keep.discard(task)
        if on_done:
            on_done(result)

    def finished_err(msg):
        _keep.discard(task)
        if on_error:
            on_error(msg)

    task.signals.done.connect(finished_ok)
    task.signals.failed.connect(finished_err)
    task.setAutoDelete(False)
    QThreadPool.globalInstance().start(task)
