"""Tests for the 3D projection pipeline and the read-only /map endpoint.

The generator is tested separately from HTTP. A small synthetic corpus keeps
the suite fast; UMAP itself is only exercised where determinism is the point.
"""

from __future__ import annotations

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

    def test_parses_once_for_an_unchanged_file(self) -> None:
        artifact, _ = ProjectionGenerator(lambda: make_frame(), SMALL_CONFIG).generate()

        with TemporaryDirectory() as directory:
            path = Path(directory) / "map.json"
            write_artifact(artifact, path)
            service = MapService(path)

            with mock.patch("api.map_service.read_artifact", wraps=read_artifact) as spy:
                first = service.load()
                second = service.load()
                third = service.load()

            self.assertIs(first, second)
            self.assertIs(second, third)
            self.assertEqual(spy.call_count, 1)

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


if __name__ == "__main__":
    unittest.main()
