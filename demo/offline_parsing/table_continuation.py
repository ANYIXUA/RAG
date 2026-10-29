from __future__ import annotations

import hashlib
import re

from .models import MergedTable, TableCandidate, TableRow, TextChunk


_CODE_LIKE_RE = re.compile(r"^[A-Z]{1,5}[-_]?\d{2,}$", re.IGNORECASE)


def merge_table_candidates(candidates: list[TableCandidate]) -> list[MergedTable]:
    """合并固定 badcase 的跨页续表。

    这是教学启发式：只在页相邻、前表靠页尾、后表靠页首且列数一致时合并。
    每行仍保留真实页码和 bbox；规则不能代表任意 PDF 的生产能力。
    """

    ordered = sorted(candidates, key=lambda item: (item.page_number, item.bbox[1]))
    merged: list[MergedTable] = []
    previous_candidate: TableCandidate | None = None
    for candidate in ordered:
        if not candidate.rows:
            continue
        if merged and previous_candidate and _is_continuation(previous_candidate, candidate):
            table = merged[-1]
            rows = candidate.rows
            if table.header and rows and _same_row(table.header, rows[0]):
                rows = rows[1:]
            merged[-1] = MergedTable(
                table_id=table.table_id,
                header=table.header,
                rows=[
                    *table.rows,
                    *[
                        TableRow(
                            values=_clean_row(row),
                            source_page=candidate.page_number,
                            table_bbox=candidate.bbox,
                        )
                        for row in rows
                        if any(cell.strip() for cell in row)
                    ],
                ],
                source_pages=[*table.source_pages, candidate.page_number],
                bbox_by_page={**table.bbox_by_page, candidate.page_number: candidate.bbox},
            )
        else:
            header, data_rows = _split_header(candidate.rows)
            table_id = _table_id(candidate, header)
            merged.append(
                MergedTable(
                    table_id=table_id,
                    header=header,
                    rows=[
                        TableRow(
                            values=_clean_row(row),
                            source_page=candidate.page_number,
                            table_bbox=candidate.bbox,
                        )
                        for row in data_rows
                        if any(cell.strip() for cell in row)
                    ],
                    source_pages=[candidate.page_number],
                    bbox_by_page={candidate.page_number: candidate.bbox},
                )
            )
        previous_candidate = candidate
    return merged


def extract_table_candidates(pdf_path) -> list[TableCandidate]:
    """使用 PyMuPDF 的表格线检测生成单页候选，供固定样例验收使用。"""

    try:
        import pymupdf as fitz
    except ModuleNotFoundError:
        try:
            import fitz
        except ModuleNotFoundError as exc:
            raise RuntimeError("缺少 PyMuPDF，无法提取表格") from exc

    candidates: list[TableCandidate] = []
    with fitz.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            finder = page.find_tables()
            for table in finder.tables:
                rows = [
                    [str(cell or "").strip() for cell in row]
                    for row in table.extract()
                ]
                candidates.append(
                    TableCandidate(
                        page_number=page_index + 1,
                        bbox=tuple(float(value) for value in table.bbox),
                        page_width=float(page.rect.width),
                        page_height=float(page.rect.height),
                        rows=rows,
                        source=str(pdf_path),
                    )
                )
    return candidates


def table_to_chunk(table: MergedTable, *, source: str) -> TextChunk:
    """把跨页逻辑表转换成一个可追溯 Chunk，保留所有真实来源页。"""

    lines: list[str] = []
    if table.header:
        lines.append("\t".join(table.header))
    lines.extend("\t".join(row.values) for row in table.rows)
    text = "\n".join(lines)
    document_id = hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]
    chunk_payload = f"{source}\0{table.table_id}\0{text}".encode("utf-8")
    chunk_id = hashlib.sha256(chunk_payload).hexdigest()[:24]
    return TextChunk(
        id=chunk_id,
        document_id=document_id,
        text=text,
        metadata={
            "chunk_id": chunk_id,
            "document_id": document_id,
            "source": source,
            "page_number": table.source_pages[0],
            "page": table.source_pages[0],
            "source_pages": table.source_pages,
            "table_id": table.table_id,
            "block_type": "table",
            "table_bbox_by_page": table.bbox_by_page,
        },
    )


def _is_continuation(previous: TableCandidate, current: TableCandidate) -> bool:
    if current.page_number != previous.page_number + 1:
        return False
    if previous.bbox[3] < previous.page_height * 0.85:
        return False
    if current.bbox[1] > current.page_height * 0.15:
        return False
    return _column_count(previous) == _column_count(current)


def _column_count(candidate: TableCandidate) -> int:
    return max((len(row) for row in candidate.rows), default=0)


def _split_header(rows: list[list[str]]) -> tuple[list[str] | None, list[list[str]]]:
    first = _clean_row(rows[0])
    if _looks_like_header(first):
        return first, rows[1:]
    return None, rows


def _looks_like_header(row: list[str]) -> bool:
    nonempty = [cell for cell in row if cell]
    if not nonempty:
        return False
    return not any(_CODE_LIKE_RE.fullmatch(cell) for cell in nonempty)


def _same_row(left: list[str], right: list[str]) -> bool:
    return [cell.casefold() for cell in _clean_row(left)] == [
        cell.casefold() for cell in _clean_row(right)
    ]


def _clean_row(row: list[str]) -> list[str]:
    return [str(cell or "").strip() for cell in row]


def _table_id(candidate: TableCandidate, header: list[str] | None) -> str:
    signature = (
        f"{candidate.source}\0{candidate.page_number}\0"
        f"{candidate.bbox}\0{header or []}"
    )
    return f"table-{hashlib.sha256(signature.encode('utf-8')).hexdigest()[:16]}"
