# -*- coding:utf-8 -*-
"""P2-Gold-02 full automatic verification of review_p2_gold_02_draft.xlsx."""
import json
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")
from openpyxl import load_workbook

BASE = r"D:\AgentAIProgect\RAG\storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
SRC = BASE + r"\review.xlsx"
DST = BASE + r"\review_p2_gold_02_draft.xlsx"
DUMP = BASE + r"\.p2-work\dump_full.json"
CAND = r"D:\AgentAIProgect\RAG\storage\evaluation\candidates\p1-20261104-structured\candidates.jsonl"

results = {}
def chk(name, ok, detail=""):
    results[name] = {"pass": bool(ok), "detail": detail}

baseline = {}
with open(DUMP, encoding="utf-8") as f:
    for rowRec in json.load(f):
        baseline[rowRec["row"]] = rowRec["cells"]

wb_src = load_workbook(SRC)
wb_dst = load_workbook(DST)
ws_src = wb_src["候选审核"]
ws_dst = wb_dst["候选审核"]

# --- 11. zip integrity / openable
try:
    with zipfile.ZipFile(DST) as z:
        bad = z.testzip()
    chk("zip_integrity", bad is None, f"zip ok, {len(z.namelist())} entries" if bad is None else f"bad entry {bad}")
except Exception as e:
    chk("zip_integrity", False, str(e))

# --- sheet / dims
chk("sheet_name_same", wb_src.sheetnames == wb_dst.sheetnames, f"{wb_dst.sheetnames}")
chk("dims_same", ws_src.dimensions == ws_dst.dimensions, f"src={ws_src.dimensions} dst={ws_dst.dimensions}")

# --- 1. total candidates = 57
cand_rows = [r for r in range(5, 62)]
ids_xlsx = [ws_dst.cell(row=r, column=2).value for r in cand_rows]
ids_nonnull = [i for i in ids_xlsx if i]
chk("candidate_count_57", len(ids_nonnull) == 57 and ws_dst.max_row == 61,
    f"rows 5..61 candidate_id non-null: {len(ids_nonnull)}; max_row={ws_dst.max_row}")

# --- 2. candidate_id identical to source candidates.jsonl (set + order)
src_records = []
with open(CAND, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            src_records.append(json.loads(line))
ids_jsonl = [r.get("candidate_id") for r in src_records]
norm = lambda s: s
same_order = all(str(a) == str(b) for a, b in zip(ids_jsonl, ids_xlsx))
same_set = sorted(map(str, ids_jsonl)) == sorted(map(str, ids_xlsx))
chk("candidate_ids_match_source", len(ids_jsonl) == 57 and same_set,
    f"jsonl={len(ids_jsonl)}; set_equal={same_set}; row_order_equal={same_order}")

# --- draft vs baseline diff ---
allowed = {}
def put(row, col, note):
    allowed[(row, col)] = note

put(5, 8, "B01 H"); put(5, 10, "B01 J")
put(6, 8, "B02 H"); put(6, 10, "B02 J")
put(7, 8, "B03 H")
put(8, 8, "B04 H"); put(8, 10, "B04 J")
put(9, 8, "B05 H")
put(10, 8, "B06 H"); put(10, 10, "B06 J")
put(11, 8, "B07 H"); put(11, 10, "B07 J")
put(12, 9, "B08 I")
put(13, 8, "B09 H"); put(13, 10, "B09 J")
put(14, 9, "B10 I")
put(15, 9, "B11 I")
put(16, 8, "B12 H"); put(16, 10, "B12 J")

diffs_allowed, diffs_forbidden = [], []
for r in range(1, 62):
    base_cells = baseline.get(r, {})
    for c in range(1, 14):
        letter = chr(64 + c)
        old = base_cells.get(letter)
        new = ws_dst.cell(row=r, column=c).value
        old = None if old in (None, "") else old
        new = None if new in (None, "") else new
        if (old or "") != (new or ""):
            key = (r, c)
            if key in allowed:
                diffs_allowed.append((*key, allowed[key]))
            else:
                diffs_forbidden.append((r, letter, repr(old)[:80], repr(new)[:80]))

chk("diff_only_allowed_cells", len(diffs_forbidden) == 0,
    f"allowed diffs: {len(diffs_allowed)}; forbidden diffs: {len(diffs_forbidden)}" +
    ("" if not diffs_forbidden else "; first=" + str(diffs_forbidden[:1])))

# forbidden list must be exactly the 19 planned edits
chk("planned_edit_count", len(diffs_allowed) == 19, f"actual allowed diffs = {len(diffs_allowed)} (expect 19 = 9H + 3I + 7J)")

# --- 3. original question/answer unchanged (D/E), K unchanged, B/C/C insta-covered by diff check
de_k_ids_same = True
for r in cand_rows:
    for c_letter, c in (("D", 4), ("E", 5), ("K", 11)):
        old = baseline.get(r, {}).get(c_letter)
        old = None if old in (None, "") else old
        new = ws_dst.cell(row=r, column=c).value
        new = None if new in (None, "") else new
        if old != new:
            de_k_ids_same = False
chk("question_answer_chunkids_unchanged", de_k_ids_same)

# --- 4. F column all pending_review (both original & draft)
f_all = all(ws_dst.cell(row=r, column=6).value == "pending_review" for r in cand_rows)
f_src_all = all(ws_src.cell(row=r, column=6).value == "pending_review" for r in cand_rows)
chk("F_all_pending_review", f_all and f_src_all, f"draft={f_all} source={f_src_all}")

# --- G unchanged placeholder
g_all = all(ws_dst.cell(row=r, column=7).value == "human" for r in cand_rows)
chk("G_all_human_placeholder_unchanged", g_all)

# --- 5. 12 H non-empty
h_rows = list(range(5, 17))
h_vals = [(r, ws_dst.cell(row=r, column=8).value) for r in h_rows]
chk("H12_nonempty", all(v not in (None, "") for _, v in h_vals),
    "; ".join(f"r{r}={'' if v in (None,'') else v[:16]}" for r, v in h_vals))

# --- 6. 7 J cells non-empty for revise rows; empty elsewhere
rev_rows = [5, 6, 8, 10, 11, 13, 16]
j_ok = all((ws_dst.cell(row=r, column=10).value or "") != "" for r in rev_rows)
j_ok2 = all((ws_dst.cell(row=r, column=10).value in (None, "")) for r in [7, 9, 12, 14, 15])
chk("J_7_revisions_nonempty", j_ok, f"rows {rev_rows}")
chk("J_untouched_rows_still_empty", j_ok2)

# --- 7. 3 I cells non-empty for reject rows; empty elsewhere
rej_rows = [12, 14, 15]
i_ok = all((ws_dst.cell(row=r, column=9).value or "") != "" for r in rej_rows)
i_ok2 = all((ws_dst.cell(row=r, column=9).value in (None, "")) for r in [5, 6, 7, 8, 9, 10, 11, 13, 16])
chk("I_3_rejections_nonempty", i_ok, f"rows {rej_rows}")
chk("I_untouched_rows_still_empty", i_ok2)

# --- 8. H of rejects unchanged ('建议驳回')
h_rej_same = all((ws_dst.cell(row=r, column=8).value or "") == "建议驳回" for r in rej_rows)
chk("reject_H_unchanged", h_rej_same)

# --- 9. 45 others unchanged (rows 17..61 full compare + rows 1..4 preview)
others_same = True
for r in list(range(17, 62)) + list(range(1, 5)):
    for c in range(1, 14):
        letter = chr(64 + c)
        old = baseline.get(r, {}).get(letter)
        old = None if old in (None, "") else old
        new = ws_dst.cell(row=r, column=c).value
        new = None if new in (None, "") else new
        if old != new:
            others_same = False
chk("other_45_rows_and_header_unchanged", others_same)

# --- 10. source file review.xlsx itself untouched (re-dump & compare to baseline)
wb_re = load_workbook(SRC)
ws_re = wb_re["候选审核"]
src_untouched = True
for r in range(1, 62):
    base_cells = baseline.get(r, {})
    for c in range(1, 14):
        letter = chr(64 + c)
        old = base_cells.get(letter)
        old = None if old in (None, "") else str(old)
        new = ws_re.cell(row=r, column=c).value
        new = None if new in (None, "") else str(new)
        if old != new:
            src_untouched = False
chk("review_xlsx_untouched", src_untouched)

# --- summarise rejected values for the report
report_rows = []
for r in h_rows:
    report_rows.append({
        "row": r,
        "batch_id": ws_dst.cell(row=r, column=1).value,
        "candidate_id": ws_dst.cell(row=r, column=2).value,
        "F": ws_dst.cell(row=r, column=6).value,
        "G": ws_dst.cell(row=r, column=7).value,
        "H_nonempty": bool((ws_dst.cell(row=r, column=8).value or "").strip()),
        "I_nonempty": bool((ws_dst.cell(row=r, column=9).value or "").strip()),
        "J_nonempty": bool((ws_dst.cell(row=r, column=10).value or "").strip()),
        "row_height": ws_dst.row_dimensions[r].height,
    })

out_path = BASE + r"\.p2-work\verify_result.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"checks": results, "b12_rows": report_rows}, f, ensure_ascii=False, indent=1)

for k, v in results.items():
    print(("PASS " if v["pass"] else "FAIL ") + k + "  :: " + v["detail"])
print()
print("ALL PASS" if all(v["pass"] for v in results.values()) else "SOME FAILED")
print("detail rows:")
for rr in report_rows:
    print(rr)
print("report saved:", out_path)
