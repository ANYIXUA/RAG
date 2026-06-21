import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from rag_app import prompt_templates
from rag_app.core.models import Chunk, RetrievalResult
from rag_app.retrieval.llm import OpenAIAnswerGenerator


class LLMTest(unittest.TestCase):
    def test_openai_answer_generator_sends_augmented_context(self) -> None:
        fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
        sources = [
            RetrievalResult(
                chunk=Chunk(
                    id="c1",
                    document_id="d1",
                    text="LOS red light usually means optical path failure.",
                    metadata={
                        "source": "fault_cases.md",
                        "section_title": "LOS red light",
                    },
                ),
                score=0.91,
            )
        ]

        with patch.dict(sys.modules, {"openai": fake_module}):
            generator = OpenAIAnswerGenerator(
                api_key="test-key",
                model="test-chat",
                base_url="https://example.test/v1",
                max_tokens=800,
                timeout_seconds=6.5,
                max_retries=0,
            )
            answer = generator.answer("How to handle LOS red light?", sources)

        self.assertEqual(answer, "model answer [1]")
        self.assertEqual(generator.client.timeout, 6.5)
        self.assertEqual(generator.client.max_retries, 0)
        completion_kwargs = generator.client.chat.completions.last_kwargs
        self.assertEqual(completion_kwargs["max_tokens"], 800)
        self.assertEqual(completion_kwargs["timeout"], 6.5)
        user_message = completion_kwargs["messages"][1]["content"]
        self.assertIn("How to handle LOS red light?", user_message)
        self.assertIn("fault_cases.md", user_message)

    def test_openai_answer_generator_trims_long_augmented_context(self) -> None:
        fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
        long_context = "A" * 200 + "TAIL_SHOULD_BE_REMOVED"

        with patch.dict(sys.modules, {"openai": fake_module}):
            generator = OpenAIAnswerGenerator(
                api_key="test-key",
                model="test-chat",
                context_max_chars=80,
            )
            generator.answer(
                "How to handle LOS red light?",
                sources=[],
                augmented_context=long_context,
            )

        user_message = generator.client.chat.completions.last_kwargs["messages"][1]["content"]
        sent_context = user_message.split("增强上下文：\n", 1)[1]
        self.assertLessEqual(len(sent_context), 130)
        self.assertIn("上下文已截断", sent_context)
        self.assertNotIn("TAIL_SHOULD_BE_REMOVED", sent_context)

    def test_openai_answer_generator_streams_answer_chunks(self) -> None:
        fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)

        with patch.dict(sys.modules, {"openai": fake_module}):
            generator = OpenAIAnswerGenerator(
                api_key="test-key",
                model="test-chat",
                timeout_seconds=5.0,
                max_retries=0,
            )
            chunks = list(
                generator.stream_answer(
                    "How to handle LOS red light?",
                    sources=[],
                    augmented_context="context",
                )
            )

        self.assertEqual(chunks, ["first ", "second"])
        completion_kwargs = generator.client.chat.completions.last_kwargs
        self.assertTrue(completion_kwargs["stream"])
        self.assertEqual(completion_kwargs["timeout"], 5.0)

    def test_openai_answer_generator_uses_external_prompt_templates(self) -> None:
        fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)

        with tempfile.TemporaryDirectory() as tmp_dir:
            prompt_root = Path(tmp_dir) / "prompts"
            prompt_dir = prompt_root / "answer_generation"
            prompt_dir.mkdir(parents=True)
            (prompt_dir / "system.md").write_text("SYSTEM FROM TEMPLATE", encoding="utf-8")
            (prompt_dir / "user.md").write_text(
                "QUESTION={question}\nCONTEXT={context}",
                encoding="utf-8",
            )

            with (
                patch.object(prompt_templates, "PROMPT_ROOT", prompt_root),
                patch.dict(sys.modules, {"openai": fake_module}),
            ):
                prompt_templates.load_prompt_template.cache_clear()
                generator = OpenAIAnswerGenerator(
                    api_key="test-key",
                    model="test-chat",
                )
                generator.answer(
                    "How to handle LOS red light?",
                    sources=[],
                    augmented_context="retrieved context",
                )

        prompt_templates.load_prompt_template.cache_clear()
        completion_kwargs = generator.client.chat.completions.last_kwargs
        self.assertEqual(
            completion_kwargs["messages"][0]["content"],
            "SYSTEM FROM TEMPLATE",
        )
        self.assertEqual(
            completion_kwargs["messages"][1]["content"],
            "QUESTION=How to handle LOS red light?\nCONTEXT=retrieved context",
        )


class _FakeCompletions:
    def __init__(self) -> None:
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        if kwargs.get("stream"):
            return [
                types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            delta=types.SimpleNamespace(content="first ")
                        )
                    ]
                ),
                types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            delta=types.SimpleNamespace(content=None)
                        )
                    ]
                ),
                types.SimpleNamespace(
                    choices=[
                        types.SimpleNamespace(
                            delta=types.SimpleNamespace(content="second")
                        )
                    ]
                ),
            ]
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content="model answer [1]")
                )
            ]
        )


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeOpenAI:
    def __init__(
        self,
        api_key=None,
        base_url=None,
        timeout=None,
        max_retries=None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.chat = _FakeChat()


if __name__ == "__main__":
    unittest.main()
