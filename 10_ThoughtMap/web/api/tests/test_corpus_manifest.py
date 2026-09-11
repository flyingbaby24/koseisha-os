"""The manifest must make the stale embedding snapshot impossible to use.

A partial embedding file joins perfectly cleanly against the full documents
master — search simply returns fewer things. Nothing looks broken. These tests
pin the checks that turn that silent 7%-corpus failure into a loud one.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from api.corpus_manifest import MANIFEST_FILENAME, CorpusManifest, CorpusMismatchError


CANONICAL = {
    "schema_version": 1,
    "document_count": 63891,
    "embedding_count": 63891,
    "embedding_dimension": 384,
    "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
    "embedding_artifact_sha256": "a" * 64,
    "embedding_artifact_bytes": 541_994_243,
    "embedding_artifact_filename": "thoughtmap_canonical_embeddings.csv",
    "documents_sha256": "b" * 64,
    "sources": {"gutendex": 62306, "user_suno": 992, "user_note": 471, "zip": 122},
}


def write_manifest(directory: Path, data: dict | None = None) -> CorpusManifest:
    (directory / MANIFEST_FILENAME).write_text(
        json.dumps(data or CANONICAL), encoding="utf-8"
    )
    manifest = CorpusManifest.load(directory)
    assert manifest is not None
    return manifest


class LoadTests(unittest.TestCase):
    def test_absent_manifest_is_not_an_error(self) -> None:
        # A corpus predating T4.6 has no manifest; historical behaviour applies.
        with TemporaryDirectory() as directory:
            self.assertIsNone(CorpusManifest.load(Path(directory)))

    def test_reads_the_canonical_shape(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = write_manifest(Path(directory))
            self.assertEqual(manifest.document_count, 63891)
            self.assertEqual(manifest.embedding_dimension, 384)
            self.assertEqual(manifest.sources["gutendex"], 62306)

    def test_rejects_a_corrupt_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            (Path(directory) / MANIFEST_FILENAME).write_text("{not json", encoding="utf-8")
            with self.assertRaises(CorpusMismatchError):
                CorpusManifest.load(Path(directory))


class ArtifactFileTests(unittest.TestCase):
    def test_rejects_the_stale_snapshot_by_size(self) -> None:
        """The real failure this exists to prevent."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_manifest(root)

            stale = root / "embeddings_master.csv"
            stale.write_bytes(b"x" * 1024)  # far short of 542 MB

            with self.assertRaises(CorpusMismatchError) as caught:
                manifest.check_artifact_file(stale)

            message = str(caught.exception)
            self.assertIn("does not match the corpus manifest", message)
            self.assertIn("thoughtmap_canonical_embeddings.csv", message)
            # The message must say what to do about it.
            self.assertIn("THOUGHTMAP_EMBEDDINGS_PATH", message)

    def test_accepts_an_artifact_of_the_recorded_size(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            data = {**CANONICAL, "embedding_artifact_bytes": 12}
            manifest = write_manifest(root, data)

            artifact = root / "canonical.csv"
            artifact.write_bytes(b"x" * 12)
            manifest.check_artifact_file(artifact)  # must not raise

    def test_skips_the_size_check_when_unrecorded(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_manifest(root, {**CANONICAL, "embedding_artifact_bytes": 0})
            artifact = root / "any.csv"
            artifact.write_bytes(b"x")
            manifest.check_artifact_file(artifact)  # must not raise


class LoadedCorpusTests(unittest.TestCase):
    def manifest(self, directory: str) -> CorpusManifest:
        return write_manifest(Path(directory))

    def test_rejects_a_partially_embedded_corpus(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.manifest(directory)
            with self.assertRaises(CorpusMismatchError) as caught:
                # Exactly the stale-snapshot outcome: 4,584 of 63,891.
                manifest.check_loaded_corpus(searchable=4584, documents=63891)

            message = str(caught.exception)
            self.assertIn("4,584", message)
            self.assertIn("63,891", message)
            self.assertIn("7.2%", message)

    def test_accepts_the_whole_corpus(self) -> None:
        with TemporaryDirectory() as directory:
            self.manifest(directory).check_loaded_corpus(searchable=63891, documents=63891)

    def test_warns_but_does_not_fail_on_a_deliberately_changed_corpus(self) -> None:
        # Documents differing from the manifest is a stale-manifest problem,
        # not a wrong-artifact problem, so it logs rather than raising.
        with TemporaryDirectory() as directory:
            manifest = self.manifest(directory)
            with self.assertLogs("thoughtmap.manifest", level="WARNING"):
                manifest.check_loaded_corpus(searchable=70000, documents=70000)


class ModelTests(unittest.TestCase):
    def test_accepts_the_canonical_model(self) -> None:
        with TemporaryDirectory() as directory:
            write_manifest(Path(directory)).check_model(
                {"paraphrase-multilingual-MiniLM-L12-v2"}
            )

    def test_accepts_the_namespaced_spelling(self) -> None:
        with TemporaryDirectory() as directory:
            write_manifest(Path(directory)).check_model(
                {"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
            )

    def test_rejects_a_foreign_model(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(CorpusMismatchError) as caught:
                write_manifest(Path(directory)).check_model({"all-MiniLM-L6-v2"})
            self.assertIn("cosine space", str(caught.exception))

    def test_rejects_a_mixture(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(CorpusMismatchError):
                write_manifest(Path(directory)).check_model(
                    {"paraphrase-multilingual-MiniLM-L12-v2", "all-MiniLM-L6-v2"}
                )


class HashTests(unittest.TestCase):
    def test_verifies_content(self) -> None:
        import hashlib

        with TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "canonical.csv"
            artifact.write_bytes(b"hello")
            digest = hashlib.sha256(b"hello").hexdigest()

            good = write_manifest(root, {**CANONICAL, "embedding_artifact_sha256": digest})
            self.assertTrue(good.verify_artifact_hash(artifact))

            bad = write_manifest(root, {**CANONICAL, "embedding_artifact_sha256": "c" * 64})
            self.assertFalse(bad.verify_artifact_hash(artifact))


if __name__ == "__main__":
    unittest.main()
