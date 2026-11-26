"""Minimal GitHub REST client (stdlib only) for registering works in the portfolio repo.

Writes go through the Git Data API so one registration is one commit containing every
file (JSON + thumbnails), and the branch is only fast-forwarded: if someone pushed in
the meantime the update is refused instead of overwriting their work.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import Callable
from urllib.parse import quote

from . import __version__

API = "https://api.github.com"

# transport(method, url, headers, body) -> (status, body)
Transport = Callable[[str, str, dict, bytes | None], tuple[int, bytes]]


class GitHubError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message

    def __str__(self) -> str:
        hints = {
            401: "トークンが無効か期限切れです",
            403: "権限がありません（トークンの権限・対象リポジトリを確認してください）",
            404: "見つかりません（リポジトリ名・ブランチ名、トークンの対象リポジトリを確認してください）",
        }
        hint = hints.get(self.status)
        return f"{hint}（HTTP {self.status}: {self.message}）" if hint else f"HTTP {self.status}: {self.message}"


class GitHubConflict(GitHubError):
    """The branch moved or a path appeared; nothing was overwritten."""

    def __str__(self) -> str:
        return self.message


def urllib_transport(timeout: float = 60) -> Transport:
    """HTTPS via the system proxy settings; loopback (self-test server) always direct."""
    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def send(method: str, url: str, headers: dict, body: bytes | None) -> tuple[int, bytes]:
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        local = url.startswith(("http://127.0.0.1", "http://localhost"))
        try:
            with (direct.open(req, timeout=timeout) if local else urllib.request.urlopen(req, timeout=timeout)) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
    return send


def _path(p: str) -> str:
    return quote(p, safe="/")


class GitHubClient:
    def __init__(self, token: str | None, repo: str, transport: Transport | None = None, api: str = API):
        if repo.count("/") != 1 or not all(repo.split("/")):
            raise ValueError("リポジトリは owner/name の形式で指定してください")
        self.token = token
        self.repo = repo
        self.api = api.rstrip("/")
        self.transport = transport or urllib_transport()

    def __repr__(self) -> str:
        return f"GitHubClient(repo={self.repo!r}, token=***)"

    # ------------------------------------------------------------------ plumbing
    def request(self, method: str, path: str, body=None, accept: str = "application/vnd.github+json",
                ok: tuple[int, ...] = (200, 201)) -> bytes:
        headers = {
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": f"JinnMediaUploader/{__version__}",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        url = path if path.startswith("http") else f"{self.api}{path}"
        status, raw = self.transport(method, url, headers, data)
        if status in ok:
            return raw
        try:
            message = json.loads(raw.decode("utf-8")).get("message", "")
        except (ValueError, AttributeError):
            message = raw[:200].decode("utf-8", "replace") if raw else ""
        cls = GitHubConflict if status in (409, 422) and method in ("PATCH", "POST") else GitHubError
        raise cls(status, message or "error")

    def json(self, method: str, path: str, body=None, ok: tuple[int, ...] = (200, 201)):
        return json.loads(self.request(method, path, body, ok=ok).decode("utf-8") or "null")

    @property
    def _r(self) -> str:
        return f"/repos/{self.repo}"

    # ------------------------------------------------------------------ reads
    def get_repo(self) -> dict:
        return self.json("GET", self._r)

    def get_user(self) -> dict:
        return self.json("GET", "/user")

    def branches(self) -> list[str]:
        names: list[str] = []
        page = 1
        while True:
            batch = self.json("GET", f"{self._r}/branches?per_page=100&page={page}")
            names += [b["name"] for b in batch]
            if len(batch) < 100:
                return names
            page += 1

    def branch_head(self, branch: str) -> str:
        return self.json("GET", f"{self._r}/git/ref/heads/{_path(branch)}")["object"]["sha"]

    def git_commit(self, sha: str) -> dict:
        return self.json("GET", f"{self._r}/git/commits/{sha}")

    def file_text(self, path: str, ref: str) -> str | None:
        try:
            raw = self.request("GET", f"{self._r}/contents/{_path(path)}?ref={quote(ref, safe='')}",
                               accept="application/vnd.github.raw+json")
        except GitHubError as exc:
            if exc.status == 404:
                return None
            raise
        return raw.decode("utf-8")

    def list_dir(self, path: str, ref: str) -> list[str]:
        try:
            items = self.json("GET", f"{self._r}/contents/{_path(path)}?ref={quote(ref, safe='')}")
        except GitHubError as exc:
            if exc.status == 404:
                return []
            raise
        return [i["name"] for i in items] if isinstance(items, list) else []

    def path_exists(self, path: str, ref: str) -> bool:
        try:
            self.request("GET", f"{self._r}/contents/{_path(path)}?ref={quote(ref, safe='')}")
            return True
        except GitHubError as exc:
            if exc.status == 404:
                return False
            raise

    def check_runs(self, sha: str) -> list[dict]:
        return self.json("GET", f"{self._r}/commits/{sha}/check-runs?per_page=100").get("check_runs", [])

    # ------------------------------------------------------------------ writes
    def create_blob(self, data: bytes) -> str:
        body = {"content": base64.b64encode(data).decode("ascii"), "encoding": "base64"}
        return self.json("POST", f"{self._r}/git/blobs", body)["sha"]

    def create_tree(self, base_tree: str, files: list[tuple[str, str]]) -> str:
        entries = [{"path": p, "mode": "100644", "type": "blob", "sha": s} for p, s in files]
        return self.json("POST", f"{self._r}/git/trees", {"base_tree": base_tree, "tree": entries})["sha"]

    def create_commit(self, message: str, tree: str, parents: list[str]) -> dict:
        return self.json("POST", f"{self._r}/git/commits", {"message": message, "tree": tree, "parents": parents})

    def fast_forward(self, branch: str, sha: str) -> None:
        """Move the branch to *sha* only if that is a fast-forward (never force)."""
        self.json("PATCH", f"{self._r}/git/refs/heads/{_path(branch)}", {"sha": sha, "force": False})

    def create_branch(self, branch: str, sha: str) -> None:
        self.json("POST", f"{self._r}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})

    def create_pull(self, title: str, head: str, base: str, body: str) -> dict:
        return self.json("POST", f"{self._r}/pulls", {"title": title, "head": head, "base": base, "body": body})
