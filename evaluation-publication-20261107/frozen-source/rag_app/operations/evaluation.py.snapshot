"""检索评测、基线对比和发布门禁。"""

from __future__ import annotations

import json
import math
import statistics
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rag_app.core.config import Settings
from rag_app.retrieval.online import OnlineQueryProcessor


@dataclass(frozen=True)
class ExpectedTarget:
    """一条查询可命中的正确目标。"""

    source: str | None = None
    section_title: str | None = None
    text_contains: str | None = None


@dataclass(frozen=True)
class RetrievalEvalCase:
    """单条检索评测样本。"""

    query: str
    expected: list[ExpectedTarget]
    note: str | None = None
    intent_label: str | None = None
    business_module: str | None = None
    source_type: str | None = None
    tags: list[str] | None = None


@dataclass(frozen=True)
class EvaluationThresholds:
    """发布门禁阈值。"""

    min_hit_at_k: float = 0.8
    min_mrr: float = 0.7
    max_no_result_rate: float = 0.2
    max_avg_latency_ms: float | None = None
    max_p95_latency_ms: float | None = None
    max_hit_at_k_drop: float = 0.05
    max_mrr_drop: float = 0.05
    max_no_result_rate_increase: float = 0.05
    max_avg_latency_increase_ms: float | None = None
    max_p95_latency_increase_ms: float | None = None


def load_retrieval_eval_cases(path: Path) -> list[RetrievalEvalCase]:
    """加载 JSONL 检索评测样本。"""

    cases: list[RetrievalEvalCase] = []
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"评测文件第 {line_number} 行不是合法 JSON。") from exc
            cases.append(_case_from_payload(payload, line_number))
    if not cases:
        raise ValueError("评测集为空，请先提供至少一条样本。")
    return cases


def load_evaluation_report(path: Path) -> dict[str, Any]:
    """读取历史评测报告。"""

    return json.loads(path.read_text(encoding="utf-8"))


def save_evaluation_report(
    report: dict[str, Any],
    reports_dir: Path,
    output_path: Path | None = None,
) -> Path:
    """保存评测报告，并返回实际文件路径。"""

    if output_path is None:
        reports_dir.mkdir(parents=True, exist_ok=True)
        filename = f"retrieval_eval_{_timestamp_for_filename()}.json"
        output_path = reports_dir / filename
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def compare_rerank_runs(
    settings: Settings,
    cases: list[RetrievalEvalCase],
    top_k: int = 3,
    with_rerank_provider: str = "cross-encoder",
    with_rerank_model: str | None = None,
    dataset_path: str | None = None,
) -> dict[str, Any]:
    """对比重排关闭和开启两种配置的检索效果。"""

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    baseline_settings = replace(
        settings,
        rerank_provider="none",
    )
    rerank_settings = replace(
        settings,
        rerank_provider=with_rerank_provider,
        rerank_model=with_rerank_model or settings.rerank_model,
    )
    baseline = _evaluate_once(
        baseline_settings,
        cases=cases,
        top_k=top_k,
        run_name="no_rerank",
    )
    rerank = _evaluate_once(
        rerank_settings,
        cases=cases,
        top_k=top_k,
        run_name="with_rerank",
    )
    return {
        "report_type": "retrieval_evaluation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": dataset_path,
        "cases": len(cases),
        "top_k": top_k,
        "settings": _settings_snapshot(settings),
        "runs": [baseline, rerank],
        "delta": _compare_run_metrics(rerank, baseline),
    }


def evaluate_release_gate(
    report: dict[str, Any],
    thresholds: EvaluationThresholds | None = None,
    baseline_report: dict[str, Any] | None = None,
    candidate_run_name: str = "with_rerank",
) -> dict[str, Any]:
    """根据绝对指标和历史基线判断本次评测是否允许发布。"""

    actual_thresholds = thresholds or EvaluationThresholds()
    candidate = _find_run(report, candidate_run_name)
    if candidate is None:
        candidate = report["runs"][-1]

    checks: list[dict[str, Any]] = []
    checks.append(
        _minimum_check(
            name="min_hit_at_k",
            metric="hit_at_k",
            value=candidate["hit_at_k"],
            threshold=actual_thresholds.min_hit_at_k,
        )
    )
    checks.append(
        _minimum_check(
            name="min_mrr",
            metric="mrr",
            value=candidate["mrr"],
            threshold=actual_thresholds.min_mrr,
        )
    )
    checks.append(
        _maximum_check(
            name="max_no_result_rate",
            metric="no_result_rate",
            value=candidate["no_result_rate"],
            threshold=actual_thresholds.max_no_result_rate,
        )
    )
    checks.append(
        _optional_maximum_check(
            name="max_avg_latency_ms",
            metric="avg_latency_ms",
            value=candidate["avg_latency_ms"],
            threshold=actual_thresholds.max_avg_latency_ms,
        )
    )
    checks.append(
        _optional_maximum_check(
            name="max_p95_latency_ms",
            metric="p95_latency_ms",
            value=candidate["p95_latency_ms"],
            threshold=actual_thresholds.max_p95_latency_ms,
        )
    )

    baseline_delta: dict[str, Any] | None = None
    baseline_run_name: str | None = None
    if baseline_report is not None:
        baseline_run = (
            _find_run(baseline_report, candidate["name"])
            or _find_run(baseline_report, candidate_run_name)
            or baseline_report["runs"][-1]
        )
        baseline_run_name = baseline_run["name"]
        baseline_delta = _compare_run_metrics(candidate, baseline_run)
        checks.extend(
            [
                _drop_check(
                    name="max_hit_at_k_drop",
                    metric="hit_at_k",
                    delta=baseline_delta["hit_at_k"],
                    allowed_drop=actual_thresholds.max_hit_at_k_drop,
                ),
                _drop_check(
                    name="max_mrr_drop",
                    metric="mrr",
                    delta=baseline_delta["mrr"],
                    allowed_drop=actual_thresholds.max_mrr_drop,
                ),
                _increase_check(
                    name="max_no_result_rate_increase",
                    metric="no_result_rate",
                    delta=baseline_delta["no_result_rate"],
                    allowed_increase=actual_thresholds.max_no_result_rate_increase,
                ),
                _optional_increase_check(
                    name="max_avg_latency_increase_ms",
                    metric="avg_latency_ms",
                    delta=baseline_delta["avg_latency_ms"],
                    allowed_increase=actual_thresholds.max_avg_latency_increase_ms,
                ),
                _optional_increase_check(
                    name="max_p95_latency_increase_ms",
                    metric="p95_latency_ms",
                    delta=baseline_delta["p95_latency_ms"],
                    allowed_increase=actual_thresholds.max_p95_latency_increase_ms,
                ),
            ]
        )

    passed = all(check["passed"] for check in checks)
    return {
        "passed": passed,
        "candidate_run": candidate["name"],
        "baseline_run": baseline_run_name,
        "thresholds": asdict(actual_thresholds),
        "checks": checks,
        "baseline_delta": baseline_delta,
    }


def _evaluate_once( #单次评估执行函数
    settings: Settings,
    cases: list[RetrievalEvalCase],
    top_k: int,
    run_name: str,
) -> dict[str, Any]:
    processor = OnlineQueryProcessor(settings=settings)
    case_results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for case in cases:
        start_time = time.perf_counter()
        answer = processor.process(case.query, top_k=top_k)
        latency_ms = (time.perf_counter() - start_time) * 1000

        rank = _first_match_rank(answer.sources, case.expected)
        hit = rank is not None
        case_result = {
            "query": case.query,
            "note": case.note,
            "intent_label": case.intent_label,
            "business_module": case.business_module,
            "source_type": case.source_type,
            "tags": case.tags or [],
            "hit": hit,
            "rank": rank,
            "reciprocal_rank": round(1.0 / rank, 6) if rank is not None else 0.0,
            "no_result": len(answer.sources) == 0,
            "latency_ms": round(latency_ms, 3),
            "expected": [_target_to_dict(target) for target in case.expected],
            "top_results": [
                {
                    "source": result.chunk.metadata.get("source"),
                    "section_title": result.chunk.metadata.get("section_title"),
                    "score": round(result.score, 6),
                    "retrieval_score": _optional_round(result.retrieval_score),
                    "rerank_score": _optional_round(result.rerank_score),
                    "semantic_score": _optional_round(result.semantic_score),
                    "bm25_score": _optional_round(result.bm25_score),
                }
                for result in answer.sources
            ],
        }
        case_results.append(case_result)

        if hit:
            continue

        failures.append(
            {
                "query": case.query,
                "note": case.note,
                "intent_label": case.intent_label,
                "business_module": case.business_module,
                "source_type": case.source_type,
                "expected": case_result["expected"],
                "top_results": case_result["top_results"],
            }
        )

    metrics = _summarize_case_results(case_results)
    return {
        "name": run_name,
        "rerank_provider": settings.rerank_provider,
        "rerank_model": settings.rerank_model if settings.rerank_provider != "none" else "none",
        **metrics,
        "bucket_metrics": _bucket_metrics(case_results),
        "failures": failures,
        "case_results": case_results,
    }


def _summarize_case_results(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    case_count = len(case_results)
    hit_count = sum(1 for result in case_results if result["hit"])
    no_result_count = sum(1 for result in case_results if result["no_result"])
    reciprocal_rank_sum = sum(float(result["reciprocal_rank"]) for result in case_results)
    latencies_ms = [float(result["latency_ms"]) for result in case_results]

    if case_count <= 0:
        return {
            "case_count": 0,
            "hit_at_k": 0.0,
            "mrr": 0.0,
            "no_result_rate": 0.0,
            "avg_latency_ms": 0.0,
            "median_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "failure_count": 0,
        }

    return {
        "case_count": case_count,
        "hit_at_k": round(hit_count / case_count, 6),
        "mrr": round(reciprocal_rank_sum / case_count, 6),
        "no_result_rate": round(no_result_count / case_count, 6),
        "avg_latency_ms": round(sum(latencies_ms) / case_count, 3),
        "median_latency_ms": round(statistics.median(latencies_ms), 3),
        "p95_latency_ms": round(_percentile(latencies_ms, 0.95), 3),
        "failure_count": case_count - hit_count,
    }


def _bucket_metrics(case_results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        "intent_label": _group_metrics(case_results, "intent_label"),
        "business_module": _group_metrics(case_results, "business_module"),
        "source_type": _group_metrics(case_results, "source_type"),
    }


def _group_metrics(
    case_results: list[dict[str, Any]],
    field_name: str,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in case_results:
        key = str(item.get(field_name) or "未标注")
        grouped.setdefault(key, []).append(item)
    return {
        key: _summarize_case_results(items)
        for key, items in sorted(grouped.items(), key=lambda pair: pair[0])
    }


def _case_from_payload(payload, line_number: int) -> RetrievalEvalCase:
    if not isinstance(payload, dict):
        raise ValueError(f"评测文件第 {line_number} 行必须是 JSON 对象。")

    query = str(payload.get("query", "")).strip()
    if not query:
        raise ValueError(f"评测文件第 {line_number} 行缺少 query。")

    expected = _parse_expected(payload, line_number)
    if not expected:
        raise ValueError(f"评测文件第 {line_number} 行缺少 expected 目标。")

    return RetrievalEvalCase(
        query=query,
        expected=expected,
        note=_optional_string(payload.get("note")),
        intent_label=_optional_string(payload.get("intent_label")),
        business_module=_optional_string(payload.get("business_module")),
        source_type=_optional_string(payload.get("source_type")),
        tags=_parse_tags(payload.get("tags")),
    )


def _parse_expected(payload: dict, line_number: int) -> list[ExpectedTarget]:
    raw_expected = payload.get("expected")
    if raw_expected is None:
        # 兼容简写格式。
        source = _optional_string(payload.get("expected_source"))
        section_title = _optional_string(payload.get("expected_section_title"))
        text_contains = _optional_string(payload.get("expected_text_contains"))
        if source or section_title or text_contains:
            return [
                ExpectedTarget(
                    source=source,
                    section_title=section_title,
                    text_contains=text_contains,
                )
            ]
        return []

    if not isinstance(raw_expected, list):
        raise ValueError(f"评测文件第 {line_number} 行的 expected 必须是数组。")

    expected: list[ExpectedTarget] = []
    for index, item in enumerate(raw_expected, start=1):
        if not isinstance(item, dict):
            raise ValueError(
                f"评测文件第 {line_number} 行 expected[{index}] 必须是对象。"
            )
        target = ExpectedTarget(
            source=_optional_string(item.get("source")),
            section_title=_optional_string(item.get("section_title")),
            text_contains=_optional_string(item.get("text_contains")),
        )
        if not (target.source or target.section_title or target.text_contains):
            raise ValueError(
                f"评测文件第 {line_number} 行 expected[{index}] 至少要有一个匹配字段。"
            )
        expected.append(target)
    return expected


def _first_match_rank(results, expected: list[ExpectedTarget]) -> int | None:
    for rank, result in enumerate(results, start=1):
        for target in expected:
            if _matches_target(result, target):
                return rank
    return None


def _matches_target(result, target: ExpectedTarget) -> bool:
    source = result.chunk.metadata.get("source")
    section_title = result.chunk.metadata.get("section_title")
    text = result.chunk.text
    if target.source and source != target.source:
        return False
    if target.section_title and section_title != target.section_title:
        return False
    if target.text_contains and target.text_contains not in text:
        return False
    return True


def _target_to_dict(target: ExpectedTarget) -> dict[str, str]:
    payload: dict[str, str] = {}
    if target.source:
        payload["source"] = target.source
    if target.section_title:
        payload["section_title"] = target.section_title
    if target.text_contains:
        payload["text_contains"] = target.text_contains
    return payload


def _parse_tags(value) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _optional_string(value) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _optional_round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    if q <= 0:
        return min(values)
    if q >= 1:
        return max(values)
    sorted_values = sorted(values)
    position = (len(sorted_values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    lower_value = sorted_values[lower]
    upper_value = sorted_values[upper]
    ratio = position - lower
    return lower_value + (upper_value - lower_value) * ratio


def _settings_snapshot(settings: Settings) -> dict[str, Any]:
    return {
        "collection_name": settings.collection_name,
        "embedding_provider": settings.embedding_provider,
        "embedding_dimension": settings.embedding_dimension,
        "vector_store_provider": settings.vector_store_provider,
        "retrieval_mode": settings.retrieval_mode,
        "retrieval_candidate_k": settings.retrieval_candidate_k,
        "semantic_weight": settings.semantic_weight,
        "bm25_weight": settings.bm25_weight,
        "min_similarity_score": settings.min_similarity_score,
        "relative_score_threshold": settings.relative_score_threshold,
        "rerank_candidate_k": settings.rerank_candidate_k,
    }


def _compare_run_metrics(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    return {
        "hit_at_k": round(candidate["hit_at_k"] - baseline["hit_at_k"], 6),
        "mrr": round(candidate["mrr"] - baseline["mrr"], 6),
        "no_result_rate": round(
            candidate["no_result_rate"] - baseline["no_result_rate"],
            6,
        ),
        "avg_latency_ms": round(
            candidate["avg_latency_ms"] - baseline["avg_latency_ms"],
            3,
        ),
        "p95_latency_ms": round(
            candidate["p95_latency_ms"] - baseline["p95_latency_ms"],
            3,
        ),
    }


def _find_run(report: dict[str, Any], run_name: str) -> dict[str, Any] | None:
    for run in report.get("runs", []):
        if run.get("name") == run_name:
            return run
    return None


def _minimum_check(
    name: str,
    metric: str,
    value: float,
    threshold: float,
) -> dict[str, Any]:
    return {
        "name": name,
        "metric": metric,
        "operator": ">=",
        "value": value,
        "threshold": threshold,
        "passed": value >= threshold,
    }


def _maximum_check(
    name: str,
    metric: str,
    value: float,
    threshold: float,
) -> dict[str, Any]:
    return {
        "name": name,
        "metric": metric,
        "operator": "<=",
        "value": value,
        "threshold": threshold,
        "passed": value <= threshold,
    }


def _optional_maximum_check(
    name: str,
    metric: str,
    value: float,
    threshold: float | None,
) -> dict[str, Any]:
    if threshold is None:
        return _skipped_check(name=name, metric=metric, value=value)
    return _maximum_check(name=name, metric=metric, value=value, threshold=threshold)


def _drop_check(
    name: str,
    metric: str,
    delta: float,
    allowed_drop: float,
) -> dict[str, Any]:
    threshold = -abs(allowed_drop)
    return {
        "name": name,
        "metric": metric,
        "operator": ">=",
        "value": delta,
        "threshold": threshold,
        "passed": delta >= threshold,
    }


def _increase_check(
    name: str,
    metric: str,
    delta: float,
    allowed_increase: float,
) -> dict[str, Any]:
    threshold = abs(allowed_increase)
    return {
        "name": name,
        "metric": metric,
        "operator": "<=",
        "value": delta,
        "threshold": threshold,
        "passed": delta <= threshold,
    }


def _optional_increase_check(
    name: str,
    metric: str,
    delta: float,
    allowed_increase: float | None,
) -> dict[str, Any]:
    if allowed_increase is None:
        return _skipped_check(name=name, metric=metric, value=delta)
    return _increase_check(
        name=name,
        metric=metric,
        delta=delta,
        allowed_increase=allowed_increase,
    )


def _skipped_check(name: str, metric: str, value: float) -> dict[str, Any]:
    return {
        "name": name,
        "metric": metric,
        "operator": "skip",
        "value": value,
        "threshold": None,
        "passed": True,
        "skipped": True,
    }


def _timestamp_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
