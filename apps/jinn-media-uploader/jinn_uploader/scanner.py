"""Expanding dropped files/folders and hashing file contents."""

from __future__ import annotations

import hashlib
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .keys import IGNORED_NAMES

HASH_CHUNK = 8 * 1024 * 1024


@dataclass(frozen=True)
class ScannedFile:
    path: Path
    # Folder names between the dropped folder (inclusive) and the file, e.g. ("Album", "Disc1").
    subdirs: tuple[str, ...]
    size: int


def _is_hidden(path: Path) -> bool:
    if path.name.startswith(".") or path.name.lower() in IGNORED_NAMES:
        return True
    if os.name == "nt":
        try:
            attrs = path.stat().st_file_attributes  # type: ignore[attr-defined]
            return bool(attrs & 0x2 or attrs & 0x4)  # HIDDEN | SYSTEM
        except (OSError, AttributeError):
            return False
    return False


def scan_paths(paths: Iterable[str | Path]) -> list[ScannedFile]:
    """Expand files and folders (recursively) into a de-duplicated, ordered file list."""
    out: list[ScannedFile] = []
    seen: set[str] = set()

    def add(p: Path, subdirs: tuple[str, ...]):
        try:
            real = os.path.normcase(str(p.resolve()))
        except OSError:
            return
        if real in seen:
            return
        try:
            st = p.stat()
        except OSError:
            return
        seen.add(real)
        out.append(ScannedFile(p, subdirs, st.st_size))

    for raw in paths:
        p = Path(raw)
        if p.is_file():
            if not _is_hidden(p):
                add(p, ())
        elif p.is_dir():
            root_name = p.name
            visited: set[str] = set()
            for dirpath, dirnames, filenames in os.walk(p, followlinks=False):
                dp = Path(dirpath)
                try:
                    real_dir = str(dp.resolve())
                except OSError:
                    continue
                if real_dir in visited:
                    dirnames[:] = []
                    continue
                visited.add(real_dir)
                dirnames[:] = sorted(d for d in dirnames if not _is_hidden(dp / d))
                rel = dp.relative_to(p).parts
                for name in sorted(filenames):
                    fp = dp / name
                    if _is_hidden(fp) or not fp.is_file():
                        continue
                    add(fp, (root_name, *rel))
    return out


class Cancelled(Exception):
    pass


def hash_file(
    path: str | Path,
    progress: Callable[[int], None] | None = None,
    cancel: threading.Event | None = None,
) -> tuple[str, str]:
    """Return (md5_hex, sha256_hex) computed in one pass."""
    md5 = hashlib.md5()
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            if cancel is not None and cancel.is_set():
                raise Cancelled()
            chunk = fh.read(HASH_CHUNK)
            if not chunk:
                break
            md5.update(chunk)
            sha.update(chunk)
            if progress:
                progress(len(chunk))
    return md5.hexdigest(), sha.hexdigest()
