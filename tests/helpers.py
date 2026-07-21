from __future__ import annotations

import hashlib
import math
from dataclasses import asdict

from rag_app.core.config import Settings
from rag_app.core.models import (
    Chunk,
    OnlineProcessingTrace,
    RAGAnswer,
    RetrievalResult,
    ToolCallTrace,
)
from rag_app.indexing.vector_store import VectorRecord, _rank_vector_records
from rag_app.indexing.vector_store import _search_records_by_error_code
from rag_app.operations.ops import (
    QueryLogRecord,
    FeedbackRecord,
    summarize_feedback,
    summarize_query_logs,
)
from rag_app.core.text_utils import tokenize_for_matching


PUBLIC_TRACE_FIELDS = {
    "request_id",
    "retrieval_mode",
    "vector_store_provider",
    "query_embedding_dimensions",
    "rerank_provider",
    "rerank_model",
    "rerank_applied",
    "rerank_skip_reason",
    "embedding_latency_ms",
    "vector_search_latency_ms",
    "rerank_latency_ms",
}

PUBLIC_SOURCE_FIELDS = {"chunk", "score", "retrieval_score", "rerank_score"}

PUBLIC_SOURCE_METADATA_FIELDS = {
    "source",
    "source_path",
    "collection_name",
    "section_title",
    "title",
    "filename",
    "page_number",
}

PUBLIC_CONTRACT_CANARIES = (
    "SYSTEM_PROMPT_PUBLIC_CONTRACT_CANARY",
    "Bearer PUBLIC_CONTRACT_AUTH_CANARY",
    "sk-public-contract-api-key-canary",
    "PUBLIC_CONTRACT_COPIED_SECRET_CANARY",
    "PUBLIC_CONTRACT_AUGMENTED_CONTEXT_CANARY",
    "PUBLIC_CONTRACT_DEGRADATION_CANARY",
)


def malicious_public_contract_answer() -> RAGAnswer:
    source = RetrievalResult(
        chunk=Chunk(
            id="chunk-public-1",
            document_id="doc-public-1",
            text="公开引用正文",
            metadata={
                "source": "runbook.md",
                "source_path": "kb/runbook.md",
                "collection_name": "ops_default",
                "section_title": "恢复步骤",
                "title": "Public Runbook",
                "filename": "runbook.md",
                "page_number": 7,
                "tenant_id": "tenant-internal",
                "permission_tags": ["ops-admin"],
                "prompt": PUBLIC_CONTRACT_CANARIES[0],
                "authorization": PUBLIC_CONTRACT_CANARIES[1],
                "api_key": PUBLIC_CONTRACT_CANARIES[2],
                "tool_calls": [{"output": PUBLIC_CONTRACT_CANARIES[3]}],
            },
        ),
        score=0.91,
        semantic_score=0.81,
        bm25_score=0.71,
        normalized_bm25_score=0.61,
        keyword_score=0.51,
        retrieval_score=0.83,
        rerank_score=0.97,
    )
    trace = OnlineProcessingTrace(
        request_id="req-public-1",
        created_at="2026-07-21T00:00:00+00:00",
        session_id="session-internal",
        is_follow_up=False,
        original_query=PUBLIC_CONTRACT_CANARIES[0],
        normalized_query=PUBLIC_CONTRACT_CANARIES[1],
        contextual_query=PUBLIC_CONTRACT_CANARIES[2],
        context_terms=[PUBLIC_CONTRACT_CANARIES[3]],
        rewritten_query=PUBLIC_CONTRACT_CANARIES[4],
        retrieval_query=PUBLIC_CONTRACT_CANARIES[5],
        synonym_expansions=[PUBLIC_CONTRACT_CANARIES[0]],
        semantic_expansions=[PUBLIC_CONTRACT_CANARIES[1]],
        query_rewrite_rules=[PUBLIC_CONTRACT_CANARIES[2]],
        intent_label="internal_intent",
        intent_confidence=0.99,
        intent_reason=PUBLIC_CONTRACT_CANARIES[3],
        top_k=10,
        min_similarity_score=0.2,
        relative_score_threshold=0.7,
        retrieval_mode="hybrid",
        semantic_weight=0.7,
        bm25_weight=0.2,
        keyword_weight=0.1,
        retrieval_candidate_k=20,
        rerank_provider="cross_encoder",
        rerank_model="BAAI/bge-reranker-base",
        rerank_candidate_k=10,
        reranked_count=1,
        query_embedding_dimensions=1024,
        retrieved_count=1,
        latency_ms=30.0,
        retrieval_latency_ms=20.0,
        generation_latency_ms=10.0,
        augmented_context=PUBLIC_CONTRACT_CANARIES[4],
        vector_store_provider="pgvector",
        embedding_latency_ms=11.0,
        vector_search_latency_ms=4.0,
        rerank_latency_ms=5.0,
        rerank_applied=True,
        rerank_skip_reason=None,
        degradation_reason=PUBLIC_CONTRACT_CANARIES[5],
        user_id="user-internal",
        tenant_id="tenant-internal",
        permission_tags=("ops-admin",),
        tool_calls=[
            ToolCallTrace(
                tool_name="internal_tool",
                input={"authorization": PUBLIC_CONTRACT_CANARIES[1]},
                output={"api_key": PUBLIC_CONTRACT_CANARIES[2]},
                status="success",
                latency_ms=1.0,
            )
        ],
    )
    return RAGAnswer(
        question="公开问题",
        answer="公开答案",
        sources=[source],
        trace=trace,
    )


class DeterministicEmbedder:
    def __init__(self, dimension: int = 64) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in tokenize_for_matching(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class MemoryVectorStore:
    def __init__(self) -> None:
        self.records: list[VectorRecord] = []

    def count(self) -> int:
        return len(self.records)

    def reload(self) -> None:
        return None

    def clear(self) -> None:
        self.records = []

    def upsert(self, records: list[VectorRecord]) -> int:
        existing = {record.chunk.id: record for record in self.records}
        for record in records:
            existing[record.chunk.id] = record
        self.records = list(existing.values())
        return len(self.records)

    def delete_by_document_ids(self, document_ids: set[str]) -> int:
        before = len(self.records)
        self.records = [
            record
            for record in self.records
            if record.chunk.document_id not in document_ids
        ]
        return before - len(self.records)

    def search(
        self,
        query_embedding: list[float],
        query_text: str | None = None,
        top_k: int = 4,
        min_score: float | None = None,
        relative_score_threshold: float | None = None,
        mode: str = "hybrid",
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        bm25_weight: float | None = None,
        candidate_k: int | None = None,
        tenant_id: str | None = None,
        permission_tags: tuple[str, ...] | list[str] | None = None,
    ) -> list[RetrievalResult]:
        return _rank_vector_records(
            records=self.records,
            query_embedding=query_embedding,
            query_text=query_text,
            top_k=top_k,
            min_score=min_score,
            relative_score_threshold=relative_score_threshold,
            mode=mode,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            bm25_weight=bm25_weight,
            candidate_k=candidate_k,
            tenant_id=tenant_id,
            permission_tags=permission_tags,
        )

    def search_by_error_code(
        self,
        error_code: str,
        top_k: int = 4,
        tenant_id: str | None = None,
        permission_tags: tuple[str, ...] | list[str] | None = None,
    ) -> list[RetrievalResult]:
        return _search_records_by_error_code(
            records=self.records,
            error_code=error_code,
            top_k=top_k,
            tenant_id=tenant_id,
            permission_tags=permission_tags,
        )


class SimpleAnswerGenerator:
    def answer(
        self,
        question: str,
        sources: list[RetrievalResult],
        augmented_context: str | None = None,
    ) -> str:
        del question
        context = augmented_context or ""
        tool_lines = [
            line.removeprefix("结果摘要：").strip()
            for line in context.splitlines()
            if line.startswith("结果摘要：") and line.removeprefix("结果摘要：").strip() != "无"
        ]
        if tool_lines:
            return "工具查询结果：\n" + "\n".join(tool_lines)
        if not sources:
            return "未召回到相关上下文。"
        refs = "\n".join(
            f"- [{index}] {result.chunk.metadata.get('source', 'unknown')}"
            for index, result in enumerate(sources, start=1)
        )
        return f"召回上下文摘要：\n{sources[0].chunk.text}\n\n来源引用：\n{refs}"


class MemoryQueryLogStore:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def append(self, record: QueryLogRecord) -> None:
        self.records.append(asdict(record))

    def tail(self, limit: int = 20) -> list[dict]:
        return self.records[-limit:]

    def summary(self, limit: int = 200) -> dict:
        return summarize_query_logs(self.tail(limit))

    def get(self, request_id: str) -> dict | None:
        for record in reversed(self.records):
            if record.get("request_id") == request_id:
                return record
        return None


class MemoryFeedbackStore:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def append(self, record: FeedbackRecord) -> None:
        self.records.append(asdict(record))

    def tail(self, limit: int = 20) -> list[dict]:
        return self.records[-limit:]

    def summary(self, limit: int = 200) -> dict:
        return summarize_feedback(self.tail(limit))

    def for_request(self, request_id: str) -> list[dict]:
        return [
            record
            for record in self.records
            if record.get("request_id") == request_id
        ]


def production_settings(base_dir, data_dir=None, storage_dir=None, **overrides) -> Settings:
    kwargs = {
        "base_dir": base_dir,
        "data_dir": data_dir or base_dir / "data",
        "storage_dir": storage_dir or base_dir / "storage",
        "collection_name": "test",
        "chunk_size": 80,
        "chunk_overlap": 10,
        "top_k": 2,
        "embedding_provider": "openai",
        "embedding_dimension": 64,
        "llm_provider": "openai",
        "openai_api_key": "test-key",
        "openai_chat_model": "test-chat",
        "openai_embedding_model": "test-embedding",
        "ops_postgres_dsn": "postgresql://rag:pwd@localhost:5432/rag",
        "order_status_postgres_dsn": "postgresql://rag:pwd@localhost:5432/rag",
        "order_status_tool_enabled": False,
        "conversation_memory_provider": "memory",
        "redis_answer_override_enabled": False,
        "feedback_hot_cache_enabled": False,
        "feedback_promotion_enabled": False,
    }
    kwargs.update(overrides)
    return Settings(**kwargs)
