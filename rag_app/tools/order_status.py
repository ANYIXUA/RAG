"""查询工单状态工具。"""

from __future__ import annotations

import re
import time
from dataclasses import replace
from typing import Any, Protocol

from rag_app.core.config import Settings
from rag_app.core.models import ToolCallTrace


TOOL_NAME = "query_order_status"
WORK_ORDER_RE = re.compile(r"\b(?:WO|GD|ORDER)[-_]?\d{4,}\b", re.IGNORECASE)


class OrderStatusTool(Protocol):
    """查询工单状态的统一接口。"""

    provider_name: str
    enabled: bool

    def query(
        self,
        work_order_no: str,
        request_id: str | None = None,
    ) -> ToolCallTrace:
        ...


class DisabledOrderStatusTool:
    """关闭工具时的占位实现，保证在线链路不用判断空对象。"""

    provider_name = "disabled"
    enabled = False

    def query(
        self,
        work_order_no: str,
        request_id: str | None = None,
    ) -> ToolCallTrace:
        del request_id
        return ToolCallTrace(
            tool_name=TOOL_NAME,
            input={"work_order_no": normalize_work_order_no(work_order_no)},
            output={},
            status="skipped",
            latency_ms=0.0,
            error="order_status_tool_disabled",
        )


class PostgresOrderStatusTool:
    """从 PostgreSQL 业务表中查询工单状态，并写入工具调用日志。"""

    provider_name = "postgresql"
    enabled = True

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._ensure_tool_log_schema()

    def query(
        self,
        work_order_no: str,
        request_id: str | None = None,
    ) -> ToolCallTrace:
        started_at = time.perf_counter()
        normalized_no = normalize_work_order_no(work_order_no)
        input_payload = {"work_order_no": normalized_no, "provider": self.provider_name}
        try:
            order = self._fetch_order(normalized_no)
            output = _build_order_output(normalized_no, order)
            status = "success" if output["found"] else "not_found"
            trace = ToolCallTrace(
                tool_name=TOOL_NAME,
                input=input_payload,
                output=output,
                status=status,
                latency_ms=_elapsed_ms(started_at),
            )
        except Exception as exc:
            trace = ToolCallTrace(
                tool_name=TOOL_NAME,
                input=input_payload,
                output={},
                status="error",
                latency_ms=_elapsed_ms(started_at),
                error=str(exc),
            )
        try:
            self._append_tool_log(request_id=request_id, trace=trace)
        except Exception as exc:
            trace = replace(
                trace,
                error=_append_error(trace.error, f"tool_log_failed: {exc}"),
            )
        return trace

    def _fetch_order(self, work_order_no: str) -> dict[str, Any] | None:
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT work_order_no, order_type, status, priority, area_code,
                           address_text, device_sn, fault_type, error_code,
                           description, created_at, updated_at
                    FROM work_orders
                    WHERE UPPER(work_order_no) = UPPER(%s)
                    """,
                    (work_order_no,),
                )
                order = cursor.fetchone()
                if not order:
                    return None
                cursor.execute(
                    """
                    SELECT from_status, to_status, action_name, operator_role,
                           action_note, created_at
                    FROM work_order_flow_logs
                    WHERE UPPER(work_order_no) = UPPER(%s)
                    ORDER BY created_at DESC
                    LIMIT 5
                    """,
                    (work_order_no,),
                )
                flow_logs = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT dispatch_no, technician_id, dispatch_strategy,
                           dispatch_reason, dispatch_status, created_at
                    FROM dispatch_records
                    WHERE UPPER(work_order_no) = UPPER(%s)
                    ORDER BY created_at DESC
                    LIMIT 3
                    """,
                    (work_order_no,),
                )
                dispatch_records = cursor.fetchall()
        payload = dict(order)
        payload["flow_logs"] = [dict(item) for item in flow_logs]
        payload["dispatch_records"] = [dict(item) for item in dispatch_records]
        return _json_safe(payload)

    def _ensure_tool_log_schema(self) -> None:
        psycopg, _, _ = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rag_tool_call_logs (
                        id BIGSERIAL PRIMARY KEY,
                        query_id VARCHAR(64),
                        tool_name VARCHAR(128) NOT NULL,
                        input_json JSONB NOT NULL DEFAULT '{}'::JSONB,
                        output_json JSONB NOT NULL DEFAULT '{}'::JSONB,
                        status VARCHAR(32) NOT NULL,
                        error_message TEXT,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_rag_tool_call_logs_query "
                    "ON rag_tool_call_logs (query_id, created_at DESC)"
                )

    def _append_tool_log(self, request_id: str | None, trace: ToolCallTrace) -> None:
        psycopg, _, jsonb = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rag_tool_call_logs (
                        query_id, tool_name, input_json, output_json, status, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request_id,
                        trace.tool_name,
                        jsonb(trace.input),
                        jsonb(trace.output),
                        trace.status,
                        trace.error,
                    ),
                )


def create_order_status_tool(settings: Settings) -> OrderStatusTool:
    """根据配置创建查询工单状态工具。"""

    if not settings.order_status_tool_enabled:
        return DisabledOrderStatusTool()
    if not settings.order_status_postgres_dsn:
        raise ValueError(
            "RAG_ORDER_STATUS_POSTGRES_DSN cannot be empty when order status tool is enabled"
        )
    return PostgresOrderStatusTool(settings.order_status_postgres_dsn)


def extract_work_order_no(text: str) -> str | None:
    """从用户问题或改写后的检索 query 中提取工单号。"""

    match = WORK_ORDER_RE.search(text)
    if not match:
        return None
    return normalize_work_order_no(match.group(0))


def normalize_work_order_no(value: str) -> str:
    """统一工单号大小写和分隔符，避免 WO-001 与 wo001 匹配失败。"""

    return value.strip().upper().replace("-", "").replace("_", "")


def _build_order_output(
    work_order_no: str,
    order: dict[str, Any] | None,
) -> dict[str, Any]:
    if order is None:
        return {
            "found": False,
            "work_order_no": work_order_no,
            "summary": f"未查询到工单 {work_order_no} 的状态记录。",
        }

    flow_logs = list(order.get("flow_logs") or [])
    dispatch_records = list(order.get("dispatch_records") or [])
    latest_flow = flow_logs[0] if flow_logs else None
    latest_dispatch = dispatch_records[0] if dispatch_records else None
    summary_parts = [
        f"工单 {work_order_no} 当前状态为 {order.get('status', '未知')}",
        f"类型为 {order.get('order_type', '未知')}",
    ]
    if order.get("fault_type"):
        summary_parts.append(f"故障类型为 {order['fault_type']}")
    if order.get("address_text"):
        summary_parts.append(f"地址为 {order['address_text']}")
    if latest_flow:
        summary_parts.append(
            "最近流转动作为 "
            f"{latest_flow.get('action_name', '未知动作')}，"
            f"状态到 {latest_flow.get('to_status', order.get('status', '未知'))}"
        )
    if latest_dispatch:
        summary_parts.append(
            "最近派单状态为 "
            f"{latest_dispatch.get('dispatch_status', '未知')}"
        )
    return {
        "found": True,
        "work_order_no": work_order_no,
        "order_type": order.get("order_type"),
        "status": order.get("status"),
        "priority": order.get("priority"),
        "area_code": order.get("area_code"),
        "address_text": order.get("address_text"),
        "device_sn": order.get("device_sn"),
        "fault_type": order.get("fault_type"),
        "error_code": order.get("error_code"),
        "description": order.get("description"),
        "created_at": order.get("created_at"),
        "updated_at": order.get("updated_at"),
        "latest_flow": latest_flow,
        "latest_dispatch": latest_dispatch,
        "flow_logs": flow_logs,
        "dispatch_records": dispatch_records,
        "summary": "；".join(summary_parts) + "。",
    }


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)


def _append_error(current: str | None, item: str) -> str:
    if current:
        return f"{current}; {item}"
    return item


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _import_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PostgreSQL 工单状态工具需要安装 psycopg：pip install -e \".[pgsql]\""
        ) from exc
    return psycopg, dict_row, Jsonb
