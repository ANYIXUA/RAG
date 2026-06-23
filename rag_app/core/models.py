"""RAG 流程使用的通用数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Metadata = dict[str, Any]


@dataclass(frozen=True)
class ParsedBlock:
    """解析阶段产出的结构化知识块。

    这层是商业 RAG 的中间格式：先把原始文档还原成带结构、来源和质量信息的 block，
    再交给切片器生成 chunk，避免 PDF、表格、章节和权限信息在入库前被打散。
    """

    block_id: str
    document_id: str
    version_id: str
    block_type: str
    text: str
    raw_text: str | None = None
    clean_text: str | None = None
    page_number: int | None = None
    bbox: list[float] | None = None
    section_path: list[str] = field(default_factory=list)
    parent_block_id: str | None = None
    previous_block_id: str | None = None
    next_block_id: str | None = None
    metadata: Metadata = field(default_factory=dict)
    quality_status: str = "parsed_success"


@dataclass(frozen=True)
class ParseQualityReport:
    """文档解析质量门禁报告。"""

    status: str
    warning_codes: list[str] = field(default_factory=list)
    ocr_required: bool = False
    metrics: Metadata = field(default_factory=dict)


@dataclass(frozen=True)
class UserContext:
    """在线检索时使用的用户身份和权限上下文。"""

    user_id: str | None = None
    tenant_id: str | None = None
    permission_tags: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class Document:
    """切片前的原始文档。"""

    id: str
    text: str
    metadata: Metadata = field(default_factory=dict)
    parsed_blocks: list[ParsedBlock] = field(default_factory=list)


@dataclass(frozen=True)
class Chunk:
    """可被检索召回的文档切片。"""

    id: str
    document_id: str
    text: str
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    """带召回分数的检索结果。"""

    chunk: Chunk
    score: float
    semantic_score: float | None = None
    bm25_score: float | None = None
    normalized_bm25_score: float | None = None
    keyword_score: float | None = None
    retrieval_score: float | None = None
    rerank_score: float | None = None


@dataclass(frozen=True)
class IntentRecognitionResult:
    """用户查询意图识别结果。"""

    intent_label: str
    confidence: float
    matched_keywords: list[str]
    reason: str


@dataclass(frozen=True)
class QueryRewriteResult:
    """用户查询改写和扩展结果。"""

    original_query: str
    normalized_query: str
    rewritten_query: str
    retrieval_query: str
    synonym_expansions: list[str]
    semantic_expansions: list[str]
    applied_rules: list[str]


@dataclass(frozen=True)
class ToolCallTrace:
    """一次在线工具调用的可观测记录。"""

    tool_name: str
    input: Metadata
    output: Metadata
    status: str
    latency_ms: float
    error: str | None = None


@dataclass(frozen=True)
class OnlineProcessingTrace:
    """在线问答链路的处理轨迹。"""

    request_id: str
    created_at: str
    session_id: str | None
    is_follow_up: bool
    original_query: str
    normalized_query: str
    contextual_query: str
    context_terms: list[str]
    rewritten_query: str
    retrieval_query: str
    synonym_expansions: list[str]
    semantic_expansions: list[str]
    query_rewrite_rules: list[str]
    intent_label: str
    intent_confidence: float
    intent_reason: str
    top_k: int
    min_similarity_score: float
    relative_score_threshold: float
    retrieval_mode: str
    semantic_weight: float
    bm25_weight: float
    keyword_weight: float
    retrieval_candidate_k: int
    rerank_provider: str
    rerank_model: str
    rerank_candidate_k: int
    reranked_count: int
    query_embedding_dimensions: int
    retrieved_count: int
    latency_ms: float
    retrieval_latency_ms: float
    generation_latency_ms: float
    augmented_context: str
    context_latency_ms: float = 0.0
    intent_latency_ms: float = 0.0
    rewrite_latency_ms: float = 0.0
    embedding_latency_ms: float = 0.0
    vector_search_latency_ms: float = 0.0
    rerank_latency_ms: float = 0.0
    rerank_applied: bool = False
    rerank_skip_reason: str | None = None
    degradation_reason: str | None = None
    query_embedding_cache_hit: bool = False
    user_id: str | None = None
    tenant_id: str | None = None
    permission_tags: tuple[str, ...] = ()
    authorized_source_count: int = 0
    tool_calls: list[ToolCallTrace] = field(default_factory=list)
    conversation_history_turn_count: int = 0


@dataclass(frozen=True)
class RAGAnswer:
    """生成答案，以及生成答案时使用的召回证据。"""

    question: str
    answer: str
    sources: list[RetrievalResult]
    trace: OnlineProcessingTrace | None = None


@dataclass(frozen=True)
class OfflineRefreshReport:
    """离线知识库刷新后的统计结果。"""

    source_dir: str
    manifest_path: str
    vector_store_path: str
    documents_seen: int
    documents_changed: int
    documents_skipped: int
    documents_removed: int
    chunks_embedded: int
    stored_records: int
    files_seen: int = 0
    documents_skipped_by_policy: int = 0
    documents_failed: int = 0
    skipped_files: list[dict[str, str]] = field(default_factory=list)
    failed_files: list[dict[str, str]] = field(default_factory=list)
    refresh_report_path: str | None = None
    manifest_backup_path: str | None = None
