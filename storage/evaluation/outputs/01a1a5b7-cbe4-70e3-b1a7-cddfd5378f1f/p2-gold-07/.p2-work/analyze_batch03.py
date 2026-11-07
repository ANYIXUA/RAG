"""P2-Gold-07 stage 2: per-candidate evidence assembly for B28-B42.

Read-only over frozen inputs. Emits batch03_dump.md (human reading) and
batch03_facts.json (machine checks used later by the validator).
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(r"D:\AgentAIProgect\RAG")
OUT = ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"

data = json.loads((HERE / "b03_inputs.json").read_text(encoding="utf-8"))
records = data["records"]
corpus = [json.loads(x) for x in (ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl")
          .read_text(encoding="utf-8").splitlines() if x.strip()]
cand_all = [json.loads(x) for x in (ROOT / "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl")
            .read_text(encoding="utf-8").splitlines() if x.strip()]
mapping = {m["candidate_id"]: m for m in data["mapping"]}
batch01 = data["gold_batch01"]
batch02 = data["gold_batch02"]


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def body(chunk_text: str) -> str:
    """Chunk text without the exporter's '章节/页码' prefix line."""
    parts = chunk_text.split(" ", 3)
    # prefix format: 章节：<doc> > 第N页 页码：N <body...>
    m = re.match(r"^章节：.*?第\d+页\s*页码：\d+\s*(.*)$", chunk_text, re.S)
    return m.group(1) if m else chunk_text


targets = [f"B{i:02d}" for i in range(28, 43)]
facts: dict[str, dict] = {}
lines = ["# B28-B42 证据汇总（自动生成，仅供审核用）", ""]

for b in targets:
    rec = records[b]
    cand = rec["candidate"]
    row = rec["workbook_row"]
    entry: dict = {
        "b": b,
        "workbook_row": row,
        "candidate_id": cand["candidate_id"],
        "question_type": cand["question_type"],
        "difficulty": cand["difficulty"],
        "question": cand["question"],
        "proposed_answer": cand["proposed_answer"],
        "supporting_chunk_ids": cand["supporting_chunk_ids"],
        "chunks": [],
        "answer_in_chunk": None,
        "answer_in_pdf_page": None,
        "same_page_chunk_count": None,
        "similar": [],
        "peer_relevant_chunks": [],
    }

    for cid in cand["supporting_chunk_ids"]:
        ch = rec["evidence_chunks"][cid]
        bd = body(ch["chunk_text"])
        pno = ch["page_number"]
        pdf_text = rec["pdf_pages"][f"{ch['source']}#p{pno}"]
        in_pdf = norm(bd)[:120] in norm(pdf_text) if norm(bd) else False
        entry["chunks"].append({
            "chunk_id": cid,
            "source": ch["source"],
            "page": pno,
            "document_version": ch["document_version"],
            "chunk_text_sha256": ch["chunk_text_sha256"],
            "chunk_text": ch["chunk_text"],
            "pdf_page_exact_head_match": in_pdf,
            "pdf_page_text": pdf_text,
        })
        if entry["answer_in_chunk"] is None:
            entry["answer_in_chunk"] = norm(cand["proposed_answer"]) in norm(ch["chunk_text"])
        entry["answer_in_pdf_page"] = norm(bd)[:120] in norm(pdf_text)

    # chunks on the same document+page (row-level neighbours in the same parse unit)
    doc0 = entry["chunks"][0]["source"]
    page0 = entry["chunks"][0]["page"]
    entry["same_page_chunk_count"] = sum(
        1 for c in corpus if c["source"] == doc0 and c["page_number"] == page0)

    # duplicate scan against every other candidate question
    q = cand["question"]
    scored = []
    for other in cand_all:
        if other["candidate_id"] == cand["candidate_id"]:
            continue
        ratio = difflib.SequenceMatcher(None, q, other["question"]).ratio()
        ob = mapping.get(other["candidate_id"], {}).get("b", "?")
        scored.append((round(ratio, 4), ob, other["question"]))
    scored.sort(reverse=True)
    entry["similar"] = [
        {"ratio": r, "b": ob, "question": oq,
         "in_gold": any(g["query"] == oq for g in batch01 + batch02)}
        for r, ob, oq in scored[:5]
    ]

    # possible additional relevant chunks: same doc, contains a distinctive answer slice
    ans = cand["proposed_answer"]
    slices = [ans[:12]] if len(ans) >= 6 else [ans]
    peers = []
    for c in corpus:
        if c["chunk_id"] in cand["supporting_chunk_ids"]:
            continue
        if c["source"] != doc0:
            continue
        if any(norm(s) and norm(s) in norm(c["chunk_text"]) for s in slices):
            peers.append({"chunk_id": c["chunk_id"], "page": c["page_number"],
                          "head": c["chunk_text"][:80]})
    entry["peer_relevant_chunks"] = peers
    facts[b] = entry

    lines += [f"## {b}（工作簿第 {row} 行）", "",
              f"- candidate_id: `{cand['candidate_id']}`",
              f"- 题型/难度: {cand['question_type']} / {cand['difficulty']}",
              f"- 原题: {cand['question']}",
              f"- 原答: {cand['proposed_answer']}",
              f"- 支持 Chunk: {', '.join(cand['supporting_chunk_ids'])}",
              f"- 答案出现在支持 Chunk: {entry['answer_in_chunk']}",
              f"- Chunk 正文出现在 PDF 页: {[c['pdf_page_exact_head_match'] for c in entry['chunks']]}",
              f"- 同文档同页 Chunk 数: {entry['same_page_chunk_count']}",
              f"- 同文档其它含答案片段 Chunk: {[(p['chunk_id'], p['page']) for p in peers]}",
              f"- 最相似题: {[(s['ratio'], s['b']) for s in entry['similar'][:3]]}",
              "", "### Chunk 正文", ""]
    for c in entry["chunks"]:
        lines += [f"**{c['chunk_id']}** · {c['source']} · 物理页 {c['page']} · {c['document_version']}", "",
                  "```text", c["chunk_text"].strip(), "```", ""]
    lines += ["### PDF 该页原文", "", "```text", entry["chunks"][0]["pdf_page_text"].strip()[:2600], "```", ""]

(HERE / "batch03_facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
(HERE / "batch03_dump.md").write_text("\n".join(lines), encoding="utf-8")

for b in targets:
    e = facts[b]
    print(b, "ans_in_chunk", e["answer_in_chunk"], "pdf", e["chunks"][0]["pdf_page_exact_head_match"],
          "samepage", e["same_page_chunk_count"], "peers", len(e["peer_relevant_chunks"]),
          "top", e["similar"][0]["ratio"], e["similar"][0]["b"])
print("bytes", (HERE / "batch03_dump.md").stat().st_size)
