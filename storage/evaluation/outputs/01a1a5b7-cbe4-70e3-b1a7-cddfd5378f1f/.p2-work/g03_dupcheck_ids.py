# -*- coding: utf-8 -*-
"""g03 计算：1) B07/B12 推荐问题与 57 条候选池的近重复度（CJK 双字组 Jaccard + 覆盖度）；
2) 7 条修订候选的确定性 revision_id（规则：rev1: + sha256(parent|revised_q|revised_a)）；
3) B12 题面不含答案短语、B07 题面含限定词等断言。全部只读。"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(r"D:\AgentAIProgect\RAG\storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f")
WORK = OUT_DIR / ".p2-work"
extract = json.load(open(WORK / "g03_extract.json", encoding="utf-8"))

# ---------- g03 最终推荐 Q/A（7 条修订候选） ----------
revised = {
    "B01": {
        "parent": extract["rows"]["original"][4][1],
        "q": "非高速公路场景下，管道线路的人（手）孔检修周期是多久？",
        "a": "半年（高速公路中人孔的检修按需进行，不适用半年周期）。",
    },
    "B02": {
        "parent": extract["rows"]["original"][5][1],
        "q": "在维护分项作业表10.3.3.4（WH23104 安装、测试波分复用器）中，波分复用器测试项目“测试波分复用器1:2”（项目编码 WH23104003）的综合单价是多少（元/个）？",
        "a": "29.18 元/个（WH23104003，测试波分复用器1:2；表头计量单位：个）。",
    },
    "B04": {
        "parent": extract["rows"]["original"][7][1],
        "q": "在 7.2 智慧家庭装维工程与管理实操技能权重表中，技能等级为高级时，“安全作业”项目的权重是多少（%）？",
        "a": "10%",
    },
    "B06": {
        "parent": extract["rows"]["original"][9][1],
        "q": "《智慧家庭装维工程与管理职业技能等级标准》4.2 节中，智慧家庭工程师的职业编码是什么？",
        "a": "4-04-02-012",
    },
    "B07": {
        "parent": extract["rows"]["original"][10][1],
        "q": "在《中国移动智慧家庭全光组网产品技术规范》附录 A.2 中，光路由终端二维码的尺寸大小要求是什么？",
        "a": "不小于17×17mm（公差：±1mm)，正方形",
    },
    "B09": {
        "parent": extract["rows"]["original"][12][1],
        "q": "在室温 25±2℃ 的情况下，非嵌入式全光组网终端表面温度不得超过多少℃？",
        "a": "50℃",
    },
    "B12": {
        "parent": extract["rows"]["original"][15][1],
        "q": "根据《智慧家庭装维工程与管理职业技能等级标准》，初级基础网络质量检测与中级基础网络优化，对无线局域网知识的要求分别是什么？",
        "a": "初级要求无线局域网相关基础知识；中级要求无线局域网网优及软件基础知识。",
    },
}
# 同步 parent 的 short label 映射（对照 g02 草稿 B 列）
for r, label in ((5, "B01"), (6, "B02"), (8, "B04"), (10, "B06"), (11, "B07"), (13, "B09"), (16, "B12")):
    assert extract["rows"]["original"][r - 1][0] == label, (r, label)
    revised[label]["parent"] = extract["rows"]["original"][r - 1][1]

# ---------- 1) 查重 ----------
def norm(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", s)

def bigrams(s: str) -> set:
    t = norm(s)
    return {t[i : i + 2] for i in range(max(len(t) - 1, 0))}

cands_path = Path(r"D:\AgentAIProgect\RAG\storage\evaluation\candidates\p1-20261104-structured\candidates.jsonl")
cands = [json.loads(l) for l in open(cands_path, encoding="utf-8") if l.strip()]
assert len(cands) == 57

pool = []
for c in cands:
    pool.append({"id": c["candidate_id"], "q": c.get("question") or "", "bg": bigrams(c.get("question") or "")})

label_by_parent = {v["parent"]: k for k, v in revised.items()}

print("=== 与 57 条候选原始题面的近重复度（Top3）===")
dup_report = {}
for label in ("B07", "B12"):
    tq = revised[label]["q"]
    tbg = bigrams(tq)
    scored = []
    for item in pool:
        inter = tbg & item["bg"]
        uni = tbg | item["bg"]
        j = round(len(inter) / len(uni), 4) if uni else 0.0
        cov = round(len(inter) / len(tbg), 4) if tbg else 0.0
        scored.append((j, cov, label_by_parent.get(item["id"], ""), item["id"], item["q"]))
    scored.sort(reverse=True)
    top3 = []
    print(f"--- {label} revised_q bigrams={len(tbg)} ---")
    for j, cov, lbl, cid, q in scored[:3]:
        own = "（本条父候选）" if lbl == label else ""
        print(f"  J={j:.4f} cov={cov:.4f} {lbl or '其余候选'} {own} :: {q[:60]}")
        top3.append({"jaccard": j, "coverage": cov, "label": lbl,
                     "candidate_id": cid, "question": q})
    # 阈值断言：最近邻不达“高度重复”
    worst = scored[0]
    flag = worst[0] >= 0.35 or worst[1] >= 0.7
    print(f"  => 高度重复判定: {'⚠ 需人工复核' if flag else '否（最近邻 J<0.35 且 cov<0.70）'}")
    dup_report[label] = {
        "top3": top3,
        "top": {"jaccard": worst[0], "coverage": worst[1], "label": worst[2],
                "candidate_id": worst[3], "question": worst[4]},
        "flag_high_dup": flag,
    }

# ---------- 2) revision_id ----------
ids = {c["candidate_id"] for c in cands}
print("=== 确定性 revision_id（规则 rev1: + sha256(parent + '|' + revised_q + '|' + revised_a)）===")
ids_out = {}
for label, item in revised.items():
    seed = f'{item["parent"]}|{item["q"]}|{item["a"]}'
    h = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    rid = f"rev1:{h}"
    ids_out[label] = {
        "revision_id": rid,
        "parent_candidate_id": item["parent"],
        "revised_question": item["q"],
        "revised_answer": item["a"],
        "seed_string": seed,
    }
    flag = "⚠ 与既有 candidate_id 冲突" if rid in ids else "（与 57 个既有 candidate_id 无冲突）"
    print(f"{label}: {rid}  {flag}  parent={item['parent'][:30]}…")
    assert ids_out[label]["revision_id"] not in ids

assert len({v['revision_id'] for v in ids_out.values()}) == 7

# ---------- 3) 断言 ----------
b12q = revised["B12"]["q"]
b12a = revised["B12"]["a"]
phrases = ["无线局域网相关基础知识", "无线局域网网优及软件基础知识",
           "无线局域网相关基础知 识", "无线局域网网优及软件基础知 识"]
print("=== B12 题面不含答案短语断言 ===")
for ph in phrases:
    print(f"  '{ph}' in question ->", ph in b12q)
    assert ph not in b12q
assert "初级" in b12q and "中级" in b12q
assert "初级" in b12a and "中级" in b12a
b07q = revised["B07"]["q"]
assert "A.2" in b07q and "光路由终端" in b07q and "尺寸" in b07q
print("=== B07 题面限定断言 ===")
print("  A.2 限定:", "A.2" in b07q, "| 光路由终端:", "光路由终端" in b07q, "| 尺寸:", "尺寸" in b07q)

json.dump({"dup_report": dup_report, "revision_ids": ids_out},
          open(WORK / "g03_revision_ids.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("saved:", WORK / "g03_revision_ids.json")
