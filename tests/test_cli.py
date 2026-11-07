from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import redirect_stdout
from tempfile import TemporaryDirectory
from unittest.mock import patch

from rag_app import cli
from rag_app.operations.dify_sync import DifySyncResult


class CliTest(unittest.TestCase):
    def test_dify_sync_command_uses_env_dataset_and_outputs_json(self) -> None:
        class FakeDifySyncService:
            def sync(self, dataset_id: str, dry_run: bool = False) -> DifySyncResult:
                return DifySyncResult(dataset_id=dataset_id, dry_run=dry_run, created=1)

        with TemporaryDirectory() as temp_dir:
            env = {
                "RAG_DATA_DIR": f"{temp_dir}/data",
                "RAG_STORAGE_DIR": f"{temp_dir}/storage",
                "RAG_COLLECTION_NAME": "test",
                "OPENAI_API_KEY": "test-key",
                "RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag",
                "RAG_ORDER_STATUS_TOOL_ENABLED": "false",
                "RAG_DIFY_API_BASE_URL": "https://dify.example.com/v1",
                "RAG_DIFY_API_KEY": "dify-secret",
                "RAG_DIFY_DATASET_ID": "dataset-from-env",
            }
            output = io.StringIO()
            with (
                patch.dict(os.environ, env, clear=True),
                patch("rag_app.cli.create_dify_document_sync_service", return_value=FakeDifySyncService()),
                redirect_stdout(output),
            ):
                exit_code = cli.main(["dify-sync", "--dry-run", "--json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["dataset_id"], "dataset-from-env")
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["created"], 1)


if __name__ == "__main__":
    unittest.main()
