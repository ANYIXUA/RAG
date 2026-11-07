#!/usr/bin/env python
"""模拟：keyword 候选先按全命中集 BM25 选 TopN，再与语义 TopN 融合。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT02 = HERE.parent
REPO = PILOT02.parent
sys.path.insert(0, str(REPO / "p3-pilot-01"))
sys.path.insert(0, str(REPO))

import run_pilot as rp  # noqa: E402

from rag_app.core.text_utils import tokenize_for_keyword_search  # noqa: E402
from rag_app.indexing.embeddings import create_embedder  # noqa: E402
from rag_app.indexing.vector_store import (  # noqa: E402
    _bm25_scores,
    _merge_records,
    _rank_vector_records,
    create_vector_store,
)
from rag_app.operations.retrieval_metrics import (  # noqa: E402
    first_relevant_rank,
    hit_at_k,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)


def keyword_top(store, query: str, n: int, scan_limit: int):
    records = store._query_keyword_candidates(query, scan_limit=scan_limit)
    scores = _bm25_scores(tokenize_for_keyword_search(query), records)
    ordered = sorted(
        ((cid, s) for cid, s in scores.items() if s > 0),
        key=lambda item: item[1],
        reverse=True,
    )[:n]
    ids = {cid for cid, _ in ordered}
    return [record for record in records if record.chunk.id in ids]


def main() -> int:
    settings, _ = rp.build_settings()
    cases, _ = rp.load_gold()
    corpus, _ = rp.load_corpus()
    store = create_vector_store(settings)
    embedder = create_embedder(settings)
    records_by_id = {r.chunk.id: r for r in rp.build_corpus_records(corpus)}

    out = []
    for case in cases:
        query = case["query"]
        vector = embedder.embed([query])[0]
        sem, sem_scores = store._search_semantic_candidates(vector, rp.RETRIEVAL_TOP_K)
        kw = keyword_top(store, query, settings.retrieval_candidate_k, min(447, 2000))
        merged = _merge_records(sem, kw)

        results = {}
        for mode, recs in (("bm25", kw), ("hybrid", merged)):
            ranked = _rank_vector_records(
                records=recs,
                query_embedding=vector,
                query_text=query,
                top_k=rp.RETRIEVAL_TOP_K,
                min_score=settings.min_similarity_score,
                relative_score_threshold=settings.relative_score_threshold,
                mode=mode,
                semantic_weight=settings.semantic_weight,
                keyword_weight=settings.bm25_weight,
                bm25_weight=settings.bm25_weight,
                candidate_k=settings.retrieval_candidate_k,
                semantic_scores=sem_scores if mode == "hybrid" else None,
            )
            results[mode] = [r.chunk.id for r in ranked]

        out.append(
            {
                "gold_case_id": case["gold_case_id"],
                "batch_id": case["batch_id"],
                "query": query,
                "relevant": case["relevant_chunk_ids"],
                "bm25": results["bm25"],
                "hybrid": results["hybrid"],
            }
        )

    summary = {}
    for mode in ("bm25", "hybrid"):
        vals = []
        for row in out:
            ranked = row[mode]
            rel = set(row["relevant"])
            vals.append(
                {
                    "hit1": hit_at_k(ranked, rel, 1),
                    "hit10": hit_at_k(ranked, rel, 10),
                    "mrr": reciprocal_rank_at_k(ranked, rel, 10),
                    "ndcg": ndcg_at_k(ranked, rel, 10),
                    "recall": recall_at_k(ranked, rel, 10),
                    "rank": first_relevant_rank(ranked, rel, 10),
                }
            )
        summary[mode] = {
            k: round(sum(v[k] for v in vals) / len(vals), 6)
            for k in ("hit1", "hit10", "mrr", "ndcg", "recall")
        }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    (PILOT02 / "runs").mkdir(parents=True, exist_ok=True)
    (PILOT02 / "runs" / "variant_two_stage_sim.json").write_text(
        json.dumps({"summary": summary, "cases": out}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for row in out:
        print(row["batch_id"], "bm25", row["bm25"][:1], "hybrid", row["hybrid"][:1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
