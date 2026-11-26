import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtCore = pytest.importorskip("PySide6.QtCore")
QtGui = pytest.importorskip("PySide6.QtGui")

from jinn_uploader.credentials import CredentialStore, MemoryKeyring  # noqa: E402
from jinn_uploader.gui.app import build_window, create_app  # noqa: E402
from jinn_uploader.gui.models import PROGRESS_ROLE  # noqa: E402
from jinn_uploader.uploader import JobState  # noqa: E402


@pytest.fixture
def window(make_engine, config):
    create_app(["test"])
    win = build_window(CredentialStore(backend=MemoryKeyring()), auto_startup=False)
    win.config.generate_thumbnails = False
    win.manager.config = win.config
    win.manager._engine_factory = lambda: make_engine()
    yield win
    win.manager.shutdown()
    win.timer.stop()


def _drop(win, paths):
    mime = QtCore.QMimeData()
    mime.setUrls([QtCore.QUrl.fromLocalFile(str(p)) for p in paths])
    pos = QtCore.QPointF(20, 20)
    enter = QtGui.QDragEnterEvent(pos.toPoint(), QtCore.Qt.DropAction.CopyAction, mime,
                                  QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier)
    win.dragEnterEvent(enter)
    assert enter.isAccepted()
    drop = QtGui.QDropEvent(pos, QtCore.Qt.DropAction.CopyAction, mime,
                            QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier)
    win.dropEvent(drop)


def test_drop_folder_upload_and_progress(window, tmp_path, s3):
    folder = tmp_path / "drop"
    folder.mkdir()
    (folder / "clip.mp4").write_bytes(b"v" * 2048)
    (folder / "loop.mp3").write_bytes(b"a" * 1024)
    _drop(window, [folder])
    assert window.manager.wait_analysis(30)
    window._tick()
    model = window.queue_model
    assert model.rowCount() == 2
    keys = {model.index(r, 2).data() for r in range(2)}
    assert keys == {"mv/clip.mp4", "bgm/loop.mp3"}
    window.manager.start()
    window.manager.wait(60)
    window._tick()
    assert all(model.job(r).state == JobState.DONE for r in range(2))
    assert model.index(0, 5).data(PROGRESS_ROLE) == 1000
    assert model.index(0, 8).data().startswith("https://pub-14a29b5d61e944bfa82071f29c1817f1.r2.dev/")
    assert "2/2 件完了" in window.total_label.text()


def test_destination_prefix_change_rewrites_keys(window, tmp_path):
    f = tmp_path / "x.mp4"
    f.write_bytes(b"x")
    window.add_paths([f])
    window.mv_dest.setEditText("videos/2026")
    window._on_dest_changed()
    assert window.manager.jobs[0].key == "videos/2026/x.mp4"
