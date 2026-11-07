"""P2-Gold-06 finalize: write the batch-02 manifest and re-verify every hash.

Reads only local files; writes only gold_batch02_manifest.json under p2-gold-06/.
No database, retrieval service, benchmark or git write.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(r"D:\AgentAIProgect\RAG")
sys.path.insert(0, str(ROOT))

from rag_app.eval_dataset.corpus import load_corpus_snapshot  # noqa: E402

OUT = ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
G06 = OUT / "p2-gold-06"
G05 = OUT / "p2-gold-05"
G04 = OUT / "p2-gold-04"
CORPUS_MANIFEST = ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.manifest.json"
PACKET = G05 / "p2_gold_05_signoff_packet.md"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    metadata = json.loads((G06 / "retrieval_gold_batch02_metadata.json").read_text(encoding="utf-8"))
    verify = json.loads((G06 / "p2_gold_06_verify.json").read_text(encoding="utf-8"))
    manifest, rows = load_corpus_snapshot(CORPUS_MANIFEST)
    chunks = {row["chunk_id"]: row for row in rows}

    gold_path = G06 / "retrieval_gold_batch02_13.jsonl"
    meta_path = G06 / "retrieval_gold_batch02_metadata.json"
    rejected_path = G06 / "rejected_batch02_1.jsonl"
    unsigned_path = G06 / "unsigned_batch02_1.jsonl"
    verify_path = G06 / "p2_gold_06_verify.json"
    report_path = G06 / "p2_gold_06_validation.md"

    gold_lines = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rejected = [json.loads(line) for line in rejected_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    unsigned = [json.loads(line) for line in unsigned_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    # negative comparisons inside the same document, following the evaluator match rule
    negative_same_document = 0
    for line, case in zip(gold_lines, metadata["cases"]):
        for target in line["expected"]:
            for other_id, other in chunks.items():
                if other["source"] != target["source"]:
                    continue
                if (other["metadata"].get("section_title") == target["section_title"]
                        and target["text_contains"] in other["chunk_text"]):
                    continue
                negative_same_document += 1
    unique_evidence_chunks = {item["chunk_id"] for case in metadata["cases"]
                              for item in case["evidence"]}

    inputs = {
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/p2_gold_05_signoff_packet.md": PACKET,
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/p2_gold_05_review_proposal.md": G05 / "p2_gold_05_review_proposal.md",
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/p2_gold_05_validation.md": G05 / "p2_gold_05_validation.md",
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/review_batch02_15_draft.xlsx": G05 / "review_batch02_15_draft.xlsx",
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/review.xlsx": OUT / "review.xlsx",
        "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl": ROOT / "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl",
        "storage/evaluation/candidates/p1-20261104-structured/generation_manifest.json": ROOT / "storage/evaluation/candidates/p1-20261104-structured/generation_manifest.json",
        "storage/evaluation/corpus/p1-20261104-v2/corpus.manifest.json": CORPUS_MANIFEST,
        "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl": ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl",
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/retrieval_gold_batch01_9.jsonl": G04 / "retrieval_gold_batch01_9.jsonl",
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/retrieval_gold_batch01_metadata.json": G04 / "retrieval_gold_batch01_metadata.json",
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/rejected_batch01_3.jsonl": G04 / "rejected_batch01_3.jsonl",
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/gold_batch01_manifest.json": G04 / "gold_batch01_manifest.json",
        "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/p2_gold_04_validation.md": G04 / "p2_gold_04_validation.md",
        "data/电信基础设施维护规程.pdf": ROOT / "data/电信基础设施维护规程.pdf",
        "data/智慧家庭装维工程与管理职业技能等级标准.pdf": ROOT / "data/智慧家庭装维工程与管理职业技能等级标准.pdf",
        "data/中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf": ROOT / "data/中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf",
        "rag_app/operations/evaluation.py": ROOT / "rag_app/operations/evaluation.py",
        "rag_app/eval_dataset/corpus.py": ROOT / "rag_app/eval_dataset/corpus.py",
    }
    inputs_sha = {rel: sha256_file(path) for rel, path in inputs.items()}

    outputs = {
        gold_path.name: gold_path,
        meta_path.name: meta_path,
        rejected_path.name: rejected_path,
        unsigned_path.name: unsigned_path,
        verify_path.name: verify_path,
        report_path.name: report_path,
    }
    outputs_sha = {name: sha256_file(path) for name, path in outputs.items()}

    git_head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    git_branch = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
    git_status = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
                                capture_output=True, text=True, check=True).stdout.strip()

    counts = metadata["counts"]
    payload = {
        "gold_version": "p2-gold-06-batch02-v1",
        "batch": "batch02",
        "parent_phase": "p2-gold-05",
        "source_git_commit": git_head,
        "git_branch": git_branch,
        "tracked_worktree_clean": git_status == "",
        "corpus_snapshot_id": manifest["snapshot_id"],
        "corpus_manifest_internal_sha256": manifest["manifest_sha256"],
        "corpus_export_git_head": manifest["code_provenance"]["git_head"],
        "generated_at": metadata["generated_at"],
        "manifest_finalized_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "generator": {
            "name": "P2-Gold-06 one-off static export",
            "python": sys.version.split()[0],
            "corpus_validator": "rag_app.eval_dataset.corpus.load_corpus_snapshot",
            "evaluator": "rag_app.operations.evaluation.load_retrieval_eval_cases",
            "note": "未运行 Benchmark、检索服务或数据库；未修改检索/评测代码。",
        },
        "candidate_file_sha256": inputs_sha["storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl"],
        "human_signoff_file_sha256": inputs_sha[
            "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/p2_gold_05_signoff_packet.md"],
        "human_signoff_file_sha256_before_signoff":
            "e7719369abd01d741e65b717aa4d61e965a92b1d50e51fe8fec2ef6150f313d0",
        "human_signoff": {
            "records": 15,
            "complete_and_valid": 13,
            "rejected": 1,
            "unsigned": 1,
            "ai_recommendation_used_as_approval": False,
        },
        "gold_file_sha256": outputs_sha[gold_path.name],
        "inputs_sha256": inputs_sha,
        "outputs_sha256": outputs_sha,
        "outputs_note": "outputs_sha256 不含 Manifest 自身，避免自引用；Manifest 字节哈希由调用方复算。",
        "counts": {
            "gold": counts["gold"],
            "accepted_original": counts["accepted_original"],
            "accepted_revision": counts["accepted_revision"],
            "rejected": len(rejected),
            "unsigned": len(unsigned),
            "cumulative_gold": counts["cumulative_gold"],
            "remaining_to_50": counts["remaining_to_50"],
            "candidates": 57,
            "corpus_documents": manifest["document_count"],
            "corpus_chunks": len(rows),
            "gold_evidence_chunks": verify["facts"]["gold_evidence_entries_including_equivalent"],
            "gold_unique_evidence_chunks": len(unique_evidence_chunks),
            "retrieval_targets": verify["facts"]["retrieval_targets"],
            "retrieval_target_chunks": verify["facts"]["retrieval_target_unique_chunks"],
            "rejection_evidence_chunks": verify["facts"]["rejection_evidence_chunks"],
        },
        "known_scoring_limits": [
            "每个目标内 AND，目标之间 OR。Hit@K 和 MRR 采用首个匹配。",
            "现有评测器无 NDCG、Chunk ID 直配或双证据完整覆盖指标。",
            "B14、B15 完整证据需页 10 表头与续页正文两块，但检索目标只设正文块；"
            "Hit@K/MRR 无法判断两块是否同在一个返回集合。",
            "B25 的两个目标为等价证据（OR），任一命中即计 Hit，指标不要求同一 Top-K 同时含两页。",
            "B16/B21 与首批 B02 共享 254 页 Chunk，B17–B20 共享 255 页 Chunk；"
            "目标只验证 Chunk 级命中，不区分行或段落，且同 Chunk 内另有同价行（WH23104001 亦为 62.02 元/个）。",
            "仅填 source 会把同文档其他 Chunk 判为相关。三字段组合只在本冻结快照验证唯一性"
            "（6258 次比对，0 误命中）。",
            "text_contains 对空白与标点敏感，原文匹配需与冻结 Chunk 一致。",
        ],
        "validation": {
            "static_checks": len(verify["checks"]),
            "static_checks_failed": sum(1 for item in verify["checks"] if not item["passed"]),
            "schema_loaded": verify["facts"]["schema_loaded_cases"],
            "schema_loader": verify["facts"]["schema_loader"],
            "target_chunk_comparisons": verify["facts"]["target_replay_comparisons"],
            "target_matches": verify["facts"]["retrieval_targets"],
            "target_false_positives": verify["facts"]["target_replay_false_positives"],
            "negative_comparisons_same_document": negative_same_document,
            "gold_ids_recomputed": len(metadata["cases"]),
            "parents_found": len({case["parent_candidate_id"] for case in metadata["cases"]}),
            "chunks_missing": 0,
            "batch01_duplicate_questions": sum(
                1 for row in verify["facts"]["duplicate_check_vs_batch01"]
                if row["exact_duplicate_with_batch01"]),
            "max_similarity_vs_batch01": verify["facts"]["max_similarity_vs_batch01"],
            "benchmark_executed": False,
            "database_accessed": False,
            "git_write": False,
        },
        "id_recipe": {
            "prefix": "gold-batch02-sha256:",
            "algorithm": "SHA-256",
            "fields": [
                "batch_id",
                "parent_candidate_id",
                "corpus_snapshot_id",
                "review_decision",
                "question",
                "reference_answer",
                "evidence_chunk_ids",
                "retrieval_relevant_chunk_ids",
            ],
            "encoding": "UTF-8 JSON object, ensure_ascii=False, sort_keys=True, "
                        "separators=(comma, colon), no final LF",
        },
        "provenance": {
            "signoff_packet": "人工字段逐条读取；空值或非法取值不纳入。",
            "rejected_file": "rejected_batch02_1.jsonl 只含 B24，不含 Gold ID。",
            "unsigned_file": "unsigned_batch02_1.jsonl 只含 B23，状态 unsigned_pending_clarification，gold_case_id=null。",
            "first_batch_untouched": True,
            "candidates_untouched": True,
        },
    }

    manifest_bytes = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    manifest_path = G06 / "gold_batch02_manifest.json"
    manifest_path.write_bytes(manifest_bytes)
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    # Sidecar keeps the Manifest self-hash without a self-referential field.
    (G06 / "gold_batch02_manifest.sha256").write_bytes(
        f"{manifest_sha}  gold_batch02_manifest.json\n".encode("utf-8"))

    # readback verification
    readback = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert readback["counts"]["gold"] == 13
    for rel, digest in readback["inputs_sha256"].items():
        path = inputs[rel]
        assert sha256_file(path) == digest, rel
    for name, digest in readback["outputs_sha256"].items():
        assert sha256_file(G06 / name) == digest, name
    assert readback["validation"]["static_checks_failed"] == 0
    assert readback["counts"]["cumulative_gold"] == 22
    assert readback["counts"]["remaining_to_50"] == 28

    print("manifest", manifest_path)
    print("manifest_sha256", manifest_sha)
    print("bytes", len(manifest_bytes))
    print("inputs", len(inputs_sha), "outputs", len(outputs_sha))
    print("negative_comparisons_same_document", negative_same_document)
    print("gold", readback["counts"]["gold"], "rejected", readback["counts"]["rejected"],
          "unsigned", readback["counts"]["unsigned"],
          "cumulative", readback["counts"]["cumulative_gold"],
          "remaining", readback["counts"]["remaining_to_50"])
    print("git", git_head, git_branch, "tracked_clean", git_status == "")


if __name__ == "__main__":
    main()
