"""GitHub direct registration: fetch latest data, check IDs/slugs, one atomic commit, PR mode."""

import json
from pathlib import Path

import pytest

from jinn_uploader import portfolio
from jinn_uploader import portfolio_github as pg
from jinn_uploader.credentials import CredentialError, GitHubTokenStore, MemoryKeyring, mask_token
from jinn_uploader.github_client import GitHubClient, GitHubConflict, GitHubError
from jinn_uploader.github_fake import FakeGitHubRepo, FakeGitHubServer

FIXTURE = Path(__file__).parent / "fixtures" / "jinn-portfolio"
REPO = "flyingbaby24/Jinn-Portfolio"
TOKEN = "github_pat_test_0123456789"

# Real Cloudflare Pages check-run output (Jinn-Portfolio @ df871f5).
PAGES_RUN = {
    "name": "Cloudflare Pages", "status": "completed", "conclusion": "success",
    "app": {"slug": "cloudflare-workers-and-pages"},
    "details_url": "https://dash.cloudflare.com/?to=/x/pages/view/jinn-portfolio/03d39ff3",
    "output": {"title": "Deployed successfully", "summary": (
        "<table><tr><td><strong>Latest commit:</strong> </td><td>\n<code>df871f5</code>\n</td></tr>\n"
        "<tr><td><strong>Status:</strong></td><td>&nbsp;✅&nbsp; Deploy successful!</td></tr>\n"
        "<tr><td><strong>Preview URL:</strong></td><td>\n<a href='https://03d39ff3.jinn-portfolio.pages.dev'>"
        "https://03d39ff3.jinn-portfolio.pages.dev</a>\n</td></tr>\n<tr><td><strong>Branch Preview URL:</strong></td>"
        "<td>\n<a href='https://phase-3-1-soundscape.jinn-portfolio.pages.dev'>https://phase-3-1-soundscape.jinn-portfolio"
        ".pages.dev</a>\n</td></tr>\n</table>\n\n[View logs](https://dash.cloudflare.com/)\n")},
}


def repo_files(with_soundscape=True) -> dict[str, bytes]:
    files = {f"data/{f.name}": f.read_bytes() for f in (FIXTURE / "data").iterdir()}
    if not with_soundscape:
        files.pop("data/soundscape.json")
    for slug in ("human", "meaning-hollow", "million-consumer", "wrapped-too-beautifully"):
        files[f"public/thumbnails/{slug}.webp"] = b"webp-" + slug.encode()
        files[f"public/thumbnails/{slug}-poster.jpg"] = b"jpg-" + slug.encode()
    files["package.json"] = b'{"name": "jinn-portfolio"}\n'
    files["src/data/schema.mjs"] = b"// site code\n"
    return files


@pytest.fixture
def server():
    fake = FakeGitHubRepo(REPO, TOKEN, repo_files(), branch="main", extra_branches=("phase-3-1-soundscape",))
    with FakeGitHubServer(fake) as srv:
        yield srv


@pytest.fixture
def client(server):
    return GitHubClient(TOKEN, REPO, api=server.api)


def candidates():
    return [
        portfolio.Candidate(kind="work", key="mv/Human (Live).mp4", title="Human", duration=93.4, width=1080, height=1920),
        portfolio.Candidate(kind="work", key="mv/Night Drive.mp4", title="Night Drive", duration=188.0, width=1920, height=1080),
        portfolio.Candidate(kind="work", key="Meaning Hollow.mp4", title="Meaning Hollow", duration=50.3, width=1080, height=1920),
        portfolio.Candidate(kind="track", key="audio/Archive 01.m4a", title="Archive 01"),
    ]


def thumbs(tmp_path, cands, prefix="thumbnails/"):
    out = {}
    for c in cands:
        if c.kind == "work" and c.include:
            for name in (f"{c.slug}.webp", f"{c.slug}-poster.jpg"):
                f = tmp_path / name
                f.write_bytes(f"image {name}".encode())
                out[prefix + name] = f
    return out


def test_token_is_kept_in_the_vault_and_never_shown():
    store = GitHubTokenStore(backend=MemoryKeyring())
    assert store.load() is None
    store.save(" " + TOKEN + " ")
    assert store.load() == TOKEN
    assert TOKEN not in mask_token(TOKEN) and mask_token(TOKEN).startswith("gith")
    assert TOKEN not in repr(GitHubClient(TOKEN, REPO))
    with pytest.raises(CredentialError):
        store.save("has space")
    assert store.delete() and store.load() is None


def test_insecure_vault_refuses_token():
    from keyring.backends.fail import Keyring as FailKeyring

    with pytest.raises(CredentialError):
        GitHubTokenStore(backend=FailKeyring()).save(TOKEN)


def test_auth_and_errors_are_reported(server):
    bad = GitHubClient("wrong", REPO, api=server.api)
    with pytest.raises(GitHubError) as e:
        bad.get_repo()
    assert e.value.status == 401 and "トークン" in str(e.value)
    with pytest.raises(GitHubError) as e:
        GitHubClient(TOKEN, REPO, api=server.api).branch_head("no-such-branch")
    assert e.value.status == 404
    with pytest.raises(ValueError):
        GitHubClient(TOKEN, "no-slash")


def test_fetch_latest_data_and_plan_against_it(client, server):
    assert client.get_repo()["default_branch"] == "main"
    assert set(client.branches()) == {"main", "phase-3-1-soundscape"}
    snap = pg.fetch_snapshot(client, "phase-3-1-soundscape")
    assert snap.commit_sha == server.repo.refs["phase-3-1-soundscape"]
    assert [w["id"] for w in snap.data.works] == ["mv-0001", "mv-0002", "mv-0003", "mv-0004"]
    assert "human.webp" in snap.data.existing_thumbnails
    cands = candidates()
    portfolio.plan(cands, snap.data)
    assert [(c.id, c.slug) for c in cands[:2]] == [("mv-0005", "human-2"), ("mv-0006", "night-drive")]
    assert not cands[2].include and "mv-0002" in cands[2].note
    assert cands[3].id == "archive-01"


def test_slug_whose_thumbnail_file_exists_is_treated_as_taken(client, server):
    server.repo.push("main", {"public/thumbnails/night-drive.webp": b"orphan thumbnail"})
    snap = pg.fetch_snapshot(client, "main")
    c = portfolio.Candidate(kind="work", key="mv/Night Drive.mp4", title="Night Drive", duration=1.0, width=2, height=2)
    portfolio.plan([c], snap.data)
    assert c.slug == "night-drive-2"


def test_direct_commit_keeps_existing_works_and_adds_everything_in_one_commit(client, server, tmp_path):
    before_files = server.repo.files_at("phase-3-1-soundscape")
    snap = pg.fetch_snapshot(client, "phase-3-1-soundscape")
    cands = candidates()
    portfolio.plan(cands, snap.data)
    reg = portfolio.build(snap.data, cands)
    changes = pg.change_set(snap.data, reg, thumbs(tmp_path, cands))
    paths = [c.path for c in changes]
    assert paths == ["data/works.json", "data/soundscape.json", "data/thumbnail-sources.json",
                     "public/thumbnails/human-2-poster.jpg", "public/thumbnails/human-2.webp",
                     "public/thumbnails/night-drive-poster.jpg", "public/thumbnails/night-drive.webp"]
    works_change = changes[0]
    assert works_change.removed_lines() == 0 or works_change.removed_lines() == 1  # only "}" → "}," at most
    assert not any(c.reformatted for c in changes)
    msg = pg.default_message(reg)
    assert msg.startswith("Add mv-0005 Human, mv-0006 Night Drive, soundscape track archive-01")

    result = pg.publish(client, snap, changes, msg, "commit")
    repo = server.repo
    assert repo.refs["phase-3-1-soundscape"] == result.commit_sha
    assert repo.commits[result.commit_sha]["parents"] == [snap.commit_sha]  # exactly one new commit
    assert repo.refs["main"] == snap.commit_sha  # other branches untouched
    after = repo.files_at("phase-3-1-soundscape")
    for path, data in before_files.items():
        if path not in paths:
            assert after[path] == data, path  # every other file unchanged
    works = json.loads(after["data/works.json"])["works"]
    assert works[:4] == snap.data.works and [w["id"] for w in works[4:]] == ["mv-0005", "mv-0006"]
    assert json.loads(after["data/soundscape.json"])["tracks"] == [{"id": "archive-01", "key": "audio/Archive 01.m4a"}]
    assert after["public/thumbnails/human-2.webp"] == b"image human-2.webp"
    assert "既存作品 4 件は変更なし" in result.verified[0]
    assert portfolio.validate_works(works, json.loads(after["data/categories.json"])["categories"]) == []


def test_branch_moved_before_publish_is_refused(client, server, tmp_path):
    snap = pg.fetch_snapshot(client, "main")
    cands = candidates()[:1]
    portfolio.plan(cands, snap.data)
    changes = pg.change_set(snap.data, portfolio.build(snap.data, cands), thumbs(tmp_path, cands))
    other = server.repo.push("main", {"README.md": b"edited in the cloud session"})
    with pytest.raises(GitHubConflict) as e:
        pg.publish(client, snap, changes, "msg", "commit")
    assert "更新されています" in str(e.value)
    assert server.repo.refs["main"] == other  # nothing overwritten
    assert not any(m == "POST" for m, _ in server.repo.requests)  # nothing was even uploaded


def test_concurrent_push_during_publish_is_not_overwritten(client, server, tmp_path):
    snap = pg.fetch_snapshot(client, "main")
    cands = candidates()[:1]
    portfolio.plan(cands, snap.data)
    changes = pg.change_set(snap.data, portfolio.build(snap.data, cands), thumbs(tmp_path, cands))
    pushed = {}
    server.repo.before_ref_update = lambda b: pushed.setdefault("sha", server.repo.push(b, {"x.txt": b"race"}))
    with pytest.raises(GitHubConflict) as e:
        pg.publish(client, snap, changes, "msg", "commit")
    assert "中止" in str(e.value)
    assert server.repo.refs["main"] == pushed["sha"]
    assert json.loads(server.repo.files_at("main")["data/works.json"])["works"] == snap.data.works


def test_pull_request_mode_leaves_the_target_branch_alone(client, server, tmp_path):
    snap = pg.fetch_snapshot(client, "main")
    cands = candidates()
    portfolio.plan(cands, snap.data)
    reg = portfolio.build(snap.data, cands)
    changes = pg.change_set(snap.data, reg, thumbs(tmp_path, cands))
    result = pg.publish(client, snap, changes, pg.default_message(reg), "pr", "register/mv-0005-test")
    assert server.repo.refs["main"] == snap.commit_sha
    assert server.repo.refs["register/mv-0005-test"] == result.commit_sha
    pr = server.repo.pulls[0]
    assert (pr["head"], pr["base"]) == ("register/mv-0005-test", "main")
    assert result.pr_url.endswith("/pull/1")
    with pytest.raises(GitHubConflict):  # same branch name again
        pg.publish(client, snap, changes, "msg", "pr", "register/mv-0005-test")


def test_branch_without_soundscape_skips_bgm(tmp_path):
    fake = FakeGitHubRepo(REPO, TOKEN, repo_files(with_soundscape=False), branch="main")
    with FakeGitHubServer(fake) as srv:
        client = GitHubClient(TOKEN, REPO, api=srv.api)
        snap = pg.fetch_snapshot(client, "main")
        cands = candidates()
        portfolio.plan(cands, snap.data)
        assert not cands[3].include and "soundscape" in cands[3].note
        reg = portfolio.build(snap.data, cands)
        changes = pg.change_set(snap.data, reg, thumbs(tmp_path, cands))
        assert "data/soundscape.json" not in [c.path for c in changes]
        pg.publish(client, snap, changes, "msg")
        assert "data/soundscape.json" not in fake.files_at("main")


def test_new_file_that_appeared_is_not_overwritten(client, server, tmp_path):
    snap = pg.fetch_snapshot(client, "main")
    cands = candidates()[:1]
    portfolio.plan(cands, snap.data)
    changes = pg.change_set(snap.data, portfolio.build(snap.data, cands), thumbs(tmp_path, cands))
    # Same commit, but pretend the thumbnail path exists there (e.g. snapshot taken from a stale listing).
    server.repo.trees[server.repo.commits[snap.commit_sha]["tree"]]["public/thumbnails/human-2.webp"] = \
        server.repo.put_blob(b"existing")
    with pytest.raises(GitHubConflict) as e:
        pg.publish(client, snap, changes, "msg")
    assert "human-2.webp" in str(e.value)


def test_deploy_status_from_cloudflare_pages_check_run(client, server):
    sha = server.repo.refs["main"]
    assert pg.deploy_status(client, sha).state == "none"
    server.repo.check_runs[sha] = [{"name": "Build", "app": {"slug": "github-actions"}, "status": "completed"},
                                   {**PAGES_RUN, "status": "in_progress", "conclusion": None}]
    assert pg.deploy_status(client, sha).state == "building"
    server.repo.check_runs[sha] = [PAGES_RUN]
    st = pg.deploy_status(client, sha)
    assert st.state == "success" and st.done
    assert st.preview_url == "https://03d39ff3.jinn-portfolio.pages.dev"
    assert st.branch_url == "https://phase-3-1-soundscape.jinn-portfolio.pages.dev"


def test_pages_branch_urls():
    assert pg.pages_branch_url("jinn-portfolio", "main") == "https://jinn-portfolio.pages.dev"
    assert pg.pages_branch_url("jinn-portfolio", "phase-3-1-soundscape") == "https://phase-3-1-soundscape.jinn-portfolio.pages.dev"
    assert pg.pages_branch_url("jinn-portfolio", "register/mv-0005") == "https://register-mv-0005.jinn-portfolio.pages.dev"


def test_line_endings_of_existing_files_are_preserved(tmp_path):
    """A repo whose JSON uses CRLF must not be rewritten line by line (and LF stays LF)."""
    files = repo_files()
    for name in ("data/works.json", "data/thumbnail-sources.json"):
        files[name] = files[name].replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    fake = FakeGitHubRepo(REPO, TOKEN, files, branch="main")
    with FakeGitHubServer(fake) as srv:
        client = GitHubClient(TOKEN, REPO, api=srv.api)
        snap = pg.fetch_snapshot(client, "main")
        cands = candidates()
        portfolio.plan(cands, snap.data)
        reg = portfolio.build(snap.data, cands)
        changes = {c.path: c for c in pg.change_set(snap.data, reg, thumbs(tmp_path, cands))}
        works = changes["data/works.json"]
        assert works.removed_lines() <= 1 and not works.reformatted
        assert works.new.count(b"\r\n") == works.new.count(b"\n")  # CRLF kept
        assert b"\r\n" not in changes["data/soundscape.json"].new  # LF file stays LF
        pg.publish(client, snap, list(changes.values()), "msg")
        after = fake.files_at("main")["data/works.json"]
        assert after.startswith(files["data/works.json"][:500])  # existing bytes untouched
        assert after.count(b"\r\n") == after.count(b"\n")


def test_local_bundle_keeps_line_endings(tmp_path):
    import shutil

    root = tmp_path / "pf"
    shutil.copytree(FIXTURE, root)
    w = root / "data" / "works.json"
    w.write_bytes(w.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    data = portfolio.PortfolioData.load(root)
    cands = candidates()[:1]
    portfolio.plan(cands, data)
    bundle = portfolio.write_bundle(portfolio.build(data, cands), tmp_path / "out", {})
    out = (bundle / "data" / "works.json").read_bytes()
    assert out.count(b"\r\n") == out.count(b"\n")
    assert out.startswith(w.read_bytes()[:500])
    sound = (bundle / "data" / "soundscape.json").read_bytes()
    assert b"\r\n" not in sound  # written as bytes: no Windows text-mode translation
