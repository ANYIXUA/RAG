import sys
import types
import unittest
from unittest.mock import patch

from rag_app.retrieval.llm import OpenAIAnswerGenerator
from rag_app.core.models import Chunk, RetrievalResult


class LLMTest(unittest.TestCase):
    def test_openai_answer_generator_sends_augmented_context(self) -> None:
        fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
        sources = [
            RetrievalResult(
                chunk=Chunk(
                    id="c1",
                    document_id="d1",
                    text="光猫 LOS 红灯通常表示光路异常。建议先检查尾纤。",
                    metadata={
                        "source": "fault_cases.md",
                        "section_title": "光猫 LOS 红灯",
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
            )
            answer = generator.answer("光猫红灯怎么处理", sources)

        self.assertEqual(answer, "模型回答 [1]")
        completion_kwargs = generator.client.chat.completions.last_kwargs
        self.assertEqual(completion_kwargs["max_tokens"], 800)
        user_message = completion_kwargs["messages"][1]["content"]
        self.assertIn("光猫红灯怎么处理", user_message)
        self.assertIn("fault_cases.md", user_message)


class _FakeCompletions:
    def __init__(self) -> None:
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content="模型回答 [1]")
                )
            ]
        )


class _FakeChat:
    def __init__(self) -> None:
        self.completions = _FakeCompletions()


class _FakeOpenAI:
    def __init__(self, api_key=None, base_url=None) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.chat = _FakeChat()


if __name__ == "__main__":
    unittest.main()
