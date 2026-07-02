"""Feedback-driven hot cache and long-term knowledge promotion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from rag_app.core.config import Settings
from rag_app.operations.knowledge_lifecycle import (
    create_knowledge_build_job,
    save_uploaded_text,
)
from rag_app.operations.ops import FeedbackRecord, QueryLogStore
from rag_app.retrieval.answer_memory import AnswerMemoryStore


@dataclass(frozen=True)
class PromotionCandidate:
    filename: str
    content: str
    source_type: str
    tenant_id: str
    permission_tags: tuple[str, ...]
    request_id: str
    feedback_id: str
    activate_when_ready: bool


@dataclass(frozen=True)
class FeedbackMemoryResult:
    hot_cache_status: str = "skipped"
    promotion_status: str = "skipped"
    upload_id: str | None = None
    job_id: str | None = None
    error: str | None = None


class PromotionSink(Protocol):
    def promote(self, candidate: PromotionCandidate) -> dict[str, Any]:
        ...


class KnowledgeLifecyclePromotionSink:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def promote(self, candidate: PromotionCandidate) -> dict[str, Any]:
        upload = save_uploaded_text(
            self.settings,
            filename=candidate.filename,
            content=candidate.content,
            content_type="text/markdown",
            metadata={
                "source_type": candidate.source_type,
                "business_module": "feedback_memory",
                "tenant_id": candidate.tenant_id,
                "permission_tags": ",".join(candidate.permission_tags),
                "request_id": candidate.request_id,
                "feedback_id": candidate.feedback_id,
            },
        )
        job = None
        if self.settings.feedback_promotion_auto_build:
            job = create_knowledge_build_job(
                self.settings,
                upload_ids=[upload.upload_id],
                activate_when_ready=candidate.activate_when_ready,
                description=f"反馈自动沉淀：{candidate.feedback_id}",
            )
        return {
            "upload_id": upload.upload_id,
            "job_id": job.job_id if job else None,
        }


class FeedbackMemoryService:
    def __init__(
        self,
        *,
        settings: Settings,
        answer_memory: AnswerMemoryStore,
        query_log_store: QueryLogStore,
        promotion_sink: PromotionSink | None = None,
    ) -> None:
        self.settings = settings
        self.answer_memory = answer_memory
        self.query_log_store = query_log_store
        self.promotion_sink = promotion_sink or KnowledgeLifecyclePromotionSink(settings)

    def handle_feedback(self, feedback: FeedbackRecord) -> FeedbackMemoryResult:
        query_log = self.query_log_store.get(feedback.request_id)
        if query_log is None:
            return FeedbackMemoryResult(error="query_log_not_found")

        question = str(feedback.question or query_log.get("question") or "").strip()
        if not question:
            return FeedbackMemoryResult(error="question_missing")
        tenant_id = str(query_log.get("tenant_id") or self.settings.default_tenant_id)
        permission_tags = tuple(query_log.get("permission_tags") or self.settings.default_permission_tags)

        if _is_negative_feedback(feedback):
            self.answer_memory.record_negative_feedback(
                question=question,
                tenant_id=tenant_id,
                permission_tags=permission_tags,
                request_id=feedback.request_id,
                feedback_id=feedback.feedback_id,
                labels=tuple(feedback.labels or ()),
            )
            return FeedbackMemoryResult(hot_cache_status="negative_recorded")

        if not _is_positive_feedback(feedback, self.settings.feedback_hot_cache_min_rating):
            return FeedbackMemoryResult(hot_cache_status="skipped", promotion_status="skipped")

        answer = (feedback.expected_answer or query_log.get("answer") or "").strip()
        if not answer:
            return FeedbackMemoryResult(error="trusted_answer_missing")

        hot_cache_status = "skipped"
        if self.settings.feedback_hot_cache_enabled:
            self.answer_memory.upsert_hot_cache(
                question=question,
                answer=answer,
                tenant_id=tenant_id,
                permission_tags=permission_tags,
                request_id=feedback.request_id,
                feedback_id=feedback.feedback_id,
                ttl_seconds=self.settings.feedback_hot_cache_ttl_seconds,
            )
            hot_cache_status = "written"

        if self.answer_memory.has_transient_manual_override(
            question,
            tenant_id=tenant_id,
            permission_tags=permission_tags,
        ):
            return FeedbackMemoryResult(
                hot_cache_status=hot_cache_status,
                promotion_status="skipped_transient_override",
            )

        if not self.settings.feedback_promotion_enabled:
            return FeedbackMemoryResult(
                hot_cache_status=hot_cache_status,
                promotion_status="skipped",
            )

        candidate = _build_candidate(
            feedback=feedback,
            query_log=query_log,
            question=question,
            answer=answer,
            tenant_id=tenant_id,
            permission_tags=permission_tags,
            activate_when_ready=self.settings.feedback_promotion_auto_activate,
        )
        promoted = self.promotion_sink.promote(candidate)
        return FeedbackMemoryResult(
            hot_cache_status=hot_cache_status,
            promotion_status="queued",
            upload_id=promoted.get("upload_id"),
            job_id=promoted.get("job_id"),
        )


def _is_positive_feedback(feedback: FeedbackRecord, min_rating: int) -> bool:
    if feedback.useful is True:
        return True
    return feedback.rating is not None and feedback.rating >= min_rating


def _is_negative_feedback(feedback: FeedbackRecord) -> bool:
    if feedback.useful is False:
        return True
    return feedback.rating is not None and feedback.rating <= 2


def _build_candidate(
    *,
    feedback: FeedbackRecord,
    query_log: dict[str, Any],
    question: str,
    answer: str,
    tenant_id: str,
    permission_tags: tuple[str, ...],
    activate_when_ready: bool,
) -> PromotionCandidate:
    feedback_id = feedback.feedback_id
    request_id = feedback.request_id
    content = "\n".join(
        [
            "---",
            "knowledge_status: approved",
            "source_type: feedback_promotion",
            "business_module: feedback_memory",
            f"tenant_id: {tenant_id}",
            f"permission_tags: {','.join(permission_tags)}",
            f"request_id: {request_id}",
            f"feedback_id: {feedback_id}",
            "---",
            "",
            "# 问题",
            "",
            question,
            "",
            "# 标准回答",
            "",
            answer,
            "",
            "# 检索线索",
            "",
            f"- contextual_query: {query_log.get('contextual_query') or ''}",
            f"- retrieval_query: {query_log.get('retrieval_query') or ''}",
        ]
    )
    return PromotionCandidate(
        filename=f"feedback_{feedback_id}.md",
        content=content,
        source_type="feedback_promotion",
        tenant_id=tenant_id,
        permission_tags=permission_tags,
        request_id=request_id,
        feedback_id=feedback_id,
        activate_when_ready=activate_when_ready,
    )
