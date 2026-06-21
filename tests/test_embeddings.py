import sys
import types
import unittest
from unittest.mock import patch

from rag_app.indexing.embeddings import OpenAIEmbedder


class EmbeddingsTest(unittest.TestCase):
    def test_openai_embedder_batches_inputs_for_dashscope_limit(self) -> None:
        fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)
        texts = [f"chunk-{index}" for index in range(45)]

        with patch.dict(sys.modules, {"openai": fake_module}):
            embedder = OpenAIEmbedder(
                api_key="test-key",
                model="text-embedding-v4",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                dimensions=1024,
                batch_size=10,
                timeout_seconds=3.0,
                max_retries=0,
            )
            embeddings = embedder.embed(texts)

        self.assertEqual(len(embeddings), 45)
        self.assertEqual(embedder.client.timeout, 3.0)
        self.assertEqual(embedder.client.max_retries, 0)
        self.assertEqual(
            [len(call["input"]) for call in embedder.client.embeddings.calls],
            [10, 10, 10, 10, 5],
        )
        self.assertEqual(
            [call["timeout"] for call in embedder.client.embeddings.calls],
            [3.0, 3.0, 3.0, 3.0, 3.0],
        )
        self.assertEqual(
            [call["dimensions"] for call in embedder.client.embeddings.calls],
            [1024, 1024, 1024, 1024, 1024],
        )

    def test_openai_embedder_rejects_invalid_batch_size(self) -> None:
        fake_module = types.SimpleNamespace(OpenAI=_FakeOpenAI)

        with patch.dict(sys.modules, {"openai": fake_module}):
            with self.assertRaisesRegex(ValueError, "batch_size"):
                OpenAIEmbedder(
                    api_key="test-key",
                    model="text-embedding-v4",
                    batch_size=0,
                )


class _FakeEmbeddings:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return types.SimpleNamespace(
            data=[
                types.SimpleNamespace(index=index, embedding=[float(index)])
                for index, _ in enumerate(kwargs["input"])
            ]
        )


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
        self.embeddings = _FakeEmbeddings()


if __name__ == "__main__":
    unittest.main()
