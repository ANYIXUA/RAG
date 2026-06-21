"""Helpers for HTTP streaming responses."""

from __future__ import annotations

import json
from typing import Any


def format_sse_event(event: str, data: dict[str, Any]) -> str:
    """Encode one Server-Sent Events message with JSON data."""

    payload = json.dumps(data, ensure_ascii=False, default=str)
    lines = [f"event: {event}"]
    lines.extend(f"data: {line}" for line in payload.splitlines() or [""])
    lines.append("")
    lines.append("")
    return "\n".join(lines)
