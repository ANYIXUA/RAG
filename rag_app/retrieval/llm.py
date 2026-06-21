"""回答生成适配。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from rag_app.core.config import Settings
from rag_app.core.models import RetrievalResult
from rag_app.prompt_templates import load_prompt_template, render_prompt_template


class AnswerGenerator(Protocol):
    """基于召回上下文生成回答。"""

    def answer(
        self,
        question: str,
        sources: list[RetrievalResult],
        augmented_context: str | None = None,
    ) -> str:
        ...


class StreamingAnswerGenerator(Protocol):
    """可以逐块返回回答 token 的生成器。"""

    def stream_answer(
        self,
        question: str,
        sources: list[RetrievalResult],
        augmented_context: str | None = None,
    ) -> Iterator[str]:
        ...


class OpenAIAnswerGenerator:
    """OpenAI 兼容对话生成适配器。"""

    def __init__(
        self,
        api_key: str | None,
        model: str,
        base_url: str | None = None,
        max_tokens: int | None = 800,
        timeout_seconds: float | None = 8.0,
        max_retries: int = 0,
        context_max_chars: int = 3200,
    ) -> None:
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Install OpenAI support with: pip install -e \".[openai]\""
            ) from exc
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )
        self.model = model
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.context_max_chars = context_max_chars

    def answer(
        self,
        question: str,
        sources: list[RetrievalResult],
        augmented_context: str | None = None,
    ) -> str:
        kwargs = self._chat_completion_kwargs(
            question=question,
            sources=sources,
            augmented_context=augmented_context,
        )
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def stream_answer(
        self,
        question: str,
        sources: list[RetrievalResult],
        augmented_context: str | None = None,
    ) -> Iterator[str]:
        kwargs = self._chat_completion_kwargs(
            question=question,
            sources=sources,
            augmented_context=augmented_context,
        )
        kwargs["stream"] = True
        response = self.client.chat.completions.create(**kwargs)
        for chunk in response:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None)
            if content:
                yield content

    def _chat_completion_kwargs(
        self,
        *,
        question: str,
        sources: list[RetrievalResult],
        augmented_context: str | None,
    ) -> dict:
        context = _trim_context(
            augmented_context or _build_source_context(sources),
            max_chars=self.context_max_chars,
        )
        kwargs = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": load_prompt_template("answer_generation/system.md"),
                },
                {
                    "role": "user",
                    "content": render_prompt_template(
                        "answer_generation/user.md",
                        question=question,
                        context=context,
                    ),
                },
            ],
            "temperature": 0.2,
        }
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        if self.timeout_seconds is not None:
            kwargs["timeout"] = self.timeout_seconds
        return kwargs


def create_answer_generator(settings: Settings) -> AnswerGenerator:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return OpenAIAnswerGenerator(
            api_key=settings.openai_api_key,
            model=settings.openai_chat_model,
            base_url=settings.openai_base_url,
            max_tokens=settings.openai_max_tokens,
            timeout_seconds=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
            context_max_chars=settings.generation_context_max_chars,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def _build_source_context(sources: list[RetrievalResult]) -> str:
    sections: list[str] = []
    for index, result in enumerate(sources, start=1):
        metadata = result.chunk.metadata
        sections.append(
            render_prompt_template(
                "answer_generation/source_context_item.md",
                index=index,
                source=metadata.get("source", "unknown"),
                location=_format_reference_location(result),
                content=result.chunk.text,
            )
        )
    return "\n\n".join(sections)


def _trim_context(context: str, max_chars: int | None) -> str:
    if max_chars is None or len(context) <= max_chars:
        return context
    suffix = "\n\n" + load_prompt_template(
        "answer_generation/context_truncation_suffix.md"
    )
    budget = max(0, max_chars - len(suffix))
    return context[:budget].rstrip() + suffix


def _format_reference_location(result: RetrievalResult) -> str:
    metadata = result.chunk.metadata
    section = metadata.get("section_title") or metadata.get("title") or "unknown"
    return (
        metadata.get("page_number")
        or metadata.get("slide_number")
        or metadata.get("time_range")
        or metadata.get("timestamp_range")
        or section
    )
