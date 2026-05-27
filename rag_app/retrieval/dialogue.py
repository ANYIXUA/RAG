"""多轮对话上下文维护与跟进问句改写。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag_app.retrieval.query import normalize_query


FOLLOW_UP_PRONOUN_RE = re.compile(r"(这个|这个问题|这个情况|它|他|她|那|那个|上述|上面|前面)")
FOLLOW_UP_START_RE = re.compile(r"^(那|然后|另外|还有|关于这个|关于它|继续|顺便)")


@dataclass(frozen=True)
class ConversationTurn:
    """单轮对话摘要，用于后续跟进问答。"""

    question: str
    rewritten_query: str
    intent_label: str
    retrieved_titles: list[str]
    answer_summary: str


class ConversationMemory:
    """基于 session_id 的轻量会话记忆。"""

    def __init__(self, max_turns_per_session: int = 12) -> None:
        self.max_turns_per_session = max_turns_per_session
        self._sessions: dict[str, list[ConversationTurn]] = {}

    def get_recent_turns(self, session_id: str | None, limit: int = 3) -> list[ConversationTurn]:
        if not session_id:
            return []
        turns = self._sessions.get(session_id, [])
        if limit <= 0:
            return []
        return turns[-limit:]

    def append_turn(self, session_id: str | None, turn: ConversationTurn) -> None:
        if not session_id:
            return
        turns = self._sessions.setdefault(session_id, [])
        turns.append(turn)
        if len(turns) > self.max_turns_per_session:
            self._sessions[session_id] = turns[-self.max_turns_per_session :]


def rewrite_query_with_context(
    question: str,
    history: list[ConversationTurn],
    max_context_terms: int = 8,#最多从历史中提取多少个关键词
) -> tuple[str, bool, list[str]]:
    """如果是跟进问句，则拼接上下文关键词，扩展成更完整的检索问题。"""

    normalized = normalize_query(question)#标准化问题
    if not normalized:
        return normalized, False, []
    if not history:
        return normalized, False, []
    if not is_follow_up_question(normalized):
        return normalized, False, []
    #如果是追问，就从最近历史中提取关键词
    context_terms = _collect_context_terms(history, max_terms=max_context_terms)
    if not context_terms: #历史中没有关键词，强行改写也没有意义
        return normalized, False, []
    #重新进行改写
    contextual_query = normalize_query(f"{normalized} {' '.join(context_terms)}")
    return contextual_query, True, context_terms


def is_follow_up_question(question: str) -> bool:
    """检测当前问题是否依赖上文（代词、省略、承接词）。"""

    normalized = normalize_query(question)
    if not normalized:
        return False
    if FOLLOW_UP_PRONOUN_RE.search(normalized):
        return True
    if FOLLOW_UP_START_RE.search(normalized):
        return True
    # 短句且不包含明显业务主体时，通常是跟进追问。
    if len(normalized) <= 8 and "?" in normalized:
        return True
    if len(normalized) <= 8 and "？" in normalized:
        return True
    return False


def summarize_answer(answer: str, max_chars: int = 120) -> str:
    """生成回答摘要，避免会话状态无限膨胀。"""

    normalized = normalize_query(answer)
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars]}..."


def _collect_context_terms(history: list[ConversationTurn], max_terms: int) -> list[str]:
    terms: list[str] = []
    for turn in history[-2:]:
        if turn.rewritten_query:
            terms.append(turn.rewritten_query)
        terms.extend(title for title in turn.retrieved_titles if title)
    return _dedupe([normalize_query(term) for term in terms if normalize_query(term)])[:max_terms]


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
