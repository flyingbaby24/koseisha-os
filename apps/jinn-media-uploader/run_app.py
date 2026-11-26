"""PyInstaller entry point (also runnable directly: python run_app.py)."""

import sys

from jinn_uploader.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
