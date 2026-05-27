"""RAG 本地压测脚本，支持 API 和 CLI 两种模式。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


DEFAULT_QUESTION = "光猫红灯咋办"


@dataclass(frozen=True)
class RequestResult:
    """单次请求的压测结果。"""

    index: int
    question: str
    ok: bool
    latency_ms: float
    mode: str
    status_code: int | None = None
    request_id: str | None = None
    intent_label: str | None = None
    source_count: int = 0
    first_source: str | None = None
    error: str | None = None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    questions = load_questions(args)
    if args.requests <= 0:
        raise ValueError("--requests must be greater than 0")
    if args.concurrency <= 0:
        raise ValueError("--concurrency must be greater than 0")
    if args.warmup < 0:
        raise ValueError("--warmup cannot be negative")

    for index in range(args.warmup):
        run_one(
            index=index,
            question=questions[index % len(questions)],
            args=args,
        )

    started_at = datetime.now(timezone.utc)
    start = time.perf_counter()
    results = run_load(questions=questions, args=args)
    duration_ms = (time.perf_counter() - start) * 1000
    report = build_report(
        args=args,
        questions=questions,
        results=results,
        started_at=started_at,
        duration_ms=duration_ms,
    )
    output_path = write_report(report, args.output)
    print_summary(report, output_path)

    if args.fail_on_error_rate is not None and (
        report["summary"]["error_rate"] > args.fail_on_error_rate
    ):
        return 1
    if args.fail_on_p95_ms is not None and (
        report["summary"]["p95_latency_ms"] > args.fail_on_p95_ms
    ):
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RAG load test")
    parser.add_argument(
        "--mode",
        choices=["api", "cli"],
        default="api",
        help="压测模式：api 调用 HTTP 接口，cli 调用命令行查询",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/query",
        help="API 模式下的 /query 地址",
    )
    parser.add_argument(
        "--question",
        action="append",
        default=[],
        help="压测问题，可重复传入多次",
    )
    parser.add_argument(
        "--questions-file",
        type=Path,
        default=None,
        help="问题文件，支持纯文本、JSONL 的 question/query 字段",
    )
    parser.add_argument("--requests", type=int, default=50, help="总请求数")
    parser.add_argument("--concurrency", type=int, default=5, help="并发数")
    parser.add_argument("--warmup", type=int, default=3, help="正式统计前预热次数")
    parser.add_argument("--top-k", type=int, default=2, help="查询 top_k")
    parser.add_argument("--timeout", type=float, default=10.0, help="单请求超时时间")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="报告输出路径；不传时写入 reports/load_test_*.json",
    )
    parser.add_argument(
        "--fail-on-error-rate",
        type=float,
        default=None,
        help="错误率超过该阈值时返回非 0，例如 0.01",
    )
    parser.add_argument(
        "--fail-on-p95-ms",
        type=float,
        default=None,
        help="P95 延迟超过该阈值时返回非 0",
    )
    return parser


def load_questions(args: argparse.Namespace) -> list[str]:
    questions: list[str] = []
    questions.extend(item.strip() for item in args.question if item.strip())
    if args.questions_file is not None:
        questions.extend(_load_questions_file(args.questions_file))
    return questions or [DEFAULT_QUESTION]


def run_load(
    questions: list[str],
    args: argparse.Namespace,
) -> list[RequestResult]:
    results: list[RequestResult] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(
                run_one,
                index=index,
                question=questions[index % len(questions)],
                args=args,
            )
            for index in range(args.requests)
        ]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda item: item.index)


def run_one(
    index: int,
    question: str,
    args: argparse.Namespace,
) -> RequestResult:
    if args.mode == "api":
        return run_api_request(index=index, question=question, args=args)
    return run_cli_request(index=index, question=question, args=args)


def run_api_request(
    index: int,
    question: str,
    args: argparse.Namespace,
) -> RequestResult:
    payload = json.dumps(
        {"question": question, "top_k": args.top_k},
        ensure_ascii=False,
    ).encode("utf-8")
    http_request = request.Request(
        args.url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with request.urlopen(http_request, timeout=args.timeout) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
            latency_ms = (time.perf_counter() - start) * 1000
            return _result_from_payload(
                index=index,
                question=question,
                mode="api",
                latency_ms=latency_ms,
                status_code=response.status,
                payload=data,
            )
    except error.HTTPError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            index=index,
            question=question,
            ok=False,
            latency_ms=round(latency_ms, 3),
            mode="api",
            status_code=exc.code,
            error=str(exc),
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            index=index,
            question=question,
            ok=False,
            latency_ms=round(latency_ms, 3),
            mode="api",
            error=str(exc),
        )


def run_cli_request(
    index: int,
    question: str,
    args: argparse.Namespace,
) -> RequestResult:
    command = [
        sys.executable,
        "-m",
        "rag_app.cli",
        "query",
        question,
        "--top-k",
        str(args.top_k),
        "--json",
    ]
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.timeout,
            check=False,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        if completed.returncode != 0:
            return RequestResult(
                index=index,
                question=question,
                ok=False,
                latency_ms=round(latency_ms, 3),
                mode="cli",
                error=completed.stderr.strip() or completed.stdout.strip(),
            )
        data = json.loads(completed.stdout)
        return _result_from_payload(
            index=index,
            question=question,
            mode="cli",
            latency_ms=latency_ms,
            status_code=None,
            payload=data,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return RequestResult(
            index=index,
            question=question,
            ok=False,
            latency_ms=round(latency_ms, 3),
            mode="cli",
            error=str(exc),
        )


def build_report(
    args: argparse.Namespace,
    questions: list[str],
    results: list[RequestResult],
    started_at: datetime,
    duration_ms: float,
) -> dict:
    successes = [item for item in results if item.ok]
    failures = [item for item in results if not item.ok]
    latencies = [item.latency_ms for item in results]
    success_latencies = [item.latency_ms for item in successes]
    return {
        "report_type": "load_test",
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "mode": args.mode,
        "url": args.url if args.mode == "api" else None,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "warmup": args.warmup,
        "top_k": args.top_k,
        "question_count": len(questions),
        "questions": questions,
        "summary": {
            "total": len(results),
            "success": len(successes),
            "errors": len(failures),
            "error_rate": round(len(failures) / len(results), 6) if results else 0.0,
            "duration_ms": round(duration_ms, 3),
            "throughput_rps": round(len(results) / (duration_ms / 1000), 3)
            if duration_ms > 0
            else 0.0,
            "avg_latency_ms": round(_average(latencies), 3),
            "success_avg_latency_ms": round(_average(success_latencies), 3),
            "min_latency_ms": round(min(latencies), 3) if latencies else 0.0,
            "max_latency_ms": round(max(latencies), 3) if latencies else 0.0,
            "p50_latency_ms": round(percentile(latencies, 0.50), 3),
            "p90_latency_ms": round(percentile(latencies, 0.90), 3),
            "p95_latency_ms": round(percentile(latencies, 0.95), 3),
            "p99_latency_ms": round(percentile(latencies, 0.99), 3),
        },
        "failures": [asdict(item) for item in failures[:20]],
        "results": [asdict(item) for item in results],
    }


def write_report(report: dict, output_path: Path | None) -> Path:
    if output_path is None:
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = reports_dir / f"load_test_{timestamp}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def print_summary(report: dict, output_path: Path) -> None:
    summary = report["summary"]
    print(
        "压测完成："
        f"mode={report['mode']} "
        f"requests={summary['total']} "
        f"concurrency={report['concurrency']} "
        f"errors={summary['errors']} "
        f"error_rate={summary['error_rate']:.4f}"
    )
    print(
        "延迟："
        f"avg={summary['avg_latency_ms']:.1f}ms "
        f"p50={summary['p50_latency_ms']:.1f}ms "
        f"p90={summary['p90_latency_ms']:.1f}ms "
        f"p95={summary['p95_latency_ms']:.1f}ms "
        f"p99={summary['p99_latency_ms']:.1f}ms "
        f"max={summary['max_latency_ms']:.1f}ms"
    )
    print(f"吞吐：{summary['throughput_rps']:.2f} req/s")
    print(f"报告：{output_path}")


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if q <= 0:
        return ordered[0]
    if q >= 1:
        return ordered[-1]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    ratio = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * ratio


def _result_from_payload(
    index: int,
    question: str,
    mode: str,
    latency_ms: float,
    status_code: int | None,
    payload: dict,
) -> RequestResult:
    trace = payload.get("trace") or {}
    sources = payload.get("sources") or []
    first_source = None
    if sources:
        first_source = (
            sources[0]
            .get("chunk", {})
            .get("metadata", {})
            .get("source")
        )
    return RequestResult(
        index=index,
        question=question,
        ok=True,
        latency_ms=round(latency_ms, 3),
        mode=mode,
        status_code=status_code,
        request_id=payload.get("request_id") or trace.get("request_id"),
        intent_label=trace.get("intent_label"),
        source_count=len(sources),
        first_source=first_source,
    )


def _load_questions_file(path: Path) -> list[str]:
    questions: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("{"):
            payload = json.loads(stripped)
            question = str(payload.get("question") or payload.get("query") or "").strip()
            if not question:
                raise ValueError(f"{path} 第 {line_number} 行缺少 question/query")
            questions.append(question)
        else:
            questions.append(stripped)
    return questions


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


if __name__ == "__main__":
    raise SystemExit(main())
