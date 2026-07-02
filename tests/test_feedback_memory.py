import unittest

from rag_app.operations.feedback_memory import FeedbackMemoryService, PromotionCandidate
from rag_app.operations.ops import QueryLogRecord, build_feedback_record
from rag_app.retrieval.answer_memory import (
    AnswerOverrideInput,
    MemoryAnswerMemoryStore,
)
from tests.helpers import MemoryQueryLogStore, production_settings


class FeedbackMemoryTest(unittest.TestCase):
    def test_positive_feedback_writes_hot_cache_with_expected_answer(self) -> None:
        query_store = MemoryQueryLogStore()
        query_store.append(_query_log())
        answer_memory = MemoryAnswerMemoryStore()
        service = FeedbackMemoryService(
            settings=_settings(),
            answer_memory=answer_memory,
            query_log_store=query_store,
            promotion_sink=_FakePromotionSink(),
        )
        feedback = build_feedback_record(
            request_id="req-1",
            rating=5,
            useful=True,
            expected_answer="标准答案：系统故障时请稍后再试。",
            labels=["good_answer"],
        )

        result = service.handle_feedback(feedback)
        hit = answer_memory.lookup(
            "系统是不是故障了？",
            tenant_id="tenant-a",
            permission_tags=("public",),
        )

        self.assertEqual(result.hot_cache_status, "written")
        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.answer, "标准答案：系统故障时请稍后再试。")
        self.assertEqual(hit.answer_source, "redis_hot_cache")

    def test_negative_feedback_only_records_stats(self) -> None:
        query_store = MemoryQueryLogStore()
        query_store.append(_query_log())
        answer_memory = MemoryAnswerMemoryStore()
        service = FeedbackMemoryService(
            settings=_settings(),
            answer_memory=answer_memory,
            query_log_store=query_store,
            promotion_sink=_FakePromotionSink(),
        )
        feedback = build_feedback_record(
            request_id="req-1",
            rating=1,
            useful=False,
            comment="答错了",
            labels=["bad_answer"],
        )

        result = service.handle_feedback(feedback)
        hit = answer_memory.lookup(
            "系统是不是故障了？",
            tenant_id="tenant-a",
            permission_tags=("public",),
        )
        stats = answer_memory.get_negative_stats(
            "系统是不是故障了？",
            tenant_id="tenant-a",
            permission_tags=("public",),
        )

        self.assertEqual(result.hot_cache_status, "negative_recorded")
        self.assertEqual(result.promotion_status, "skipped")
        self.assertIsNone(hit)
        self.assertIsNotNone(stats)
        assert stats is not None
        self.assertEqual(stats.count, 1)
        self.assertIn("bad_answer", stats.labels)

    def test_positive_feedback_creates_long_term_candidate_without_auto_activate(self) -> None:
        query_store = MemoryQueryLogStore()
        query_store.append(_query_log())
        answer_memory = MemoryAnswerMemoryStore()
        promotion_sink = _FakePromotionSink()
        service = FeedbackMemoryService(
            settings=_settings(),
            answer_memory=answer_memory,
            query_log_store=query_store,
            promotion_sink=promotion_sink,
        )
        feedback = build_feedback_record(
            request_id="req-1",
            rating=5,
            useful=True,
            expected_answer="标准答案：系统恢复后可重新发起查询。",
            labels=["promote"],
        )

        result = service.handle_feedback(feedback)

        self.assertEqual(result.promotion_status, "queued")
        self.assertEqual(len(promotion_sink.candidates), 1)
        candidate = promotion_sink.candidates[0]
        self.assertEqual(candidate.source_type, "feedback_promotion")
        self.assertFalse(candidate.activate_when_ready)
        self.assertIn("source_type: feedback_promotion", candidate.content)
        self.assertIn("标准答案：系统恢复后可重新发起查询。", candidate.content)

    def test_manual_incident_override_is_not_promoted(self) -> None:
        query_store = MemoryQueryLogStore()
        query_store.append(_query_log())
        answer_memory = MemoryAnswerMemoryStore()
        answer_memory.upsert_override(
            AnswerOverrideInput(
                question="系统是不是故障了？",
                answer="系统当前故障，请稍后再试。",
                tenant_id="tenant-a",
                permission_tags=("public",),
                category="incident",
                promote_to_long_term=True,
            )
        )
        promotion_sink = _FakePromotionSink()
        service = FeedbackMemoryService(
            settings=_settings(),
            answer_memory=answer_memory,
            query_log_store=query_store,
            promotion_sink=promotion_sink,
        )
        feedback = build_feedback_record(
            request_id="req-1",
            rating=5,
            useful=True,
            expected_answer="系统当前故障，请稍后再试。",
        )

        result = service.handle_feedback(feedback)

        self.assertEqual(result.promotion_status, "skipped_transient_override")
        self.assertEqual(promotion_sink.candidates, [])


class _FakePromotionSink:
    def __init__(self) -> None:
        self.candidates: list[PromotionCandidate] = []

    def promote(self, candidate: PromotionCandidate) -> dict:
        self.candidates.append(candidate)
        return {"upload_id": "upload-1", "job_id": "job-1"}


def _query_log() -> QueryLogRecord:
    return QueryLogRecord(
        request_id="req-1",
        created_at="2026-06-23T00:00:00+00:00",
        session_id="s-1",
        question="系统是不是故障了？",
        contextual_query="系统是不是故障了？",
        rewritten_query="系统是不是故障了？",
        retrieval_query="系统是不是故障了？",
        answer="系统状态请以公告为准。",
        intent_label="general_knowledge",
        intent_confidence=0.8,
        is_follow_up=False,
        top_k=1,
        retrieved_count=1,
        reranked_count=1,
        source_count=1,
        status="answered",
        latency_ms=1.0,
        retrieval_latency_ms=0.5,
        generation_latency_ms=0.5,
        sources=[],
        tool_calls=[],
        tenant_id="tenant-a",
        permission_tags=["public"],
    )


def _base_dir():
    from pathlib import Path

    return Path(".").resolve()


def _settings():
    return production_settings(
        _base_dir(),
        feedback_hot_cache_enabled=True,
        feedback_promotion_enabled=True,
        feedback_promotion_auto_build=True,
        feedback_promotion_auto_activate=False,
    )


if __name__ == "__main__":
    unittest.main()
