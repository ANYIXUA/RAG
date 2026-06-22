import os
import sys
import types
import urllib.request
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class MinerUAdapterTest(unittest.TestCase):
    def test_parse_pdf_with_mineru_converts_markdown_output(self) -> None:
        from rag_app.ingestion.mineru_adapter import parse_pdf_with_mineru

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "borderless.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            fake_module = types.SimpleNamespace(
                parse_pdf=lambda input_path: {
                    "markdown": "# borderless\n\n## 无边框表格\n|字段|值|\n|---|---|\n|状态|正常|"
                }
            )
            with patch.dict(sys.modules, {"mineru": fake_module}):
                parsed = parse_pdf_with_mineru(path)

        self.assertIn("无边框表格", parsed.text)
        self.assertIn("|状态|正常|", parsed.text)
        self.assertEqual(parsed.metadata["parser_strategy"], "mineru_borderless_table")
        self.assertEqual(parsed.metadata["table_parser_route"], "mineru")
        self.assertEqual(parsed.metadata["mineru_used"], True)

    def test_parse_pdf_with_mineru_uses_online_agent_when_enabled_and_local_missing(self) -> None:
        from rag_app.ingestion import mineru_adapter

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "borderless.pdf"
            path.write_bytes(b"%PDF-1.4\n")

            calls: list[tuple[str, str, str]] = []

            def fake_http_json(
                method: str,
                url: str,
                payload: dict[str, object] | None = None,
                timeout_seconds: float = 30.0,
            ) -> dict[str, object]:
                calls.append(("json", method, url))
                if url.endswith("/parse/file"):
                    self.assertEqual(payload["file_name"], "borderless.pdf")
                    self.assertEqual(payload["enable_table"], True)
                    return {
                        "code": 0,
                        "data": {
                            "task_id": "task-1",
                            "file_url": "https://upload.example/file",
                        },
                    }
                self.assertTrue(url.endswith("/parse/task-1"))
                return {
                    "code": 0,
                    "data": {
                        "task_id": "task-1",
                        "state": "done",
                        "markdown_url": "https://cdn.example/full.md",
                    },
                }

            with (
                patch.dict(
                    os.environ,
                    {
                        "RAG_MINERU_ONLINE_ENABLED": "true",
                        "RAG_MINERU_ONLINE_API_BASE": "https://mineru.test/api/v1/agent/",
                        "RAG_MINERU_ONLINE_POLL_INTERVAL_SECONDS": "0",
                        "RAG_MINERU_ONLINE_TIMEOUT_SECONDS": "1",
                    },
                    clear=False,
                ),
                patch.dict(sys.modules, {"mineru": None}),
                patch.object(mineru_adapter, "_http_json", side_effect=fake_http_json),
                patch.object(mineru_adapter, "_http_put_file") as put_file,
                patch.object(
                    mineru_adapter,
                    "_http_text",
                    return_value="# online\n\n|字段|值|\n|---|---|\n|状态|正常|",
                ) as get_text,
            ):
                parsed = mineru_adapter.parse_pdf_with_mineru(path)

        self.assertIn("# online", parsed.text)
        self.assertIn("|状态|正常|", parsed.text)
        self.assertEqual(parsed.metadata["parser_strategy"], "mineru_online_agent")
        self.assertEqual(parsed.metadata["table_parser_route"], "mineru")
        self.assertEqual(parsed.metadata["mineru_used"], True)
        self.assertEqual(parsed.metadata["mineru_online_used"], True)
        self.assertEqual(parsed.metadata["external_parser_used"], True)
        self.assertEqual(parsed.metadata["mineru_online_task_id"], "task-1")
        self.assertEqual(
            calls,
            [
                ("json", "POST", "https://mineru.test/api/v1/agent/parse/file"),
                ("json", "GET", "https://mineru.test/api/v1/agent/parse/task-1"),
            ],
        )
        put_file.assert_called_once_with(
            "https://upload.example/file",
            path,
            timeout_seconds=1.0,
        )
        get_text.assert_called_once_with(
            "https://cdn.example/full.md",
            timeout_seconds=1.0,
        )

    def test_online_mineru_is_opt_in_when_local_module_is_missing(self) -> None:
        from rag_app.ingestion.mineru_adapter import parse_pdf_with_mineru

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "borderless.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            with (
                patch.dict(os.environ, {"RAG_MINERU_ONLINE_ENABLED": "false"}, clear=False),
                patch.dict(sys.modules, {"mineru": None}),
                self.assertRaisesRegex(RuntimeError, "online fallback is disabled"),
            ):
                parse_pdf_with_mineru(path)

    def test_online_mineru_failed_state_raises(self) -> None:
        from rag_app.ingestion import mineru_adapter

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "borderless.pdf"
            path.write_bytes(b"%PDF-1.4\n")

            def fake_http_json(
                method: str,
                url: str,
                payload: dict[str, object] | None = None,
                timeout_seconds: float = 30.0,
            ) -> dict[str, object]:
                if url.endswith("/parse/file"):
                    return {
                        "code": 0,
                        "data": {
                            "task_id": "task-1",
                            "file_url": "https://upload.example/file",
                        },
                    }
                return {
                    "code": 0,
                    "data": {
                        "task_id": "task-1",
                        "state": "failed",
                        "err_code": "E_PARSE",
                        "err_msg": "parse failed",
                    },
                }

            with (
                patch.dict(
                    os.environ,
                    {
                        "RAG_MINERU_ONLINE_ENABLED": "true",
                        "RAG_MINERU_ONLINE_POLL_INTERVAL_SECONDS": "0",
                        "RAG_MINERU_ONLINE_TIMEOUT_SECONDS": "1",
                    },
                    clear=False,
                ),
                patch.dict(sys.modules, {"mineru": None}),
                patch.object(mineru_adapter, "_http_json", side_effect=fake_http_json),
                patch.object(mineru_adapter, "_http_put_file"),
                self.assertRaisesRegex(RuntimeError, "parse failed"),
            ):
                mineru_adapter.parse_pdf_with_mineru(path)

    def test_online_upload_does_not_force_content_type_for_signed_url(self) -> None:
        from rag_app.ingestion.mineru_adapter import _http_put_file

        captured: dict[str, urllib.request.Request] = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return None

            def read(self) -> bytes:
                return b""

        def fake_urlopen(request: urllib.request.Request, timeout: float):
            captured["request"] = request
            return FakeResponse()

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "borderless.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                _http_put_file("https://upload.example/signed-url", path)

        request = captured["request"]
        self.assertEqual(request.get_method(), "PUT")
        self.assertIsNone(request.headers.get("Content-type"))
        self.assertIsNone(request.headers.get("Content-Type"))


if __name__ == "__main__":
    unittest.main()
