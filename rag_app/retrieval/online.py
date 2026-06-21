"""在线问答处理流程。"""

from __future__ import annotations

from collections.abc import Iterator
from collections import OrderedDict
from dataclasses import asdict, replace
from queue import Queue
from threading import Thread
import time
from pathlib import Path
from typing import Any

from rag_app.core.error_codes import extract_error_code
from rag_app.core.config import Settings
from rag_app.retrieval.dialogue import (
    ConversationMemory,
    ConversationTurn,
    rewrite_query_with_context,
    summarize_answer,
)
from rag_app.indexing.embeddings import Embedder, create_embedder
from rag_app.retrieval.llm import AnswerGenerator, create_answer_generator
from rag_app.core.models import OnlineProcessingTrace, RAGAnswer, RetrievalResult, UserContext
from rag_app.operations.ops import (
    QueryLogStore,
    build_query_log_record,
    create_query_log_store,
    new_request_id,
    utc_now,
)
from rag_app.retrieval.query import recognize_intent, rewrite_query
from rag_app.retrieval.rerank import Reranker, create_reranker
from rag_app.indexing.vector_store import VectorStore, create_vector_store
from rag_app.tools.order_status import (
    OrderStatusTool,
    create_order_status_tool,
    extract_work_order_no,
)


class OnlineQueryProcessor:
    """在线阶段只负责查询向量化、混合检索和增强上下文生成。"""

    def __init__(
        self,
        settings: Settings,
        embedder: Embedder | None = None,
        answer_generator: AnswerGenerator | None = None,
        vector_store: VectorStore | None = None,
        reranker: Reranker | None = None,
        order_status_tool: OrderStatusTool | None = None,
        conversation_memory: ConversationMemory | None = None,
        query_log_store: QueryLogStore | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or create_embedder(settings)
        self.answer_generator = answer_generator or create_answer_generator(settings)
        self.vector_store = vector_store or create_vector_store(settings)
        self.reranker = reranker or create_reranker(settings)
        self.order_status_tool = order_status_tool or create_order_status_tool(settings)
        self.conversation_memory = conversation_memory or ConversationMemory()
        self.query_log_store = query_log_store or create_query_log_store(settings)
        self._query_embedding_cache: OrderedDict[str, list[float]] = OrderedDict()

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "OnlineQueryProcessor":
        return cls(Settings.from_env(base_dir=base_dir))

    def process(
        self,
        question: str,
        top_k: int | None = None,
        session_id: str | None = None,
        user_context: UserContext | None = None,
    ) -> RAGAnswer:
        # 1. 每次请求先生成 request_id。灰度期间所有日志、反馈、trace 都靠它串联。
        request_id = new_request_id()
        created_at = utc_now()
        total_start = time.perf_counter()
        original_query = question.strip()
        if not original_query:
            raise ValueError("question must not be empty")
        user_context = user_context or UserContext()

        # 2. 会话上下文改写：处理“这个怎么弄”“那下一步呢”这类追问。
        context_start = time.perf_counter()
        normalized_query = _normalize_query(original_query) #清洗，去掉多余空格之类的，大小写归一化
        history = self.conversation_memory.get_recent_turns(session_id=session_id, limit=5) #获取session中最近的5轮对话
        contextual_query, is_follow_up, context_terms = rewrite_query_with_context(
            normalized_query,
            history,
        )#改写追问，contextual_query：改写后的完整问题；is_follow_up：表示当前问题是不是追问；context_terms：从历史上下文中提取的关键词
        context_latency_ms = (time.perf_counter() - context_start) * 1000

        # 3. 意图识别和 Query 改写会影响召回词、语义扩展和重排触发策略。
        intent_start = time.perf_counter()
        intent = recognize_intent(contextual_query)
        intent_latency_ms = (time.perf_counter() - intent_start) * 1000

        rewrite_start = time.perf_counter()
        rewrite = rewrite_query(contextual_query, intent=intent)
        rewrite_latency_ms = (time.perf_counter() - rewrite_start) * 1000
        tool_calls = self._maybe_call_order_status_tool(
            request_id=request_id,
            original_query=original_query,
            contextual_query=contextual_query,
            retrieval_query=rewrite.retrieval_query,
            intent_label=intent.intent_label,
        )

        actual_top_k = self.settings.top_k if top_k is None else top_k
        exact_error_code = (
            extract_error_code(rewrite.retrieval_query)
            if intent.intent_label == "explain_error"
            else None
        )
        if exact_error_code:
            return self._process_exact_error_code(
                request_id=request_id,
                created_at=created_at,
                total_start=total_start,
                original_query=original_query,
                normalized_query=normalized_query,
                contextual_query=contextual_query,
                is_follow_up=is_follow_up,
                context_terms=context_terms,
                rewrite=rewrite,
                intent=intent,
                top_k=actual_top_k,
                session_id=session_id,
                user_context=user_context,
                tool_calls=tool_calls,
                error_code=exact_error_code,
                context_latency_ms=context_latency_ms,
                intent_latency_ms=intent_latency_ms,
                rewrite_latency_ms=rewrite_latency_ms,
            )
        #本次是否跳过重排序
        rerank_skip_reason = _precheck_rerank_skip_reason(
            settings=self.settings,
            reranker=self.reranker,
            intent_label=intent.intent_label,
            intent_confidence=intent.confidence,
            is_follow_up=is_follow_up,
        )

        search_top_k = actual_top_k
        if rerank_skip_reason is None: #如果要走重排序，就需要扩大检索范围
            search_top_k = max(actual_top_k, self.settings.rerank_candidate_k)
        search_candidate_k = max(search_top_k, self.settings.retrieval_candidate_k)
        degradation_reason: str | None = None #记录降级原因。

        # 4. 在线阶段只对查询向量化，不做文档解析和知识库构建。
        retrieval_start = time.perf_counter()
        embedding_start = time.perf_counter()
        #如果同一个 query 之前已经算过 embedding，就可以直接从缓存拿。
        actual_retrieval_mode = self.settings.retrieval_mode
        try:
            query_embedding, cache_hit = self._embed_query(rewrite.retrieval_query)
        except Exception as exc:
            query_embedding = []
            cache_hit = False
            actual_retrieval_mode = "bm25"
            degradation_reason = _append_degradation(
                degradation_reason,
                f"embedding_failed: {exc}",
            )
        embedding_latency_ms = (time.perf_counter() - embedding_start) * 1000

        # 5. 每次检索前 reload，确保能读到离线刷新或 active 版本切换后的最新知识。
        vector_search_start = time.perf_counter()
        self.vector_store.reload() #重新加载向量库，确保当前查询使用的是最新的向量库数据。
        #从向量数据库获取相关的知识片段
        retrieved_sources = self.vector_store.search(
            query_embedding=query_embedding,#语义检索
            query_text=rewrite.retrieval_query,#关键词检索
            top_k=search_top_k,
            min_score=self.settings.min_similarity_score,
            relative_score_threshold=self.settings.relative_score_threshold,#相对分数过滤
            mode=actual_retrieval_mode,#决定检索模式
            semantic_weight=self.settings.semantic_weight,
            keyword_weight=self.settings.bm25_weight,
            bm25_weight=self.settings.bm25_weight,
            candidate_k=search_candidate_k,#候选池大小
            #权限控制
            tenant_id=user_context.tenant_id,
            permission_tags=user_context.permission_tags,
        )
        vector_search_latency_ms = (time.perf_counter() - vector_search_start) * 1000

        rerank_latency_ms = 0.0
        rerank_applied = False
        #候选数量不足跳过rerank
        if rerank_skip_reason is None and len(retrieved_sources) <= actual_top_k:
            rerank_skip_reason = "not_enough_candidates"

        # 6. 重排失败不让请求失败，而是降级使用粗召回结果，并把原因写入 trace。
        if rerank_skip_reason is None:
            rerank_start = time.perf_counter()
            try:
                sources = self.reranker.rerank(
                    query=rewrite.retrieval_query,
                    results=retrieved_sources,
                    top_k=actual_top_k,
                )
                rerank_applied = True #重排成功后标记
            except Exception as exc:#失败后降级
                sources = _top_without_rerank(retrieved_sources, actual_top_k)
                rerank_skip_reason = "rerank_failed"
                degradation_reason = f"rerank_failed: {exc}"
            rerank_latency_ms = (time.perf_counter() - rerank_start) * 1000
        else:
            sources = _top_without_rerank(retrieved_sources, actual_top_k)
        retrieval_latency_ms = (time.perf_counter() - retrieval_start) * 1000
        # 7. 增强上下文把查询理解和召回证据一起交给生成器，降低幻觉并保留可追溯信息。
        augmented_context = build_augmented_context(
            request_id=request_id,
            session_id=session_id,
            original_query=original_query,
            normalized_query=normalized_query,
            contextual_query=contextual_query,
            is_follow_up=is_follow_up,
            context_terms=context_terms,
            rewritten_query=rewrite.rewritten_query,
            retrieval_query=rewrite.retrieval_query,
            synonym_expansions=rewrite.synonym_expansions,
            semantic_expansions=rewrite.semantic_expansions,
            intent_label=intent.intent_label,
            sources=sources,
            user_context=user_context,
            tool_calls=tool_calls,
        )
        generation_start = time.perf_counter()
        try:
            answer = self.answer_generator.answer(
                question=original_query,
                sources=sources,
                augmented_context=augmented_context,
            )
        except Exception as exc:
            answer = _fallback_answer_for_generation_error(sources)
            degradation_reason = _append_degradation(
                degradation_reason,
                f"generation_failed: {exc}",
            )
        generation_latency_ms = (time.perf_counter() - generation_start) * 1000
        # 8. 将本轮摘要写入内存会话，供下一轮追问改写使用。
        retrieved_titles = [
            str(
                result.chunk.metadata.get("section_title")
                or result.chunk.metadata.get("title")
                or result.chunk.metadata.get("filename")
                or result.chunk.metadata.get("source", "unknown")
            )
            for result in sources[:3]
        ]
        self.conversation_memory.append_turn(
            session_id=session_id,
            turn=ConversationTurn(
                question=original_query,
                rewritten_query=rewrite.rewritten_query,
                intent_label=intent.intent_label,
                retrieved_titles=retrieved_titles,
                answer_summary=summarize_answer(answer),
            ),
        )
        latency_ms = (time.perf_counter() - total_start) * 1000
        # 9. trace 是灰度排查的核心资产：它记录每个阶段的输入、输出、耗时和降级原因。
        trace = OnlineProcessingTrace(
            request_id=request_id,
            created_at=created_at,
            session_id=session_id,
            is_follow_up=is_follow_up,
            original_query=original_query,
            normalized_query=normalized_query,
            contextual_query=contextual_query,
            context_terms=context_terms,
            rewritten_query=rewrite.rewritten_query,
            retrieval_query=rewrite.retrieval_query,
            synonym_expansions=rewrite.synonym_expansions,
            semantic_expansions=rewrite.semantic_expansions,
            query_rewrite_rules=rewrite.applied_rules,
            intent_label=intent.intent_label,
            intent_confidence=intent.confidence,
            intent_reason=intent.reason,
            top_k=actual_top_k,
            min_similarity_score=self.settings.min_similarity_score,
            relative_score_threshold=self.settings.relative_score_threshold,
            retrieval_mode=actual_retrieval_mode,
            semantic_weight=self.settings.semantic_weight,
            bm25_weight=self.settings.bm25_weight,
            keyword_weight=self.settings.keyword_weight,
            retrieval_candidate_k=self.settings.retrieval_candidate_k,
            rerank_provider=getattr(self.reranker, "provider_name", "none"),
            rerank_model=getattr(self.reranker, "model_name", "none"),
            rerank_candidate_k=self.settings.rerank_candidate_k,
            reranked_count=len(sources),
            query_embedding_dimensions=len(query_embedding),
            retrieved_count=len(retrieved_sources),
            latency_ms=round(latency_ms, 3),
            retrieval_latency_ms=round(retrieval_latency_ms, 3),
            generation_latency_ms=round(generation_latency_ms, 3),
            augmented_context=augmented_context,
            context_latency_ms=round(context_latency_ms, 3),
            intent_latency_ms=round(intent_latency_ms, 3),
            rewrite_latency_ms=round(rewrite_latency_ms, 3),
            embedding_latency_ms=round(embedding_latency_ms, 3),
            vector_search_latency_ms=round(vector_search_latency_ms, 3),
            rerank_latency_ms=round(rerank_latency_ms, 3),
            rerank_applied=rerank_applied,
            rerank_skip_reason=rerank_skip_reason,
            degradation_reason=degradation_reason,
            query_embedding_cache_hit=cache_hit,
            user_id=user_context.user_id,
            tenant_id=user_context.tenant_id,
            permission_tags=user_context.permission_tags,
            authorized_source_count=len(sources),
            tool_calls=tool_calls,
        )
        rag_answer = RAGAnswer(
            question=original_query,
            answer=answer,
            sources=sources,
            trace=trace,
        )
        if self.settings.query_logging_enabled:
            # 10. 结构化日志落库后，/ops/trace/{request_id} 和人工反馈可以按 request_id 串联。
            self.query_log_store.append(
                build_query_log_record(
                    request_id=request_id,
                    answer=rag_answer,
                    latency_ms=latency_ms,
                    retrieval_latency_ms=retrieval_latency_ms,
                    generation_latency_ms=generation_latency_ms,
                )
            )
        return rag_answer

    def stream_process(
        self,
        question: str,
        top_k: int | None = None,
        session_id: str | None = None,
        user_context: UserContext | None = None,
    ) -> Iterator[dict[str, Any]]:
        """复用同步处理链路，并把生成阶段转成事件流。"""

        events: Queue[dict[str, Any] | object] = Queue()
        proxy = _StreamingAnswerProxy(self.answer_generator, events)
        worker = OnlineQueryProcessor(
            settings=self.settings,
            embedder=self.embedder,
            answer_generator=proxy,
            vector_store=self.vector_store,
            reranker=self.reranker,
            order_status_tool=self.order_status_tool,
            conversation_memory=self.conversation_memory,
            query_log_store=self.query_log_store,
        )
        worker._query_embedding_cache = self._query_embedding_cache

        def run_query() -> None:
            try:
                answer = worker.process(
                    question,
                    top_k=top_k,
                    session_id=session_id,
                    user_context=user_context,
                )
                payload = asdict(answer)
                payload["request_id"] = answer.trace.request_id if answer.trace else None
                events.put({"event": "complete", "data": payload})
            except Exception as exc:
                events.put(
                    {
                        "event": "error",
                        "data": {
                            "code": "STREAM_QUERY_ERROR",
                            "message": str(exc),
                        },
                    }
                )
            finally:
                events.put(_STREAM_DONE)

        thread = Thread(target=run_query, daemon=True)
        thread.start()
        while True:
            item = events.get()
            if item is _STREAM_DONE:
                break
            yield item
        thread.join()

    def _process_exact_error_code(
        self,
        *,
        request_id: str,
        created_at: str,
        total_start: float,
        original_query: str,
        normalized_query: str,
        contextual_query: str,
        is_follow_up: bool,
        context_terms: list[str],
        rewrite,
        intent,
        top_k: int,
        session_id: str | None,
        user_context: UserContext,
        tool_calls: list,
        error_code: str,
        context_latency_ms: float,
        intent_latency_ms: float,
        rewrite_latency_ms: float,
    ) -> RAGAnswer:
        """异常码意图走结构化精确匹配，避免语义召回误命中相近错误码。"""

        retrieval_start = time.perf_counter()
        vector_search_start = time.perf_counter()
        self.vector_store.reload()
        sources = self.vector_store.search_by_error_code(
            error_code=error_code,
            top_k=top_k,
            tenant_id=user_context.tenant_id,
            permission_tags=user_context.permission_tags,
        )
        vector_search_latency_ms = (time.perf_counter() - vector_search_start) * 1000
        retrieval_latency_ms = (time.perf_counter() - retrieval_start) * 1000

        augmented_context = build_augmented_context(
            request_id=request_id,
            session_id=session_id,
            original_query=original_query,
            normalized_query=normalized_query,
            contextual_query=contextual_query,
            is_follow_up=is_follow_up,
            context_terms=context_terms,
            rewritten_query=rewrite.rewritten_query,
            retrieval_query=rewrite.retrieval_query,
            synonym_expansions=rewrite.synonym_expansions,
            semantic_expansions=rewrite.semantic_expansions,
            intent_label=intent.intent_label,
            sources=sources,
            user_context=user_context,
            tool_calls=tool_calls,
        )
        generation_start = time.perf_counter()
        degradation_reason: str | None = None
        try:
            answer = self.answer_generator.answer(
                question=original_query,
                sources=sources,
                augmented_context=augmented_context,
            )
        except Exception as exc:
            answer = _fallback_answer_for_generation_error(sources)
            degradation_reason = f"generation_failed: {exc}"
        generation_latency_ms = (time.perf_counter() - generation_start) * 1000

        retrieved_titles = [
            str(
                result.chunk.metadata.get("section_title")
                or result.chunk.metadata.get("title")
                or result.chunk.metadata.get("filename")
                or result.chunk.metadata.get("source", "unknown")
            )
            for result in sources[:3]
        ]
        self.conversation_memory.append_turn(
            session_id=session_id,
            turn=ConversationTurn(
                question=original_query,
                rewritten_query=rewrite.rewritten_query,
                intent_label=intent.intent_label,
                retrieved_titles=retrieved_titles,
                answer_summary=summarize_answer(answer),
            ),
        )
        latency_ms = (time.perf_counter() - total_start) * 1000
        trace = OnlineProcessingTrace(
            request_id=request_id,
            created_at=created_at,
            session_id=session_id,
            is_follow_up=is_follow_up,
            original_query=original_query,
            normalized_query=normalized_query,
            contextual_query=contextual_query,
            context_terms=context_terms,
            rewritten_query=rewrite.rewritten_query,
            retrieval_query=rewrite.retrieval_query,
            synonym_expansions=rewrite.synonym_expansions,
            semantic_expansions=rewrite.semantic_expansions,
            query_rewrite_rules=rewrite.applied_rules,
            intent_label=intent.intent_label,
            intent_confidence=intent.confidence,
            intent_reason=intent.reason,
            top_k=top_k,
            min_similarity_score=self.settings.min_similarity_score,
            relative_score_threshold=self.settings.relative_score_threshold,
            retrieval_mode="exact_error_code",
            semantic_weight=self.settings.semantic_weight,
            bm25_weight=self.settings.bm25_weight,
            keyword_weight=self.settings.keyword_weight,
            retrieval_candidate_k=self.settings.retrieval_candidate_k,
            rerank_provider=getattr(self.reranker, "provider_name", "none"),
            rerank_model=getattr(self.reranker, "model_name", "none"),
            rerank_candidate_k=self.settings.rerank_candidate_k,
            reranked_count=len(sources),
            query_embedding_dimensions=0,
            retrieved_count=len(sources),
            latency_ms=round(latency_ms, 3),
            retrieval_latency_ms=round(retrieval_latency_ms, 3),
            generation_latency_ms=round(generation_latency_ms, 3),
            augmented_context=augmented_context,
            context_latency_ms=round(context_latency_ms, 3),
            intent_latency_ms=round(intent_latency_ms, 3),
            rewrite_latency_ms=round(rewrite_latency_ms, 3),
            embedding_latency_ms=0.0,
            vector_search_latency_ms=round(vector_search_latency_ms, 3),
            rerank_latency_ms=0.0,
            rerank_applied=False,
            rerank_skip_reason="exact_error_code",
            degradation_reason=degradation_reason,
            query_embedding_cache_hit=False,
            user_id=user_context.user_id,
            tenant_id=user_context.tenant_id,
            permission_tags=user_context.permission_tags,
            authorized_source_count=len(sources),
            tool_calls=tool_calls,
        )
        rag_answer = RAGAnswer(
            question=original_query,
            answer=answer,
            sources=sources,
            trace=trace,
        )
        if self.settings.query_logging_enabled:
            self.query_log_store.append(
                build_query_log_record(
                    request_id=request_id,
                    answer=rag_answer,
                    latency_ms=latency_ms,
                    retrieval_latency_ms=retrieval_latency_ms,
                    generation_latency_ms=generation_latency_ms,
                )
            )
        return rag_answer

    def _embed_query(self, retrieval_query: str) -> tuple[list[float], bool]:
        """对查询向量做轻量缓存，减少重复问法的在线开销。"""

        if not self.settings.query_embedding_cache_enabled:
            return self.embedder.embed([retrieval_query])[0], False

        cached = self._query_embedding_cache.get(retrieval_query)
        if cached is not None:
            self._query_embedding_cache.move_to_end(retrieval_query)
            return list(cached), True

        embedding = self.embedder.embed([retrieval_query])[0]
        self._query_embedding_cache[retrieval_query] = list(embedding)
        while len(self._query_embedding_cache) > self.settings.query_embedding_cache_size:
            self._query_embedding_cache.popitem(last=False)
        return embedding, False

    def _maybe_call_order_status_tool(
        self,
        request_id: str,
        original_query: str,
        contextual_query: str,
        retrieval_query: str,
        intent_label: str,
    ):
        """工单状态意图命中时调用查询工具，并把调用结果写入 trace。"""

        if intent_label != "query_order_status":
            return []
        work_order_no = (
            extract_work_order_no(original_query)
            or extract_work_order_no(contextual_query)
            or extract_work_order_no(retrieval_query)
        )
        if not work_order_no:
            return [
                _tool_call_trace(
                    tool_name="query_order_status",
                    input_payload={"query": original_query},
                    output_payload={},
                    status="skipped",
                    error="missing_work_order_no",
                )
            ]
        return [self.order_status_tool.query(work_order_no, request_id=request_id)]


def build_augmented_context(
    request_id: str,
    session_id: str | None,
    original_query: str,
    normalized_query: str,
    contextual_query: str,
    is_follow_up: bool,
    context_terms: list[str],
    rewritten_query: str,
    retrieval_query: str,
    synonym_expansions: list[str],
    semantic_expansions: list[str],
    intent_label: str,
    sources: list[RetrievalResult],
    user_context: UserContext | None = None,
    tool_calls: list | None = None,
) -> str:
    """把用户原始问题和召回文档拼成大模型输入上下文。"""

    user_context = user_context or UserContext()
    lines = [
        f"请求ID：{request_id}",
        f"会话ID：{session_id or '无'}",
        f"租户ID：{user_context.tenant_id or '未指定'}",
        f"用户ID：{user_context.user_id or '未指定'}",
        f"权限标签：{', '.join(user_context.permission_tags) if user_context.permission_tags else '未指定'}",
        f"用户原始问题：{original_query}",
        f"归一化查询：{normalized_query}",
        f"是否跟进问答：{'是' if is_follow_up else '否'}",
        f"上下文改写查询：{contextual_query}",
        f"上下文关键术语：{', '.join(context_terms) if context_terms else '无'}",
        f"改写查询：{rewritten_query}",
        f"检索查询：{retrieval_query}",
        f"同义词扩展：{', '.join(synonym_expansions) if synonym_expansions else '无'}",
        f"语义扩展：{', '.join(semantic_expansions) if semantic_expansions else '无'}",
        f"识别意图：{intent_label}",
        "",
        "工具调用结果：",
    ]
    actual_tool_calls = tool_calls or []
    if actual_tool_calls:
        for index, call in enumerate(actual_tool_calls, start=1):
            payload = _tool_call_to_dict(call)
            output = payload.get("output") or {}
            lines.extend(
                [
                    f"[tool-{index}] 工具：{payload.get('tool_name')}",
                    f"状态：{payload.get('status')}",
                    f"耗时：{payload.get('latency_ms')}ms",
                    f"入参：{payload.get('input')}",
                    f"结果摘要：{output.get('summary', '无')}",
                ]
            )
            if payload.get("error"):
                lines.append(f"错误：{payload['error']}")
    else:
        lines.append("无")
    lines.extend(
        [
            "",
            "检索到的相关文档：",
        ]
    )
    if not sources:
        lines.append("未召回到相关文档。")
        return "\n".join(lines)

    for index, result in enumerate(sources, start=1):
        source = result.chunk.metadata.get("source", "unknown")
        title = (
            result.chunk.metadata.get("section_title")
            or result.chunk.metadata.get("title")
            or result.chunk.metadata.get("filename")
            or source
        )
        lines.extend(
            [
                f"[{index}] 来源：{source}",
                f"引用标签：[{index}]",
                f"标题：{title}",
                f"定位信息：{_format_location(result)}",
                f"综合分：{result.score:.6f}",
                f"召回综合分：{_format_score(result.retrieval_score)}",
                f"重排分：{_format_score(result.rerank_score)}",
                f"语义分：{_format_score(result.semantic_score)}",
                f"BM25 原始分：{_format_score(result.bm25_score)}",
                f"BM25 归一化分：{_format_score(result.normalized_bm25_score)}",
                f"内容：{result.chunk.text}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def _normalize_query(question: str) -> str:
    return " ".join(question.split())


_STREAM_DONE = object()


class _StreamingAnswerProxy:
    def __init__(
        self,
        answer_generator: AnswerGenerator,
        events: Queue[dict[str, Any] | object],
    ) -> None:
        self.answer_generator = answer_generator
        self.events = events
        self._retrieval_emitted = False

    def answer(
        self,
        question: str,
        sources: list[RetrievalResult],
        augmented_context: str | None = None,
    ) -> str:
        request_id = _request_id_from_augmented_context(augmented_context)
        self._emit_retrieval(request_id=request_id, sources=sources)
        chunks: list[str] = []
        stream_answer = getattr(self.answer_generator, "stream_answer", None)
        if callable(stream_answer):
            for chunk in stream_answer(
                question=question,
                sources=sources,
                augmented_context=augmented_context,
            ):
                if not chunk:
                    continue
                chunks.append(chunk)
                self.events.put(
                    {
                        "event": "answer_delta",
                        "data": {
                            "request_id": request_id,
                            "delta": chunk,
                        },
                    }
                )
            return "".join(chunks)

        answer = self.answer_generator.answer(
            question=question,
            sources=sources,
            augmented_context=augmented_context,
        )
        if answer:
            self.events.put(
                {
                    "event": "answer_delta",
                    "data": {
                        "request_id": request_id,
                        "delta": answer,
                    },
                }
            )
        return answer

    def _emit_retrieval(
        self,
        *,
        request_id: str | None,
        sources: list[RetrievalResult],
    ) -> None:
        if self._retrieval_emitted:
            return
        self._retrieval_emitted = True
        self.events.put(
            {
                "event": "retrieval",
                "data": {
                    "request_id": request_id,
                    "retrieved_count": len(sources),
                    "reranked_count": len(sources),
                    "sources": [_stream_source_snapshot(source) for source in sources],
                },
            }
        )


def _request_id_from_augmented_context(context: str | None) -> str | None:
    if not context:
        return None
    for line in context.splitlines():
        if line.startswith("请求ID："):
            return line.split("：", 1)[1].strip() or None
    return None


def _stream_source_snapshot(result: RetrievalResult) -> dict[str, Any]:
    return {
        "chunk": {
            "id": result.chunk.id,
            "document_id": result.chunk.document_id,
            "text": result.chunk.text,
            "metadata": _stream_source_metadata(result.chunk.metadata),
        },
        "score": result.score,
        "semantic_score": result.semantic_score,
        "bm25_score": result.bm25_score,
        "normalized_bm25_score": result.normalized_bm25_score,
        "keyword_score": result.keyword_score,
        "retrieval_score": result.retrieval_score,
        "rerank_score": result.rerank_score,
    }


def _stream_source_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "source",
        "section_title",
        "title",
        "filename",
        "page_number",
        "slide_number",
        "time_range",
        "timestamp_range",
        "business_module",
    )
    return {
        key: metadata[key]
        for key in keys
        if metadata.get(key) not in (None, "")
    }


def _precheck_rerank_skip_reason(
    settings: Settings,
    reranker: Reranker,
    intent_label: str,
    intent_confidence: float,
    is_follow_up: bool,
) -> str | None:
    if not getattr(reranker, "enabled", False):
        return "provider_disabled"
    if settings.rerank_trigger == "always":
        return None
    if is_follow_up:
        return None
    if intent_label in settings.rerank_intents:
        return None
    if intent_confidence < settings.rerank_min_intent_confidence:
        return None
    return "auto_trigger_not_matched"


def _top_without_rerank(
    results: list[RetrievalResult],
    top_k: int,
) -> list[RetrievalResult]:
    if top_k <= 0:
        return []
    normalized: list[RetrievalResult] = []
    for result in results[:top_k]:
        base_score = result.score if result.retrieval_score is None else result.retrieval_score
        normalized.append(replace(result, retrieval_score=base_score))
    return normalized


def _fallback_answer_for_generation_error(sources: list[RetrievalResult]) -> str:
    if not sources:
        return "回答生成失败，且未召回到可用知识片段，请转人工处理。"
    return (
        "回答生成失败，已保留本次检索到的知识来源。"
        "请根据来源片段人工核验处理建议，必要时转人工闭环。"
    )


def _append_degradation(current: str | None, item: str) -> str:
    if not current:
        return item
    return f"{current}; {item}"


def _tool_call_trace(
    tool_name: str,
    input_payload: dict,
    output_payload: dict,
    status: str,
    error: str | None = None,
):
    from rag_app.core.models import ToolCallTrace

    return ToolCallTrace(
        tool_name=tool_name,
        input=input_payload,
        output=output_payload,
        status=status,
        latency_ms=0.0,
        error=error,
    )


def _tool_call_to_dict(call) -> dict:
    if isinstance(call, dict):
        return call
    return asdict(call)


def _format_score(score: float | None) -> str:
    if score is None:
        return "无"
    return f"{score:.6f}"


def _format_location(result: RetrievalResult) -> str:
    metadata = result.chunk.metadata
    for key in ("page_number", "slide_number", "time_range", "timestamp_range"):
        value = metadata.get(key)
        if value not in (None, ""):
            return str(value)
    section_title = metadata.get("section_title")
    if section_title not in (None, ""):
        return str(section_title)
    return "无"
