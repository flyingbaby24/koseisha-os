"""Settings, duplicate/overwrite decisions and Infinite Archive export dialogs."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from .. import archive_json, media
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
        self.gen_thumbs = QCheckBox("MV/BGM のサムネイルを生成する")
        self.gen_thumbs.setChecked(self.config.generate_thumbnails)
        self.up_thumbs = QCheckBox("生成したサムネイルも R2 にアップロードする")
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
        self.next_mv = QSpinBox()
        self.next_mv.setRange(1, 9999)
        self.next_mv.setValue(self.config.archive_next_mv_number)
        self.next_bgm = QSpinBox()
        self.next_bgm.setRange(1, 9999)
        self.next_bgm.setValue(self.config.archive_next_bgm_number)
        f2.addRow("MV の保存先", self.mv_prefix)
        f2.addRow("BGM の保存先", self.bgm_prefix)
        f2.addRow("サムネイルの保存先", self.thumb_prefix)
        f2.addRow("その他の保存先", self.other_prefix)
        f2.addRow("出力フォルダ（JSON・サムネイル）", r2)
        f2.addRow("アーティスト名（JSON）", self.artist)
        f2.addRow("次の MV 番号（mv-XXXX）", self.next_mv)
        f2.addRow("次の BGM 番号（bgm-XXXX）", self.next_bgm)
        lay.addWidget(g1)
        lay.addWidget(g2)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------------ actions
    def _browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(self, "ffmpeg を選択", "", "ffmpeg (ffmpeg*);;すべて (*)")
        if path:
            self.ffmpeg_path.setText(path)

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
        c.archive_next_mv_number = self.next_mv.value()
        c.archive_next_bgm_number = self.next_bgm.value()
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
    """Review titles/slugs/IDs, then write the Infinite Archive registration JSON."""

    COLS = ["種別", "ID番号", "slug", "タイトル", "アーティスト", "説明", "キー"]

    def __init__(self, parent, items: list[archive_json.ArchiveItem], config: AppConfig):
        super().__init__(parent)
        self.setWindowTitle("Infinite Archive 登録用 JSON の出力")
        self.resize(1000, 460)
        self.items = items
        self.config = config
        self.output_path: Path | None = None
        self.table = QTableWidget(len(items), len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        for row, it in enumerate(items):
            values = ["MV" if it.category == "mv" else "BGM", str(it.number), it.slug, it.title, it.artist,
                      it.description or "", it.key]
            for col, v in enumerate(values):
                cell = QTableWidgetItem(v)
                if col in (0, 6):
                    cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, cell)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.dir_edit = QLineEdit(str(config.export_path()))
        browse = QPushButton("参照…")
        browse.clicked.connect(self._browse)
        r = QHBoxLayout()
        r.addWidget(QLabel("出力先"))
        r.addWidget(self.dir_edit, 1)
        r.addWidget(browse)
        buttons = QDialogButtonBox()
        write_btn = buttons.addButton("JSON を出力", QDialogButtonBox.ButtonRole.AcceptRole)
        write_btn.setObjectName("primary")
        copy_btn = buttons.addButton("クリップボードにコピー", QDialogButtonBox.ButtonRole.ActionRole)
        buttons.addButton("閉じる", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._write)
        buttons.rejected.connect(self.reject)
        copy_btn.clicked.connect(self._copy)
        lay = QVBoxLayout(self)
        lay.addWidget(_hint("works は Infinite Archive の x-data（id / slug / title / artist / w / h / durationText / "
                            "thumb / poster / video / page / description / lyrics）と同じ形式です。"
                            "セルをダブルクリックして編集できます。"))
        lay.addWidget(self.table)
        lay.addLayout(r)
        lay.addWidget(buttons)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "出力フォルダ", self.dir_edit.text())
        if path:
            self.dir_edit.setText(path)

    def _collect(self) -> dict | None:
        for row, it in enumerate(self.items):
            try:
                it.number = int(self.table.item(row, 1).text())
            except ValueError:
                QMessageBox.warning(self, "ID番号", f"{row + 1} 行目の ID番号が数値ではありません")
                return None
            it.slug = self.table.item(row, 2).text().strip()
            it.title = self.table.item(row, 3).text().strip()
            it.artist = self.table.item(row, 4).text().strip()
            it.description = self.table.item(row, 5).text().strip() or None
        doc = archive_json.build_document(self.items, self.config.public_base_url, self.config.bucket)
        problems = archive_json.validate_document(doc)
        if problems:
            QMessageBox.warning(self, "確認してください", "\n".join(problems))
            return None
        return doc

    def _copy(self):
        doc = self._collect()
        if doc:
            QGuiApplication.clipboard().setText(json.dumps(doc, ensure_ascii=False, indent=2))

    def _write(self):
        doc = self._collect()
        if not doc:
            return
        out_dir = Path(self.dir_edit.text().strip() or self.config.export_path())
        try:
            self.output_path = archive_json.write_document(doc, out_dir)
        except OSError as exc:
            QMessageBox.critical(self, "出力できません", str(exc))
            return
        mv_numbers = [i.number for i in self.items if i.category == "mv"]
        bgm_numbers = [i.number for i in self.items if i.category == "bgm"]
        if mv_numbers:
            self.config.archive_next_mv_number = max(self.config.archive_next_mv_number, max(mv_numbers) + 1)
        if bgm_numbers:
            self.config.archive_next_bgm_number = max(self.config.archive_next_bgm_number, max(bgm_numbers) + 1)
        box = QMessageBox(self)
        box.setWindowTitle("出力しました")
        box.setText(f"JSON を出力しました:\n{self.output_path}")
        open_btn = box.addButton("フォルダを開く", QMessageBox.ButtonRole.ActionRole)
        box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if box.clickedButton() is open_btn:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path.parent)))
        self.accept()
