from __future__ import annotations

import io
import logging
import unittest

import pandas as pd

from api.config import ApiSettings, normalize_database_url
from api.personal_repository import create_personal_repository, email_hash_for
from api.schemas import SaveDocumentRequest
from api.user_library_service import UserLibraryService


class FakeSearchRepository:
    def __init__(self) -> None:
        self.load_count = 0
        self.frame = pd.DataFrame(
            [
                {
                    "doc_id": "doc:1",
                    "title": "First Work",
                    "author": "Author A",
                    "source": "test",
                    "embedding": "[0.1, 0.2]",
                    "model_name": "test-model",
                },
                {
                    "doc_id": "doc:2",
                    "title": "Second Work",
                    "author": "Author B",
                    "source": "test",
                    "embedding": "[0.3, 0.4]",
                    "model_name": "test-model",
                },
            ]
        )

    def load_index(self) -> pd.DataFrame:
        self.load_count += 1
        return self.frame


class InMemoryPersonalRepository:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, dict[str, object]]] = {}

    def save_document(self, email_hash, row, saved_at, parameters):
        from api.personal_repository import build_saved_item, normalize_parameters, saved_document_from_mapping
        from api.schemas import SaveDocumentResponse

        doc_id = str(row.get("doc_id", ""))
        user_items = self.items.setdefault(email_hash, {})
        if doc_id in user_items:
            return SaveDocumentResponse(
                saved=False,
                duplicate=True,
                item=saved_document_from_mapping(user_items[doc_id]),
            )
        item = build_saved_item(row, saved_at, normalize_parameters(parameters))
        user_items[doc_id] = item
        return SaveDocumentResponse(
            saved=True,
            duplicate=False,
            item=saved_document_from_mapping(item),
        )

    def list_saved(self, email_hash):
        from api.personal_repository import saved_document_from_mapping
        from api.schemas import SavedDocumentsResponse

        return SavedDocumentsResponse(
            items=[saved_document_from_mapping(item) for item in self.items.get(email_hash, {}).values()]
        )

    def delete_saved(self, email_hash, doc_id):
        from api.schemas import DeleteSavedDocumentResponse

        user_items = self.items.setdefault(email_hash, {})
        deleted = doc_id in user_items
        user_items.pop(doc_id, None)
        return DeleteSavedDocumentResponse(deleted=deleted, doc_id=doc_id)


def make_service(personal_repository=None, repository=None) -> UserLibraryService:
    return UserLibraryService(
        ApiSettings(),
        repository=repository or FakeSearchRepository(),
        personal_repository=personal_repository or InMemoryPersonalRepository(),
    )


class UserLibraryServiceTests(unittest.TestCase):
    def test_normalize_database_url_uses_psycopg3_for_render_postgres_url(self) -> None:
        normalized = normalize_database_url("postgresql://user:pass@host:5432/db")

        self.assertEqual(normalized, "postgresql+psycopg://user:pass@host:5432/db")

    def test_normalize_database_url_keeps_explicit_psycopg3_url(self) -> None:
        normalized = normalize_database_url("postgresql+psycopg://user:pass@host:5432/db")

        self.assertEqual(normalized, "postgresql+psycopg://user:pass@host:5432/db")

    def test_normalize_database_url_keeps_non_postgres_url(self) -> None:
        normalized = normalize_database_url("sqlite:///local.db")

        self.assertEqual(normalized, "sqlite:///local.db")

    def test_duplicate_save_same_email_doc_id_is_not_duplicated(self) -> None:
        service = make_service()
        request = SaveDocumentRequest(doc_id="doc:1")

        first = service.save_document_by_email("USER@example.com", request)
        second = service.save_document_by_email(" user@example.com ", request)

        self.assertTrue(first.saved)
        self.assertFalse(second.saved)
        self.assertTrue(second.duplicate)
        self.assertEqual(len(service.list_saved_by_email("user@example.com").items), 1)

    def test_saved_works_are_isolated_by_user(self) -> None:
        service = make_service()
        service.save_document_by_email("one@example.com", SaveDocumentRequest(doc_id="doc:1"))
        service.save_document_by_email("two@example.com", SaveDocumentRequest(doc_id="doc:2"))

        one = service.list_saved_by_email("one@example.com").items
        two = service.list_saved_by_email("two@example.com").items

        self.assertEqual([item.doc_id for item in one], ["doc:1"])
        self.assertEqual([item.doc_id for item in two], ["doc:2"])

    def test_delete_removes_saved_work(self) -> None:
        service = make_service()
        service.save_document_by_email("user@example.com", SaveDocumentRequest(doc_id="doc:1"))

        deleted = service.delete_saved_by_email("user@example.com", "doc:1")

        self.assertTrue(deleted.deleted)
        self.assertEqual(service.list_saved_by_email("user@example.com").items, [])

    def test_default_api_maps_to_fixed_user(self) -> None:
        repo = InMemoryPersonalRepository()
        service = make_service(repo)

        service.save_document("default", SaveDocumentRequest(doc_id="doc:1"))

        default_hash = email_hash_for("default@example.local")
        self.assertIn("doc:1", repo.items[default_hash])

    def test_parameters_round_trip_for_dict_and_list(self) -> None:
        service = make_service()
        service.save_document_by_email(
            "user@example.com",
            SaveDocumentRequest(doc_id="doc:1", parameters={"philosophy": 42.0}),
        )
        service.save_document_by_email(
            "user@example.com",
            SaveDocumentRequest(doc_id="doc:2", parameters=[{"key": "science", "value": 12.5}]),
        )

        items = {item.doc_id: item for item in service.list_saved_by_email("user@example.com").items}

        self.assertEqual(items["doc:1"].parameters[0].key, "philosophy")
        self.assertEqual(items["doc:1"].parameters[0].value, 42.0)
        self.assertEqual(items["doc:2"].parameters[0].key, "science")
        self.assertEqual(items["doc:2"].parameters[0].value, 12.5)

    def test_parameter_aliases_are_returned_as_canonical_source_of_thought_keys(self) -> None:
        service = make_service()
        service.save_document_by_email(
            "user@example.com",
            SaveDocumentRequest(
                doc_id="doc:1",
                parameters={
                    "economics": 11.0,
                    "moral": 22.0,
                    "ideal": 33.0,
                    "community": 44.0,
                },
            ),
        )

        saved = service.list_saved_by_email("user@example.com").items[0]
        values = {item.key: item.value for item in saved.parameters}

        self.assertNotIn("economics", values)
        self.assertNotIn("moral", values)
        self.assertNotIn("ideal", values)
        self.assertEqual(values["economy"], 11.0)
        self.assertEqual(values["morality"], 22.0)
        self.assertEqual(values["ideology"], 33.0)
        self.assertEqual(values["community"], 44.0)

    def test_postgres_backend_requires_database_url(self) -> None:
        settings = ApiSettings(personal_backend="postgres", database_url="")

        with self.assertRaisesRegex(RuntimeError, "DATABASE_URL is required"):
            create_personal_repository(settings)

    def test_raw_email_is_not_logged(self) -> None:
        logger = logging.getLogger()
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        try:
            service = make_service()
            service.save_document_by_email("private@example.com", SaveDocumentRequest(doc_id="doc:1"))
        finally:
            logger.removeHandler(handler)

        self.assertNotIn("private@example.com", stream.getvalue())

    def test_uploaded_document_metadata_is_not_replaced_by_official_db(self) -> None:
        repository = FakeSearchRepository()
        service = make_service(repository=repository)

        service.save_document_by_email(
            "user@example.com",
            SaveDocumentRequest(
                doc_id="doc:1",
                title="Uploaded Original Title",
                author="Uploader",
                source="upload",
                embedding="[0.9, 0.8]",
            ),
        )

        saved = service.list_saved_by_email("user@example.com").items[0]
        self.assertEqual(saved.title, "Uploaded Original Title")
        self.assertEqual(saved.author, "Uploader")
        self.assertEqual(saved.source, "upload")
        self.assertEqual(repository.load_count, 0)

    def test_official_source_type_uses_official_lookup(self) -> None:
        repository = FakeSearchRepository()
        service = make_service(repository=repository)

        service.save_document_by_email(
            "user@example.com",
            SaveDocumentRequest(doc_id="doc:1", source_type="official"),
        )

        saved = service.list_saved_by_email("user@example.com").items[0]
        self.assertEqual(saved.title, "First Work")
        self.assertEqual(repository.load_count, 1)

    def test_upload_doc_ids_are_unique_for_ten_documents(self) -> None:
        upload_session_id = "upload_12345678_deadbeef"
        doc_ids = [f"{upload_session_id}_{i:06d}" for i in range(10)]

        self.assertEqual(len(doc_ids), 10)
        self.assertEqual(len(set(doc_ids)), 10)
        self.assertTrue(all(not doc_id.startswith("doc_") for doc_id in doc_ids))


if __name__ == "__main__":
    unittest.main()
