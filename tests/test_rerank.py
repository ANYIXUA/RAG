import unittest
from pathlib import Path
import sys
import types
from unittest.mock import patch

from rag_app.core.models import Chunk, RetrievalResult
from rag_app.retrieval.rerank import CrossEncoderReranker, NoopReranker, create_reranker
from tests.helpers import production_settings


class RerankTest(unittest.TestCase):
    def test_cross_encoder_pairs_all_candidates_and_sorts_before_truncation(self):
        from unittest.mock import Mock
        reranker = object.__new__(CrossEncoderReranker)
        reranker.model = Mock()
        reranker.model.predict.return_value = [-3.0, -5.0, -1.0]
        results = [RetrievalResult(Chunk(cid, 'doc', text), score)
                   for cid, text, score in [('a', '全文 A', .9), ('b', '全文 B', .8), ('c', '全文 C', .7)]]
        output = reranker.rerank('原始问题', results, top_k=2)
        reranker.model.predict.assert_called_once_with([
            ('原始问题', '全文 A'), ('原始问题', '全文 B'), ('原始问题', '全文 C')])
        self.assertEqual([r.chunk.id for r in output], ['c', 'a'])
        self.assertEqual([r.rerank_score for r in output], [-1., -3.])
        self.assertEqual([r.retrieval_score for r in output], [.7, .9])
        self.assertEqual([r.score for r in results], [.9, .8, .7])

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

    def test_create_reranker_builds_cross_encoder_provider(self) -> None:
        module = types.ModuleType("sentence_transformers")

        class FakeCrossEncoder:
            def __init__(self, model_name: str) -> None:
                self.model_name = model_name

            def predict(self, pairs):
                return [0.5 for _ in pairs]

        module.CrossEncoder = FakeCrossEncoder
        settings = production_settings(
            Path(".").resolve(),
            data_dir=Path(".").resolve(),
            storage_dir=Path(".").resolve(),
            chunk_size=100,
            chunk_overlap=10,
            rerank_provider="cross-encoder",
            rerank_model="test-cross-encoder",
        )

        with patch.dict(sys.modules, {"sentence_transformers": module}):
            reranker = create_reranker(settings)

        self.assertTrue(reranker.enabled)
        self.assertEqual(reranker.provider_name, "cross-encoder")
        self.assertEqual(reranker.model_name, "test-cross-encoder")


if __name__ == "__main__":
    unittest.main()
