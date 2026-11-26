"""Compatibility with flyingbaby24/Jinn-Portfolio (branch phase-3-1-soundscape) data files."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from jinn_uploader import portfolio
from jinn_uploader.portfolio import Candidate, PortfolioData

HERE = Path(__file__).parent
FIXTURE = HERE / "fixtures" / "jinn-portfolio"
SPEC = HERE / "portfolio_spec"
CATEGORIES = FIXTURE / "data" / "categories.json"


@pytest.fixture
def data():
    return PortfolioData.load(FIXTURE)


def mv(key, title, duration=120.5, width=1920, height=1080, **kw):
    return Candidate(kind="work", key=key, title=title, duration=duration, width=width, height=height, **kw)


def run_js(data_dir: Path) -> dict:
    node = shutil.which("node")
    if not node:
        if os.environ.get("JMU_REQUIRE_NODE"):
            pytest.fail("node is required for the portfolio validator cross-check")
        pytest.skip("node not available")
    out = subprocess.run([node, str(SPEC / "validate.mjs"), str(data_dir), str(CATEGORIES)],
                         capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


def test_existing_files_round_trip_byte_for_byte(data):
    for name, doc in (("works.json", data.works_doc), ("soundscape.json", data.soundscape_doc),
                      ("thumbnail-sources.json", data.thumbnail_sources)):
        assert portfolio.dump_json(doc) == (FIXTURE / "data" / name).read_text(encoding="utf-8"), name


def test_existing_data_summary(data):
    assert [w["id"] for w in data.works] == ["mv-0001", "mv-0002", "mv-0003", "mv-0004"]
    assert data.tracks == []
    assert "作品 4 件" in data.summary()
    assert PortfolioData.load(FIXTURE / "data").root == FIXTURE  # data/ folder also accepted
    with pytest.raises(portfolio.PortfolioError):
        PortfolioData.load(HERE)


def test_entry_has_exactly_the_site_fields_in_file_order(data):
    c = mv("mv/Night Drive.mp4", "Night Drive")
    portfolio.plan([c], data)
    entry = portfolio.work_entry(c, "thumbnails/", "Jinn Project")
    assert list(entry) == list(data.works[0])  # same 23 keys, same order as the real file
    assert entry["thumbnailKey"] == "thumbnails/night-drive.webp"
    assert entry["posterKey"] == "thumbnails/night-drive-poster.jpg"
    for f in ("description", "lyrics", "genre", "createdDate", "language"):
        assert entry[f] is None  # nothing unprovided is filled in
    for f in ("themes", "tags", "productionTools", "relatedArticles", "relatedWorks"):
        assert entry[f] == []


def test_ids_and_slugs_never_collide(data):
    a = mv("mv/Human (Live).mp4", "Human")  # slug "human" is taken by mv-0001
    b = mv("mv/Night Drive.mp4", "Night Drive")
    c = mv("mv/夜明け.mp4", "夜明け")  # no ASCII slug → falls back to the ID
    portfolio.plan([a, b, c], data)
    assert [a.id, b.id, c.id] == ["mv-0005", "mv-0006", "mv-0007"]
    assert [a.slug, b.slug, c.slug] == ["human-2", "night-drive", "mv-0007"]


def test_ids_issued_by_earlier_exports_are_respected(data):
    issued = {"mv/Other.mp4": "mv-0005"}  # exported before, not committed to works.json yet
    a = mv("mv/New.mp4", "New")
    portfolio.plan([a], data, issued)
    assert a.id == "mv-0006"
    again = mv("mv/Other.mp4", "Other")  # re-exporting the same file keeps its ID
    portfolio.plan([again], data, issued)
    assert again.id == "mv-0005"


def test_gaps_and_higher_numbers(tmp_path, data):
    root = tmp_path / "pf"
    shutil.copytree(FIXTURE, root)
    doc = json.loads((root / "data" / "works.json").read_text(encoding="utf-8"))
    doc["works"][3]["id"] = "mv-0042"
    (root / "data" / "works.json").write_text(portfolio.dump_json(doc), encoding="utf-8")
    c = mv("mv/x.mp4", "X")
    portfolio.plan([c], PortfolioData.load(root))
    assert c.id == "mv-0043"


def test_already_registered_video_is_not_registered_twice(data):
    c = mv("Meaning Hollow.mp4", "Meaning Hollow")
    portfolio.plan([c], data)
    assert not c.include and c.id == "mv-0002" and "登録済み" in c.note
    reg = portfolio.build(data, [c])
    assert reg.new_works == [] and len(reg.works_doc["works"]) == 4


def test_missing_measurements_make_a_draft(data):
    c = mv("mv/unknown.mp4", "Unknown", duration=None, width=None, height=None)
    portfolio.plan([c], data)
    assert c.status == "draft"
    assert portfolio.build(data, [c]).problems == []


def test_tracks_for_the_soundscape(data):
    t1 = Candidate(kind="track", key="audio/Archive 01 (v2).m4a", title="Archive 01 (v2)")
    t2 = Candidate(kind="track", key="audio/Archive 01.mp3", title="Archive 01 v2")
    t3 = Candidate(kind="track", key="audio/old.wma", title="old")
    portfolio.plan([t1, t2, t3], data)
    assert (t1.id, t2.id) == ("archive-01-v2", "archive-01-v2-2")
    assert not t3.include and "形式" in t3.note
    reg = portfolio.build(data, [t1, t2, t3])
    assert reg.new_tracks == [{"id": "archive-01-v2", "key": "audio/Archive 01 (v2).m4a"},
                              {"id": "archive-01-v2-2", "key": "audio/Archive 01.mp3"}]
    assert reg.soundscape_doc["placeholder"] == "synth" and reg.soundscape_doc["crossfade"] == 8
    assert reg.problems == []


def test_bundle_mirrors_the_repository(tmp_path, data):
    a = mv("mv/Night Drive.mp4", "Night Drive", width=1080, height=1920, duration=93.4)
    t = Candidate(kind="track", key="audio/Ambient 01.m4a", title="Ambient 01")
    portfolio.plan([a, t], data)
    a.thumb_time = 9.34
    reg = portfolio.build(data, [a, t])
    assert reg.problems == []
    thumb = tmp_path / "t.webp"
    thumb.write_bytes(b"webp")
    poster = tmp_path / "p.jpg"
    poster.write_bytes(b"jpg")
    bundle = portfolio.write_bundle(reg, tmp_path / "out", {a_key: f for a_key, f in (
        ("thumbnails/night-drive.webp", thumb), ("thumbnails/night-drive-poster.jpg", poster))})
    merged = PortfolioData.load(bundle)  # also re-validates
    assert merged.works[:4] == data.works
    assert merged.works[4]["id"] == "mv-0005" and merged.works[4]["status"] == "published"
    assert merged.tracks == [{"id": "ambient-01", "key": "audio/Ambient 01.m4a"}]
    assert merged.thumbnail_sources["night-drive"] == 9.34
    assert merged.thumbnail_sources["human"] == 8.5
    assert (bundle / "public" / "thumbnails" / "night-drive.webp").read_bytes() == b"webp"
    assert (bundle / "public" / "thumbnails" / "night-drive-poster.jpg").is_file()
    new = json.loads((bundle / "new-entries.json").read_text(encoding="utf-8"))
    assert [w["id"] for w in new["works"]] == ["mv-0005"] and new["thumbnailSources"] == {"night-drive": 9.34}
    js = run_js(bundle / "data")  # the site's own validators accept the merged files
    assert js["works"] == [] and js["soundscape"] == []


def test_invalid_export_is_refused(tmp_path, data):
    c = mv("mv/x.mp4", "X")
    portfolio.plan([c], data)
    c.slug = "Bad Slug"
    reg = portfolio.build(data, [c])
    assert reg.problems
    with pytest.raises(portfolio.PortfolioError):
        portfolio.write_bundle(reg, tmp_path, {})


BROKEN_WORKS = [
    {"id": "mv-0001", "slug": "human", "category": "music-videos", "title": "Dup", "status": "published"},
    {"id": "Bad Id", "slug": "Bad Slug", "category": "nope", "title": "", "status": "live", "extra": 1,
     "videoKey": "/abs.mp4", "duration": -1, "width": 1.5, "themes": ["", 2], "publishedDate": "2026/01/01",
     "relatedWorks": ["mv-9999"], "language": "Japanese", "relatedArticles": [{"title": "x", "url": "ftp://x"}]},
    {"id": "mv-0100", "slug": "ok", "category": "music-videos", "title": {"ja": "題", "en": "T"}, "status": "published",
     "videoKey": "a.mp4"},
]
BROKEN_SOUND = {"placeholder": "loud", "crossfade": 40, "tracks": [
    {"id": "a", "key": "audio/a.m4a"}, {"id": "a", "key": "https://x/y.mp3"}, {"id": "B", "key": "audio/c.txt", "gain": 3},
    {"id": "d", "key": "audio/d.mp3", "start": 10, "end": 10.5}]}


def test_python_validators_match_the_site_exactly(tmp_path):
    d = tmp_path / "broken"
    d.mkdir()
    works = json.loads((FIXTURE / "data" / "works.json").read_text(encoding="utf-8"))["works"] + BROKEN_WORKS
    (d / "works.json").write_text(json.dumps({"schemaVersion": 1, "works": works}), encoding="utf-8")
    (d / "soundscape.json").write_text(json.dumps(BROKEN_SOUND), encoding="utf-8")
    categories = json.loads(CATEGORIES.read_text(encoding="utf-8"))["categories"]
    py_works = portfolio.validate_works(works, categories)
    py_sound = portfolio.validate_soundscape(BROKEN_SOUND)
    assert len(py_works) > 10 and len(py_sound) > 5
    js = run_js(d)
    assert py_works == js["works"]
    assert py_sound == js["soundscape"]


def test_public_url_encoding_matches_the_site(tmp_path, data):
    from jinn_uploader.keys import public_url

    t = Candidate(kind="track", key="audio/Archive 01 (v2)!*'.m4a", title="x")
    a = mv("mv/未完こそ、かわいい。.mp4", "y")
    portfolio.plan([a, t], data)
    reg = portfolio.build(data, [a, t])
    d = tmp_path / "enc"
    d.mkdir()
    (d / "works.json").write_text(portfolio.dump_json(reg.works_doc), encoding="utf-8")
    (d / "soundscape.json").write_text(portfolio.dump_json(reg.soundscape_doc), encoding="utf-8")
    js = run_js(d)
    for key, encoded in js["encodedKeys"].items():
        assert public_url("https://b", key) == f"https://b/{encoded}", key
