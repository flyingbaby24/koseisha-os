"""In-process stand-in for the parts of the GitHub REST API the uploader uses.

Used by the test suite and by ``--selftest`` so the GitHub registration path (the real
HTTP client included) can be exercised without touching the real repository. It
implements Git Data semantics that matter for safety: refs only fast-forward unless
forced, branch creation fails if the branch exists, and authentication is required.
"""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse


def _sha(kind: str, data: bytes) -> str:
    return hashlib.sha1(kind.encode() + b"\0" + data).hexdigest()


class FakeGitHubRepo:
    def __init__(self, full_name: str, token: str, files: dict[str, bytes], branch: str = "main",
                 extra_branches: tuple[str, ...] = ()):
        self.full_name = full_name
        self.token = token
        self.default_branch = branch
        self.blobs: dict[str, bytes] = {}
        self.trees: dict[str, dict[str, str]] = {}
        self.commits: dict[str, dict] = {}
        self.refs: dict[str, str] = {}
        self.pulls: list[dict] = []
        self.check_runs: dict[str, list[dict]] = {}
        self.requests: list[tuple[str, str]] = []
        self.before_ref_update = None  # hook(branch) — e.g. simulate a concurrent push
        self.lock = threading.Lock()
        root = self.commit_files(files, [], "Initial")
        self.refs[branch] = root
        for b in extra_branches:
            self.refs[b] = root

    # ------------------------------------------------------------------ model
    def put_blob(self, data: bytes) -> str:
        sha = _sha("blob", data)
        self.blobs[sha] = data
        return sha

    def put_tree(self, mapping: dict[str, str]) -> str:
        sha = _sha("tree", json.dumps(sorted(mapping.items())).encode())
        self.trees[sha] = dict(mapping)
        return sha

    def put_commit(self, tree: str, parents: list[str], message: str) -> str:
        date = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        sha = _sha("commit", json.dumps([tree, parents, message, date, len(self.commits)]).encode())
        self.commits[sha] = {"tree": tree, "parents": list(parents), "message": message, "date": date}
        return sha

    def commit_files(self, files: dict[str, bytes], parents: list[str], message: str, base_tree: str | None = None) -> str:
        mapping = dict(self.trees[base_tree]) if base_tree else {}
        for path, data in files.items():
            mapping[path] = self.put_blob(data)
        return self.put_commit(self.put_tree(mapping), parents, message)

    def files_at(self, ref: str) -> dict[str, bytes]:
        sha = self.refs.get(ref, ref)
        tree = self.trees[self.commits[sha]["tree"]]
        return {p: self.blobs[b] for p, b in tree.items()}

    def push(self, branch: str, files: dict[str, bytes], message: str = "someone else's push") -> str:
        """Simulate a commit made elsewhere (e.g. from the cloud development session)."""
        head = self.refs[branch]
        sha = self.commit_files(files, [head], message, base_tree=self.commits[head]["tree"])
        self.refs[branch] = sha
        return sha

    def _ancestors(self, sha: str) -> set[str]:
        seen, todo = set(), [sha]
        while todo:
            s = todo.pop()
            if s in seen or s not in self.commits:
                continue
            seen.add(s)
            todo += self.commits[s]["parents"]
        return seen

    # ------------------------------------------------------------------ HTTP
    def handle(self, method: str, path: str, query: dict, headers: dict, body: bytes) -> tuple[int, bytes, str]:
        with self.lock:
            self.requests.append((method, path))
            if headers.get("authorization") != f"Bearer {self.token}":
                return self._json(401, {"message": "Bad credentials"})
            prefix = f"/repos/{self.full_name}"
            if path == "/user":
                return self._json(200, {"login": "fake-user"})
            if not path.startswith(prefix):
                return self._json(404, {"message": "Not Found"})
            rest = path[len(prefix):]
            data = json.loads(body.decode() or "null") if body else None
            try:
                return self._route(method, rest, query, headers, data)
            except KeyError:
                return self._json(404, {"message": "Not Found"})

    def _route(self, method, rest, query, headers, data):
        if method == "GET" and rest == "":
            return self._json(200, {"full_name": self.full_name, "default_branch": self.default_branch, "private": True})
        if method == "GET" and rest == "/branches":
            names = sorted(self.refs)
            page, per = int(query.get("page", ["1"])[0]), int(query.get("per_page", ["30"])[0])
            return self._json(200, [{"name": n} for n in names[(page - 1) * per: page * per]])
        if method == "GET" and rest.startswith("/git/ref/heads/"):
            return self._json(200, {"object": {"sha": self.refs[unquote(rest[len("/git/ref/heads/"):])]}})
        if method == "GET" and rest.startswith("/git/commits/"):
            c = self.commits[rest[len("/git/commits/"):]]
            return self._json(200, {"sha": rest.split("/")[-1], "tree": {"sha": c["tree"]}, "message": c["message"],
                                    "committer": {"date": c["date"]}, "parents": [{"sha": p} for p in c["parents"]]})
        if method == "GET" and rest.startswith("/contents/"):
            path = unquote(rest[len("/contents/"):])
            files = self.files_at(query.get("ref", [self.default_branch])[0])
            if path in files:
                if "raw" in headers.get("accept", ""):
                    return 200, files[path], "application/octet-stream"
                return self._json(200, {"name": path.rsplit("/", 1)[-1], "path": path, "type": "file"})
            children = sorted({p[len(path) + 1:].split("/", 1)[0] for p in files if p.startswith(path + "/")})
            if children:
                return self._json(200, [{"name": n, "path": f"{path}/{n}"} for n in children])
            return self._json(404, {"message": "Not Found"})
        if method == "GET" and rest.startswith("/commits/") and rest.endswith("/check-runs"):
            return self._json(200, {"check_runs": self.check_runs.get(rest.split("/")[2], [])})
        if method == "POST" and rest == "/git/blobs":
            return self._json(201, {"sha": self.put_blob(base64.b64decode(data["content"]))})
        if method == "POST" and rest == "/git/trees":
            mapping = dict(self.trees[data["base_tree"]])
            for e in data["tree"]:
                if e["sha"] not in self.blobs:
                    return self._json(422, {"message": "unknown blob"})
                mapping[e["path"]] = e["sha"]
            return self._json(201, {"sha": self.put_tree(mapping)})
        if method == "POST" and rest == "/git/commits":
            sha = self.put_commit(data["tree"], data["parents"], data["message"])
            return self._json(201, {"sha": sha, "html_url": f"https://github.com/{self.full_name}/commit/{sha}"})
        if method == "PATCH" and rest.startswith("/git/refs/heads/"):
            branch = unquote(rest[len("/git/refs/heads/"):])
            if self.before_ref_update:
                hook, self.before_ref_update = self.before_ref_update, None
                self.lock.release()
                try:
                    hook(branch)
                finally:
                    self.lock.acquire()
            current = self.refs[branch]
            if not data.get("force") and current not in self._ancestors(data["sha"]):
                return self._json(422, {"message": "Update is not a fast forward"})
            self.refs[branch] = data["sha"]
            return self._json(200, {"object": {"sha": data["sha"]}})
        if method == "POST" and rest == "/git/refs":
            name = data["ref"][len("refs/heads/"):]
            if name in self.refs:
                return self._json(422, {"message": "Reference already exists"})
            self.refs[name] = data["sha"]
            return self._json(201, {"ref": data["ref"]})
        if method == "POST" and rest == "/pulls":
            n = len(self.pulls) + 1
            pr = {**data, "number": n, "html_url": f"https://github.com/{self.full_name}/pull/{n}"}
            self.pulls.append(pr)
            return self._json(201, pr)
        return self._json(404, {"message": "Not Found"})

    @staticmethod
    def _json(status: int, obj) -> tuple[int, bytes, str]:
        return status, json.dumps(obj).encode(), "application/json"


class FakeGitHubServer:
    """Serve a FakeGitHubRepo on 127.0.0.1 (context manager). ``api`` is the base URL."""

    def __init__(self, repo: FakeGitHubRepo):
        self.repo = repo
        fake = repo

        class Handler(BaseHTTPRequestHandler):
            def _do(self):
                u = urlparse(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                status, out, ctype = fake.handle(self.command, u.path, parse_qs(u.query),
                                                 {k.lower(): v for k, v in self.headers.items()}, body)
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            do_GET = do_POST = do_PATCH = _do

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.api = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self) -> "FakeGitHubServer":
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
