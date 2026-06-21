from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from dataclasses import replace
from unittest.mock import patch

from rag_app import prompt_templates
from rag_app.core.config import Settings
from rag_app.core.models import ToolCallTrace, UserContext
from rag_app.indexing.offline import OfflineKnowledgeBuilder
from rag_app.retrieval.online import OnlineQueryProcessor, build_augmented_context
from tests.helpers import (
    DeterministicEmbedder,
    MemoryQueryLogStore,
    MemoryVectorStore,
    SimpleAnswerGenerator,
    production_settings,
)


class OnlineProcessingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.vector_store = MemoryVectorStore()
        self.query_log_store = MemoryQueryLogStore()
        self.embedder = DeterministicEmbedder()
        self.answer_generator = SimpleAnswerGenerator()
        self.patches = [
            patch("rag_app.indexing.offline.create_embedder", return_value=self.embedder),
            patch("rag_app.indexing.offline.create_vector_store", return_value=self.vector_store),
            patch("rag_app.retrieval.online.create_embedder", return_value=self.embedder),
            patch("rag_app.retrieval.online.create_vector_store", return_value=self.vector_store),
            patch("rag_app.retrieval.online.create_answer_generator", return_value=self.answer_generator),
            patch("rag_app.retrieval.online.create_query_log_store", return_value=self.query_log_store),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()

    def test_online_processing_builds_augmented_context(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text(
                "# 故障案例\n\n## 光猫 LOS 红灯\n\n光猫 LOS 红灯通常表示光路异常，需要检查尾纤、分光器端口和光功率。",
                encoding="utf-8",
            )
            settings = _settings(base_dir, data_dir, storage_dir)
            OfflineKnowledgeBuilder(settings).refresh(reset=True)

            processor = OnlineQueryProcessor(settings)
            result = processor.process("光猫红灯怎么处理？", top_k=1)
            repeat = processor.process("光猫红灯怎么处理？", top_k=1)

            self.assertEqual(result.question, "光猫红灯怎么处理？")
            self.assertEqual(len(result.sources), 1)
            self.assertIsNotNone(result.trace)
            self.assertEqual(result.trace.top_k, 1)
            self.assertEqual(result.trace.retrieval_mode, "hybrid")
            self.assertEqual(result.trace.bm25_weight, 0.3)
            self.assertEqual(result.trace.retrieval_candidate_k, 20)
            self.assertTrue(result.trace.request_id)
            self.assertTrue(result.trace.created_at)
            self.assertIsNone(result.trace.session_id)
            self.assertFalse(result.trace.is_follow_up)
            self.assertEqual(result.trace.rerank_provider, "none")
            self.assertEqual(result.trace.rerank_model, "none")
            self.assertEqual(result.trace.rerank_candidate_k, 20)
            self.assertEqual(result.trace.reranked_count, 1)
            self.assertEqual(result.trace.intent_label, "recommend_solution")
            self.assertEqual(result.trace.contextual_query, "光猫红灯怎么处理？")
            self.assertEqual(result.trace.context_terms, [])
            self.assertIn("现场处理建议", result.trace.retrieval_query)
            self.assertIn("ONU", result.trace.synonym_expansions)
            self.assertGreater(result.trace.query_embedding_dimensions, 0)
            self.assertGreaterEqual(result.trace.latency_ms, 0.0)
            self.assertGreaterEqual(result.trace.retrieval_latency_ms, 0.0)
            self.assertGreaterEqual(result.trace.generation_latency_ms, 0.0)
            self.assertGreaterEqual(result.trace.context_latency_ms, 0.0)
            self.assertGreaterEqual(result.trace.intent_latency_ms, 0.0)
            self.assertGreaterEqual(result.trace.rewrite_latency_ms, 0.0)
            self.assertGreaterEqual(result.trace.embedding_latency_ms, 0.0)
            self.assertGreaterEqual(result.trace.vector_search_latency_ms, 0.0)
            self.assertGreaterEqual(result.trace.rerank_latency_ms, 0.0)
            self.assertFalse(result.trace.rerank_applied)
            self.assertEqual(result.trace.rerank_skip_reason, "provider_disabled")
            self.assertIsNone(result.trace.degradation_reason)
            self.assertFalse(result.trace.query_embedding_cache_hit)
            self.assertTrue(repeat.trace.query_embedding_cache_hit)
            self.assertIn("请求ID：", result.trace.augmented_context)
            self.assertIn("会话ID：无", result.trace.augmented_context)
            self.assertIn("是否跟进问答：否", result.trace.augmented_context)
            self.assertIn("上下文关键术语：无", result.trace.augmented_context)
            self.assertIn("用户原始问题：光猫红灯怎么处理？", result.trace.augmented_context)
            self.assertIn("检索查询：", result.trace.augmented_context)
            self.assertIn("语义扩展：", result.trace.augmented_context)
            self.assertIn("综合分：", result.trace.augmented_context)
            self.assertIn("召回综合分：", result.trace.augmented_context)
            self.assertIn("重排分：", result.trace.augmented_context)
            self.assertIn("BM25 原始分：", result.trace.augmented_context)
            self.assertIn("BM25 归一化分：", result.trace.augmented_context)
            self.assertIn("标题：光猫 LOS 红灯", result.trace.augmented_context)
            self.assertIn("识别意图：recommend_solution", result.trace.augmented_context)
            self.assertIn("检索到的相关文档", result.trace.augmented_context)
            self.assertIn("光猫 LOS 红灯", result.trace.augmented_context)
            self.assertEqual(len(self.query_log_store.records), 2)

    def test_augmented_context_uses_external_prompt_templates(self) -> None:
        with TemporaryDirectory() as temp_dir:
            prompt_root = Path(temp_dir) / "prompts"
            prompt_dir = prompt_root / "answer_generation"
            prompt_dir.mkdir(parents=True)
            (prompt_dir / "augmented_context.md").write_text(
                "REQ={request_id}\nTOOLS={tool_calls_block}\nSOURCES={sources_block}",
                encoding="utf-8",
            )
            (prompt_dir / "augmented_tool_calls_empty.md").write_text(
                "NO TOOLS",
                encoding="utf-8",
            )
            (prompt_dir / "augmented_sources_empty.md").write_text(
                "NO SOURCES",
                encoding="utf-8",
            )

            with patch.object(prompt_templates, "PROMPT_ROOT", prompt_root):
                prompt_templates.load_prompt_template.cache_clear()
                context = build_augmented_context(
                    request_id="req-1",
                    session_id=None,
                    original_query="光猫红灯怎么处理？",
                    normalized_query="光猫红灯怎么处理？",
                    contextual_query="光猫红灯怎么处理？",
                    is_follow_up=False,
                    context_terms=[],
                    rewritten_query="光猫 LOS 红灯怎么处理？",
                    retrieval_query="光猫 LOS 红灯怎么处理？ ONU",
                    synonym_expansions=["ONU"],
                    semantic_expansions=["现场处理建议"],
                    intent_label="recommend_solution",
                    sources=[],
                    user_context=UserContext(),
                    tool_calls=[],
                )

        prompt_templates.load_prompt_template.cache_clear()
        self.assertEqual(
            context,
            "REQ=req-1\nTOOLS=NO TOOLS\nSOURCES=NO SOURCES",
        )

    def test_online_processing_reads_latest_vector_store_each_query(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            source_file = data_dir / "fault.md"
            source_file.write_text(
                "光猫 LOS 红灯需要检查尾纤。",
                encoding="utf-8",
            )
            settings = _settings(base_dir, data_dir, storage_dir)
            OfflineKnowledgeBuilder(settings).refresh(reset=True)
            processor = OnlineQueryProcessor(settings)

            first = processor.process("光猫红灯怎么处理？", top_k=1)
            source_file.write_text(
                "光猫 LOS 红灯需要检查尾纤，并登记转人工原因。",
                encoding="utf-8",
            )
            OfflineKnowledgeBuilder(settings).refresh()
            second = processor.process("转人工原因怎么登记？", top_k=1)

            self.assertIn("需要检查尾纤", first.trace.augmented_context)
            self.assertNotIn("登记转人工原因", first.trace.augmented_context)
            self.assertIn("登记转人工原因", second.trace.augmented_context)

    def test_online_processing_can_apply_custom_reranker(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text(
                "# 故障案例\n\n## 光猫 LOS 红灯\n\n光猫 LOS 红灯处理建议。\n\n## 地址校验失败\n\n地址校验失败处理建议。",
                encoding="utf-8",
            )
            settings = production_settings(
                base_dir,
                data_dir=data_dir,
                storage_dir=storage_dir,
                chunk_size=200,
                chunk_overlap=20,
                min_similarity_score=-1.0,
                relative_score_threshold=0.0,
                rerank_candidate_k=2,
            )
            OfflineKnowledgeBuilder(settings).refresh(reset=True)
            processor = OnlineQueryProcessor(settings, reranker=_PreferAddressReranker())

            result = processor.process("光猫红灯怎么处理？", top_k=1)

            self.assertEqual(result.sources[0].chunk.metadata.get("section_title"), "地址校验失败")
            self.assertEqual(result.sources[0].rerank_score, 1.0)
            self.assertEqual(result.trace.rerank_provider, "stub-cross-encoder")
            self.assertEqual(result.trace.rerank_model, "stub")
            self.assertEqual(result.trace.reranked_count, 1)
            self.assertTrue(result.trace.rerank_applied)
            self.assertIsNone(result.trace.rerank_skip_reason)

    def test_online_processing_rewrites_follow_up_query_with_session(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text(
                "# 故障案例\n\n## 光猫 LOS 红灯\n\n光猫 LOS 红灯需要先检查尾纤。",
                encoding="utf-8",
            )
            settings = _settings(base_dir, data_dir, storage_dir)
            OfflineKnowledgeBuilder(settings).refresh(reset=True)
            processor = OnlineQueryProcessor(settings)

            first = processor.process("光猫红灯咋办", top_k=1, session_id="u-1")
            second = processor.process("这个要先看什么", top_k=1, session_id="u-1")

            self.assertFalse(first.trace.is_follow_up)
            self.assertTrue(second.trace.is_follow_up)
            self.assertEqual(second.trace.session_id, "u-1")
            self.assertIn("光猫 LOS 红灯怎么处理", second.trace.contextual_query)
            self.assertIn("会话ID：u-1", second.trace.augmented_context)
            self.assertIn("是否跟进问答：是", second.trace.augmented_context)

    def test_auto_rerank_skips_low_risk_query(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "knowledge.md").write_text(
                "# RAG 知识库\n\nRAG 用于连接大模型和可检索知识库。",
                encoding="utf-8",
            )
            settings = _settings(
                base_dir,
                data_dir,
                storage_dir,
            )
            settings = replace(
                settings,
                rerank_trigger="auto",
                rerank_intents=("recommend_solution",),
                rerank_min_intent_confidence=0.0,
            )
            OfflineKnowledgeBuilder(settings).refresh(reset=True)

            result = OnlineQueryProcessor(
                settings,
                reranker=_FailingReranker(),
            ).process("介绍 RAG 框架", top_k=1)

            self.assertEqual(result.trace.intent_label, "general_knowledge")
            self.assertFalse(result.trace.rerank_applied)
            self.assertEqual(result.trace.rerank_skip_reason, "auto_trigger_not_matched")
            self.assertIsNone(result.trace.degradation_reason)

    def test_rerank_failure_degrades_to_first_stage_results(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text(
                "# 故障案例\n\n## 光猫 LOS 红灯\n\n光猫 LOS 红灯处理建议。"
                "\n\n## 地址校验失败\n\n地址校验失败处理建议。",
                encoding="utf-8",
            )
            settings = replace(
                _settings(base_dir, data_dir, storage_dir),
                min_similarity_score=-1.0,
                relative_score_threshold=0.0,
            )
            OfflineKnowledgeBuilder(settings).refresh(reset=True)

            result = OnlineQueryProcessor(
                settings,
                reranker=_FailingReranker(),
            ).process("光猫红灯咋办", top_k=1)

            self.assertEqual(len(result.sources), 1)
            self.assertFalse(result.trace.rerank_applied)
            self.assertEqual(result.trace.rerank_skip_reason, "rerank_failed")
            self.assertIn("rerank_failed", result.trace.degradation_reason)

    def test_generation_failure_returns_degraded_answer(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text(
                "# 故障案例\n\n## 光猫 LOS 红灯\n\n光猫 LOS 红灯处理建议。",
                encoding="utf-8",
            )
            settings = _settings(base_dir, data_dir, storage_dir)
            OfflineKnowledgeBuilder(settings).refresh(reset=True)

            result = OnlineQueryProcessor(
                settings,
                answer_generator=_FailingAnswerGenerator(),
            ).process("光猫红灯咋办", top_k=1)

            self.assertIn("回答生成失败", result.answer)
            self.assertIn("generation_failed", result.trace.degradation_reason)

    def test_embedding_failure_falls_back_to_bm25_retrieval(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text(
                "# 故障案例\n\n## 光猫 LOS 红灯\n\n光猫 LOS 红灯处理建议。",
                encoding="utf-8",
            )
            settings = _settings(base_dir, data_dir, storage_dir)
            OfflineKnowledgeBuilder(settings).refresh(reset=True)

            result = OnlineQueryProcessor(
                settings,
                embedder=_FailingEmbedder(),
            ).process("光猫 LOS 红灯怎么办", top_k=1)

            self.assertEqual(len(result.sources), 1)
            self.assertEqual(result.trace.retrieval_mode, "bm25")
            self.assertEqual(result.trace.query_embedding_dimensions, 0)
            self.assertIn("embedding_failed", result.trace.degradation_reason)

    def test_order_status_query_calls_tool(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            settings = _settings(base_dir, data_dir, storage_dir)

            result = OnlineQueryProcessor(
                settings,
                order_status_tool=_StaticOrderStatusTool(),
            ).process(
                "帮我查一下工单 WO202604290001 现在到哪了",
                top_k=1,
            )

            self.assertEqual(result.trace.intent_label, "query_order_status")
            self.assertEqual(len(result.trace.tool_calls), 1)
            self.assertEqual(result.trace.tool_calls[0].status, "success")
            self.assertEqual(result.trace.tool_calls[0].output["status"], "处理中")
            self.assertIn("工具查询结果", result.answer)
            self.assertIn("处理中", result.answer)
            self.assertIn("工具调用结果", result.trace.augmented_context)
            self.assertTrue(self.query_log_store.records[-1]["tool_calls"])

    def test_error_code_query_uses_exact_match(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "error_codes.json").write_text(
                (
                    '{"title":"异常码说明","errors":['
                    '{"error_code":"E203","message":"地址不存在","advice":"核对标准地址"},'
                    '{"error_code":"E204","message":"账号冻结","advice":"联系管理员"}'
                    ']}'
                ),
                encoding="utf-8",
            )
            settings = production_settings(
                base_dir,
                data_dir=data_dir,
                storage_dir=storage_dir,
                chunk_size=200,
                chunk_overlap=20,
            )
            OfflineKnowledgeBuilder(settings).refresh(reset=True)

            result = OnlineQueryProcessor(settings).process(
                "接口返回 e203 是什么意思？",
                top_k=2,
            )

            self.assertEqual(result.trace.intent_label, "explain_error")
            self.assertEqual(result.trace.retrieval_mode, "exact_error_code")
            self.assertEqual(result.trace.query_embedding_dimensions, 0)
            self.assertEqual(result.trace.rerank_skip_reason, "exact_error_code")
            self.assertEqual([item.chunk.metadata.get("error_code") for item in result.sources], ["E203"])
            self.assertIn("地址不存在", result.trace.augmented_context)
            self.assertNotIn("账号冻结", result.trace.augmented_context)

    def test_stream_processing_emits_retrieval_deltas_and_complete_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text(
                "# 故障案例\n\n## 光猫 LOS 红灯\n\n光猫 LOS 红灯需要检查尾纤。",
                encoding="utf-8",
            )
            settings = _settings(base_dir, data_dir, storage_dir)
            OfflineKnowledgeBuilder(settings).refresh(reset=True)
            for record in self.vector_store.records:
                record.chunk.metadata["pdf_page_reports"] = [{"page_number": 1}]

            events = list(
                OnlineQueryProcessor(
                    settings,
                    answer_generator=_StreamingAnswerGenerator(),
                ).stream_process("光猫红灯咋办", top_k=1)
            )

            self.assertEqual(
                [event["event"] for event in events],
                ["retrieval", "answer_delta", "answer_delta", "complete"],
            )
            retrieval = events[0]["data"]
            self.assertTrue(retrieval["request_id"])
            self.assertEqual(retrieval["retrieved_count"], 1)
            self.assertEqual(retrieval["reranked_count"], 1)
            self.assertEqual(len(retrieval["sources"]), 1)
            self.assertNotIn("pdf_page_reports", retrieval["sources"][0]["chunk"]["metadata"])
            self.assertEqual(events[1]["data"]["delta"], "第一段")
            self.assertEqual(events[2]["data"]["delta"], "第二段")
            complete = events[-1]["data"]
            self.assertEqual(complete["answer"], "第一段第二段")
            self.assertEqual(complete["request_id"], retrieval["request_id"])
            self.assertEqual(complete["trace"]["request_id"], retrieval["request_id"])
            self.assertEqual(len(self.query_log_store.records), 1)


def _settings(base_dir: Path, data_dir: Path, storage_dir: Path) -> Settings:
    return production_settings(
        base_dir,
        data_dir=data_dir,
        storage_dir=storage_dir,
        chunk_size=40,
        chunk_overlap=5,
    )


class _PreferAddressReranker:
    provider_name = "stub-cross-encoder"
    model_name = "stub"
    enabled = True

    def rerank(self, query: str, results, top_k: int):
        del query
        reranked = []
        for result in results:
            score = 1.0 if "地址校验失败" in result.chunk.text else 0.0
            reranked.append(
                replace(
                    result,
                    score=score,
                    retrieval_score=result.score,
                    rerank_score=score,
                )
            )
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:top_k]


class _FailingReranker:
    provider_name = "stub-cross-encoder"
    model_name = "stub"
    enabled = True

    def rerank(self, query: str, results, top_k: int):
        del query, results, top_k
        raise RuntimeError("rerank unavailable")


class _FailingAnswerGenerator:
    def answer(self, question: str, sources, augmented_context: str | None = None) -> str:
        del question, sources, augmented_context
        raise RuntimeError("llm timeout")


class _StreamingAnswerGenerator:
    def answer(self, question: str, sources, augmented_context: str | None = None) -> str:
        del question, sources, augmented_context
        return "同步回答"

    def stream_answer(self, question: str, sources, augmented_context: str | None = None):
        del question, sources, augmented_context
        yield "第一段"
        yield "第二段"


class _FailingEmbedder:
    def embed(self, texts: list[str]) -> list[list[float]]:
        del texts
        raise RuntimeError("embedding timeout")


class _StaticOrderStatusTool:
    provider_name = "postgresql"
    enabled = True

    def query(
        self,
        work_order_no: str,
        request_id: str | None = None,
    ) -> ToolCallTrace:
        return ToolCallTrace(
            tool_name="query_order_status",
            input={
                "work_order_no": work_order_no,
                "provider": self.provider_name,
                "request_id": request_id,
            },
            output={
                "found": True,
                "work_order_no": work_order_no,
                "status": "处理中",
                "summary": f"工单 {work_order_no} 当前状态为 处理中，最近流转动作为 现场处理。",
            },
            status="success",
            latency_ms=1.0,
        )


if __name__ == "__main__":
    unittest.main()
