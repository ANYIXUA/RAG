#!/usr/bin/env python
"""P3-Pilot-01 结果分析：逐题排名差异、失败归因、可读表格。

只读操作：重新查询向量库是为了拿到**生产候选池**（keyword 池 / 语义池）与
**去掉阈值后的排序**，用来把“没命中”拆成可验证的阶段，而不是猜测原因。
不会写数据库，也不会修改任何检索代码。
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_pilot as rp  # noqa: E402

K = 10


def load_rankings(run_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    with (run_dir / "rankings.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            rows[(record["method"], record["gold_case_id"])] = record
    return rows


def cases_from(rows: dict[tuple[str, str], dict[str, Any]]) -> "OrderedDict[str, dict]":
    ordered: "OrderedDict[str, dict]" = OrderedDict()
    for record in rows.values():
        ordered.setdefault(
            record["gold_case_id"],
            {
                "gold_case_id": record["gold_case_id"],
                "batch_id": record["batch_id"],
                "query": record["query"],
                "question_type": record["question_type"],
                "requires_all_evidence": record["requires_all_evidence"],
                "relevant_chunk_ids": record["relevant_chunk_ids"],
                "required_evidence_chunk_ids": record.get("required_evidence_chunk_ids", []),
            },
        )
    return ordered


def first_rank(ranked: list[str], relevant: list[str], k: int = K) -> int | None:
    for index, chunk_id in enumerate(ranked[:k], start=1):
        if chunk_id in relevant:
            return index
    return None


def attribute(
    ranked: list[str],
    unfiltered: list[str],
    pool_ids: set[str],
    relevant: list[str],
) -> dict[str, Any]:
    """把“Top10 内没有相关 Chunk”拆解到具体阶段。"""

    if first_rank(ranked, relevant) is not None:
        return {"stage": "hit", "detail": None}
    in_pool = [cid for cid in relevant if cid in pool_ids]
    if not in_pool:
        return {
            "stage": "candidate_pool_miss",
            "detail": "相关 Chunk 没有进入该方法的候选池",
        }
    unfiltered_rank = first_rank(unfiltered, relevant, len(unfiltered) or 1)
    if unfiltered_rank is None:
        return {
            "stage": "scored_below_pool_cutoff",
            "detail": "相关 Chunk 在池内但没有进入去阈值后的返回列表",
        }
    return {
        "stage": "filtered_by_threshold",
        "detail": f"去掉 min_similarity_score / relative_score_threshold 后本应排第 {unfiltered_rank}",
        "unfiltered_rank": unfiltered_rank,
    }


def main() -> int:
    run_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "p3-pilot-01/runs/run1")
    out_json = Path(sys.argv[2] if len(sys.argv) > 2 else "p3-pilot-01/runs/analysis.json")
    out_md = Path(sys.argv[3] if len(sys.argv) > 3 else "p3-pilot-01/docs/generated_tables.md")

    from rag_app.indexing.embeddings import create_embedder
    from rag_app.indexing.vector_store import create_vector_store

    rows = load_rankings(run_dir)
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    settings, dsn = rp.build_settings()
    store = create_vector_store(settings)
    embedder = create_embedder(settings)
    cases = cases_from(rows)

    import psycopg

    method_modes = {}
    for (method, _), record in rows.items():
        method_modes[method] = record["mode"]

    per_case: dict[str, Any] = {}
    for case_id, case in cases.items():
        vector = embedder.embed([case["query"]])[0]
        semantic_pool, semantic_scores = store._search_semantic_candidates(vector, rp.RETRIEVAL_TOP_K)
        keyword_pool = store._query_keyword_candidates(case["query"], rp.RETRIEVAL_TOP_K)
        semantic_pool_ids = {record.chunk.id for record in semantic_pool}
        keyword_pool_ids = {record.chunk.id for record in keyword_pool}

        # 关键词 token 命中总数（复制生产谓词，仅用于诊断数量级）
        from rag_app.core.text_utils import tokenize_for_keyword_search

        tokens = tokenize_for_keyword_search(case["query"])[:12]
        with psycopg.connect(dsn, connect_timeout=10) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM rag_knowledge_chunks "
                    "WHERE collection_name = %s AND status = 'active' AND ("
                    + " OR ".join(["chunk_text ILIKE %s"] * len(tokens))
                    + ")",
                    ("default", *[f"%{token}%" for token in tokens]),
                )
                token_match_count = cursor.fetchone()[0]

        unfiltered: dict[str, list[str]] = {}
        for method, mode in method_modes.items():
            if mode == "bm25_full_corpus":
                continue
            results = store.search(
                query_embedding=vector,
                query_text=case["query"],
                top_k=rp.RETRIEVAL_TOP_K,
                min_score=None,
                relative_score_threshold=None,
                mode=mode,
                semantic_weight=settings.semantic_weight,
                keyword_weight=settings.bm25_weight,
                bm25_weight=settings.bm25_weight,
                candidate_k=settings.retrieval_candidate_k,
                tenant_id=None,
                permission_tags=None,
            )
            unfiltered[method] = [item.chunk.id for item in results]

        per_method: dict[str, Any] = {}
        for method, mode in method_modes.items():
            record = rows[(method, case_id)]
            ranked = record["ranked_chunk_ids"]
            relevant = case["relevant_chunk_ids"]
            if mode == "bm25_full_corpus":
                pool_ids = set()
                stage = attribute(ranked, ranked, set(ranked), relevant)
                stage = (
                    {"stage": "hit", "detail": None}
                    if first_rank(ranked, relevant) is not None
                    else {"stage": "not_in_full_corpus_ranking", "detail": "全库 BM25 未进入 Top10"}
                )
            else:
                if mode == "bm25":
                    pool_ids = keyword_pool_ids
                elif mode == "semantic":
                    pool_ids = semantic_pool_ids
                else:
                    pool_ids = semantic_pool_ids | keyword_pool_ids
                stage = attribute(ranked, unfiltered.get(method, []), pool_ids, relevant)
            per_method[method] = {
                "ranked_chunk_ids": ranked,
                "first_relevant_rank": first_rank(ranked, relevant),
                "relevant_ranks": {
                    cid: ranked.index(cid) + 1 for cid in relevant if cid in ranked
                },
                "ndcg_at_10": record["metrics"]["ndcg_at_10"],
                "recall_at_10": record["metrics"]["recall_at_10"],
                "retrieval_latency_ms": record["metrics"]["retrieval_latency_ms"],
                "failure": stage,
            }

        per_case[case_id] = {
            **case,
            "diagnostics": {
                "keyword_tokens": tokens,
                "token_match_count": token_match_count,
                "keyword_pool_size": len(keyword_pool_ids),
                "keyword_pool_contains_relevant": {
                    cid: cid in keyword_pool_ids for cid in case["relevant_chunk_ids"]
                },
                "semantic_pool_size": len(semantic_pool_ids),
                "semantic_pool_contains_relevant": {
                    cid: cid in semantic_pool_ids for cid in case["relevant_chunk_ids"]
                },
                "semantic_score_of_relevant": {
                    cid: round(semantic_scores.get(cid, 0.0), 6)
                    for cid in case["relevant_chunk_ids"]
                },
            },
            "methods": per_method,
        }

    # ---- 汇总统计 ----
    method_names = list(method_modes)
    hit_counts = {}
    for method in method_names:
        hit_counts[method] = sum(
            1 for case in per_case.values() if case["methods"][method]["first_relevant_rank"] is not None
        )
    rerank_rank_changes = []
    for case in per_case.values():
        c = case["methods"]["hybrid"]["first_relevant_rank"]
        d = case["methods"]["hybrid_rerank"]["first_relevant_rank"]
        if c == d:
            continue
        rerank_rank_changes.append(
            {
                "batch_id": case["batch_id"],
                "gold_case_id": case["gold_case_id"],
                "query": case["query"],
                "hybrid_rank": c,
                "hybrid_rerank_rank": d,
                "delta": (None if c is None or d is None else d - c),
            }
        )

    analysis = {
        "run_dir": str(run_dir),
        "cases": len(per_case),
        "methods": method_names,
        "hit_at_10_counts": hit_counts,
        "rerank_rank_changes": rerank_rank_changes,
        "keyword_pool": {
            "cases_with_relevant_in_pool": sum(
                1
                for case in per_case.values()
                if any(case["diagnostics"]["keyword_pool_contains_relevant"].values())
            ),
            "pool_size": sorted(
                {case["diagnostics"]["keyword_pool_size"] for case in per_case.values()}
            ),
            "token_match_count_range": [
                min(case["diagnostics"]["token_match_count"] for case in per_case.values()),
                max(case["diagnostics"]["token_match_count"] for case in per_case.values()),
            ],
            "corpus_chunks": 447,
        },
        "semantic_pool": {
            "cases_with_relevant_in_pool": sum(
                1
                for case in per_case.values()
                if any(case["diagnostics"]["semantic_pool_contains_relevant"].values())
            )
        },
        "per_case": per_case,
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- Markdown 表 ----
    lines: list[str] = []
    add = lines.append

    add("## 表 1　四组检索指标对照（22 题，K 上限 10）")
    add("")
    add("| 方案 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 | NDCG@10 | Recall@10 | p50 (ms) | p95 (ms) |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    labels = {
        "bm25_only": "A BM25 Only",
        "vector_only": "B Vector Only",
        "hybrid": "C Hybrid",
        "hybrid_rerank": "D Hybrid + Rerank",
    }
    for method in ("bm25_only", "vector_only", "hybrid", "hybrid_rerank"):
        if method not in metrics["metrics"]:
            continue
        m = metrics["metrics"][method]
        add(
            f"| {labels[method]} | {m['hit@1']:.3f} | {m['hit@3']:.3f} | {m['hit@5']:.3f} | "
            f"{m['hit@10']:.3f} | {m['mrr@10']:.3f} | {m['ndcg@10']:.3f} | {m['recall@10']:.3f} | "
            f"{m['latency_p50_ms']:.0f} | {m['latency_p95_ms']:.0f} |"
        )
    for method, m in metrics.get("supplementary_metrics", {}).items():
        add(
            f"| {m['method_key']} BM25 全库（诊断） | {m['hit@1']:.3f} | {m['hit@3']:.3f} | "
            f"{m['hit@5']:.3f} | {m['hit@10']:.3f} | {m['mrr@10']:.3f} | {m['ndcg@10']:.3f} | "
            f"{m['recall@10']:.3f} | {m['latency_p50_ms']:.0f} | {m['latency_p95_ms']:.0f} |"
        )
    add("")
    add("> 补充指标 `required_evidence_coverage@10`（4 道 requires_all_evidence 题）："
        + "、".join(
            f"{labels.get(k, k)}={v['required_evidence_coverage@10']}"
            for k, v in {**metrics["metrics"], **metrics.get("supplementary_metrics", {})}.items()
        ))
    add("")

    add("## 表 2　指标绝对变化（Δ）")
    add("")
    add("| 对比 | ΔHit@1 | ΔHit@10 | ΔMRR@10 | ΔNDCG@10 | ΔRecall@10 |")
    add("| --- | ---: | ---: | ---: | ---: | ---: |")
    for name, block in metrics["deltas"].items():
        add(
            f"| {name} | {block['hit@1']['absolute']:+.3f} | {block['hit@10']['absolute']:+.3f} | "
            f"{block['mrr@10']['absolute']:+.3f} | {block['ndcg@10']['absolute']:+.3f} | "
            f"{block['recall@10']['absolute']:+.3f} |"
        )
    add("")

    add("## 表 3　逐题首个相关 Chunk 名次（— 表示 Top10 内未命中）")
    add("")
    add("| 题号 | 题型 | A BM25 | B Vector | C Hybrid | D Hybrid+Rerank | A2 BM25 全库 |")
    add("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for case_id, case in per_case.items():
        cells = []
        for method in ("bm25_only", "vector_only", "hybrid", "hybrid_rerank", "bm25_full_corpus"):
            if method not in case["methods"]:
                cells.append("—")
                continue
            rank = case["methods"][method]["first_relevant_rank"]
            cells.append("—" if rank is None else str(rank))
        add(
            f"| {case['batch_id']} | {case['question_type']} | "
            + " | ".join(cells)
            + " |"
        )
    add("")

    add("## 表 4　Rerank 造成的逐题名次变化（仅列变化题）")
    add("")
    add("| 题号 | C 名次 | D 名次 | 变化 | 查询（截断） |")
    add("| --- | ---: | ---: | ---: | --- |")
    if not rerank_rank_changes:
        add("| — | — | — | — | 无变化 |")
    for item in rerank_rank_changes:
        c = "—" if item["hybrid_rank"] is None else item["hybrid_rank"]
        d = "—" if item["hybrid_rerank_rank"] is None else item["hybrid_rerank_rank"]
        delta = "—" if item["delta"] is None else f"{item['delta']:+d}"
        add(f"| {item['batch_id']} | {c} | {d} | {delta} | {item['query'][:34]}… |")
    add("")

    add("## 表 5　BM25 候选池诊断（生产 keyword 候选 = priority/updated_at 排序后 LIMIT 20）")
    add("")
    add("| 题号 | token 命中 Chunk 数 | 候选池大小 | 相关 Chunk 是否在池内 |")
    add("| --- | ---: | ---: | --- |")
    for case_id, case in per_case.items():
        diag = case["diagnostics"]
        inside = [cid for cid, ok in diag["keyword_pool_contains_relevant"].items() if ok]
        add(
            f"| {case['batch_id']} | {diag['token_match_count']} | {diag['keyword_pool_size']} | "
            f"{'是（' + str(len(inside)) + '/' + str(len(case['relevant_chunk_ids'])) + '）' if inside else '否'} |"
        )
    add("")

    add("## 表 6　失败归因（Top10 未命中）")
    add("")
    add("| 题号 | 方案 | 失败阶段 | 说明 |")
    add("| --- | --- | --- | --- |")
    anything = False
    for case_id, case in per_case.items():
        for method in ("bm25_only", "vector_only", "hybrid", "hybrid_rerank", "bm25_full_corpus"):
            if method not in case["methods"]:
                continue
            failure = case["methods"][method]["failure"]
            if failure["stage"] == "hit":
                continue
            anything = True
            add(
                f"| {case['batch_id']} | {labels.get(method, method)} | {failure['stage']} | "
                f"{failure['detail'] or ''} |"
            )
    if not anything:
        add("| — | — | — | 无 |")
    add("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "analysis": str(out_json),
                "tables": str(out_md),
                "hit_at_10_counts": hit_counts,
                "keyword_pool": analysis["keyword_pool"],
                "semantic_pool": analysis["semantic_pool"],
                "rerank_rank_change_count": len(rerank_rank_changes),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
