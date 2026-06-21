import json
import os
import unittest
from unittest.mock import patch

from rag_app.streaming import format_sse_event

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("RAG_OPS_POSTGRES_DSN", "postgresql://rag:pwd@localhost:5432/rag")
os.environ.setdefault("RAG_ORDER_STATUS_TOOL_ENABLED", "false")

try:
    from fastapi.testclient import TestClient
    from rag_app import api
except ModuleNotFoundError:  # pragma: no cover - API 依赖是可选安装项
    TestClient = None
    api = None


class StreamingTest(unittest.TestCase):
    def test_format_sse_event_encodes_named_json_event(self) -> None:
        payload = format_sse_event("answer_delta", {"delta": "第一段"})

        self.assertEqual(payload, 'event: answer_delta\ndata: {"delta": "第一段"}\n\n')

    def test_format_sse_event_uses_json_serializable_fallback(self) -> None:
        payload = format_sse_event("complete", {"items": ("a", "b")})
        data_line = payload.splitlines()[1].removeprefix("data: ")

        self.assertEqual(json.loads(data_line), {"items": ["a", "b"]})


@unittest.skipIf(TestClient is None, "FastAPI API dependencies are not installed")
class ApiStreamingTest(unittest.TestCase):
    def test_query_stream_returns_sse_events_from_pipeline(self) -> None:
        assert api is not None
        client = TestClient(api.app)
        with patch.object(api, "_get_pipeline", return_value=_FakePipeline()):
            with client.stream(
                "POST",
                "/query/stream",
                json={"question": "光猫红灯咋办"},
            ) as response:
                body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("event: retrieval", body)
        self.assertIn("event: answer_delta", body)
        self.assertIn("event: complete", body)
        self.assertIn('"delta": "第一段"', body)


class _FakePipeline:
    def stream_query(self, question, top_k=None, session_id=None, user_context=None):
        del question, top_k, session_id, user_context
        yield {"event": "retrieval", "data": {"request_id": "req-1", "sources": []}}
        yield {
            "event": "answer_delta",
            "data": {"request_id": "req-1", "delta": "第一段"},
        }
        yield {
            "event": "complete",
            "data": {"request_id": "req-1", "answer": "第一段"},
        }


if __name__ == "__main__":
    unittest.main()
