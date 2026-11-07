#!/usr/bin/env python
"""把两批已签核 Gold 合并成一份只读快照，并记录来源哈希。

不做任何内容改写：按字节拼接两个 JSONL 源文件，仅在两段之间补一个换行。
合并结果用于后续 50 题正式 Benchmark 的单一输入，原始 Gold 文件保持不动。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_pilot as rp  # noqa: E402


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    repo = rp.REPO_ROOT
    sources = [
        ("batch01", repo / rp.GOLD_SOURCES["batch01_jsonl"], repo / rp.GOLD_SOURCES["batch01_metadata"]),
        ("batch02", repo / rp.GOLD_SOURCES["batch02_jsonl"], repo / rp.GOLD_SOURCES["batch02_metadata"]),
    ]

    out_dir = repo / "p3-pilot-01" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    merged = b""
    records = []
    for batch_name, jsonl_path, meta_path in sources:
        payload = jsonl_path.read_bytes()
        merged += payload if payload.endswith(b"\n") else payload + b"\n"

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta_by_id = {case["gold_case_id"]: case for case in meta["cases"]}
        for line in payload.decode("utf-8").splitlines():
            if not line.strip():
                continue
            case = json.loads(line)
            gold_id = case["note"]
            meta_case = meta_by_id[gold_id]
            records.append(
                {
                    "batch": batch_name,
                    "batch_id": meta_case["batch_id"],
                    "gold_case_id": gold_id,
                    "query": case["query"],
                    "expected": case["expected"],
                    "relevant_chunk_ids": meta_case["retrieval_relevant_chunk_ids"],
                    "evidence_chunk_ids": meta_case["evidence_chunk_ids"],
                    "requires_all_evidence": meta_case["requires_all_evidence"],
                    "question_type": meta_case["question_type"],
                }
            )

    merged_path = out_dir / "gold_22_merged.jsonl"
    merged_path.write_bytes(merged)

    batch_ids = [record["batch_id"] for record in records]
    excluded = sorted(
        {batch_id for batch_id in batch_ids if batch_id in rp.EXCLUDED_BATCH_IDS}
    )
    provenance = {
        "note": "只读快照；原始 Gold 未被修改，本文件仅按字节拼接两批 JSONL。",
        "merged_file": str(merged_path.relative_to(repo)),
        "merged_sha256": sha256(merged),
        "merged_cases": len(records),
        "batch_ids": batch_ids,
        "excluded_batch_ids_present": excluded,
        "sources": {
            key: {"path": rel, "sha256": sha256((repo / rel).read_bytes())}
            for key, rel in rp.GOLD_SOURCES.items()
        },
        "cases": records,
        "generated_by": "p3-pilot-01/build_gold_bundle.py",
    }
    (out_dir / "gold_provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "merged_cases": len(records),
                "merged_sha256": provenance["merged_sha256"],
                "excluded_batch_ids_present": excluded,
                "merged_file": str(merged_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if excluded or len(records) != 22:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
