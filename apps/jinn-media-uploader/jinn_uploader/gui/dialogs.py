"""Settings, duplicate/overwrite decisions and Infinite Archive export dialogs."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import media, portfolio
from ..config import AppConfig
from ..credentials import CredentialError, CredentialStore, R2Credentials
from ..keys import format_bytes, normalize_prefix
from ..r2client import R2Service, endpoint_for, make_client
from ..uploader import REMOTE_LABELS, UploadJob
from .worker import run_async

COMPRESSION_LABELS = [
    ("none", "元ファイルのまま（推奨・無変換）"),
    ("faststart", "Web最適化（無劣化・faststart）"),
    ("h264", "圧縮（H.264 再エンコード）"),
]


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("muted")
    lbl.setWordWrap(True)
    return lbl


class SettingsDialog(QDialog):
    def __init__(self, parent, config: AppConfig, cred_store: CredentialStore):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setMinimumWidth(620)
        self.config = config
        self.cred_store = cred_store
        self.credentials_changed = False
        try:
            self.saved_creds = cred_store.load()
        except CredentialError:
            self.saved_creds = None

        tabs = QTabWidget()
        tabs.addTab(self._connection_tab(), "R2 接続")
        tabs.addTab(self._transfer_tab(), "転送")
        tabs.addTab(self._media_tab(), "メディア・出力")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("キャンセル")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        lay.addWidget(buttons)

    # ------------------------------------------------------------------ tabs
    def _connection_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout()
        self.account_label = QLineEdit(self.config.account_label)
        self.account_id = QLineEdit(self.saved_creds.account_id if self.saved_creds else "")
        self.account_id.setPlaceholderText("32桁の16進数（Cloudflare ダッシュボード → R2 → Account ID）")
        self.access_key = QLineEdit(self.saved_creds.access_key_id if self.saved_creds else "")
        self.access_key.setPlaceholderText("R2 API トークンの Access Key ID")
        self.secret_key = QLineEdit()
        self.secret_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.secret_key.setPlaceholderText(
            "保存済み（変更する場合のみ入力）" if self.saved_creds else "R2 API トークンの Secret Access Key"
        )
        show = QCheckBox("表示")
        show.toggled.connect(
            lambda on: self.secret_key.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)
        )
        secret_row = QHBoxLayout()
        secret_row.addWidget(self.secret_key, 1)
        secret_row.addWidget(show)
        self.bucket = QLineEdit(self.config.bucket)
        self.public_url = QLineEdit(self.config.public_base_url)
        self.endpoint = QLineEdit(self.config.endpoint_override)
        self.endpoint.setPlaceholderText("空欄 = https://<Account ID>.r2.cloudflarestorage.com")

        form.addRow("アカウント（表示名）", self.account_label)
        form.addRow("Account ID", self.account_id)
        form.addRow("Access Key ID", self.access_key)
        form.addRow("Secret Access Key", secret_row)
        form.addRow("バケット", self.bucket)
        form.addRow("公開ベースURL", self.public_url)
        form.addRow("エンドポイント（任意）", self.endpoint)

        store_lbl = _hint(
            f"認証情報の保存先: {self.cred_store.backend_label}"
            + ("" if self.cred_store.secure else "（安全なストアが見つからないため保存できません）")
            + "。設定ファイルやログには書き込みません。"
        )
        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        test_btn = QPushButton("接続テスト（読み取りのみ）")
        test_btn.clicked.connect(self._test)
        del_btn = QPushButton("保存済み認証情報を削除")
        del_btn.clicked.connect(self._delete_creds)
        del_btn.setEnabled(self.saved_creds is not None)
        row = QHBoxLayout()
        row.addWidget(test_btn)
        row.addStretch(1)
        row.addWidget(del_btn)

        lay = QVBoxLayout(w)
        lay.addLayout(form)
        lay.addWidget(store_lbl)
        lay.addWidget(_hint("推奨: R2 の API トークンは「オブジェクト読み取りと書き込み」権限で、対象を jinn-mv-portfolio バケットのみに限定してください。"))
        lay.addLayout(row)
        lay.addWidget(self.test_result)
        lay.addStretch(1)
        return w

    def _transfer_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.part_size = QSpinBox()
        self.part_size.setRange(5, 512)
        self.part_size.setSuffix(" MiB")
        self.part_size.setValue(self.config.part_size_mib)
        self.threshold = QSpinBox()
        self.threshold.setRange(5, 4096)
        self.threshold.setSuffix(" MiB")
        self.threshold.setValue(self.config.multipart_threshold_mib)
        self.concurrency = QSpinBox()
        self.concurrency.setRange(1, 16)
        self.concurrency.setValue(self.config.concurrency)
        self.retries = QSpinBox()
        self.retries.setRange(0, 20)
        self.retries.setValue(self.config.max_retries)
        form.addRow("パートサイズ", self.part_size)
        form.addRow("マルチパート開始サイズ", self.threshold)
        form.addRow("同時送信パート数", self.concurrency)
        form.addRow("パートごとの再試行回数", self.retries)
        form.addRow(_hint(
            "300MB を超える動画も、パート単位で並列送信・失敗時はそのパートだけ自動再試行します。"
            "一時停止・中断したアップロードは送信済みパートから再開します。"
        ))
        return w

    def _media_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        g1 = QGroupBox("FFmpeg")
        f1 = QFormLayout(g1)
        self.ffmpeg_path = QLineEdit(self.config.ffmpeg_path)
        self.ffmpeg_path.setPlaceholderText("空欄 = EXE と同じフォルダの ffmpeg\\ → PATH の順で自動検出")
        browse = QPushButton("参照…")
        browse.clicked.connect(self._browse_ffmpeg)
        r = QHBoxLayout()
        r.addWidget(self.ffmpeg_path, 1)
        r.addWidget(browse)
        f1.addRow("ffmpeg.exe", r)
        found, probe_found = media.find_ffmpeg(self.config.ffmpeg_path)
        f1.addRow(_hint(f"検出: {found or '見つかりません'} / ffprobe: {probe_found or '見つかりません'}"))
        self.compression = QComboBox()
        for key, label in COMPRESSION_LABELS:
            self.compression.addItem(label, key)
        self.compression.setCurrentIndex(max(0, self.compression.findData(self.config.compression)))
        self.crf = QSpinBox()
        self.crf.setRange(14, 35)
        self.crf.setValue(self.config.h264_crf)
        self.gen_thumbs = QCheckBox("MV のサムネイル（WebP カード用・JPEG ポスター）を生成する")
        self.gen_thumbs.setChecked(self.config.generate_thumbnails)
        self.up_thumbs = QCheckBox("生成したサムネイルを R2 にもコピーする（通常は不要：サイトの public/thumbnails から配信）")
        self.up_thumbs.setChecked(self.config.upload_thumbnails)
        f1.addRow("動画の処理", self.compression)
        f1.addRow("H.264 品質 (CRF)", self.crf)
        f1.addRow(self.gen_thumbs)
        f1.addRow(self.up_thumbs)

        g2 = QGroupBox("保存先・出力")
        f2 = QFormLayout(g2)
        self.mv_prefix = QLineEdit(self.config.mv_prefix)
        self.bgm_prefix = QLineEdit(self.config.bgm_prefix)
        self.thumb_prefix = QLineEdit(self.config.thumb_prefix)
        self.other_prefix = QLineEdit(self.config.other_prefix)
        self.export_dir = QLineEdit(str(self.config.export_path()))
        exp_browse = QPushButton("参照…")
        exp_browse.clicked.connect(self._browse_export)
        r2 = QHBoxLayout()
        r2.addWidget(self.export_dir, 1)
        r2.addWidget(exp_browse)
        self.artist = QLineEdit(self.config.archive_artist)
        self.portfolio_dir = QLineEdit(self.config.portfolio_dir)
        self.portfolio_dir.setPlaceholderText("Jinn-Portfolio リポジトリのフォルダ（data/works.json があるところ）")
        pf_browse = QPushButton("参照…")
        pf_browse.clicked.connect(self._browse_portfolio)
        r3 = QHBoxLayout()
        r3.addWidget(self.portfolio_dir, 1)
        r3.addWidget(pf_browse)
        f2.addRow("MV の保存先", self.mv_prefix)
        f2.addRow("BGM の保存先", self.bgm_prefix)
        f2.addRow("サムネイルの保存先", self.thumb_prefix)
        f2.addRow("その他の保存先", self.other_prefix)
        f2.addRow("出力フォルダ（JSON・サムネイル）", r2)
        f2.addRow("ポートフォリオのフォルダ", r3)
        f2.addRow("アーティスト名（works.json）", self.artist)
        f2.addRow(_hint("作品 ID（mv-XXXX）・slug・BGM の id は、ポートフォリオの既存データと過去の出力を確認して"
                        "重複しない値を自動で割り当てます。"))
        lay.addWidget(g1)
        lay.addWidget(g2)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------ actions
    def _browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "ffmpeg を選択", "", "ffmpeg (ffmpeg*);;すべて (*)")
        if path:
            self.ffmpeg_path.setText(path)

    def _browse_portfolio(self):
        path = QFileDialog.getExistingDirectory(self, "Jinn-Portfolio のフォルダを選択", self.portfolio_dir.text())
        if path:
            self.portfolio_dir.setText(path)

    def _browse_export(self):
        path = QFileDialog.getExistingDirectory(self, "出力フォルダを選択", self.export_dir.text())
        if path:
            self.export_dir.setText(path)

    def _entered_creds(self) -> R2Credentials | None:
        secret = self.secret_key.text().strip() or (self.saved_creds.secret_access_key if self.saved_creds else "")
        creds = R2Credentials(self.account_id.text(), self.access_key.text(), secret)
        if creds.problems():
            return None
        return creds.cleaned()

    def _test(self):
        creds = self._entered_creds()
        if creds is None:
            self.test_result.setText("Account ID / Access Key ID / Secret Access Key を入力してください。")
            return
        bucket = self.bucket.text().strip()
        endpoint = self.endpoint.text().strip()
        public = self.public_url.text().strip()
        self.test_result.setText(f"接続中… {endpoint_for(creds.account_id, endpoint)}")

        def work():
            svc = R2Service(make_client(creds, endpoint), bucket, public)
            return svc.test_connection()

        def ok(result):
            sample = result["sample"][0] if result["sample"] else "（空）"
            self.test_result.setText(f"✔ 接続できました。バケット「{bucket}」を読み取れます（例: {sample}）。")

        run_async(work, on_done=ok, on_error=lambda m: self.test_result.setText("✖ 接続できません: " + m))

    def _delete_creds(self):
        if QMessageBox.question(self, "確認", "保存済みの R2 認証情報を、このPCの資格情報マネージャーから削除しますか？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.cred_store.delete()
        except CredentialError as exc:
            QMessageBox.warning(self, "エラー", str(exc))
            return
        self.saved_creds = None
        self.account_id.clear()
        self.access_key.clear()
        self.secret_key.clear()
        self.secret_key.setPlaceholderText("R2 API トークンの Secret Access Key")
        self.credentials_changed = True
        self.test_result.setText("認証情報を削除しました。")

    def _save(self):
        try:
            prefixes = {
                "mv": normalize_prefix(self.mv_prefix.text()),
                "bgm": normalize_prefix(self.bgm_prefix.text()),
                "thumb": normalize_prefix(self.thumb_prefix.text()),
                "other": normalize_prefix(self.other_prefix.text()),
            }
        except ValueError as exc:
            QMessageBox.warning(self, "保存先", str(exc))
            return
        entered = any(x.text().strip() for x in (self.account_id, self.access_key, self.secret_key))
        if entered:
            creds = self._entered_creds()
            if creds is None:
                QMessageBox.warning(self, "認証情報", "Account ID / Access Key ID / Secret Access Key をすべて入力してください。")
                return
            warnings = creds.warnings()
            if warnings and QMessageBox.question(
                self, "確認", "\n".join(warnings) + "\n\nこのまま保存しますか？"
            ) != QMessageBox.StandardButton.Yes:
                return
            if creds != self.saved_creds:
                try:
                    self.cred_store.save(creds)
                except CredentialError as exc:
                    QMessageBox.critical(self, "保存できません", str(exc))
                    return
                self.credentials_changed = True
        c = self.config
        if (c.bucket, c.endpoint_override) != (self.bucket.text().strip(), self.endpoint.text().strip()):
            self.credentials_changed = True
        c.account_label = self.account_label.text().strip() or c.account_label
        c.bucket = self.bucket.text().strip() or c.bucket
        c.public_base_url = self.public_url.text().strip() or c.public_base_url
        c.endpoint_override = self.endpoint.text().strip()
        c.part_size_mib = self.part_size.value()
        c.multipart_threshold_mib = self.threshold.value()
        c.concurrency = self.concurrency.value()
        c.max_retries = self.retries.value()
        c.ffmpeg_path = self.ffmpeg_path.text().strip()
        c.compression = self.compression.currentData()
        c.h264_crf = self.crf.value()
        c.generate_thumbnails = self.gen_thumbs.isChecked()
        c.upload_thumbnails = self.up_thumbs.isChecked()
        c.mv_prefix, c.bgm_prefix = prefixes["mv"], prefixes["bgm"]
        c.thumb_prefix, c.other_prefix = prefixes["thumb"], prefixes["other"]
        c.export_dir = self.export_dir.text().strip()
        c.archive_artist = self.artist.text().strip() or "Jinn Project"
        c.portfolio_dir = self.portfolio_dir.text().strip()
        c.normalized()
        self.accept()


# ---------------------------------------------------------------------- decisions
DECISION_LABELS = {
    "skip": "スキップ",
    "rename": "別名で保存",
    "overwrite": "上書きする",
    "upload": "それでもアップロード",
}

OPTIONS_BY_REMOTE = {
    "identical": ["skip", "rename", "overwrite"],
    "conflict": ["rename", "skip", "overwrite"],
    "content_dup": ["skip", "upload"],
    "queue_dup": ["skip", "upload"],
    "queue_key": ["rename", "skip"],
}


class DecisionDialog(QDialog):
    """Ask what to do with duplicates and existing keys before uploading."""

    def __init__(self, parent, jobs: list[UploadJob]):
        super().__init__(parent)
        self.setWindowTitle("重複・既存ファイルの確認")
        self.resize(980, 420)
        self.jobs = jobs
        self.table = QTableWidget(len(jobs), 4)
        self.table.setHorizontalHeaderLabels(["ファイル", "保存先キー", "状況", "対応"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.combos: list[QComboBox] = []
        for row, job in enumerate(jobs):
            self.table.setItem(row, 0, QTableWidgetItem(job.name))
            self.table.setItem(row, 1, QTableWidgetItem(job.key))
            detail = REMOTE_LABELS.get(job.remote, job.remote)
            if job.remote_info is not None:
                ri = job.remote_info
                when = ri.last_modified.astimezone().strftime("%Y-%m-%d %H:%M") if ri.last_modified else "?"
                detail += f" — 既存: {format_bytes(ri.size)}, {when}"
            if job.duplicates:
                detail += " — " + ", ".join(job.duplicates)
            item = QTableWidgetItem(detail)
            item.setToolTip(detail)
            self.table.setItem(row, 2, item)
            cb = QComboBox()
            for d in OPTIONS_BY_REMOTE.get(job.remote, ["skip", "upload"]):
                cb.addItem(DECISION_LABELS[d], d)
            self.table.setCellWidget(row, 3, cb)
            self.combos.append(cb)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        all_skip = QPushButton("すべてスキップ")
        all_skip.clicked.connect(lambda: self._set_all("skip"))
        all_rename = QPushButton("可能なものはすべて別名で保存")
        all_rename.clicked.connect(lambda: self._set_all("rename"))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("この内容で続行")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("キャンセル")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(all_skip)
        row.addWidget(all_rename)
        row.addStretch(1)
        row.addWidget(buttons)
        lay = QVBoxLayout(self)
        lay.addWidget(_hint("同じ保存先のファイルや同一内容のファイルが見つかりました。それぞれの対応を選んでください。"
                            "既存ファイルは「上書きする」を選んで再確認した場合を除き、変更されません。"))
        lay.addWidget(self.table)
        lay.addLayout(row)
        self.decisions: dict[str, str] = {}

    def _set_all(self, decision: str):
        for cb in self.combos:
            i = cb.findData(decision)
            if i >= 0:
                cb.setCurrentIndex(i)

    def _accept(self):
        decisions = {job.id: cb.currentData() for job, cb in zip(self.jobs, self.combos)}
        overwrites = [job.key for job in self.jobs if decisions[job.id] == "overwrite"]
        if overwrites:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("上書きの確認")
            msg.setText(f"R2 上の既存ファイル {len(overwrites)} 件を上書きします。元に戻せません。本当によろしいですか？")
            msg.setDetailedText("\n".join(overwrites))
            yes = msg.addButton("上書きする", QMessageBox.ButtonRole.DestructiveRole)
            msg.addButton("やめる", QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            if msg.clickedButton() is not yes:
                return
        self.decisions = decisions
        self.accept()


# ---------------------------------------------------------------------- export
class ExportDialog(QDialog):
    """Register uploaded MVs/BGM in the portfolio's data files (works.json / soundscape.json).

    IDs and slugs are allocated around the portfolio's existing data and around IDs
    issued by earlier exports; the result is validated with ports of the site's own
    validators before anything is written.
    """

    COLS = ["登録", "種別", "ID", "slug", "タイトル", "状態", "掲載日", "サムネ位置(秒)", "オブジェクトキー", "備考"]
    C_INC, C_KIND, C_ID, C_SLUG, C_TITLE, C_STATUS, C_DATE, C_TIME, C_KEY, C_NOTE = range(10)

    def __init__(self, parent, candidates: list[portfolio.Candidate], config: AppConfig, history,
                 ffmpeg: str | None, public_url_for):
        super().__init__(parent)
        self.setWindowTitle("ポートフォリオ（Infinite Archive）への登録データを出力")
        self.resize(1180, 520)
        self.cands = candidates
        self.config = config
        self.history = history
        self.ffmpeg = ffmpeg
        self.public_url_for = public_url_for
        self.data: portfolio.PortfolioData | None = None
        self.output_path: Path | None = None
        self._filling = False

        self.pf_edit = QLineEdit(config.portfolio_dir)
        self.pf_edit.setPlaceholderText("Jinn-Portfolio リポジトリのフォルダ（data/works.json があるところ）")
        self.pf_edit.editingFinished.connect(lambda: self._load(self.pf_edit.text()))
        pf_browse = QPushButton("参照…")
        pf_browse.clicked.connect(self._browse_portfolio)
        self.pf_status = QLabel("")
        self.pf_status.setWordWrap(True)
        top = QHBoxLayout()
        top.addWidget(QLabel("ポートフォリオ"))
        top.addWidget(self.pf_edit, 1)
        top.addWidget(pf_browse)

        self.table = QTableWidget(len(candidates), len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(self.C_NOTE, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)

        self.dir_edit = QLineEdit(str(config.export_path()))
        browse = QPushButton("参照…")
        browse.clicked.connect(self._browse_out)
        r = QHBoxLayout()
        r.addWidget(QLabel("出力先"))
        r.addWidget(self.dir_edit, 1)
        r.addWidget(browse)
        buttons = QDialogButtonBox()
        self.write_btn = buttons.addButton("登録データを出力", QDialogButtonBox.ButtonRole.AcceptRole)
        self.write_btn.setObjectName("primary")
        buttons.addButton("閉じる", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._write)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.pf_status)
        lay.addWidget(_hint(
            "出力されるのはリポジトリと同じ構成のフォルダ（data/works.json・data/soundscape.json・"
            "data/thumbnail-sources.json・public/thumbnails/…）です。既存の記述は変更せず末尾に追加します。"
            "解説・歌詞・ジャンルなど未提供の項目は null / [] のままにします。"))
        lay.addWidget(self.table, 1)
        lay.addLayout(r)
        lay.addWidget(buttons)
        if config.portfolio_dir:
            self._load(config.portfolio_dir)
        else:
            self._set_status("Jinn-Portfolio のフォルダを指定してください（既存の作品 ID との重複を防ぐために必要です）。", False)
            self._fill()

    # ------------------------------------------------------------------ portfolio data
    def _set_status(self, text: str, ok: bool):
        self.pf_status.setText(("✔ " if ok else "✖ ") + text)
        self.pf_status.setStyleSheet(f"color: {'#7fbf8e' if ok else '#e07a6e'};")
        self.write_btn.setEnabled(ok)

    def _browse_portfolio(self):
        path = QFileDialog.getExistingDirectory(self, "Jinn-Portfolio のフォルダを選択", self.pf_edit.text())
        if path:
            self.pf_edit.setText(path)
            self._load(path)

    def _load(self, path: str):
        path = path.strip()
        if not path:
            return
        try:
            self.data = portfolio.PortfolioData.load(path)
        except portfolio.PortfolioError as exc:
            self.data = None
            self._set_status(str(exc), False)
            self._fill()
            return
        self.config.portfolio_dir = str(self.data.root)
        self._set_status(f"既存データ: {self.data.summary()}（{self.data.root}）", True)
        issued = {**self.history.issued_ids("work"), **self.history.issued_ids("track")}
        portfolio.plan(self.cands, self.data, issued)
        self._fill()

    # ------------------------------------------------------------------ table
    def _fill(self):
        self._filling = True
        ro = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        for row, c in enumerate(self.cands):
            is_work = c.kind == "work"
            registered = c.note.startswith("登録済み") or c.note.startswith("サイトが再生できない")
            inc = QTableWidgetItem()
            inc.setFlags(ro | (Qt.ItemFlag.ItemIsUserCheckable if not registered and self.data else Qt.ItemFlag.NoItemFlags))
            inc.setCheckState(Qt.CheckState.Checked if c.include and self.data else Qt.CheckState.Unchecked)
            self.table.setItem(row, self.C_INC, inc)
            values = {
                self.C_KIND: ("MV" if is_work else "BGM", False),
                self.C_ID: (c.id, not registered),
                self.C_SLUG: (c.slug if is_work else "—", is_work and not registered),
                self.C_TITLE: (c.title, is_work and not registered),
                self.C_DATE: (c.published_date if is_work and not registered else "—", is_work and not registered),
                self.C_TIME: (f"{c.thumb_time:g}" if is_work and not registered else "—", is_work and not registered),
                self.C_KEY: (c.key, False),
                self.C_NOTE: (c.note, False),
            }
            for col, (text, editable) in values.items():
                item = QTableWidgetItem(text)
                item.setFlags(ro | (Qt.ItemFlag.ItemIsEditable if editable else Qt.ItemFlag.NoItemFlags))
                self.table.setItem(row, col, item)
            if is_work and not registered:
                cb = QComboBox()
                for st in ("published", "draft", "unlisted"):
                    cb.addItem(st, st)
                cb.setCurrentIndex(max(0, cb.findData(c.status)))
                self.table.setCellWidget(row, self.C_STATUS, cb)
            else:
                self.table.removeCellWidget(row, self.C_STATUS)
                self.table.setItem(row, self.C_STATUS, QTableWidgetItem("—"))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(self.C_NOTE, QHeaderView.ResizeMode.Stretch)
        self._filling = False

    def _on_item_changed(self, item):
        if self._filling or item.column() != self.C_INC:
            return
        self.cands[item.row()].include = item.checkState() == Qt.CheckState.Checked

    def _browse_out(self):
        path = QFileDialog.getExistingDirectory(self, "出力フォルダ", self.dir_edit.text())
        if path:
            self.dir_edit.setText(path)

    def _collect(self) -> list[str]:
        errors = []
        for row, c in enumerate(self.cands):
            if not c.include:
                continue
            text = lambda col: (self.table.item(row, col).text().strip() if self.table.item(row, col) else "")  # noqa: E731
            c.id = text(self.C_ID)
            if c.kind == "work":
                c.slug = text(self.C_SLUG)
                c.title = text(self.C_TITLE)
                c.published_date = text(self.C_DATE)
                cb = self.table.cellWidget(row, self.C_STATUS)
                c.status = cb.currentData() if cb else c.status
                try:
                    c.thumb_time = round(float(text(self.C_TIME)), 2)
                except ValueError:
                    errors.append(f"{c.id}: サムネ位置は秒数で入力してください")
                if c.duration and not (0 <= c.thumb_time < c.duration):
                    errors.append(f"{c.id}: サムネ位置が動画の長さ（{c.duration:g} 秒）の範囲外です")
        return errors

    # ------------------------------------------------------------------ output
    def _thumbnail_files(self, work_dir: Path) -> tuple[dict[str, Path], list[str]]:
        files: dict[str, Path] = {}
        errors: list[str] = []
        prefix = self.config.thumb_prefix
        for c in self.cands:
            if not (c.include and c.kind == "work"):
                continue
            thumb_key, poster_key = f"{prefix}{c.slug}.webp", f"{prefix}{c.slug}-poster.jpg"
            cached = (c.thumb_local and c.poster_local and Path(c.thumb_local).is_file()
                      and Path(c.poster_local).is_file() and Path(c.thumb_local).stem == c.slug
                      and c.thumb_time_generated is not None and abs(c.thumb_time_generated - c.thumb_time) < 0.005)
            if cached:
                files[thumb_key], files[poster_key] = Path(c.thumb_local), Path(c.poster_local)
                continue
            if not self.ffmpeg:
                errors.append(f"{c.id}: FFmpeg が見つからないためサムネイルを作成できません")
                continue
            src = c.local_path if c.local_path and Path(c.local_path).is_file() else self.public_url_for(c.key)
            try:
                th = media.make_site_thumbnails(self.ffmpeg, src, work_dir / f"{c.slug}.webp",
                                                work_dir / f"{c.slug}-poster.jpg", c.thumb_time, c.landscape)
            except media.FFmpegError as exc:
                errors.append(f"{c.id}: サムネイルを作成できません: {exc}")
                continue
            files[thumb_key], files[poster_key] = th.thumb, th.poster
        return files, errors

    def _write(self):
        if self.data is None:
            QMessageBox.warning(self, "ポートフォリオ未指定", "Jinn-Portfolio のフォルダを指定してください。")
            return
        errors = self._collect()
        if not any(c.include for c in self.cands):
            errors.append("登録する項目がありません")
        reg = portfolio.build(self.data, self.cands, self.config.thumb_prefix, self.config.archive_artist)
        errors += reg.problems
        if errors:
            QMessageBox.warning(self, "確認してください", "\n".join(errors))
            return
        import tempfile

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with tempfile.TemporaryDirectory(prefix="jmu-thumbs-") as td:
                thumbs, t_errors = self._thumbnail_files(Path(td))
                if t_errors:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.warning(self, "サムネイル", "\n".join(t_errors))
                    return
                out_dir = Path(self.dir_edit.text().strip() or self.config.export_path())
                self.output_path = portfolio.write_bundle(reg, out_dir, thumbs)
        except (OSError, portfolio.PortfolioError) as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "出力できません", str(exc))
            return
        QApplication.restoreOverrideCursor()
        self.history.record_issued("work", [(w["id"], w["videoKey"]) for w in reg.new_works])
        self.history.record_issued("track", [(t["id"], t["key"]) for t in reg.new_tracks])
        box = QMessageBox(self)
        box.setWindowTitle("出力しました")
        box.setText(
            f"作品 {len(reg.new_works)} 件・BGM {len(reg.new_tracks)} 曲の登録データを出力しました。\n{self.output_path}\n\n"
            "このフォルダの data/ と public/ を Jinn-Portfolio リポジトリのルートにコピーし、"
            "npm run build && npm test で確認してください。")
        open_btn = box.addButton("フォルダを開く", QMessageBox.ButtonRole.ActionRole)
        box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path)))
        self.accept()
