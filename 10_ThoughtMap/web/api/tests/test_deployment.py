"""Deployment behaviour: configuration safety, readiness, caching, gating.

These are the checks that decide whether a deployment is allowed to serve
traffic, so they are pinned here rather than left to a live smoke run. They use
temporary directories and fake state throughout — nothing here depends on the
542 MB artifact, on a network, or on which machine it runs on (T6 §50).
"""

from __future__ import annotations

import gzip
import json
import os
import sys
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from api import config as config_module
from api.config import DEVELOPMENT, PRODUCTION, PUBLIC_DEMO, WARMUP_FULL, WARMUP_OFF, get_settings
from api.corpus_manifest import MANIFEST_FILENAME, CorpusManifest
from api.map_response_cache import MapResponseCache, accepts_gzip
from api.readiness import (
    DEFERRED,
    FAILED,
    OK,
    PENDING,
    ReadinessState,
    evaluate_configuration,
    evaluate_manifest,
    run_warmup,
)


@contextmanager
def environment(**values: str):
    """Run with exactly these THOUGHTMAP_* variables set, and no others."""
    removed = {
        key: os.environ.pop(key)
        for key in list(os.environ)
        if key.startswith("THOUGHTMAP_")
    }
    try:
        os.environ.update(values)
        yield
    finally:
        for key in list(os.environ):
            if key.startswith("THOUGHTMAP_"):
                del os.environ[key]
        os.environ.update(removed)


class DeploymentModeTests(unittest.TestCase):
    def test_development_is_the_default_and_stays_permissive(self) -> None:
        with environment():
            settings = get_settings()
        self.assertEqual(settings.deployment_mode, DEVELOPMENT)
        self.assertEqual(settings.allowed_origins, ("*",))
        self.assertEqual(settings.warmup, WARMUP_OFF)
        self.assertTrue(settings.library_enabled)
        self.assertEqual(settings.configuration_errors, ())

    def test_public_deployment_never_defaults_to_a_wildcard_origin(self) -> None:
        # Unset must mean "no cross-origin access", never "every origin".
        with environment(THOUGHTMAP_DEPLOYMENT_MODE=PUBLIC_DEMO):
            settings = get_settings()

        self.assertEqual(settings.allowed_origins, ())

    def test_unset_origins_are_valid_for_a_same_origin_deployment(self) -> None:
        # The recommended topology serves the frontend and the API from one
        # hostname, so there is no cross-origin request to allow. T6 treated
        # this as a configuration error, which stopped the recommended
        # deployment from ever becoming ready.
        with environment(
            THOUGHTMAP_DEPLOYMENT_MODE=PUBLIC_DEMO,
            THOUGHTMAP_ENCODER_PROVIDER="sentence-transformers",
        ):
            settings = get_settings()

        self.assertEqual(settings.allowed_origins, ())
        self.assertEqual(settings.configuration_errors, ())

    def test_public_deployment_strips_an_explicit_wildcard(self) -> None:
        with environment(
            THOUGHTMAP_DEPLOYMENT_MODE=PRODUCTION,
            THOUGHTMAP_ALLOWED_ORIGINS="*,https://thoughtmap.example",
        ):
            settings = get_settings()

        self.assertEqual(settings.allowed_origins, ("https://thoughtmap.example",))
        self.assertTrue(any("may not be '*'" in e for e in settings.configuration_errors))

    def test_explicit_origins_are_accepted(self) -> None:
        # A public deployment must also name its query encoder (T7 §7), so a
        # fully-valid public configuration sets both.
        with environment(
            THOUGHTMAP_DEPLOYMENT_MODE=PUBLIC_DEMO,
            THOUGHTMAP_ALLOWED_ORIGINS="https://a.example, https://b.example",
            THOUGHTMAP_ENCODER_PROVIDER="sentence-transformers",
        ):
            settings = get_settings()

        self.assertEqual(settings.allowed_origins, ("https://a.example", "https://b.example"))
        self.assertEqual(settings.configuration_errors, ())

    def test_onnx_without_an_encoder_directory_is_a_configuration_error(self) -> None:
        # Silence here would mean a deployment that cannot encode a query
        # discovering it at the first search rather than at startup.
        with environment(
            THOUGHTMAP_DEPLOYMENT_MODE=PUBLIC_DEMO,
            THOUGHTMAP_ALLOWED_ORIGINS="https://a.example",
            THOUGHTMAP_ENCODER_PROVIDER="onnx",
        ):
            settings = get_settings()

        self.assertTrue(
            any("THOUGHTMAP_ENCODER_DIR" in error for error in settings.configuration_errors)
        )

    def test_public_deployments_default_to_the_onnx_encoder(self) -> None:
        # ONNX needs no torch and contacts no model registry, which is what
        # makes a deployment self-contained (T7 §8).
        with environment(
            THOUGHTMAP_DEPLOYMENT_MODE=PUBLIC_DEMO,
            THOUGHTMAP_ALLOWED_ORIGINS="https://a.example",
            THOUGHTMAP_ENCODER_DIR="/data/encoder",
        ):
            settings = get_settings()

        self.assertEqual(settings.encoder_provider, "onnx")
        self.assertEqual(settings.configuration_errors, ())

    def test_development_defaults_to_the_reference_encoder(self) -> None:
        with environment():
            settings = get_settings()

        self.assertEqual(settings.encoder_provider, "sentence-transformers")

    def test_an_unknown_encoder_provider_is_reported(self) -> None:
        with environment(THOUGHTMAP_ENCODER_PROVIDER="magic"):
            settings = get_settings()

        self.assertTrue(
            any("THOUGHTMAP_ENCODER_PROVIDER" in e for e in settings.configuration_errors)
        )
        self.assertEqual(settings.encoder_provider, "sentence-transformers")

    def test_library_is_off_by_default_where_it_would_be_public(self) -> None:
        for mode in (PUBLIC_DEMO, PRODUCTION):
            with self.subTest(mode=mode), environment(
                THOUGHTMAP_DEPLOYMENT_MODE=mode,
                THOUGHTMAP_ALLOWED_ORIGINS="https://a.example",
            ):
                settings = get_settings()
            self.assertFalse(
                settings.library_enabled,
                "an unauthenticated library must not be exposed by default",
            )

    def test_library_can_be_enabled_deliberately(self) -> None:
        with environment(
            THOUGHTMAP_DEPLOYMENT_MODE=PUBLIC_DEMO,
            THOUGHTMAP_ALLOWED_ORIGINS="https://a.example",
            THOUGHTMAP_LIBRARY_ENABLED="true",
        ):
            settings = get_settings()
        self.assertTrue(settings.library_enabled)

    def test_public_deployments_warm_up_by_default(self) -> None:
        with environment(
            THOUGHTMAP_DEPLOYMENT_MODE=PUBLIC_DEMO,
            THOUGHTMAP_ALLOWED_ORIGINS="https://a.example",
        ):
            settings = get_settings()
        self.assertEqual(settings.warmup, WARMUP_FULL)

    def test_an_unknown_mode_falls_back_and_reports(self) -> None:
        with environment(THOUGHTMAP_DEPLOYMENT_MODE="staging-ish"):
            settings = get_settings()
        self.assertEqual(settings.deployment_mode, DEVELOPMENT)
        self.assertTrue(settings.configuration_errors)

    def test_features_are_stated_in_one_place(self) -> None:
        with environment(THOUGHTMAP_DEPLOYMENT_MODE=DEVELOPMENT):
            features = get_settings().features()
        self.assertEqual(
            set(features),
            {
                "deployment_mode",
                "library_enabled",
                "diagnostics_enabled",
                "semantic_search_enabled",
            },
        )


def _settings(**overrides):
    with environment():
        base = get_settings()
    return config_module.ApiSettings(**{**base.__dict__, **overrides})


class ReadinessTests(unittest.TestCase):
    def test_a_fresh_state_is_not_ready(self) -> None:
        state = ReadinessState(_settings())
        self.assertFalse(state.ready)

    def test_an_expected_check_blocks_until_it_reports(self) -> None:
        # The bug this pins: readiness computed only from checks that had
        # already been written reported ready while the model was still
        # loading, because the absent check could not block.
        state = ReadinessState(_settings())
        state.set("configuration", OK)
        state.expect("embedding_model")

        snapshot = state.snapshot()
        self.assertFalse(snapshot["ready"])
        self.assertEqual(snapshot["blocked_by"], ["embedding_model"])

        state.set("embedding_model", OK)
        self.assertTrue(state.ready)

    def test_expect_never_overwrites_a_reported_check(self) -> None:
        state = ReadinessState(_settings())
        state.set("search_engine", OK, documents=63891)
        state.expect("search_engine")
        self.assertTrue(state.ready)

    def test_a_failed_check_blocks(self) -> None:
        state = ReadinessState(_settings())
        state.set("configuration", OK)
        state.set("embedding_artifact", FAILED, detail="wrong file")
        self.assertFalse(state.ready)
        self.assertEqual(state.snapshot()["blocked_by"], ["embedding_artifact"])

    def test_a_deferred_check_does_not_block(self) -> None:
        # Lazy loading in development is a choice, not a fault.
        state = ReadinessState(_settings())
        state.set("configuration", OK)
        state.set("search_engine", DEFERRED, detail="loads on first search")
        self.assertTrue(state.ready)

    def test_configuration_errors_make_the_process_unready(self) -> None:
        state = ReadinessState(_settings(configuration_errors=("origins missing",)))
        evaluate_configuration(state, _settings(configuration_errors=("origins missing",)))
        self.assertFalse(state.ready)

    def test_snapshot_is_cheap_and_repeatable(self) -> None:
        state = ReadinessState(_settings())
        state.set("configuration", OK)
        first = state.snapshot()
        second = state.snapshot()
        self.assertEqual(first["checks"], second["checks"])


class ManifestReadinessTests(unittest.TestCase):
    CANONICAL = {
        "corpus_version": "20260909",
        "document_count": 63891,
        "embedding_count": 63891,
        "embedding_dimension": 384,
        "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
        "embedding_artifact_sha256": "a" * 64,
        "embedding_artifact_bytes": 32,
        "embedding_artifact_filename": "thoughtmap_canonical_embeddings.csv",
        "documents_sha256": "b" * 64,
        "sources": {"gutendex": 62306},
    }

    def _manifest_dir(self, root: Path) -> Path:
        (root / MANIFEST_FILENAME).write_text(json.dumps(self.CANONICAL), encoding="utf-8")
        return root

    def test_a_public_deployment_requires_a_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            settings = _settings(deployment_mode=PUBLIC_DEMO)
            state = ReadinessState(settings)
            evaluate_manifest(state, settings, Path(directory))
            self.assertFalse(state.ready)

    def test_development_tolerates_a_missing_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            settings = _settings(deployment_mode=DEVELOPMENT)
            state = ReadinessState(settings)
            state.set("configuration", OK)
            evaluate_manifest(state, settings, Path(directory))
            self.assertTrue(state.ready)

    def test_a_public_deployment_requires_the_artifact_path(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._manifest_dir(Path(directory))
            settings = _settings(deployment_mode=PUBLIC_DEMO, embeddings_path=None)
            state = ReadinessState(settings)
            evaluate_manifest(state, settings, root)

            snapshot = state.snapshot()
            self.assertIn("embedding_artifact", snapshot["blocked_by"])
            detail = next(
                c["detail"] for c in snapshot["checks"] if c["name"] == "embedding_artifact"
            )
            self.assertIn("THOUGHTMAP_EMBEDDINGS_PATH", detail)

    def test_the_stale_snapshot_is_rejected_by_size(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._manifest_dir(Path(directory))
            stale = root / "embeddings_master.csv"
            stale.write_bytes(b"x" * 8)  # not the recorded 32

            settings = _settings(deployment_mode=PUBLIC_DEMO, embeddings_path=stale)
            state = ReadinessState(settings)
            evaluate_manifest(state, settings, root)

            self.assertIn("embedding_artifact", state.snapshot()["blocked_by"])

    def test_a_missing_artifact_names_the_path(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._manifest_dir(Path(directory))
            missing = root / "not-here.csv"

            settings = _settings(deployment_mode=PUBLIC_DEMO, embeddings_path=missing)
            state = ReadinessState(settings)
            evaluate_manifest(state, settings, root)

            detail = next(
                c["detail"]
                for c in state.snapshot()["checks"]
                if c["name"] == "embedding_artifact"
            )
            self.assertIn("not-here.csv", detail)

    def test_a_matching_artifact_passes_and_records_the_corpus_version(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._manifest_dir(Path(directory))
            artifact = root / "thoughtmap_canonical_embeddings.csv"
            artifact.write_bytes(b"x" * 32)

            settings = _settings(deployment_mode=PUBLIC_DEMO, embeddings_path=artifact)
            state = ReadinessState(settings)
            state.set("configuration", OK)
            evaluate_manifest(state, settings, root)

            snapshot = state.snapshot()
            self.assertTrue(snapshot["ready"])
            self.assertEqual(snapshot["corpus_version"], "20260909")
            self.assertEqual(snapshot["document_count"], 63891)


class WarmupTests(unittest.TestCase):
    def test_warmup_off_defers_rather_than_failing(self) -> None:
        settings = _settings(warmup=WARMUP_OFF)
        state = ReadinessState(settings)
        state.set("configuration", OK)
        run_warmup(state, settings, lambda: [], lambda: None)

        statuses = {c["name"]: c["status"] for c in state.snapshot()["checks"]}
        self.assertEqual(statuses["search_engine"], DEFERRED)
        self.assertEqual(statuses["embedding_model"], DEFERRED)
        self.assertTrue(state.ready)

    def test_full_warmup_records_both_stages(self) -> None:
        settings = _settings(warmup=WARMUP_FULL)
        state = ReadinessState(settings)
        state.set("configuration", OK)
        run_warmup(state, settings, lambda: [1, 2, 3], lambda: object())

        snapshot = state.snapshot()
        self.assertTrue(snapshot["ready"])
        self.assertIn("corpus_load", snapshot["startup_ms"])
        self.assertIn("model_load", snapshot["startup_ms"])

    def test_a_corpus_failure_is_recorded_not_raised(self) -> None:
        # A process that cannot load the corpus must stay up and explain
        # itself, so an operator can read /ready instead of a crash loop.
        def explode():
            raise RuntimeError("artifact missing")

        settings = _settings(warmup=WARMUP_FULL)
        state = ReadinessState(settings)
        run_warmup(state, settings, explode, lambda: object())

        snapshot = state.snapshot()
        self.assertFalse(snapshot["ready"])
        self.assertIn("search_engine", snapshot["blocked_by"])

    def test_a_model_failure_blocks_a_public_deployment(self) -> None:
        def explode():
            raise RuntimeError("no torch")

        settings = _settings(warmup=WARMUP_FULL, deployment_mode=PUBLIC_DEMO)
        state = ReadinessState(settings)
        state.set("configuration", OK)
        run_warmup(state, settings, lambda: [1], explode)

        self.assertFalse(state.ready)

    def test_a_model_failure_only_defers_in_development(self) -> None:
        # Keyword search still works, so locally this is a capability gap.
        def explode():
            raise RuntimeError("no torch")

        settings = _settings(warmup=WARMUP_FULL, deployment_mode=DEVELOPMENT)
        state = ReadinessState(settings)
        state.set("configuration", OK)
        run_warmup(state, settings, lambda: [1], explode)

        self.assertTrue(state.ready)


class WarmupSideEffectTests(unittest.TestCase):
    """Two things warmup does besides loading: prepare /map, and trim.

    Both exist for memory, and both must be unable to break a start. A /map
    artifact that cannot be read is a 503 on one endpoint; a warmup that
    raised because of it would be a dead instance.
    """

    def test_the_map_payload_is_prepared_during_warmup(self) -> None:
        # Otherwise the first visitor pays a 12 MB parse and a gzip, at the
        # same moment as a cold instance's first burst of traffic.
        prepared = []
        settings = _settings(warmup=WARMUP_FULL)
        state = ReadinessState(settings)
        state.set("configuration", OK)

        run_warmup(
            state, settings, lambda: [1], lambda: object(), lambda: prepared.append(1)
        )

        self.assertEqual(prepared, [1])
        self.assertIn("map_payload", state.snapshot()["startup_ms"])

    def test_a_map_failure_does_not_block_readiness(self) -> None:
        def explode():
            raise RuntimeError("projection not generated")

        settings = _settings(warmup=WARMUP_FULL, deployment_mode=PUBLIC_DEMO)
        state = ReadinessState(settings)
        state.set("configuration", OK)

        run_warmup(state, settings, lambda: [1], lambda: object(), explode)

        # Search works without a projection; /map answers 503 with a reason.
        self.assertTrue(state.ready)

    def test_nothing_is_prepared_when_warmup_is_off(self) -> None:
        prepared = []
        settings = _settings(warmup=WARMUP_OFF)
        state = ReadinessState(settings)
        state.set("configuration", OK)

        run_warmup(
            state, settings, lambda: [], lambda: None, lambda: prepared.append(1)
        )

        self.assertEqual(prepared, [])

    def test_warmup_completes_without_a_map_preparer(self) -> None:
        # The argument is optional, and every existing caller omits it.
        settings = _settings(warmup=WARMUP_FULL)
        state = ReadinessState(settings)
        state.set("configuration", OK)

        run_warmup(state, settings, lambda: [1], lambda: object())

        self.assertTrue(state.ready)

    def test_the_heap_trim_is_safe_on_every_platform(self) -> None:
        # Returns False rather than raising where there is no malloc_trim, and
        # never touches live objects where there is.
        from api.process_memory import release_free_heap

        first = release_free_heap()
        second = release_free_heap()

        self.assertIsInstance(first, bool)
        self.assertEqual(first, second)
        if not sys.platform.startswith("linux"):
            self.assertFalse(first, "only glibc can return free heap to the OS")


class HeapTrimVerifierTests(unittest.TestCase):
    def test_it_refuses_to_report_a_number_it_cannot_measure(self) -> None:
        # A trim figure from a platform that cannot trim would be quoted later
        # as if it meant something.
        from api.verify_heap_trim import main

        if sys.platform.startswith("linux"):
            self.skipTest("this platform can trim; nothing to refuse")
        self.assertEqual(main(["--limit-mb", "512"]), 2)


class MapResponseCacheTests(unittest.TestCase):
    def artifact(self, fingerprint: str = "abc123", nodes: int = 3) -> dict:
        return {
            "schema_version": 1,
            "projection": {"dataset_fingerprint": fingerprint},
            "nodes": [{"doc_id": f"doc_{i}", "x": 0.0, "y": 0.0, "z": 0.0} for i in range(nodes)],
        }

    def test_encodes_once_per_fingerprint(self) -> None:
        cache = MapResponseCache()
        first = cache.get(self.artifact())
        second = cache.get(self.artifact())
        self.assertIs(first, second)

    def test_a_new_fingerprint_replaces_the_payload(self) -> None:
        # A regenerated projection must take effect without a restart.
        cache = MapResponseCache()
        first = cache.get(self.artifact("aaa", nodes=3))
        second = cache.get(self.artifact("bbb", nodes=5))

        self.assertIsNot(first, second)
        self.assertEqual(second.node_count, 5)
        self.assertNotEqual(first.etag, second.etag)

    def test_the_gzip_body_decodes_to_the_raw_body(self) -> None:
        cache = MapResponseCache()
        encoded = cache.get(self.artifact())
        self.assertEqual(gzip.decompress(encoded.gzipped), encoded.raw)

    def test_the_payload_round_trips_as_json(self) -> None:
        cache = MapResponseCache()
        artifact = self.artifact()
        encoded = cache.get(artifact)
        self.assertEqual(json.loads(encoded.raw), artifact)

    def test_the_etag_is_derived_from_the_fingerprint(self) -> None:
        cache = MapResponseCache()
        encoded = cache.get(self.artifact("ce109523a9cd9962"))
        self.assertIn("ce109523a9cd9962", encoded.etag)

    def test_no_fingerprint_means_no_etag(self) -> None:
        # Better no validator than one that cannot detect a change.
        cache = MapResponseCache()
        encoded = cache.get(self.artifact(""))
        self.assertEqual(encoded.etag, "")

    def test_accepts_gzip_reads_the_header(self) -> None:
        self.assertTrue(accepts_gzip("gzip, deflate, br"))
        self.assertTrue(accepts_gzip("GZIP"))
        self.assertFalse(accepts_gzip("br"))
        self.assertFalse(accepts_gzip(""))


if __name__ == "__main__":
    unittest.main()


class LogRedactionTests(unittest.TestCase):
    """Access logs must not become a record of who searched for what.

    The application's own structured events were already careful. The gap this
    covers is uvicorn's access log, which records the full request target -
    including the search text and a Personal Library address - and which no
    amount of care in `log_event` affects (T7 §36).
    """

    def test_search_text_is_removed(self) -> None:
        from api.observability import redact_query_string

        redacted = redact_query_string("/search?q=Plato%20and%20the%20soul&mode=semantic")
        self.assertNotIn("Plato", redacted)
        self.assertIn("q=<redacted>", redacted)
        # The shape stays useful: endpoint and non-sensitive parameters remain.
        self.assertIn("/search", redacted)
        self.assertIn("mode=semantic", redacted)

    def test_library_identity_is_removed(self) -> None:
        from api.observability import redact_query_string

        redacted = redact_query_string("/users/by-email/saved?email=someone@example.invalid")
        self.assertNotIn("someone", redacted)
        self.assertNotIn("@example.invalid", redacted)
        self.assertIn("email=<redacted>", redacted)

    def test_every_sensitive_parameter_is_covered(self) -> None:
        from api.observability import REDACTED_PARAMETERS, redact_query_string

        query = "&".join(f"{name}=secret{i}" for i, name in enumerate(REDACTED_PARAMETERS))
        redacted = redact_query_string(f"/search?{query}")
        self.assertNotIn("secret", redacted)

    def test_paths_without_a_query_string_are_untouched(self) -> None:
        from api.observability import redact_query_string

        self.assertEqual(redact_query_string("/health"), "/health")
        self.assertEqual(redact_query_string("/map"), "/map")

    def test_the_filter_rewrites_a_uvicorn_access_record(self) -> None:
        import logging as logging_module

        from api.observability import RedactAccessLogFilter

        record = logging_module.LogRecord(
            name="uvicorn.access",
            level=logging_module.INFO,
            pathname=__file__,
            lineno=1,
            msg='%s - "%s %s HTTP/%s" %d',
            args=("127.0.0.1:1", "GET", "/search?q=private+words", "1.1", 200),
            exc_info=None,
        )

        RedactAccessLogFilter().filter(record)

        self.assertNotIn("private", record.getMessage())
        self.assertIn("<redacted>", record.getMessage())

    def test_the_filter_never_drops_a_record(self) -> None:
        # It is a redactor, not a suppressor: operators still need the line.
        import logging as logging_module

        from api.observability import RedactAccessLogFilter

        record = logging_module.LogRecord(
            name="uvicorn.access", level=logging_module.INFO, pathname=__file__,
            lineno=1, msg="something else", args=None, exc_info=None,
        )
        self.assertTrue(RedactAccessLogFilter().filter(record))

    def test_installation_is_idempotent(self) -> None:
        import logging as logging_module

        from api.observability import RedactAccessLogFilter, install_access_log_redaction

        access = logging_module.getLogger("uvicorn.access")
        before = len(access.filters)
        install_access_log_redaction()
        install_access_log_redaction()
        installed = [f for f in access.filters if isinstance(f, RedactAccessLogFilter)]
        self.assertEqual(len(installed), 1)
        self.assertLessEqual(len(access.filters), before + 1)
