from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_app.indexing.offline import OfflineKnowledgeBuilder
from rag_app.rag import RAGPipeline
from tests.helpers import (
    DeterministicEmbedder,
    MemoryQueryLogStore,
    MemoryVectorStore,
    SimpleAnswerGenerator,
    production_settings,
)


class RAGPipelineTest(unittest.TestCase):
    def test_ingest_and_query_local_pipeline(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "guide.md").write_text(
                "RAG loads documents and retrieves relevant context before answering. "
                "The production system stores vectors in PostgreSQL with pgvector. "
                "光猫红灯需要检查尾纤和光功率。",
                encoding="utf-8",
            )
            settings = production_settings(
                base_dir,
                data_dir=data_dir,
                storage_dir=storage_dir,
                chunk_size=40,
                chunk_overlap=5,
            )
            embedder = DeterministicEmbedder(settings.embedding_dimension)
            vector_store = MemoryVectorStore()
            answer_generator = SimpleAnswerGenerator()

            builder = OfflineKnowledgeBuilder(
                settings,
                embedder=embedder,
                vector_store=vector_store,
            )
            with patch(
                "rag_app.retrieval.online.create_query_log_store",
                return_value=MemoryQueryLogStore(),
            ):
                pipeline = RAGPipeline(
                    settings,
                    embedder=embedder,
                    vector_store=vector_store,
                    answer_generator=answer_generator,
                )
            report = builder.refresh(reset=True)
            answer = pipeline.query("What does RAG retrieve?")
            chinese_answer = pipeline.query("光猫红灯需要检查什么？")

            self.assertEqual(report.documents_seen, 1)
            self.assertGreaterEqual(report.chunks_embedded, 1)
            self.assertGreaterEqual(report.stored_records, 1)
            self.assertIn("召回上下文摘要", answer.answer)
            self.assertGreaterEqual(len(answer.sources), 1)
            self.assertIn("guide.md", answer.sources[0].chunk.metadata["source"])
            self.assertIsNotNone(answer.trace)
            self.assertGreaterEqual(answer.trace.retrieved_count, 1)
            self.assertIn("用户原始问题", answer.trace.augmented_context)
            self.assertGreater(chinese_answer.sources[0].score, 0)


if __name__ == "__main__":
    unittest.main()
