"""诊断：BM25-only 为什么在 22 题上全部未命中。"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
os.chdir(REPO)

env = {}
for line in open(".env", encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip()
dsn = re.sub(r"@[^/@:]+:\d+/", "@127.0.0.1:15432/", env["RAG_OPS_POSTGRES_DSN"])

import psycopg

from rag_app.core.models import Chunk
from rag_app.core.text_utils import tokenize_for_keyword_search
from rag_app.indexing.vector_store import (
    VectorRecord,
    _bm25_scores,
    _normalize_positive_scores,
)

# 从 smoke 运行结果里取出 22 条评测题（同一题四个方法重复出现）
gold = {}
for line in open("p3-pilot-01/_scratch/smoke/rankings.jsonl", encoding="utf-8"):
    rec = json.loads(line)
    gold[rec["gold_case_id"]] = {
        "query": rec["query"],
        "relevant_chunk_ids": rec["relevant_chunk_ids"],
        "batch_id": rec["batch_id"],
    }
print("cases", len(gold))

with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "select chunk_id, document_id, chunk_text, metadata, priority, updated_at "
            "from rag_knowledge_chunks where collection_name='default' and status='active'"
        )
        rows = cur.fetchall()

all_ids = [r[0] for r in rows]
texts = {r[0]: r[2] for r in rows}
prio = {r[0]: r[4] for r in rows}
print("priority_values", sorted(set(prio.values())), "chunks", len(all_ids))

# 生产 keyword 候选顺序：priority DESC, updated_at DESC
ordered = [r[0] for r in sorted(rows, key=lambda r: (r[4], r[5]), reverse=True)]

hit_any = 0
for case in gold.values():
    query = case["query"]
    relevant = case["relevant_chunk_ids"]
    tokens = tokenize_for_keyword_search(query)[:12]
    matching = {cid for cid in all_ids if any(t in texts[cid].lower() for t in tokens)}
    rel_match = {cid: (cid in matching) for cid in relevant}
    kw_pool = [cid for cid in ordered if cid in matching][:20]
    in_pool = [c in kw_pool for c in relevant]
    print("=" * 78)
    print(case["batch_id"], "|", query[:58])
    print("  tokens:", tokens)
    print("  token_matching_chunks:", len(matching), "/", len(all_ids))
    print("  relevant_token_match:", rel_match, "in_kw_pool20:", in_pool)
    if any(in_pool):
        hit_any += 1
        recs = [
            VectorRecord(
                chunk=Chunk(
                    id=r[0],
                    document_id=r[1],
                    text=r[2],
                    metadata=r[3] if isinstance(r[3], dict) else json.loads(r[3]),
                ),
                embedding=[],
            )
            for r in rows
            if r[0] in set(kw_pool)
        ]
        scores = _bm25_scores(tokens, recs)
        norm = _normalize_positive_scores(scores)
        ranked = sorted(norm.items(), key=lambda kv: kv[1], reverse=True)
        for cid in relevant:
            if cid in kw_pool:
                pos = [i for i, (k, _) in enumerate(ranked, 1) if k == cid]
                print("   ", cid, "bm25_rank", pos, "norm", round(norm.get(cid, 0), 4))
        print("    top3:", [(k, round(v, 3)) for k, v in ranked[:3]])
print("=" * 78)
print("cases_with_relevant_in_kw_pool", hit_any, "of", len(gold))
