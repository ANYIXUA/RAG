# -*- coding: utf-8 -*-
"""g03 只读检查：retrieval_eval_20261103_134741.json 的结构与判分口径证据。
不修改任何文件。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

P = r"D:\AgentAIProgect\RAG\retrieval_eval_20261103_134741.json"
print("size bytes:", os.path.getsize(P))
d = json.load(open(P, encoding="utf-8"))


def walk(o, prefix="", depth=0, max_list=1):
    if depth > 4:
        return
    if isinstance(o, dict):
        for k, v in list(o.items())[:50]:
            if isinstance(v, (dict, list)):
                print(f"{prefix}{k}: <{type(v).__name__} len={len(v)}>")
                skip_keys = {"cases", "results", "chunks", "items",
                             "case_results", "top_results", "failures"}
                if depth < 2 and k not in skip_keys:
                    walk(v, prefix + "  ", depth + 1, max_list)
            else:
                print(f"{prefix}{k}: {repr(v)[:140]}")
    elif isinstance(o, list):
        print(f"{prefix}<list len={len(o)}>")
        if o and depth < 4:
            print(f"{prefix}[0]:")
            walk(o[0], prefix + "  ", depth + 1, max_list)


print("=== TOP STRUCTURE ===")
walk(d)

# 若存在 case_results，打印前 2 条的 expected 与 hit/rank 字段
cr = d.get("case_results")
if cr is None and isinstance(d, dict):
    for run in d.values():
        if isinstance(run, dict) and "case_results" in run:
            cr = run["case_results"]
            break
if cr:
    print("=== first 2 case_results (expected + hit/rank) ===")
    for c in cr[:2]:
        slim = {k: c.get(k) for k in ("query", "hit", "rank", "expected")}
        print(json.dumps(slim, ensure_ascii=False)[:1200])
    # 统计 expected 中多目标条目
    multi = [c for c in cr if isinstance(c.get("expected"), list) and len(c["expected"]) > 1]
    print("cases with >1 expected targets:", len(multi), "/", len(cr))
    if multi:
        print(json.dumps(multi[0]["expected"], ensure_ascii=False)[:800])
