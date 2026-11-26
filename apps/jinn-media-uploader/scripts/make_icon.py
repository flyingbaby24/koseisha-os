"""Regenerate assets/icon.png and assets/icon.ico from the QPainter drawing (needs Pillow)."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from jinn_uploader.gui.icon import draw_icon  # noqa: E402

app = QApplication([])
assets = ROOT / "assets"
assets.mkdir(exist_ok=True)
png = assets / "icon.png"
draw_icon(256).save(str(png))
Image.open(png).save(assets / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("wrote", png, assets / "icon.ico")
