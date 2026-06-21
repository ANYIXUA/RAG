"""RAG 流程编排。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from rag_app.core.config import Settings
from rag_app.indexing.embeddings import Embedder, create_embedder
from rag_app.retrieval.llm import AnswerGenerator, create_answer_generator
from rag_app.core.models import RAGAnswer, UserContext
from rag_app.retrieval.online import OnlineQueryProcessor
from rag_app.indexing.vector_store import VectorStore, create_vector_store


class RAGPipeline:
    """协调在线检索和回答生成；离线构建统一交给 OfflineKnowledgeBuilder。"""

    def __init__(
        self,
        settings: Settings,
        embedder: Embedder | None = None,
        answer_generator: AnswerGenerator | None = None,
        vector_store: VectorStore | None = None,
        online_processor: OnlineQueryProcessor | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or create_embedder(settings)
        self.answer_generator = answer_generator or create_answer_generator(settings)
        self.vector_store = vector_store or create_vector_store(settings)
        self.online_processor = online_processor or OnlineQueryProcessor(
            settings=self.settings,
            embedder=self.embedder,
            answer_generator=self.answer_generator,
            vector_store=self.vector_store,
        )

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "RAGPipeline":
        return cls(Settings.from_env(base_dir=base_dir))

    def query(
        self,
        question: str,
        top_k: int | None = None,
        session_id: str | None = None,
        user_context: UserContext | None = None,
    ) -> RAGAnswer:
        return self.online_processor.process(
            question,
            top_k=top_k,
            session_id=session_id,
            user_context=user_context,
        )

    def stream_query(
        self,
        question: str,
        top_k: int | None = None,
        session_id: str | None = None,
        user_context: UserContext | None = None,
    ) -> Iterator[dict[str, Any]]:
        return self.online_processor.stream_process(
            question,
            top_k=top_k,
            session_id=session_id,
            user_context=user_context,
        )
