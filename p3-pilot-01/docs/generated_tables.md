## 表 1　四组检索指标对照（22 题，K 上限 10）

| 方案 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 | NDCG@10 | Recall@10 | p50 (ms) | p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A BM25 Only | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 90 | 133 |
| B Vector Only | 0.727 | 0.864 | 0.909 | 0.955 | 0.802 | 0.835 | 0.955 | 76 | 93 |
| C Hybrid | 0.909 | 0.955 | 0.955 | 1.000 | 0.931 | 0.943 | 1.000 | 125 | 189 |
| D Hybrid + Rerank | 0.727 | 0.818 | 0.864 | 1.000 | 0.799 | 0.838 | 1.000 | 3293 | 3553 |
| A2 BM25 全库（诊断） | 0.727 | 0.818 | 0.955 | 0.955 | 0.802 | 0.841 | 0.955 | 112 | 151 |

> 补充指标 `required_evidence_coverage@10`（4 道 requires_all_evidence 题）：A BM25 Only=0.0、B Vector Only=0.875、C Hybrid=0.875、D Hybrid + Rerank=1.0、bm25_full_corpus=0.875

## 表 2　指标绝对变化（Δ）

| 对比 | ΔHit@1 | ΔHit@10 | ΔMRR@10 | ΔNDCG@10 | ΔRecall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| vector_only_vs_bm25_only | +0.727 | +0.955 | +0.802 | +0.835 | +0.955 |
| hybrid_vs_bm25_only | +0.909 | +1.000 | +0.931 | +0.943 | +1.000 |
| hybrid_rerank_vs_bm25_only | +0.727 | +1.000 | +0.799 | +0.838 | +1.000 |
| hybrid_rerank_vs_hybrid | -0.182 | +0.000 | -0.132 | -0.105 | +0.000 |
| bm25_only_vs_vector_only | -0.727 | -0.955 | -0.802 | -0.835 | -0.955 |
| hybrid_vs_vector_only | +0.182 | +0.045 | +0.129 | +0.108 | +0.045 |
| bm25_full_corpus_vs_bm25_only | +0.727 | +0.955 | +0.802 | +0.841 | +0.955 |

## 表 3　逐题首个相关 Chunk 名次（— 表示 Top10 内未命中）

| 题号 | 题型 | A BM25 | B Vector | C Hybrid | D Hybrid+Rerank | A2 BM25 全库 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| B01 | exact_entity | — | 1 | 1 | 1 | 1 |
| B02 | exact_entity | — | 1 | 1 | 1 | 1 |
| B03 | exact_entity | — | 5 | 7 | 2 | 1 |
| B04 | exact_entity | — | 1 | 1 | 1 | 2 |
| B05 | exact_entity | — | 1 | 1 | 1 | 1 |
| B06 | semantic | — | — | 1 | 7 | 4 |
| B07 | semantic | — | 2 | 1 | 2 | 1 |
| B09 | semantic | — | 2 | 1 | 1 | 1 |
| B12 | confusable | — | 1 | 1 | 1 | 5 |
| B13 | semantic | — | 1 | 1 | 1 | 2 |
| B14 | semantic | — | 3 | 3 | 9 | — |
| B15 | semantic | — | 9 | 1 | 5 | 1 |
| B16 | exact_entity | — | 1 | 1 | 1 | 1 |
| B17 | exact_entity | — | 1 | 1 | 1 | 1 |
| B18 | exact_entity | — | 1 | 1 | 1 | 1 |
| B19 | semantic | — | 1 | 1 | 1 | 1 |
| B20 | semantic | — | 1 | 1 | 1 | 1 |
| B21 | semantic | — | 1 | 1 | 1 | 1 |
| B22 | semantic | — | 1 | 1 | 8 | 5 |
| B25 | exact_entity | — | 1 | 1 | 1 | 1 |
| B26 | exact_entity | — | 1 | 1 | 1 | 1 |
| B27 | exact_entity | — | 1 | 1 | 1 | 1 |

## 表 4　Rerank 造成的逐题名次变化（仅列变化题）

| 题号 | C 名次 | D 名次 | 变化 | 查询（截断） |
| --- | ---: | ---: | ---: | --- |
| B03 | 7 | 2 | -5 | 智慧家庭全光组网产品技术规范的版本是什么？… |
| B06 | 1 | 7 | +6 | 《智慧家庭装维工程与管理职业技能等级标准》4.2 节中，智慧家庭工程… |
| B07 | 1 | 2 | +1 | 在《中国移动智慧家庭全光组网产品技术规范》附录 A.2 中，光路由终… |
| B14 | 3 | 9 | +6 | 在《智慧家庭装维工程与管理职业技能等级标准》表 1 中，中级人员在“… |
| B15 | 1 | 5 | +4 | 在《智慧家庭装维工程与管理职业技能等级标准》表 1 中，高级人员在“… |
| B22 | 1 | 8 | +7 | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0 第 4.8.… |

## 表 5　BM25 候选池诊断（生产 keyword 候选 = priority/updated_at 排序后 LIMIT 20）

| 题号 | token 命中 Chunk 数 | 候选池大小 | 相关 Chunk 是否在池内 |
| --- | ---: | ---: | --- |
| B01 | 125 | 20 | 否 |
| B02 | 447 | 20 | 否 |
| B03 | 146 | 20 | 是（1/1） |
| B04 | 432 | 20 | 否 |
| B05 | 420 | 20 | 否 |
| B06 | 437 | 20 | 否 |
| B07 | 447 | 20 | 否 |
| B09 | 420 | 20 | 否 |
| B12 | 439 | 20 | 否 |
| B13 | 429 | 20 | 否 |
| B14 | 440 | 20 | 否 |
| B15 | 440 | 20 | 否 |
| B16 | 444 | 20 | 否 |
| B17 | 446 | 20 | 否 |
| B18 | 446 | 20 | 否 |
| B19 | 342 | 20 | 否 |
| B20 | 446 | 20 | 否 |
| B21 | 447 | 20 | 否 |
| B22 | 443 | 20 | 否 |
| B25 | 326 | 20 | 否 |
| B26 | 440 | 20 | 否 |
| B27 | 320 | 20 | 否 |

## 表 6　失败归因（Top10 未命中）

| 题号 | 方案 | 失败阶段 | 说明 |
| --- | --- | --- | --- |
| B01 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B02 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B03 | A BM25 Only | filtered_by_threshold | 去掉 min_similarity_score / relative_score_threshold 后本应排第 5 |
| B04 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B05 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B06 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B06 | B Vector Only | filtered_by_threshold | 去掉 min_similarity_score / relative_score_threshold 后本应排第 13 |
| B07 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B09 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B12 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B13 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B14 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B14 | bm25_full_corpus | not_in_full_corpus_ranking | 全库 BM25 未进入 Top10 |
| B15 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B16 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B17 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B18 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B19 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B20 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B21 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B22 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B25 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B26 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |
| B27 | A BM25 Only | candidate_pool_miss | 相关 Chunk 没有进入该方法的候选池 |

