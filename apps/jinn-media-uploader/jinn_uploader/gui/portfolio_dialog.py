"""Portfolio (Infinite Archive) registration: GitHub direct mode and local-folder mode."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
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
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import media, portfolio
from .. import portfolio_github as pg
from ..config import AppConfig
from ..credentials import CredentialError, GitHubTokenStore, mask_token
from ..github_client import GitHubClient
from .worker import run_async

OK_COLOR, ERR_COLOR, MUTED = "#7fbf8e", "#e07a6e", "#9c978d"


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("muted")
    lbl.setWordWrap(True)
    return lbl


def _link(url: str, text: str | None = None) -> str:
    return f'<a href="{url}">{text or url}</a>'


# ---------------------------------------------------------------------- token
class GitHubTokenDialog(QDialog):
    """Enter, test and store the GitHub token in Windows Credential Manager."""

    def __init__(self, parent, store: GitHubTokenStore, repo: str, api: str = "https://api.github.com"):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("GitHub トークン")
        self.setMinimumWidth(560)
        self.store = store
        self.repo = repo
        self.saved = False
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        try:
            current = store.load()
        except CredentialError:
            current = None
        self.token.setPlaceholderText(f"保存済み（{mask_token(current)}）— 変更する場合のみ入力" if current else "github_pat_…")
        self.result_lbl = QLabel("")
        self.result_lbl.setWordWrap(True)
        test = QPushButton("接続テスト（読み取りのみ）")
        test.clicked.connect(self._test)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("資格情報マネージャーに保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("キャンセル")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        form = QFormLayout()
        form.addRow("リポジトリ", QLabel(repo))
        form.addRow("トークン", self.token)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(_hint(
            "GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens で作成します。"
            f"Repository access は「Only select repositories」で {repo} だけを選び、権限は "
            "Contents: Read and write、Pull requests: Read and write（プルリクエスト方式を使う場合）、"
            "Checks: Read-only（デプロイ状況の表示用）にしてください。"))
        lay.addWidget(_hint(f"保存先: {store.backend_label}（汎用資格情報 JinnMediaUploader/GitHub）。設定ファイルやログには書き込みません。"))
        row = QHBoxLayout()
        row.addWidget(test)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addWidget(self.result_lbl)
        lay.addWidget(buttons)

    def _entered(self) -> str | None:
        text = self.token.text().strip()
        if text:
            return text
        try:
            return self.store.load()
        except CredentialError:
            return None

    def _test(self):
        token = self._entered()
        if not token:
            self.result_lbl.setText("トークンを入力してください。")
            return
        self.result_lbl.setText("確認中…")
        repo = self.repo

        def work():
            client = GitHubClient(token, repo, api=self.api)
            info = client.get_repo()
            return info.get("full_name"), info.get("default_branch"), info.get("private")

        def ok(res):
            name, default, private = res
            self.result_lbl.setText(f"✔ {name} を読み取れます（既定ブランチ {default}{'・Private' if private else ''}）。"
                                    "書き込み権限は反映時に確認されます。")

        run_async(work, on_done=ok, on_error=lambda m: self.result_lbl.setText("✖ " + m))

    def _save(self):
        text = self.token.text().strip()
        if not text:
            self.reject()
            return
        try:
            self.store.save(text)
        except CredentialError as exc:
            QMessageBox.critical(self, "保存できません", str(exc))
            return
        self.saved = True
        self.accept()


# ---------------------------------------------------------------------- review
class ReviewDialog(QDialog):
    """Show exactly what will be committed before anything is sent to GitHub."""

    def __init__(self, parent, snap: pg.RemoteSnapshot, changes: list[pg.FileChange], reg: portfolio.Registration,
                 mode: str, pr_branch: str, site_url: str):
        super().__init__(parent)
        self.setWindowTitle("GitHub へ反映する内容の確認")
        self.resize(1100, 720)
        self.changes = changes
        target = (f"{snap.repo} の <b>{snap.branch}</b> に直接コミット" if mode == "commit"
                  else f"{snap.repo} に新しいブランチ <b>{pr_branch}</b> を作成し、{snap.branch} へのプルリクエストを作成")
        head = QLabel(
            f"{target}<br>基準のコミット: {snap.short}（{snap.commit_date[:16].replace('T', ' ')}）{snap.commit_message}<br>"
            f"既存: {snap.data.summary()} → 追加: 作品 {len(reg.new_works)} 件・BGM {len(reg.new_tracks)} 曲<br>"
            f"反映後、Cloudflare Pages が自動でビルドします（{_link(site_url)}）。")
        head.setTextFormat(Qt.TextFormat.RichText)
        head.setOpenExternalLinks(True)
        head.setWordWrap(True)

        summary = QTableWidget(len(reg.new_works) + len(reg.new_tracks), 4)
        summary.setHorizontalHeaderLabels(["ID", "slug / key", "タイトル", "状態"])
        summary.verticalHeader().setVisible(False)
        row = 0
        for w in reg.new_works:
            for col, v in enumerate([w["id"], w["slug"], str(w["title"]), w["status"]]):
                summary.setItem(row, col, QTableWidgetItem(v))
            row += 1
        for t in reg.new_tracks:
            for col, v in enumerate([t["id"], t["key"], "（BGM）", "soundscape"]):
                summary.setItem(row, col, QTableWidgetItem(v))
            row += 1
        summary.resizeColumnsToContents()
        summary.horizontalHeader().setStretchLastSection(True)
        summary.setMaximumHeight(150)

        self.files = QListWidget()
        for ch in changes:
            stat = "画像" if ch.binary else f"+{ch.added_lines()} / -{ch.removed_lines()}"
            note = "（既存の書式も整形されます）" if ch.reformatted else ""
            self.files.addItem(f"{ch.kind}  {ch.path}   {stat}{note}")
        self.files.currentRowChanged.connect(self._show)
        self.diff = QPlainTextEdit()
        self.diff.setReadOnly(True)
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.diff.setFont(mono)
        self.image = QLabel()
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer = QStackedWidget()
        self.viewer.addWidget(self.diff)
        self.viewer.addWidget(self.image)
        split = QSplitter()
        split.addWidget(self.files)
        split.addWidget(self.viewer)
        split.setSizes([360, 740])

        self.message = QPlainTextEdit(pg.default_message(reg))
        self.message.setMaximumHeight(110)
        buttons = QDialogButtonBox()
        go = buttons.addButton("GitHub へ反映する" if mode == "commit" else "プルリクエストを作成する",
                               QDialogButtonBox.ButtonRole.AcceptRole)
        go.setObjectName("primary")
        buttons.addButton("戻る", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(head)
        lay.addWidget(summary)
        lay.addWidget(QLabel("変更されるファイル（既存の作品・BGM の記述は変更されません）"))
        lay.addWidget(split, 1)
        lay.addWidget(QLabel("コミットメッセージ"))
        lay.addWidget(self.message)
        lay.addWidget(buttons)
        if changes:
            self.files.setCurrentRow(0)

    def _show(self, row: int):
        if row < 0:
            return
        ch = self.changes[row]
        if ch.binary:
            pm = QPixmap()
            pm.loadFromData(ch.new)
            if not pm.isNull() and pm.width() > 640:
                pm = pm.scaledToWidth(640, Qt.TransformationMode.SmoothTransformation)
            self.image.setPixmap(pm)
            if pm.isNull():
                self.image.setText(ch.diff())
            self.viewer.setCurrentIndex(1)
        else:
            self.diff.setPlainText(ch.diff())
            self.viewer.setCurrentIndex(0)

    def commit_message(self) -> str:
        return self.message.toPlainText().strip() + "\n"


# ---------------------------------------------------------------------- result
class PublishedDialog(QDialog):
    """Show the commit / PR and follow the Cloudflare Pages build for it."""

    def __init__(self, parent, client: GitHubClient, result: pg.PublishResult, site_url: str):
        super().__init__(parent)
        self.setWindowTitle("GitHub に反映しました")
        self.setMinimumWidth(640)
        self.client = client
        self.result = result
        self._polls = 0
        lines = [f"コミット: {_link(result.commit_url, result.commit_sha[:7])}（{result.branch}）"]
        if result.pr_url:
            lines.append(f"プルリクエスト: {_link(result.pr_url)}")
        lines += [f"確認: {n}" for n in result.verified]
        lines.append(f"サイト: {_link(site_url)}")
        info = QLabel("<br>".join(lines))
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setOpenExternalLinks(True)
        info.setWordWrap(True)
        self.deploy = QLabel("Cloudflare Pages のビルドを確認しています…")
        self.deploy.setTextFormat(Qt.TextFormat.RichText)
        self.deploy.setOpenExternalLinks(True)
        self.deploy.setWordWrap(True)
        box = QGroupBox("デプロイ状況（Cloudflare Pages）")
        bl = QVBoxLayout(box)
        bl.addWidget(self.deploy)
        close = QPushButton("閉じる")
        close.clicked.connect(self.accept)
        lay = QVBoxLayout(self)
        lay.addWidget(info)
        lay.addWidget(box)
        lay.addWidget(_hint("ビルドは数分かかります。この画面を閉じてもデプロイは続きます。"
                            "プルリクエスト方式の場合は、マージ後に反映先ブランチがビルドされます。"))
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(15000)
        QTimer.singleShot(3000, self._poll)

    def _poll(self):
        self._polls += 1
        if self._polls > 60:
            self.timer.stop()
            return
        run_async(pg.deploy_status, self.client, self.result.commit_sha, on_done=self._render,
                  on_error=lambda m: self.deploy.setText(
                      "デプロイ状況を取得できません（トークンに Checks: Read-only を付けると表示できます）。"
                      "Cloudflare ダッシュボードの Workers & Pages で確認してください。<br>" + m))

    def _render(self, st: pg.DeployStatus):
        labels = {"none": "ビルドの開始を待っています…", "queued": "ビルド待ち…", "building": "ビルド中…",
                  "success": "✔ デプロイが完了しました", "failure": "✖ デプロイに失敗しました"}
        parts = [labels.get(st.state, st.state) + (f"（{st.title}）" if st.title else "")]
        if st.branch_url:
            parts.append("ブランチの URL: " + _link(st.branch_url))
        if st.preview_url:
            parts.append("このデプロイの URL: " + _link(st.preview_url))
        if st.details_url:
            parts.append(_link(st.details_url, "Cloudflare のビルドログ"))
        self.deploy.setText("<br>".join(parts))
        if st.done:
            self.timer.stop()


# ---------------------------------------------------------------------- main dialog
class PortfolioDialog(QDialog):
    """Register uploaded MVs/BGM in the portfolio: directly on GitHub, or as a local bundle."""

    COLS = ["登録", "種別", "ID", "slug", "タイトル", "状態", "掲載日", "サムネ位置(秒)", "オブジェクトキー", "備考"]
    C_INC, C_KIND, C_ID, C_SLUG, C_TITLE, C_STATUS, C_DATE, C_TIME, C_KEY, C_NOTE = range(10)

    def __init__(self, parent, candidates: list[portfolio.Candidate], config: AppConfig, history,
                 ffmpeg: str | None, public_url_for, token_store: GitHubTokenStore):
        super().__init__(parent)
        self.setWindowTitle("ポートフォリオ（Infinite Archive）への登録")
        self.resize(1220, 640)
        self.cands = candidates
        self.config = config
        self.history = history
        self.ffmpeg = ffmpeg
        self.public_url_for = public_url_for
        self.token_store = token_store
        self.data: portfolio.PortfolioData | None = None
        self.snap: pg.RemoteSnapshot | None = None
        self.output_path: Path | None = None
        self.published: pg.PublishResult | None = None
        self._filling = False
        self._tmp = tempfile.TemporaryDirectory(prefix="jmu-portfolio-")
        self._fetch_seq = 0
        self._default_branch = ""

        # --- source selector
        self.rb_github = QRadioButton("GitHub に直接登録（ローカルのリポジトリ不要）")
        self.rb_local = QRadioButton("ローカルのリポジトリ / フォルダに出力")
        group = QButtonGroup(self)
        group.addButton(self.rb_github)
        group.addButton(self.rb_local)
        (self.rb_local if config.portfolio_source == "local" else self.rb_github).setChecked(True)
        self.rb_github.toggled.connect(self._on_source_changed)
        src_row = QHBoxLayout()
        src_row.addWidget(self.rb_github)
        src_row.addWidget(self.rb_local)
        src_row.addStretch(1)

        # --- GitHub panel
        gh = QWidget()
        gl = QHBoxLayout(gh)
        gl.setContentsMargins(0, 0, 0, 0)
        self.repo_lbl = QLabel(config.github_repo)
        self.branch = QComboBox()
        self.branch.setMinimumWidth(220)
        self.branch.activated.connect(lambda _i: self._fetch())
        refresh = QPushButton("最新データを取得")
        refresh.clicked.connect(self._fetch)
        self.token_btn = QPushButton("トークン…")
        self.token_btn.clicked.connect(self._edit_token)
        gl.addWidget(QLabel("リポジトリ"))
        gl.addWidget(self.repo_lbl)
        gl.addSpacing(12)
        gl.addWidget(QLabel("反映先ブランチ"))
        gl.addWidget(self.branch)
        gl.addWidget(refresh)
        gl.addStretch(1)
        gl.addWidget(self.token_btn)

        # --- local panel
        lc = QWidget()
        ll = QHBoxLayout(lc)
        ll.setContentsMargins(0, 0, 0, 0)
        self.pf_edit = QLineEdit(config.portfolio_dir)
        self.pf_edit.setPlaceholderText("Jinn-Portfolio リポジトリのフォルダ（data/works.json があるところ）")
        self.pf_edit.editingFinished.connect(lambda: self._load_local(self.pf_edit.text()))
        pf_browse = QPushButton("参照…")
        pf_browse.clicked.connect(self._browse_portfolio)
        ll.addWidget(QLabel("フォルダ"))
        ll.addWidget(self.pf_edit, 1)
        ll.addWidget(pf_browse)
        self.src_stack = QStackedWidget()
        self.src_stack.addWidget(gh)
        self.src_stack.addWidget(lc)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.RichText)
        self.status.setOpenExternalLinks(True)

        # --- table
        self.table = QTableWidget(len(candidates), len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(self.C_NOTE, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)

        # --- bottom: GitHub mode / local output
        gb = QWidget()
        gbl = QHBoxLayout(gb)
        gbl.setContentsMargins(0, 0, 0, 0)
        self.rb_commit = QRadioButton("反映先ブランチに直接コミット")
        self.rb_pr = QRadioButton("新しいブランチを作り、プルリクエストで反映")
        mg = QButtonGroup(self)
        mg.addButton(self.rb_commit)
        mg.addButton(self.rb_pr)
        (self.rb_pr if config.github_mode == "pr" else self.rb_commit).setChecked(True)
        self.rb_commit.toggled.connect(self._update_site_hint)
        gbl.addWidget(QLabel("反映方法"))
        gbl.addWidget(self.rb_commit)
        gbl.addWidget(self.rb_pr)
        gbl.addStretch(1)
        lb = QWidget()
        lbl = QHBoxLayout(lb)
        lbl.setContentsMargins(0, 0, 0, 0)
        self.dir_edit = QLineEdit(str(config.export_path()))
        browse = QPushButton("参照…")
        browse.clicked.connect(self._browse_out)
        lbl.addWidget(QLabel("出力先"))
        lbl.addWidget(self.dir_edit, 1)
        lbl.addWidget(browse)
        self.bottom_stack = QStackedWidget()
        self.bottom_stack.addWidget(gb)
        self.bottom_stack.addWidget(lb)
        self.bottom_stack.setMaximumHeight(44)

        buttons = QDialogButtonBox()
        self.go_btn = buttons.addButton("確認して GitHub へ反映…", QDialogButtonBox.ButtonRole.ActionRole)
        self.go_btn.setObjectName("primary")
        self.go_btn.clicked.connect(self._go)
        buttons.addButton("閉じる", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(src_row)
        lay.addWidget(self.src_stack)
        lay.addWidget(self.status)
        lay.addWidget(_hint(
            "既存の作品・BGM の記述は変更せず、新しい項目を末尾に追加します。作品 ID・slug・BGM の id は既存データと"
            "過去の出力の両方と重ならない値を自動で割り当てます。解説・歌詞・ジャンルなど未提供の項目は null / [] のままです。"))
        lay.addWidget(self.table, 1)
        lay.addWidget(self.bottom_stack)
        lay.addWidget(buttons)
        self._on_source_changed()

    # ------------------------------------------------------------------ helpers
    @property
    def github_mode(self) -> bool:
        return self.rb_github.isChecked()

    def _set_status(self, html: str, ok: bool | None):
        color = MUTED if ok is None else (OK_COLOR if ok else ERR_COLOR)
        mark = "" if ok is None else ("✔ " if ok else "✖ ")
        self.status.setText(f'<span style="color:{color}">{mark}{html}</span>')
        self.go_btn.setEnabled(bool(ok))

    def _client(self) -> GitHubClient | None:
        try:
            token = self.token_store.load()
        except CredentialError:
            token = None
        if not token:
            return None
        return GitHubClient(token, self.config.github_repo, api=self.config.github_api)

    def _site_url(self, branch: str) -> str:
        return pg.pages_branch_url(self.config.pages_project, branch, self._default_branch or "main")

    def _update_site_hint(self):
        if not (self.github_mode and self.snap):
            return
        branch = self.snap.branch
        kind = "本番" if branch == (self._default_branch or "main") else "プレビュー"
        how = "コミット後に自動でビルド" if self.rb_commit.isChecked() else "プルリクエストのマージ後にビルド（PR 用ブランチのプレビューも作成）"
        self._set_status(
            f"最新データ: {self.snap.label()} — {self.snap.data.summary()}<br>"
            f"反映先: {branch}（Cloudflare Pages {kind}: {_link(self._site_url(branch))}・{how}）", True)

    # ------------------------------------------------------------------ source switching
    def _on_source_changed(self):
        gh = self.github_mode
        self.config.portfolio_source = "github" if gh else "local"
        self.src_stack.setCurrentIndex(0 if gh else 1)
        self.bottom_stack.setCurrentIndex(0 if gh else 1)
        self.go_btn.setText("確認して GitHub へ反映…" if gh else "登録データを出力")
        self.data = None
        self.snap = None
        if gh:
            self._start_github()
        elif self.config.portfolio_dir:
            self._load_local(self.config.portfolio_dir)
        else:
            self._set_status("Jinn-Portfolio のフォルダを指定してください。", False)
            self._fill()

    def _start_github(self):
        client = self._client()
        if client is None:
            self._set_status("GitHub トークンが未設定です。［トークン…］から登録してください（Windows 資格情報マネージャーに保存されます）。", False)
            self._fill()
            return
        self._set_status(f"{self.config.github_repo} のブランチを確認しています…", None)

        def work():
            info = client.get_repo()
            return info.get("default_branch") or "main", client.branches()

        def ok(res):
            default, branches = res
            self._default_branch = default
            self.branch.blockSignals(True)
            self.branch.clear()
            for b in branches:
                self.branch.addItem(b + ("（既定・本番）" if b == default else ""), b)
            want = self.config.github_branch or default
            self.branch.setCurrentIndex(max(0, self.branch.findData(want)))
            self.branch.blockSignals(False)
            self._fetch()

        run_async(work, on_done=ok, on_error=lambda m: (self._set_status(f"GitHub に接続できません: {m}", False), self._fill()))

    def _fetch(self):
        client = self._client()
        branch = self.branch.currentData()
        if client is None or not branch:
            return
        self._fetch_seq += 1
        seq = self._fetch_seq
        self.snap = None
        self.data = None
        self._set_status(f"{self.config.github_repo}@{branch} の最新データを取得しています…", None)
        prefix = self.config.thumb_prefix

        def ok(snap):
            if seq != self._fetch_seq:
                return  # a newer fetch superseded this one
            self.snap = snap
            self.data = snap.data
            self.config.github_branch = snap.branch
            self._plan()
            self._update_site_hint()

        def fail(msg):
            if seq == self._fetch_seq:
                self._set_status(f"最新データを取得できません: {msg}", False)
                self._fill()

        run_async(pg.fetch_snapshot, client, branch, prefix, on_done=ok, on_error=fail)

    def _edit_token(self):
        dlg = GitHubTokenDialog(self, self.token_store, self.config.github_repo, self.config.github_api)
        if dlg.exec() and dlg.saved and self.github_mode:
            self._start_github()

    def _browse_portfolio(self):
        path = QFileDialog.getExistingDirectory(self, "Jinn-Portfolio のフォルダを選択", self.pf_edit.text())
        if path:
            self.pf_edit.setText(path)
            self._load_local(path)

    def _load_local(self, path: str):
        path = path.strip()
        if not path or self.github_mode:
            return
        try:
            self.data = portfolio.PortfolioData.load(path, self.config.thumb_prefix)
        except portfolio.PortfolioError as exc:
            self.data = None
            self._set_status(str(exc), False)
            self._fill()
            return
        self.config.portfolio_dir = str(self.data.root)
        self._set_status(f"既存データ: {self.data.summary()}（{self.data.root}）", True)
        self._plan()

    def _plan(self):
        issued = {**self.history.issued_ids("work"), **self.history.issued_ids("track")}
        portfolio.plan(self.cands, self.data, issued)
        self._fill()

    # ------------------------------------------------------------------ table
    def _fill(self):
        self._filling = True
        ro = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        ready = self.data is not None
        for row, c in enumerate(self.cands):
            is_work = c.kind == "work"
            open_ = ready and not c.locked
            inc = QTableWidgetItem()
            inc.setFlags(ro | (Qt.ItemFlag.ItemIsUserCheckable if open_ else Qt.ItemFlag.NoItemFlags))
            inc.setCheckState(Qt.CheckState.Checked if c.include and ready else Qt.CheckState.Unchecked)
            self.table.setItem(row, self.C_INC, inc)
            values = {
                self.C_KIND: ("MV" if is_work else "BGM", False),
                self.C_ID: (c.id if ready else "", open_),
                self.C_SLUG: ((c.slug if ready else "") if is_work else "—", is_work and open_),
                self.C_TITLE: (c.title, is_work and open_),
                self.C_DATE: (c.published_date if is_work and not c.locked else "—", is_work and open_),
                self.C_TIME: (f"{c.thumb_time:g}" if is_work and not c.locked else "—", is_work and open_),
                self.C_KEY: (c.key, False),
                self.C_NOTE: (c.note if ready else "", False),
            }
            for col, (text, editable) in values.items():
                item = QTableWidgetItem(text)
                item.setFlags(ro | (Qt.ItemFlag.ItemIsEditable if editable else Qt.ItemFlag.NoItemFlags))
                self.table.setItem(row, col, item)
            if is_work and open_:
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
                    continue
                if c.duration and not (0 <= c.thumb_time < c.duration):
                    errors.append(f"{c.id}: サムネ位置が動画の長さ（{c.duration:g} 秒）の範囲外です")
                if self.data and f"{c.slug}.webp" in self.data.existing_thumbnails:
                    errors.append(f"{c.id}: public/{self.config.thumb_prefix}{c.slug}.webp はすでに存在します（slug を変えてください）")
        return errors

    def _thumbnail_files(self) -> tuple[dict[str, Path], list[str]]:
        files: dict[str, Path] = {}
        errors: list[str] = []
        prefix = self.config.thumb_prefix
        work_dir = Path(self._tmp.name) / datetime.now().strftime("%H%M%S%f")
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

    def _prepare(self) -> tuple[portfolio.Registration, dict[str, Path]] | None:
        if self.data is None:
            QMessageBox.warning(self, "登録先", "登録先のデータを読み込めていません。")
            return None
        errors = self._collect()
        if not any(c.include for c in self.cands):
            errors.append("登録する項目がありません")
        reg = portfolio.build(self.data, self.cands, self.config.thumb_prefix, self.config.archive_artist)
        errors += reg.problems
        if errors:
            QMessageBox.warning(self, "確認してください", "\n".join(errors))
            return None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            thumbs, t_errors = self._thumbnail_files()
        finally:
            QApplication.restoreOverrideCursor()
        if t_errors:
            QMessageBox.warning(self, "サムネイル", "\n".join(t_errors))
            return None
        return reg, thumbs

    def _record_issued(self, reg: portfolio.Registration):
        self.history.record_issued("work", [(w["id"], w["videoKey"]) for w in reg.new_works])
        self.history.record_issued("track", [(t["id"], t["key"]) for t in reg.new_tracks])

    # ------------------------------------------------------------------ actions
    def _go(self):
        if self.github_mode:
            self._go_github()
        else:
            self._go_local()

    def _go_local(self):
        prepared = self._prepare()
        if not prepared:
            return
        reg, thumbs = prepared
        out_dir = Path(self.dir_edit.text().strip() or self.config.export_path())
        try:
            self.output_path = portfolio.write_bundle(reg, out_dir, thumbs)
        except (OSError, portfolio.PortfolioError) as exc:
            QMessageBox.critical(self, "出力できません", str(exc))
            return
        self._record_issued(reg)
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

    def _go_github(self):
        client = self._client()
        if client is None or self.snap is None:
            QMessageBox.warning(self, "GitHub", "最新データを取得してから反映してください。")
            return
        prepared = self._prepare()
        if not prepared:
            return
        reg, thumbs = prepared
        try:
            changes = pg.change_set(self.snap.data, reg, thumbs)
        except portfolio.PortfolioError as exc:
            QMessageBox.warning(self, "確認してください", str(exc))
            return
        mode = "commit" if self.rb_commit.isChecked() else "pr"
        self.config.github_mode = mode
        ids = "-".join(w["id"] for w in reg.new_works) or "audio"
        pr_branch = f"register/{ids}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        site = self._site_url(self.snap.branch)
        review = ReviewDialog(self, self.snap, changes, reg, mode, pr_branch, site)
        if not review.exec():
            return
        message = review.commit_message()
        snap = self.snap
        busy = QMessageBox(self)
        busy.setWindowTitle("GitHub へ反映しています")
        busy.setText("送信しています…")
        busy.setStandardButtons(QMessageBox.StandardButton.NoButton)
        busy.show()
        progress_lines: list[str] = []

        def on_progress(msg):  # called from the worker thread: only store, GUI reads via timer
            progress_lines.append(msg)

        timer = QTimer(self)
        timer.timeout.connect(lambda: busy.setText(progress_lines[-1] if progress_lines else "送信しています…"))
        timer.start(200)

        def done(result: pg.PublishResult):
            timer.stop()
            busy.done(0)
            self.published = result
            self._record_issued(reg)
            PublishedDialog(self, client, result, site).exec()
            self.accept()

        def failed(msg: str):
            timer.stop()
            busy.done(0)
            QMessageBox.warning(self, "反映できませんでした", msg + "\n\n最新データを取得し直します。")
            self._fetch()

        run_async(pg.publish, client, snap, changes, message, mode, pr_branch, progress=on_progress,
                  on_done=done, on_error=failed)

    def done(self, r):  # noqa: D401 - QDialog API
        try:
            self._tmp.cleanup()
        except OSError:
            pass
        super().done(r)
