import json

import pytest

from jinn_uploader import archive_json, keys, pricing
from jinn_uploader.config import AppConfig, ConfigStore, DEFAULT_BUCKET, DEFAULT_PUBLIC_BASE_URL, Pricing
from jinn_uploader.credentials import CredentialError, CredentialStore, MemoryKeyring, R2Credentials
from jinn_uploader.scanner import hash_file, scan_paths


def test_public_url_matches_existing_archive_urls():
    base = DEFAULT_PUBLIC_BASE_URL
    assert keys.public_url(base, "Meaning Hollow.mp4") == base + "/Meaning%20Hollow.mp4"
    assert keys.public_url(base + "/", "Million consumer full.mp4") == base + "/Million%20consumer%20full.mp4"
    assert keys.public_url(base, "mv/未完こそ、かわいい。.mp4").startswith(base + "/mv/%E6%9C%AA")


def test_build_key_and_prefixes():
    assert keys.normalize_prefix("\\MV\\2026\\") == "MV/2026/"
    assert keys.normalize_prefix("") == ""
    assert keys.build_key("mv/", "Human.mp4") == "mv/Human.mp4"
    assert keys.build_key("", "Human.mp4") == "Human.mp4"
    assert keys.build_key("bgm", "a.mp3", ("Album", "Disc 1")) == "bgm/Album/Disc 1/a.mp3"
    with pytest.raises(ValueError):
        keys.normalize_prefix("../etc")
    with pytest.raises(ValueError):
        keys.validate_key("mv/")


def test_rename_candidate():
    taken = {"mv/Song (2).mp4"}
    assert keys.rename_candidate("mv/Song.mp4", taken) == "mv/Song (3).mp4"
    assert keys.rename_candidate("Song (3).mp4", set()) == "Song (4).mp4"
    assert keys.rename_candidate("noext", set()) == "noext (2)"


def test_classify_and_content_type():
    assert keys.classify("x.MP4") == "mv"
    assert keys.classify("x.wav") == "bgm"
    assert keys.classify("x.png") == "other"
    assert keys.content_type_for("a.mov") == "video/quicktime"
    assert keys.content_type_for("a.mp3") == "audio/mpeg"


def test_formatting():
    assert keys.format_duration(85.2) == "1:25"
    assert keys.format_duration(3725) == "1:02:05"
    assert keys.iso8601_duration(85) == "PT1M25S"
    assert keys.iso8601_duration(0) == "PT0S"
    assert keys.slugify("Wrapped Too Beautifully") == "wrapped-too-beautifully"
    assert keys.slugify("未完こそ", "mv-0005") == "mv-0005"


def test_config_roundtrip(tmp_path):
    store = ConfigStore(tmp_path / "c.json")
    cfg = store.load()
    assert cfg.bucket == DEFAULT_BUCKET
    assert cfg.public_base_url == DEFAULT_PUBLIC_BASE_URL
    assert cfg.compression == "none"  # originals by default
    cfg.mv_prefix = "videos/"
    cfg.pricing.usd_jpy = 160
    store.save(cfg)
    again = store.load()
    assert again.mv_prefix == "videos/" and again.pricing.usd_jpy == 160
    raw = (tmp_path / "c.json").read_text(encoding="utf-8")
    assert "secret" not in raw.lower()
    (tmp_path / "c.json").write_text("{broken", encoding="utf-8")
    assert store.load().bucket == DEFAULT_BUCKET


def test_credentials_roundtrip_and_masking():
    store = CredentialStore(backend=MemoryKeyring())
    assert store.load() is None
    creds = R2Credentials("A" * 32, "b" * 32, "c" * 64)
    store.save(creds)
    loaded = store.load()
    assert loaded.account_id == "a" * 32  # normalized
    assert "c" * 64 not in repr(loaded) and "***" in repr(loaded)
    assert store.delete() is True
    assert store.load() is None
    with pytest.raises(CredentialError):
        store.save(R2Credentials("", "", ""))


def test_insecure_backend_is_refused():
    from keyring.backends.fail import Keyring as FailKeyring

    store = CredentialStore(backend=FailKeyring())
    assert not store.secure
    with pytest.raises(CredentialError):
        store.save(R2Credentials("a" * 32, "b" * 32, "c" * 64))


def test_credential_warnings():
    assert R2Credentials("Jinn Project Media", "x", "y").warnings()
    assert not R2Credentials("a" * 32, "b" * 32, "c" * 64).warnings()


def test_scan_paths_and_hash(tmp_path):
    root = tmp_path / "Album"
    (root / "sub").mkdir(parents=True)
    (root / "a.mp3").write_bytes(b"aaa")
    (root / "sub" / "b.mp4").write_bytes(b"bbbb")
    (root / ".hidden").write_bytes(b"h")
    (root / "Thumbs.db").write_bytes(b"t")
    single = tmp_path / "c.wav"
    single.write_bytes(b"cc")
    found = scan_paths([root, single, single])
    names = [f.path.name for f in found]
    assert names == ["a.mp3", "b.mp4", "c.wav"]
    assert found[1].subdirs == ("Album", "sub")
    md5, sha = hash_file(single)
    assert md5 == "e0323a9039add2978bf5b49550572c7c"
    assert sha == "355b1bbfc96725cdce8f4a2708fda310a80e6d13315aec4e5eed2a75fe8032ce"


def test_pricing_estimate():
    est = pricing.estimate(25 * 10**9, class_a_ops=0, class_b_ops=0, pricing=Pricing())
    assert est.billable_storage_gb == pytest.approx(15)
    assert est.total_usd == pytest.approx(15 * 0.015)
    assert pricing.estimate(5 * 10**9).within_free_tier
    assert pricing.upload_class_a_ops(10, 100, 50) == 1
    assert pricing.upload_class_a_ops(330 * 2**20, 32 * 2**20, 16 * 2**20) == 21 + 2


def test_archive_document_matches_site_schema(tmp_path):
    row = {
        "key": "mv/Human.mp4", "local_path": "C:/MV/Human.mp4", "category": "mv", "width": 1080,
        "height": 1920, "duration": 85.0, "content_type": "video/mp4", "size": 123, "sha256": "ab",
        "thumb_key": "thumbnails/human.webp", "poster_key": "thumbnails/human-poster.jpg",
        "uploaded_at": "2026-11-26T00:00:00+00:00",
    }
    item = archive_json.ArchiveItem.from_history(row, 5, "Jinn Project")
    doc = archive_json.build_document([item], DEFAULT_PUBLIC_BASE_URL, DEFAULT_BUCKET)
    work = doc["works"][0]
    # Same keys, in the same order, as the archive's embedded x-data works.
    assert list(work)[:13] == list(archive_json.REQUIRED_WORK_KEYS)
    assert work["id"] == "mv-0005" and work["slug"] == "human" and work["durationText"] == "1:25"
    assert work["video"] == DEFAULT_PUBLIC_BASE_URL + "/mv/Human.mp4"
    assert work["thumb"].endswith("/thumbnails/human.webp")
    assert work["duration"] == "PT1M25S" and work["uploadDate"] == "2026-11-26"
    assert archive_json.validate_document(doc) == []
    path = archive_json.write_document(doc, tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["works"][0]["title"] == "Human"
