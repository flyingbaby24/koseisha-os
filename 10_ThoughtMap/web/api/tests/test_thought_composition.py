"""The Thought Composition arithmetic, and the dependency it must not have.

Two separate guarantees live here, and they fail for different reasons:

1. **The numbers.** `cosine_similarity` was scikit-learn's; it is now NumPy's.
   The values feed a user-visible radar, so they are compared against the real
   scikit-learn implementation wherever it is installed — which is CI, via
   `requirements-ci.txt`.

2. **The dependency.** scikit-learn is deliberately absent from the production
   runtime. When `thought_composition` imported it, the deployed public demo
   raised `ModuleNotFoundError` on every search, `query_profile` swallowed it,
   and `query_parameters` came back empty with a 200. Nothing failed loudly.
   That is the failure this file exists to make impossible to reintroduce.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np

from thought_composition import (
    THOUGHT_COMPOSITION_PARAMETERS,
    cosine_similarity,
    make_filter_scores,
)

try:
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine
except ImportError:  # production runtime, by design
    sklearn_cosine = None


class StubEncoder:
    """Returns fixed vectors, so only the arithmetic under test varies."""

    def __init__(self, vectors: np.ndarray) -> None:
        self._vectors = vectors

    def encode(self, texts, show_progress_bar: bool = False):
        return self._vectors


def categories() -> dict[str, str]:
    return {key: f"description of {key}" for key in THOUGHT_COMPOSITION_PARAMETERS}


class CosineSimilarityTests(unittest.TestCase):
    """Properties that hold with or without scikit-learn present."""

    def setUp(self) -> None:
        self.rng = np.random.default_rng(4242)

    def test_matches_a_hand_computed_value(self) -> None:
        # Orthogonal, identical and opposite rows: 0, 1, -1.
        x = np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
        y = np.array([[0.0, 1.0], [1.0, 0.0], [-1.0, 0.0]])

        result = cosine_similarity(x, y)

        self.assertAlmostEqual(result[0][0], 0.0, places=12)
        self.assertAlmostEqual(result[0][1], 1.0, places=12)
        self.assertAlmostEqual(result[0][2], -1.0, places=12)

    def test_scale_invariance(self) -> None:
        # Cosine ignores magnitude; a 1000x row must score identically.
        a = self.rng.standard_normal((3, 16))
        b = self.rng.standard_normal((4, 16))

        self.assertTrue(
            np.allclose(cosine_similarity(a, b), cosine_similarity(a * 1000.0, b))
        )

    def test_a_zero_row_scores_zero_rather_than_nan(self) -> None:
        # The degenerate case: a document with no embedding. Dividing by its
        # zero norm would give NaN, which would propagate into the radar.
        a = self.rng.standard_normal((2, 8))
        a[1] = 0.0
        b = self.rng.standard_normal((3, 8))

        result = cosine_similarity(a, b)

        self.assertFalse(np.isnan(result).any())
        self.assertTrue(np.all(result[1] == 0.0))

    def test_float32_inputs_stay_float32(self) -> None:
        # Matches scikit-learn's promotion rule. Query vectors are float32,
        # so this keeps the production path in the precision it was verified in.
        a = self.rng.standard_normal((2, 8), dtype=np.float32)
        self.assertEqual(cosine_similarity(a, a).dtype, np.float32)

    def test_mixed_precision_promotes_to_float64(self) -> None:
        a = self.rng.standard_normal((2, 8), dtype=np.float32)
        b = self.rng.standard_normal((2, 8))
        self.assertEqual(cosine_similarity(a, b).dtype, np.float64)

    def test_a_one_dimensional_input_is_treated_as_one_row(self) -> None:
        flat = self.rng.standard_normal(8)
        two_d = flat.reshape(1, -1)
        self.assertTrue(
            np.allclose(cosine_similarity(flat, two_d), cosine_similarity(two_d, two_d))
        )

    def test_mismatched_dimensions_raise(self) -> None:
        with self.assertRaises(ValueError):
            cosine_similarity(np.zeros((2, 8)), np.zeros((2, 9)))


@unittest.skipIf(sklearn_cosine is None, "scikit-learn not installed (production runtime)")
class MatchesScikitLearnTests(unittest.TestCase):
    """The replacement must not move the numbers."""

    def setUp(self) -> None:
        self.rng = np.random.default_rng(20260913)

    def assert_same(self, a, b, label: str) -> None:
        expected = sklearn_cosine(a, b)
        actual = cosine_similarity(a, b)
        self.assertEqual(actual.dtype, expected.dtype, f"{label}: dtype")
        self.assertTrue(
            np.array_equal(expected, actual),
            f"{label}: max abs delta "
            f"{np.max(np.abs(expected.astype(float) - actual.astype(float)))}",
        )

    def test_production_shape_one_query_ten_axes(self) -> None:
        self.assert_same(
            self.rng.standard_normal((1, 384), dtype=np.float32),
            self.rng.standard_normal((10, 384), dtype=np.float32),
            "1x384 vs 10x384",
        )

    def test_a_batch_of_documents(self) -> None:
        self.assert_same(
            self.rng.standard_normal((512, 384), dtype=np.float32),
            self.rng.standard_normal((10, 384), dtype=np.float32),
            "512x384 vs 10x384",
        )

    def test_zero_rows_on_both_sides(self) -> None:
        a = self.rng.standard_normal((6, 32), dtype=np.float32)
        a[3] = 0.0
        b = self.rng.standard_normal((10, 32), dtype=np.float32)
        b[7] = 0.0
        self.assert_same(a, b, "zero rows")

    def test_float64(self) -> None:
        self.assert_same(
            self.rng.standard_normal((8, 32)),
            self.rng.standard_normal((10, 32)),
            "float64",
        )

    def test_make_filter_scores_end_to_end(self) -> None:
        # The clip and the row normalisation after the similarity are where a
        # sign error or a zero row would actually surface.
        import thought_composition as module

        axes = self.rng.standard_normal((10, 384), dtype=np.float32)
        embeddings = self.rng.standard_normal((128, 384), dtype=np.float32)
        embeddings[2] = 0.0
        embeddings[3] = -axes.sum(axis=0) * 1000.0  # clips to all zeros

        with_numpy = make_filter_scores(embeddings, categories(), StubEncoder(axes))
        original = module.cosine_similarity
        try:
            module.cosine_similarity = sklearn_cosine
            with_sklearn = make_filter_scores(embeddings, categories(), StubEncoder(axes))
        finally:
            module.cosine_similarity = original

        self.assertEqual(list(with_numpy.columns), list(with_sklearn.columns))
        self.assertTrue(
            np.array_equal(with_numpy.to_numpy(), with_sklearn.to_numpy()),
            "make_filter_scores values diverged",
        )


class FilterScoreShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rng = np.random.default_rng(11)
        self.axes = self.rng.standard_normal((10, 64), dtype=np.float32)

    def test_ten_canonical_axes_in_canonical_order(self) -> None:
        frame = make_filter_scores(
            self.rng.standard_normal((5, 64), dtype=np.float32),
            categories(),
            StubEncoder(self.axes),
        )

        self.assertEqual(list(frame.columns), THOUGHT_COMPOSITION_PARAMETERS)
        self.assertEqual(len(frame.columns), 10)

    def test_scored_rows_sum_to_one(self) -> None:
        frame = make_filter_scores(
            self.rng.standard_normal((32, 64), dtype=np.float32),
            categories(),
            StubEncoder(self.axes),
        )

        sums = frame.to_numpy(dtype=np.float64).sum(axis=1)
        scored = sums[sums > 0]
        self.assertTrue(scored.size > 0)
        self.assertTrue(np.allclose(scored, 1.0, atol=1e-6))

    def test_a_row_with_no_affinity_stays_all_zero(self) -> None:
        # Canonical behaviour: clip to zero, then leave the row rather than
        # dividing by a zero total.
        embeddings = np.repeat(-self.axes.sum(axis=0)[None, :] * 1000.0, 2, axis=0)

        frame = make_filter_scores(embeddings, categories(), StubEncoder(self.axes))

        self.assertTrue(np.all(frame.to_numpy() == 0.0))

    def test_no_categories_returns_none(self) -> None:
        self.assertIsNone(make_filter_scores(np.zeros((2, 64)), {}, StubEncoder(self.axes)))


class ProductionDependencyTests(unittest.TestCase):
    """The guarantee that the deployed container can actually satisfy."""

    def test_query_radar_works_when_sklearn_is_unavailable(self) -> None:
        module_dir = Path(__file__).resolve().parents[2]
        probe = """
import sys
import importlib.abc
class NoSklearn(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] == 'sklearn':
            raise ModuleNotFoundError('sklearn deliberately blocked')
sys.meta_path.insert(0, NoSklearn())
import numpy as np
from api.query_profile import QueryProfileService
from thought_composition import THOUGHT_COMPOSITION_PARAMETERS
class Encoder:
    def encode(self, texts, show_progress_bar=False):
        return np.ones((len(texts), 384), dtype=np.float32)
profile = QueryProfileService(lambda: Encoder()).score_query('Plato')
assert profile is not None
assert [p.key for p in profile] == THOUGHT_COMPOSITION_PARAMETERS
assert all(np.isfinite(p.value) for p in profile)
assert abs(sum(p.value for p in profile) - 1.0) < 1e-6
assert not any(m.split('.')[0] == 'sklearn' for m in sys.modules)
"""
        result = subprocess.run([sys.executable, "-c", probe], cwd=module_dir,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])

    def test_importing_thought_composition_does_not_import_sklearn(self) -> None:
        # A subprocess, because scikit-learn is already imported in this one by
        # the comparison tests above. Asked as "what did the import pull in",
        # not "does the source mention sklearn" — the docstrings name it
        # deliberately and a grep would fail on the explanation.
        module_dir = Path(__file__).resolve().parents[2]
        probe = (
            "import sys;"
            f"sys.path.insert(0, {str(module_dir)!r});"
            "import thought_composition;"
            "print(','.join(sorted(m for m in sys.modules if m.split('.')[0] == 'sklearn')))"
        )

        result = subprocess.run(
            [sys.executable, "-c", probe], capture_output=True, text=True, timeout=120
        )

        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertEqual(
            result.stdout.strip(),
            "",
            "thought_composition pulled scikit-learn into the runtime; the "
            "production container does not install it and the query radar "
            "would silently return no profile.",
        )


if __name__ == "__main__":
    unittest.main()
