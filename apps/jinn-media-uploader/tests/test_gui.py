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
    assert keys == {"mv/clip.mp4", "audio/loop.mp3"}
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


def test_export_dialog_writes_portfolio_bundle(window, tmp_path, s3, monkeypatch, ffmpeg_bins):
    import json
    import shutil
    import subprocess
    from pathlib import Path

    from PySide6.QtWidgets import QMessageBox

    from jinn_uploader import portfolio
    from jinn_uploader.gui.dialogs import ExportDialog

    ffmpeg, ffprobe = ffmpeg_bins
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    pf = tmp_path / "Jinn-Portfolio"
    shutil.copytree(Path(__file__).parent / "fixtures" / "jinn-portfolio", pf)

    src = tmp_path / "Human.mp4"  # same title as mv-0001 → slug must not collide
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=1080x1920:rate=25:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(src)],
                   check=True)
    bgm = tmp_path / "Archive 01.mp3"
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=220:duration=2", str(bgm)], check=True)
    window.ffmpeg, window.ffprobe = ffmpeg, ffprobe
    engine = window.manager.engine()
    engine.ffmpeg, engine.ffprobe = ffmpeg, ffprobe
    window.config.generate_thumbnails = True
    window.config.export_dir = str(tmp_path / "out")
    window.add_paths([src, bgm])
    assert window.manager.wait_analysis(30)
    window.manager.start()
    window.manager.wait(60)
    rows = list(reversed(window.history.recent(window.config.bucket)))
    assert {r["key"] for r in rows} == {"mv/Human.mp4", "audio/Archive 01.mp3"}

    cands = window._candidates_from_rows(rows)
    window.config.portfolio_dir = str(pf)
    dlg = ExportDialog(window, cands, window.config, window.history, ffmpeg, lambda k: "https://x/" + k)
    work = next(c for c in cands if c.kind == "work")
    track = next(c for c in cands if c.kind == "track")
    assert (work.id, work.slug, track.id) == ("mv-0005", "human-2", "archive-01")
    dlg._write()
    assert not shown, shown
    bundle = dlg.output_path
    merged = portfolio.PortfolioData.load(bundle)
    assert [w["id"] for w in merged.works][-1] == "mv-0005"
    assert merged.works[-1]["videoKey"] == "mv/Human.mp4"
    assert merged.tracks == [{"id": "archive-01", "key": "audio/Archive 01.mp3"}]
    assert (bundle / "public" / "thumbnails" / "human-2.webp").is_file()  # regenerated for the new slug
    assert json.loads((bundle / "data" / "thumbnail-sources.json").read_text(encoding="utf-8"))["human-2"] == 0.3
    assert window.history.issued_ids("work") == {"mv/Human.mp4": "mv-0005"}

    # A second export before the first one is committed must not hand out mv-0005 again.
    other = portfolio.Candidate(kind="work", key="mv/Other.mp4", title="Other", duration=5.0, width=1920, height=1080)
    dlg2 = ExportDialog(window, [other], window.config, window.history, ffmpeg, lambda k: "")
    assert other.id == "mv-0006"
    dlg2.close()
