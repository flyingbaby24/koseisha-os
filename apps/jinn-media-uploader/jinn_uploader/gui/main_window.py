"""Main window: drag & drop queue, R2 file list, usage/cost, history and log."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME, __version__, media, portfolio, pricing
from ..config import AppConfig, ConfigStore
from ..credentials import CredentialError, CredentialStore
from ..history import History, ResumeStore
from ..jobs import JobManager, NotConnected
from ..keys import CATEGORY_LABELS, format_bytes, format_duration, format_eta, format_rate, normalize_prefix, public_url
from ..r2client import R2Service, make_client
from ..uploader import JobState, UploadEngine
from .dialogs import COMPRESSION_LABELS, DecisionDialog, ExportDialog, SettingsDialog
from .models import CategoryDelegate, ObjectsFilter, ObjectsModel, ProgressDelegate, QueueModel
from .worker import run_async

log = logging.getLogger("jinn_uploader")


class _LogBridge(QObject):
    line = Signal(str)


class QtLogHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.bridge = _LogBridge()
        self.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s", "%H:%M:%S"))

    def emit(self, record):
        try:
            self.bridge.line.emit(self.format(record))
        except RuntimeError:
            pass


class _FinishBridge(QObject):
    finished = Signal()


class DropZone(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")
        self.setProperty("active", False)

    def set_active(self, on: bool):
        self.setProperty("active", on)
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self, config_store: ConfigStore, cred_store: CredentialStore, history: History,
                 resume: ResumeStore, icon: QIcon | None = None, auto_startup: bool = True):
        super().__init__()
        self.config_store = config_store
        self.config: AppConfig = config_store.load()
        self.cred_store = cred_store
        self.history = history
        self.resume = resume
        self.ffmpeg, self.ffprobe = media.find_ffmpeg(self.config.ffmpeg_path)
        self.manager = JobManager(self.config, self._make_engine)
        self._finish = _FinishBridge()
        self._finish.finished.connect(self._on_uploads_finished)
        self.manager.on_finished = self._finish.finished.emit
        self._objects: list = []
        self._usage = None
        self.connection_ok: bool | None = None

        self.setWindowTitle(f"{APP_NAME} {__version__}")
        if icon is not None:
            self.setWindowIcon(icon)
        self.resize(1320, 820)
        self.setAcceptDrops(True)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_upload_tab(), "アップロード")
        self.tabs.addTab(self._build_objects_tab(), "R2 ファイル一覧")
        self.tabs.addTab(self._build_usage_tab(), "使用量・料金")
        self.tabs.addTab(self._build_history_tab(), "履歴")
        self.tabs.addTab(self._build_log_tab(), "ログ")
        self.tabs.currentChanged.connect(self._on_tab)
        self.setCentralWidget(self.tabs)
        self._build_toolbar()

        self.status_conn = QLabel()
        self.status_store = QLabel()
        self.status_ff = QLabel()
        for w in (self.status_conn, self.status_store, self.status_ff):
            self.statusBar().addPermanentWidget(w)
        self._update_status()

        self.log_handler = QtLogHandler()
        self.log_handler.bridge.line.connect(self.log_view.appendPlainText)
        logging.getLogger("jinn_uploader").addHandler(self.log_handler)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(300)
        if auto_startup:
            QTimer.singleShot(200, self._startup)

    # ------------------------------------------------------------------ engine
    def _make_engine(self) -> UploadEngine:
        try:
            creds = self.cred_store.load()
        except CredentialError as exc:
            raise NotConnected(str(exc)) from exc
        if creds is None:
            raise NotConnected("R2 の認証情報が未設定です。［設定］から登録してください。")
        client = make_client(creds, self.config.endpoint_override, max_pool=self.config.concurrency + 6)
        service = R2Service(client, self.config.bucket, self.config.public_base_url)
        return UploadEngine(service, self.config, self.history, self.resume, ffmpeg=self.ffmpeg, ffprobe=self.ffprobe)

    def _service(self) -> R2Service:
        return self.manager.engine().service

    # ------------------------------------------------------------------ UI: toolbar
    def _build_toolbar(self):
        tb = self.addToolBar("main")
        tb.setMovable(False)
        tb.setIconSize(QSize(16, 16))
        a_settings = QAction("設定", self)
        a_settings.setShortcut(QKeySequence("Ctrl+,"))
        a_settings.triggered.connect(self.open_settings)
        a_test = QAction("接続テスト", self)
        a_test.triggered.connect(lambda: self.check_connection(verbose=True))
        a_files = QAction("ファイルを追加", self)
        a_files.setShortcut(QKeySequence("Ctrl+O"))
        a_files.triggered.connect(self.add_files_dialog)
        a_folder = QAction("フォルダを追加", self)
        a_folder.triggered.connect(self.add_folder_dialog)
        a_json = QAction("ポートフォリオ登録データ出力", self)
        a_json.triggered.connect(self.export_session_json)
        for a in (a_files, a_folder, None, a_settings, a_test, None, a_json):
            if a is None:
                tb.addSeparator()
            else:
                tb.addAction(a)

    # ------------------------------------------------------------------ UI: upload tab
    def _build_upload_tab(self) -> QWidget:
        w = QWidget()
        self.drop_zone = DropZone()
        dz = QHBoxLayout(self.drop_zone)
        dz.setContentsMargins(18, 14, 18, 14)
        title = QLabel("ここに MV・BGM のファイルやフォルダをドラッグ＆ドロップ")
        title.setObjectName("dropTitle")
        sub = QLabel("動画 → MV、音声 → BGM に自動で振り分けます。300MB を超える動画もマルチパートで分割送信します。")
        sub.setObjectName("muted")
        texts = QVBoxLayout()
        texts.addWidget(title)
        texts.addWidget(sub)
        dz.addLayout(texts, 1)
        b_files = QPushButton("ファイルを追加…")
        b_files.clicked.connect(self.add_files_dialog)
        b_folder = QPushButton("フォルダを追加…")
        b_folder.clicked.connect(self.add_folder_dialog)
        dz.addWidget(b_files)
        dz.addWidget(b_folder)

        dest = QGroupBox("保存先")
        dl = QHBoxLayout(dest)
        self.mv_dest = self._prefix_combo(self.config.mv_prefix)
        self.bgm_dest = self._prefix_combo(self.config.bgm_prefix)
        self.other_dest = self._prefix_combo(self.config.other_prefix)
        self.keep_tree = QCheckBox("フォルダ構造を保持")
        self.keep_tree.setChecked(self.config.keep_folder_structure)
        self.keep_tree.toggled.connect(self._on_dest_changed)
        for label, combo in (("MV", self.mv_dest), ("BGM", self.bgm_dest), ("その他", self.other_dest)):
            dl.addWidget(QLabel(label))
            dl.addWidget(combo, 1)
        dl.addWidget(self.keep_tree)

        opts = QGroupBox("処理")
        ol = QHBoxLayout(opts)
        self.compress_combo = QComboBox()
        for key, label in COMPRESSION_LABELS:
            self.compress_combo.addItem(label, key)
        self.compress_combo.setCurrentIndex(max(0, self.compress_combo.findData(self.config.compression)))
        self.compress_combo.currentIndexChanged.connect(self._on_options_changed)
        self.thumb_check = QCheckBox("サムネイル生成（FFmpeg）")
        self.thumb_check.setChecked(self.config.generate_thumbnails)
        self.thumb_check.toggled.connect(self._on_options_changed)
        self.thumb_up_check = QCheckBox("サムネイルも R2 へ")
        self.thumb_up_check.setChecked(self.config.upload_thumbnails)
        self.thumb_up_check.toggled.connect(self._on_options_changed)
        ol.addWidget(QLabel("動画"))
        ol.addWidget(self.compress_combo)
        ol.addSpacing(12)
        ol.addWidget(self.thumb_check)
        ol.addWidget(self.thumb_up_check)
        ol.addStretch(1)

        self.queue_model = QueueModel(self.manager)
        self.queue_model.editError.connect(lambda m: QMessageBox.warning(self, "保存先キー", m))
        self.queue_view = QTableView()
        self.queue_view.setModel(self.queue_model)
        self.queue_view.setItemDelegateForColumn(5, ProgressDelegate(self.queue_view))
        self.queue_view.setItemDelegateForColumn(1, CategoryDelegate(self.queue_view))
        self.queue_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue_view.setAlternatingRowColors(True)
        self.queue_view.verticalHeader().setVisible(False)
        self.queue_view.verticalHeader().setDefaultSectionSize(30)
        self.queue_view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.queue_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_view.customContextMenuRequested.connect(self._queue_menu)
        hh = self.queue_view.horizontalHeader()
        for col, width in enumerate([210, 70, 260, 85, 170, 150, 90, 80, 260, 260]):
            self.queue_view.setColumnWidth(col, width)
        hh.setStretchLastSection(True)

        self.total_bar = QProgressBar()
        self.total_bar.setRange(0, 1000)
        self.total_bar.setFormat("%p%")
        self.total_label = QLabel("キューは空です")
        self.total_label.setObjectName("muted")
        totals = QHBoxLayout()
        totals.addWidget(QLabel("全体"))
        totals.addWidget(self.total_bar, 1)
        totals.addWidget(self.total_label)

        self.btn_start = QPushButton("アップロード開始")
        self.btn_start.setObjectName("primary")
        self.btn_start.clicked.connect(self.start_uploads)
        self.btn_pause = QPushButton("一時停止")
        self.btn_pause.clicked.connect(self.pause_uploads)
        self.btn_cancel = QPushButton("選択をキャンセル")
        self.btn_cancel.clicked.connect(self.cancel_selected)
        self.btn_retry = QPushButton("失敗・中断を再試行")
        self.btn_retry.clicked.connect(self.retry_failed)
        self.btn_remove = QPushButton("選択を一覧から外す")
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear = QPushButton("完了を消去")
        self.btn_clear.clicked.connect(lambda: self.manager.clear_finished())
        self.btn_copy = QPushButton("公開URLをコピー")
        self.btn_copy.clicked.connect(self.copy_selected_urls)
        self.btn_json = QPushButton("ポートフォリオ登録")
        self.btn_json.clicked.connect(self.export_session_json)
        buttons = QHBoxLayout()
        for b in (self.btn_start, self.btn_pause, self.btn_cancel, self.btn_retry):
            buttons.addWidget(b)
        buttons.addStretch(1)
        for b in (self.btn_remove, self.btn_clear, self.btn_copy, self.btn_json):
            buttons.addWidget(b)

        lay = QVBoxLayout(w)
        lay.addWidget(self.drop_zone)
        top = QHBoxLayout()
        top.addWidget(dest, 3)
        top.addWidget(opts, 2)
        lay.addLayout(top)
        lay.addWidget(self.queue_view, 1)
        lay.addLayout(totals)
        lay.addLayout(buttons)
        return w

    def _prefix_combo(self, value: str) -> QComboBox:
        cb = QComboBox()
        cb.setEditable(True)
        items = [value] + [p for p in self.config.recent_prefixes if p != value]
        for v in ("mv/", "audio/", "misc/", ""):
            if v not in items:
                items.append(v)
        for v in items:
            cb.addItem(v if v else "（バケット直下）", v)
        cb.setCurrentIndex(0)
        cb.setToolTip("R2 上の保存先フォルダ（例: mv/2026/）。空欄はバケット直下。")
        cb.lineEdit().editingFinished.connect(self._on_dest_changed)
        cb.activated.connect(lambda _i: self._on_dest_changed())
        return cb

    @staticmethod
    def _combo_prefix(cb: QComboBox) -> str:
        text = cb.currentText().strip()
        if text == "（バケット直下）":
            return ""
        return normalize_prefix(text)

    def _on_dest_changed(self):
        try:
            mv, bgm, other = (self._combo_prefix(c) for c in (self.mv_dest, self.bgm_dest, self.other_dest))
        except ValueError as exc:
            QMessageBox.warning(self, "保存先", str(exc))
            return
        c = self.config
        changed = (c.mv_prefix, c.bgm_prefix, c.other_prefix, c.keep_folder_structure) != (
            mv, bgm, other, self.keep_tree.isChecked())
        c.mv_prefix, c.bgm_prefix, c.other_prefix = mv, bgm, other
        c.keep_folder_structure = self.keep_tree.isChecked()
        for p in (mv, bgm, other):
            c.remember_prefix(p)
        if changed:
            self.config_store.save(c)
            self.manager.apply_prefixes()
            log.info("保存先: MV=%s BGM=%s その他=%s", mv or "（直下）", bgm or "（直下）", other or "（直下）")

    def _on_options_changed(self):
        self.config.compression = self.compress_combo.currentData()
        self.config.generate_thumbnails = self.thumb_check.isChecked()
        self.config.upload_thumbnails = self.thumb_up_check.isChecked()
        self.thumb_up_check.setEnabled(self.thumb_check.isChecked())
        self.config_store.save(self.config)

    # ------------------------------------------------------------------ UI: objects tab
    def _build_objects_tab(self) -> QWidget:
        w = QWidget()
        self.obj_model = ObjectsModel(lambda k: public_url(self.config.public_base_url, k))
        self.obj_filter = ObjectsFilter()
        self.obj_filter.setSourceModel(self.obj_model)
        self.obj_view = QTableView()
        self.obj_view.setModel(self.obj_filter)
        self.obj_view.setSortingEnabled(True)
        self.obj_view.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        self.obj_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.obj_view.setAlternatingRowColors(True)
        self.obj_view.verticalHeader().setVisible(False)
        self.obj_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.obj_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.obj_view.customContextMenuRequested.connect(self._objects_menu)
        self.obj_view.doubleClicked.connect(lambda _i: self.copy_object_urls())
        for col, width in enumerate([420, 100, 140, 70]):
            self.obj_view.setColumnWidth(col, width)
        self.obj_view.horizontalHeader().setStretchLastSection(True)

        self.obj_prefix = QComboBox()
        self.obj_prefix.addItem("すべて", "")
        self.obj_prefix.currentIndexChanged.connect(self._apply_obj_filter)
        self.obj_search = QLineEdit()
        self.obj_search.setPlaceholderText("キーで検索")
        self.obj_search.textChanged.connect(self._apply_obj_filter)
        refresh = QPushButton("一覧を更新")
        refresh.clicked.connect(self.refresh_objects)
        self.obj_summary = QLabel("")
        self.obj_summary.setObjectName("muted")
        top = QHBoxLayout()
        top.addWidget(QLabel("フォルダ"))
        top.addWidget(self.obj_prefix)
        top.addWidget(self.obj_search, 1)
        top.addWidget(refresh)

        copy = QPushButton("公開URLをコピー")
        copy.clicked.connect(self.copy_object_urls)
        open_b = QPushButton("ブラウザで開く")
        open_b.clicked.connect(self.open_object_urls)
        export = QPushButton("選択をポートフォリオ登録")
        export.clicked.connect(self.export_objects_json)
        note = QLabel("このアプリは R2 上の既存ファイルを削除・変更しません（一覧は読み取り専用）。")
        note.setObjectName("muted")
        bottom = QHBoxLayout()
        bottom.addWidget(copy)
        bottom.addWidget(open_b)
        bottom.addWidget(export)
        bottom.addStretch(1)
        bottom.addWidget(note)

        lay = QVBoxLayout(w)
        lay.addLayout(top)
        lay.addWidget(self.obj_view, 1)
        lay.addWidget(self.obj_summary)
        lay.addLayout(bottom)
        return w

    def _apply_obj_filter(self):
        self.obj_filter.set_filter(self.obj_prefix.currentData() or "", self.obj_search.text())
        self.obj_summary.setText(f"表示 {self.obj_filter.rowCount()} 件 / 全 {self.obj_model.rowCount()} 件")

    # ------------------------------------------------------------------ UI: usage tab
    def _build_usage_tab(self) -> QWidget:
        w = QWidget()
        usage = QGroupBox("R2 使用容量")
        g = QGridLayout(usage)
        self.u_count = QLabel("—")
        self.u_size = QLabel("—")
        self.u_when = QLabel("—")
        for lbl in (self.u_count, self.u_size):
            lbl.setObjectName("stat")
        g.addWidget(QLabel("オブジェクト数"), 0, 0)
        g.addWidget(self.u_count, 1, 0)
        g.addWidget(QLabel("合計サイズ"), 0, 1)
        g.addWidget(self.u_size, 1, 1)
        g.addWidget(QLabel("取得日時"), 0, 2)
        g.addWidget(self.u_when, 1, 2)
        self.u_table = QTableWidget(0, 3)
        self.u_table.setHorizontalHeaderLabels(["フォルダ", "ファイル数", "サイズ"])
        self.u_table.verticalHeader().setVisible(False)
        self.u_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.u_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        g.addWidget(self.u_table, 2, 0, 1, 3)

        cost = QGroupBox("推定月額料金（R2 Standard）")
        cl = QVBoxLayout(cost)
        self.c_total = QLabel("—")
        self.c_total.setObjectName("cost")
        self.c_detail = QLabel("")
        self.c_detail.setWordWrap(True)
        cl.addWidget(self.c_total)
        cl.addWidget(self.c_detail)
        note = QLabel("Cloudflare R2 の公開価格に基づく概算です（エグレス無料、無料枠を差し引き）。"
                      "Class A 操作数はこのアプリで今月行ったアップロード分のみを計上します。実際の請求は Cloudflare ダッシュボードで確認してください。")
        note.setObjectName("muted")
        note.setWordWrap(True)
        cl.addWidget(note)
        cl.addStretch(1)

        prices = QGroupBox("料金設定（USD）")
        pf = QFormLayout(prices)
        p = self.config.pricing
        self.p_storage = self._money(p.storage_per_gb_month, 4)
        self.p_a = self._money(p.class_a_per_million, 2)
        self.p_b = self._money(p.class_b_per_million, 2)
        self.p_free = self._money(p.free_storage_gb, 1)
        self.p_rate = self._money(p.usd_jpy, 2, 1000)
        pf.addRow("ストレージ / GB・月", self.p_storage)
        pf.addRow("Class A / 100万回", self.p_a)
        pf.addRow("Class B / 100万回", self.p_b)
        pf.addRow("無料ストレージ (GB)", self.p_free)
        pf.addRow("為替 (円/USD)", self.p_rate)
        for sb in (self.p_storage, self.p_a, self.p_b, self.p_free, self.p_rate):
            sb.valueChanged.connect(self._on_pricing_changed)

        refresh = QPushButton("使用量を更新")
        refresh.clicked.connect(self.refresh_objects)
        lay = QGridLayout(w)
        lay.addWidget(usage, 0, 0, 2, 1)
        lay.addWidget(cost, 0, 1)
        lay.addWidget(prices, 1, 1)
        lay.addWidget(refresh, 2, 0, 1, 2, Qt.AlignmentFlag.AlignLeft)
        lay.setColumnStretch(0, 3)
        lay.setColumnStretch(1, 2)
        return w

    @staticmethod
    def _money(value: float, decimals: int, maximum: float = 100.0) -> QDoubleSpinBox:
        sb = QDoubleSpinBox()
        sb.setDecimals(decimals)
        sb.setRange(0, maximum)
        sb.setValue(value)
        return sb

    def _on_pricing_changed(self):
        p = self.config.pricing
        p.storage_per_gb_month = self.p_storage.value()
        p.class_a_per_million = self.p_a.value()
        p.class_b_per_million = self.p_b.value()
        p.free_storage_gb = self.p_free.value()
        p.usd_jpy = self.p_rate.value()
        self.config_store.save(self.config)
        self._render_usage()

    # ------------------------------------------------------------------ UI: history / log
    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        self.h_table = QTableWidget(0, 7)
        self.h_table.setHorizontalHeaderLabels(["日時", "キー", "種別", "サイズ", "長さ", "解像度", "公開URL"])
        self.h_table.verticalHeader().setVisible(False)
        self.h_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.h_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.h_table.setAlternatingRowColors(True)
        self.h_table.horizontalHeader().setStretchLastSection(True)
        copy = QPushButton("公開URLをコピー")
        copy.clicked.connect(self.copy_history_urls)
        export = QPushButton("選択をポートフォリオ登録")
        export.setObjectName("primary")
        export.clicked.connect(self.export_history_json)
        reload_b = QPushButton("再読み込み")
        reload_b.clicked.connect(self.refresh_history)
        row = QHBoxLayout()
        row.addWidget(copy)
        row.addWidget(export)
        row.addStretch(1)
        row.addWidget(reload_b)
        lay = QVBoxLayout(w)
        lay.addWidget(self.h_table, 1)
        lay.addLayout(row)
        self._history_rows: list[dict] = []
        return w

    def _build_log_tab(self) -> QWidget:
        w = QWidget()
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(5000)
        lay = QVBoxLayout(w)
        lay.addWidget(self.log_view)
        return w

    # ------------------------------------------------------------------ startup / status
    def _startup(self):
        try:
            creds = self.cred_store.load()
        except CredentialError as exc:
            creds = None
            log.error("%s", exc)
        self.refresh_history()
        if creds is None:
            self._update_status()
            QMessageBox.information(
                self, "はじめに",
                "R2 の認証情報（Account ID / Access Key ID / Secret Access Key）を登録してください。\n"
                f"認証情報は {self.cred_store.backend_label} に保存されます。",
            )
            self.open_settings()
        else:
            self.check_connection()
        self._restore_interrupted()

    def _restore_interrupted(self):
        states = [s for s in self.resume.all() if s.bucket == self.config.bucket and Path(s.source_path).is_file()]
        if not states:
            return
        for s in states:
            added, _ = self.manager.add_paths([s.source_path])
            for job in added:
                if job.key != s.key:
                    self.manager.set_key(job, s.key)
                job.message = "前回の続きから再開できます"
        log.info("前回中断したアップロードが %d 件あります。［アップロード開始］で続きから再開します。", len(states))

    def _update_status(self):
        if self.connection_ok is None:
            conn = "R2: 未確認"
        elif self.connection_ok:
            conn = f"R2: 接続OK（{self.config.account_label} / {self.config.bucket}）"
        else:
            conn = "R2: 未接続"
        self.status_conn.setText(conn)
        self.status_store.setText(f"認証情報: {self.cred_store.backend_label}")
        self.status_ff.setText(f"FFmpeg: {'検出済み' if self.ffmpeg else '未検出（サムネイル無効）'}")
        self.thumb_check.setEnabled(bool(self.ffmpeg))
        self.compress_combo.setEnabled(bool(self.ffmpeg))
        if not self.ffmpeg:
            self.thumb_check.setToolTip("FFmpeg が見つかりません。設定で ffmpeg.exe を指定してください。")

    def check_connection(self, verbose: bool = False):
        try:
            svc = self._service()
        except Exception as exc:  # noqa: BLE001
            self.connection_ok = False
            self._update_status()
            if verbose:
                QMessageBox.warning(self, "接続テスト", str(exc))
            return
        self.status_conn.setText("R2: 接続確認中…")

        def ok(_result):
            self.connection_ok = True
            self._update_status()
            log.info("R2 に接続しました（バケット %s）", self.config.bucket)
            if verbose:
                QMessageBox.information(self, "接続テスト", f"バケット「{self.config.bucket}」に接続できました。")
            self.refresh_objects()

        def fail(msg):
            self.connection_ok = False
            self._update_status()
            log.error("R2 に接続できません: %s", msg)
            if verbose:
                QMessageBox.warning(self, "接続テスト", msg)

        run_async(svc.test_connection, on_done=ok, on_error=fail)

    def open_settings(self):
        dlg = SettingsDialog(self, self.config, self.cred_store)
        if dlg.exec():
            self.config_store.save(self.config)
            self.ffmpeg, self.ffprobe = media.find_ffmpeg(self.config.ffmpeg_path)
            self.manager.reset_engine()
            self._sync_option_widgets()
            self.manager.apply_prefixes()
            if dlg.credentials_changed:
                self.connection_ok = None
                self.manager.reanalyze_all()
            self.check_connection()
        elif dlg.credentials_changed:
            self.manager.reset_engine()
            self.connection_ok = None
        self._update_status()

    def _sync_option_widgets(self):
        for cb, value in ((self.mv_dest, self.config.mv_prefix), (self.bgm_dest, self.config.bgm_prefix),
                          (self.other_dest, self.config.other_prefix)):
            cb.setEditText(value)
        self.compress_combo.setCurrentIndex(max(0, self.compress_combo.findData(self.config.compression)))
        self.thumb_check.setChecked(self.config.generate_thumbnails)
        self.thumb_up_check.setChecked(self.config.upload_thumbnails)

    # ------------------------------------------------------------------ drag & drop
    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()
            self.drop_zone.set_active(True)
            self.tabs.setCurrentIndex(0)
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):  # noqa: N802
        self.drop_zone.set_active(False)

    def dropEvent(self, event):  # noqa: N802
        self.drop_zone.set_active(False)
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.add_paths(paths)

    def add_paths(self, paths):
        added, skipped = self.manager.add_paths(paths)
        if added:
            by_cat: dict[str, int] = {}
            for j in added:
                by_cat[j.category] = by_cat.get(j.category, 0) + 1
            parts = ", ".join(f"{CATEGORY_LABELS.get(k, k)} {v}件" for k, v in by_cat.items())
            log.info("%d 件を追加しました（%s）", len(added), parts)
        if skipped:
            log.info("%d 件はすでに一覧にあるため追加しませんでした", skipped)
        self.queue_model.refresh()
        return added

    def add_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "アップロードするファイル", "",
            "メディア (*.mp4 *.mov *.m4v *.webm *.mkv *.avi *.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.aiff);;すべて (*)",
        )
        if files:
            self.add_paths(files)

    def add_folder_dialog(self):
        folder = QFileDialog.getExistingDirectory(self, "アップロードするフォルダ")
        if folder:
            self.add_paths([folder])

    # ------------------------------------------------------------------ queue actions
    def _selected_jobs(self):
        rows = sorted({i.row() for i in self.queue_view.selectionModel().selectedRows()})
        return [self.queue_model.job(r) for r in rows]

    def start_uploads(self):
        if self.manager.running:
            return
        try:
            self.manager.engine()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "R2 未接続", str(exc))
            return
        if self.manager.analysis_pending():
            progress = QProgressDialog("ファイルを解析しています（ハッシュ計算・重複確認）…", "中止", 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(300)
            while self.manager.analysis_pending():
                QGuiApplication.processEvents()
                if progress.wasCanceled():
                    return
                self.manager.wait_analysis(0.1)
            progress.close()
        undecided = self.manager.undecided()
        if undecided:
            dlg = DecisionDialog(self, undecided)
            if not dlg.exec():
                return
            for job in undecided:
                self.manager.apply_decision(job, dlg.decisions[job.id])
        if not any(j.state in (JobState.READY, JobState.PAUSED) for j in self.manager.jobs):
            log.info("アップロード待ちのファイルはありません")
            return
        try:
            self.manager.start()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "開始できません", str(exc))
            return
        log.info("アップロードを開始しました")

    def pause_uploads(self):
        if self.manager.running:
            self.manager.pause()
            log.info("一時停止します（送信中のパートが終わり次第止まります）")

    def cancel_selected(self):
        jobs = self._selected_jobs()
        if not jobs:
            return
        if QMessageBox.question(self, "キャンセル", f"選択した {len(jobs)} 件のアップロードをキャンセルしますか？\n"
                                "（送信途中のマルチパートは破棄されます。R2 上の既存ファイルには影響しません）") != QMessageBox.StandardButton.Yes:
            return
        self.manager.cancel(jobs)

    def retry_failed(self):
        n = self.manager.retry_failed()
        if n:
            log.info("%d 件を再試行します", n)
            self.start_uploads()

    def remove_selected(self):
        n = self.manager.remove(self._selected_jobs())
        if n:
            self.queue_model.refresh()

    def copy_selected_urls(self):
        jobs = [j for j in (self._selected_jobs() or self.manager.jobs) if j.public_url]
        self._copy_urls([j.public_url for j in jobs])

    def _copy_urls(self, urls):
        if not urls:
            self.statusBar().showMessage("コピーできる公開URLがありません", 3000)
            return
        QGuiApplication.clipboard().setText("\n".join(urls))
        self.statusBar().showMessage(f"公開URLを {len(urls)} 件コピーしました", 3000)

    def _queue_menu(self, pos):
        jobs = self._selected_jobs()
        if not jobs:
            return
        menu = QMenu(self)
        menu.addAction("公開URLをコピー", self.copy_selected_urls)
        menu.addAction("ブラウザで開く", lambda: [QDesktopServices.openUrl(QUrl(j.public_url)) for j in jobs if j.public_url])
        menu.addAction("フォルダを開く", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(jobs[0].path.parent))))
        menu.addSeparator()
        sub = menu.addMenu("種別を変更")
        for key, label in (("mv", "MV"), ("bgm", "BGM"), ("other", "その他")):
            sub.addAction(label, lambda k=key: [self.manager.set_category(j, k) for j in jobs])
        menu.addAction("重複・存在を再確認", lambda: [self.manager.recheck(j) for j in jobs])
        menu.addSeparator()
        menu.addAction("一覧から外す", self.remove_selected)
        menu.exec(self.queue_view.viewport().mapToGlobal(pos))

    def _on_uploads_finished(self):
        t = self.manager.totals()
        log.info("アップロード処理が終了しました（完了 %d / 失敗 %d）", t["completed"], t["failed"])
        if self.manager.undecided():
            log.warning("確認が必要なファイルがあります（状態「要確認」）。［アップロード開始］で対応を選べます。")
        self.refresh_history()
        self.refresh_objects()

    def _tick(self):
        self.queue_model.refresh()
        t = self.manager.totals()
        running = self.manager.running
        if t["count"]:
            self.total_bar.setValue(int(1000 * t["done"] / t["total"]) if t["total"] else 0)
            text = f"{t['completed']}/{t['count']} 件完了  {format_bytes(t['done'])} / {format_bytes(t['total'])}"
            if running:
                text += f"  速度 {format_rate(t['rate'])}  残り {format_eta(t['eta'])}"
            if t["failed"]:
                text += f"  失敗 {t['failed']}"
            self.total_label.setText(text)
        else:
            self.total_bar.setValue(0)
            self.total_label.setText("キューは空です — ファイルやフォルダをドロップしてください")
        self.btn_start.setEnabled(not running)
        self.btn_pause.setEnabled(running)

    def _on_tab(self, index):
        if index == 3:
            self.refresh_history()

    # ------------------------------------------------------------------ objects / usage
    def refresh_objects(self):
        try:
            svc = self._service()
        except Exception:  # noqa: BLE001
            return
        self.obj_summary.setText("読み込み中…")

        def done(objects):
            self._objects = objects
            self.manager.set_remote_objects(objects)
            self.obj_model.set_objects(objects)
            current = self.obj_prefix.currentData()
            self.obj_prefix.blockSignals(True)
            self.obj_prefix.clear()
            self.obj_prefix.addItem("すべて", "")
            for top in sorted({o.key.split("/", 1)[0] + "/" for o in objects if "/" in o.key}):
                self.obj_prefix.addItem(top, top)
            self.obj_prefix.setCurrentIndex(max(0, self.obj_prefix.findData(current)))
            self.obj_prefix.blockSignals(False)
            self._apply_obj_filter()
            self._usage = R2Service.summarize(objects)
            self._render_usage()

        run_async(svc.list_all, on_done=done, on_error=lambda m: self.obj_summary.setText("取得できません: " + m))

    def _render_usage(self):
        u = self._usage
        if u is None:
            return
        self.u_count.setText(f"{u.object_count:,}")
        self.u_size.setText(f"{u.total_bytes / 1e9:,.2f} GB")
        self.u_size.setToolTip(f"{u.total_bytes:,} バイト（{format_bytes(u.total_bytes).replace('B', 'iB')}）")
        self.u_when.setText(u.listed_at.strftime("%Y-%m-%d %H:%M"))
        self.u_table.setRowCount(len(u.by_prefix))
        for row, (prefix, (count, size)) in enumerate(u.by_prefix.items()):
            self.u_table.setItem(row, 0, QTableWidgetItem(prefix))
            self.u_table.setItem(row, 1, QTableWidgetItem(f"{count:,}"))
            self.u_table.setItem(row, 2, QTableWidgetItem(format_bytes(size)))
        ops_a = self.history.class_a_ops_this_month(self.config.bucket)
        est = pricing.estimate(u.total_bytes, class_a_ops=ops_a, pricing=self.config.pricing)
        self.c_total.setText(f"${est.total_usd:,.2f} / 月  （約 ¥{est.total_jpy:,.0f}）")
        self.c_detail.setText(
            f"ストレージ {est.storage_gb:,.2f} GB（1 GB = 10億バイト換算、無料枠 {self.config.pricing.free_storage_gb:g} GB 超過分 "
            f"{est.billable_storage_gb:,.2f} GB）→ ${est.storage_usd:,.2f}\n"
            f"Class A 操作（今月・本アプリ分）{est.class_a_ops:,} 回 → ${est.class_a_usd:,.2f}"
            + ("\n現在は無料枠の範囲内です。" if est.within_free_tier else "")
        )

    def _selected_objects(self):
        rows = sorted({self.obj_filter.mapToSource(i).row() for i in self.obj_view.selectionModel().selectedRows()})
        return [self.obj_model.object(r) for r in rows]

    def copy_object_urls(self):
        self._copy_urls([public_url(self.config.public_base_url, o.key) for o in self._selected_objects()])

    def open_object_urls(self):
        for o in self._selected_objects()[:10]:
            QDesktopServices.openUrl(QUrl(public_url(self.config.public_base_url, o.key)))

    def _objects_menu(self, pos):
        if not self._selected_objects():
            return
        menu = QMenu(self)
        menu.addAction("公開URLをコピー", self.copy_object_urls)
        menu.addAction("ブラウザで開く", self.open_object_urls)
        menu.addAction("ポートフォリオ登録データ出力", self.export_objects_json)
        menu.exec(self.obj_view.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------ history
    def refresh_history(self):
        rows = self.history.recent(self.config.bucket)
        self._history_rows = rows
        self.h_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            res = f"{row['width']}×{row['height']}" if row.get("width") else ""
            values = [
                (row["uploaded_at"] or "")[:19].replace("T", " "), row["key"],
                CATEGORY_LABELS.get(row.get("category") or "", ""), format_bytes(row.get("size")),
                format_duration(row["duration"]) if row.get("duration") else "", res, row.get("public_url") or "",
            ]
            for c, v in enumerate(values):
                self.h_table.setItem(r, c, QTableWidgetItem(v))
        self.h_table.resizeColumnsToContents()

    def _selected_history(self):
        rows = sorted({i.row() for i in self.h_table.selectionModel().selectedRows()})
        return [self._history_rows[r] for r in rows]

    def copy_history_urls(self):
        self._copy_urls([r["public_url"] for r in self._selected_history() if r.get("public_url")])

    # ------------------------------------------------------------------ JSON export
    def _candidates_from_rows(self, rows: list[dict]) -> list[portfolio.Candidate]:
        """MV/BGM rows → registration candidates; probe the public URL for missing length/size."""
        cands = []
        for row in rows:
            if row.get("category") not in ("mv", "bgm"):
                continue
            c = portfolio.Candidate.from_history(row)
            if c.kind == "work" and (c.duration is None or not c.width) and self.ffprobe:
                try:
                    info = media.probe(self.ffprobe, public_url(self.config.public_base_url, c.key))
                    c.duration = round(info.duration, 2) if info.duration else None
                    c.width, c.height = info.display_size
                    c.thumb_time = portfolio.default_thumb_time(c.duration)
                except media.FFmpegError as exc:
                    log.warning("Could not probe %s: %s", c.key, exc)
            cands.append(c)
        return cands

    def _export(self, rows: list[dict]):
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            cands = self._candidates_from_rows(rows)
        finally:
            QGuiApplication.restoreOverrideCursor()
        if not cands:
            QMessageBox.information(self, "登録データ出力", "出力できる MV / BGM がありません（アップロード済みのものを選択してください）。")
            return
        dlg = ExportDialog(self, cands, self.config, self.history, self.ffmpeg,
                           lambda k: public_url(self.config.public_base_url, k))
        dlg.exec()
        self.config_store.save(self.config)
        if dlg.output_path:
            log.info("ポートフォリオ登録データを出力しました: %s", dlg.output_path)

    def export_session_json(self):
        jobs = [j for j in (self._selected_jobs() or self.manager.jobs) if j.state == JobState.DONE and j.history_id]
        ids = {j.history_id for j in jobs}
        rows = [r for r in reversed(self.history.recent(self.config.bucket)) if r["id"] in ids]
        if not rows:
            self.tabs.setCurrentIndex(3)
            QMessageBox.information(self, "ポートフォリオ登録", "このセッションでアップロードしたファイルがありません。［履歴］タブから選んで出力できます。")
            return
        self._export(rows)

    def export_history_json(self):
        self._export(list(reversed(self._selected_history())))

    def export_objects_json(self):
        rows = []
        for o in self._selected_objects():
            hist = self.history.latest_for_key(self.config.bucket, o.key)
            if hist:
                rows.append(hist)
                continue
            from ..keys import classify, content_type_for

            row = {"key": o.key, "category": classify(o.key), "size": o.size, "content_type": content_type_for(o.key),
                   "uploaded_at": o.last_modified.isoformat() if o.last_modified else None}
            rows.append(row)
        self._export(rows)

    # ------------------------------------------------------------------ close
    def closeEvent(self, event):  # noqa: N802
        if self.manager.running:
            ans = QMessageBox.question(
                self, "終了", "アップロード中です。一時停止して終了しますか？\n（次回起動時に続きから再開できます）")
            if ans != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.manager.pause()
            progress = QProgressDialog("送信中のパートを完了しています…", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            while self.manager.running:
                QGuiApplication.processEvents()
                self.manager.wait(0.1)
            progress.close()
        self.timer.stop()
        self.manager.shutdown()
        logging.getLogger("jinn_uploader").removeHandler(self.log_handler)
        self.config_store.save(self.config)
        event.accept()
