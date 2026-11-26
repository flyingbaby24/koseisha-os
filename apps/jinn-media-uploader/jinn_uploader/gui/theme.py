"""Dark Fusion theme in the archive's palette (ink background, warm paper text)."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

INK = "#111114"
PANEL = "#18181d"
PANEL_2 = "#202027"
LINE = "#2e2e38"
TEXT = "#ece6da"
MUTED = "#9c978d"
ACCENT = "#d9a35b"
ACCENT_2 = "#e8bf86"
OK = "#7fbf8e"
WARN = "#e2b04a"
ERR = "#e07a6e"

STATE_COLORS = {
    "完了": OK,
    "失敗": ERR,
    "要確認": WARN,
    "一時停止": ACCENT_2,
    "スキップ": MUTED,
    "キャンセル": MUTED,
}

STYLESHEET = f"""
QWidget {{ color: {TEXT}; }}
QMainWindow, QDialog {{ background: {INK}; }}
QTabWidget::pane {{ border: 1px solid {LINE}; border-radius: 6px; top: -1px; background: {PANEL}; }}
QTabBar::tab {{ background: transparent; color: {MUTED}; padding: 8px 16px; border: none; }}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}
QGroupBox {{ border: 1px solid {LINE}; border-radius: 6px; margin-top: 14px; padding: 10px 8px 8px 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {ACCENT_2}; }}
QPushButton {{ background: {PANEL_2}; border: 1px solid {LINE}; border-radius: 5px; padding: 6px 12px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #5d5a55; border-color: #25252c; }}
QPushButton#primary {{ background: {ACCENT}; color: #1a1408; border: 1px solid {ACCENT}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {ACCENT_2}; }}
QPushButton#primary:disabled {{ background: #4a3d2c; color: #7d705f; border-color: #4a3d2c; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {PANEL_2}; border: 1px solid {LINE}; border-radius: 4px; padding: 4px 6px;
    selection-background-color: {ACCENT}; selection-color: #1a1408;
}}
QComboBox QAbstractItemView {{ background: {PANEL_2}; border: 1px solid {LINE}; selection-background-color: #3a3122; }}
QTableView {{ background: {PANEL}; alternate-background-color: #1c1c22; gridline-color: {LINE};
    border: 1px solid {LINE}; border-radius: 4px; selection-background-color: #3a3122; selection-color: {TEXT}; }}
QHeaderView::section {{ background: {PANEL_2}; color: {MUTED}; border: none; border-right: 1px solid {LINE};
    border-bottom: 1px solid {LINE}; padding: 5px 6px; }}
QProgressBar {{ background: {PANEL_2}; border: 1px solid {LINE}; border-radius: 4px; text-align: center; height: 16px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
QStatusBar {{ background: {PANEL}; color: {MUTED}; border-top: 1px solid {LINE}; }}
QToolTip {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {LINE}; }}
QFrame#dropZone {{ border: 2px dashed #4a4a57; border-radius: 10px; background: {PANEL}; }}
QFrame#dropZone[active="true"] {{ border-color: {ACCENT}; background: #241f17; }}
QLabel#dropTitle {{ font-size: 15px; color: {TEXT}; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#stat {{ font-size: 20px; color: {TEXT}; }}
QLabel#cost {{ font-size: 26px; color: {ACCENT_2}; }}
QCheckBox::indicator {{ width: 15px; height: 15px; }}
"""


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(INK))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base, QColor(PANEL))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#1c1c22"))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button, QColor(PANEL_2))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#1a1408"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(PANEL_2))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(MUTED))
    pal.setColor(QPalette.ColorRole.Link, QColor(ACCENT_2))
    app.setPalette(pal)
    families = set(QFontDatabase.families())
    for name in ("Yu Gothic UI", "Meiryo UI", "Noto Sans CJK JP", "Noto Sans JP", "WenQuanYi Zen Hei"):
        if name in families:
            font = QFont(name, 10 if name.startswith(("Yu", "Meiryo")) else 9)
            app.setFont(font)
            break
    app.setStyleSheet(STYLESHEET)
