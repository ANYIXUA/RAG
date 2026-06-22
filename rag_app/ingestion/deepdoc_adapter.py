"""Optional DeepDoc adapter for complex PDF parsing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DeepDocParsedPdf:
    text: str
    metadata: dict[str, Any]


def parse_pdf_with_deepdoc(path: Path) -> DeepDocParsedPdf:
    """Parse a PDF through RAGFlow DeepDoc when the optional package is available."""

    try:
        from deepdoc.parser import PdfParser
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "DeepDoc PDF 解析需要可导入 deepdoc.parser.PdfParser。"
            "请安装或挂载 RAGFlow DeepDoc 运行环境。"
        ) from exc

    parser = PdfParser()
    result = parser(str(path))
    text = _deepdoc_result_to_markdown(path, result)
    if not text.strip() or text.strip() == f"# {path.stem}":
        raise RuntimeError(f"DeepDoc 未从 PDF 中抽取到可用文本: {path}")
    return DeepDocParsedPdf(
        text=text,
        metadata={
            "parser_name": "pdf",
            "media_type": "pdf",
            "title": path.stem,
            "parser_strategy": "deepdoc_complex_pdf",
            "pdf_document_class": "deepdoc_complex_pdf",
            "parse_quality_status": "parsed_success",
            "parse_warnings": [],
            "ocr_required": False,
            "deepdoc_used": True,
        },
    )


def _deepdoc_result_to_markdown(path: Path, result: Any) -> str:
    text_items, table_items = _split_deepdoc_result(result)
    lines = [f"# {path.stem}"]
    for index, item in enumerate(text_items, start=1):
        content = _item_text(item)
        if not content:
            continue
        page_number = _item_page_number(item)
        title = f"第{page_number}页" if page_number is not None else f"DeepDoc 片段 {index}"
        lines.extend(["", f"## {title}", content])

    for index, item in enumerate(table_items, start=1):
        content = _item_text(item)
        if not content:
            continue
        lines.extend(["", f"### DeepDoc 表格 {index}", content])
    return _clean_markdown("\n".join(lines))


def _split_deepdoc_result(result: Any) -> tuple[list[Any], list[Any]]:
    if isinstance(result, tuple):
        text_items = _ensure_list(result[0]) if len(result) >= 1 else []
        table_items = _ensure_list(result[1]) if len(result) >= 2 else []
        return text_items, table_items
    if isinstance(result, dict):
        text_items = _ensure_list(
            result.get("chunks")
            or result.get("texts")
            or result.get("text_chunks")
            or result.get("pages")
            or result.get("documents")
        )
        table_items = _ensure_list(result.get("tables"))
        return text_items, table_items
    return _ensure_list(result), []


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _item_text(item: Any) -> str:
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("text", "content", "markdown", "html"):
            value = item.get(key)
            if value:
                return str(value).strip()
        return ""
    for attr in ("text", "content", "markdown", "html"):
        value = getattr(item, attr, None)
        if value:
            return str(value).strip()
    return str(item).strip()


def _item_page_number(item: Any) -> int | None:
    if isinstance(item, dict):
        value = item.get("page_number") or item.get("page") or item.get("page_no")
    else:
        value = (
            getattr(item, "page_number", None)
            or getattr(item, "page", None)
            or getattr(item, "page_no", None)
        )
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _clean_markdown(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    compact: list[str] = []
    blank_count = 0
    for line in lines:
        if line:
            blank_count = 0
            compact.append(line)
            continue
        blank_count += 1
        if blank_count <= 1:
            compact.append(line)
    return "\n".join(compact).strip()
