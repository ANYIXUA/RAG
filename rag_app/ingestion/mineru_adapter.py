"""Optional MinerU adapter for borderless PDF table parsing."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_DEFAULT_ONLINE_API_BASE = "https://mineru.net/api/v1/agent"
_DEFAULT_HTTP_RETRIES = 3
_ONLINE_TRUE_VALUES = {"1", "true", "yes", "on"}
_ONLINE_RUNNING_STATES = {"waiting-file", "uploading", "pending", "running"}
_ONLINE_FAILED_STATES = {"failed", "error"}


class _SignedUrlPutRequest(urllib.request.Request):
    """PUT request for OSS signed URLs without urllib's implicit Content-Type."""

    def has_header(self, header_name: str) -> bool:
        if header_name.lower() == "content-type":
            return True
        return super().has_header(header_name)


@dataclass(frozen=True)
class MinerUParsedPdf:
    text: str
    metadata: dict[str, Any]


def parse_pdf_with_mineru(path: Path) -> MinerUParsedPdf:
    """Parse a PDF through local MinerU, or the online Agent API when enabled."""

    local_error: Exception | None = None
    try:
        import mineru
    except ModuleNotFoundError as exc:
        local_error = exc
    else:
        try:
            return _parse_pdf_with_local_mineru(path, mineru)
        except Exception as exc:  # pragma: no cover - covered by online fallback path.
            local_error = exc

    if _mineru_online_enabled():
        return _parse_pdf_with_online_mineru(path)

    raise RuntimeError(
        "MinerU local parser is unavailable and online fallback is disabled. "
        "Install/deploy MinerU2.5 locally, or set RAG_MINERU_ONLINE_ENABLED=true "
        "after confirming the PDF may be uploaded to MinerU online parsing."
    ) from local_error


def _parse_pdf_with_local_mineru(path: Path, mineru_module: Any) -> MinerUParsedPdf:
    result = _call_mineru_parser(mineru_module, path)
    text = _mineru_result_to_markdown(path, result)
    if not text.strip() or text.strip() == f"# {path.stem}":
        raise RuntimeError(f"MinerU 未从 PDF 中抽取到可用文本: {path}")
    return MinerUParsedPdf(
        text=text,
        metadata={
            "parser_name": "pdf",
            "media_type": "pdf",
            "title": path.stem,
            "parser_strategy": "mineru_borderless_table",
            "pdf_document_class": "borderless_table_pdf",
            "table_parser_route": "mineru",
            "parse_quality_status": "parsed_success",
            "parse_warnings": [],
            "ocr_required": False,
            "external_parser_used": True,
            "mineru_used": True,
            "mineru_online_used": False,
        },
    )


def _parse_pdf_with_online_mineru(path: Path) -> MinerUParsedPdf:
    api_base = _normalize_api_base(
        os.getenv("RAG_MINERU_ONLINE_API_BASE", _DEFAULT_ONLINE_API_BASE)
    )
    timeout_seconds = _env_float("RAG_MINERU_ONLINE_TIMEOUT_SECONDS", 300.0)
    poll_interval_seconds = _env_float("RAG_MINERU_ONLINE_POLL_INTERVAL_SECONDS", 3.0)

    create_payload: dict[str, Any] = {
        "file_name": path.name,
        "language": os.getenv("RAG_MINERU_ONLINE_LANGUAGE", "ch"),
        "enable_table": _env_bool("RAG_MINERU_ONLINE_ENABLE_TABLE", True),
        "is_ocr": _env_bool("RAG_MINERU_ONLINE_ENABLE_OCR", False),
        "enable_formula": _env_bool("RAG_MINERU_ONLINE_ENABLE_FORMULA", True),
    }
    page_range = os.getenv("RAG_MINERU_ONLINE_PAGE_RANGE", "").strip()
    if page_range:
        create_payload["page_range"] = page_range

    create_response = _http_json(
        "POST",
        f"{api_base}/parse/file",
        payload=create_payload,
        timeout_seconds=timeout_seconds,
    )
    task_data = _response_data(create_response, "create task")
    task_id = _required_string(task_data, "task_id", "create task")
    file_url = _required_string(task_data, "file_url", "create task")

    _http_put_file(file_url, path, timeout_seconds=timeout_seconds)
    result_data = _wait_for_online_result(
        api_base=api_base,
        task_id=task_id,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    markdown_url = _required_string(result_data, "markdown_url", "poll task")
    text = _ensure_title(path, _http_text(markdown_url, timeout_seconds=timeout_seconds))
    if not text.strip() or text.strip() == f"# {path.stem}":
        raise RuntimeError(f"MinerU online parser returned empty markdown for PDF: {path}")

    return MinerUParsedPdf(
        text=text,
        metadata={
            "parser_name": "pdf",
            "media_type": "pdf",
            "title": path.stem,
            "parser_strategy": "mineru_online_agent",
            "pdf_document_class": "borderless_table_pdf",
            "table_parser_route": "mineru",
            "parse_quality_status": "parsed_success",
            "parse_warnings": [],
            "ocr_required": False,
            "external_parser_used": True,
            "mineru_used": True,
            "mineru_online_used": True,
            "mineru_online_task_id": task_id,
            "mineru_online_state": "done",
            "mineru_online_api_base": api_base,
        },
    )


def _wait_for_online_result(
    *,
    api_base: str,
    task_id: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        response = _http_json(
            "GET",
            f"{api_base}/parse/{task_id}",
            timeout_seconds=timeout_seconds,
        )
        data = _response_data(response, "poll task")
        state = str(data.get("state") or "").strip().lower()
        if state == "done":
            return data
        if state in _ONLINE_FAILED_STATES:
            detail = data.get("err_msg") or data.get("msg") or data.get("message") or state
            err_code = data.get("err_code")
            if err_code:
                detail = f"{err_code}: {detail}"
            raise RuntimeError(f"MinerU online parsing failed for task {task_id}: {detail}")
        if state and state not in _ONLINE_RUNNING_STATES:
            raise RuntimeError(
                f"MinerU online parsing task {task_id} returned unexpected state: {state}"
            )
        if time.monotonic() >= deadline:
            raise RuntimeError(f"MinerU online parsing timed out for task {task_id}")
        if poll_interval_seconds > 0:
            time.sleep(min(poll_interval_seconds, max(0.0, deadline - time.monotonic())))


def _mineru_online_enabled() -> bool:
    return str(os.getenv("RAG_MINERU_ONLINE_ENABLED", "")).strip().lower() in _ONLINE_TRUE_VALUES


def _http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    token = os.getenv("RAG_MINERU_ONLINE_TOKEN") or os.getenv("MINERU_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _urlopen_with_retries(request, timeout_seconds=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MinerU online API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"MinerU online API request failed: {exc.reason}") from exc
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"MinerU online API returned non-JSON response: {body[:200]}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("MinerU online API returned an unexpected JSON payload")
    return parsed


def _http_put_file(url: str, path: Path, timeout_seconds: float = 30.0) -> None:
    request = _SignedUrlPutRequest(
        url,
        data=path.read_bytes(),
        method="PUT",
    )
    try:
        with _urlopen_with_retries(request, timeout_seconds=timeout_seconds) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MinerU online upload HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"MinerU online upload failed: {exc.reason}") from exc


def _http_text(url: str, timeout_seconds: float = 30.0) -> str:
    request = urllib.request.Request(url, headers={"Accept": "text/markdown,text/plain,*/*"})
    try:
        with _urlopen_with_retries(request, timeout_seconds=timeout_seconds) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MinerU online markdown download HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"MinerU online markdown download failed: {exc.reason}") from exc


def _urlopen_with_retries(
    request: urllib.request.Request,
    *,
    timeout_seconds: float,
):
    max_attempts = _env_int("RAG_MINERU_ONLINE_HTTP_RETRIES", _DEFAULT_HTTP_RETRIES)
    retry_backoff_seconds = _env_float(
        "RAG_MINERU_ONLINE_RETRY_BACKOFF_SECONDS",
        1.0,
    )
    last_error: urllib.error.URLError | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return urllib.request.urlopen(request, timeout=timeout_seconds)
        except urllib.error.HTTPError:
            raise
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt >= max_attempts:
                raise
            if retry_backoff_seconds > 0:
                time.sleep(retry_backoff_seconds * attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError("MinerU online request retry loop ended unexpectedly")


def _response_data(response: dict[str, Any], action: str) -> dict[str, Any]:
    code = response.get("code", 0)
    if code not in (0, "0"):
        message = response.get("msg") or response.get("message") or response.get("err_msg") or code
        raise RuntimeError(f"MinerU online {action} failed: {message}")
    data = response.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"MinerU online {action} response missing data object")
    return data


def _required_string(data: dict[str, Any], key: str, action: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"MinerU online {action} response missing {key}")
    return value.strip()


def _normalize_api_base(value: str) -> str:
    normalized = value.strip().rstrip("/")
    return normalized or _DEFAULT_ONLINE_API_BASE


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in _ONLINE_TRUE_VALUES


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        number = float(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if number < 0:
        raise RuntimeError(f"{name} must be zero or greater")
    return number


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        number = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if number <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return number


def _call_mineru_parser(mineru_module: Any, path: Path) -> Any:
    if hasattr(mineru_module, "parse_pdf"):
        return mineru_module.parse_pdf(str(path))
    parser = getattr(mineru_module, "PdfParser", None)
    if parser is not None:
        return parser()(str(path))
    raise RuntimeError("MinerU adapter expected mineru.parse_pdf or mineru.PdfParser")


def _mineru_result_to_markdown(path: Path, result: Any) -> str:
    if isinstance(result, str):
        return _ensure_title(path, result)
    if isinstance(result, dict):
        for key in ("markdown", "md", "content", "text"):
            value = result.get(key)
            if value:
                return _ensure_title(path, str(value))
        if result.get("pages"):
            lines = [f"# {path.stem}"]
            for index, page in enumerate(result["pages"], start=1):
                content = _item_text(page)
                if content:
                    lines.extend(["", f"## 第{index}页", content])
            return _clean_markdown("\n".join(lines))
    if isinstance(result, (list, tuple)):
        lines = [f"# {path.stem}"]
        for index, item in enumerate(result, start=1):
            content = _item_text(item)
            if content:
                lines.extend(["", f"## MinerU 片段 {index}", content])
        return _clean_markdown("\n".join(lines))
    return _ensure_title(path, str(result))


def _item_text(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("markdown", "text", "content", "html"):
            value = item.get(key)
            if value:
                return str(value).strip()
        return ""
    for attr in ("markdown", "text", "content", "html"):
        value = getattr(item, attr, None)
        if value:
            return str(value).strip()
    return str(item).strip()


def _ensure_title(path: Path, markdown: str) -> str:
    text = _clean_markdown(markdown)
    return text if text.startswith("#") else f"# {path.stem}\n\n{text}"


def _clean_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()
