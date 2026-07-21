import json
import os
import unittest
from dataclasses import asdict
from unittest.mock import patch

from rag_app.streaming import format_sse_event
from rag_app.retrieval.online import _stream_source_snapshot
from tests.helpers import (
    PUBLIC_CONTRACT_CANARIES,
    PUBLIC_SOURCE_FIELDS,
    PUBLIC_SOURCE_METADATA_FIELDS,
    PUBLIC_TRACE_FIELDS,
    malicious_public_contract_answer,
)

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

    def test_retrieval_source_snapshot_uses_public_source_allowlist(self) -> None:
        source = malicious_public_contract_answer().sources[0]

        payload = _stream_source_snapshot(source)

        self.assertEqual(set(payload), PUBLIC_SOURCE_FIELDS)
        self.assertEqual(
            set(payload["chunk"]["metadata"]),
            PUBLIC_SOURCE_METADATA_FIELDS,
        )
        self.assertEqual(payload["retrieval_score"], 0.83)
        self.assertEqual(payload["rerank_score"], 0.97)
        serialized = json.dumps(payload, ensure_ascii=False)
        for canary in PUBLIC_CONTRACT_CANARIES:
            self.assertNotIn(canary, serialized)


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

    def test_query_stream_projects_retrieval_and_complete_events(self) -> None:
        assert api is not None
        client = TestClient(api.app)
        with patch.object(api, "_get_pipeline", return_value=_MaliciousPipeline()):
            with client.stream(
                "POST",
                "/query/stream",
                json={"question": "公开问题"},
            ) as response:
                body = "".join(response.iter_text())

        events = _parse_sse_events(body)
        retrieval = next(data for event, data in events if event == "retrieval")
        complete = next(data for event, data in events if event == "complete")
        self.assertEqual(set(retrieval["sources"][0]), PUBLIC_SOURCE_FIELDS)
        self.assertEqual(
            set(retrieval["sources"][0]["chunk"]["metadata"]),
            PUBLIC_SOURCE_METADATA_FIELDS,
        )
        self.assertEqual(set(complete["trace"]), PUBLIC_TRACE_FIELDS)
        self.assertEqual(complete["sources"][0]["retrieval_score"], 0.83)
        self.assertEqual(complete["sources"][0]["rerank_score"], 0.97)
        for canary in PUBLIC_CONTRACT_CANARIES:
            self.assertNotIn(canary, body)

    def test_query_stream_redacts_internal_error_details(self) -> None:
        assert api is not None
        client = TestClient(api.app)
        with patch.object(api, "_get_pipeline", return_value=_ErrorPipeline()):
            with client.stream(
                "POST",
                "/query/stream",
                json={"question": "公开问题"},
            ) as response:
                body = "".join(response.iter_text())

        events = _parse_sse_events(body)
        self.assertEqual(
            events,
            [
                (
                    "error",
                    {
                        "code": "STREAM_QUERY_ERROR",
                        "message": "查询流处理失败",
                    },
                )
            ],
        )
        self.assertNotIn(PUBLIC_CONTRACT_CANARIES[2], body)


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


class _MaliciousPipeline:
    def stream_query(self, question, top_k=None, session_id=None, user_context=None):
        del question, top_k, session_id, user_context
        answer = malicious_public_contract_answer()
        source = asdict(answer.sources[0])
        yield {
            "event": "retrieval",
            "data": {
                "request_id": "req-public-1",
                "retrieved_count": 1,
                "reranked_count": 1,
                "sources": [source],
                "tool_calls": [{"output": PUBLIC_CONTRACT_CANARIES[3]}],
            },
        }
        yield {"event": "complete", "data": asdict(answer)}


class _ErrorPipeline:
    def stream_query(self, question, top_k=None, session_id=None, user_context=None):
        del question, top_k, session_id, user_context
        yield {
            "event": "error",
            "data": {
                "code": "STREAM_QUERY_ERROR",
                "message": f"provider failed with {PUBLIC_CONTRACT_CANARIES[2]}",
            },
        }


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        event = lines[0].removeprefix("event: ")
        data = json.loads(lines[1].removeprefix("data: "))
        events.append((event, data))
    return events


if __name__ == "__main__":
    unittest.main()
