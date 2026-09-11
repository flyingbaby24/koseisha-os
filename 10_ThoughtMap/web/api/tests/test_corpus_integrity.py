"""Integrity guards for the recovered 63,891-document corpus.

These run against the real committed documents master, so they fail loudly if a
future import reintroduces the duplication pattern T4.5 uncovered.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import pandas as pd

from api.recover_full_corpus import (
    CANONICAL_MODEL,
    EXPECTED_DIMENSION,
    OFFICIAL_DIR,
    prefixed_doc_id,
)


DOCUMENTS = OFFICIAL_DIR / "documents_master.csv"
MANIFEST = OFFICIAL_DIR / "corpus_manifest.json"
PARAMETERS = OFFICIAL_DIR / "parameter_scores.csv"

EXPECTED_SOURCES = {
    "gutendex": 62306,
    "user_suno": 992,
    "user_note": 471,
    "zip": 122,
}
EXPECTED_TOTAL = sum(EXPECTED_SOURCES.values())  # 63,891


def load_documents() -> pd.DataFrame:
    return pd.read_csv(DOCUMENTS, dtype=str, encoding="utf-8-sig").fillna("")


class DocumentMasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not DOCUMENTS.exists():
            raise unittest.SkipTest("documents master not present")
        cls.documents = load_documents()

    def test_holds_the_full_recovered_corpus(self) -> None:
        self.assertEqual(len(self.documents), EXPECTED_TOTAL)

    def test_every_doc_id_is_unique(self) -> None:
        self.assertEqual(self.documents["doc_id"].nunique(), len(self.documents))

    def test_source_distribution_matches_the_recovery_plan(self) -> None:
        actual = {str(k): int(v) for k, v in self.documents["source"].value_counts().items()}
        self.assertEqual(actual, EXPECTED_SOURCES)

    def test_personal_works_survived_the_merge(self) -> None:
        personal = self.documents[self.documents["source"] != "gutendex"]
        self.assertEqual(len(personal), 1585)

    def test_no_gutenberg_work_appears_twice(self) -> None:
        """The T4.5 bug: 331 works imported under bare and prefixed ids."""
        gutendex = self.documents[self.documents["source"] == "gutendex"]
        identified = gutendex[gutendex["gutenberg_id"] != ""]
        duplicates = identified[identified["gutenberg_id"].duplicated(keep=False)]

        self.assertEqual(
            len(duplicates),
            0,
            f"{len(duplicates)} rows share a gutenberg_id: "
            f"{sorted(set(duplicates['gutenberg_id']))[:5]}",
        )

    def test_every_doc_id_carries_its_source_prefix(self) -> None:
        """A bare id is ambiguous across sources and is what allowed the bug."""
        bare = self.documents[~self.documents["doc_id"].str.contains(":")]
        self.assertEqual(len(bare), 0, f"{len(bare)} rows still use a bare doc_id")

    def test_doc_id_prefix_agrees_with_the_source_column(self) -> None:
        mismatched = [
            (doc_id, source)
            for doc_id, source in zip(self.documents["doc_id"], self.documents["source"])
            if doc_id.split(":", 1)[0] != source
        ]
        self.assertEqual(mismatched[:5], [])

    def test_no_row_lost_its_identity(self) -> None:
        self.assertEqual(int((self.documents["doc_id"].str.strip() == "").sum()), 0)
        gutendex = self.documents[self.documents["source"] == "gutendex"]
        self.assertEqual(int((gutendex["gutenberg_id"].str.strip() == "").sum()), 0)

    def test_the_symposium_duplicate_is_gone(self) -> None:
        """The visible symptom: two identical Symposium hits in T3/T4 search."""
        symposium = self.documents[
            (self.documents["source"] == "gutendex")
            & (self.documents["title"].str.strip().str.lower() == "symposium")
        ]
        # Distinct Gutenberg editions may legitimately share this title, but no
        # two rows may share one gutenberg_id.
        self.assertEqual(int(symposium["gutenberg_id"].duplicated().sum()), 0)
        self.assertEqual(symposium["doc_id"].nunique(), len(symposium))


class IdempotenceTests(unittest.TestCase):
    def test_prefixing_an_already_merged_master_changes_nothing(self) -> None:
        """Re-running the merge must not create new rows."""
        if not DOCUMENTS.exists():
            self.skipTest("documents master not present")

        documents = load_documents()
        again = [
            prefixed_doc_id(source, doc_id)
            for source, doc_id in zip(documents["source"], documents["doc_id"])
        ]
        self.assertEqual(again, documents["doc_id"].tolist())
        self.assertEqual(len(set(again)), len(documents))


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not MANIFEST.exists():
            raise unittest.SkipTest("corpus manifest not present")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_records_the_corpus_shape(self) -> None:
        self.assertEqual(self.manifest["document_count"], EXPECTED_TOTAL)
        self.assertEqual(self.manifest["embedding_count"], EXPECTED_TOTAL)
        self.assertEqual(self.manifest["embedding_dimension"], EXPECTED_DIMENSION)
        self.assertEqual(self.manifest["embedding_model"], CANONICAL_MODEL)

    def test_identifies_the_embedding_artifact_by_content(self) -> None:
        # Content hash, not a path: the artifact may live anywhere.
        self.assertEqual(len(self.manifest["embedding_artifact_sha256"]), 64)
        self.assertGreater(self.manifest["embedding_artifact_bytes"], 0)

    def test_agrees_with_the_documents_master(self) -> None:
        if not DOCUMENTS.exists():
            self.skipTest("documents master not present")
        documents = load_documents()
        self.assertEqual(self.manifest["document_count"], len(documents))
        self.assertEqual(
            self.manifest["sources"],
            {str(k): int(v) for k, v in documents["source"].value_counts().items()},
        )


class ParameterScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not PARAMETERS.exists():
            raise unittest.SkipTest("parameter scores not present")
        cls.parameters = pd.read_csv(PARAMETERS, dtype=str, encoding="utf-8-sig").fillna("")

    def axis_columns(self) -> list[str]:
        return [
            c
            for c in self.parameters.columns
            if c not in {"doc_id", "title", "author", "source"}
        ]

    def test_covers_every_document(self) -> None:
        if not DOCUMENTS.exists():
            self.skipTest("documents master not present")
        self.assertEqual(len(self.parameters), len(load_documents()))

    def test_has_the_ten_canonical_axes(self) -> None:
        self.assertEqual(len(self.axis_columns()), 10)

    def test_values_are_a_composition_summing_to_one(self) -> None:
        axes = self.axis_columns()
        values = self.parameters[axes].apply(pd.to_numeric, errors="coerce")

        self.assertTrue(values.notna().all().all(), "non-numeric parameter values")
        self.assertGreaterEqual(float(values.to_numpy().min()), 0.0)
        self.assertLessEqual(float(values.to_numpy().max()), 1.0)

        sums = values.sum(axis=1)
        scored = sums[sums > 0]

        # Every scored row is a composition.
        self.assertAlmostEqual(float(scored.min()), 1.0, places=4)
        self.assertAlmostEqual(float(scored.max()), 1.0, places=4)

    def test_a_document_with_no_axis_affinity_scores_all_zeros(self) -> None:
        """Canonical behaviour, not a defect.

        `make_filter_scores` clips negative cosines to zero and then divides by
        the row total `where=totals != 0`. A document whose similarity to all
        ten axes is <= 0 therefore stays at zero rather than being normalised.
        Exactly one document in the 63,891-row corpus lands there. Rewriting it
        to a uniform 0.1 would invent an affinity the model did not find.
        """
        axes = self.axis_columns()
        values = self.parameters[axes].apply(pd.to_numeric, errors="coerce")
        sums = values.sum(axis=1)

        unscored = int((sums == 0).sum())
        self.assertLessEqual(
            unscored,
            10,
            f"{unscored} documents have no axis affinity, which suggests a "
            "scoring problem rather than a genuine outlier",
        )


if __name__ == "__main__":
    unittest.main()
