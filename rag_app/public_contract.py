"""面向跨服务调用方的最小公开响应契约。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rag_app.core.models import RAGAnswer, RetrievalResult


PUBLIC_TRACE_FIELDS = (
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
)

PUBLIC_SOURCE_METADATA_FIELDS = (
    "source",
    "source_path",
    "collection_name",
    "section_title",
    "section_path",
    "title",
    "filename",
    "page_number",
    "slide_number",
    "time_range",
    "timestamp_range",
    "business_module",
)

PUBLIC_STREAM_ERROR = {
    "code": "STREAM_QUERY_ERROR",
    "message": "查询流处理失败",
}


def public_answer_payload(answer: RAGAnswer | Mapping[str, Any]) -> dict[str, Any]:
    """把内部 RAGAnswer 投影为稳定、无内部上下文的公开 DTO。"""

    trace = _field(answer, "trace")
    request_id = _field(answer, "request_id")
    if request_id is None and trace is not None:
        request_id = _field(trace, "request_id")
    sources = _field(answer, "sources")
    if not isinstance(sources, (list, tuple)):
        sources = []
    return {
        "question": _field(answer, "question"),
        "answer": _field(answer, "answer"),
        "sources": [public_source_payload(source) for source in sources],
        "request_id": request_id,
        "trace": public_trace_payload(trace),
    }


def public_trace_payload(trace: object | None) -> dict[str, Any] | None:
    if trace is None:
        return None
    return {field: _field(trace, field) for field in PUBLIC_TRACE_FIELDS}


def public_source_payload(
    source: RetrievalResult | Mapping[str, Any],
) -> dict[str, Any]:
    chunk = _field(source, "chunk")
    metadata = _field(chunk, "metadata")
    if not isinstance(metadata, Mapping):
        metadata = {}
    return {
        "chunk": {
            "id": _field(chunk, "id"),
            "document_id": _field(chunk, "document_id"),
            "text": _field(chunk, "text"),
            "metadata": {
                field: metadata[field]
                for field in PUBLIC_SOURCE_METADATA_FIELDS
                if metadata.get(field) not in (None, "")
            },
        },
        "score": _field(source, "score"),
        "retrieval_score": _field(source, "retrieval_score"),
        "rerank_score": _field(source, "rerank_score"),
    }


def public_stream_event_payload(event: str, data: object) -> dict[str, Any]:
    """按事件类型执行 allowlist，防止内部事件字段穿透 SSE 边界。"""

    if event == "complete":
        return public_answer_payload(_mapping(data))
    if event == "retrieval":
        payload = _mapping(data)
        sources = payload.get("sources")
        if not isinstance(sources, (list, tuple)):
            sources = []
        return {
            "request_id": payload.get("request_id"),
            "retrieved_count": payload.get("retrieved_count"),
            "reranked_count": payload.get("reranked_count"),
            "sources": [public_source_payload(source) for source in sources],
        }
    if event == "answer_delta":
        payload = _mapping(data)
        return {
            "request_id": payload.get("request_id"),
            "delta": payload.get("delta"),
        }
    if event == "error":
        return dict(PUBLIC_STREAM_ERROR)
    payload = _mapping(data)
    return {"request_id": payload.get("request_id")}


def _field(value: object, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
