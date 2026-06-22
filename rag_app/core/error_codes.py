"""Error-code detection and normalization helpers."""

from __future__ import annotations

import re


ERROR_CODE_RE = re.compile(r"\b[A-Za-z][-_]?\d{2,6}\b")
ERROR_CONTEXT_BEFORE_RE = re.compile(
    r"(异常码|错误码|故障码|报错码|返回码|状态码|接口返回|error\s*code|err(?:or)?\s*code)\s*[:：=为-]*\s*$",
    re.IGNORECASE,
)
NON_ERROR_CONTEXT_RE = re.compile(
    r"(不是|非|普通|资料|条目|章节|规范|标准|表号|表格|图号|编号|编码)",
    re.IGNORECASE,
)


def normalize_error_code(value: str) -> str:
    """Normalize code case and separators for indexing and lookup."""

    return value.strip().upper().replace("-", "").replace("_", "")


def extract_error_code(text: str) -> str | None:
    """Extract the first strict error code from text."""

    codes = extract_error_codes(text)
    return codes[0] if codes else None


def extract_error_codes(text: str) -> list[str]:
    """Extract strict error codes that should drive exact-code retrieval."""

    result: list[str] = []
    seen: set[str] = set()
    for match in ERROR_CODE_RE.finditer(text):
        if not _is_strict_error_code_match(text, match):
            continue
        code = normalize_error_code(match.group(0))
        if code in seen:
            continue
        seen.add(code)
        result.append(code)
    return result


def extract_detected_codes(text: str) -> list[str]:
    """Extract all ordinary document codes without treating them as errors."""

    result: list[str] = []
    seen: set[str] = set()
    for match in ERROR_CODE_RE.finditer(text):
        code = normalize_error_code(match.group(0))
        if code in seen:
            continue
        seen.add(code)
        result.append(code)
    return result


def _is_strict_error_code_match(text: str, match: re.Match[str]) -> bool:
    code = normalize_error_code(match.group(0))
    if re.fullmatch(r"E\d{2,6}", code):
        return True

    left = text[max(0, match.start() - 16):match.start()]
    right = text[match.end():min(len(text), match.end() + 16)]
    context = f"{left}{right}"
    if NON_ERROR_CONTEXT_RE.search(context):
        return False
    return ERROR_CONTEXT_BEFORE_RE.search(left) is not None
