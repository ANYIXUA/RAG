from __future__ import annotations

import hashlib
import math
from dataclasses import asdict

from rag_app.core.config import Settings
from rag_app.core.models import RetrievalResult
from rag_app.indexing.vector_store import VectorRecord, _rank_vector_records
from rag_app.indexing.vector_store import _search_records_by_error_code
from rag_app.operations.ops import (
    QueryLogRecord,
    FeedbackRecord,
    summarize_feedback,
    summarize_query_logs,
)
from rag_app.core.text_utils import tokenize_for_matching


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
    }
    kwargs.update(overrides)
    return Settings(**kwargs)
