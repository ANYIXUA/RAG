import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

_TEST_POSTGRES_DSN = os.getenv("RAG_TEST_POSTGRES_DSN")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault(
    "RAG_OPS_POSTGRES_DSN",
    _TEST_POSTGRES_DSN or "postgresql://rag:pwd@localhost:5432/rag",
)
os.environ.setdefault("RAG_ORDER_STATUS_TOOL_ENABLED", "false")

try:
    from fastapi.testclient import TestClient
    from rag_app import api
except ModuleNotFoundError:  # pragma: no cover - API 依赖是可选安装项
    TestClient = None
    api = None

from rag_app.indexing.offline import OfflineKnowledgeBuilder


@unittest.skipIf(TestClient is None, "FastAPI API dependencies are not installed")
class ApiMemoryOverrideTest(unittest.TestCase):
    def setUp(self) -> None:
        assert api is not None
        api._PIPELINE = None
        api._PIPELINE_KNOWLEDGE_KEY = None

    def tearDown(self) -> None:
        assert api is not None
        api._PIPELINE = None
        api._PIPELINE_KNOWLEDGE_KEY = None

    def test_memory_override_management_endpoints(self) -> None:
        from rag_app.retrieval.answer_memory import MemoryAnswerMemoryStore

        assert api is not None
        store = MemoryAnswerMemoryStore()
        env = {
            "OPENAI_API_KEY": "test-key",
            "RAG_OPS_POSTGRES_DSN": "postgresql://rag:pwd@localhost:5432/rag",
            "RAG_ORDER_STATUS_TOOL_ENABLED": "false",
            "RAG_API_ADMIN_TOKEN": "secret-token",
            "RAG_REDIS_ANSWER_OVERRIDE_ENABLED": "true",
        }
        with (
            patch.dict(os.environ, env, clear=True),
            patch("rag_app.api.create_answer_memory_store", return_value=store),
        ):
            client = TestClient(api.app)
            unauthorized = client.post(
                "/memory/overrides",
                json={
                    "question": "系统是不是故障了？",
                    "answer": "系统当前故障，请稍后再试。",
                    "tenant_id": "tenant-a",
                    "permission_tags": ["public"],
                    "category": "incident",
                    "promote_to_long_term": True,
                },
            )
            created = client.post(
                "/memory/overrides",
                headers={"X-API-Key": "secret-token"},
                json={
                    "question": "系统是不是故障了？",
                    "answer": "系统当前故障，请稍后再试。",
                    "tenant_id": "tenant-a",
                    "permission_tags": ["public"],
                    "category": "incident",
                    "promote_to_long_term": True,
                    "ttl_seconds": 1800,
                    "created_by": "ops",
                },
            )
            override_id = created.json()["override_id"]
            listed = client.get(
                "/memory/overrides?tenant_id=tenant-a",
                headers={"X-API-Key": "secret-token"},
            )
            patched = client.patch(
                f"/memory/overrides/{override_id}",
                headers={"X-API-Key": "secret-token"},
                json={"enabled": False},
            )
            deleted = client.delete(
                f"/memory/overrides/{override_id}",
                headers={"X-API-Key": "secret-token"},
            )

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["answer"], "系统当前故障，请稍后再试。")
        self.assertEqual(created.json()["category"], "incident")
        self.assertFalse(created.json()["promote_to_long_term"])
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["items"]), 1)
        self.assertEqual(patched.status_code, 200)
        self.assertFalse(patched.json()["enabled"])
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["deleted"])


@unittest.skipIf(TestClient is None, "FastAPI API dependencies are not installed")
@unittest.skipUnless(_TEST_POSTGRES_DSN, "PostgreSQL integration DSN is not configured")
class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        assert api is not None
        api._PIPELINE = None
        api._PIPELINE_KNOWLEDGE_KEY = None

    def tearDown(self) -> None:
        assert api is not None
        api._PIPELINE = None
        api._PIPELINE_KNOWLEDGE_KEY = None

    def test_ready_reports_not_ready_when_vector_store_missing(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = _env(temp_dir)
            with patch.dict(os.environ, env, clear=True):
                client = TestClient(api.app)
                response = client.get("/ready")

            self.assertEqual(response.status_code, 503)
            payload = response.json()
            self.assertEqual(payload["status"], "not_ready")
            self.assertIn("vector_store_missing", payload["knowledge"]["reasons"])

    def test_health_and_ready_after_offline_refresh(self) -> None:
        with TemporaryDirectory() as temp_dir:
            _write_knowledge(temp_dir)
            env = _env(temp_dir)
            with patch.dict(os.environ, env, clear=True):
                OfflineKnowledgeBuilder.from_env(base_dir=Path(temp_dir)).refresh(
                    reset=True
                )
                client = TestClient(api.app)
                health = client.get("/health")
                ready = client.get("/ready")

            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json()["status"], "ok")
            self.assertEqual(health.json()["build"]["app_version"], "0.1.0")
            self.assertGreaterEqual(health.json()["knowledge"]["records"], 1)
            self.assertEqual(ready.status_code, 200)
            self.assertEqual(ready.json()["status"], "ready")

    def test_admin_token_protects_management_endpoints(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = _env(temp_dir)
            env["RAG_API_ADMIN_TOKEN"] = "secret-token"
            with patch.dict(os.environ, env, clear=True):
                client = TestClient(api.app)
                unauthorized = client.get("/ops/summary")
                authorized = client.get(
                    "/ops/summary",
                    headers={"X-API-Key": "secret-token"},
                )

            self.assertEqual(unauthorized.status_code, 401)
            self.assertEqual(unauthorized.json()["error"]["code"], "UNAUTHORIZED")
            self.assertEqual(authorized.status_code, 200)
            self.assertIn("query_logs", authorized.json())

    def test_validation_errors_use_unified_error_shape(self) -> None:
        with TemporaryDirectory() as temp_dir:
            env = _env(temp_dir)
            with patch.dict(os.environ, env, clear=True):
                client = TestClient(api.app)
                response = client.post("/query", json={"question": "", "top_k": 0})

            self.assertEqual(response.status_code, 422)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
            self.assertIn("request_id", payload["error"])

    def test_query_exposes_request_id_for_feedback_and_trace(self) -> None:
        with TemporaryDirectory() as temp_dir:
            _write_knowledge(temp_dir)
            env = _env(temp_dir)
            with patch.dict(os.environ, env, clear=True):
                OfflineKnowledgeBuilder.from_env(base_dir=Path(temp_dir)).refresh(
                    reset=True
                )
                client = TestClient(api.app)
                query = client.post("/query", json={"question": "光猫红灯咋办"})
                request_id = query.json()["request_id"]
                feedback = client.post(
                    "/feedback",
                    json={
                        "request_id": request_id,
                        "rating": 5,
                        "useful": True,
                    },
                )
                trace = client.get(f"/ops/trace/{request_id}")

            self.assertEqual(query.status_code, 200)
            self.assertEqual(query.json()["trace"]["request_id"], request_id)
            self.assertEqual(feedback.status_code, 200)
            self.assertEqual(trace.status_code, 200)
            self.assertTrue(trace.json()["found"])
            self.assertEqual(len(trace.json()["feedback"]), 1)

    def test_text_upload_builds_and_activates_new_knowledge_version(self) -> None:
        with TemporaryDirectory() as temp_dir:
            _write_knowledge(temp_dir)
            env = _env(temp_dir)
            with patch.dict(os.environ, env, clear=True):
                client = TestClient(api.app)
                response = client.post(
                    "/knowledge/uploads/text",
                    json={
                        "filename": "address.md",
                        "content": "# 地址校验\n\n标准地址不存在时需要转资源核查。",
                        "business_module": "地址校验",
                        "auto_build": True,
                        "activate_when_ready": True,
                    },
                )
                active = client.get("/knowledge/active")
                ready = client.get("/ready")

            self.assertEqual(response.status_code, 200)
            self.assertIsNotNone(response.json()["job"])
            self.assertEqual(active.status_code, 200)
            self.assertIsNotNone(active.json()["active_version"])
            self.assertEqual(ready.status_code, 200)
            self.assertGreaterEqual(ready.json()["knowledge"]["records"], 2)


def _env(temp_dir: str) -> dict[str, str]:
    return {
        "RAG_DATA_DIR": str(Path(temp_dir) / "data"),
        "RAG_STORAGE_DIR": str(Path(temp_dir) / "storage"),
        "RAG_COLLECTION_NAME": "test",
        "RAG_EMBEDDING_PROVIDER": "openai",
        "RAG_EMBEDDING_DIMENSION": "64",
        "RAG_LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "test-key",
        "RAG_OPS_POSTGRES_DSN": _TEST_POSTGRES_DSN or "",
        "RAG_ORDER_STATUS_TOOL_ENABLED": "false",
        "RAG_QUERY_LOGGING_ENABLED": "true",
    }


def _write_knowledge(temp_dir: str) -> None:
    data_dir = Path(temp_dir) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "fault.md").write_text(
        "# 光猫 LOS 红灯\n\n光猫红灯需要检查尾纤和光功率。",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
