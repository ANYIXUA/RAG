"""RAG 框架的命令行入口。"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from rag_app.operations.evaluation import (
    EvaluationThresholds,
    compare_rerank_runs,
    evaluate_release_gate,
    load_evaluation_report,
    load_retrieval_eval_cases,
    save_evaluation_report,
)
from rag_app.core.config import Settings
from rag_app.indexing.offline import OfflineKnowledgeBuilder
from rag_app.operations.ops import (
    build_feedback_record,
    build_request_trace,
    create_feedback_store,
    create_query_log_store,
)
from rag_app.rag import RAGPipeline
from rag_app.version import get_build_info


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ops RAG CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    version = subparsers.add_parser("version", help="查看应用版本和构建信息")
    version.add_argument("--json", action="store_true", help="输出 JSON 结果")

    offline = subparsers.add_parser(
        "offline-refresh",
        help="离线刷新知识库：扫描文档、切片、向量化并写入向量库",
    )
    offline.add_argument("--source", type=Path, default=None, help="知识文档目录")
    offline.add_argument("--reset", action="store_true", help="清空已有向量后全量重建")
    offline.add_argument("--force", action="store_true", help="即使文件未变化也重新向量化")
    offline.add_argument("--json", action="store_true", help="输出 JSON 结果")

    query = subparsers.add_parser("query", help="在线问答：查询向量化、混合检索并生成回答")
    query.add_argument("question", help="用户原始问题")
    query.add_argument("--top-k", type=int, default=None, help="召回的知识切片数量")
    query.add_argument("--session-id", default=None, help="会话 ID，用于多轮上下文连续问答")
    query.add_argument("--show-context", action="store_true", help="打印增强上下文")
    query.add_argument("--json", action="store_true", help="输出 JSON 结果")

    evaluate = subparsers.add_parser(
        "evaluate-retrieval",
        help="评测检索效果，并对比重排开启前后指标",
    )
    evaluate.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="检索评测集 JSONL 文件",
    )
    evaluate.add_argument("--top-k", type=int, default=3, help="评测使用的 top_k")
    evaluate.add_argument(
        "--with-rerank-provider",
        default="cross-encoder",
        help="对比实验中开启重排时的 provider",
    )
    evaluate.add_argument(
        "--with-rerank-model",
        default=None,
        help="对比实验中开启重排时的模型名或路径",
    )
    evaluate.add_argument(
        "--show-failures",
        action="store_true",
        help="打印未命中样本详情",
    )
    evaluate.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
        help="评测报告输出目录",
    )
    evaluate.add_argument(
        "--output",
        type=Path,
        default=None,
        help="评测报告输出文件；不传时自动按时间生成",
    )
    evaluate.add_argument(
        "--baseline",
        type=Path,
        default=Path("reports/retrieval_eval_baseline.json"),
        help="历史基线报告文件；文件不存在时只执行绝对指标门禁",
    )
    evaluate.add_argument("--no-save", action="store_true", help="只打印结果，不保存评测报告")
    evaluate.add_argument("--fail-on-gate", action="store_true", help="发布门禁失败时返回非 0")
    evaluate.add_argument("--min-hit-at-k", type=float, default=0.8, help="发布门禁：最低 Hit@K")
    evaluate.add_argument("--min-mrr", type=float, default=0.7, help="发布门禁：最低 MRR")
    evaluate.add_argument(
        "--max-no-result-rate",
        type=float,
        default=0.2,
        help="发布门禁：最大无结果率",
    )
    evaluate.add_argument(
        "--max-hit-at-k-drop",
        type=float,
        default=0.05,
        help="发布门禁：相对基线允许的 Hit@K 最大下降",
    )
    evaluate.add_argument(
        "--max-mrr-drop",
        type=float,
        default=0.05,
        help="发布门禁：相对基线允许的 MRR 最大下降",
    )
    evaluate.add_argument(
        "--max-no-result-rate-increase",
        type=float,
        default=0.05,
        help="发布门禁：相对基线允许的无结果率最大上升",
    )
    evaluate.add_argument(
        "--max-avg-latency-ms",
        type=float,
        default=None,
        help="发布门禁：最大平均延迟，默认不限制",
    )
    evaluate.add_argument(
        "--max-p95-latency-ms",
        type=float,
        default=None,
        help="发布门禁：最大 P95 延迟，默认不限制",
    )
    evaluate.add_argument(
        "--max-avg-latency-increase-ms",
        type=float,
        default=None,
        help="发布门禁：相对基线允许的平均延迟最大上升，默认不限制",
    )
    evaluate.add_argument(
        "--max-p95-latency-increase-ms",
        type=float,
        default=None,
        help="发布门禁：相对基线允许的 P95 延迟最大上升，默认不限制",
    )
    evaluate.add_argument("--json", action="store_true", help="输出 JSON 结果")

    query_logs = subparsers.add_parser(
        "query-logs",
        help="查看最近的在线问答结构化日志",
    )
    query_logs.add_argument("--limit", type=int, default=20, help="读取最近多少条")
    query_logs.add_argument("--json", action="store_true", help="输出 JSON 结果")

    feedback = subparsers.add_parser(
        "feedback",
        help="写入一次人工反馈，用于后续排查和样本沉淀",
    )
    feedback.add_argument("--request-id", required=True, help="需要反馈的请求 ID")
    feedback.add_argument("--session-id", default=None, help="会话 ID")
    feedback.add_argument("--question", default=None, help="用户问题")
    feedback.add_argument("--rating", type=int, default=None, help="1 到 5 分评分")
    feedback.add_argument(
        "--useful",
        choices=["true", "false"],
        default=None,
        help="回答是否有用",
    )
    feedback.add_argument("--comment", default=None, help="反馈说明")
    feedback.add_argument("--expected-answer", default=None, help="期望答案")
    feedback.add_argument("--label", action="append", default=[], help="问题标签，可重复")
    feedback.add_argument("--json", action="store_true", help="输出 JSON 结果")

    ops_summary = subparsers.add_parser(
        "ops-summary",
        help="查看查询日志和反馈的运维摘要",
    )
    ops_summary.add_argument("--limit", type=int, default=200, help="统计最近多少条")
    ops_summary.add_argument("--json", action="store_true", help="输出 JSON 结果")

    ops_trace = subparsers.add_parser(
        "ops-trace",
        help="按 request_id 查看一次问答的查询日志和反馈",
    )
    ops_trace.add_argument("request_id", help="请求 ID")
    ops_trace.add_argument("--json", action="store_true", help="输出 JSON 结果")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        payload = get_build_info()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"应用：{payload['app_name']}")
            print(f"版本：{payload['app_version']}")
            print(f"构建提交：{payload['build_commit'] or '未配置'}")
            print(f"构建时间：{payload['build_time'] or '未配置'}")
            print(f"镜像标签：{payload['image_tag'] or '未配置'}")
            print(f"知识库版本：{payload['knowledge_version'] or '未配置'}")
        return 0

    if args.command == "offline-refresh":
        builder = OfflineKnowledgeBuilder.from_env()
        report = builder.refresh(
            source_dir=args.source,
            reset=args.reset,
            force=args.force,
        )
        if args.json:
            print(json.dumps(asdict(report), ensure_ascii=False, indent=2))
        else:
            print(
                "离线知识库刷新完成："
                f"扫描 {report.documents_seen} 个文档，"
                f"更新 {report.documents_changed} 个，"
                f"跳过 {report.documents_skipped} 个，"
                f"删除 {report.documents_removed} 个，"
                f"向量化 {report.chunks_embedded} 个切片。"
            )
            print(
                "治理结果："
                f"候选文件 {report.files_seen} 个，"
                f"策略跳过 {report.documents_skipped_by_policy} 个，"
                f"解析失败 {report.documents_failed} 个。"
            )
            print(f"向量库记录数：{report.stored_records}")
            print(f"处理清单：{report.manifest_path}")
            print(f"向量库位置：{report.vector_store_path}")
            if report.refresh_report_path:
                print(f"刷新报告：{report.refresh_report_path}")
            if report.manifest_backup_path:
                print(f"上一版清单备份：{report.manifest_backup_path}")
            if report.skipped_files:
                print("跳过明细：")
                for item in report.skipped_files[:10]:
                    print(
                        f"- {item['source']} => {item['reason']}：{item['detail']}"
                    )
                if len(report.skipped_files) > 10:
                    print(f"- 其余 {len(report.skipped_files) - 10} 条见刷新报告")
            if report.failed_files:
                print("失败明细：")
                for item in report.failed_files[:10]:
                    print(
                        f"- {item['source']} => {item['reason']}：{item['detail']}"
                    )
        return 0

    if args.command == "query":
        pipeline = RAGPipeline.from_env()
        answer = pipeline.query(
            args.question,
            top_k=args.top_k,
            session_id=args.session_id,
        )
        if args.json:
            print(json.dumps(_answer_to_dict(answer), ensure_ascii=False, indent=2))
        else:
            if answer.trace is not None:
                print(f"请求ID：{answer.trace.request_id}")
                print(
                    "识别意图："
                    f"{answer.trace.intent_label} "
                    f"(confidence={answer.trace.intent_confidence:.2f})"
                )
                print(f"是否跟进问答：{'是' if answer.trace.is_follow_up else '否'}")
                if answer.trace.context_terms:
                    print(f"上下文术语：{', '.join(answer.trace.context_terms)}")
                print(f"改写查询：{answer.trace.rewritten_query}")
                if answer.trace.rerank_provider != "none":
                    print(
                        "重排配置："
                        f"{answer.trace.rerank_provider} "
                        f"({answer.trace.rerank_model}) "
                        f"candidate_k={answer.trace.rerank_candidate_k}"
                    )
                print(
                    "耗时："
                    f"total={answer.trace.latency_ms:.1f}ms "
                    f"retrieval={answer.trace.retrieval_latency_ms:.1f}ms "
                    f"generation={answer.trace.generation_latency_ms:.1f}ms"
                )
                print(
                    "阶段耗时："
                    f"context={answer.trace.context_latency_ms:.1f}ms "
                    f"intent={answer.trace.intent_latency_ms:.1f}ms "
                    f"rewrite={answer.trace.rewrite_latency_ms:.1f}ms "
                    f"embedding={answer.trace.embedding_latency_ms:.1f}ms "
                    f"vector={answer.trace.vector_search_latency_ms:.1f}ms "
                    f"rerank={answer.trace.rerank_latency_ms:.1f}ms"
                )
                print(
                    "重排状态："
                    f"{'已执行' if answer.trace.rerank_applied else '未执行'}"
                    f"（{answer.trace.rerank_skip_reason or '无跳过原因'}）"
                )
                if answer.trace.degradation_reason:
                    print(f"降级原因：{answer.trace.degradation_reason}")
            print(answer.answer)
            if answer.sources:
                print("\n来源：")
                for index, result in enumerate(answer.sources, start=1):
                    source = result.chunk.metadata.get("source", "unknown")
                    semantic = _format_optional_score(result.semantic_score)
                    bm25 = _format_optional_score(result.normalized_bm25_score)
                    retrieval = _format_optional_score(result.retrieval_score)
                    rerank = _format_optional_score(result.rerank_score)
                    print(
                        f"[{index}] score={result.score:.3f} "
                        f"retrieval={retrieval} rerank={rerank} "
                        f"semantic={semantic} bm25={bm25} source={source}"
                    )
            if args.show_context and answer.trace is not None:
                print("\n增强上下文：")
                print(answer.trace.augmented_context)
        return 0

    if args.command == "evaluate-retrieval":
        settings = Settings.from_env()
        cases = load_retrieval_eval_cases(args.dataset)
        report = compare_rerank_runs(
            settings=settings,
            cases=cases,
            top_k=args.top_k,
            with_rerank_provider=args.with_rerank_provider,
            with_rerank_model=args.with_rerank_model,
            dataset_path=str(args.dataset),
        )
        baseline_report = (
            load_evaluation_report(args.baseline)
            if args.baseline is not None and args.baseline.exists()
            else None
        )
        report["release_gate"] = evaluate_release_gate(
            report,
            thresholds=_build_eval_thresholds(args),
            baseline_report=baseline_report,
        )
        report_path = None
        if not args.no_save:
            report_path = save_evaluation_report(
                report,
                reports_dir=args.reports_dir,
                output_path=args.output,
            )
            report["report_path"] = str(report_path)
            save_evaluation_report(
                report,
                reports_dir=args.reports_dir,
                output_path=report_path,
            )
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(
                f"检索评测完成：样本 {report['cases']} 条，top_k={report['top_k']}。"
            )
            for run in report["runs"]:
                print(
                    f"[{run['name']}] provider={run['rerank_provider']} "
                    f"hit@k={run['hit_at_k']:.3f} mrr={run['mrr']:.3f} "
                    f"no_result={run['no_result_rate']:.3f} "
                    f"avg={run['avg_latency_ms']:.1f}ms p95={run['p95_latency_ms']:.1f}ms"
                )
                if args.show_failures and run["failures"]:
                    print(f"  未命中样本：{len(run['failures'])}")
                    for failure in run["failures"]:
                        print(f"  - query={failure['query']}")
                        for result in failure["top_results"]:
                            print(
                                "    "
                                f"source={result['source']} "
                                f"section={result['section_title']} "
                                f"score={result['score']}"
                            )
            delta = report["delta"]
            print(
                "差异（with_rerank - no_rerank）："
                f" hit@k={delta['hit_at_k']:+.3f},"
                f" mrr={delta['mrr']:+.3f},"
                f" no_result_rate={delta['no_result_rate']:+.3f},"
                f" avg_latency_ms={delta['avg_latency_ms']:+.1f},"
                f" p95_latency_ms={delta['p95_latency_ms']:+.1f}"
            )
            if baseline_report is None and args.baseline is not None:
                print(f"基线报告：未找到 {args.baseline}，本次只执行绝对指标门禁。")
            gate = report["release_gate"]
            print(f"发布门禁：{'通过' if gate['passed'] else '失败'}")
            failed_checks = [
                check
                for check in gate["checks"]
                if not check["passed"]
            ]
            for check in failed_checks:
                print(
                    "- "
                    f"{check['name']} 未通过："
                    f"value={check['value']} "
                    f"{check['operator']} {check['threshold']}"
                )
            if report_path is not None:
                print(f"评测报告：{report_path}")
        if args.fail_on_gate and not report["release_gate"]["passed"]:
            return 1
        return 0

    if args.command == "query-logs":
        settings = Settings.from_env()
        store = create_query_log_store(settings)
        items = store.tail(limit=args.limit)
        if args.json:
            print(json.dumps({"items": items}, ensure_ascii=False, indent=2))
        else:
            print(f"最近查询日志：{len(items)} 条")
            for item in items:
                print(
                    f"- {item.get('created_at')} "
                    f"request_id={item.get('request_id')} "
                    f"intent={item.get('intent_label')} "
                    f"status={item.get('status')} "
                    f"latency={item.get('latency_ms')}ms "
                    f"question={item.get('question')}"
                )
        return 0

    if args.command == "feedback":
        settings = Settings.from_env()
        store = create_feedback_store(settings)
        record = build_feedback_record(
            request_id=args.request_id,
            session_id=args.session_id,
            question=args.question,
            rating=args.rating,
            useful=_parse_optional_bool(args.useful),
            comment=args.comment,
            expected_answer=args.expected_answer,
            labels=args.label,
        )
        store.append(record)
        payload = asdict(record)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"反馈已记录：{record.feedback_id}")
            print(f"请求ID：{record.request_id}")
            if record.rating is not None:
                print(f"评分：{record.rating}")
            if record.useful is not None:
                print(f"是否有用：{'是' if record.useful else '否'}")
        return 0

    if args.command == "ops-summary":
        settings = Settings.from_env()
        query_store = create_query_log_store(settings)
        feedback_store = create_feedback_store(settings)
        payload = {
            "query_logs": query_store.summary(limit=args.limit),
            "feedback": feedback_store.summary(limit=args.limit),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            query_summary = payload["query_logs"]
            feedback_summary = payload["feedback"]
            print("查询日志摘要：")
            print(
                f"- total={query_summary['total']} "
                f"answered={query_summary['success']} "
                f"no_context={query_summary['no_context']} "
                f"avg_latency={query_summary['avg_latency_ms']}ms"
            )
            print(f"- intent_counts={query_summary['intent_counts']}")
            print("反馈摘要：")
            print(
                f"- total={feedback_summary['total']} "
                f"useful={feedback_summary['useful']} "
                f"not_useful={feedback_summary['not_useful']} "
                f"avg_rating={feedback_summary['avg_rating']}"
            )
            print(f"- label_counts={feedback_summary['label_counts']}")
        return 0

    if args.command == "ops-trace":
        settings = Settings.from_env()
        payload = build_request_trace(settings, args.request_id)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"请求ID：{payload['request_id']}")
            if not payload["found"]:
                print("未找到对应的查询日志或反馈。")
                return 1
            query_log = payload.get("query_log")
            if query_log:
                print("查询日志：")
                print(f"- 时间：{query_log.get('created_at')}")
                print(f"- 问题：{query_log.get('question')}")
                print(f"- 意图：{query_log.get('intent_label')}")
                print(f"- 状态：{query_log.get('status')}")
                print(f"- 耗时：{query_log.get('latency_ms')}ms")
                print(f"- 召回数量：{query_log.get('source_count')}")
            feedback_items = payload.get("feedback") or []
            print(f"反馈记录：{len(feedback_items)} 条")
            for item in feedback_items:
                print(
                    f"- rating={item.get('rating')} useful={item.get('useful')} "
                    f"labels={item.get('labels')} comment={item.get('comment')}"
                )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _answer_to_dict(answer) -> dict:
    payload = asdict(answer)
    for source in payload["sources"]:
        source["score"] = round(source["score"], 6)
    return payload


def _format_optional_score(score: float | None) -> str:
    if score is None:
        return "-"
    return f"{score:.3f}"


def _parse_optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "true"


def _build_eval_thresholds(args) -> EvaluationThresholds:
    return EvaluationThresholds(
        min_hit_at_k=args.min_hit_at_k,
        min_mrr=args.min_mrr,
        max_no_result_rate=args.max_no_result_rate,
        max_avg_latency_ms=args.max_avg_latency_ms,
        max_p95_latency_ms=args.max_p95_latency_ms,
        max_hit_at_k_drop=args.max_hit_at_k_drop,
        max_mrr_drop=args.max_mrr_drop,
        max_no_result_rate_increase=args.max_no_result_rate_increase,
        max_avg_latency_increase_ms=args.max_avg_latency_increase_ms,
        max_p95_latency_increase_ms=args.max_p95_latency_increase_ms,
    )


if __name__ == "__main__":
    raise SystemExit(main())
