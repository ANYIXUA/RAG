"""RAG 流程的 FastAPI 接口适配。"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status
    from fastapi.exceptions import RequestValidationError
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
    from pydantic import BaseModel, Field
except ModuleNotFoundError as exc:
    raise RuntimeError("Install API support with: pip install -e \".[api]\"") from exc

from rag_app.core.config import Settings
from rag_app.operations.knowledge_lifecycle import (
    create_knowledge_build_job,
    create_knowledge_lifecycle_store,
    get_active_knowledge_context,
    run_knowledge_build_job,
    save_uploaded_text,
)
from rag_app.core.models import UserContext
from rag_app.indexing.offline import OfflineKnowledgeBuilder
from rag_app.operations.ops import (
    build_feedback_record,
    build_request_trace,
    create_feedback_store,
    create_query_log_store,
)
from rag_app.operations.feedback_memory import FeedbackMemoryService
from rag_app.retrieval.answer_memory import (
    AnswerOverrideInput,
    AnswerOverridePatch,
    create_answer_memory_store,
)
from rag_app.rag import RAGPipeline
from rag_app.streaming import format_sse_event
from rag_app.version import APP_VERSION, get_build_info
from rag_app.indexing.vector_store import create_vector_store


class OfflineRefreshRequest(BaseModel):
    source_dir: str | None = Field(default=None)
    reset: bool = Field(default=False)
    force: bool = Field(default=False)


class KnowledgeTextUploadRequest(BaseModel):
    filename: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_type: str | None = Field(default="text/markdown")
    source_type: str | None = Field(default="manual_upload")
    business_module: str | None = Field(default=None)
    title: str | None = Field(default=None)
    tenant_id: str | None = Field(default=None)
    permission_tags: list[str] = Field(default_factory=list)
    auto_build: bool = Field(default=True)
    activate_when_ready: bool = Field(default=True)
    description: str | None = Field(default=None)


class KnowledgeBuildRequest(BaseModel):
    source_dir: str | None = Field(default=None)
    upload_ids: list[str] = Field(default_factory=list)
    activate_when_ready: bool = Field(default=True)
    description: str | None = Field(default=None)


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1)
    session_id: str | None = Field(default=None)
    user_id: str | None = Field(default=None)
    tenant_id: str | None = Field(default=None)
    permission_tags: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=1)
    session_id: str | None = Field(default=None)
    question: str | None = Field(default=None)
    rating: int | None = Field(default=None, ge=1, le=5)
    useful: bool | None = Field(default=None)
    comment: str | None = Field(default=None)
    expected_answer: str | None = Field(default=None)
    labels: list[str] = Field(default_factory=list)


class AnswerOverrideCreateRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    permission_tags: list[str] = Field(default_factory=lambda: ["public"])
    category: str = Field(default="manual")
    ttl_seconds: int | None = Field(default=None, ge=0)
    created_by: str | None = Field(default=None)
    enabled: bool = Field(default=True)
    priority: int = Field(default=100)
    promote_to_long_term: bool = Field(default=False)


class AnswerOverridePatchRequest(BaseModel):
    answer: str | None = Field(default=None)
    permission_tags: list[str] | None = Field(default=None)
    category: str | None = Field(default=None)
    ttl_seconds: int | None = Field(default=None, ge=0)
    enabled: bool | None = Field(default=None)
    priority: int | None = Field(default=None)
    promote_to_long_term: bool | None = Field(default=None)
    updated_by: str | None = Field(default=None)


app = FastAPI(title="Ops RAG", version=APP_VERSION)
_PIPELINE: RAGPipeline | None = None
_PIPELINE_KNOWLEDGE_KEY: str | None = None


def _configure_cors() -> None:
    settings = Settings.from_env()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.api_cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


_configure_cors()


def _get_pipeline() -> RAGPipeline:
    global _PIPELINE, _PIPELINE_KNOWLEDGE_KEY
    settings = Settings.from_env()
    knowledge_context = get_active_knowledge_context(settings)
    pipeline_cache_key = (
        f"{knowledge_context.cache_key}:{knowledge_context.settings.config_fingerprint}"
    )
    # 在线服务缓存 pipeline，避免每个请求重复初始化模型和向量库连接。
    # active knowledge 或配置文件变化时 cache_key 会变化，下一次请求自动切到新版本。
    if (
        _PIPELINE is None
        or _PIPELINE_KNOWLEDGE_KEY != pipeline_cache_key
    ):
        _PIPELINE = RAGPipeline(
            settings=knowledge_context.settings,
            vector_store=create_vector_store(knowledge_context.settings),
            answer_memory=create_answer_memory_store(knowledge_context.settings),
        )
        _PIPELINE_KNOWLEDGE_KEY = pipeline_cache_key
    return _PIPELINE


def _invalidate_pipeline_cache() -> None:
    global _PIPELINE, _PIPELINE_KNOWLEDGE_KEY
    # 管理操作完成后主动失效缓存，保证后续查询不会继续读旧 collection。
    _PIPELINE = None
    _PIPELINE_KNOWLEDGE_KEY = None


def _api_error(
    *,
    code: str,
    message: str,
    status_code: int,
    request_id: str | None = None,
    detail: Any = None,
) -> JSONResponse:
    # 统一错误结构便于网关、前端和灰度监控按 code/request_id 聚合问题。
    payload = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id or uuid4().hex,
            "detail": detail,
        }
    }
    return JSONResponse(status_code=status_code, content=payload)


def _settings_summary(settings: Settings) -> dict[str, Any]:
    return {
        "data_dir": str(settings.data_dir),
        "storage_dir": str(settings.storage_dir),
        "collection": settings.collection_name,
        "embedding_provider": settings.embedding_provider,
        "llm_provider": settings.llm_provider,
        "openai_base_url": settings.openai_base_url,
        "openai_chat_model": settings.openai_chat_model,
        "openai_max_tokens": settings.openai_max_tokens,
        "openai_timeout_seconds": settings.openai_timeout_seconds,
        "openai_max_retries": settings.openai_max_retries,
        "openai_embedding_model": settings.openai_embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "embedding_batch_size": settings.embedding_batch_size,
        "embedding_timeout_seconds": settings.embedding_timeout_seconds,
        "embedding_max_retries": settings.embedding_max_retries,
        "generation_context_max_chars": settings.generation_context_max_chars,
        "top_k": settings.top_k,
        "retrieval_mode": settings.retrieval_mode,
        "retrieval_candidate_k": settings.retrieval_candidate_k,
        "semantic_weight": settings.semantic_weight,
        "bm25_weight": settings.bm25_weight,
        "min_similarity_score": settings.min_similarity_score,
        "relative_score_threshold": settings.relative_score_threshold,
        "rerank_provider": settings.rerank_provider,
        "rerank_candidate_k": settings.rerank_candidate_k,
        "rerank_trigger": settings.rerank_trigger,
        "rerank_min_intent_confidence": settings.rerank_min_intent_confidence,
        "query_embedding_cache_enabled": settings.query_embedding_cache_enabled,
        "query_embedding_cache_size": settings.query_embedding_cache_size,
        "vector_store_provider": settings.vector_store_provider,
        "query_logging_enabled": settings.query_logging_enabled,
        "conversation_memory_provider": settings.conversation_memory_provider,
        "conversation_memory_max_turns": settings.conversation_memory_max_turns,
        "conversation_memory_history_limit": settings.conversation_memory_history_limit,
        "conversation_memory_ttl_seconds": settings.conversation_memory_ttl_seconds,
        "conversation_coreference_enabled": settings.conversation_coreference_enabled,
        "redis_answer_override_enabled": settings.redis_answer_override_enabled,
        "redis_answer_override_ttl_seconds": settings.redis_answer_override_ttl_seconds,
        "redis_answer_override_timeout_ms": settings.redis_answer_override_timeout_ms,
        "feedback_hot_cache_enabled": settings.feedback_hot_cache_enabled,
        "feedback_hot_cache_ttl_seconds": settings.feedback_hot_cache_ttl_seconds,
        "feedback_hot_cache_min_rating": settings.feedback_hot_cache_min_rating,
        "feedback_promotion_enabled": settings.feedback_promotion_enabled,
        "feedback_promotion_auto_build": settings.feedback_promotion_auto_build,
        "feedback_promotion_auto_activate": settings.feedback_promotion_auto_activate,
        "redis_configured": (
            settings.conversation_memory_provider == "redis"
            and settings.redis_url is not None
        ),
        "ops_store_provider": settings.ops_store_provider,
        "knowledge_upload_dir": str(settings.knowledge_upload_dir),
        "knowledge_build_dir": str(settings.knowledge_build_dir),
        "default_tenant_id": settings.default_tenant_id,
        "default_permission_tags": list(settings.default_permission_tags),
        "parse_quality_gate_enabled": settings.parse_quality_gate_enabled,
        "allowed_parse_quality_statuses": list(settings.allowed_parse_quality_statuses),
        "pdf_complex_parser": settings.pdf_complex_parser,
        "pdf_bordered_table_parser": settings.pdf_bordered_table_parser,
        "pdf_borderless_table_parser": settings.pdf_borderless_table_parser,
        "pdf_semistructured_table_parser": settings.pdf_semistructured_table_parser,
        "order_status_tool_enabled": settings.order_status_tool_enabled,
        "order_status_postgres_configured": settings.order_status_postgres_dsn is not None,
        "admin_auth_enabled": settings.api_admin_token is not None,
        "config_sources": list(settings.config_sources),
        "config_fingerprint": settings.config_fingerprint,
    }


def _knowledge_status(settings: Settings) -> dict[str, Any]:
    # ready 检查不只看服务进程是否存活，还确认 active collection 的 pgvector 记录可用。
    knowledge_context = get_active_knowledge_context(settings)
    active_settings = knowledge_context.settings
    vector_store = create_vector_store(active_settings)
    vector_store_exists = True
    reasons: list[str] = []
    error_detail: str | None = None
    try:
        record_count = vector_store.count()
    except Exception as exc:
        record_count = 0
        vector_store_exists = False
        error_detail = str(exc)
        reasons.append("vector_store_error")
    if not vector_store_exists:
        reasons.append("vector_store_missing")
    if vector_store_exists and record_count <= 0:
        reasons.append("vector_store_empty")
    ready = vector_store_exists and record_count > 0
    return {
        "ready": ready,
        "records": record_count,
        "base_collection": settings.collection_name,
        "active_version": (
            asdict(knowledge_context.active_version)
            if knowledge_context.active_version
            else None
        ),
        "active_collection": knowledge_context.collection_name,
        "vector_store_provider": active_settings.vector_store_provider,
        "vector_store_exists": vector_store_exists,
        "vector_store_location": active_settings.vector_store_location,
        "error": error_detail,
        "reasons": reasons,
    }


def _extract_bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return None


def require_admin_token(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> None:
    settings = Settings.from_env()
    expected = settings.api_admin_token
    if expected is None:
        return
    # 灰度期间管理类接口可能接入网关或脚本，兼容 X-API-Key 和 Bearer token 两种传法。
    actual = x_api_key or _extract_bearer_token(authorization)
    if actual != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "管理接口需要有效的 Token",
            },
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    del request
    return _api_error(
        code="VALIDATION_ERROR",
        message="请求参数校验失败",
        status_code=422,
        detail=exc.errors(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    del request
    detail = exc.detail
    code = "HTTP_ERROR"
    message = str(detail)
    extra_detail: Any = detail
    if isinstance(detail, dict):
        code = str(detail.get("code", code))
        message = str(detail.get("message", message))
        extra_detail = detail.get("detail")
    return _api_error(
        code=code,
        message=message,
        status_code=exc.status_code,
        detail=extra_detail,
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    del request
    return _api_error(
        code="CONFIG_ERROR",
        message=str(exc),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    del request
    return _api_error(
        code="INTERNAL_ERROR",
        message="服务内部异常",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    )


@app.get("/health")
def health() -> dict:
    settings = Settings.from_env()
    knowledge = _knowledge_status(settings)
    return {
        "status": "ok",
        "service": "rag-api",
        "build": get_build_info(),
        "config": _settings_summary(settings),
        "knowledge": knowledge,
        "records": knowledge["records"],
        "collection": knowledge["active_collection"],
        "query_logging_enabled": settings.query_logging_enabled,
    }


@app.get("/ready")
def ready() -> Any:
    settings = Settings.from_env()
    knowledge = _knowledge_status(settings)
    payload = {
        "status": "ready" if knowledge["ready"] else "not_ready",
        "knowledge": knowledge,
    }
    if not knowledge["ready"]:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload,
        )
    return payload


@app.post("/offline-refresh", dependencies=[Depends(require_admin_token)])
def offline_refresh(request: OfflineRefreshRequest) -> dict:
    builder = OfflineKnowledgeBuilder.from_env()
    source_dir = Path(request.source_dir) if request.source_dir else None
    report = builder.refresh(
        source_dir=source_dir,
        reset=request.reset,
        force=request.force,
    )
    # 离线刷新可能改变 base collection，刷新完成后让在线 pipeline 重新读取向量库。
    _invalidate_pipeline_cache()
    return asdict(report)


@app.post("/knowledge/uploads/text", dependencies=[Depends(require_admin_token)])
def upload_knowledge_text(
    request: KnowledgeTextUploadRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    settings = Settings.from_env()
    metadata = {
        "source_type": request.source_type or "manual_upload",
        "business_module": request.business_module,
        "title": request.title,
        "tenant_id": request.tenant_id,
        "permission_tags": ",".join(request.permission_tags) if request.permission_tags else None,
    }
    upload = save_uploaded_text(
        settings,
        filename=request.filename,
        content=request.content,
        content_type=request.content_type,
        metadata=metadata,
    )
    job = None
    if request.auto_build:
        job = create_knowledge_build_job(
            settings,
            upload_ids=[upload.upload_id],
            activate_when_ready=request.activate_when_ready,
            description=request.description or f"上传文件触发构建：{upload.filename}",
        )
        # 构建任务放到 FastAPI background task 中执行，接口快速返回 job_id 供调用方查询进度。
        background_tasks.add_task(_run_build_job_background, settings, job.job_id)
    return {
        "upload": asdict(upload),
        "job": asdict(job) if job else None,
    }


@app.post("/knowledge/build-jobs", dependencies=[Depends(require_admin_token)])
def create_knowledge_job(
    request: KnowledgeBuildRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    settings = Settings.from_env()
    source_dir = Path(request.source_dir) if request.source_dir else None
    job = create_knowledge_build_job(
        settings,
        source_dir=source_dir,
        upload_ids=request.upload_ids,
        activate_when_ready=request.activate_when_ready,
        description=request.description,
    )
    background_tasks.add_task(_run_build_job_background, settings, job.job_id)
    return {"job": asdict(job)}


@app.get("/knowledge/uploads", dependencies=[Depends(require_admin_token)])
def knowledge_uploads(limit: int = 50) -> dict:
    settings = Settings.from_env()
    store = create_knowledge_lifecycle_store(settings)
    return {"items": [asdict(item) for item in store.list_uploads(limit=limit)]}


@app.get("/knowledge/build-jobs", dependencies=[Depends(require_admin_token)])
def knowledge_jobs(limit: int = 50) -> dict:
    settings = Settings.from_env()
    store = create_knowledge_lifecycle_store(settings)
    return {"items": [asdict(item) for item in store.list_jobs(limit=limit)]}


@app.get("/knowledge/build-jobs/{job_id}", dependencies=[Depends(require_admin_token)])
def knowledge_job(job_id: str) -> dict:
    settings = Settings.from_env()
    store = create_knowledge_lifecycle_store(settings)
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "知识构建任务不存在"},
        )
    return asdict(job)


@app.get("/knowledge/versions", dependencies=[Depends(require_admin_token)])
def knowledge_versions(limit: int = 50) -> dict:
    settings = Settings.from_env()
    store = create_knowledge_lifecycle_store(settings)
    active = store.get_active_version(settings.collection_name)
    return {
        "active": asdict(active) if active else None,
        "items": [asdict(item) for item in store.list_versions(limit=limit)],
    }


@app.get("/knowledge/active", dependencies=[Depends(require_admin_token)])
def knowledge_active() -> dict:
    settings = Settings.from_env()
    context = get_active_knowledge_context(settings)
    return {
        "base_collection": settings.collection_name,
        "active_collection": context.collection_name,
        "active_version": (
            asdict(context.active_version) if context.active_version else None
        ),
    }


@app.post(
    "/knowledge/versions/{version}/activate",
    dependencies=[Depends(require_admin_token)],
)
def activate_knowledge_version(version: str) -> dict:
    settings = Settings.from_env()
    store = create_knowledge_lifecycle_store(settings)
    active = store.activate_version(settings.collection_name, version)
    # 手动激活版本后立刻清缓存，确保下一次 /query 读取新的 active collection。
    _invalidate_pipeline_cache()
    return asdict(active)


@app.post("/knowledge/rollback", dependencies=[Depends(require_admin_token)])
def rollback_knowledge_version() -> dict:
    settings = Settings.from_env()
    store = create_knowledge_lifecycle_store(settings)
    active = store.get_active_version(settings.collection_name)
    if active is None or not active.previous_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ROLLBACK_UNAVAILABLE", "message": "没有可回滚的知识版本"},
        )
    rolled_back = store.activate_version(
        settings.collection_name,
        active.previous_version,
    )
    _invalidate_pipeline_cache()
    return asdict(rolled_back)


def _run_build_job_background(settings: Settings, job_id: str) -> None:
    run_knowledge_build_job(settings, job_id)
    # 构建任务如果激活了新版本，后台结束后需要让在线服务感知版本变化。
    _invalidate_pipeline_cache()


@app.post("/memory/overrides", dependencies=[Depends(require_admin_token)])
def create_memory_override(request: AnswerOverrideCreateRequest) -> dict:
    settings = Settings.from_env()
    store = create_answer_memory_store(settings)
    record = store.upsert_override(
        AnswerOverrideInput(
            question=request.question,
            answer=request.answer,
            tenant_id=request.tenant_id,
            permission_tags=tuple(request.permission_tags or ["public"]),
            category=request.category,
            ttl_seconds=(
                request.ttl_seconds
                if request.ttl_seconds is not None
                else settings.redis_answer_override_ttl_seconds
            ),
            created_by=request.created_by,
            enabled=request.enabled,
            priority=request.priority,
            promote_to_long_term=request.promote_to_long_term,
        )
    )
    return asdict(record)


@app.get("/memory/overrides", dependencies=[Depends(require_admin_token)])
def list_memory_overrides(
    tenant_id: str | None = None,
    enabled: bool | None = None,
) -> dict:
    settings = Settings.from_env()
    store = create_answer_memory_store(settings)
    return {
        "items": [
            asdict(item)
            for item in store.list_overrides(tenant_id=tenant_id, enabled=enabled)
        ]
    }


@app.patch("/memory/overrides/{override_id}", dependencies=[Depends(require_admin_token)])
def patch_memory_override(
    override_id: str,
    request: AnswerOverridePatchRequest,
) -> dict:
    settings = Settings.from_env()
    store = create_answer_memory_store(settings)
    record = store.patch_override(
        override_id,
        AnswerOverridePatch(
            answer=request.answer,
            permission_tags=(
                tuple(request.permission_tags)
                if request.permission_tags is not None
                else None
            ),
            category=request.category,
            ttl_seconds=request.ttl_seconds,
            enabled=request.enabled,
            priority=request.priority,
            promote_to_long_term=request.promote_to_long_term,
            updated_by=request.updated_by,
        ),
    )
    return asdict(record)


@app.delete("/memory/overrides/{override_id}", dependencies=[Depends(require_admin_token)])
def delete_memory_override(override_id: str) -> dict:
    settings = Settings.from_env()
    store = create_answer_memory_store(settings)
    return {"override_id": override_id, "deleted": store.delete_override(override_id)}


@app.post("/query")
def query(request: QueryRequest) -> dict:
    pipeline = _get_pipeline()
    answer = pipeline.query(
        request.question,
        top_k=request.top_k,
        session_id=request.session_id,
        user_context=UserContext(
            user_id=request.user_id,
            tenant_id=request.tenant_id,
            permission_tags=tuple(request.permission_tags),
        ),
    )
    payload = asdict(answer)
    # request_id 提升到响应顶层，方便前端直接提交反馈或查询 trace。
    payload["request_id"] = answer.trace.request_id if answer.trace else None
    return payload


@app.post("/query/stream")
def query_stream(request: QueryRequest) -> StreamingResponse:
    def event_source():
        pipeline = _get_pipeline()
        user_context = UserContext(
            user_id=request.user_id,
            tenant_id=request.tenant_id,
            permission_tags=tuple(request.permission_tags),
        )
        for item in pipeline.stream_query(
            request.question,
            top_k=request.top_k,
            session_id=request.session_id,
            user_context=user_context,
        ):
            yield format_sse_event(item["event"], item["data"])

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/feedback")
def feedback(request: FeedbackRequest) -> dict:
    settings = Settings.from_env()
    store = create_feedback_store(settings)
    query_store = create_query_log_store(settings)
    record = build_feedback_record(
        request_id=request.request_id,
        session_id=request.session_id,
        question=request.question,
        rating=request.rating,
        useful=request.useful,
        comment=request.comment,
        expected_answer=request.expected_answer,
        labels=request.labels,
    )
    store.append(record)
    payload = asdict(record)
    try:
        memory = FeedbackMemoryService(
            settings=settings,
            answer_memory=create_answer_memory_store(settings),
            query_log_store=query_store,
        ).handle_feedback(record)
        payload["memory"] = asdict(memory)
    except Exception as exc:
        payload["memory"] = {
            "hot_cache_status": "failed",
            "promotion_status": "failed",
            "error": str(exc),
        }
    return payload


@app.get("/ops/query-logs", dependencies=[Depends(require_admin_token)])
def query_logs(limit: int = 20) -> dict:
    settings = Settings.from_env()
    store = create_query_log_store(settings)
    return {"items": store.tail(limit=limit)}


@app.get("/ops/feedback", dependencies=[Depends(require_admin_token)])
def feedback_logs(limit: int = 20) -> dict:
    settings = Settings.from_env()
    store = create_feedback_store(settings)
    return {"items": store.tail(limit=limit)}


@app.get("/ops/summary", dependencies=[Depends(require_admin_token)])
def ops_summary(limit: int = 200) -> dict:
    settings = Settings.from_env()
    query_store = create_query_log_store(settings)
    feedback_store = create_feedback_store(settings)
    return {
        "query_logs": query_store.summary(limit=limit),
        "feedback": feedback_store.summary(limit=limit),
    }


@app.get("/ops/trace/{request_id}", dependencies=[Depends(require_admin_token)])
def ops_trace(request_id: str) -> dict:
    settings = Settings.from_env()
    return build_request_trace(settings, request_id)
