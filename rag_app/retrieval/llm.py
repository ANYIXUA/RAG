"""回答生成适配。"""

from __future__ import annotations

from typing import Protocol

from rag_app.core.config import Settings
from rag_app.core.models import RetrievalResult


class AnswerGenerator(Protocol):
    """基于召回上下文生成回答。"""

    def answer(
        self,
        question: str,
        sources: list[RetrievalResult],
        augmented_context: str | None = None,
    ) -> str:
        ...


class OpenAIAnswerGenerator:
    """OpenAI 兼容对话生成适配器。"""

    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str | None = None,
        max_tokens: int | None = 800,
    ) -> None:
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Install OpenAI support with: pip install -e \".[openai]\""
            ) from exc
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_tokens = max_tokens

    def answer(
        self,
        question: str,
        sources: list[RetrievalResult],
        augmented_context: str | None = None,
    ) -> str:
        context = augmented_context or _build_source_context(sources)
        kwargs = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是装维业务知识问答助手。"
                        "只能基于提供的检索上下文回答问题，不得编造。"
                        "回答中的每个关键结论都需要使用 [1]、[2] 这样的编号引用来源。"
                        "引用编号只能来自提供的上下文片段。"
                        "如果上下文中没有答案，要明确说明不知道，并提示补充信息或转人工。"
                        "请用 5 条以内要点回答，每条不超过 40 字；只基于检索上下文回答。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"用户原始问题：\n{question}\n\n增强上下文：\n{context}",
                },
            ],
            "temperature": 0.2,
        }
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


def create_answer_generator(settings: Settings) -> AnswerGenerator:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return OpenAIAnswerGenerator(
            api_key=settings.openai_api_key,
            model=settings.openai_chat_model,
            base_url=settings.openai_base_url,
            max_tokens=settings.openai_max_tokens,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def _format_reference_line(index: int, result: RetrievalResult) -> str:
    metadata = result.chunk.metadata
    source = metadata.get("source", "unknown")
    section = metadata.get("section_title") or metadata.get("title") or source
    location = (
        metadata.get("page_number")
        or metadata.get("slide_number")
        or metadata.get("time_range")
        or metadata.get("timestamp_range")
        or section
    )
    return f"- [{index}] {source} | {location}"


def _build_source_context(sources: list[RetrievalResult]) -> str:
    sections: list[str] = []
    for index, result in enumerate(sources, start=1):
        sections.append(
            "\n".join(
                [
                    _format_reference_line(index, result),
                    result.chunk.text,
                ]
            )
        )
    return "\n\n".join(sections)
