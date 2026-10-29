from __future__ import annotations

import hashlib
import re

from .models import ParsedDocument, TextChunk


_HEADING_RE = re.compile(r"^(?:#{1,6}\s+.+|第[一二三四五六七八九十百\d]+[章节]\s*.+)$")
_CJK_RE = re.compile(r"[\u3400-\u9fff]")


def split_document(
    document: ParsedDocument,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    min_section_chars: int = 120,
) -> list[TextChunk]:
    return list(
        iter_document_chunks(
            document,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_section_chars=min_section_chars,
        )
    )


def iter_document_chunks(
    document: ParsedDocument,
    *,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    min_section_chars: int = 120,
):
    """先按页和标题/段落保留结构，再对超长段做 800/120 滑窗。"""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be in [0, chunk_size)")

    chunk_index = 0
    for page in document.pages:
        for section_index, (section_title, section_text) in enumerate(
            _structural_sections(page.text, min_section_chars=min_section_chars)
        ):
            units, joiner = _text_units(section_text)
            if not units:
                continue
            step = chunk_size - chunk_overlap
            for split_index, start in enumerate(range(0, len(units), step)):
                end = min(start + chunk_size, len(units))
                chunk_text = joiner.join(units[start:end]).strip()
                if not chunk_text:
                    continue
                chunk_id = _chunk_id(
                    document.document_id,
                    page.page_number,
                    chunk_index,
                    chunk_text,
                )
                metadata = {
                    **document.metadata,
                    "source": document.source,
                    "source_path": document.source_path,
                    "page": page.page_number,
                    "page_number": page.page_number,
                    "chunk_id": chunk_id,
                    "document_id": document.document_id,
                    "chunk_index": chunk_index,
                    "section_index": section_index,
                    "section_title": section_title,
                    "split_index": split_index,
                    "start_unit": start,
                    "end_unit": end,
                    "parser": document.parser,
                }
                yield TextChunk(
                    id=chunk_id,
                    document_id=document.document_id,
                    text=chunk_text,
                    metadata=metadata,
                )
                chunk_index += 1
                if end == len(units):
                    break


def _structural_sections(text: str, *, min_section_chars: int) -> list[tuple[str | None, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    sections: list[tuple[str | None, str]] = []
    current_title: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        body = "\n".join(buffer).strip()
        if body:
            sections.append((current_title, body))
        buffer = []

    for line in lines:
        if _HEADING_RE.match(line):
            flush()
            current_title = line.lstrip("# ").strip()
            buffer.append(line)
            continue
        buffer.append(line)
        if sum(len(item) for item in buffer) >= min_section_chars and line.endswith(("。", ".", "！", "!", "？", "?")):
            flush()
    flush()
    return _merge_short_sections(sections, min_section_chars)


def _merge_short_sections(
    sections: list[tuple[str | None, str]],
    min_section_chars: int,
) -> list[tuple[str | None, str]]:
    merged: list[tuple[str | None, str]] = []
    for title, body in sections:
        if merged and len(body) < min_section_chars and merged[-1][0] == title:
            previous_title, previous_body = merged[-1]
            merged[-1] = (previous_title, f"{previous_body}\n{body}")
        else:
            merged.append((title, body))
    return merged


def _text_units(text: str) -> tuple[list[str], str]:
    compact = text.replace("\n", "")
    cjk_ratio = len(_CJK_RE.findall(compact)) / max(len(compact), 1)
    if cjk_ratio >= 0.3 and len(text.split()) <= 3:
        return list(compact), ""
    return text.split(), " "


def _chunk_id(
    document_id: str,
    page_number: int,
    chunk_index: int,
    text: str,
) -> str:
    payload = f"{document_id}\0{page_number}\0{chunk_index}\0{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]
