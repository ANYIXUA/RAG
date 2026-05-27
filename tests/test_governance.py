from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from rag_app.ingestion.governance import KnowledgeGovernancePolicy
from rag_app.ingestion.loaders import DirectoryDocumentLoader


class KnowledgeGovernanceTest(unittest.TestCase):
    def test_loader_skips_system_dataset_and_unapproved_crawled_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            crawled_dir = data_dir / "crawled"
            crawled_dir.mkdir(parents=True)
            (data_dir / "fault.md").write_text(
                "# 光猫 LOS 红灯\n\n需要检查尾纤。",
                encoding="utf-8",
            )
            (data_dir / "knowledge_sources.json").write_text("{}", encoding="utf-8")
            (data_dir / "retrieval_eval.jsonl").write_text(
                '{"query":"光猫红灯"}\n',
                encoding="utf-8",
            )
            (crawled_dir / "web.md").write_text(
                "\n".join(
                    [
                        "---",
                        "title: 网页资料",
                        "source_type: web_crawl",
                        "knowledge_status: draft",
                        "---",
                        "# 网页资料",
                        "",
                        "光猫 LOS 红灯处理说明。",
                    ]
                ),
                encoding="utf-8",
            )

            report = DirectoryDocumentLoader(data_dir).load_with_report()

            self.assertEqual(report.files_seen, 4)
            self.assertEqual(len(report.documents), 1)
            self.assertEqual(report.documents[0].metadata["source"], "fault.md")
            reasons = {item.reason for item in report.skipped}
            self.assertIn("system_file", reasons)
            self.assertIn("dataset_file", reasons)
            self.assertIn("pending_review", reasons)

    def test_registry_can_approve_crawled_document(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            crawled_dir = data_dir / "crawled"
            crawled_dir.mkdir(parents=True)
            (crawled_dir / "web.md").write_text(
                "\n".join(
                    [
                        "---",
                        "title: 网页资料",
                        "source_type: web_crawl",
                        "knowledge_status: draft",
                        "---",
                        "# 网页资料",
                        "",
                        "光猫 LOS 红灯处理说明。",
                    ]
                ),
                encoding="utf-8",
            )
            registry_path = data_dir / "knowledge_registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "path": "crawled/web.md",
                                "status": "approved",
                                "reviewer": "qa",
                                "reviewed_at": "2026-05-07",
                                "version": "v1",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            policy = KnowledgeGovernancePolicy(
                source_dir=data_dir,
                registry_path=registry_path,
            )

            report = DirectoryDocumentLoader(
                data_dir,
                governance_policy=policy,
            ).load_with_report()

            self.assertEqual(len(report.documents), 1)
            document = report.documents[0]
            self.assertEqual(document.metadata["knowledge_status"], "approved")
            self.assertEqual(document.metadata["reviewer"], "qa")
            self.assertEqual(document.metadata["governance_source"], "registry")

    def test_crawled_document_without_explicit_status_needs_review(self) -> None:
        with TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            crawled_dir = data_dir / "crawled"
            crawled_dir.mkdir(parents=True)
            (crawled_dir / "legacy_web.md").write_text(
                "\n".join(
                    [
                        "---",
                        "title: 旧网页资料",
                        "source_type: web_crawl",
                        "---",
                        "# 旧网页资料",
                        "",
                        "光猫 LOS 红灯处理说明。",
                    ]
                ),
                encoding="utf-8",
            )

            report = DirectoryDocumentLoader(data_dir).load_with_report()

            self.assertEqual(len(report.documents), 0)
            self.assertEqual(report.skipped[0].reason, "pending_review")


if __name__ == "__main__":
    unittest.main()
