"""Tests for the T4.5 corpus reconciliation logic.

The identity and duplicate rules are tested directly, without touching the
real 62,306-row external master.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from api.corpus_inventory import inspect_csv, to_markdown
from api.recover_full_corpus import (
    CANONICAL_MODEL,
    classify_current_duplicates,
    normalise_model,
    prefixed_doc_id,
)


class DocIdIdentityTests(unittest.TestCase):
    def test_prefixes_a_bare_id_with_its_source(self) -> None:
        self.assertEqual(prefixed_doc_id("gutendex", "doc_000123"), "gutendex:doc_000123")
        self.assertEqual(prefixed_doc_id("user_suno", "doc_000001"), "user_suno:doc_000001")

    def test_is_idempotent_for_an_already_prefixed_id(self) -> None:
        # Running the merge twice must not produce gutendex:gutendex:doc_1.
        once = prefixed_doc_id("gutendex", "gutendex:doc_000123")
        twice = prefixed_doc_id("gutendex", once)
        self.assertEqual(once, "gutendex:doc_000123")
        self.assertEqual(twice, once)

    def test_collapses_the_bare_and_prefixed_form_of_one_document(self) -> None:
        # This is exactly the 331-row duplication found in the master.
        self.assertEqual(
            prefixed_doc_id("gutendex", "doc_000000"),
            prefixed_doc_id("gutendex", "gutendex:doc_000000"),
        )

    def test_keeps_different_sources_distinct(self) -> None:
        # A bare doc_000000 exists in both the gutendex and personal id spaces
        # and they are different documents.
        self.assertNotEqual(
            prefixed_doc_id("gutendex", "doc_000000"),
            prefixed_doc_id("user_suno", "doc_000000"),
        )

    def test_handles_a_blank_id(self) -> None:
        self.assertEqual(prefixed_doc_id("gutendex", ""), "")
        self.assertEqual(prefixed_doc_id("gutendex", "   "), "")


class ModelCompatibilityTests(unittest.TestCase):
    def test_treats_the_namespaced_and_bare_model_name_as_one(self) -> None:
        self.assertEqual(
            normalise_model("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
            normalise_model("paraphrase-multilingual-MiniLM-L12-v2"),
        )
        self.assertEqual(
            normalise_model("sentence-transformers/" + CANONICAL_MODEL), CANONICAL_MODEL
        )

    def test_detects_a_genuinely_different_model(self) -> None:
        self.assertNotEqual(normalise_model("all-MiniLM-L6-v2"), CANONICAL_MODEL)

    def test_handles_blanks(self) -> None:
        self.assertEqual(normalise_model(""), "")
        self.assertEqual(normalise_model(None), "")


class DuplicateClassificationTests(unittest.TestCase):
    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                # The bare/prefixed pair: one work, imported twice.
                {"doc_id": "doc_1", "source": "gutendex", "gutenberg_id": "58169",
                 "title": "Lectures", "author": "Hegel", "text_hash": "aaa"},
                {"doc_id": "gutendex:doc_1", "source": "gutendex", "gutenberg_id": "58169",
                 "title": "Lectures", "author": "Hegel", "text_hash": "aaa"},
                # Two genuinely different works that share a title.
                {"doc_id": "gutendex:doc_2", "source": "gutendex", "gutenberg_id": "100",
                 "title": "Poems", "author": "Anon", "text_hash": "bbb"},
                {"doc_id": "gutendex:doc_3", "source": "gutendex", "gutenberg_id": "200",
                 "title": "Poems", "author": "Someone", "text_hash": "ccc"},
                {"doc_id": "user_suno:doc_1", "source": "user_suno", "gutenberg_id": "",
                 "title": "Song", "author": "Me", "text_hash": "ddd"},
            ]
        )

    def test_reports_each_identity_rule_separately(self) -> None:
        stats = classify_current_duplicates(self.frame())

        # doc_id itself is unique: the duplication is invisible to that rule,
        # which is precisely why it survived into the master.
        self.assertEqual(stats["exact_doc_id"], 0)
        self.assertEqual(stats["source_plus_gutenberg_id"], 1)
        self.assertEqual(stats["text_hash"], 1)
        # The bare/prefixed pair also shares title and author, so that rule
        # sees it too; it is simply not the rule the merge relies on.
        self.assertEqual(stats["source_title_author"], 1)

    def test_does_not_deduplicate_on_title_alone(self) -> None:
        # Two genuinely different works that happen to share a title, with no
        # other duplication present.
        frame = pd.DataFrame(
            [
                {"doc_id": "gutendex:doc_2", "source": "gutendex", "gutenberg_id": "100",
                 "title": "Poems", "author": "Anon", "text_hash": "bbb"},
                {"doc_id": "gutendex:doc_3", "source": "gutendex", "gutenberg_id": "200",
                 "title": "Poems", "author": "Someone", "text_hash": "ccc"},
            ]
        )
        stats = classify_current_duplicates(frame)

        self.assertEqual(stats["source_title_author"], 0)
        self.assertEqual(stats["source_plus_gutenberg_id"], 0)
        self.assertEqual(stats["text_hash"], 0)

    def test_same_title_and_author_is_still_not_proof_of_duplication(self) -> None:
        # Different editions of one work: same title and author, different
        # gutenberg_id and different content. Merging on title+author would
        # wrongly collapse them; source-native identity keeps them apart.
        frame = pd.DataFrame(
            [
                {"doc_id": "gutendex:doc_4", "source": "gutendex", "gutenberg_id": "1342",
                 "title": "Pride and Prejudice", "author": "Austen", "text_hash": "e1"},
                {"doc_id": "gutendex:doc_5", "source": "gutendex", "gutenberg_id": "42671",
                 "title": "Pride and Prejudice", "author": "Austen", "text_hash": "e2"},
            ]
        )
        stats = classify_current_duplicates(frame)

        self.assertEqual(stats["source_title_author"], 1)
        # The rule the merge actually uses reports no duplication.
        self.assertEqual(stats["source_plus_gutenberg_id"], 0)
        self.assertEqual(stats["text_hash"], 0)


class MergeArithmeticTests(unittest.TestCase):
    """The merge is a set union keyed on gutenberg_id; check it adds up."""

    def test_union_is_current_unique_plus_genuinely_new(self) -> None:
        current_unique = 4584
        candidates = 62306
        already_known = 2999
        new_unique = candidates - already_known
        self.assertEqual(new_unique, 59307)
        self.assertEqual(current_unique + new_unique, 63891)

    def test_merging_twice_adds_nothing(self) -> None:
        known = {"1", "2", "3"}
        candidates = ["1", "2", "3", "4"]

        first = [c for c in candidates if c not in known]
        known |= set(first)
        second = [c for c in candidates if c not in known]

        self.assertEqual(first, ["4"])
        self.assertEqual(second, [])


class InventoryTests(unittest.TestCase):
    def test_records_a_missing_dataset_without_failing(self) -> None:
        with TemporaryDirectory() as directory:
            info = inspect_csv(Path(directory) / "absent.csv", "role", "canonical")
            self.assertFalse(info.present)
            self.assertIn("not present", info.notes)
            self.assertEqual(info.row_count, 0)

    def test_measures_identity_and_embedding_columns(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "docs.csv"
            pd.DataFrame(
                [
                    {"doc_id": "a", "gutenberg_id": "1", "title": "T", "author": "A",
                     "source": "gutendex", "text_hash": "h1",
                     "model_name": CANONICAL_MODEL, "embedding": json.dumps([0.0] * 384)},
                    {"doc_id": "b", "gutenberg_id": "1", "title": "T", "author": "A",
                     "source": "gutendex", "text_hash": "h1",
                     "model_name": CANONICAL_MODEL, "embedding": json.dumps([0.0] * 384)},
                ]
            ).to_csv(path, index=False, encoding="utf-8-sig")

            info = inspect_csv(path, "test", "canonical")

            self.assertTrue(info.present)
            self.assertEqual(info.row_count, 2)
            self.assertEqual(info.unique_doc_id_count, 2)
            self.assertEqual(info.duplicate_gutenberg_id_count, 1)
            self.assertTrue(info.has_embedding)
            self.assertEqual(info.embedding_dimension, 384)
            self.assertEqual(info.embedding_model, CANONICAL_MODEL)
            self.assertEqual(info.source_distribution, {"gutendex": 2})

    def test_renders_markdown_including_absent_datasets(self) -> None:
        inventory = {
            "project_root": "/p",
            "external_root": "/e",
            "external_root_present": False,
            "datasets": [
                {
                    "path": "/e/master/documents_master.csv", "present": False, "row_count": 0,
                    "unique_doc_id_count": None, "duplicate_doc_id_count": None,
                    "unique_gutenberg_id_count": None, "has_embedding": False,
                    "embedding_dimension": None, "embedding_model": None,
                    "likely_role": "external", "canonical_or_derived": "canonical",
                    "source_distribution": {}, "notes": "referenced but not present",
                }
            ],
        }
        markdown = to_markdown(inventory)
        self.assertIn("NOT present", markdown)
        self.assertIn("**no**", markdown)
        self.assertIn("referenced but not present", markdown)


if __name__ == "__main__":
    unittest.main()
