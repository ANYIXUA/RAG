"""面向检索的文本切片逻辑。"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from rag_app.core.models import Chunk, Document, ParsedBlock


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PAGE_TITLE_RE = re.compile(r"^第\s*(\d+)\s*页$")
SLIDE_TITLE_RE = re.compile(r"^第\s*(\d+)\s*页幻灯片$")
SEGMENT_TITLE_RE = re.compile(r"^片段\s+\d+\s+\[(.+)\]$")
CHUNKER_VERSION = "block-aware-v6"

_CHUNK_METADATA_EXCLUDED_KEYS = {
    "block_count",
    "pdf_document_class",
    "page_count",
    "extracted_page_count",
    "empty_page_count",
    "low_text_page_count",
    "scanned_page_candidates",
    "table_like_page_count",
    "parse_quality_status",
    "parse_warnings",
    "ocr_required",
    "ocr_candidate_pages",
    "ocr_applied",
    "ocr_provider",
    "ocr_page_count",
    "ocr_pages",
    "ocr_confidence_avg",
    "ocr_unavailable_reason",
    "pdf_page_reports",
    "external_parser_attempted",
    "external_parser_used",
    "deepdoc_attempted",
    "deepdoc_used",
    "deepdoc_trigger_warnings",
    "mineru_attempted",
    "mineru_used",
    "mineru_online_api_base",
    "mineru_online_state",
    "mineru_online_task_id",
    "mineru_online_used",
    "mineru_trigger_warnings",
    "rules_ml_attempted",
    "rules_ml_used",
    "rules_ml_trigger_warnings",
}
_PRESERVE_EMPTY_CHUNK_KEYS = {
    "chunk_parse_warning_codes",
    "detected_codes",
    "error_codes",
    "page_warning_codes",
}


@dataclass(frozen=True)
class _Section:
    text: str
    title: str | None
    heading_path: list[str]
    start_line: int


class WhitespaceChunker:
    """优先按 Markdown 标题切片，再对超长文本做窗口切分。"""

    version = CHUNKER_VERSION

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be zero or greater")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: list[Document]) -> list[Chunk]:
        chunks: list[Chunk] = []
        for document in documents:
            document_metadata = _chunk_document_metadata(document.metadata)
            if document.parsed_blocks:
                chunks.extend(
                    self._split_parsed_blocks(
                        document,
                        document_metadata=document_metadata,
                        start_index=0,
                    )
                )
                continue

            # 优先复用解析阶段生成的 Markdown 结构，把标题路径保留下来。
            # 这样召回结果不仅有文本，还有 section_title、heading_path、页码/时间段等定位信息。
            sections = _split_markdown_sections(document.text)
            chunk_index = 0
            for section_index, section in enumerate(sections):
                for split_index, chunk_text, start, end in self._split_section_text(section.text):
                    location_metadata = _extract_section_location(section.title)
                    chunks.append(
                        Chunk(
                            id=self._chunk_id(document.id, chunk_index, chunk_text),
                            document_id=document.id,
                            text=chunk_text,
                            metadata={
                                **document_metadata,
                                "business_module": _infer_section_business_module(
                                    section.text,
                                    str(document.metadata.get("business_module", "通用知识")),
                                ),
                                "chunk_index": chunk_index,
                                "section_index": section_index,
                                "section_title": section.title,
                                "heading_path": section.heading_path,
                                "start_line": section.start_line,
                                "split_index": split_index,
                                "start_unit": start,
                                "end_unit": end,
                                **location_metadata,
                            },
                        )
                    )
                    chunk_index += 1
        return chunks

    def _split_parsed_blocks(
        self,
        document: Document,
        document_metadata: dict,
        start_index: int = 0,
    ) -> list[Chunk]:
        """按解析 block 切片，保留来源结构和权限信息。"""

        chunks: list[Chunk] = []
        chunk_index = start_index
        content_blocks = [
            block
            for block in document.parsed_blocks
            if block.block_type != "heading" and block.text.strip()
        ]
        if not content_blocks:
            return []

        for block_index, block in enumerate(content_blocks):
            chunk_source_text = _block_text_with_context(block)
            for split_index, chunk_text, start, end in self._split_section_text(chunk_source_text):
                section_title = block.section_path[-1] if block.section_path else None
                location_metadata = _block_location_metadata(block)
                block_metadata = _chunk_block_metadata(block.metadata)
                page_warning_codes = _page_warning_codes(
                    document.metadata,
                    block.page_number,
                )
                block_metadata.setdefault("page_warning_codes", page_warning_codes)
                block_metadata.setdefault("chunk_parse_warning_codes", page_warning_codes)
                table_metadata = _table_parse_metadata(document.metadata, block)
                chunks.append(
                    Chunk(
                        id=self._chunk_id(document.id, chunk_index, chunk_text),
                        document_id=document.id,
                        text=chunk_text,
                        metadata={
                            **document_metadata,
                            **block_metadata,
                            "business_module": _infer_section_business_module(
                                chunk_text,
                                str(document.metadata.get("business_module", "通用知识")),
                            ),
                            "chunk_index": chunk_index,
                            "block_index": block_index,
                            "block_id": block.block_id,
                            "block_type": block.block_type,
                            "source_block_ids": [block.block_id],
                            "section_title": section_title,
                            "section_path": block.section_path,
                            "heading_path": block.section_path,
                            "parent_block_id": block.parent_block_id,
                            "previous_block_id": block.previous_block_id,
                            "next_block_id": block.next_block_id,
                            "split_index": split_index,
                            "start_unit": start,
                            "end_unit": end,
                            "chunk_parse_quality_status": block.quality_status,
                            **table_metadata,
                            **location_metadata,
                        },
                    )
                )
                chunk_index += 1
        return chunks

    def _split_section_text(self, text: str) -> list[tuple[int, str, int, int]]:
        units = _text_units(text)
        if not units:
            return []

        # 中文资料通常没有稳定空格，短词场景按字符切；英文或表格文本按空白 token 切。
        # overlap 保留上下文，减少切片边界刚好切断关键处理步骤的概率。
        joiner = "" if _should_split_by_character(text) else " "
        step = self.chunk_size - self.chunk_overlap
        chunks: list[tuple[int, str, int, int]] = []
        for split_index, start in enumerate(range(0, len(units), step)):
            end = min(start + self.chunk_size, len(units))
            chunk_text = joiner.join(units[start:end]).strip()
            if chunk_text:
                chunks.append((split_index, chunk_text, start, end))
            if end == len(units):
                break
        return chunks

    @staticmethod
    def _chunk_id(document_id: str, chunk_index: int, text: str) -> str:
        digest = hashlib.sha256()
        digest.update(document_id.encode("utf-8"))
        digest.update(str(chunk_index).encode("utf-8"))
        digest.update(text.encode("utf-8"))
        return digest.hexdigest()[:24]


def _split_markdown_sections(text: str) -> list[_Section]:
    lines = text.splitlines()
    sections: list[_Section] = []
    heading_stack: list[tuple[int, str]] = []
    body_lines: list[str] = []
    section_start_line = 1

    def flush() -> None:
        body = "\n".join(body_lines).strip()
        if not body:
            return
        heading_text = "\n".join(
            f"{'#' * level} {title}"
            for level, title in heading_stack
        )
        section_text = f"{heading_text}\n\n{body}".strip() if heading_text else body
        sections.append(
            _Section(
                text=section_text,
                title=heading_stack[-1][1] if heading_stack else None,
                heading_path=[title for _, title in heading_stack],
                start_line=section_start_line,
            )
        )

    for line_no, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if not match:
            body_lines.append(line)
            continue

        flush()
        level = len(match.group(1))
        title = match.group(2).strip()
        heading_stack = [
            (existing_level, existing_title)
            for existing_level, existing_title in heading_stack
            if existing_level < level
        ]
        heading_stack.append((level, title))
        body_lines = []
        section_start_line = line_no

    flush()
    if sections:
        return sections
    # 没有标题的纯文本仍然保留为一个 section，避免资料因为结构不规范而丢失。
    stripped = text.strip()
    if not stripped:
        return []
    return [_Section(text=stripped, title=None, heading_path=[], start_line=1)]


def _text_units(text: str) -> list[str]:
    if _should_split_by_character(text):
        return list(text)
    return text.split()


def _should_split_by_character(text: str) -> bool:
    words = text.split()
    return len(words) < 20 and len(text) > 0


def _infer_section_business_module(text: str, default: str) -> str:
    lowered = text.lower()
    if _contains_any(lowered, ("地址", "address")):
        return "地址校验"
    if _contains_any(lowered, ("派单", "dispatch")):
        return "智能派单"
    if _contains_any(lowered, ("光猫", "los", "pon", "onu", "ont", "设备", "device")):
        return "设备维护"
    if _contains_any(lowered, ("异常码", "错误码", "接口", "api", "error")):
        return "异常处理"
    if _contains_any(lowered, ("工单", "work_order", "order")):
        return "工单流转"
    return default


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _chunk_document_metadata(document_metadata: dict) -> dict:
    metadata = _compact_chunk_metadata(document_metadata)
    document_status = str(
        document_metadata.get("parse_quality_status") or "parsed_success"
    )
    metadata["document_parse_quality_status"] = document_status
    metadata["chunk_parse_quality_status"] = document_status
    metadata["document_ocr_status"] = _document_ocr_status(document_metadata)

    ocr_provider = document_metadata.get("ocr_provider")
    if ocr_provider not in (None, ""):
        metadata["document_ocr_provider"] = ocr_provider

    ocr_page_count = _document_ocr_page_count(document_metadata)
    if ocr_page_count is not None:
        metadata["document_ocr_page_count"] = ocr_page_count

    warnings = document_metadata.get("parse_warnings") or []
    if warnings:
        metadata["document_parse_warning_count"] = len(warnings)

    metadata.setdefault("permission_tags", ["public"])
    return metadata


def _chunk_block_metadata(block_metadata: dict) -> dict:
    return _compact_chunk_metadata(block_metadata)


def _compact_chunk_metadata(metadata: dict) -> dict:
    return {
        key: value
        for key, value in metadata.items()
        if key not in _CHUNK_METADATA_EXCLUDED_KEYS
        and (
            key in _PRESERVE_EMPTY_CHUNK_KEYS
            or not _is_empty_metadata_value(value)
        )
    }


def _is_empty_metadata_value(value) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _document_ocr_status(document_metadata: dict) -> str:
    warnings = set(document_metadata.get("parse_warnings") or [])
    if bool(document_metadata.get("ocr_applied", False)):
        return "applied"
    if not bool(document_metadata.get("ocr_required", False)):
        return "not_required"
    if "ocr_disabled" in warnings:
        return "required_disabled"
    if document_metadata.get("ocr_unavailable_reason") or "ocr_fallback_unavailable" in warnings:
        return "required_failed"
    return "required_not_applied"


def _document_ocr_page_count(document_metadata: dict) -> int | None:
    raw_count = document_metadata.get("ocr_page_count")
    if isinstance(raw_count, int):
        return raw_count
    raw_pages = document_metadata.get("ocr_pages")
    if isinstance(raw_pages, list):
        return len(raw_pages)
    return None


def _table_parse_metadata(document_metadata: dict, block: ParsedBlock) -> dict:
    route = str(document_metadata.get("table_parser_route") or "").strip().lower()
    if not route:
        return {}

    if block.block_type != "table":
        return {
            "table_parse_applied": False,
            "table_parse_status": "skipped",
            "table_parse_skip_reason": f"block_type_is_{block.block_type}",
        }

    if _table_route_was_applied(document_metadata, route):
        return {
            "table_parse_applied": True,
            "table_parse_status": "applied",
        }

    return {
        "table_parse_applied": False,
        "table_parse_status": "fallback",
        "table_parse_skip_reason": _table_parse_fallback_reason(
            document_metadata,
            route,
        ),
    }


def _table_route_was_applied(document_metadata: dict, route: str) -> bool:
    route_key = f"{route}_used"
    return bool(document_metadata.get(route_key) or document_metadata.get("external_parser_used"))


def _table_parse_fallback_reason(document_metadata: dict, route: str) -> str:
    warnings = set(document_metadata.get("parse_warnings") or [])
    fallback_warning = f"{route}_fallback_unavailable"
    if fallback_warning in warnings:
        return fallback_warning
    if bool(document_metadata.get(f"{route}_attempted")):
        return f"{route}_not_applied"
    return "table_parser_not_attempted"


def _page_warning_codes(
    document_metadata: dict,
    page_number: int | None,
) -> list[str]:
    if page_number is None:
        return []
    for report in document_metadata.get("pdf_page_reports") or []:
        if not isinstance(report, dict):
            continue
        if int(report.get("page_number") or 0) != page_number:
            continue
        return [
            str(code)
            for code in report.get("warning_codes") or []
        ]
    return []


def _extract_section_location(section_title: str | None) -> dict[str, str | int]:
    if not section_title:
        return {}
    page_match = PAGE_TITLE_RE.match(section_title)
    if page_match:
        return {"page_number": int(page_match.group(1))}
    slide_match = SLIDE_TITLE_RE.match(section_title)
    if slide_match:
        return {"slide_number": int(slide_match.group(1))}
    segment_match = SEGMENT_TITLE_RE.match(section_title)
    if segment_match:
        return {"time_range": segment_match.group(1)}
    return {}


def _block_text_with_context(block: ParsedBlock) -> str:
    prefix: list[str] = []
    if block.section_path:
        prefix.append(f"章节：{' > '.join(block.section_path)}")
    if block.block_type == "table":
        prefix.append("内容类型：表格")
    if block.page_number is not None:
        prefix.append(f"页码：{block.page_number}")
    if not prefix:
        return block.text
    return "\n".join([*prefix, block.text]).strip()


def _block_location_metadata(block: ParsedBlock) -> dict[str, str | int]:
    metadata: dict[str, str | int] = {}
    if block.page_number is not None:
        metadata["page_number"] = block.page_number
    for key in ("slide_number", "time_range"):
        value = block.metadata.get(key)
        if value not in (None, ""):
            metadata[key] = value
    return metadata
