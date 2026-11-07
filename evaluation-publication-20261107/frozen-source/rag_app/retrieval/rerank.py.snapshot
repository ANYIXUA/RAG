"""检索结果重排模块。"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from rag_app.core.config import Settings
from rag_app.core.models import RetrievalResult


class Reranker(Protocol):
    """对候选检索结果进行二阶段重排。"""

    provider_name: str
    model_name: str
    enabled: bool

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        ...


class NoopReranker:
    """不启用重排时的占位实现。"""

    provider_name = "none"
    model_name = "none"
    enabled = False

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        del query
        if top_k <= 0:
            return []
        normalized: list[RetrievalResult] = []
        for result in results[:top_k]:
            base_score = result.score if result.retrieval_score is None else result.retrieval_score
            normalized.append(
                replace(
                    result,
                    retrieval_score=base_score,
                )
            )
        return normalized


class CrossEncoderReranker:
    """使用 SentenceTransformers CrossEncoder 对候选做相关性精排。"""

    provider_name = "cross-encoder"
    enabled = True

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "缺少重排依赖，请先执行: pip install -e \".[rerank]\" "
                "或 pip install sentence-transformers torch"
            ) from exc
        self.model_name = model_name
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        if top_k <= 0 or not results:
            return []
        pairs = [(query, result.chunk.text) for result in results]
        scores = self.model.predict(pairs)
        reranked: list[RetrievalResult] = []
        for result, rerank_score in zip(results, scores):
            base_score = result.score if result.retrieval_score is None else result.retrieval_score
            score_value = float(rerank_score)
            reranked.append(
                replace(
                    result,
                    score=score_value,
                    retrieval_score=base_score,
                    rerank_score=score_value,
                )
            )
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:top_k]


def create_reranker(settings: Settings) -> Reranker:
    provider = settings.rerank_provider.lower()
    if provider in {"none", "off", "disabled"}:
        return NoopReranker()
    if provider in {"cross-encoder", "cross_encoder", "crossencoder"}:
        return CrossEncoderReranker(settings.rerank_model)
    raise ValueError(f"Unsupported rerank provider: {settings.rerank_provider}")
