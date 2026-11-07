from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_app.core.models import Chunk
from rag_app.indexing.vector_store import (
    PostgresVectorStore,
    VectorRecord,
    _rank_vector_records,
    create_vector_store,
)
from tests.helpers import production_settings


class VectorStoreRankingTest(unittest.TestCase):
    def test_search_filters_results_below_min_score(self) -> None:
        results = _rank_vector_records(
            records=[
                VectorRecord(
                    chunk=Chunk(id="positive", document_id="doc-1", text="相关文档"),
                    embedding=[1.0, 0.0],
                ),
                VectorRecord(
                    chunk=Chunk(id="negative", document_id="doc-2", text="不相关文档"),
                    embedding=[-1.0, 0.0],
                ),
            ],
            query_embedding=[1.0, 0.0],
            top_k=2,
            min_score=0.0,
        )

        self.assertEqual([result.chunk.id for result in results], ["positive"])

    def test_hybrid_search_uses_bm25_score_to_improve_ranking(self) -> None:
        results = _rank_vector_records(
            records=[
                VectorRecord(
                    chunk=Chunk(
                        id="keyword-match",
                        document_id="doc-1",
                        text="光猫 LOS 红灯处理步骤：检查尾纤和光功率。",
                    ),
                    embedding=[-1.0, 0.0],
                ),
                VectorRecord(
                    chunk=Chunk(
                        id="semantic-only",
                        document_id="doc-2",
                        text="普通装维知识库说明。",
                    ),
                    embedding=[1.0, 0.0],
                ),
            ],
            query_embedding=[1.0, 0.0],
            query_text="光猫 LOS 红灯怎么处理",
            top_k=2,
            mode="hybrid",
            semantic_weight=0.1,
            keyword_weight=0.9,
        )

        self.assertEqual(results[0].chunk.id, "keyword-match")
        self.assertGreater(results[0].bm25_score, 0.0)
        self.assertEqual(results[0].normalized_bm25_score, 1.0)
        self.assertGreater(results[0].score, results[1].score)

    def test_bm25_mode_returns_exact_term_candidate(self) -> None:
        results = _rank_vector_records(
            records=[
                VectorRecord(
                    chunk=Chunk(
                        id="error-code",
                        document_id="doc-1",
                        text="异常码 E203 表示地址资源不存在，需要核对标准地址。",
                    ),
                    embedding=[-1.0, 0.0],
                ),
                VectorRecord(
                    chunk=Chunk(
                        id="general",
                        document_id="doc-2",
                        text="装维业务知识库说明。",
                    ),
                    embedding=[1.0, 0.0],
                ),
            ],
            query_embedding=[1.0, 0.0],
            query_text="E203 是什么意思",
            top_k=2,
            mode="bm25",
            min_score=0.0,
        )

        self.assertEqual([result.chunk.id for result in results], ["error-code"])

    def test_search_applies_tenant_and_permission_filters(self) -> None:
        results = _rank_vector_records(
            records=[
                VectorRecord(
                    chunk=Chunk(
                        id="tenant-a-ops",
                        document_id="doc-1",
                        text="接口超时需要检查下游接口状态。",
                        metadata={
                            "tenant_id": "tenant-a",
                            "permission_tags": ["OPS_L2"],
                        },
                    ),
                    embedding=[1.0, 0.0],
                ),
                VectorRecord(
                    chunk=Chunk(
                        id="tenant-b-ops",
                        document_id="doc-2",
                        text="接口超时需要检查数据库。",
                        metadata={
                            "tenant_id": "tenant-b",
                            "permission_tags": ["OPS_L2"],
                        },
                    ),
                    embedding=[1.0, 0.0],
                ),
            ],
            query_embedding=[1.0, 0.0],
            query_text="接口超时",
            top_k=5,
            min_score=-1.0,
            tenant_id="tenant-a",
            permission_tags=("OPS_L2",),
        )

        self.assertEqual([result.chunk.id for result in results], ["tenant-a-ops"])

    def test_vector_store_factory_uses_postgres(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = production_settings(Path(temp_dir))

            with patch.object(PostgresVectorStore, "__init__", return_value=None) as init:
                store = create_vector_store(settings)

            self.assertIsInstance(store, PostgresVectorStore)
            init.assert_called_once()


if __name__ == "__main__":
    unittest.main()
