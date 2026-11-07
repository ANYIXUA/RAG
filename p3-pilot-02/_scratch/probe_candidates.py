#!/usr/bin/env python
"""P3-Pilot-02 诊断：BM25 keyword 候选池召回链路。

只读。逐题比较四种候选生成方式，定位 priority / updated_at / ILIKE OR /
提前 LIMIT 各自对候选召回的影响。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT02 = HERE.parent
REPO = PILOT02.parent
sys.path.insert(0, str(REPO / "p3-pilot-01"))

import psycopg  # noqa: E402
import run_pilot as rp  # noqa: E402

from rag_app.core.text_utils import tokenize_for_keyword_search  # noqa: E402
from rag_app.indexing.vector_store import (  # noqa: E402
    VectorRecord,
    _bm25_scores,
    _normalize_positive_scores,
)
from rag_app.core.models import Chunk  # noqa: E402


def fetch_rows(dsn: str, tokens: list[str], order_sql: str, limit: int | None = None):
    predicates = " OR ".join(["chunk_text ILIKE %s"] * len(tokens))
    params: list = ["default", *[f"%{t}%" for t in tokens]]
    sql = (
        "SELECT chunk_id, chunk_text, metadata FROM rag_knowledge_chunks "
        "WHERE collection_name = %s AND status = 'active' AND ("
        + predicates
        + f") ORDER BY {order_sql}"
    )
    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)
    with psycopg.connect(dsn, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()


def to_records(rows) -> list[VectorRecord]:
    return [
        VectorRecord(
            chunk=Chunk(id=row[0], document_id="", text=row[1], metadata=row[2] or {}),
            embedding=[],
        )
        for row in rows
    ]


def bm25_top(records: list[VectorRecord], query: str, top_n: int) -> list[str]:
    scores = _bm25_scores(tokenize_for_keyword_search(query), records)
    normalized = _normalize_positive_scores(scores)
    ordered = sorted(
        ((cid, s) for cid, s in normalized.items() if s > 0),
        key=lambda item: item[1],
        reverse=True,
    )
    return [cid for cid, _ in ordered[:top_n]]


def rank_of(ids: list[str], relevant: set[str]) -> list[int]:
    out = []
    for i, cid in enumerate(ids, start=1):
        if cid in relevant:
            out.append(i)
    return out


def main() -> int:
    settings, dsn = rp.build_settings()
    cases, _ = rp.load_gold()
    corpus, _ = rp.load_corpus()
    corpus_records = rp.build_corpus_records(corpus)
    corpus_ids = set(corpus)

    with psycopg.connect(dsn, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), COUNT(DISTINCT priority), COUNT(DISTINCT updated_at), "
                "MIN(priority), MAX(priority), MIN(updated_at), MAX(updated_at) "
                "FROM rag_knowledge_chunks WHERE collection_name = %s AND status = 'active'",
                ("default",),
            )
            stats = cur.fetchone()
            cur.execute(
                "SELECT priority, COUNT(*) FROM rag_knowledge_chunks "
                "WHERE collection_name = %s AND status = 'active' GROUP BY priority ORDER BY priority",
                ("default",),
            )
            priority_dist = cur.fetchall()
            cur.execute(
                "SELECT updated_at, COUNT(*) FROM rag_knowledge_chunks "
                "WHERE collection_name = %s AND status = 'active' GROUP BY updated_at ORDER BY updated_at",
                ("default",),
            )
            updated_dist = cur.fetchall()

    db_stats = {
        "active_chunks": stats[0],
        "distinct_priority": stats[1],
        "distinct_updated_at": stats[2],
        "priority_min": stats[3],
        "priority_max": stats[4],
        "updated_at_min": stats[5].isoformat(),
        "updated_at_max": stats[6].isoformat(),
        "priority_distribution": priority_dist,
        "updated_at_distinct_values": len(updated_dist),
    }

    per_case = []
    summary = {
        "old_pool_has_relevant": 0,
        "fix_all_pool_has_relevant": 0,
        "fix_oversample_pool_has_relevant": 0,
        "a2_top10_hit": 0,
        "fix_all_top10_hit": 0,
        "old_top10_hit": 0,
    }
    for case in cases:
        query = case["query"]
        relevant = set(case["relevant_chunk_ids"])
        tokens = tokenize_for_keyword_search(query)[:12]
        match_count_expr = " + ".join(
            ["(CASE WHEN chunk_text ILIKE %s THEN 1 ELSE 0 END)"] * len(tokens)
        )
        # 参数顺序：collection, 谓词参数, 排序 CASE 参数
        predicates = " OR ".join(["chunk_text ILIKE %s"] * len(tokens))

        def fetch(tokens_list, order_sql, limit):
            sql = (
                "SELECT chunk_id, chunk_text, metadata FROM rag_knowledge_chunks "
                "WHERE collection_name = %s AND status = 'active' AND ("
                + predicates
                + f") ORDER BY {order_sql}"
            )
            params: list = ["default", *[f"%{t}%" for t in tokens_list]]
            if "CASE" in order_sql:
                params.extend([f"%{t}%" for t in tokens_list])
            if limit is not None:
                sql += " LIMIT %s"
                params.append(limit)
            with psycopg.connect(dsn, connect_timeout=10) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, tuple(params))
                    return cur.fetchall()

        old_rows = fetch(tokens, "priority DESC, updated_at DESC", 20)
        all_rows = fetch(tokens, "priority DESC, updated_at DESC", None)
        oversample_rows = fetch(
            tokens,
            f"({match_count_expr}) DESC, priority DESC, updated_at DESC",
            max(200, 20),
        )
        match_rows = fetch(
            tokens,
            f"({match_count_expr}) DESC, priority DESC, updated_at DESC",
            None,
        )

        old_ids = [r[0] for r in old_rows]
        all_records = to_records(all_rows)
        all_ids = [r[0] for r in all_rows]
        over_records = to_records(oversample_rows)
        over_ids = [r[0] for r in oversample_rows]

        old_top = bm25_top(to_records(old_rows), query, 20)
        all_top = bm25_top(all_records, query, 20)
        over_top = bm25_top(over_records, query, 20)
        a2_top = bm25_top(corpus_records, query, 20)

        # 相关 Chunk 在 ILIKE 全命中集合里按 match_count 的位次
        matched_rank = {}
        for i, row in enumerate(match_rows, start=1):
            if row[0] in relevant:
                matched_rank[row[0]] = i

        matched_counts = {}
        for row in all_rows:
            if row[0] in relevant:
                text = row[1]
                matched_counts[row[0]] = sum(1 for t in tokens if t.lower() in text.lower())

        record = {
            "gold_case_id": case["gold_case_id"],
            "query": query,
            "tokens": tokens,
            "token_match_count": len(all_rows),
            "old_pool_ids": old_ids,
            "old_pool_has_relevant": sorted(relevant & set(old_ids)),
            "old_top10_ranks": rank_of(old_top, relevant),
            "fix_all_top10_ranks": rank_of(all_top, relevant),
            "fix_oversample_top10_ranks": rank_of(over_top, relevant),
            "a2_top10_ranks": rank_of(a2_top, relevant),
            "relevant_match_count": matched_counts,
            "relevant_match_count_rank": matched_rank,
            "relevant_in_oversample": sorted(relevant & set(over_ids)),
            "relevant_in_all": sorted(relevant & set(all_ids)),
        }
        per_case.append(record)
        summary["old_pool_has_relevant"] += bool(record["old_pool_has_relevant"])
        summary["fix_all_pool_has_relevant"] += bool(relevant & set(all_ids))
        summary["fix_oversample_pool_has_relevant"] += bool(relevant & set(over_ids))
        summary["old_top10_hit"] += bool(record["old_top10_ranks"])
        summary["fix_all_top10_hit"] += bool(record["fix_all_top10_ranks"])
        summary["a2_top10_hit"] += bool(record["a2_top10_ranks"])

    output = {
        "db_stats": db_stats,
        "summary": summary,
        "case_count": len(per_case),
        "per_case": per_case,
    }
    out = PILOT02 / "runs" / "candidate_probe_before.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"db_stats": db_stats, "summary": summary}, ensure_ascii=False, indent=2))
    for c in per_case:
        print(
            f"{c['gold_case_id']}: match={c['token_match_count']:3d} "
            f"old_pool={c['old_pool_has_relevant'] or '-'} "
            f"old_top10={c['old_top10_ranks'] or '-'} "
            f"all_top10={c['fix_all_top10_ranks'] or '-'} "
            f"over_top10={c['fix_oversample_top10_ranks'] or '-'} "
            f"a2_top10={c['a2_top10_ranks'] or '-'} "
            f"matchrank={c['relevant_match_count_rank']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
