"""异常码识别和标准化工具。"""

from __future__ import annotations

import re


ERROR_CODE_RE = re.compile(r"\b[A-Za-z][-_]?\d{2,6}\b")


def normalize_error_code(value: str) -> str:
    """统一异常码大小写和分隔符，保证离线入库和在线查询能精确匹配。"""

    return value.strip().upper().replace("-", "").replace("_", "")


def extract_error_code(text: str) -> str | None:
    """从文本中提取第一个异常码。"""

    codes = extract_error_codes(text)
    return codes[0] if codes else None


def extract_error_codes(text: str) -> list[str]:
    """从文本中提取所有异常码，按出现顺序去重。"""

    result: list[str] = []
    seen: set[str] = set()
    for match in ERROR_CODE_RE.finditer(text):
        code = normalize_error_code(match.group(0))
        if code in seen:
            continue
        seen.add(code)
        result.append(code)
    return result
