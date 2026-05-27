import unittest
from pathlib import Path

from rag_app.core.models import Chunk, RetrievalResult
from rag_app.retrieval.rerank import NoopReranker, create_reranker
from tests.helpers import production_settings


class RerankTest(unittest.TestCase):
    def test_noop_reranker_keeps_order_and_sets_retrieval_score(self) -> None:
        reranker = NoopReranker()
        results = [
            RetrievalResult(
                chunk=Chunk(id="a", document_id="doc-1", text="A"),
                score=0.8,
            ),
            RetrievalResult(
                chunk=Chunk(id="b", document_id="doc-2", text="B"),
                score=0.5,
            ),
        ]

        reranked = reranker.rerank("query", results, top_k=1)

        self.assertEqual(len(reranked), 1)
        self.assertEqual(reranked[0].chunk.id, "a")
        self.assertEqual(reranked[0].retrieval_score, 0.8)
        self.assertIsNone(reranked[0].rerank_score)

    def test_create_reranker_returns_noop_for_none_provider(self) -> None:
        base_dir = Path(".").resolve()
        settings = production_settings(
            base_dir,
            data_dir=base_dir,
            storage_dir=base_dir,
            chunk_size=100,
            chunk_overlap=10,
            rerank_provider="none",
        )
        reranker = create_reranker(settings)
        self.assertFalse(reranker.enabled)
        self.assertEqual(reranker.provider_name, "none")


if __name__ == "__main__":
    unittest.main()
