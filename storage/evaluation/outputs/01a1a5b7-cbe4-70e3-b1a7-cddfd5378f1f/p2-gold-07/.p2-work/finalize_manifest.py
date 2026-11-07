"""P2-Gold-07: build the Manifest and its SHA-256 sidecar, then verify both.

Read-only over frozen inputs. Writes p2_gold_07_manifest.json and
p2_gold_07_manifest.sha256 into the phase directory.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"D:\AgentAIProgect\RAG")
OUT = ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
G07 = OUT / "p2-gold-07"
HERE = G07 / ".p2-work"

TZ = timezone(timedelta(hours=8))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


verify = json.loads((G07 / "p2_gold_07_verify.json").read_text(encoding="utf-8"))
facts = json.loads((HERE / "batch03_facts.json").read_text(encoding="utf-8"))
packet = (G07 / "p2_gold_07_signoff_packet.md").read_text(encoding="utf-8")

INPUTS = [
    "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl",
    "storage/evaluation/candidates/p1-20261104-structured/generation_manifest.json",
    "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl",
    "storage/evaluation/corpus/p1-20261104-v2/corpus.manifest.json",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/review.xlsx",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/review-index.md",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/retrieval_gold_batch01_9.jsonl",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/retrieval_gold_batch01_metadata.json",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/rejected_batch01_3.jsonl",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/gold_batch01_manifest.json",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/p2_gold_04_validation.md",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/p2_gold_05_review_proposal.md",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/p2_gold_05_signoff_packet.md",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/p2_gold_05_validation.md",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/review_batch02_15_draft.xlsx",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06/retrieval_gold_batch02_13.jsonl",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06/retrieval_gold_batch02_metadata.json",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06/rejected_batch02_1.jsonl",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06/unsigned_batch02_1.jsonl",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06/gold_batch02_manifest.json",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06/p2_gold_06_validation.md",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06/p2_gold_06_verify.json",
    "data/电信基础设施维护规程.pdf",
    "data/智慧家庭装维工程与管理职业技能等级标准.pdf",
    "data/中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf",
]

INPUTS = [p for p in INPUTS if (ROOT / p).is_file()]
INPUTS += ["rag_app/operations/evaluation.py", "rag_app/eval_dataset/corpus.py"]
INPUTS = sorted(set(INPUTS))

outputs = {}
for p in sorted(G07.glob("*")):
    if p.is_file() and p.name not in {"p2_gold_07_manifest.json", "p2_gold_07_manifest.sha256"}:
        outputs[p.name] = sha(p)
for p in sorted(HERE.glob("*")):
    if p.is_file():
        outputs[f".p2-work/{p.name}"] = sha(p)

accept = packet.count("review_recommendation: Accept")
revise = packet.count("review_recommendation: Revise")
reject = packet.count("review_recommendation: Reject")
nv = packet.count("review_recommendation: Needs Verification")


def pid_list(value: str) -> list[str]:
    value = value.strip().strip("[]")
    return [p.strip().strip("'\"") for p in re.split(r"[,\s]+", value) if p.strip(" '\"")]


ev_total = 0
ev_unique: set[str] = set()
rel_total = 0
for block in re.findall(r"```text\n(.*?)\n```", packet, re.S):
    kv = {}
    for line in block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            kv[k.strip()] = v.strip()
    ids = pid_list(kv.get("evidence_chunk_ids", ""))
    ev_total += len(ids)
    ev_unique.update(ids)
    rel_total += len(pid_list(kv.get("retrieval_relevant_chunk_ids", "")))

manifest = {
    "gold_version": "p2-gold-07-batch03-review-v1",
    "batch": "batch03",
    "phase": "P2-Gold-07",
    "parent_phase": "P2-Gold-06",
    "deliverable_type": "review_and_signoff_packet_only",
    "source_git_commit": "7810bfb54d43a1e5ffb4b6428bd30c0b4b0161a5",
    "git_branch": "codex/eval-corpus-export-v1",
    "tracked_worktree_clean": True,
    "untracked_files_not_created_by_this_phase": [
        "retrieval_eval_20261103_134741.json（仓库根目录，2026-11-03 生成，早于本轮）",
        "一个以 \"-files\" 开头的乱码文件（疑为既有 shell 误建，仓库根目录）",
    ],
    "corpus_snapshot_id": "sha256:eedd1783956ca582c1cdfbbdad486fdf1554c7dab79681bba0675eec47089fce",
    "corpus_manifest_internal_sha256": "0ddcdfe183ab387767065dcf029dd31ba5cdf0088ee9dc7e3501254d72223827",
    "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
    "generator": {
        "name": "P2-Gold-07 one-off static review",
        "python": "3.12.14",
        "corpus_validator": "rag_app.eval_dataset.corpus.load_corpus_snapshot",
        "evaluator": "rag_app.operations.evaluation.load_retrieval_eval_cases",
        "pdf_text": "PyMuPDF 1.27.2.3 (fitz), text layer + word coordinates",
        "note": "未运行 Benchmark、检索服务或数据库；未修改候选、语料、PDF 或既有 Gold。",
    },
    "candidate_file_sha256": sha(ROOT / "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl"),
    "corpus_file_sha256": sha(ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl"),
    "gold_exported_this_phase": 0,
    "cumulative_gold": 22,
    "remaining_to_50": 28,
    "human_signoff": {
        "records": 15,
        "signed": 0,
        "unsigned": 15,
        "ai_recommendation_used_as_approval": False,
        "fields_must_stay_empty_until_human_review": [
            "human_decision", "human_reviewer", "human_reviewed_at", "human_comment",
        ],
    },
    "ai_review": {
        "accept": accept,
        "revise": revise,
        "reject": reject,
        "needs_verification": nv,
        "total": accept + revise + reject + nv,
    },
    "counts": {
        "candidates_in_batch": 15,
        "candidates_total_frozen": 57,
        "corpus_documents": 3,
        "corpus_chunks": 447,
        "evidence_chunk_references": ev_total,
        "evidence_chunks_unique": len(ev_unique),
        "retrieval_targets": rel_total,
        "batch01_gold": 9,
        "batch02_gold": 13,
        "batch02_unsigned": 1,
        "batch02_rejected": 1,
    },
    "b23_status": {
        "batch_id": "B23",
        "candidate_id": "sha256:0f3b338e277722ef4de67a59096d7e8c931138eb05c300808fc9d2ea9a186468",
        "state": "unsigned_pending_clarification",
        "counted_in_gold": False,
        "human_fields_filled_by_this_phase": False,
        "recommended_decision_not_recorded": "接受修订（待人工确认，见 p2_gold_07_b23_recheck.md）",
    },
    "reviewer_field_audit": {
        "b27_human_reviewer": "systemsystem",
        "other_batch02": "system",
        "batch01": "system",
        "workbooks": "review.xlsx 与 review_batch02_15_draft.xlsx 的审核人列均为字面量 human（模板占位）",
        "real_identity_confirmed": False,
        "files_modified_this_phase": [],
    },
    "known_scoring_limits": [
        "每个目标内 AND，目标之间 OR。Hit@K 和 MRR 采用首个匹配。",
        "现有评测器无 NDCG、Chunk ID 直配或双证据完整覆盖指标。",
        "B38 需两块完整覆盖，但目标之间为 OR，无法验证「同时命中」。",
        "B32（物理页 2→7）、B33（2→8）、B35（3→15）的修订改变检索目标页。",
        "B28／B29／B36／B37 的答案数值在语料中重复出现，判定必须依赖表名＋行名＋列名，不能只用数值串。",
        "B29 同页 WH23130003 与 WH23130002 同为 18.24，数值本身对行不具区分性。",
        "物理页 19 承载 B04（已入库）＋B36＋B37；物理页 286、287 各承载两题，同页集中会重复计分。",
        "仅填 source 会把同文档其他 Chunk 判为相关；三字段组合只在本次冻结快照下验证过。",
        "text_contains 对空白与标点敏感，原文匹配需与冻结 Chunk 一致。",
    ],
    "inputs_sha256": {p: sha(ROOT / p) for p in INPUTS},
    "outputs_sha256": outputs,
    "outputs_note": "outputs_sha256 不含 Manifest 自身与 .sha256 sidecar，避免自引用。",
    "validation": {
        "static_checks": verify["summary"]["checks_total"],
        "static_checks_failed": verify["summary"]["checks_failed"],
        "validator": ".p2-work/static_check.py",
        "verify_file": "p2_gold_07_verify.json",
        "benchmark_executed": False,
        "database_accessed": False,
        "git_write": False,
        "retrieval_model_called": False,
    },
    "provenance": {
        "candidates_untouched": True,
        "corpus_untouched": True,
        "pdf_untouched": True,
        "batch01_untouched": True,
        "batch02_untouched": True,
        "signoff_packet_generated_from_frozen_inputs": True,
        "human_fields_empty": True,
    },
}

mpath = G07 / "p2_gold_07_manifest.json"
mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
digest = sha(mpath)
(G07 / "p2_gold_07_manifest.sha256").write_text(f"{digest}  p2_gold_07_manifest.json\n",
                                                encoding="utf-8")

# ---- verify
assert (G07 / "p2_gold_07_manifest.sha256").read_text(encoding="utf-8").split()[0] == sha(mpath)
for name, d in manifest["outputs_sha256"].items():
    assert sha(G07 / name) == d, name
for path, d in manifest["inputs_sha256"].items():
    assert sha(ROOT / path) == d, path
print("manifest_sha256", digest)
print("inputs", len(manifest["inputs_sha256"]), "outputs", len(manifest["outputs_sha256"]))
print("ai_review", manifest["ai_review"])
print("static_checks", manifest["validation"]["static_checks"],
      "failed", manifest["validation"]["static_checks_failed"])
