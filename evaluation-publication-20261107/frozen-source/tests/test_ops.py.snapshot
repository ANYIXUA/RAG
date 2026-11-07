from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_app.core.models import Chunk, OnlineProcessingTrace, RAGAnswer, RetrievalResult
from rag_app.operations.ops import (
    PostgresFeedbackStore,
    PostgresQueryLogStore,
    build_feedback_record,
    build_query_log_record,
    create_feedback_store,
    create_query_log_store,
    summarize_feedback,
    summarize_query_logs,
)
from tests.helpers import production_settings


class OpsTest(unittest.TestCase):
    def test_query_log_record_summarizes_answer(self) -> None:
        record = build_query_log_record(
            request_id="req-1",
            answer=_answer(),
            latency_ms=12.345,
            retrieval_latency_ms=3.2,
            generation_latency_ms=7.8,
        )

        summary = summarize_query_logs([record.__dict__])

        self.assertEqual(record.status, "answered")
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["success"], 1)
        self.assertEqual(summary["intent_counts"]["recommend_solution"], 1)

    def test_feedback_record_summarizes_feedback(self) -> None:
        record = build_feedback_record(
            request_id="req-1",
            rating=2,
            useful=False,
            comment="召回不准",
            labels=["bad_retrieval"],
        )

        summary = summarize_feedback([record.__dict__])

        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["not_useful"], 1)
        self.assertEqual(summary["avg_rating"], 2.0)
        self.assertEqual(summary["label_counts"]["bad_retrieval"], 1)

    def test_feedback_rating_must_be_between_one_and_five(self) -> None:
        with self.assertRaises(ValueError):
            build_feedback_record(request_id="req-1", rating=6)

    def test_store_factories_create_postgres_stores(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = production_settings(Path(temp_dir))

            with (
                patch.object(PostgresQueryLogStore, "__init__", return_value=None),
                patch.object(PostgresFeedbackStore, "__init__", return_value=None),
            ):
                query_store = create_query_log_store(settings)
                feedback_store = create_feedback_store(settings)

            self.assertIsInstance(query_store, PostgresQueryLogStore)
            self.assertIsInstance(feedback_store, PostgresFeedbackStore)


def _answer() -> RAGAnswer:
    chunk = Chunk(
        id="c1",
        document_id="d1",
        text="光猫 LOS 红灯需要检查尾纤。",
        metadata={
            "source": "fault_cases.md",
            "section_title": "光猫 LOS 红灯",
        },
    )
    trace = OnlineProcessingTrace(
        request_id="req-1",
        created_at="2026-05-05T00:00:00+00:00",
        session_id="s1",
        is_follow_up=False,
        original_query="光猫红灯咋办",
        normalized_query="光猫红灯咋办",
        contextual_query="光猫红灯咋办",
        context_terms=[],
        rewritten_query="光猫 LOS 红灯怎么处理",
        retrieval_query="光猫 LOS 红灯怎么处理",
        synonym_expansions=["ONU"],
        semantic_expansions=["排查步骤"],
        query_rewrite_rules=["故障现象标准化"],
        intent_label="recommend_solution",
        intent_confidence=0.85,
        intent_reason="问题在询问现场处理办法。",
        top_k=1,
        min_similarity_score=0.05,
        relative_score_threshold=0.35,
        retrieval_mode="hybrid",
        semantic_weight=0.7,
        bm25_weight=0.3,
        keyword_weight=0.3,
        retrieval_candidate_k=20,
        rerank_provider="none",
        rerank_model="none",
        rerank_candidate_k=20,
        reranked_count=1,
        query_embedding_dimensions=64,
        retrieved_count=1,
        latency_ms=12.345,
        retrieval_latency_ms=3.2,
        generation_latency_ms=7.8,
        augmented_context="context",
    )
    return RAGAnswer(
        question="光猫红灯咋办",
        answer="检查尾纤。[1]",
        sources=[RetrievalResult(chunk=chunk, score=0.9, retrieval_score=0.9)],
        trace=trace,
    )


if __name__ == "__main__":
    unittest.main()
