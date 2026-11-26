"""Register works directly in the Jinn-Portfolio repository on GitHub.

Flow: fetch the branch's latest data → plan IDs/slugs against it → build the change set
(JSON files + thumbnails) and show it → one commit with all files → fast-forward the
branch (or open a pull request). Cloudflare Pages builds every push automatically:
the production branch deploys the site, other branches get a preview URL.
"""

from __future__ import annotations

import difflib
import html
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .github_client import GitHubClient, GitHubConflict, GitHubError
from .portfolio import DATA_FILES, PortfolioData, PortfolioError, Registration, dump_json

PAGES_APP_SLUG = "cloudflare-workers-and-pages"


@dataclass
class RemoteSnapshot:
    repo: str
    branch: str
    commit_sha: str
    commit_date: str
    commit_message: str
    data: PortfolioData
    default_branch: str = ""

    @property
    def short(self) -> str:
        return self.commit_sha[:7]

    def label(self) -> str:
        return f"{self.repo}@{self.branch}（{self.short}・{self.commit_date[:16].replace('T', ' ')}）"


def fetch_snapshot(client: GitHubClient, branch: str, thumb_prefix: str = "thumbnails/") -> RemoteSnapshot:
    """Read the branch's current data files (always the latest commit, never a cache)."""
    sha = client.branch_head(branch)
    commit = client.git_commit(sha)
    texts = {name: client.file_text(f"data/{name}", sha) for name in DATA_FILES}
    if texts.get("works.json") is None:
        raise PortfolioError(f"{client.repo}@{branch} に data/works.json がありません")
    thumbs = client.list_dir("public/" + thumb_prefix.strip("/"), sha)
    data = PortfolioData.from_texts(texts, f"{client.repo}@{branch} ({sha[:7]})", existing_thumbnails=set(thumbs))
    when = (commit.get("committer") or {}).get("date") or (commit.get("author") or {}).get("date") or ""
    return RemoteSnapshot(client.repo, branch, sha, when, (commit.get("message") or "").splitlines()[0] if commit.get("message") else "", data)


# ---------------------------------------------------------------------- change set
@dataclass
class FileChange:
    path: str
    new: bytes
    old_text: str | None = None  # None → new file
    binary: bool = False
    reformatted: bool = False  # existing file's layout differs from the uploader's JSON layout

    @property
    def kind(self) -> str:
        return "追加" if self.old_text is None else "変更"

    def diff(self) -> str:
        if self.binary:
            return f"（画像 {len(self.new):,} バイト）"
        old = (self.old_text or "").splitlines(keepends=True)
        new = self.new.decode("utf-8").splitlines(keepends=True)
        return "".join(difflib.unified_diff(old, new, f"a/{self.path}", f"b/{self.path}", n=3))

    def added_lines(self) -> int:
        if self.binary:
            return 0
        return sum(1 for line in self.diff().splitlines() if line.startswith("+") and not line.startswith("+++"))

    def removed_lines(self) -> int:
        if self.binary:
            return 0
        return sum(1 for line in self.diff().splitlines() if line.startswith("-") and not line.startswith("---"))


def change_set(data: PortfolioData, reg: Registration, thumbnails: dict[str, Path]) -> list[FileChange]:
    """Files to write; unchanged files are left out."""
    if reg.problems:
        raise PortfolioError("検証エラーがあるため反映できません:\n- " + "\n- ".join(reg.problems))
    changes: list[FileChange] = []
    for name, doc in (("works.json", reg.works_doc), ("soundscape.json", reg.soundscape_doc),
                      ("thumbnail-sources.json", reg.thumbnail_sources)):
        old = data.raw_texts.get(name)
        new_text = dump_json(doc)
        if old is None and name == "soundscape.json" and not reg.new_tracks:
            continue
        if old == new_text:
            continue
        reformatted = old is not None and dump_json(json.loads(old)) != old
        changes.append(FileChange(f"data/{name}", new_text.encode("utf-8"), old, False, reformatted))
    for key, src in sorted(thumbnails.items()):
        changes.append(FileChange(f"public/{key}", Path(src).read_bytes(), None, True))
    return changes


def default_message(reg: Registration) -> str:
    parts = [f"{w['id']} {w['title'] if isinstance(w['title'], str) else w['slug']}" for w in reg.new_works]
    parts += [f"soundscape track {t['id']}" for t in reg.new_tracks]
    head = "Add " + ", ".join(parts) if parts else "Update registration data"
    if len(head) > 72:
        head = f"Add {len(reg.new_works)} work(s) and {len(reg.new_tracks)} soundscape track(s)"
    body = ["", "Registered with Jinn Media Uploader."]
    for w in reg.new_works:
        body.append(f"- {w['id']} {w['slug']}: {w['videoKey']} ({w['status']})")
    for t in reg.new_tracks:
        body.append(f"- {t['id']}: {t['key']}")
    return "\n".join([head, *body]) + "\n"


# ---------------------------------------------------------------------- publish
@dataclass
class PublishResult:
    commit_sha: str
    commit_url: str
    branch: str
    pr_url: str | None = None
    verified: list[str] = field(default_factory=list)


def publish(client: GitHubClient, snap: RemoteSnapshot, changes: list[FileChange], message: str,
            mode: str = "commit", pr_branch: str | None = None, progress=None) -> PublishResult:
    """Create one commit on top of the snapshot and fast-forward the branch (or open a PR).

    Refuses (GitHubConflict) if the branch moved since the snapshot or a new file's
    path already exists — the caller must fetch the latest data and re-check.
    """
    say = progress or (lambda _msg: None)
    if not changes:
        raise PortfolioError("反映する変更がありません")
    say("ブランチの最新状態を確認しています…")
    head = client.branch_head(snap.branch)
    if head != snap.commit_sha:
        raise GitHubConflict(409, f"{snap.branch} が更新されています（{snap.short} → {head[:7]}）。最新データを取得し直してください。")
    for ch in changes:
        if ch.old_text is None and client.path_exists(ch.path, snap.commit_sha):
            raise GitHubConflict(409, f"{ch.path} がすでに存在します。最新データを取得し直してください。")

    base_tree = client.git_commit(snap.commit_sha)["tree"]["sha"]
    files = []
    for i, ch in enumerate(changes, 1):
        say(f"ファイルを送信しています（{i}/{len(changes)}）: {ch.path}")
        files.append((ch.path, client.create_blob(ch.new)))
    say("コミットを作成しています…")
    tree = client.create_tree(base_tree, files)
    commit = client.create_commit(message, tree, [snap.commit_sha])
    sha = commit["sha"]

    pr_url = None
    if mode == "commit":
        say(f"{snap.branch} に反映しています…")
        try:
            client.fast_forward(snap.branch, sha)
        except GitHubConflict as exc:
            raise GitHubConflict(exc.status, f"{snap.branch} が直前に更新されたため反映を中止しました（既存の内容は変更していません）。"
                                             f"最新データを取得し直してください。（{exc.message}）") from exc
        target = snap.branch
    elif mode == "pr":
        if not pr_branch:
            raise ValueError("pr_branch is required")
        say(f"ブランチ {pr_branch} を作成しています…")
        try:
            client.create_branch(pr_branch, sha)
        except GitHubConflict as exc:
            raise GitHubConflict(exc.status, f"ブランチ {pr_branch} を作成できません（同名のブランチがある可能性があります）: {exc.message}") from exc
        first = message.splitlines()[0]
        body = message.split("\n", 1)[1].strip() if "\n" in message else ""
        pr = client.create_pull(first, pr_branch, snap.branch, body)
        pr_url = pr.get("html_url")
        target = pr_branch
    else:
        raise ValueError(mode)

    say("反映結果を確認しています…")
    verified = verify_commit(client, snap, changes, sha)
    url = commit.get("html_url") or f"https://github.com/{client.repo}/commit/{sha}"
    return PublishResult(sha, url, target, pr_url, verified)


def verify_commit(client: GitHubClient, snap: RemoteSnapshot, changes: list[FileChange], sha: str) -> list[str]:
    """Read the new commit back: every changed file as sent, and every existing work kept."""
    notes = []
    for ch in changes:
        if ch.binary:
            continue
        text = client.file_text(ch.path, sha)
        if text is None or text.encode("utf-8") != ch.new:
            raise GitHubError(500, f"反映後の {ch.path} が送信内容と一致しません")
    works_text = client.file_text("data/works.json", sha)
    after = json.loads(works_text)["works"] if works_text else []
    before = snap.data.works
    if after[:len(before)] != before:
        raise GitHubError(500, "反映後の works.json で既存作品が変化しています")
    notes.append(f"既存作品 {len(before)} 件は変更なし、作品は合計 {len(after)} 件")
    return notes


# ---------------------------------------------------------------------- deploy status
@dataclass
class DeployStatus:
    state: str  # "queued" | "building" | "success" | "failure" | "none"
    title: str = ""
    preview_url: str | None = None
    branch_url: str | None = None
    details_url: str | None = None

    @property
    def done(self) -> bool:
        return self.state in ("success", "failure")


def _href_after(label: str, summary: str) -> str | None:
    m = re.search(rf"{re.escape(label)}:</strong>.*?href='([^']+)'", summary, re.S)
    return html.unescape(m.group(1)) if m else None


def parse_pages_check(run: dict) -> DeployStatus:
    out = run.get("output") or {}
    summary = out.get("summary") or ""
    if run.get("status") != "completed":
        state = "queued" if run.get("status") == "queued" else "building"
    else:
        state = "success" if run.get("conclusion") == "success" else "failure"
    return DeployStatus(state, out.get("title") or "", _href_after("Preview URL", summary),
                        _href_after("Branch Preview URL", summary), run.get("details_url"))


def deploy_status(client: GitHubClient, sha: str) -> DeployStatus:
    """Cloudflare Pages reports each build as a check run on the commit."""
    for run in client.check_runs(sha):
        if (run.get("app") or {}).get("slug") == PAGES_APP_SLUG or run.get("name") == "Cloudflare Pages":
            return parse_pages_check(run)
    return DeployStatus("none")


def wait_for_deploy(client: GitHubClient, sha: str, timeout: float = 900, interval: float = 15,
                    on_update=None) -> DeployStatus:
    end = time.monotonic() + timeout
    status = DeployStatus("none")
    while time.monotonic() < end:
        status = deploy_status(client, sha)
        if on_update:
            on_update(status)
        if status.done:
            return status
        time.sleep(interval)
    return status


def pages_branch_url(project: str, branch: str, production_branch: str = "main") -> str:
    """URL Cloudflare Pages serves the branch's latest build on."""
    if branch == production_branch:
        return f"https://{project}.pages.dev"
    alias = re.sub(r"[^a-z0-9]+", "-", branch.lower()).strip("-")[:28].strip("-")
    return f"https://{alias}.{project}.pages.dev"
