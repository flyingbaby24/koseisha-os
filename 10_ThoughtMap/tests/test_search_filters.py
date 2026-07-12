import pandas as pd
import sqlite3

from web.search_utils import (
    apply_metadata_filter,
    apply_parameter_filter,
    filter_options,
)
from web.api.db_source import OfficialDatabaseSource
from web.api.repositories import _join_parameter_scores


def sample_index():
    return pd.DataFrame([
        {"doc_id": "1", "source": " Gutendex ", "category": '["Philosophy", "History"]', "parameter_scores": {"philosophy": 0.8, "science": 0.2}},
        {"doc_id": "2", "source": "suno", "category": "music|AI", "parameter_scores": {"philosophy": 0.1, "science": 0.9}},
        {"doc_id": "3", "source": None, "category": None, "parameter_scores": {}},
    ])


def test_filter_options_ignore_null_and_preserve_values():
    frame = sample_index()
    assert filter_options(frame, "source") == ["all", "Gutendex", "suno"]
    assert set(filter_options(frame, "category", multi=True)) == {"all", "Philosophy", "History", "music", "AI"}


def test_filters_work_alone_and_in_combination():
    frame = sample_index()
    assert apply_metadata_filter(frame, "source", " GUTENDEX ")["doc_id"].tolist() == ["1"]
    assert apply_metadata_filter(frame, "category", "philosophy", multi=True)["doc_id"].tolist() == ["1"]
    assert apply_parameter_filter(frame, "SCIENCE")["doc_id"].tolist() == ["2"]
    combined = apply_metadata_filter(frame, "source", "suno")
    combined = apply_metadata_filter(combined, "category", "ai", multi=True)
    combined = apply_parameter_filter(combined, "science")
    assert combined["doc_id"].tolist() == ["2"]


def test_no_filter_empty_and_missing_columns_are_safe():
    frame = sample_index()
    assert len(apply_parameter_filter(frame, "general")) == 3
    assert len(apply_metadata_filter(frame, "source", "all")) == 3
    assert apply_parameter_filter(apply_metadata_filter(frame, "source", "missing"), "science").empty
    missing = pd.DataFrame([{"doc_id": "1"}])
    assert filter_options(missing, "source") == ["all"]
    assert len(apply_metadata_filter(missing, "source", "anything")) == 1


def test_top_is_applied_after_filtering():
    frame = pd.concat([sample_index()] * 4, ignore_index=True)
    filtered = apply_parameter_filter(frame, "science")
    assert len(filtered.head(2)) == 2
    assert set(filtered.head(2)["doc_id"]) == {"2"}


def test_parameter_join_normalizes_ids_and_drops_missing():
    documents = pd.DataFrame([{"doc_id": " 1 "}, {"doc_id": "2"}])
    scores = pd.DataFrame([
        {"doc_id": 1, "philosophy": 0.8},
        {"doc_id": " 2 ", "philosophy": 0.4},
        {"doc_id": None, "philosophy": 1.0},
    ])
    joined = _join_parameter_scores(documents, scores)
    assert joined["doc_id"].tolist() == ["1", "2"]
    assert joined["parameter_scores"].tolist() == [{"philosophy": 0.8}, {"philosophy": 0.4}]


def test_parameter_tie_uses_first_definition_order_like_idxmax():
    frame = pd.DataFrame([{"doc_id": "1", "parameter_scores": {"philosophy": 0.8, "science": 0.8}}])
    assert apply_parameter_filter(frame, "philosophy")["doc_id"].tolist() == ["1"]
    assert apply_parameter_filter(frame, "science").empty


def test_database_source_download_is_mockable_and_atomic(tmp_path):
    target = tmp_path / "cache" / "thoughtmap.sqlite"
    calls = []
    def downloader(url, destination):
        calls.append(url)
        with sqlite3.connect(destination) as connection:
            connection.execute("CREATE TABLE documents (doc_id TEXT)")
            connection.execute("CREATE TABLE embeddings (doc_id TEXT, embedding TEXT)")
    source = OfficialDatabaseSource(target, "https://example.test/files/thoughtmap.sqlite", downloader)
    assert source.ensure_local() == target
    assert source.ensure_local() == target
    assert calls == ["https://example.test/files/thoughtmap.sqlite"]
    assert not list(target.parent.glob("*.tmp"))


def test_database_source_removes_broken_download(tmp_path):
    target = tmp_path / "thoughtmap.sqlite"
    def broken(_url, destination):
        destination.write_bytes(b"not sqlite")
    try:
        OfficialDatabaseSource(target, "https://example.test/file", broken).ensure_local()
        raise AssertionError("broken SQLite download should fail")
    except (sqlite3.DatabaseError, ValueError):
        pass
    assert not target.exists()
    assert not list(tmp_path.glob("*.tmp"))
