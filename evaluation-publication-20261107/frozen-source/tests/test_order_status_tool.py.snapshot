from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_app.core.models import ToolCallTrace
from rag_app.tools.order_status import (
    PostgresOrderStatusTool,
    create_order_status_tool,
    extract_work_order_no,
)
from tests.helpers import production_settings


class OrderStatusToolTest(unittest.TestCase):
    def test_extract_work_order_no_normalizes_value(self) -> None:
        self.assertEqual(
            extract_work_order_no("帮我查工单 wo-202604290001 到哪了"),
            "WO202604290001",
        )

    def test_postgres_tool_builds_status_trace(self) -> None:
        tool = _MemoryPostgresOrderStatusTool(
            dsn="postgresql://rag:pwd@localhost:5432/rag",
            order={
                "work_order_no": "WO202604290001",
                "order_type": "修障",
                "status": "处理中",
                "priority": 80,
                "address_text": "西湖区文三路 88 号",
                "flow_logs": [
                    {
                        "from_status": "已派单",
                        "to_status": "处理中",
                        "action_name": "现场处理",
                        "created_at": "2026-04-29T10:20:00+08:00",
                    }
                ],
            },
        )

        trace = tool.query("wo-202604290001", request_id="req-1")

        self.assertEqual(trace.tool_name, "query_order_status")
        self.assertEqual(trace.status, "success")
        self.assertTrue(trace.output["found"])
        self.assertEqual(trace.output["status"], "处理中")
        self.assertIn("现场处理", trace.output["summary"])
        self.assertEqual(tool.logged_request_id, "req-1")

    def test_factory_creates_postgres_tool(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = _settings(Path(temp_dir))

            with patch.object(PostgresOrderStatusTool, "_ensure_tool_log_schema"):
                tool = create_order_status_tool(settings)

            self.assertTrue(tool.enabled)
            self.assertEqual(tool.provider_name, "postgresql")

    def test_factory_can_disable_order_status_tool(self) -> None:
        with TemporaryDirectory() as temp_dir:
            settings = _settings(
                Path(temp_dir),
                order_status_tool_enabled=False,
                order_status_postgres_dsn=None,
            )

            tool = create_order_status_tool(settings)
            trace = tool.query("WO202604290001")

            self.assertFalse(tool.enabled)
            self.assertEqual(trace.status, "skipped")
            self.assertEqual(trace.error, "order_status_tool_disabled")


class _MemoryPostgresOrderStatusTool(PostgresOrderStatusTool):
    def __init__(self, dsn: str, order: dict) -> None:
        self.dsn = dsn
        self.order = order
        self.logged_request_id: str | None = None

    def _fetch_order(self, work_order_no: str) -> dict | None:
        if self.order["work_order_no"] == work_order_no:
            return self.order
        return None

    def _append_tool_log(self, request_id: str | None, trace: ToolCallTrace) -> None:
        del trace
        self.logged_request_id = request_id


def _settings(
    base_dir: Path,
    order_status_tool_enabled: bool = True,
    order_status_postgres_dsn: str | None = "postgresql://rag:pwd@localhost:5432/rag",
):
    return production_settings(
        base_dir,
        order_status_tool_enabled=order_status_tool_enabled,
        order_status_postgres_dsn=order_status_postgres_dsn,
    )


if __name__ == "__main__":
    unittest.main()
