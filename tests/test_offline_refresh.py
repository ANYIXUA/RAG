from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import unittest

from rag_app.core.config import Settings
from rag_app.indexing.offline import OfflineKnowledgeBuilder
from tests.helpers import DeterministicEmbedder, MemoryVectorStore, production_settings


class OfflineRefreshTest(unittest.TestCase):
    def test_incremental_refresh_tracks_file_changes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            source_file = data_dir / "fault.md"
            source_file.write_text("光猫 LOS 红灯需要检查尾纤和光功率。", encoding="utf-8")

            builder = _builder(base_dir, data_dir, storage_dir)

            first = builder.refresh(reset=True)
            second = builder.refresh()
            source_file.write_text("光猫 LOS 红灯需要检查尾纤、分光器端口和光功率。", encoding="utf-8")
            third = builder.refresh()
            source_file.unlink()
            fourth = builder.refresh()

            self.assertEqual(first.documents_seen, 1)
            self.assertEqual(first.documents_changed, 1)
            self.assertEqual(first.chunks_embedded, 1)
            self.assertEqual(first.stored_records, 1)

            self.assertEqual(second.documents_changed, 0)
            self.assertEqual(second.documents_skipped, 1)
            self.assertEqual(second.stored_records, 1)

            self.assertEqual(third.documents_changed, 1)
            self.assertEqual(third.documents_removed, 0)
            self.assertEqual(third.stored_records, 1)

            self.assertEqual(fourth.documents_seen, 0)
            self.assertEqual(fourth.documents_removed, 1)
            self.assertEqual(fourth.stored_records, 0)

    def test_manifest_records_parser_and_chunker_versions(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text("# 故障案例\n\n光猫 LOS 红灯。", encoding="utf-8")

            builder = _builder(base_dir, data_dir, storage_dir)
            builder.refresh(reset=True)

            manifest = (storage_dir / "test_manifest.json").read_text(encoding="utf-8")

            self.assertIn("parser_version", manifest)
            self.assertIn("chunker_version", manifest)
            self.assertIn("knowledge_status", manifest)
            self.assertIn("governance", manifest)

    def test_refresh_report_records_governance_skips(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text("光猫 LOS 红灯。", encoding="utf-8")
            (data_dir / "knowledge_sources.json").write_text("{}", encoding="utf-8")

            builder = _builder(base_dir, data_dir, storage_dir)
            report = builder.refresh(reset=True)

            self.assertEqual(report.files_seen, 2)
            self.assertEqual(report.documents_seen, 1)
            self.assertEqual(report.documents_skipped_by_policy, 1)
            self.assertEqual(report.documents_failed, 0)
            self.assertEqual(report.skipped_files[0]["reason"], "system_file")
            self.assertTrue(Path(report.refresh_report_path).exists())

    def test_refresh_backs_up_previous_manifest(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            source_file = data_dir / "fault.md"
            source_file.write_text("第一次内容。", encoding="utf-8")

            builder = _builder(base_dir, data_dir, storage_dir)
            builder.refresh(reset=True)
            source_file.write_text("第二次内容。", encoding="utf-8")
            report = builder.refresh(force=True)

            backup_path = Path(report.manifest_backup_path)
            self.assertTrue(backup_path.exists())
            backup = json.loads(backup_path.read_text(encoding="utf-8"))
            source_path = str(source_file.resolve())
            self.assertEqual(
                backup["files"][source_path]["content_hash"],
                hashlib.sha256("第一次内容。".encode("utf-8")).hexdigest(),
            )


def _settings(base_dir: Path, data_dir: Path, storage_dir: Path) -> Settings:
    return production_settings(
        base_dir,
        data_dir=data_dir,
        storage_dir=storage_dir,
        chunk_size=40,
        chunk_overlap=5,
    )


def _builder(base_dir: Path, data_dir: Path, storage_dir: Path) -> OfflineKnowledgeBuilder:
    settings = _settings(base_dir, data_dir, storage_dir)
    return OfflineKnowledgeBuilder(
        settings,
        embedder=DeterministicEmbedder(settings.embedding_dimension),
        vector_store=MemoryVectorStore(),
    )


if __name__ == "__main__":
    unittest.main()
