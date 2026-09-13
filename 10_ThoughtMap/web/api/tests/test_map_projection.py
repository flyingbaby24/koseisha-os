"""Tests for the 3D projection pipeline and the read-only /map endpoint.

The generator is tested separately from HTTP. A small synthetic corpus keeps
the suite fast; UMAP itself is only exercised where determinism is the point.
"""

from __future__ import annotations

import gzip
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from api import main as api_main
from api.map_projection import (
    PROJECTION_SCHEMA_VERSION,
    ProjectionConfig,
    ProjectionError,
    ProjectionGenerator,
    compute_dataset_fingerprint,
    read_artifact,
    validate_artifact,
    write_artifact,
)
from api.config import DEVELOPMENT, PUBLIC_DEMO
from api.map_service import MapService, ProjectionUnavailableError


def make_frame(count: int = 40, dimension: int = 12, seed: int = 7) -> pd.DataFrame:
    """A synthetic corpus with clearly separated groups, so UMAP behaves."""
    rng = np.random.default_rng(seed)
    rows = []
    for index in range(count):
        group = index % 4
        centre = np.zeros(dimension, dtype=np.float32)
        centre[group] = 5.0
        vector = centre + rng.normal(scale=0.35, size=dimension).astype(np.float32)
        rows.append(
            {
                "doc_id": f"src{group}:doc_{index:04d}",
                "title": f"Document {index}",
                "author": f"Author {group}",
                "source": ["gutendex", "user_suno", "user_note", "zip"][group],
                "_embedding_vec": vector,
            }
        )
    return pd.DataFrame(rows)


SMALL_CONFIG = ProjectionConfig(n_neighbors=5, cluster_count=4)


class FingerprintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = make_frame()
        self.doc_ids = self.frame["doc_id"].tolist()
        self.vectors = self.frame["_embedding_vec"].tolist()

    def fingerprint(self, doc_ids=None, vectors=None, config=None) -> str:
        return compute_dataset_fingerprint(
            doc_ids if doc_ids is not None else self.doc_ids,
            vectors if vectors is not None else self.vectors,
            config or SMALL_CONFIG,
        )

    def test_is_stable_for_identical_inputs(self) -> None:
        self.assertEqual(self.fingerprint(), self.fingerprint())

    def test_is_independent_of_row_order(self) -> None:
        order = list(range(len(self.doc_ids)))[::-1]
        shuffled_ids = [self.doc_ids[i] for i in order]
        shuffled_vectors = [self.vectors[i] for i in order]
        self.assertEqual(self.fingerprint(), self.fingerprint(shuffled_ids, shuffled_vectors))

    def test_detects_a_changed_document_identity(self) -> None:
        changed = list(self.doc_ids)
        changed[0] = "renamed:doc_0000"
        self.assertNotEqual(self.fingerprint(), self.fingerprint(doc_ids=changed))

    def test_detects_a_changed_embedding(self) -> None:
        changed = [vector.copy() for vector in self.vectors]
        changed[3] = changed[3] + np.float32(0.001)
        self.assertNotEqual(self.fingerprint(), self.fingerprint(vectors=changed))

    def test_detects_an_added_document(self) -> None:
        self.assertNotEqual(
            self.fingerprint(),
            self.fingerprint(
                doc_ids=[*self.doc_ids, "extra:doc_9999"],
                vectors=[*self.vectors, self.vectors[0].copy()],
            ),
        )

    def test_detects_a_changed_projection_config(self) -> None:
        for changed in (
            ProjectionConfig(n_neighbors=6, cluster_count=4),
            ProjectionConfig(n_neighbors=5, cluster_count=4, min_dist=0.3),
            ProjectionConfig(n_neighbors=5, cluster_count=4, random_seed=1),
            ProjectionConfig(n_neighbors=5, cluster_count=4, metric="euclidean"),
            ProjectionConfig(n_neighbors=5, cluster_count=4, n_components=2),
        ):
            with self.subTest(config=changed):
                self.assertNotEqual(self.fingerprint(), self.fingerprint(config=changed))

    def test_ignores_display_metadata_that_cannot_move_a_node(self) -> None:
        # Title and author are carried in the artifact but never reach the
        # projection, so they are deliberately outside the fingerprint.
        renamed = self.frame.copy()
        renamed["title"] = "Retitled"
        renamed["author"] = "Someone Else"
        self.assertEqual(
            self.fingerprint(),
            compute_dataset_fingerprint(
                renamed["doc_id"].tolist(), renamed["_embedding_vec"].tolist(), SMALL_CONFIG
            ),
        )


class GeneratorTests(unittest.TestCase):
    def generate(self, frame: pd.DataFrame | None = None, config: ProjectionConfig | None = None):
        source = frame if frame is not None else make_frame()
        generator = ProjectionGenerator(lambda: source, config or SMALL_CONFIG)
        return generator.generate()

    def test_projects_every_document(self) -> None:
        frame = make_frame(count=40)
        artifact, stats = self.generate(frame)

        self.assertEqual(len(artifact["nodes"]), 40)
        self.assertEqual(artifact["projection"]["document_count"], 40)
        self.assertEqual(stats.document_count, 40)
        self.assertEqual(
            {node["doc_id"] for node in artifact["nodes"]},
            set(frame["doc_id"]),
        )

    def test_produces_three_finite_coordinates_per_node(self) -> None:
        artifact, _ = self.generate()
        for node in artifact["nodes"]:
            for axis in ("x", "y", "z"):
                self.assertTrue(np.isfinite(node[axis]), f"{node['doc_id']}.{axis}")

    def test_records_the_full_projection_configuration(self) -> None:
        artifact, _ = self.generate()
        projection = artifact["projection"]

        self.assertEqual(artifact["schema_version"], PROJECTION_SCHEMA_VERSION)
        self.assertEqual(projection["algorithm"], "umap")
        self.assertEqual(projection["n_components"], 3)
        self.assertEqual(projection["metric"], "cosine")
        self.assertEqual(projection["min_dist"], 0.2)
        self.assertEqual(projection["random_seed"], 42)
        self.assertEqual(projection["embedding_dimension"], 12)
        self.assertIn("generated_at", projection)
        self.assertIn("dataset_fingerprint", projection)

    def test_is_deterministic_across_runs(self) -> None:
        # The core reproducibility guarantee: same data, same config, same seed.
        frame = make_frame()
        first, _ = self.generate(frame)
        second, _ = self.generate(frame)

        self.assertEqual(
            first["projection"]["dataset_fingerprint"],
            second["projection"]["dataset_fingerprint"],
        )

        for a, b in zip(first["nodes"], second["nodes"]):
            self.assertEqual(a["doc_id"], b["doc_id"])
            for axis in ("x", "y", "z"):
                self.assertAlmostEqual(a[axis], b[axis], places=5, msg=f"{a['doc_id']}.{axis}")

    def test_is_independent_of_input_row_order(self) -> None:
        frame = make_frame()
        shuffled = frame.iloc[::-1].reset_index(drop=True)

        ordered, _ = self.generate(frame)
        reversed_run, _ = self.generate(shuffled)

        self.assertEqual(
            ordered["projection"]["dataset_fingerprint"],
            reversed_run["projection"]["dataset_fingerprint"],
        )
        self.assertEqual(
            [node["doc_id"] for node in ordered["nodes"]],
            [node["doc_id"] for node in reversed_run["nodes"]],
        )

    def test_assigns_clusters_when_configured(self) -> None:
        artifact, stats = self.generate()
        clusters = {node["cluster"] for node in artifact["nodes"]}
        self.assertTrue(clusters <= {0, 1, 2, 3})
        self.assertEqual(sum(stats.cluster_populations.values()), len(artifact["nodes"]))

    def test_cluster_is_null_when_clustering_is_disabled(self) -> None:
        config = ProjectionConfig(n_neighbors=5, cluster_algorithm=None, cluster_count=None)
        artifact, stats = self.generate(config=config)

        self.assertTrue(all(node["cluster"] is None for node in artifact["nodes"]))
        self.assertEqual(stats.cluster_populations, {})

    def test_reports_coordinate_bounds_and_diagnostics(self) -> None:
        _, stats = self.generate()
        for axis in ("x", "y", "z"):
            low, high = stats.bounds[axis]
            self.assertLessEqual(low, high)
            self.assertTrue(np.isfinite(low) and np.isfinite(high))
        self.assertGreater(stats.bounding_sphere_radius, 0)

    def test_rejects_an_empty_index(self) -> None:
        with self.assertRaises(ProjectionError):
            ProjectionGenerator(lambda: pd.DataFrame(), SMALL_CONFIG).generate()

    def test_rejects_duplicate_doc_ids(self) -> None:
        frame = make_frame(count=12)
        frame.loc[1, "doc_id"] = frame.loc[0, "doc_id"]
        with self.assertRaises(ProjectionError) as caught:
            self.generate(frame)
        self.assertIn("duplicate", str(caught.exception).lower())

    def test_rejects_a_blank_doc_id(self) -> None:
        frame = make_frame(count=12)
        frame.loc[2, "doc_id"] = "   "
        with self.assertRaises(ProjectionError) as caught:
            self.generate(frame)
        self.assertIn("blank", str(caught.exception).lower())

    def test_rejects_inconsistent_embedding_dimensions(self) -> None:
        frame = make_frame(count=12)
        frame.at[3, "_embedding_vec"] = np.zeros(5, dtype=np.float32)
        with self.assertRaises(ProjectionError) as caught:
            self.generate(frame)
        self.assertIn("dimension", str(caught.exception).lower())

    def test_rejects_non_finite_embeddings(self) -> None:
        frame = make_frame(count=12)
        broken = frame.at[3, "_embedding_vec"].copy()
        broken[0] = np.nan
        frame.at[3, "_embedding_vec"] = broken
        with self.assertRaises(ProjectionError):
            self.generate(frame)


class ValidationTests(unittest.TestCase):
    def valid_artifact(self) -> dict:
        return {
            "schema_version": PROJECTION_SCHEMA_VERSION,
            "projection": {
                "generated_at": "2026-09-09T00:00:00+00:00",
                "dataset_fingerprint": "abc123",
                "document_count": 2,
                "embedding_dimension": 384,
                "dimensions": 3,
                "algorithm": "umap",
                "n_components": 3,
                "metric": "cosine",
                "n_neighbors": 10,
                "min_dist": 0.2,
                "random_seed": 42,
            },
            "nodes": [
                {"doc_id": "a", "title": "A", "author": "", "source": "gutendex", "x": 0.0, "y": 0.0, "z": 0.0, "cluster": 0},
                {"doc_id": "b", "title": "B", "author": "", "source": "zip", "x": 1.0, "y": 2.0, "z": 3.0, "cluster": 1},
            ],
        }

    def test_accepts_a_well_formed_artifact(self) -> None:
        validate_artifact(self.valid_artifact())

    def test_rejects_an_unsupported_schema_version(self) -> None:
        artifact = self.valid_artifact()
        artifact["schema_version"] = 99
        with self.assertRaises(ProjectionError):
            validate_artifact(artifact)

    def test_rejects_missing_metadata(self) -> None:
        artifact = self.valid_artifact()
        del artifact["projection"]["random_seed"]
        with self.assertRaises(ProjectionError):
            validate_artifact(artifact)

    def test_rejects_no_nodes(self) -> None:
        artifact = self.valid_artifact()
        artifact["nodes"] = []
        with self.assertRaises(ProjectionError):
            validate_artifact(artifact)

    def test_rejects_duplicate_doc_ids(self) -> None:
        artifact = self.valid_artifact()
        artifact["nodes"][1]["doc_id"] = "a"
        with self.assertRaises(ProjectionError):
            validate_artifact(artifact)

    def test_rejects_nan_and_infinity(self) -> None:
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=bad):
                artifact = self.valid_artifact()
                artifact["nodes"][0]["x"] = bad
                with self.assertRaises(ProjectionError):
                    validate_artifact(artifact)

    def test_rejects_a_non_numeric_coordinate(self) -> None:
        artifact = self.valid_artifact()
        artifact["nodes"][0]["y"] = "0.5"
        with self.assertRaises(ProjectionError):
            validate_artifact(artifact)

    def test_rejects_two_documents_on_the_same_point(self) -> None:
        artifact = self.valid_artifact()
        artifact["nodes"][1]["x"] = 0.0
        artifact["nodes"][1]["y"] = 0.0
        artifact["nodes"][1]["z"] = 0.0
        with self.assertRaises(ProjectionError):
            validate_artifact(artifact)

    def test_rejects_a_count_that_disagrees_with_the_nodes(self) -> None:
        artifact = self.valid_artifact()
        artifact["projection"]["document_count"] = 5
        with self.assertRaises(ProjectionError):
            validate_artifact(artifact)


class ArtifactIoTests(unittest.TestCase):
    def test_writes_and_reads_back_an_artifact(self) -> None:
        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()

        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            written = write_artifact(artifact, path)
            self.assertTrue(written.exists())

            loaded = read_artifact(written)
            self.assertEqual(len(loaded["nodes"]), len(artifact["nodes"]))

    def test_leaves_no_temp_file_behind(self) -> None:
        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            write_artifact(artifact, path)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_a_failed_write_keeps_the_previous_artifact(self) -> None:
        good, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()

        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            write_artifact(good, path)
            original = path.read_text(encoding="utf-8")

            broken = {"schema_version": 99, "projection": {}, "nodes": []}
            with self.assertRaises(ProjectionError):
                write_artifact(broken, path)

            # Untouched, and no debris left next to it.
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_read_rejects_malformed_json(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ProjectionError):
                read_artifact(path)

    def test_read_reports_a_missing_artifact(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                read_artifact(Path(directory) / "absent.json")


class MapServiceTests(unittest.TestCase):
    def test_reports_a_missing_artifact_as_unavailable(self) -> None:
        with TemporaryDirectory() as directory:
            service = MapService(Path(directory) / "absent.json")
            with self.assertRaises(ProjectionUnavailableError) as caught:
                service.load()
            self.assertIn("generate_map_projection", str(caught.exception))

    def test_reports_a_malformed_artifact_as_unavailable(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            path.write_text('{"schema_version": 99}', encoding="utf-8")
            service = MapService(path)
            with self.assertRaises(ProjectionUnavailableError):
                service.load()

    def test_serving_never_parses_the_artifact(self) -> None:
        """The guarantee got stronger: not "parsed once" but "never parsed".

        It used to be parsed once per artifact version, to be turned into
        bytes. Those bytes are now produced by `write_artifact` at projection
        time, so a serving instance only opens files — which is the point, at
        63,891 nodes a parse is 37.5 MB of transient dicts.
        """
        from api.map_response_cache import MapResponseCache

        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()

        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            write_artifact(artifact, path)
            service = MapService(path)
            cache = MapResponseCache()

            with mock.patch("api.map_service.read_artifact", wraps=read_artifact) as spy:
                first = cache.get_for(service)
                second = cache.get_for(service)
                third = cache.get_for(service)

            self.assertIs(first, second)
            self.assertIs(second, third)
            self.assertEqual(spy.call_count, 0, "the artifact must not be parsed")

    def test_the_parsed_artifact_is_not_retained(self) -> None:
        """MapService must hand the dicts over and keep no reference.

        This is the whole point of the change: at full corpus size the parsed
        nodes are 37.5 MB, and nothing needs them after serialisation.
        """
        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()

        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            write_artifact(artifact, path)
            service = MapService(path)

            first = service.load()
            second = service.load()

            self.assertIsNot(first, second, "each load must return a fresh parse")
            # No attribute may hold a parsed artifact. `artifact_path` is a
            # Path and is fine; a dict or a list of nodes is not.
            retained = {
                name: type(value).__name__
                for name, value in vars(service).items()
                if isinstance(value, (dict, list))
            }
            self.assertEqual(retained, {}, f"MapService retained parsed data: {retained}")

    def test_the_response_cache_re_parses_a_regenerated_artifact(self) -> None:
        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()

        from api.map_response_cache import MapResponseCache

        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            write_artifact(artifact, path)
            service = MapService(path)
            cache = MapResponseCache()

            before = cache.get_for(service)

            # Regenerate with a different fingerprint and a different mtime.
            changed = dict(artifact)
            changed["projection"] = {
                **artifact["projection"],
                "dataset_fingerprint": "f" * 64,
            }
            import os
            import time

            write_artifact(changed, path)
            future = time.time() + 10
            os.utime(path, (future, future))

            after = cache.get_for(service)

            self.assertNotEqual(before.etag, after.etag)
            self.assertNotEqual(before.fingerprint, after.fingerprint)

    def test_picks_up_a_regenerated_artifact_without_a_restart(self) -> None:
        first_artifact, _ = ProjectionGenerator(lambda: make_frame(count=40), SMALL_CONFIG).generate()
        second_artifact, _ = ProjectionGenerator(lambda: make_frame(count=32), SMALL_CONFIG).generate()

        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            write_artifact(first_artifact, path)
            service = MapService(path)
            self.assertEqual(len(service.load()["nodes"]), 40)

            write_artifact(second_artifact, path)
            # Cache key includes size and mtime, so the new file is noticed.
            self.assertEqual(len(service.load()["nodes"]), 32)


class MapEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "map.json"
        self.client = TestClient(api_main.app)

    def install(self, artifact: dict) -> MapService:
        write_artifact(artifact, self.path)
        service = MapService(self.path)
        patcher = mock.patch.object(api_main, "get_map_service", return_value=service)
        patcher.start()
        self.addCleanup(patcher.stop)
        return service

    def generated(self, count: int = 40) -> dict:
        artifact, _ = ProjectionGenerator(lambda: make_frame(count=count), SMALL_CONFIG).generate()
        return artifact

    def test_returns_the_projection(self) -> None:
        self.install(self.generated())
        response = self.client.get("/map")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], PROJECTION_SCHEMA_VERSION)
        self.assertEqual(len(payload["nodes"]), 40)

    def test_metadata_shape_is_stable(self) -> None:
        self.install(self.generated())
        projection = self.client.get("/map").json()["projection"]

        for key in (
            "generated_at",
            "dataset_fingerprint",
            "document_count",
            "embedding_dimension",
            "dimensions",
            "algorithm",
            "metric",
            "n_neighbors",
            "min_dist",
            "random_seed",
        ):
            self.assertIn(key, projection)

    def test_node_shape_is_stable(self) -> None:
        self.install(self.generated())
        node = self.client.get("/map").json()["nodes"][0]

        self.assertEqual(
            set(node),
            {"doc_id", "title", "author", "source", "x", "y", "z", "cluster"},
        )
        # A map node is not a search result: no similarity, no parameters, no url.
        self.assertNotIn("similarity", node)
        self.assertNotIn("parameters", node)

    def test_doc_ids_are_unique_and_coordinates_finite(self) -> None:
        self.install(self.generated())
        nodes = self.client.get("/map").json()["nodes"]

        doc_ids = [node["doc_id"] for node in nodes]
        self.assertEqual(len(doc_ids), len(set(doc_ids)))

        for node in nodes:
            for axis in ("x", "y", "z"):
                self.assertTrue(np.isfinite(node[axis]))

    def test_missing_artifact_returns_503(self) -> None:
        service = MapService(Path(self.directory.name) / "absent.json")
        with mock.patch.object(api_main, "get_map_service", return_value=service):
            response = self.client.get("/map")

        self.assertEqual(response.status_code, 503)
        self.assertIn("generate_map_projection", response.json()["detail"])

    def test_malformed_artifact_returns_503(self) -> None:
        self.path.write_text('{"schema_version": 42, "nodes": []}', encoding="utf-8")
        service = MapService(self.path)
        with mock.patch.object(api_main, "get_map_service", return_value=service):
            response = self.client.get("/map")

        self.assertEqual(response.status_code, 503)

    def test_get_map_never_runs_umap(self) -> None:
        """The whole point of the artifact: no fitting inside a request."""
        self.install(self.generated())

        import umap

        with mock.patch.object(umap.UMAP, "fit_transform", side_effect=AssertionError("UMAP ran")):
            response = self.client.get("/map")

        self.assertEqual(response.status_code, 200)

    def test_search_is_unaffected_by_a_missing_projection(self) -> None:
        service = MapService(Path(self.directory.name) / "absent.json")
        with mock.patch.object(api_main, "get_map_service", return_value=service):
            self.assertEqual(self.client.get("/map").status_code, 503)
            # Text search must keep working when the map cannot be served.
            self.assertEqual(self.client.get("/health").status_code, 200)


class PreparedMapResponseTests(unittest.TestCase):
    """The `/map` payload is a release artifact, not a runtime computation.

    Producing it costs a 12 MB parse into ~37.5 MB of dicts plus a
    re-serialisation and a gzip: 87 MB of transient, measured, and the largest
    peak in a cold start. It is deterministic output of the projection, so
    `write_artifact` publishes it and a serving instance only opens it.
    """

    def setUp(self) -> None:
        from api.map_response_cache import MapResponseCache

        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "map.json"
        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()
        write_artifact(artifact, self.path)
        self.artifact = artifact
        self.service = MapService(self.path)
        self.cache = MapResponseCache()

    def gzip_path(self) -> Path:
        from api.map_projection import gzip_path_for

        return gzip_path_for(self.path)

    def meta_path(self) -> Path:
        from api.map_projection import meta_path_for

        return meta_path_for(self.path)

    # --- generation -------------------------------------------------------

    def test_generation_publishes_the_response(self) -> None:
        self.assertTrue(self.gzip_path().exists())
        self.assertTrue(self.meta_path().exists())

    def test_the_gzip_decompresses_to_the_artifact(self) -> None:
        self.assertEqual(
            gzip.decompress(self.gzip_path().read_bytes()), self.path.read_bytes()
        )

    def test_the_metadata_records_what_it_was_built_from(self) -> None:
        import hashlib

        meta = json.loads(self.meta_path().read_text(encoding="utf-8"))
        raw = self.path.read_bytes()

        self.assertEqual(
            meta["fingerprint"], self.artifact["projection"]["dataset_fingerprint"]
        )
        self.assertEqual(meta["node_count"], len(self.artifact["nodes"]))
        self.assertEqual(meta["raw_size"], len(raw))
        self.assertEqual(meta["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(
            meta["gzip_sha256"],
            hashlib.sha256(self.gzip_path().read_bytes()).hexdigest(),
        )

    def test_sidecars_can_be_suppressed_for_a_test_artifact(self) -> None:
        path = Path(self.directory.name) / "bare.json"
        write_artifact(self.artifact, path, sidecars=False)

        from api.map_projection import gzip_path_for

        self.assertTrue(path.exists())
        self.assertFalse(gzip_path_for(path).exists())

    def test_a_failed_write_publishes_nothing(self) -> None:
        # The artifact is replaced last, so a crash while writing the response
        # leaves the previous artifact and its previous response in place.
        path = Path(self.directory.name) / "doomed.json"
        with mock.patch(
            "api.map_projection.write_map_sidecars", side_effect=OSError("disk full")
        ):
            with self.assertRaises(OSError):
                write_artifact(self.artifact, path)

        self.assertFalse(path.exists())
        self.assertFalse(list(Path(self.directory.name).glob("doomed.json.tmp*")))

    # --- serving ----------------------------------------------------------

    def test_serving_opens_the_prepared_files(self) -> None:
        encoded = self.cache.get_for(self.service)

        self.assertTrue(encoded.on_disk)
        self.assertIsNone(encoded.raw, "raw bytes must not be held in memory")
        self.assertIsNone(encoded.gzipped, "gzipped bytes must not be held in memory")
        self.assertEqual(encoded.raw_path, self.path)
        self.assertEqual(encoded.gzip_path, self.gzip_path())

    def test_the_artifact_itself_is_the_identity_response(self) -> None:
        # `write_artifact` writes compact JSON, so there is no second copy of
        # the uncompressed payload anywhere.
        encoded = self.cache.get_for(self.service)

        self.assertEqual(encoded.raw_size, self.path.stat().st_size)

    def test_a_fresh_process_serves_without_parsing(self) -> None:
        from api.map_response_cache import MapResponseCache

        with mock.patch("api.map_service.read_artifact") as spy:
            encoded = MapResponseCache().get_for(MapService(self.path))

        spy.assert_not_called()
        self.assertTrue(encoded.on_disk)
        self.assertEqual(
            encoded.fingerprint, self.artifact["projection"]["dataset_fingerprint"]
        )

    # --- validity is tied to content, not timestamps ----------------------

    def test_a_copied_artifact_is_still_valid(self) -> None:
        # Copying to a server changes every timestamp and no bytes. An
        # mtime-keyed check would reject this; a checksum does not.
        import os
        import time as time_module

        from api.map_response_cache import MapResponseCache

        future = time_module.time() + 10_000
        os.utime(self.path, (future, future))
        os.utime(self.gzip_path(), (future, future))

        encoded = MapResponseCache().get_for(MapService(self.path))

        self.assertTrue(encoded.on_disk)

    def test_a_regenerated_projection_republishes_the_response(self) -> None:
        changed = dict(self.artifact)
        changed["projection"] = {
            **self.artifact["projection"],
            "dataset_fingerprint": "f" * 64,
        }
        write_artifact(changed, self.path)

        from api.map_response_cache import MapResponseCache

        encoded = MapResponseCache().get_for(MapService(self.path))

        self.assertEqual(encoded.fingerprint, "f" * 64)
        self.assertEqual(
            gzip.decompress(self.gzip_path().read_bytes()), self.path.read_bytes()
        )

    # --- refusal ----------------------------------------------------------

    def assert_public_refuses(self, expected: str) -> None:
        from api.map_response_cache import MapPayloadUnavailableError, MapResponseCache

        cache = MapResponseCache(allow_rebuild=False)
        with self.assertRaises(MapPayloadUnavailableError) as caught:
            cache.get_for(MapService(self.path))

        message = str(caught.exception)
        self.assertIn(expected, message)
        # Every refusal names the command that fixes it.
        self.assertIn("prepare_map_sidecars", message)

    def test_a_public_deployment_refuses_a_missing_response(self) -> None:
        self.gzip_path().unlink()
        self.meta_path().unlink()
        self.assert_public_refuses("No prepared /map response")

    def test_a_public_deployment_refuses_a_missing_gzip(self) -> None:
        self.gzip_path().unlink()
        self.assert_public_refuses("missing")

    def test_a_public_deployment_refuses_a_corrupt_gzip(self) -> None:
        # Same length, different bytes: only the checksum catches this.
        payload = self.gzip_path().read_bytes()
        self.gzip_path().write_bytes(b"\x00" * len(payload))
        self.assert_public_refuses("corrupt")

    def test_a_public_deployment_refuses_a_stale_response(self) -> None:
        self.path.write_bytes(self.path.read_bytes() + b" ")
        self.assert_public_refuses("stale")

    def test_a_public_deployment_refuses_unreadable_metadata(self) -> None:
        self.meta_path().write_text("{ not json", encoding="utf-8")
        self.assert_public_refuses("No prepared /map response")

    def test_a_public_deployment_refuses_a_future_sidecar_version(self) -> None:
        meta = json.loads(self.meta_path().read_text(encoding="utf-8"))
        meta["sidecar_version"] = 99
        self.meta_path().write_text(json.dumps(meta), encoding="utf-8")
        self.assert_public_refuses("sidecar version")

    def test_a_public_deployment_refuses_a_response_with_no_fingerprint(self) -> None:
        # Without one the ETag would be empty and every browser would refetch
        # 3.7 MB on every visit.
        meta = json.loads(self.meta_path().read_text(encoding="utf-8"))
        meta["fingerprint"] = ""
        self.meta_path().write_text(json.dumps(meta), encoding="utf-8")
        self.assert_public_refuses("fingerprint")

    def test_development_rebuilds_in_memory_and_still_serves(self) -> None:
        # The escape hatch, and only here: a hand-built artifact still works
        # locally, at the cost the sidecar exists to avoid.
        from api.map_response_cache import MapResponseCache

        self.gzip_path().unlink()
        self.meta_path().unlink()

        cache = MapResponseCache(allow_rebuild=True)
        with self.assertLogs("thoughtmap.map", level="WARNING") as logs:
            encoded = cache.get_for(MapService(self.path))

        self.assertFalse(encoded.on_disk)
        self.assertEqual(encoded.raw, self.path.read_bytes())
        self.assertIn("prepare_map_sidecars", "".join(logs.output))


class ProjectionReadinessTests(unittest.TestCase):
    """A public instance must refuse to start rather than rebuild in RAM.

    Rebuilding costs 87 MB of transient. An instance that does it quietly
    looks healthy right up to the moment the platform kills it, which is the
    worst possible way to find out.
    """

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "map.json"
        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()
        write_artifact(artifact, self.path)
        self.nodes = len(artifact["nodes"])

    def check(self, mode: str):
        from api import config as config_module
        from api.config import get_settings
        from api.readiness import ReadinessState, evaluate_projection

        import os

        removed = {
            k: os.environ.pop(k) for k in list(os.environ) if k.startswith("THOUGHTMAP_")
        }
        try:
            base = get_settings()
        finally:
            os.environ.update(removed)
        settings = config_module.ApiSettings(
            **{**base.__dict__, "deployment_mode": mode}
        )

        state = ReadinessState(settings)
        evaluate_projection(state, settings, self.path, 0)
        return next(
            c for c in state.snapshot()["checks"] if c["name"] == "map_projection"
        )

    def test_a_prepared_projection_is_ready(self) -> None:
        from api.readiness import OK

        check = self.check(PUBLIC_DEMO)

        self.assertEqual(check["status"], OK)
        self.assertEqual(check["nodes"], self.nodes)
        self.assertTrue(check["fingerprint"])

    def test_readiness_does_not_parse_the_projection(self) -> None:
        # The node count comes from the sidecar. Parsing here would reintroduce
        # the transient on a second code path.
        with mock.patch("api.map_projection.read_artifact") as spy:
            self.check(PUBLIC_DEMO)
        spy.assert_not_called()

    def test_a_missing_response_fails_a_public_deployment(self) -> None:
        from api.map_projection import gzip_path_for, meta_path_for
        from api.readiness import FAILED

        gzip_path_for(self.path).unlink()
        meta_path_for(self.path).unlink()

        check = self.check(PUBLIC_DEMO)

        self.assertEqual(check["status"], FAILED)
        self.assertIn("prepare_map_sidecars", check["detail"])

    def test_a_stale_response_fails_a_public_deployment(self) -> None:
        from api.readiness import FAILED

        self.path.write_bytes(self.path.read_bytes() + b" ")

        check = self.check(PUBLIC_DEMO)

        self.assertEqual(check["status"], FAILED)
        self.assertIn("stale", check["detail"])

    def test_the_same_gap_only_defers_in_development(self) -> None:
        from api.map_projection import gzip_path_for, meta_path_for
        from api.readiness import DEFERRED

        gzip_path_for(self.path).unlink()
        meta_path_for(self.path).unlink()

        check = self.check(DEVELOPMENT)

        self.assertEqual(check["status"], DEFERRED)


class PrepareMapSidecarsCommandTests(unittest.TestCase):
    """The explicit rebuild, for artifacts that arrived without a response."""

    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "map.json"
        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()
        write_artifact(artifact, self.path, sidecars=False)
        self.artifact = artifact

    def run_command(self, *args: str) -> int:
        from api.prepare_map_sidecars import main

        return main(["--artifact", str(self.path), *args])

    def test_check_fails_before_the_response_exists(self) -> None:
        self.assertEqual(self.run_command("--check"), 1)

    def test_it_builds_a_valid_response(self) -> None:
        from api.map_projection import gzip_path_for, verify_map_sidecars

        self.assertEqual(self.run_command(), 0)

        meta, reason = verify_map_sidecars(self.path)
        self.assertIsNotNone(meta, reason)
        self.assertEqual(
            gzip.decompress(gzip_path_for(self.path).read_bytes()),
            self.path.read_bytes(),
        )

    def test_it_matches_what_generation_would_have_written(self) -> None:
        # The command and the generator must not diverge, or an artifact
        # repaired in the field would serve different bytes.
        from api.map_projection import gzip_path_for, meta_path_for

        # Deliberately cross a clock boundary: gzip headers must be stable.
        from unittest.mock import patch
        with patch("time.time", return_value=1000):
            self.run_command()
        by_command = gzip_path_for(self.path).read_bytes()
        command_meta = json.loads(meta_path_for(self.path).read_text(encoding="utf-8"))

        regenerated = Path(self.directory.name) / "regenerated.json"
        with patch("time.time", return_value=2000):
            write_artifact(self.artifact, regenerated)
        by_generator = gzip_path_for(regenerated).read_bytes()
        generator_meta = json.loads(
            meta_path_for(regenerated).read_text(encoding="utf-8")
        )

        self.assertEqual(by_command, by_generator)
        for field in ("fingerprint", "node_count", "raw_size", "raw_sha256",
                      "gzip_size", "gzip_sha256"):
            self.assertEqual(command_meta[field], generator_meta[field], field)

    def test_check_passes_once_it_is_built(self) -> None:
        self.run_command()
        self.assertEqual(self.run_command("--check"), 0)

    def test_a_second_run_is_a_no_op(self) -> None:
        self.run_command()
        from api.map_projection import meta_path_for

        before = meta_path_for(self.path).read_bytes()
        self.assertEqual(self.run_command(), 0)
        self.assertEqual(meta_path_for(self.path).read_bytes(), before)

    def test_force_rebuilds_an_already_valid_response(self) -> None:
        self.run_command()
        self.assertEqual(self.run_command("--force"), 0)
        from api.map_projection import verify_map_sidecars

        meta, reason = verify_map_sidecars(self.path)
        self.assertIsNotNone(meta, reason)

    def test_a_missing_artifact_is_an_error_not_a_traceback(self) -> None:
        from api.prepare_map_sidecars import main

        absent = Path(self.directory.name) / "absent.json"
        self.assertEqual(main(["--artifact", str(absent)]), 1)


class DiskBackedMapHttpTests(unittest.TestCase):
    """The same thing, through the real route."""

    def setUp(self) -> None:
        self.client = TestClient(api_main.app)
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "map.json"
        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()
        write_artifact(artifact, self.path)
        self.node_count = len(artifact["nodes"])
        api_main._map_cache.clear()
        self.addCleanup(api_main._map_cache.clear)
        self.patcher = mock.patch.object(
            api_main, "get_map_service", return_value=MapService(self.path)
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_gzip_clients_get_the_sidecar_and_it_decodes(self) -> None:
        response = self.client.get("/map", headers={"Accept-Encoding": "gzip"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
        self.assertEqual(response.headers.get("Vary"), "Accept-Encoding")
        self.assertEqual(len(response.json()["nodes"]), self.node_count)

    def test_identity_clients_get_the_artifact_itself(self) -> None:
        response = self.client.get("/map", headers={"Accept-Encoding": "identity"})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Content-Encoding", response.headers)
        self.assertEqual(response.content, self.path.read_bytes())

    def test_the_etag_survives_being_served_from_a_file(self) -> None:
        # FileResponse sets its own validators from the file's mtime. The
        # projection fingerprint has to win, or a re-projection that happened
        # to preserve mtime would be invisible to every cached browser.
        first = self.client.get("/map")
        etag = first.headers["ETag"]

        self.assertTrue(etag.startswith('W/"map-'))
        second = self.client.get("/map", headers={"If-None-Match": etag})
        self.assertEqual(second.status_code, 304)
        self.assertEqual(second.content, b"")

    def test_the_body_is_not_double_compressed(self) -> None:
        response = self.client.get("/map", headers={"Accept-Encoding": "gzip"})
        raw = response.read() if hasattr(response, "read") else response.content

        if response.headers.get("Content-Encoding") == "gzip":
            try:
                once = gzip.decompress(raw)
            except Exception:
                once = raw  # httpx already decoded it
            self.assertIsInstance(json.loads(once), dict)


if __name__ == "__main__":
    unittest.main()
