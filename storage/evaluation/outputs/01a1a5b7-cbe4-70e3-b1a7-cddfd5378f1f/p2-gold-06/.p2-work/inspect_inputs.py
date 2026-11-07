"""Read-only inspection of inputs for P2-Gold-06; writes one UTF-8 JSON report."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\AgentAIProgect\RAG")
sys.path.insert(0, str(ROOT))

from rag_app.eval_dataset.corpus import load_corpus_snapshot  # noqa: E402

OUT = ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
CAND = ROOT / "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl"
CORPUS_MANIFEST = ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.manifest.json"
DEST = OUT / "p2-gold-06/.p2-work/inspect.json"

manifest, rows = load_corpus_snapshot(CORPUS_MANIFEST)
chunks = {r["chunk_id"]: r for r in rows}

doc_map = {}
for r in rows:
    doc_map[r["source"]] = {
        "document_id": r["document_id"],
        "document_version": r["document_version"],
        "document_content_hash": r["document_content_hash"],
    }

ids = [
    "0eb4bd6e18d599063371f51b", "e010fe39879d92fa21dc59d9", "1c317b1dd2cebfbf9647d03e",
    "92108b5bb6dcc5b2227d531c", "03e5582a4a0f7d3c76a33e66", "81951fb8b5e157346ed83d77",
    "5ab56d780f65ff344900b1a2", "469978708f9fe4506fc1fa7f", "611a9eb6554a2b482561c775",
    "4931f1a7b903ba2672bbb512", "a264a91966d85e2ec3b52e02", "95cb40813342a7e91c27e7d3",
]
batch01_ids = [
    "831af7c41fd776db6b5b3ff9", "4f32247f7a6d7526df77bddd", "02c18b66c8c7d17fa1fb910e",
    "4812f97659f77c46891223fa", "c120df3a569ae215d69183ac", "38ea5e749604f43f5f040901",
    "9b5d9b92dc528a1c594e3ec2", "48ecc091e26caaa3ccbd3be5", "c10a8b3b89210595f9880fc6",
]

chunk_info = {}
for cid in ids + batch01_ids:
    r = chunks.get(cid)
    chunk_info[cid] = None if r is None else {
        "source": r["source"], "page_number": r["page_number"],
        "section_title": r["metadata"].get("section_title"),
        "document_version": r["document_version"],
        "chunk_text": r["chunk_text"], "chunk_text_sha256": r["chunk_text_sha256"],
    }

cand_ids = {
    "B13": "sha256:ba50e7af3e31659d88a2d0b4937eb510a09e19e2238d1c0e93a923a1aa42fe50",
    "B14": "sha256:6b27f4cd6fb8a57d3ba3c96049bb0c8ce98b909be142ed809ab85a0bac89fba6",
    "B15": "sha256:029aaf51ce9894999917d4730c0682047e6aee33d34f15d1bbc64e1195361c91",
    "B16": "sha256:c0ee402dcbe543fe04df844c2c9d2134f4922a88177a166d82f0e2b2cdcd37c6",
    "B17": "sha256:8fcecc4204b0c7149f3d002b1b693d01b9be5a5e8930d621c5ef089f39e0585a",
    "B18": "sha256:b36c80cc90660614833ec0bdf464df7b4d37db9064457a2d1e2c496856ced6ba",
    "B19": "sha256:4f4129854aedf46810ac9654b5e918be591a55ffb3a8bd01c24ca7aa787237de",
    "B20": "sha256:0c141695e2654b721a2a70e712bfdd9cc951d132b823ef8b710b0f07c17d7f73",
    "B21": "sha256:af261cdb97be35e69dd294aff4351ed7ec7477048b2377adaee100697c1809d3",
    "B22": "sha256:474ea2ea4e472386215819df6edeb7f88ca3c1af3abae6259f11972588f52812",
    "B23": "sha256:0f3b338e277722ef4de67a59096d7e8c931138eb05c300808fc9d2ea9a186468",
    "B24": "sha256:d049bb19337a6de2e27a654729cdbfc8b84ef5e4b93dd4f31606dc51f4a0c6dd",
    "B25": "sha256:2fa4c3c7182110647ed797c132138313300e447227199131a9731a8acd4a1afa",
    "B26": "sha256:6535e6f78dc8eeb10b933e995f8321cd01ed80d90f405c5042b7fbfccf08ac95",
    "B27": "sha256:0412887e0c24cae711a326d0032a59e8cce8c7618478be6748fd98c2cfc9f4bf",
}
items = [json.loads(line) for line in CAND.read_text(encoding="utf-8").splitlines() if line.strip()]
by_id = {it["candidate_id"]: it for it in items}
cands = {label: by_id.get(cid) for label, cid in cand_ids.items()}

files = [
    OUT / "p2-gold-05/p2_gold_05_signoff_packet.md",
    OUT / "p2-gold-05/p2_gold_05_review_proposal.md",
    OUT / "p2-gold-05/p2_gold_05_validation.md",
    OUT / "p2-gold-05/review_batch02_15_draft.xlsx",
    OUT / "review.xlsx",
    OUT / "review-index.md",
    OUT / "first-batch-evidence.md",
    CAND,
    CORPUS_MANIFEST,
    ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl",
    OUT / "p2-gold-04/retrieval_gold_batch01_9.jsonl",
    OUT / "p2-gold-04/retrieval_gold_batch01_metadata.json",
    OUT / "p2-gold-04/rejected_batch01_3.jsonl",
    OUT / "p2-gold-04/gold_batch01_manifest.json",
    OUT / "p2-gold-04/p2_gold_04_validation.md",
    ROOT / "storage/evaluation/candidates/p1-20261104-structured/generation_manifest.json",
    ROOT / "rag_app/operations/evaluation.py",
    ROOT / "rag_app/eval_dataset/corpus.py",
    ROOT / "rag_app/eval_dataset/candidates.py",
    ROOT / "rag_app/eval_dataset/schemas.py",
]
file_hashes = {
    f.relative_to(ROOT).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest() for f in files
}

workbook = {"error": None, "header": [], "rows": []}
try:
    from openpyxl import load_workbook
    wb = load_workbook(OUT / "p2-gold-05/review_batch02_15_draft.xlsx", read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    workbook["sheets"] = wb.sheetnames
    workbook["max_row"], workbook["max_col"] = ws.max_row, ws.max_column
    for row in ws.iter_rows(min_row=1, max_row=2, values_only=True):
        workbook["header"].append([None if v is None else str(v) for v in row])
    for index, row in enumerate(ws.iter_rows(min_row=16, max_row=32, values_only=True), start=16):
        workbook["rows"].append([index] + [None if v is None else str(v) for v in row])
except Exception as exc:  # noqa: BLE001
    workbook["error"] = f"{type(exc).__name__}: {exc}"

report = {
    "snapshot_id": manifest["snapshot_id"],
    "manifest_sha256": manifest["manifest_sha256"],
    "record_count": len(rows),
    "document_count": manifest["document_count"],
    "scope": manifest["scope"],
    "doc_map": doc_map,
    "chunk_info": chunk_info,
    "candidates": cands,
    "candidate_file_count": len(items),
    "candidate_unique_ids": len(by_id),
    "file_hashes": file_hashes,
    "workbook": workbook,
}
DEST.parent.mkdir(parents=True, exist_ok=True)
DEST.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", DEST, "bytes", DEST.stat().st_size)
