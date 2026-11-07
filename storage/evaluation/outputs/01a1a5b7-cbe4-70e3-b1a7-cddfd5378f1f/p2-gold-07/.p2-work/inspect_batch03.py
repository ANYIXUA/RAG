"""P2-Gold-07 stage 1: read-only collection of frozen inputs for B23/B27/B28-B42.

Writes b03_inputs.json next to this script. Does not modify any frozen artefact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz
import openpyxl

ROOT = Path(r"D:\AgentAIProgect\RAG")
OUT = ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
G05 = OUT / "p2-gold-05"
G06 = OUT / "p2-gold-06"
HERE = Path(__file__).resolve().parent

CANDS = ROOT / "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl"
CORPUS = ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl"
PDF_DIR = ROOT / "data"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


cands = load_jsonl(CANDS)
chunks = load_jsonl(CORPUS)
cand_by_id = {c["candidate_id"]: c for c in cands}
chunk_by_id = {c["chunk_id"]: c for c in chunks}

# --- workbook B-number mapping (authoritative: B = row - 4) ---
wb = openpyxl.load_workbook(OUT / "review.xlsx", read_only=True, data_only=True)
ws = wb.active
header = [ws.cell(row=4, column=i).value for i in range(1, 9)]
mapping = []
for row in range(5, 62):
    cid = ws.cell(row=row, column=2).value
    mapping.append({"row": row, "b": f"B{row - 4:02d}", "candidate_id": cid})

# --- PDF page cache ---
pdf_cache: dict[str, fitz.Document] = {}


def page_text(doc_name: str, page_no: int) -> str:
    if doc_name not in pdf_cache:
        pdf_cache[doc_name] = fitz.open(PDF_DIR / doc_name)
    doc = pdf_cache[doc_name]
    if page_no < 1 or page_no > doc.page_count:
        return ""
    return doc[page_no - 1].get_text("text")


def collect(bnum: str) -> dict:
    entry = next(m for m in mapping if m["b"] == bnum)
    cand = cand_by_id[entry["candidate_id"]]
    ev = {cid: chunk_by_id[cid] for cid in cand["supporting_chunk_ids"]}
    pages = {}
    for cid, ch in ev.items():
        doc = ch["source"]
        pno = ch["page_number"]
        key = f"{doc}#p{pno}"
        if key not in pages:
            pages[key] = page_text(doc, pno)
    return {
        "b": bnum,
        "workbook_row": entry["row"],
        "candidate": cand,
        "evidence_chunks": ev,
        "pdf_pages": pages,
    }


targets = ["B23", "B27"] + [f"B{i:02d}" for i in range(28, 43)]
payload = {
    "frozen_sha256": {
        "candidates.jsonl": sha(CANDS),
        "corpus.jsonl": sha(CORPUS),
    },
    "counts": {"candidates": len(cands), "chunks": len(chunks), "mapping": len(mapping)},
    "workbook_header_row4": header,
    "mapping": mapping,
    "records": {b: collect(b) for b in targets},
    "gold_batch01": load_jsonl(OUT / "p2-gold-04/retrieval_gold_batch01_9.jsonl"),
    "gold_batch02": load_jsonl(G06 / "retrieval_gold_batch02_13.jsonl"),
}

(HERE / "b03_inputs.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
)

print("candidates_sha256", payload["frozen_sha256"]["candidates.jsonl"])
print("corpus_sha256", payload["frozen_sha256"]["corpus.jsonl"])
print("cands", len(cands), "chunks", len(chunks))
print("header", header)
for b in targets:
    r = payload["records"][b]
    c = r["candidate"]
    print(b, r["workbook_row"], c["candidate_id"][7:15], len(c["supporting_chunk_ids"]),
          c["question_type"], c["difficulty"])
print("wrote", HERE / "b03_inputs.json")
