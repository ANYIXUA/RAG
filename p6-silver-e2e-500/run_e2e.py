"""P6-Silver-E2E-500 任务二/三：调用真实生产 RAG 链路执行 500 条测试并记录完整 Trace。

要点：
- 生产入口：rag_app.retrieval.online.OnlineQueryProcessor.process()（与 CLI query / rag-api 同一条代码路径）。
- 不 mock：检索、Embedding、LLM、Redis 会话记忆、PostgreSQL 日志全部走真实配置。
- Cross-Encoder 默认关闭（.env RAG_RERANK_PROVIDER=none，与 P5 方法 C hybrid 一致）。
- 评测层包装器只做观测：记录 chat completion 的 token usage 与 embedding 用量、Prompt 哈希，
  不改变请求参数与提示词。
- 断点续跑：results.jsonl 已存在的 case_id 自动跳过；单条最多 3 次尝试；失败保留记录。
- 并发：3 个线程各自独立的处理器实例，互不共享可变状态。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT)]

OUT = Path(__file__).parent
CASES = OUT / "silver_cases.jsonl"
RESULTS = OUT / "results.jsonl"
RUN_CONFIG = OUT / "run_config.json"

P6_VERSION = "p6-silver-e2e-v1"


def _load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _prepare_runtime_env() -> None:
    # Published archive: supply local DB/Redis endpoints via .env or environment.
    _load_env_file()

class TokenCountingAnswerGenerator:
    """包装真实 OpenAIAnswerGenerator：请求参数不变，仅捕获 usage 与输入内容哈希。"""

    def __init__(self, delegate) -> None:
        self._delegate = delegate
        self.last_usage: dict = {}
        self.last_prompt_sha256: str | None = None
        self.last_request: dict = {}

    def answer(self, question: str, sources, augmented_context: str | None = None) -> str:
        kwargs = self._delegate._chat_completion_kwargs(
            question=question, sources=sources, augmented_context=augmented_context,
        )
        self.last_request = {
            "model": kwargs.get("model"),
            "temperature": kwargs.get("temperature"),
            "max_tokens": kwargs.get("max_tokens"),
        }
        self.last_prompt_sha256 = hashlib.sha256(
            json.dumps(kwargs["messages"], ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        response = self._delegate.client.chat.completions.create(**kwargs)
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.last_usage = {
                "input_tokens": getattr(usage, "prompt_tokens", None),
                "output_tokens": getattr(usage, "completion_tokens", None),
            }
        return response.choices[0].message.content or ""


class TokenCountingEmbedder:
    """包装真实 OpenAIEmbedder：同样只记录 usage。"""

    def __init__(self, delegate) -> None:
        self._delegate = delegate
        self.embed_calls = 0
        self.last_usage: dict = {}

    def embed(self, texts: list[str]) -> list[list[float]]:
        chunks = []
        batch = self._delegate.batch_size
        for start in range(0, len(texts), batch):
            seg = texts[start:start + batch]
            kwargs = {"model": self._delegate.model, "input": seg}
            if self._delegate.dimensions is not None:
                kwargs["dimensions"] = self._delegate.dimensions
            response = self._delegate.client.embeddings.create(**kwargs)
            usage = getattr(response, "usage", None)
            if usage is not None:
                self.last_usage = {
                    "input_tokens": getattr(usage, "total_tokens", None),
                }
            self.embed_calls += len(seg)
            from rag_app.indexing.embeddings import _ordered_embeddings
            chunks.extend(_ordered_embeddings(response.data))
        return chunks


def _build_processor():
    from rag_app.core.config import Settings
    from rag_app.retrieval.online import OnlineQueryProcessor

    settings = Settings.from_env()
    processor = OnlineQueryProcessor(settings)
    processor.answer_generator = TokenCountingAnswerGenerator(processor.answer_generator)
    processor.embedder = TokenCountingEmbedder(processor.embedder)
    return settings, processor


def _source_snapshot(result) -> dict:
    chunk = result.chunk
    meta = chunk.metadata or {}
    return {
        "chunk_id": chunk.chunk_id if hasattr(chunk, "chunk_id") else meta.get("chunk_id"),
        "source": meta.get("source"),
        "title": meta.get("section_title") or meta.get("title"),
        "page_number": meta.get("page_number"),
        "score": round(result.score, 6),
        "retrieval_score": None if result.retrieval_score is None else round(result.retrieval_score, 6),
        "semantic_score": None if result.semantic_score is None else round(result.semantic_score, 6),
        "bm25_score": None if result.bm25_score is None else round(result.bm25_score, 6),
        "rerank_score": None if result.rerank_score is None else round(result.rerank_score, 6),
    }


def _trace_snapshot(trace) -> dict:
    return {
        "request_id": trace.request_id,
        "session_id": trace.session_id,
        "is_follow_up": trace.is_follow_up,
        "original_query": trace.original_query,
        "normalized_query": trace.normalized_query,
        "contextual_query": trace.contextual_query,
        "context_terms": trace.context_terms,
        "rewritten_query": trace.rewritten_query,
        "retrieval_query": trace.retrieval_query,
        "synonym_expansions": trace.synonym_expansions,
        "semantic_expansions": trace.semantic_expansions,
        "query_rewrite_rules": trace.query_rewrite_rules,
        "intent_label": trace.intent_label,
        "intent_confidence": trace.intent_confidence,
        "top_k": trace.top_k,
        "retrieval_mode": trace.retrieval_mode,
        "semantic_weight": trace.semantic_weight,
        "bm25_weight": trace.bm25_weight,
        "retrieval_candidate_k": trace.retrieval_candidate_k,
        "rerank_provider": trace.rerank_provider,
        "rerank_model": trace.rerank_model,
        "reranked_count": trace.reranked_count,
        "retrieved_count": trace.retrieved_count,
        "latency_ms": trace.latency_ms,
        "retrieval_latency_ms": trace.retrieval_latency_ms,
        "generation_latency_ms": trace.generation_latency_ms,
        "context_latency_ms": trace.context_latency_ms,
        "intent_latency_ms": trace.intent_latency_ms,
        "rewrite_latency_ms": trace.rewrite_latency_ms,
        "embedding_latency_ms": trace.embedding_latency_ms,
        "vector_search_latency_ms": trace.vector_search_latency_ms,
        "rerank_latency_ms": trace.rerank_latency_ms,
        "rerank_applied": trace.rerank_applied,
        "rerank_skip_reason": trace.rerank_skip_reason,
        "degradation_reason": trace.degradation_reason,
        "query_embedding_cache_hit": trace.query_embedding_cache_hit,
        "authorized_source_count": trace.authorized_source_count,
        "tool_calls": [
            {
                "tool_name": call.tool_name,
                "status": call.status,
                "error": call.error,
                "latency_ms": call.latency_ms,
            }
            if not isinstance(call, dict) else call
            for call in (trace.tool_calls or [])
        ],
        "augmented_context": trace.augmented_context,
    }


class Worker:
    def __init__(self) -> None:
        self.settings, self.processor = _build_processor()
        self.model_name = self.processor.answer_generator._delegate.model
        self.embedding_model = self.processor.embedder._delegate.model

    def run_case(self, case: dict) -> dict:
        started = time.time()
        attempts = 0
        errors: list[str] = []
        record: dict | None = None
        while attempts < 3:
            attempts += 1
            try:
                self.processor.answer_generator.last_usage = {}
                self.processor.answer_generator.last_request = {}
                self.processor.embedder.last_usage = {}
                session_id = f"p6-e2e-{case['case_id']}"
                answer = self.processor.process(
                    case["question"], top_k=self.settings.top_k, session_id=session_id,
                )
                trace = answer.trace
                elapsed = time.time() - started
                record = {
                    "case_id": case["case_id"],
                    "question": case["question"],
                    "question_type": case["question_type"],
                    "label_type": case.get("label_type", "silver"),
                    "expected_behavior": case.get("expected_behavior"),
                    "reference_answer": case.get("reference_answer"),
                    "source_chunk_ids": case.get("source_chunk_ids", []),
                    "reference_evidence": case.get("source_evidence", []),
                    "run_state": "success",
                    "error_category": None,
                    "attempts": attempts,
                    "retries": attempts - 1,
                    "wall_seconds": round(elapsed, 3),
                    "execution": _trace_snapshot(trace),
                    "retrieval": {
                        "retrieval_mode": trace.retrieval_mode,
                        "retrieved_count": trace.retrieved_count,
                        "candidates": [_source_snapshot(s) for s in answer.sources],
                        "retrieval_latency_ms": trace.retrieval_latency_ms,
                        "vector_search_latency_ms": trace.vector_search_latency_ms,
                        "embedding_latency_ms": trace.embedding_latency_ms,
                        "rerank_latency_ms": trace.rerank_latency_ms,
                        "rerank_applied": trace.rerank_applied,
                        "rerank_skip_reason": trace.rerank_skip_reason,
                    },
                    "generation": {
                        "model": self.processor.answer_generator.last_request.get("model") or self.model_name,
                        "temperature": self.processor.answer_generator.last_request.get("temperature"),
                        "max_tokens": self.processor.answer_generator.last_request.get("max_tokens"),
                        "prompt_sha256": self.processor.answer_generator.last_prompt_sha256,
                        "answer": answer.answer,
                        "citations": [
                            {"chunk_id": s.chunk.metadata.get("chunk_id")
                             or getattr(s.chunk, "chunk_id", None),
                             "index_in_context": i + 1}
                            for i, s in enumerate(answer.sources)
                        ],
                        "usage": self.processor.answer_generator.last_usage,
                        "embedding_usage": self.processor.embedder.last_usage,
                        "generation_latency_ms": trace.generation_latency_ms,
                    },
                }
                break
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(exc).__name__}: {exc}")
                time.sleep(2.0 * attempts)
        if record is None:
            record = {
                "case_id": case["case_id"],
                "question": case["question"],
                "question_type": case["question_type"],
                "label_type": case.get("label_type", "silver"),
                "expected_behavior": case.get("expected_behavior"),
                "reference_answer": case.get("reference_answer"),
                "source_chunk_ids": case.get("source_chunk_ids", []),
                "reference_evidence": case.get("source_evidence", []),
                "run_state": "failed",
                "error_category": "model_call_or_execution_failure",
                "attempts": attempts,
                "retries": attempts - 1,
                "wall_seconds": round(time.time() - started, 3),
                "execution": None,
                "retrieval": None,
                "generation": {"answer": None, "usage": {}},
                "errors_detail": errors,
            }
        record["run_config_version"] = P6_VERSION
        return record


def _write_run_config(settings, workers: list) -> None:
    from rag_app import version as rag_version

    fingerprint_fp = getattr(settings, "config_fingerprint", None)
    config = {
        "run_config_version": P6_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project_version": getattr(rag_version, "APP_VERSION", None),
        "code_entry": "rag_app.retrieval.online.OnlineQueryProcessor.process（生产同步链路，未修改）",
        "retrieval": {
            "top_k": settings.top_k,
            "retrieval_mode": settings.retrieval_mode,
            "retrieval_candidate_k": settings.retrieval_candidate_k,
            "semantic_weight": settings.semantic_weight,
            "bm25_weight": settings.bm25_weight,
            "min_similarity_score": settings.min_similarity_score,
            "relative_score_threshold": settings.relative_score_threshold,
            "vector_store_provider": settings.vector_store_provider,
        },
        "rerank": {
            "provider": settings.rerank_provider,
            "model": settings.rerank_model,
            "trigger": settings.rerank_trigger,
            "note": "Cross-Encoder 与 P5 结论一致默认关闭（provider=none）",
        },
        "generation_model": {
            "provider": settings.llm_provider,
            "chat_model": settings.openai_chat_model,
            "base_url": settings.openai_base_url,
            "max_tokens": settings.openai_max_tokens,
            "temperature": 0.2,
            "generation_context_max_chars": settings.generation_context_max_chars,
        },
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.openai_embedding_model,
            "dimension": settings.embedding_dimension,
        },
        "auxiliary_services": {
            "conversation_memory_provider": settings.conversation_memory_provider,
            "redis_url": settings.redis_url,
            "ops_store": "postgresql（生产查询日志写入 rag 表）",
            "order_status_tool_enabled": settings.order_status_tool_enabled,
        },
        "observation_note": "评测层包装 TokenCounting 回答/Embedding 适配器只读取 usage，"
                            "不修改提示词与请求参数；未改动任何生产代码。",
        "execution_policy": {
            "concurrency": 3,
            "max_attempts_per_case": 3,
            "retry_backoff_seconds": 2,
            "per_case_unique_session": True,
            "checkpoint_resume": True,
            "denominator_rule": "每 case 仅计入一次；失败/超时单独统计，不冒充成功",
        },
        "config_fingerprint": fingerprint_fp,
        "llm_observed_models": sorted({w.model_name for w in workers}),
        "embedding_observed_models": sorted({w.embedding_model for w in workers}),
    }
    RUN_CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（0=全部剩余）")
    ap.add_argument("--smoke", type=int, default=10, help="先跑 N 条冒烟")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--only-smoke", action="store_true")
    a = ap.parse_args()

    _prepare_runtime_env()
    cases = [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]

    done: set[str] = set()
    if RESULTS.exists():
        for line in RESULTS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["case_id"])
    todo = [c for c in cases if c["case_id"] not in done]
    if a.limit:
        todo = todo[: a.limit]

    smoke_out = OUT / "smoke_report.md"
    if todo:
        # 冒烟测试：前 10 条串行执行并生成冒烟报告，不通过则终止全量
        smoke_cases = todo[: a.smoke]
        smoke_results = []
        workers = {i: Worker() for i in range(a.concurrency)}
        _write_run_config(workers[0].settings, list(workers.values()))
        for idx, case in enumerate(smoke_cases):
            w = workers[idx % a.concurrency]
            rec = w.run_case(case)
            smoke_results.append(rec)
            with RESULTS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        real_llm = sum(1 for r in smoke_results
                       if r["run_state"] == "success"
                       and r["generation"]["usage"].get("output_tokens"))
        retrieved = sum(1 for r in smoke_results
                        if r["run_state"] == "success"
                        and (r["execution"]["retrieved_count"] > 0 or r["retrieval"]["candidates"]))
        answers = sum(1 for r in smoke_results
                      if r["run_state"] == "success" and r["generation"]["answer"])
        lines = [
            "# P6 Silver Smoke Test（前 10 条）",
            "",
            f"- 执行数：{len(smoke_results)}",
            f"- 调用真实 LLM 并获得 token 用量：{real_llm}/{len(smoke_results)}",
            f"- 检索返回候选：{retrieved}/{len(smoke_results)}",
            f"- 生成最终答案非空：{answers}/{len(smoke_results)}",
            "",
            "| case_id | 问题 | 状态 | 检索数 | 意图 | 耗时ms | 答案摘要 |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in smoke_results:
            ex = r["execution"] or {}
            q = (r["question"] or "")[:22].replace("|", "丨")
            ans = (r["generation"].get("answer") or "")[:40].replace("|", "丨").replace("\n", " ")
            lines.append(
                f"| {r['case_id']} | {q} | {r['run_state']} | "
                f"{(ex.get('retrieved_count') if ex else 0)} | {ex.get('intent_label', '-') if ex else '-'} | "
                f"{r['wall_seconds'] * 1000:.0f} | {ans} |"
            )
        smoke_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        if answers < len(smoke_results) - 1 or real_llm < len(smoke_results) - 1:
            print("SMOKE GATE FAILED；停止全量执行。", flush=True)
            return 4
        print("SMOKE PASS。", flush=True)

    if a.only_smoke:
        return 0

    done_after_smoke = {c["case_id"] for c in smoke_results} if todo else set()
    main_done = done | done_after_smoke
    pending = [c for c in cases if c["case_id"] not in main_done][: a.limit or None]
    print(f"待执行 {len(pending)} 条（已完成 {len(done)}）。", flush=True)
    results_lock = Lock()
    workers = [Worker() for _ in range(a.concurrency)]
    if not (OUT / "run_config.json").exists():
        try:
            _write_run_config(workers[0].settings, workers)
        except Exception as exc:  # noqa: BLE001
            print(f"run_config 写入失败（不阻断）：{exc!r}", flush=True)

    def run(idx: int, case: dict) -> dict:
        return workers[idx % a.concurrency].run_case(case)

    started_wall = time.time()
    ok = err = 0
    with ThreadPoolExecutor(max_workers=a.concurrency) as pool:
        futures = {pool.submit(run, i, case): case["case_id"]
                   for i, case in enumerate(pending)}
        for future in as_completed(futures):
            rec = future.result()
            with results_lock, RESULTS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec["run_state"] == "success":
                ok += 1
            else:
                err += 1
                print(f"[FAIL] {rec['case_id']} {rec['errors_detail'][:1]}", flush=True)
            total = ok + err
            if total % 25 == 0:
                rate = total / max(time.time() - started_wall, 1)
                print(f"progress {total}/{len(pending)} ok={ok} err={err} rate={rate:.2f}/s", flush=True)
    print(f"完成：ok={ok} err={err} 用时 {time.time() - started_wall:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
