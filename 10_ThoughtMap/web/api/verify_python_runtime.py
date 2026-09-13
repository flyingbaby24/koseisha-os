"""Fail CI and Render startup if the validated Python runtime drifts."""
from __future__ import annotations

import sys
from pathlib import Path


def verify_runtime(version=None):
    web = Path(__file__).resolve().parents[1]
    pin = (web / ".python-version").read_text(encoding="utf-8").strip()
    repository_file = web.parents[1] / ".python-version"
    repository_pin = repository_file.read_text(encoding="utf-8").strip() if repository_file.exists() else pin
    expected = tuple(int(part) for part in pin.split("."))
    actual = tuple(sys.version_info[:3] if version is None else version)
    if len(expected) != 3 or expected[:2] != (3, 13) or repository_pin != pin:
        raise RuntimeError("Render and CI must share the validated Python 3.13 patch pin")
    if actual != expected:
        raise RuntimeError(f"Python runtime drift: expected {pin}, got {actual}")
    return pin


if __name__ == "__main__":
    print(f"Validated Python {verify_runtime()}")
