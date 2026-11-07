from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_app.operations.knowledge_lifecycle import (
    PostgresKnowledgeLifecycleStore,
    collection_name_for_version,
    create_knowledge_lifecycle_store,
    settings_for_collection,
)
from tests.helpers import production_settings


class KnowledgeLifecycleTest(unittest.TestCase):
    def test_collection_name_for_version_is_pg_identifier_safe(self) -> None:
        collection = collection_name_for_version("default", "kb-2026/05")

        self.assertEqual(collection, "default_kb_2026_05")

    def test_settings_for_collection_switches_pgvector_collection(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = production_settings(Path(temp_dir), collection_name="base")

            version_settings = settings_for_collection(settings, "base_kb_1")

            self.assertEqual(version_settings.collection_name, "base_kb_1")
            self.assertEqual(version_settings.vector_store_provider, "postgresql")

    def test_lifecycle_store_factory_uses_postgres(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = production_settings(Path(temp_dir))

            with patch.object(PostgresKnowledgeLifecycleStore, "__init__", return_value=None):
                store = create_knowledge_lifecycle_store(settings)

            self.assertIsInstance(store, PostgresKnowledgeLifecycleStore)


if __name__ == "__main__":
    unittest.main()
