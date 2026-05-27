"""文本匹配和本地向量化使用的分词工具。"""

from __future__ import annotations

import re


ASCII_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
CJK_BLOCK_RE = re.compile(r"[\u4e00-\u9fff]+")


def tokenize_for_matching(text: str) -> list[str]:
    """提取适合中英文混合检索的轻量 token。"""

    tokens = [token.lower() for token in ASCII_TOKEN_RE.findall(text)]
    for block in CJK_BLOCK_RE.findall(text):
        tokens.extend(block)
        tokens.extend(block[index : index + 2] for index in range(len(block) - 1))
    return tokens


def tokenize_for_keyword_search(text: str) -> list[str]:
    """提取适合关键词检索的 token，避免单字带来过多噪声。"""

    tokens = [token.lower() for token in ASCII_TOKEN_RE.findall(text)]
    for block in CJK_BLOCK_RE.findall(text):
        if len(block) == 1:
            tokens.append(block)
        else:
            tokens.extend(block[index : index + 2] for index in range(len(block) - 1))
    return tokens
