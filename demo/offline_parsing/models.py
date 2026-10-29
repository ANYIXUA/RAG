from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Metadata = dict[str, Any]
BBox = tuple[float, float, float, float]


@dataclass(frozen=True)
class ParsedPage:
    """解析后的真实页面；TXT/Word 没有分页信息时统一使用第 1 页。"""

    page_number: int
    text: str
    width: float | None = None
    height: float | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedDocument:
    """独立 Demo 的解析器统一输出。"""

    document_id: str
    source: str
    source_path: str
    pages: list[ParsedPage]
    parser: str
    parse_seconds: float = 0.0
    metadata: Metadata = field(default_factory=dict)
    quality_status: str = "parsed_success"
    quality_warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ParseOutcome:
    source: str
    document: ParsedDocument | None = None
    error_type: str | None = None
    error_message: str | None = None
    parse_seconds: float = 0.0


@dataclass(frozen=True)
class TextChunk:
    id: str
    document_id: str
    text: str
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    id: str
    text: str
    metadata: Metadata
    score: float


@dataclass(frozen=True)
class TableCandidate:
    """单页表格候选；bbox 和 page_number 必须来自原 PDF。"""

    page_number: int
    bbox: BBox
    page_width: float
    page_height: float
    rows: list[list[str]]
    source: str = ""


@dataclass(frozen=True)
class TableRow:
    values: list[str]
    source_page: int
    table_bbox: BBox


@dataclass(frozen=True)
class MergedTable:
    table_id: str
    header: list[str] | None
    rows: list[TableRow]
    source_pages: list[int]
    bbox_by_page: dict[int, BBox]
