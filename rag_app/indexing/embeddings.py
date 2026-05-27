"""Embedding 向量化适配。"""

from __future__ import annotations

from typing import Protocol

from rag_app.core.config import Settings


class Embedder(Protocol):
    """将文本转换为稠密数值向量。"""

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class OpenAIEmbedder:
    """OpenAI 兼容 Embedding 适配器。"""

    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str | None = None,
        dimensions: int | None = None,
        batch_size: int = 10,
    ) -> None:
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Install OpenAI support with: pip install -e \".[openai]\""
            ) from exc
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            kwargs = {"model": self.model, "input": batch}
            if self.dimensions is not None:
                kwargs["dimensions"] = self.dimensions
            response = self.client.embeddings.create(**kwargs)
            embeddings.extend(_ordered_embeddings(response.data))
        return embeddings


def create_embedder(settings: Settings) -> Embedder:
    provider = settings.embedding_provider.lower()
    if provider == "openai":
        return OpenAIEmbedder(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            base_url=settings.openai_base_url,
            dimensions=settings.embedding_dimension,
            batch_size=settings.embedding_batch_size,
        )
    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")


def _ordered_embeddings(data) -> list[list[float]]:
    indexed = [
        item
        for item in data
        if getattr(item, "index", None) is not None
    ]
    if len(indexed) == len(data):
        data = sorted(data, key=lambda item: item.index)
    return [item.embedding for item in data]
