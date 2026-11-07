# -*- coding: utf-8 -*-
"""g03 自动验收 + 签核包数据打印。只读检查，不修改任何源文件。
检查项：
 1 g03 草稿可打开（zip 完整、openpyxl 加载、工作表与尺寸与 g02 一致）
 2 g02 → g03 全簿 A1:M61 逐格 diff = 仅 行11/16 × H/J = 4 格
 3 g03/g02 第 17–61 行与其余 45 条逐格不变（包含于第 2 项，单列复核）
 4 内存基线：review.xlsx（原始）在本会话内逐格未变（对比 g03_extract.json 中 original 快照）
 5 F 列 57 条全部 pending_review；G 列保持 human
 6 H 列 12 条非空；I 列仅 12/14/15；J 列仅 5/6/8/10/11/13/16
 7 候选 JSONL：57 条、全 pending_review、candidate_id 集合与工作簿一致
 8 B07/B12 父候选原始字段未被改动（question/answer/supporting 与本轮快照一致）
 9 g03 草稿内容断言：H11 含两 Chunk id 与核验结论；J16 推荐问题不含答案短语（含解析空格变体）；
   J16 答案含 初级/中级 两部分；J16 含 any-hit/hit_at_k 口径记录；行高只增不减
10 Git：无已跟踪文件改动、无新增提交
"""
import json
import subprocess
import sys
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(r"D:\AgentAIProgect\RAG\storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f")
WORK = OUT_DIR / ".p2-work"
G02 = OUT_DIR / "review_p2_gold_02_draft.xlsx"
G03 = OUT_DIR / "review_p2_gold_03_draft.xlsx"
ORIG = OUT_DIR / "review.xlsx"

results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((ok, name, detail))
    print(("PASS" if ok else "FAIL"), "|", name, "|", detail)


# 1) 可打开
wb2 = openpyxl.load_workbook(G02)
wb3 = openpyxl.load_workbook(G03)
ws2, ws3 = wb2.active, wb3.active
check("g03 草稿可正常打开（openpyxl 加载成功）", wb3 is not None)
check("工作表名与尺寸一致", ws2.title == ws3.title and ws2.max_row == ws3.max_row and ws2.max_column == ws3.max_column,
      f"{ws3.title} {ws3.max_row}x{ws3.max_column}")

# 2) 全簿 diff g02 -> g03
diffs = []
for r in range(1, max(ws2.max_row, ws3.max_row) + 1):
    for c in range(1, max(ws2.max_column, ws3.max_column) + 1):
        v2 = ws2.cell(row=r, column=c).value
        v3 = ws3.cell(row=r, column=c).value
        if v2 != v3:
            diffs.append((r, c))
allowed = {(11, 8), (11, 10), (16, 8), (16, 10)}
check("全簿逐格 diff 仅 4 授权格（行11/16 × H/J）", set(diffs) == allowed, f"diff={sorted(diffs)}")

r17_61 = [(r, c) for r, c in diffs if r >= 17]
check("第 17–61 行（其余 45 条与表注）零差异", not r17_61)

# 3) 行高只增不减
import json as _json  # noqa: E402
height_check = []
for r, base in ((11, 540.0), (16, 729.0)):
    h3 = ws3.row_dimensions[r].height
    h2 = ws2.row_dimensions[r].height
    height_check.append(h2 is not None and h3 is not None and h3 >= h2)
check("行 11/16 行高只增不减（540→{:.1f}，729→{:.1f}）".format(
    ws3.row_dimensions[11].height or 0, ws3.row_dimensions[16].height or 0), all(height_check))
wrap_ok = all(ws3.cell(row=r, column=c).alignment.wrapText for r in (11, 16) for c in (8, 10))
check("行 11/16 H/J wrap_text=True", wrap_ok)

# 4) review.xlsx 本会话未变（对比 g03_extract.json 的 original 快照 rows 1-16）
extract = _json.load(open(WORK / "g03_extract.json", encoding="utf-8"))
wbO = openpyxl.load_workbook(ORIG)
wsO = wbO.active
stab = []
for r in range(1, 17):
    for c in range(1, 14):
        v_old = extract["rows"]["original"][r - 1][c - 1]
        v_now = wsO.cell(row=r, column=c).value
        v_now = "" if v_now is None else str(v_now)
        if ("" if v_old is None else str(v_old)) != v_now:
            stab.append((r, c))
check("原始 review.xlsx 逐格未变（对比本会话早前快照）", not stab, f"{stab}")

# 5) F/G 状态
f_pending = all(str(ws3.cell(row=r, column=6).value) == "pending_review" for r in range(5, 62))
check("F 列 57 条全部 pending_review", f_pending and ws3.max_row == 61)
g_human = all(str(ws3.cell(row=r, column=7).value) == "human" for r in range(5, 62))
check("G 列保持 human 占位", g_human)

# 6) H/I/J 布局
h_ok = all(str(ws3.cell(row=r, column=8).value or "").strip() for r in range(5, 17))
i_rows = [r for r in range(5, 62) if str(ws3.cell(row=r, column=9).value or "").strip()]
j_rows = [r for r in range(5, 62) if str(ws3.cell(row=r, column=10).value or "").strip()]
check("H 列 B01–B12 非空", h_ok)
check("I 列仅行 12/14/15", i_rows == [12, 14, 15], f"{i_rows}")
check("J 列仅行 5/6/8/10/11/13/16", j_rows == [5, 6, 8, 10, 11, 13, 16], f"{j_rows}")

# 7) 候选 JSONL
cands_path = Path(r"D:\AgentAIProgect\RAG\storage\evaluation\candidates\p1-20261104-structured\candidates.jsonl")
cands = [_json.loads(l) for l in open(cands_path, encoding="utf-8") if l.strip()]
check("候选 JSONL 总数 57", len(cands) == 57)
check("57 条全部 review_status=pending_review",
      all(c.get("review_status") == "pending_review" for c in cands))
sheet_ids = [str(ws3.cell(row=r, column=2).value) for r in range(5, 62)]
check("candidate_id 集合与工作簿一致", {c["candidate_id"] for c in cands} == set(sheet_ids))

# 8) B07/B12 父候选原始字段未变
parent_rows = {11: "B07", 16: "B12"}
immutable_ok = True
detail8 = []
for sheet_row, label in parent_rows.items():
    cid = str(ws3.cell(row=sheet_row, column=2).value)
    rec = next(c for c in cands if c["candidate_id"] == cid)
    d_old = str(ws2.cell(row=sheet_row, column=4).value)
    e_old = str(ws2.cell(row=sheet_row, column=5).value)
    ok = rec["question"] == d_old and rec["proposed_answer"] == e_old
    sup_ok = set(rec["supporting_chunk_ids"]) == set(str(ws3.cell(row=sheet_row, column=11).value).split())
    immutable_ok &= ok and sup_ok
    detail8.append(f"{label}:q_ok={ok},support_ok={sup_ok},chunks={rec['supporting_chunk_ids']}")
check("B07/B12 父候选原始 question/answer/supporting_chunk_ids 未被改动", immutable_ok, "; ".join(detail8))

# 9) 内容断言
h11 = str(ws3.cell(row=11, column=8).value)
h16 = str(ws3.cell(row=16, column=8).value)
j16 = str(ws3.cell(row=16, column=10).value)
check("B07 意见含来源 Chunk 核验结论",
      "38ea5e749604f43f5f040901" in h11 and "c120df3a569ae215d69183ac" in h11 and "跨页续文" in h11)
q_start = j16.index("5. 推荐修改后的 question：") + len("5. 推荐修改后的 question：")
q_end = j16.index("\n6. 推荐修改后的 proposed_answer：")
recommended_q = j16[q_start:q_end].strip()
recommended_a = j16[q_end + len("\n6. 推荐修改后的 proposed_answer："):].strip()
leak_clean = all(ph not in recommended_q for ph in (
    "无线局域网相关基础知识", "无线局域网网优及软件基础知识",
    "无线局域网相关基础知 识", "无线局域网网优及软件基础知 识"))
check("B12 推荐问题不含两个答案短语（含解析空格变体）", leak_clean, repr(recommended_q[:60]) + "…")
check("B12 推荐答案同时含 初级/中级 两部分", "初级" in recommended_a and "中级" in recommended_a and
      "无线局域网网优及软件基础知识" in recommended_a and "无线局域网相关基础知识" in recommended_a)
check("B12 意见含 any-hit 口径记录", "any-hit" in h16 and "any-hit" in h16 + j16 and
      ("hit_at_k" in j16 and "_first_match_rank" in j16))
check("B12 意见含中级三项口径说明", "3.2.3" in h16 and "3.2.2" in h16)

# 10) Git 状态
st = subprocess.run(
    ["git", "-C", r"D:\AgentAIProgect\RAG", "status", "--porcelain=v1"],
    capture_output=True, text=True).stdout
tracked_mods = [l for l in st.splitlines() if l and not l.startswith("??")]
check("Git 无已跟踪文件改动、无 commit", not tracked_mods, repr(st.replace("\n", " | ")))

n_fail = sum(1 for ok, _, _ in results if not ok)
print(f"\n=== 汇总：{len(results) - n_fail}/{len(results)} 通过，{n_fail} 失败 ===")
_json.dump([{"name": n, "ok": ok, "detail": d} for ok, n, d in results],
           open(WORK / "g03_verify_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# —— 签核包数据打印：行 5–16 的 label/candidate_id/题型/原问/原答/引用 ——
print("\n=== 签核包数据：行 5–16 原始记录（candidate.jsonl）===")
for r in range(5, 17):
    cid = str(ws3.cell(row=r, column=2).value)
    label = str(ws3.cell(row=r, column=1).value)
    rec = next(c for c in cands if c["candidate_id"] == cid)
    print(f"{label} | row {r} | {cid}")
    print(f"    type={rec['question_type']} supp={rec['supporting_chunk_ids']}")
    print(f"    Q={rec['question']}")
    print(f"    A={rec['proposed_answer']}")
_json.dump({"rows": {str(ws3.cell(row=r, column=1).value): {
                "row": r,
                "candidate_id": str(ws3.cell(row=r, column=2).value),
                "question_type": (next(c for c in cands if c['candidate_id'] == str(ws3.cell(row=r, column=2).value)))["question_type"],
                "question": str(ws3.cell(row=r, column=4).value),
                "answer": str(ws3.cell(row=r, column=5).value),
                "supporting": str(ws3.cell(row=r, column=11).value),
            } for r in range(5, 17)},
            "verify": [{"name": n, "ok": ok, "detail": d} for ok, n, d in results]},
           open(WORK / "g03_packet_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("saved:", WORK / "g03_packet_data.json")
