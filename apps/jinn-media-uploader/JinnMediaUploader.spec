# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller --noconfirm JinnMediaUploader.spec   (on Windows)
import sys

from PyInstaller.utils.hooks import collect_submodules

hidden = ["keyring.backends.Windows"]
if sys.platform == "win32":
    hidden += collect_submodules("win32ctypes")

a = Analysis(
    ["run_app.py"],
    pathex=["."],
    binaries=[],
    datas=[("assets/icon.png", "assets")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc_data", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick",
              "PySide6.QtOpenGL", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDBus", "moto", "pytest"],
    noarchive=False,
)


def _keep(entry):
    """Only ship the S3 service model from botocore/boto3 (the full set is ~70 MB)."""
    dest = entry[0].replace("\\", "/")
    for root, keep in (("botocore/data/", {"s3"}), ("boto3/data/", {"s3"})):
        if dest.startswith(root):
            rest = dest[len(root):]
            return "/" not in rest or rest.split("/", 1)[0] in keep
    return True


a.datas = [d for d in a.datas if _keep(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="JinnMediaUploader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/icon.ico",
    version="version_info.txt",
)
