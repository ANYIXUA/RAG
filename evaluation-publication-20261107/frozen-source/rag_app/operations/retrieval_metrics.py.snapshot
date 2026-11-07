"""按 Chunk ID 判定相关性的检索排序指标。

现有 ``rag_app.operations.evaluation`` 只用 ``source`` / ``section_title`` /
``text_contains`` 三字段定位首个命中位置，没有 Hit@K、NDCG、Recall@K，也无法
用 Gold 里已签核的 ``retrieval_relevant_chunk_ids`` 逐条核对。本模块只补齐这层
纯计算，不参与检索、不改动既有评测器行为。

口径（所有函数共用）：

- 相关性是二元的：chunk_id 在 ``relevant`` 集合内即相关，不区分程度。
- 一条查询可以有多个相关 Chunk；``relevant`` 是该查询完整的相关集合。
- 排序列表按名次从 1 开始；重复 ID 只按首次出现计分，避免同一 Chunk 重复抬高 DCG。
- ``k`` 为评估截断深度，先截断再计算；``k <= 0`` 视为无效深度，指标取 0。
- 只截断排序列表，不重新排序，也不做任何补位或平滑。
"""

from __future__ import annotations

import math
from collections.abc import Sequence

__all__ = [
    "coverage_at_k",
    "dedupe_preserving_order",
    "first_relevant_rank",
    "hit_at_k",
    "ndcg_at_k",
    "percentile",
    "recall_at_k",
    "reciprocal_rank_at_k",
    "summarize_ranking",
]


def dedupe_preserving_order(ranked: Sequence[str]) -> list[str]:
    """去掉重复 chunk_id，保留首次出现的名次。"""

    seen: set[str] = set()
    ordered: list[str] = []
    for chunk_id in ranked:
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        ordered.append(chunk_id)
    return ordered


def _normalized(
    ranked: Sequence[str],
    relevant: set[str],
    k: int,
) -> tuple[list[str], set[str]]:
    if k <= 0:
        return [], set()
    return dedupe_preserving_order(ranked)[:k], set(relevant)


def hit_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> bool:
    """Top-K 内是否至少命中一个相关 Chunk。"""

    truncated, relevant_ids = _normalized(ranked, relevant, k)
    return any(chunk_id in relevant_ids for chunk_id in truncated)


def first_relevant_rank(
    ranked: Sequence[str],
    relevant: set[str],
    k: int,
) -> int | None:
    """Top-K 内首个相关 Chunk 的名次（1 起），未命中返回 None。"""

    truncated, relevant_ids = _normalized(ranked, relevant, k)
    for rank, chunk_id in enumerate(truncated, start=1):
        if chunk_id in relevant_ids:
            return rank
    return None


def reciprocal_rank_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """Top-K 内首个相关 Chunk 的倒数名次，未命中记 0。"""

    rank = first_relevant_rank(ranked, relevant, k)
    if rank is None:
        return 0.0
    return 1.0 / rank


def ndcg_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """二元增益的 NDCG@K。

    ``DCG = sum_{i=1..k} rel_i / log2(i + 1)``，
    ``IDCG = sum_{i=1..min(|relevant|, k)} 1 / log2(i + 1)``。
    ``k <= 0`` 或相关集合为空时返回 0。
    """

    truncated, relevant_ids = _normalized(ranked, relevant, k)
    if not relevant_ids or not truncated:
        return 0.0
    dcg = 0.0
    for rank, chunk_id in enumerate(truncated, start=1):
        if chunk_id in relevant_ids:
            dcg += 1.0 / math.log2(rank + 1)
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg


def recall_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """Top-K 覆盖到的相关 Chunk 占完整相关集合的比例。"""

    truncated, relevant_ids = _normalized(ranked, relevant, k)
    if not relevant_ids:
        return 0.0
    return len(set(truncated) & relevant_ids) / len(relevant_ids)


def coverage_at_k(ranked: Sequence[str], required: set[str], k: int) -> float:
    """Top-K 对“必须命中证据集合”的覆盖率（补充指标）。

    仅用于 ``requires_all_evidence`` 的题：该值为 1 才表示所有必需证据同时
    出现在 Top-K 内，单命中即可的现象不会被误读。
    """

    truncated, required_ids = _normalized(ranked, required, k)
    if not required_ids:
        return 0.0
    return len(set(truncated) & required_ids) / len(required_ids)


def percentile(values: Sequence[float], q: float) -> float:
    """线性插值分位数，口径与 ``evaluation._percentile`` 保持一致。"""

    if not values:
        return 0.0
    if q <= 0:
        return min(values)
    if q >= 1:
        return max(values)
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize_ranking(
    ranked: Sequence[str],
    relevant: set[str],
    k_values: Sequence[int] = (1, 3, 5, 10),
    max_k: int = 10,
) -> dict[str, float | int | bool | None | dict[str, float | bool]]:
    """汇总一条查询在各截断深度上的指标。"""

    return {
        "hit": {f"hit@{k}": hit_at_k(ranked, relevant, k) for k in k_values},
        "reciprocal_rank": reciprocal_rank_at_k(ranked, relevant, max_k),
        "ndcg": ndcg_at_k(ranked, relevant, max_k),
        "recall": recall_at_k(ranked, relevant, max_k),
        "first_relevant_rank": first_relevant_rank(ranked, relevant, max_k),
    }
