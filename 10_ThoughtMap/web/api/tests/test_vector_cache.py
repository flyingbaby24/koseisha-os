"""The parsed-vector cache must be fast, and must never be wrong.

It is the reason a restart takes ~4 s instead of ~50 s, and — since T6 — the
reason the 542 MB artifact can be left unread entirely. Both make correctness
here load-bearing: a cache accepted when it should not be would serve wrong
vectors, and wrong vectors are wrong search results that look perfectly normal.

Every test below asserts the same rule from a different angle: **when in doubt,
reparse.** No rejection path may return data (T6 §16).
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from api.repositories import (
    VECTOR_CACHE_VERSION,
    _load_cached_vectors,
    _store_cached_vectors,
    _vector_cache_path,
)


SHA = "a" * 64
OTHER_SHA = "b" * 64


class VectorCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.artifact = self.root / "embeddings.csv"
        self.artifact.write_bytes(b"doc_id,embedding\n" + b"x" * 512)

        self.doc_ids = [f"doc_{i:03d}" for i in range(10)]
        self.vectors = np.arange(10 * 4, dtype=np.float32).reshape(10, 4)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def store(self, sha: str = SHA) -> None:
        _store_cached_vectors(self.artifact, self.doc_ids, self.vectors, sha)

    # --- the happy path --------------------------------------------------

    def test_round_trips_vectors_exactly(self) -> None:
        self.store()
        cached = _load_cached_vectors(self.artifact, SHA)

        self.assertIsNotNone(cached)
        assert cached is not None
        self.assertEqual(list(cached["doc_id"]), self.doc_ids)
        # Exact, not approximate: these are the vectors search will rank on.
        self.assertTrue(np.array_equal(cached["vectors"], self.vectors))

    def test_reports_matching_by_checksum(self) -> None:
        # The load path only skips reading the artifact on a checksum match,
        # so the distinction has to be visible.
        self.store()
        cached = _load_cached_vectors(self.artifact, SHA)
        assert cached is not None
        self.assertEqual(cached["matched_by"], "sha256")

    def test_falls_back_to_mtime_when_no_checksum_is_known(self) -> None:
        _store_cached_vectors(self.artifact, self.doc_ids, self.vectors, "")
        cached = _load_cached_vectors(self.artifact, "")
        assert cached is not None
        self.assertEqual(cached["matched_by"], "mtime")

    def test_a_checksum_match_survives_a_changed_mtime(self) -> None:
        # This is the property that lets a cache be built once and shipped:
        # copying the artifact changes its mtime but not its content.
        self.store()
        import os
        import time

        future = time.time() + 5_000
        os.utime(self.artifact, (future, future))

        cached = _load_cached_vectors(self.artifact, SHA)
        self.assertIsNotNone(cached)
        assert cached is not None
        self.assertEqual(cached["matched_by"], "sha256")

    # --- invalidation ----------------------------------------------------

    def test_absent_cache_is_not_an_error(self) -> None:
        self.assertIsNone(_load_cached_vectors(self.artifact, SHA))

    def test_a_different_artifact_checksum_invalidates(self) -> None:
        self.store(SHA)
        self.assertIsNone(_load_cached_vectors(self.artifact, OTHER_SHA))

    def test_a_changed_artifact_size_invalidates_without_a_checksum(self) -> None:
        _store_cached_vectors(self.artifact, self.doc_ids, self.vectors, "")
        self.artifact.write_bytes(b"different length entirely")
        self.assertIsNone(_load_cached_vectors(self.artifact, ""))

    def test_an_older_cache_version_is_ignored(self) -> None:
        cache = _vector_cache_path(self.artifact)
        np.savez(
            cache,
            doc_id=np.asarray(self.doc_ids).astype("U"),
            vectors=self.vectors,
            cache_version=np.int64(VECTOR_CACHE_VERSION - 1),
            source_sha256=np.str_(SHA),
            source_size=np.int64(self.artifact.stat().st_size),
            source_mtime_ns=np.int64(self.artifact.stat().st_mtime_ns),
        )
        self.assertIsNone(_load_cached_vectors(self.artifact, SHA))

    # --- corruption ------------------------------------------------------

    def test_a_truncated_cache_is_rejected(self) -> None:
        self.store()
        cache = _vector_cache_path(self.artifact)
        data = cache.read_bytes()
        cache.write_bytes(data[: len(data) // 2])

        self.assertIsNone(_load_cached_vectors(self.artifact, SHA))

    def test_a_garbage_cache_is_rejected(self) -> None:
        self.store()
        _vector_cache_path(self.artifact).write_bytes(b"this is not an npz file")
        self.assertIsNone(_load_cached_vectors(self.artifact, SHA))

    def test_an_empty_cache_is_rejected(self) -> None:
        _store_cached_vectors(self.artifact, [], np.zeros((0, 4), dtype=np.float32), SHA)
        self.assertIsNone(_load_cached_vectors(self.artifact, SHA))

    def test_mismatched_array_lengths_are_rejected(self) -> None:
        # np.load validates the container and each array header but not that
        # the two arrays still describe each other, which is exactly what a
        # partial write breaks.
        cache = _vector_cache_path(self.artifact)
        np.savez(
            cache,
            doc_id=np.asarray(self.doc_ids[:5]).astype("U"),
            vectors=self.vectors,  # 10 rows against 5 ids
            cache_version=np.int64(VECTOR_CACHE_VERSION),
            source_sha256=np.str_(SHA),
            source_size=np.int64(self.artifact.stat().st_size),
            source_mtime_ns=np.int64(self.artifact.stat().st_mtime_ns),
        )
        self.assertIsNone(_load_cached_vectors(self.artifact, SHA))

    def test_a_one_dimensional_vector_array_is_rejected(self) -> None:
        cache = _vector_cache_path(self.artifact)
        np.savez(
            cache,
            doc_id=np.asarray(self.doc_ids).astype("U"),
            vectors=np.arange(10, dtype=np.float32),
            cache_version=np.int64(VECTOR_CACHE_VERSION),
            source_sha256=np.str_(SHA),
            source_size=np.int64(self.artifact.stat().st_size),
            source_mtime_ns=np.int64(self.artifact.stat().st_mtime_ns),
        )
        self.assertIsNone(_load_cached_vectors(self.artifact, SHA))

    # --- writing ---------------------------------------------------------

    def test_writing_leaves_no_temporary_file_behind(self) -> None:
        self.store()
        leftovers = list(self.root.glob("*.tmp*"))
        self.assertEqual(leftovers, [], f"temporary files left behind: {leftovers}")

    def test_a_rewrite_replaces_the_previous_cache(self) -> None:
        self.store()
        replacement = np.full((10, 4), 7.0, dtype=np.float32)
        _store_cached_vectors(self.artifact, self.doc_ids, replacement, SHA)

        cached = _load_cached_vectors(self.artifact, SHA)
        assert cached is not None
        self.assertTrue(np.array_equal(cached["vectors"], replacement))

    def test_an_unwritable_destination_is_not_fatal(self) -> None:
        # A read-only artifact directory is a legitimate deployment; it costs
        # parse time on every start, not a failure.
        missing = self.root / "no-such-directory" / "embeddings.csv"
        _store_cached_vectors(missing, self.doc_ids, self.vectors, SHA)
        self.assertFalse((self.root / "no-such-directory").exists())

    def test_the_cache_sits_beside_the_artifact(self) -> None:
        self.assertEqual(
            _vector_cache_path(self.artifact).name, "embeddings.csv.vectors.npz"
        )


if __name__ == "__main__":
    unittest.main()
