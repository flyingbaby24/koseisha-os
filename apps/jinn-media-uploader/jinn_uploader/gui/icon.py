"""App icon drawn with QPainter (also used by scripts/make_icon.py to produce icon.ico)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap


def draw_icon(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256.0
    bg = QLinearGradient(0, 0, 0, size)
    bg.setColorAt(0, QColor("#24222b"))
    bg.setColorAt(1, QColor("#0f0f12"))
    rect = QRectF(8 * s, 8 * s, 240 * s, 240 * s)
    p.setPen(QPen(QColor("#3a3530"), max(1.0, 4 * s)))
    p.setBrush(bg)
    p.drawRoundedRect(rect, 52 * s, 52 * s)

    # Cloud-ish arc (storage) in warm accent.
    accent = QColor("#d9a35b")
    pen = QPen(accent, 14 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(72 * s, 170 * s)
    path.cubicTo(40 * s, 170 * s, 40 * s, 118 * s, 78 * s, 116 * s)
    path.cubicTo(84 * s, 74 * s, 150 * s, 66 * s, 168 * s, 106 * s)
    path.cubicTo(214 * s, 100 * s, 222 * s, 170 * s, 182 * s, 170 * s)
    p.drawPath(path)

    # Upload arrow.
    p.setPen(QPen(QColor("#ece6da"), 16 * s, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawLine(QPointF(128 * s, 206 * s), QPointF(128 * s, 120 * s))
    arrow = QPainterPath()
    arrow.moveTo(96 * s, 150 * s)
    arrow.lineTo(128 * s, 118 * s)
    arrow.lineTo(160 * s, 150 * s)
    p.drawPath(arrow)
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(draw_icon(size))
    return icon
