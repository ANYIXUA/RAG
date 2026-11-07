# -*- coding: utf-8 -*-
"""g03 只读抽取：
1) 评测样例 case_results 的 expected 目标结构（判分口径证据）；
2) g02 草稿与原始 review.xlsx 的行 1-16 逐格值（含 H/I/J 文本、F/G 状态、候选映射）；
3) 输出 g03_extract.json 供后续脚本复用。全部只读，不改任何源文件。"""
import json
import sys
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(r"D:\AgentAIProgect\RAG\storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f")
WORK = OUT_DIR / ".p2-work"
EVAL_JSON = Path(r"D:\AgentAIProgect\RAG\retrieval_eval_20261103_134741.json")
G02 = OUT_DIR / "review_p2_gold_02_draft.xlsx"
ORIG = OUT_DIR / "review.xlsx"

payload: dict = {}

# --- 1) 评测样例 expected 结构 ---
d = json.load(open(EVAL_JSON, encoding="utf-8"))
runs = d.get("runs", [])
cr = runs[0].get("case_results", []) if runs else []
payload["eval_sample"] = [
    {
        "query": c.get("query"),
        "hit": c.get("hit"),
        "rank": c.get("rank"),
        "expected": c.get("expected"),
    }
    for c in cr
]

# --- 2) 行 1-16 逐格 ---
rows = {}
for label, path in (("g02_draft", G02), ("original", ORIG)):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    dump = []
    for r in range(1, 17):
        vals = []
        for c in range(1, 14):
            cell = ws.cell(row=r, column=c)
            v = cell.value
            vals.append("" if v is None else str(v))
        dump.append(vals)
    rows[label] = dump
payload["rows"] = rows

# --- 3) B01-B12 行映射（行号 -> candidate 上下文） ---
cands_path = Path(r"D:\AgentAIProgect\RAG\storage\evaluation\candidates\p1-20261104-structured\candidates.jsonl")
cands = [json.loads(l) for l in open(cands_path, encoding="utf-8") if l.strip()]
by_id = {c["candidate_id"]: c for c in cands}
mapping = []
for r in range(5, 17):
    cid = rows["original"][r - 1][0]  # A 列
    c = by_id.get(cid, {})
    mapping.append(
        {
            "row": r,
            "candidate_id": cid,
            "question_type": c.get("question_type"),
            "question": c.get("question"),
            "proposed_answer": c.get("proposed_answer"),
            "supporting_chunk_ids": c.get("supporting_chunk_ids"),
        }
    )
payload["b_rows"] = mapping

out = WORK / "g03_extract.json"
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("saved:", out)

print("=== eval sample case_results (query/hit/rank/expected) ===")
for e in payload["eval_sample"]:
    print(json.dumps(e, ensure_ascii=False)[:600])

print("=== B01-B12 rows (row, candidate_id, type, F, G, H) ===")
for m in mapping:
    r = m["row"]
    print(
        r,
        m["candidate_id"][:28] + "…",
        m["question_type"],
        "|F=", rows["g02_draft"][r - 1][5],
        "|G=", rows["g02_draft"][r - 1][6],
        "|H=", rows["g02_draft"][r - 1][7][:18],
    )

print("=== g02 draft J column texts (rows 5..16) ===")
for m in mapping:
    r = m["row"]
    j = rows["g02_draft"][r - 1][9]
    i = rows["g02_draft"][r - 1][8]
    if j:
        print(f"row {r} J:", j[:120], "…" if len(j) > 120 else "")
    if i:
        print(f"row {r} I:", i[:100])
