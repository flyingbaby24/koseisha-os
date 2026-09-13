"""The query encoder boundary: chosen by configuration, never by availability.

The property these tests exist to protect is determinism. If a deployment can
quietly end up using a different encoder than it was configured for, then two
instances of the same commit can rank the same query differently and nothing
in the system says so (T7 §7).

No test here loads a real model: they use temporary directories and manifests.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from api import config as config_module
from api.config import DEVELOPMENT, PUBLIC_DEMO, get_settings
from api.embedding_model import EmbeddingModelUnavailableError
from api.query_encoder import (
    MANIFEST_FILENAME,
    PROVIDER_ONNX,
    PROVIDER_SENTENCE_TRANSFORMERS,
    QueryEncoderUnavailableError,
    create_query_encoder,
    describe_encoder,
    encoder_manifest,
    verify_encoder_artifacts,
)
from api.readiness import FAILED, OK, ReadinessState, evaluate_query_encoder


def settings_with(**overrides):
    import os

    removed = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("THOUGHTMAP_")}
    try:
        base = get_settings()
    finally:
        os.environ.update(removed)
    return config_module.ApiSettings(**{**base.__dict__, **overrides})


def write_encoder(directory: Path, *, model_bytes: bytes = b"onnx-graph") -> dict:
    (directory / "model.onnx").write_bytes(model_bytes)
    (directory / "tokenizer.json").write_text("{}", encoding="utf-8")
    # Both tokenizer forms, because a prepared encoder directory carries both:
    # tokenizer.spm is what a deployment loads and tokenizer.json is the
    # reference it was verified against. Neither is parsed here - these tests
    # are about manifests and configuration, not about tokenization.
    (directory / "tokenizer.spm").write_bytes(b"spm")

    import hashlib

    manifest = {
        "schema_version": 1,
        "encoder_version": 1,
        "model_id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "revision": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
        "runtime": "onnxruntime",
        "embedding_dimension": 384,
        "files": {
            "model.onnx": {
                "bytes": len(model_bytes),
                "sha256": hashlib.sha256(model_bytes).hexdigest(),
            },
            "tokenizer.json": {
                "bytes": 2,
                "sha256": hashlib.sha256(b"{}").hexdigest(),
            },
            "tokenizer.spm": {
                "bytes": 3,
                "sha256": hashlib.sha256(b"spm").hexdigest(),
            },
        },
    }
    (directory / MANIFEST_FILENAME).write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


class ArtifactVerificationTests(unittest.TestCase):
    def test_accepts_a_complete_encoder(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_encoder(root)
            verify_encoder_artifacts(root, manifest, verify_checksums=True)

    def test_rejects_a_missing_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(QueryEncoderUnavailableError) as caught:
                verify_encoder_artifacts(Path(directory))
            self.assertIn("model identity", str(caught.exception))

    def test_rejects_an_unpinned_model(self) -> None:
        # An encoder that does not say which model it came from cannot be
        # reproduced, and its ranking cannot be attributed to anything.
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / MANIFEST_FILENAME).write_text(json.dumps({"files": {}}), encoding="utf-8")
            with self.assertRaises(QueryEncoderUnavailableError) as caught:
                verify_encoder_artifacts(root)
            self.assertIn("model_id", str(caught.exception))

    def test_rejects_a_missing_file(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_encoder(root)
            (root / "model.onnx").unlink()
            with self.assertRaises(QueryEncoderUnavailableError) as caught:
                verify_encoder_artifacts(root, manifest)
            self.assertIn("model.onnx", str(caught.exception))

    def test_rejects_a_truncated_file_by_size(self) -> None:
        # The realistic failure: an interrupted transfer of a 449 MB weights
        # sidecar, caught by a stat rather than by a wrong answer later.
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_encoder(root)
            (root / "model.onnx").write_bytes(b"trunc")
            with self.assertRaises(QueryEncoderUnavailableError) as caught:
                verify_encoder_artifacts(root, manifest)
            self.assertIn("wrong size", str(caught.exception))

    def test_rejects_a_corrupt_file_by_checksum(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = write_encoder(root, model_bytes=b"0123456789")
            (root / "model.onnx").write_bytes(b"9876543210")  # same length
            verify_encoder_artifacts(root, manifest, verify_checksums=False)  # size-only passes
            with self.assertRaises(QueryEncoderUnavailableError):
                verify_encoder_artifacts(root, manifest, verify_checksums=True)

    def test_rejects_invalid_manifest_json(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / MANIFEST_FILENAME).write_text("{not json", encoding="utf-8")
            with self.assertRaises(QueryEncoderUnavailableError):
                encoder_manifest(root)

    def test_absent_manifest_reads_as_none(self) -> None:
        with TemporaryDirectory() as directory:
            self.assertIsNone(encoder_manifest(Path(directory)))


class ProviderSelectionTests(unittest.TestCase):
    def test_onnx_without_a_directory_raises(self) -> None:
        settings = settings_with(encoder_provider=PROVIDER_ONNX, encoder_dir=None)
        with self.assertRaises(QueryEncoderUnavailableError) as caught:
            create_query_encoder(settings)
        self.assertIn("THOUGHTMAP_ENCODER_DIR", str(caught.exception))

    def test_a_broken_onnx_encoder_never_falls_back(self) -> None:
        # The heart of it: a configured-but-broken encoder must fail loudly.
        # Silently producing a sentence-transformers encoder here would make
        # two deployments of one commit rank differently.
        with TemporaryDirectory() as directory:
            settings = settings_with(
                encoder_provider=PROVIDER_ONNX, encoder_dir=Path(directory)
            )
            with self.assertRaises(QueryEncoderUnavailableError):
                create_query_encoder(settings)

    def test_an_unknown_provider_raises(self) -> None:
        settings = settings_with(encoder_provider="telepathy")
        with self.assertRaises(QueryEncoderUnavailableError) as caught:
            create_query_encoder(settings)
        self.assertIn("telepathy", str(caught.exception))

    def test_encoder_errors_are_answered_as_503(self) -> None:
        # QueryEncoderUnavailableError must remain a subclass of the error the
        # HTTP layer already translates to 503, not a new 500.
        self.assertTrue(
            issubclass(QueryEncoderUnavailableError, EmbeddingModelUnavailableError)
        )

    def test_describe_reports_the_pinned_identity(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_encoder(root)
            settings = settings_with(encoder_provider=PROVIDER_ONNX, encoder_dir=root)
            described = describe_encoder(settings)

        self.assertEqual(described["provider"], PROVIDER_ONNX)
        self.assertIn("MiniLM", described["model_id"])
        self.assertEqual(described["revision"], "e8f8c211226b894fcb81acc59f3b34ba3efd5f42")

    def test_describe_loads_nothing(self) -> None:
        # /config calls this on every request; it must not touch the model.
        settings = settings_with(
            encoder_provider=PROVIDER_ONNX, encoder_dir=Path("/nonexistent")
        )
        described = describe_encoder(settings)
        self.assertEqual(described["provider"], PROVIDER_ONNX)


class ReadinessIntegrationTests(unittest.TestCase):
    def test_a_valid_encoder_passes_readiness(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_encoder(root)
            settings = settings_with(
                encoder_provider=PROVIDER_ONNX,
                encoder_dir=root,
                deployment_mode=PUBLIC_DEMO,
            )
            state = ReadinessState(settings)
            evaluate_query_encoder(state, settings)

        check = next(c for c in state.snapshot()["checks"] if c["name"] == "query_encoder")
        self.assertEqual(check["status"], OK)
        self.assertIn("MiniLM", check["model_id"])

    def test_a_missing_encoder_blocks_readiness_with_a_reason(self) -> None:
        with TemporaryDirectory() as directory:
            settings = settings_with(
                encoder_provider=PROVIDER_ONNX,
                encoder_dir=Path(directory),
                deployment_mode=PUBLIC_DEMO,
            )
            state = ReadinessState(settings)
            evaluate_query_encoder(state, settings)

        snapshot = state.snapshot()
        self.assertFalse(snapshot["ready"])
        self.assertIn("query_encoder", snapshot["blocked_by"])
        check = next(c for c in snapshot["checks"] if c["name"] == "query_encoder")
        self.assertEqual(check["status"], FAILED)
        self.assertTrue(check["detail"], "a failure must say what is wrong")

    def test_an_unset_directory_blocks_readiness(self) -> None:
        settings = settings_with(
            encoder_provider=PROVIDER_ONNX, encoder_dir=None, deployment_mode=PUBLIC_DEMO
        )
        state = ReadinessState(settings)
        evaluate_query_encoder(state, settings)

        self.assertIn("query_encoder", state.snapshot()["blocked_by"])

    def test_the_reference_provider_does_not_block_development(self) -> None:
        settings = settings_with(
            encoder_provider=PROVIDER_SENTENCE_TRANSFORMERS, deployment_mode=DEVELOPMENT
        )
        state = ReadinessState(settings)
        state.set("configuration", OK)
        evaluate_query_encoder(state, settings)

        self.assertTrue(state.ready)


if __name__ == "__main__":
    unittest.main()
