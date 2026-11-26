"""Settings and duplicate/overwrite decision dialogs (portfolio registration: portfolio_dialog.py)."""

from __future__ import annotations

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

from .. import media
from ..config import AppConfig
from ..credentials import CredentialError, CredentialStore, GitHubTokenStore, R2Credentials, mask_token
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
    def __init__(self, parent, config: AppConfig, cred_store: CredentialStore,
                 github_store: GitHubTokenStore | None = None):
        super().__init__(parent)
        self.github_store = github_store or GitHubTokenStore(backend=cred_store.backend)
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
        tabs.addTab(self._github_tab(), "ポートフォリオ（GitHub）")

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
        self.portfolio_dir.setPlaceholderText("ローカル出力方式で使う Jinn-Portfolio のフォルダ（GitHub 直接登録では不要）")
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
        f2.addRow("ローカルのポートフォリオ（任意）", r3)
        f2.addRow("アーティスト名（works.json）", self.artist)
        f2.addRow(_hint("作品 ID（mv-XXXX）・slug・BGM の id は、ポートフォリオの既存データと過去の出力を確認して"
                        "重複しない値を自動で割り当てます。"))
        lay.addWidget(g1)
        lay.addWidget(g2)
        lay.addStretch(1)
        return w

    def _github_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout()
        self.gh_repo = QLineEdit(self.config.github_repo)
        self.gh_repo.setPlaceholderText("owner/name")
        self.gh_branch = QLineEdit(self.config.github_branch)
        self.gh_branch.setPlaceholderText("空欄 = リポジトリの既定ブランチ（登録画面で選択できます）")
        self.pages_project = QLineEdit(self.config.pages_project)
        self.gh_token_lbl = QLabel()
        token_btn = QPushButton("トークンを登録・変更…")
        token_btn.clicked.connect(self._edit_github_token)
        self.gh_del_btn = QPushButton("トークンを削除")
        self.gh_del_btn.clicked.connect(self._delete_github_token)
        tr = QHBoxLayout()
        tr.addWidget(self.gh_token_lbl, 1)
        tr.addWidget(token_btn)
        tr.addWidget(self.gh_del_btn)
        form.addRow("リポジトリ", self.gh_repo)
        form.addRow("反映先ブランチ（既定）", self.gh_branch)
        form.addRow("Cloudflare Pages プロジェクト", self.pages_project)
        form.addRow("GitHub トークン", tr)
        lay = QVBoxLayout(w)
        lay.addLayout(form)
        lay.addWidget(_hint(
            "登録画面の「GitHub に直接登録」は、GitHub API からこのリポジトリの最新データを取得し、確認後に"
            "1 回のコミット（data/*.json と public/thumbnails/*）として反映します。ブランチは早送りでのみ更新し、"
            "途中で他の更新があった場合は上書きせずに中止します。反映後は Cloudflare Pages が自動でビルドします"
            "（本番ブランチ → サイト、その他のブランチ → プレビュー URL）。"))
        lay.addWidget(_hint(f"トークンの保存先: {self.github_store.backend_label}（汎用資格情報 JinnMediaUploader/GitHub）。"))
        lay.addStretch(1)
        self._refresh_github_token()
        return w

    def _refresh_github_token(self):
        try:
            token = self.github_store.load()
        except CredentialError as exc:
            token = None
            self.gh_token_lbl.setText(str(exc))
        if token:
            self.gh_token_lbl.setText(f"保存済み（{mask_token(token)}）")
        elif not self.gh_token_lbl.text():
            self.gh_token_lbl.setText("未設定")
        self.gh_del_btn.setEnabled(bool(token))

    def _edit_github_token(self):
        from .portfolio_dialog import GitHubTokenDialog

        GitHubTokenDialog(self, self.github_store, self.gh_repo.text().strip() or self.config.github_repo,
                          self.config.github_api).exec()
        self._refresh_github_token()

    def _delete_github_token(self):
        if QMessageBox.question(self, "確認", "保存済みの GitHub トークンを、このPCの資格情報マネージャーから削除しますか？") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.github_store.delete()
        except CredentialError as exc:
            QMessageBox.warning(self, "エラー", str(exc))
        self.gh_token_lbl.setText("未設定")
        self._refresh_github_token()

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
        repo = self.gh_repo.text().strip().strip("/")
        if repo and (repo.count("/") != 1 or not all(repo.split("/"))):
            QMessageBox.warning(self, "GitHub", "リポジトリは owner/name の形式で指定してください。")
            return
        c.github_repo = repo or c.github_repo
        c.github_branch = self.gh_branch.text().strip()
        c.pages_project = self.pages_project.text().strip() or c.pages_project
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
