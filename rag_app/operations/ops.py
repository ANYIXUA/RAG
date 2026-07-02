"""线上运行日志、反馈闭环和运维摘要。"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from rag_app.core.config import Settings
from rag_app.core.models import RAGAnswer


@dataclass(frozen=True)
class QueryLogRecord:
    """单次在线问答的结构化运行日志。"""

    request_id: str
    created_at: str
    session_id: str | None
    question: str
    contextual_query: str
    rewritten_query: str
    retrieval_query: str
    answer: str
    intent_label: str
    intent_confidence: float
    is_follow_up: bool
    top_k: int
    retrieved_count: int
    reranked_count: int
    source_count: int
    status: str
    latency_ms: float
    retrieval_latency_ms: float
    generation_latency_ms: float
    sources: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    tenant_id: str | None = None
    permission_tags: list[str] | None = None


@dataclass(frozen=True)
class FeedbackRecord:
    """用户或人工质检对一次回答的反馈。"""

    feedback_id: str
    created_at: str
    request_id: str
    session_id: str | None = None
    question: str | None = None
    rating: int | None = None
    useful: bool | None = None
    comment: str | None = None
    expected_answer: str | None = None
    labels: list[str] | None = None


class QueryLogStore(Protocol):
    """查询日志存储接口。"""

    def append(self, record: QueryLogRecord) -> None:
        ...

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        ...

    def summary(self, limit: int = 200) -> dict[str, Any]:
        ...

    def get(self, request_id: str) -> dict[str, Any] | None:
        ...


class FeedbackStore(Protocol):
    """人工反馈存储接口。"""

    def append(self, record: FeedbackRecord) -> None:
        ...

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        ...

    def summary(self, limit: int = 200) -> dict[str, Any]:
        ...

    def for_request(self, request_id: str) -> list[dict[str, Any]]:
        ...


class PostgresQueryLogStore:
    """用 PostgreSQL 保存查询日志，适合生产环境集中查询和统计。"""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._ensure_schema()

    def append(self, record: QueryLogRecord) -> None:
        psycopg, dict_row, jsonb = _import_psycopg()
        del dict_row
        payload = asdict(record)
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO query_logs (
                        request_id, created_at, session_id, question, contextual_query,
                        rewritten_query, retrieval_query, answer, intent_label,
                        intent_confidence, is_follow_up, top_k, retrieved_count,
                        reranked_count, source_count, status, latency_ms,
                        retrieval_latency_ms, generation_latency_ms, sources_json,
                        tool_calls_json, tenant_id, permission_tags_json
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    )
                    ON CONFLICT (request_id) DO UPDATE SET
                        created_at = EXCLUDED.created_at,
                        session_id = EXCLUDED.session_id,
                        question = EXCLUDED.question,
                        contextual_query = EXCLUDED.contextual_query,
                        rewritten_query = EXCLUDED.rewritten_query,
                        retrieval_query = EXCLUDED.retrieval_query,
                        answer = EXCLUDED.answer,
                        intent_label = EXCLUDED.intent_label,
                        intent_confidence = EXCLUDED.intent_confidence,
                        is_follow_up = EXCLUDED.is_follow_up,
                        top_k = EXCLUDED.top_k,
                        retrieved_count = EXCLUDED.retrieved_count,
                        reranked_count = EXCLUDED.reranked_count,
                        source_count = EXCLUDED.source_count,
                        status = EXCLUDED.status,
                        latency_ms = EXCLUDED.latency_ms,
                        retrieval_latency_ms = EXCLUDED.retrieval_latency_ms,
                        generation_latency_ms = EXCLUDED.generation_latency_ms,
                        sources_json = EXCLUDED.sources_json,
                        tool_calls_json = EXCLUDED.tool_calls_json,
                        tenant_id = EXCLUDED.tenant_id,
                        permission_tags_json = EXCLUDED.permission_tags_json
                    """,
                    (
                        record.request_id,
                        record.created_at,
                        record.session_id,
                        record.question,
                        record.contextual_query,
                        record.rewritten_query,
                        record.retrieval_query,
                        record.answer,
                        record.intent_label,
                        record.intent_confidence,
                        record.is_follow_up,
                        record.top_k,
                        record.retrieved_count,
                        record.reranked_count,
                        record.source_count,
                        record.status,
                        record.latency_ms,
                        record.retrieval_latency_ms,
                        record.generation_latency_ms,
                        jsonb(payload["sources"]),
                        jsonb(payload["tool_calls"]),
                        record.tenant_id,
                        jsonb(record.permission_tags or []),
                    ),
                )

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM query_logs ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
                rows = cursor.fetchall()
        return [_postgres_query_row_to_dict(row) for row in reversed(rows)]

    def get(self, request_id: str) -> dict[str, Any] | None:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM query_logs WHERE request_id = %s",
                    (request_id,),
                )
                row = cursor.fetchone()
        return _postgres_query_row_to_dict(row) if row else None

    def summary(self, limit: int = 200) -> dict[str, Any]:
        return summarize_query_logs(self.tail(limit=limit))

    def _ensure_schema(self) -> None:
        psycopg, _, _ = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS query_logs (
                        request_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        session_id TEXT,
                        question TEXT NOT NULL,
                        contextual_query TEXT NOT NULL,
                        rewritten_query TEXT NOT NULL,
                        retrieval_query TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        intent_label TEXT NOT NULL,
                        intent_confidence DOUBLE PRECISION NOT NULL,
                        is_follow_up BOOLEAN NOT NULL,
                        top_k INTEGER NOT NULL,
                        retrieved_count INTEGER NOT NULL,
                        reranked_count INTEGER NOT NULL,
                        source_count INTEGER NOT NULL,
                        status TEXT NOT NULL,
                        latency_ms DOUBLE PRECISION NOT NULL,
                        retrieval_latency_ms DOUBLE PRECISION NOT NULL,
                        generation_latency_ms DOUBLE PRECISION NOT NULL,
                        sources_json JSONB NOT NULL,
                        tool_calls_json JSONB NOT NULL DEFAULT '[]'::JSONB,
                        tenant_id TEXT,
                        permission_tags_json JSONB NOT NULL DEFAULT '[]'::JSONB
                    )
                    """
                )
                cursor.execute(
                    "ALTER TABLE query_logs "
                    "ADD COLUMN IF NOT EXISTS tool_calls_json JSONB NOT NULL DEFAULT '[]'::JSONB"
                )
                cursor.execute(
                    "ALTER TABLE query_logs "
                    "ADD COLUMN IF NOT EXISTS tenant_id TEXT"
                )
                cursor.execute(
                    "ALTER TABLE query_logs "
                    "ADD COLUMN IF NOT EXISTS permission_tags_json JSONB NOT NULL DEFAULT '[]'::JSONB"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_query_logs_status ON query_logs(status)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_query_logs_intent ON query_logs(intent_label)"
                )


class PostgresFeedbackStore:
    """用 PostgreSQL 保存人工反馈。"""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._ensure_schema()

    def append(self, record: FeedbackRecord) -> None:
        psycopg, dict_row, jsonb = _import_psycopg()
        del dict_row
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feedback (
                        feedback_id, created_at, request_id, session_id, question,
                        rating, useful, comment, expected_answer, labels_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (feedback_id) DO UPDATE SET
                        created_at = EXCLUDED.created_at,
                        request_id = EXCLUDED.request_id,
                        session_id = EXCLUDED.session_id,
                        question = EXCLUDED.question,
                        rating = EXCLUDED.rating,
                        useful = EXCLUDED.useful,
                        comment = EXCLUDED.comment,
                        expected_answer = EXCLUDED.expected_answer,
                        labels_json = EXCLUDED.labels_json
                    """,
                    (
                        record.feedback_id,
                        record.created_at,
                        record.request_id,
                        record.session_id,
                        record.question,
                        record.rating,
                        record.useful,
                        record.comment,
                        record.expected_answer,
                        jsonb(record.labels or []),
                    ),
                )

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM feedback ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
                rows = cursor.fetchall()
        return [_postgres_feedback_row_to_dict(row) for row in reversed(rows)]

    def for_request(self, request_id: str) -> list[dict[str, Any]]:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM feedback WHERE request_id = %s ORDER BY created_at ASC",
                    (request_id,),
                )
                rows = cursor.fetchall()
        return [_postgres_feedback_row_to_dict(row) for row in rows]

    def summary(self, limit: int = 200) -> dict[str, Any]:
        return summarize_feedback(self.tail(limit=limit))

    def _ensure_schema(self) -> None:
        psycopg, _, _ = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS feedback (
                        feedback_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        request_id TEXT NOT NULL,
                        session_id TEXT,
                        question TEXT,
                        rating INTEGER,
                        useful BOOLEAN,
                        comment TEXT,
                        expected_answer TEXT,
                        labels_json JSONB NOT NULL
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_feedback_request_id ON feedback(request_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at)"
                )


def new_request_id() -> str:
    """生成一次请求的追踪 ID。"""

    return uuid4().hex


def new_feedback_id() -> str:
    """生成一条反馈记录 ID。"""

    return uuid4().hex


def utc_now() -> str:
    """返回 UTC ISO 时间。"""

    return datetime.now(timezone.utc).isoformat()


def build_query_log_record(
    request_id: str,
    answer: RAGAnswer,
    latency_ms: float,
    retrieval_latency_ms: float,
    generation_latency_ms: float,
) -> QueryLogRecord:
    """从问答结果构造结构化查询日志。"""

    trace = answer.trace
    if trace is None:
        raise ValueError("answer.trace is required to build query log")
    has_tool_answer = any(
        call.status in {"success", "not_found"}
        for call in trace.tool_calls
    )
    if trace.override_hit:
        status = "override_answered"
    else:
        status = "answered" if answer.sources or has_tool_answer else "no_context"
    # 查询日志只保存来源快照和核心分数，避免把完整增强上下文重复写入运行库。
    return QueryLogRecord(
        request_id=request_id,
        created_at=utc_now(),
        session_id=trace.session_id,
        question=answer.question,
        contextual_query=trace.contextual_query,
        rewritten_query=trace.rewritten_query,
        retrieval_query=trace.retrieval_query,
        answer=answer.answer,
        intent_label=trace.intent_label,
        intent_confidence=trace.intent_confidence,
        is_follow_up=trace.is_follow_up,
        top_k=trace.top_k,
        retrieved_count=trace.retrieved_count,
        reranked_count=trace.reranked_count,
        source_count=len(answer.sources),
        status=status,
        latency_ms=round(latency_ms, 3),
        retrieval_latency_ms=round(retrieval_latency_ms, 3),
        generation_latency_ms=round(generation_latency_ms, 3),
        sources=[
            {
                "rank": index,
                "chunk_id": result.chunk.id,
                "source": result.chunk.metadata.get("source"),
                "section_title": result.chunk.metadata.get("section_title"),
                "score": round(result.score, 6),
                "retrieval_score": _optional_round(result.retrieval_score),
                "rerank_score": _optional_round(result.rerank_score),
            }
            for index, result in enumerate(answer.sources, start=1)
        ],
        tool_calls=[asdict(call) for call in trace.tool_calls],
        tenant_id=trace.tenant_id,
        permission_tags=list(trace.permission_tags),
    )


def build_feedback_record(
    request_id: str,
    session_id: str | None = None,
    question: str | None = None,
    rating: int | None = None,
    useful: bool | None = None,
    comment: str | None = None,
    expected_answer: str | None = None,
    labels: list[str] | None = None,
) -> FeedbackRecord:
    """构造人工反馈记录。"""

    if rating is not None and not 1 <= rating <= 5:
        raise ValueError("rating must be between 1 and 5")
    return FeedbackRecord(
        feedback_id=new_feedback_id(),
        created_at=utc_now(),
        request_id=request_id,
        session_id=session_id,
        question=question,
        rating=rating,
        useful=useful,
        comment=comment,
        expected_answer=expected_answer,
        labels=labels or [],
    )


def create_query_log_store(settings: Settings) -> QueryLogStore:
    """根据配置创建查询日志存储。"""

    if settings.ops_store_provider == "postgresql":
        assert settings.ops_postgres_dsn is not None
        return PostgresQueryLogStore(settings.ops_postgres_dsn)
    raise ValueError(f"Unsupported ops store provider: {settings.ops_store_provider}")


def create_feedback_store(settings: Settings) -> FeedbackStore:
    """根据配置创建反馈存储。"""

    if settings.ops_store_provider == "postgresql":
        assert settings.ops_postgres_dsn is not None
        return PostgresFeedbackStore(settings.ops_postgres_dsn)
    raise ValueError(f"Unsupported ops store provider: {settings.ops_store_provider}")


def build_request_trace(settings: Settings, request_id: str) -> dict[str, Any]:
    """按 request_id 聚合查询日志和人工反馈，便于排查完整链路。"""

    # 灰度排查时，一个 request_id 能把“当时怎么检索”和“人工怎么反馈”串起来。
    query_store = create_query_log_store(settings)
    feedback_store = create_feedback_store(settings)
    query_log = query_store.get(request_id)
    feedback_items = feedback_store.for_request(request_id)
    return {
        "request_id": request_id,
        "found": query_log is not None or bool(feedback_items),
        "query_log": query_log,
        "feedback": feedback_items,
    }


def summarize_query_logs(records: list[dict[str, Any]]) -> dict[str, Any]:
    """统计查询日志摘要。"""

    # 摘要面向灰度看板：成功/无上下文、平均耗时和意图分布是最先看的几个指标。
    total = len(records)
    if total == 0:
        return {
            "total": 0,
            "success": 0,
            "no_context": 0,
            "avg_latency_ms": 0.0,
            "avg_retrieval_latency_ms": 0.0,
            "avg_generation_latency_ms": 0.0,
            "intent_counts": {},
        }

    status_counts = _count_by(records, "status")
    intent_counts = _count_by(records, "intent_label")
    return {
        "total": total,
        "success": status_counts.get("answered", 0),
        "no_context": status_counts.get("no_context", 0),
        "avg_latency_ms": _avg(records, "latency_ms"),
        "avg_retrieval_latency_ms": _avg(records, "retrieval_latency_ms"),
        "avg_generation_latency_ms": _avg(records, "generation_latency_ms"),
        "intent_counts": intent_counts,
    }


def summarize_feedback(records: list[dict[str, Any]]) -> dict[str, Any]:
    """统计人工反馈摘要。"""

    total = len(records)
    if total == 0:
        return {
            "total": 0,
            "useful": 0,
            "not_useful": 0,
            "avg_rating": None,
            "label_counts": {},
        }
    ratings = [
        float(record["rating"])
        for record in records
        if record.get("rating") is not None
    ]
    label_counts: dict[str, int] = {}
    for record in records:
        for label in record.get("labels") or []:
            label_counts[label] = label_counts.get(label, 0) + 1
    useful_count = sum(1 for record in records if record.get("useful") is True)
    not_useful_count = sum(1 for record in records if record.get("useful") is False)
    return {
        "total": total,
        "useful": useful_count,
        "not_useful": not_useful_count,
        "avg_rating": round(sum(ratings) / len(ratings), 3) if ratings else None,
        "label_counts": label_counts,
    }


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _avg(records: list[dict[str, Any]], key: str) -> float:
    values = [float(record.get(key) or 0.0) for record in records]
    if not values:
        return 0.0
    return round(sum(values) / len(values), 3)


def _optional_round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


def _postgres_query_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": row["request_id"],
        "created_at": row["created_at"],
        "session_id": row["session_id"],
        "question": row["question"],
        "contextual_query": row["contextual_query"],
        "rewritten_query": row["rewritten_query"],
        "retrieval_query": row["retrieval_query"],
        "answer": row["answer"],
        "intent_label": row["intent_label"],
        "intent_confidence": row["intent_confidence"],
        "is_follow_up": bool(row["is_follow_up"]),
        "top_k": row["top_k"],
        "retrieved_count": row["retrieved_count"],
        "reranked_count": row["reranked_count"],
        "source_count": row["source_count"],
        "status": row["status"],
        "latency_ms": row["latency_ms"],
        "retrieval_latency_ms": row["retrieval_latency_ms"],
        "generation_latency_ms": row["generation_latency_ms"],
        "sources": _decode_json_value(row["sources_json"], default=[]),
        "tool_calls": _decode_json_value(row.get("tool_calls_json"), default=[]),
        "tenant_id": row.get("tenant_id"),
        "permission_tags": _decode_json_value(row.get("permission_tags_json"), default=[]),
    }


def _postgres_feedback_row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "feedback_id": row["feedback_id"],
        "created_at": row["created_at"],
        "request_id": row["request_id"],
        "session_id": row["session_id"],
        "question": row["question"],
        "rating": row["rating"],
        "useful": row["useful"],
        "comment": row["comment"],
        "expected_answer": row["expected_answer"],
        "labels": _decode_json_value(row["labels_json"], default=[]),
    }


def _decode_json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _import_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PostgreSQL 存储需要安装 psycopg：pip install -e \".[pgsql]\""
        ) from exc
    return psycopg, dict_row, Jsonb
