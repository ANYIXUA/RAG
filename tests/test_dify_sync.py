from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rag_app.operations.dify_sync import (
    DifyDocumentSyncService,
    JsonDifySyncStateStore,
)
from tests.helpers import production_settings


class FakeDifyClient:
    def __init__(self) -> None:
        self.created: list[tuple[str, dict]] = []
        self.updated: list[tuple[str, str, dict]] = []

    def create_document_by_text(self, dataset_id: str, payload: dict) -> dict:
        self.created.append((dataset_id, payload))
        return {"document": {"id": f"dify-doc-{len(self.created)}"}, "batch": "batch-create"}

    def update_document_by_text(self, dataset_id: str, document_id: str, payload: dict) -> dict:
        self.updated.append((dataset_id, document_id, payload))
        return {"document": {"id": document_id}, "batch": "batch-update"}


class DifySyncTest(unittest.TestCase):
    def test_creates_dify_document_from_manifest_entry_and_records_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            source = _write_source(base_dir, "fault.md", "# 故障案例\n\n接口超时先检查下游。")
            settings = production_settings(base_dir)
            _write_manifest(
                settings,
                {
                    str(source): {
                        "document_id": "doc-1",
                        "content_hash": "hash-1",
                        "filename": "fault.md",
                        "title": "故障案例",
                        "parser_version": "parser-v1",
                        "chunker_version": "chunker-v1",
                        "parse_quality_status": "parsed_success",
                        "tenant_id": "tenant-a",
                        "permission_tags": ["OPS_L2"],
                    }
                },
            )
            client = FakeDifyClient()
            state_store = JsonDifySyncStateStore(settings.storage_dir / "dify_state.json")

            result = DifyDocumentSyncService(
                settings=settings,
                client=client,
                state_store=state_store,
            ).sync(dataset_id="dataset-1")

            self.assertEqual(result.created, 1)
            self.assertEqual(result.updated, 0)
            self.assertEqual(client.created[0][0], "dataset-1")
            payload = client.created[0][1]
            self.assertEqual(payload["name"], "fault.md")
            self.assertEqual(payload["text"], "# 故障案例\n\n接口超时先检查下游。")
            self.assertEqual(payload["doc_form"], "text_model")
            self.assertEqual(payload["doc_language"], "Chinese")
            self.assertEqual(payload["original_document_id"], "doc-1")

            state = state_store.load()
            entry = state["documents"][str(source)]
            self.assertEqual(entry["dify_document_id"], "dify-doc-1")
            self.assertEqual(entry["dify_batch_id"], "batch-create")
            self.assertEqual(entry["content_hash"], "hash-1")
            self.assertEqual(entry["sync_status"], "synced")

    def test_updates_existing_dify_document_when_manifest_hash_changes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            source = _write_source(base_dir, "fault.md", "第二版内容。")
            settings = production_settings(base_dir)
            _write_manifest(
                settings,
                {
                    str(source): {
                        "document_id": "doc-1",
                        "content_hash": "hash-2",
                        "filename": "fault.md",
                        "parser_version": "parser-v2",
                        "chunker_version": "chunker-v1",
                    }
                },
            )
            state_store = JsonDifySyncStateStore(settings.storage_dir / "dify_state.json")
            state_store.save(
                {
                    "documents": {
                        str(source): {
                            "source_path": str(source),
                            "document_id": "doc-1",
                            "content_hash": "hash-1",
                            "parser_version": "parser-v1",
                            "chunker_version": "chunker-v1",
                            "dify_dataset_id": "dataset-1",
                            "dify_document_id": "dify-doc-old",
                            "dify_batch_id": "batch-old",
                            "sync_status": "synced",
                            "last_synced_at": "2026-07-01T00:00:00+00:00",
                            "last_error": None,
                        }
                    }
                }
            )
            client = FakeDifyClient()

            result = DifyDocumentSyncService(
                settings=settings,
                client=client,
                state_store=state_store,
            ).sync(dataset_id="dataset-1")

            self.assertEqual(result.created, 0)
            self.assertEqual(result.updated, 1)
            self.assertEqual(client.updated[0][1], "dify-doc-old")
            self.assertEqual(client.updated[0][2]["text"], "第二版内容。")
            state = state_store.load()
            self.assertEqual(state["documents"][str(source)]["content_hash"], "hash-2")
            self.assertEqual(state["documents"][str(source)]["dify_batch_id"], "batch-update")

    def test_dry_run_reports_stale_documents_without_calling_dify(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            settings = production_settings(base_dir)
            _write_manifest(settings, {})
            state_store = JsonDifySyncStateStore(settings.storage_dir / "dify_state.json")
            state_store.save(
                {
                    "documents": {
                        "D:/old.md": {
                            "source_path": "D:/old.md",
                            "document_id": "doc-old",
                            "content_hash": "hash-old",
                            "dify_dataset_id": "dataset-1",
                            "dify_document_id": "dify-doc-old",
                            "sync_status": "synced",
                        }
                    }
                }
            )
            client = FakeDifyClient()

            result = DifyDocumentSyncService(
                settings=settings,
                client=client,
                state_store=state_store,
            ).sync(dataset_id="dataset-1", dry_run=True)

            self.assertEqual(result.disabled, 1)
            self.assertEqual(result.created, 0)
            self.assertEqual(result.updated, 0)
            self.assertEqual(client.created, [])
            self.assertEqual(client.updated, [])

    def test_skips_documents_that_still_require_ocr_review(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            source = _write_source(base_dir, "scan.md", "低质量扫描件。")
            settings = production_settings(base_dir)
            _write_manifest(
                settings,
                {
                    str(source): {
                        "document_id": "doc-scan",
                        "content_hash": "hash-scan",
                        "filename": "scan.md",
                        "parse_quality_status": "parsed_success",
                        "ocr_required": True,
                    }
                },
            )
            client = FakeDifyClient()

            result = DifyDocumentSyncService(
                settings=settings,
                client=client,
                state_store=JsonDifySyncStateStore(settings.storage_dir / "dify_state.json"),
            ).sync(dataset_id="dataset-1")

            self.assertEqual(result.skipped, 1)
            self.assertEqual(result.items[0].status, "parse_quality_skipped")
            self.assertEqual(client.created, [])


def _write_source(base_dir: Path, name: str, text: str) -> Path:
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    source = data_dir / name
    source.write_text(text, encoding="utf-8")
    return source.resolve()


def _write_manifest(settings, files: dict[str, dict]) -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "collection_name": settings.collection_name,
        "files": files,
    }
    settings.manifest_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
