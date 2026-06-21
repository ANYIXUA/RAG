import os
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from rag_app.core.config import Settings
from tests.helpers import production_settings


class SettingsConfigTest(unittest.TestCase):
    def test_from_env_loads_split_config_files_after_env_defaults(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            config_dir = base_dir / "config"
            config_dir.mkdir()
            (config_dir / "retrieval.json").write_text(
                json.dumps(
                    {
                        "top_k": 9,
                        "retrieval_mode": "semantic",
                        "retrieval_candidate_k": 15,
                        "semantic_weight": 1.0,
                        "bm25_weight": 0.0,
                    }
                ),
                encoding="utf-8",
            )
            (config_dir / "storage.json").write_text(
                json.dumps({"collection_name": "manual_eval"}),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "RAG_CONFIG_DIR": str(config_dir),
                    "RAG_TOP_K": "3",
                    "RAG_RETRIEVAL_MODE": "hybrid",
                    "RAG_COLLECTION_NAME": "env_collection",
                    "OPENAI_API_KEY": "test-key",
                    "RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag",
                    "RAG_ORDER_STATUS_TOOL_ENABLED": "false",
                },
                clear=True,
            ):
                settings = Settings.from_env(base_dir=base_dir)

            self.assertEqual(settings.top_k, 9)
            self.assertEqual(settings.retrieval_mode, "semantic")
            self.assertEqual(settings.retrieval_candidate_k, 15)
            self.assertEqual(settings.collection_name, "manual_eval")
            self.assertTrue(settings.config_fingerprint)
            self.assertEqual(
                [Path(source).name for source in settings.config_sources],
                ["retrieval.json", "storage.json"],
            )

    def test_config_file_expands_environment_placeholders(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            config_dir = base_dir / "config"
            config_dir.mkdir()
            (config_dir / "storage.json").write_text(
                json.dumps(
                    {
                        "ops_postgres_dsn": "${TEST_RAG_DSN}",
                        "order_status_postgres_dsn": "${TEST_RAG_DSN}",
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "RAG_CONFIG_DIR": str(config_dir),
                    "TEST_RAG_DSN": "postgresql://rag:pwd@localhost:15432/rag",
                    "OPENAI_API_KEY": "test-key",
                },
                clear=True,
            ):
                settings = Settings.from_env(base_dir=base_dir)

            self.assertEqual(
                settings.ops_postgres_dsn,
                "postgresql://rag:pwd@localhost:15432/rag",
            )
            self.assertEqual(
                settings.order_status_postgres_dsn,
                "postgresql://rag:pwd@localhost:15432/rag",
            )

    def test_runtime_fingerprint_changes_when_config_changes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            config_dir = base_dir / "config"
            config_dir.mkdir()
            config_path = config_dir / "retrieval.json"
            config_path.write_text(json.dumps({"top_k": 4}), encoding="utf-8")
            env = {
                "RAG_CONFIG_DIR": str(config_dir),
                "OPENAI_API_KEY": "test-key",
                "RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag",
                "RAG_ORDER_STATUS_TOOL_ENABLED": "false",
            }
            with patch.dict(os.environ, env, clear=True):
                first = Settings.from_env(base_dir=base_dir)
                config_path.write_text(json.dumps({"top_k": 8}), encoding="utf-8")
                second = Settings.from_env(base_dir=base_dir)

            self.assertNotEqual(first.config_fingerprint, second.config_fingerprint)
            self.assertEqual(second.top_k, 8)

    def test_from_env_resolves_production_defaults(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            with patch.dict(
                os.environ,
                {
                    "RAG_DATA_DIR": "knowledge",
                    "RAG_STORAGE_DIR": "runtime",
                    "RAG_COLLECTION_NAME": "prod",
                    "RAG_RETRIEVAL_MODE": "BM25",
                    "RAG_RERANK_PROVIDER": "OFF",
                    "RAG_KEYWORD_WEIGHT": "0.4",
                    "OPENAI_API_KEY": "test-key",
                    "RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag",
                },
                clear=True,
            ):
                settings = Settings.from_env(base_dir=base_dir)

            self.assertEqual(settings.data_dir, (base_dir / "knowledge").resolve())
            self.assertEqual(settings.storage_dir, (base_dir / "runtime").resolve())
            self.assertEqual(settings.retrieval_mode, "bm25")
            self.assertEqual(settings.rerank_provider, "off")
            self.assertEqual(settings.bm25_weight, 0.4)
            self.assertEqual(settings.embedding_provider, "openai")
            self.assertEqual(settings.llm_provider, "openai")
            self.assertEqual(settings.ops_store_provider, "postgresql")
            self.assertEqual(settings.vector_store_provider, "postgresql")
            self.assertEqual(
                settings.order_status_postgres_dsn,
                "postgresql://rag:pwd@localhost:5432/rag",
            )

    def test_from_env_reads_openai_compatible_model_settings(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "DASHSCOPE_API_KEY": "dashscope-key",
                    "OPENAI_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    "OPENAI_CHAT_MODEL": "qwen-plus",
                    "OPENAI_EMBEDDING_MODEL": "text-embedding-v4",
                    "OPENAI_MAX_TOKENS": "800",
                    "OPENAI_TIMEOUT_SECONDS": "6.5",
                    "OPENAI_MAX_RETRIES": "0",
                    "RAG_GENERATION_CONTEXT_MAX_CHARS": "2400",
                    "RAG_EMBEDDING_DIMENSION": "1024",
                    "RAG_EMBEDDING_BATCH_SIZE": "10",
                    "RAG_EMBEDDING_TIMEOUT_SECONDS": "3.0",
                    "RAG_EMBEDDING_MAX_RETRIES": "0",
                    "RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag",
                    "RAG_ORDER_STATUS_TOOL_ENABLED": "false",
                },
                clear=True,
            ):
                settings = Settings.from_env(base_dir=Path(temp_dir))

            self.assertEqual(settings.openai_api_key, "dashscope-key")
            self.assertEqual(
                settings.openai_base_url,
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            self.assertEqual(settings.openai_chat_model, "qwen-plus")
            self.assertEqual(settings.openai_embedding_model, "text-embedding-v4")
            self.assertEqual(settings.openai_max_tokens, 800)
            self.assertEqual(settings.openai_timeout_seconds, 6.5)
            self.assertEqual(settings.openai_max_retries, 0)
            self.assertEqual(settings.generation_context_max_chars, 2400)
            self.assertEqual(settings.embedding_dimension, 1024)
            self.assertEqual(settings.embedding_batch_size, 10)
            self.assertEqual(settings.embedding_timeout_seconds, 3.0)
            self.assertEqual(settings.embedding_max_retries, 0)

    def test_rejects_invalid_chunk_overlap(self) -> None:
        base_dir = Path(".").resolve()

        with self.assertRaisesRegex(ValueError, "RAG_CHUNK_OVERLAP"):
            production_settings(
                base_dir,
                data_dir=base_dir,
                storage_dir=base_dir,
                chunk_size=100,
                chunk_overlap=100,
            )

    def test_rejects_removed_embedding_provider(self) -> None:
        base_dir = Path(".").resolve()

        with self.assertRaisesRegex(ValueError, "RAG_EMBEDDING_PROVIDER"):
            production_settings(
                base_dir,
                data_dir=base_dir,
                storage_dir=base_dir,
                embedding_provider="hashing",
            )

    def test_rejects_removed_llm_provider(self) -> None:
        base_dir = Path(".").resolve()

        with self.assertRaisesRegex(ValueError, "RAG_LLM_PROVIDER"):
            production_settings(
                base_dir,
                data_dir=base_dir,
                storage_dir=base_dir,
                llm_provider="template",
            )

    def test_rejects_invalid_rerank_trigger(self) -> None:
        base_dir = Path(".").resolve()

        with self.assertRaisesRegex(ValueError, "RAG_RERANK_TRIGGER"):
            production_settings(
                base_dir,
                data_dir=base_dir,
                storage_dir=base_dir,
                rerank_trigger="sometimes",
            )

    def test_rejects_unsafe_collection_name(self) -> None:
        base_dir = Path(".").resolve()

        with self.assertRaisesRegex(ValueError, "RAG_COLLECTION_NAME"):
            production_settings(
                base_dir,
                data_dir=base_dir,
                storage_dir=base_dir,
                collection_name="../bad",
            )

    def test_rejects_invalid_boolean_env(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "RAG_QUERY_LOGGING_ENABLED": "maybe",
                    "OPENAI_API_KEY": "test-key",
                    "RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "RAG_QUERY_LOGGING_ENABLED"):
                    Settings.from_env(base_dir=Path(temp_dir))

    def test_rejects_invalid_embedding_batch_size(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "RAG_EMBEDDING_BATCH_SIZE": "0",
                    "RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag",
                    "RAG_ORDER_STATUS_TOOL_ENABLED": "false",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "RAG_EMBEDDING_BATCH_SIZE"):
                    Settings.from_env(base_dir=Path(temp_dir))

    def test_rejects_invalid_openai_max_tokens(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "OPENAI_MAX_TOKENS": "0",
                    "RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag",
                    "RAG_ORDER_STATUS_TOOL_ENABLED": "false",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "OPENAI_MAX_TOKENS"):
                    Settings.from_env(base_dir=Path(temp_dir))

    def test_postgres_provider_requires_dsn(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {"OPENAI_API_KEY": "test-key"},
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "RAG_OPS_POSTGRES_DSN"):
                    Settings.from_env(base_dir=Path(temp_dir))

    def test_openai_provider_requires_api_key(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {"RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag"},
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
                    Settings.from_env(base_dir=Path(temp_dir))

    def test_order_status_tool_requires_postgres_dsn_when_enabled(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "RAG_ORDER_STATUS_TOOL_ENABLED": "true",
                },
                clear=True,
            ):
                with self.assertRaisesRegex(ValueError, "RAG_OPS_POSTGRES_DSN"):
                    Settings.from_env(base_dir=Path(temp_dir))


if __name__ == "__main__":
    unittest.main()
