"""GUI entry point."""

from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from .. import APP_ID, APP_NAME
from ..config import ConfigStore, app_data_dir
from ..credentials import CredentialStore
from ..history import History, ResumeStore
from . import theme
from .icon import app_icon


def create_app(argv=None) -> QApplication:
    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Jinn Project")
    app.setApplicationDisplayName(APP_NAME)
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"JinnProject.{APP_ID}")
        except Exception:  # noqa: BLE001
            pass
    theme.apply(app)
    app.setWindowIcon(app_icon())
    return app


def build_window(cred_store: CredentialStore | None = None, auto_startup: bool = True):
    from .main_window import MainWindow

    home = app_data_dir()
    return MainWindow(
        ConfigStore(home / "config.json"),
        cred_store or CredentialStore(),
        History(home / "history.sqlite3"),
        ResumeStore(home / "resume"),
        icon=app_icon(),
        auto_startup=auto_startup,
    )


def run_gui() -> int:
    app = create_app()
    win = build_window()
    win.show()
    return app.exec()


def screenshot(path: str, demo: bool = True, delay_ms: int = 1500, tab: int = 0) -> int:
    """Render the main window to a PNG (CI smoke test / documentation)."""
    from ..credentials import MemoryKeyring

    app = create_app()
    win = build_window(CredentialStore(backend=MemoryKeyring()) if demo else None, auto_startup=False)
    if demo:
        from .demo import populate

        populate(win)
    win.tabs.setCurrentIndex(tab)
    win.show()

    def grab():
        win._tick()
        win.grab().save(path)
        win.manager.shutdown()
        app.quit()

    QTimer.singleShot(delay_ms, grab)
    app.exec()
    return 0
