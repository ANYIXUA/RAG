#!/usr/bin/env python
"""比较两次 P3-Pilot-01 运行，检查检索排序与指标是否可复现。

只比较与时间无关的量：排序后的 Chunk ID 序列、四舍五入后的分数、以及各项指标。
耗时天然抖动，单独比较量级而不做相等断言。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

RANKING_FIELDS = ("chunk_id", "score", "semantic_score", "bm25_score", "normalized_bm25_score", "rerank_score")


def load_rankings(run_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    with (run_dir / "rankings.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            rows[(record["method"], record["gold_case_id"])] = record
    return rows


def canonical_digest(rows: dict[tuple[str, str], dict[str, Any]]) -> str:
    payload = []
    for key in sorted(rows):
        record = rows[key]
        payload.append(
            {
                "method": key[0],
                "gold_case_id": key[1],
                "ranked": [
                    {field: item[field] for field in RANKING_FIELDS}
                    for item in record["results"]
                ],
            }
        )
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def compare(a: Path, b: Path) -> dict[str, Any]:
    rows_a = load_rankings(a)
    rows_b = load_rankings(b)
    metrics_a = json.loads((a / "metrics.json").read_text(encoding="utf-8"))
    metrics_b = json.loads((b / "metrics.json").read_text(encoding="utf-8"))

    only_a = sorted(set(rows_a) - set(rows_b))
    only_b = sorted(set(rows_b) - set(rows_a))
    differing: list[dict[str, Any]] = []
    for key in sorted(set(rows_a) & set(rows_b)):
        ra, rb = rows_a[key], rows_b[key]
        if ra["ranked_chunk_ids"] != rb["ranked_chunk_ids"]:
            differing.append(
                {
                    "method": key[0],
                    "gold_case_id": key[1],
                    "batch_id": ra["batch_id"],
                    "ranked_run_a": ra["ranked_chunk_ids"],
                    "ranked_run_b": rb["ranked_chunk_ids"],
                }
            )
            continue
        scores_a = [(item["chunk_id"], item["score"]) for item in ra["results"]]
        scores_b = [(item["chunk_id"], item["score"]) for item in rb["results"]]
        if scores_a != scores_b:
            differing.append(
                {
                    "method": key[0],
                    "gold_case_id": key[1],
                    "batch_id": ra["batch_id"],
                    "score_mismatch": [
                        {"chunk_id": x[0], "run_a": x[1], "run_b": y[1]}
                        for x, y in zip(scores_a, scores_b)
                        if x != y
                    ],
                }
            )

    def metric_block(name: str) -> dict[str, Any]:
        ma = metrics_a.get("metrics", {}).get(name, {})
        mb = metrics_b.get("metrics", {}).get(name, {})
        keys = [k for k in ma if k not in {"latency_p50_ms", "latency_p95_ms", "latency_mean_ms"}]
        diffs = {k: {"run_a": ma.get(k), "run_b": mb.get(k)} for k in keys if ma.get(k) != mb.get(k)}
        return {
            "method": name,
            "identical": not diffs,
            "differences": diffs,
            "latency_run_a": [ma.get("latency_p50_ms"), ma.get("latency_p95_ms")],
            "latency_run_b": [mb.get("latency_p50_ms"), mb.get("latency_p95_ms")],
        }

    methods = sorted(metrics_a.get("metrics", {}))
    report = {
        "run_a": str(a),
        "run_b": str(b),
        "records_run_a": len(rows_a),
        "records_run_b": len(rows_b),
        "missing_in_b": only_a,
        "missing_in_a": only_b,
        "canonical_digest_run_a": canonical_digest(rows_a),
        "canonical_digest_run_b": canonical_digest(rows_b),
        "rankings_identical": canonical_digest(rows_a) == canonical_digest(rows_b),
        "differing_records": differing,
        "differing_record_count": len(differing),
        "metric_blocks": [metric_block(name) for name in methods],
        "metrics_identical_excluding_latency": all(
            block["identical"] for block in [metric_block(name) for name in methods]
        ),
        "gold_case_ids_match": sorted({r["gold_case_id"] for r in rows_a.values()})
        == sorted({r["gold_case_id"] for r in rows_b.values()}),
        "corpus_sha256_run_a": metrics_a.get("corpus_sha256"),
        "corpus_sha256_run_b": metrics_b.get("corpus_sha256"),
    }
    preflight_a = json.loads((a / "preflight.json").read_text(encoding="utf-8"))
    preflight_b = json.loads((b / "preflight.json").read_text(encoding="utf-8"))
    report["corpus_hash_match"] = (
        preflight_a["corpus"]["sha256"] == preflight_b["corpus"]["sha256"]
    )
    report["gold_sources_hash_match"] = (
        preflight_a["gold"]["sources"] == preflight_b["gold"]["sources"]
    )
    report["config_fingerprint_run_a"] = json.loads(
        (a / "run_config.json").read_text(encoding="utf-8")
    )["environment"]["config_fingerprint"]
    report["config_fingerprint_run_b"] = json.loads(
        (b / "run_config.json").read_text(encoding="utf-8")
    )["environment"]["config_fingerprint"]
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-a", required=True)
    parser.add_argument("--run-b", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    report = compare(Path(args.run_a), Path(args.run_b))
    Path(args.out).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "rankings_identical": report["rankings_identical"],
                "differing_record_count": report["differing_record_count"],
                "metrics_identical_excluding_latency": report[
                    "metrics_identical_excluding_latency"
                ],
                "corpus_hash_match": report["corpus_hash_match"],
                "gold_sources_hash_match": report["gold_sources_hash_match"],
                "digest_a": report["canonical_digest_run_a"],
                "digest_b": report["canonical_digest_run_b"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["rankings_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
