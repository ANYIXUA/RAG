"""多轮对话上下文维护与跟进问句改写。"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from rag_app.retrieval.query import normalize_query


FOLLOW_UP_PRONOUN_RE = re.compile(r"(这个|这个问题|这个情况|它|他|她|那|那个|上述|上面|前面)")
FOLLOW_UP_START_RE = re.compile(r"^(那|然后|另外|还有|关于这个|关于它|继续|顺便)")
SHORT_FOLLOW_UP_RE = re.compile(
    r"^(下一步|下步|怎么判断|如何判断|怎么确认|如何确认|要先看什么|先看什么|"
    r"还要看什么|需要派单吗|要派单吗|怎么处理|怎么办|咋办|为什么|原因呢|还有吗)"
)
SESSION_PART_RE = re.compile(r"[^a-zA-Z0-9_-]+")


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


class RedisConversationMemory(ConversationMemory):
    """基于 Redis 的短期会话记忆，适合多 worker 和服务重启场景。"""

    def __init__(
        self,
        redis_url: str,
        max_turns_per_session: int = 12,
        ttl_seconds: int = 7200,
        key_prefix: str = "rag:conversation",
    ) -> None:
        super().__init__(max_turns_per_session=max_turns_per_session)
        if not redis_url:
            raise RuntimeError("Redis conversation memory requires RAG_REDIS_URL")
        try:
            import redis
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Redis conversation memory requires dependency: pip install redis"
            ) from exc
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix.rstrip(":")
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get_recent_turns(self, session_id: str | None, limit: int = 3) -> list[ConversationTurn]:
        if not session_id or limit <= 0:
            return []
        raw_items = self._client.lrange(self._key(session_id), -limit, -1)
        turns: list[ConversationTurn] = []
        for raw_item in raw_items:
            try:
                payload = json.loads(raw_item)
                turns.append(_turn_from_dict(payload))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return turns

    def append_turn(self, session_id: str | None, turn: ConversationTurn) -> None:
        if not session_id:
            return
        key = self._key(session_id)
        self._client.rpush(key, json.dumps(asdict(turn), ensure_ascii=False))
        self._client.ltrim(key, -self.max_turns_per_session, -1)
        if self.ttl_seconds > 0:
            self._client.expire(key, self.ttl_seconds)

    def _key(self, session_id: str) -> str:
        return f"{self.key_prefix}:{session_id}"


def create_conversation_memory(settings: Any) -> ConversationMemory:
    provider = str(getattr(settings, "conversation_memory_provider", "memory")).lower()
    max_turns = int(getattr(settings, "conversation_memory_max_turns", 12))
    if provider == "redis":
        return RedisConversationMemory(
            redis_url=str(getattr(settings, "redis_url", "") or ""),
            max_turns_per_session=max_turns,
            ttl_seconds=int(getattr(settings, "conversation_memory_ttl_seconds", 7200)),
        )
    return ConversationMemory(max_turns_per_session=max_turns)


def generate_session_id(
    tenant_id: str | None = None,
    source: str = "api",
    now: datetime | None = None,
    random_hex: str | None = None,
) -> str:
    """生成便于排查的会话 ID，时间段使用 YYYYMMDDHHMMSS。"""

    actual_now = now or datetime.now(timezone.utc)
    timestamp = actual_now.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")
    tenant = _session_id_part(tenant_id or "default")
    source_part = _session_id_part(source or "api")
    suffix = (random_hex or uuid4().hex)[:8].lower()
    return f"sess_{timestamp}_{tenant}_{source_part}_{suffix}"


def rewrite_query_with_context(
    question: str,
    history: list[ConversationTurn],
    max_context_terms: int = 8,#最多从历史中提取多少个关键词
    coreference_enabled: bool = True,
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
    resolved_query = (
        resolve_references_with_rules(normalized, history)
        if coreference_enabled
        else normalized
    )
    #重新进行改写
    contextual_query = normalize_query(f"{resolved_query} {' '.join(context_terms)}")
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
    if SHORT_FOLLOW_UP_RE.search(normalized):
        return True
    return False


def resolve_references_with_rules(question: str, history: list[ConversationTurn]) -> str:
    """基于规则把追问中的指代词替换成最近一轮业务主题。"""

    normalized = normalize_query(question)
    reference = _primary_reference(history)
    if not normalized or not reference:
        return normalized
    if FOLLOW_UP_PRONOUN_RE.search(normalized):
        return normalize_query(FOLLOW_UP_PRONOUN_RE.sub(reference, normalized, count=1))
    if FOLLOW_UP_START_RE.search(normalized):
        suffix = FOLLOW_UP_START_RE.sub("", normalized, count=1).strip()
        return normalize_query(f"{reference} {suffix or normalized}")
    if SHORT_FOLLOW_UP_RE.search(normalized):
        return normalize_query(f"{reference} {normalized}")
    return normalized


def summarize_answer(answer: str, max_chars: int = 120) -> str:
    """生成回答摘要，避免会话状态无限膨胀。"""

    normalized = normalize_query(answer)
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars]}..."


def _collect_context_terms(history: list[ConversationTurn], max_terms: int) -> list[str]:
    terms: list[str] = []
    for turn in history[-2:]:
        terms.extend(title for title in turn.retrieved_titles if title)
        if turn.rewritten_query:
            terms.append(turn.rewritten_query)
        if turn.question:
            terms.append(turn.question)
    return _dedupe([normalize_query(term) for term in terms if normalize_query(term)])[:max_terms]


def _primary_reference(history: list[ConversationTurn]) -> str:
    for turn in reversed(history):
        for title in turn.retrieved_titles:
            normalized = normalize_query(title)
            if normalized:
                return normalized
        for candidate in (turn.rewritten_query, turn.question):
            normalized = normalize_query(candidate)
            if normalized:
                return normalized
    return ""


def _turn_from_dict(payload: dict[str, Any]) -> ConversationTurn:
    return ConversationTurn(
        question=str(payload.get("question") or ""),
        rewritten_query=str(payload.get("rewritten_query") or ""),
        intent_label=str(payload.get("intent_label") or ""),
        retrieved_titles=[
            str(item)
            for item in payload.get("retrieved_titles") or []
            if str(item).strip()
        ],
        answer_summary=str(payload.get("answer_summary") or ""),
    )


def _session_id_part(value: str) -> str:
    cleaned = SESSION_PART_RE.sub("-", value.strip()).strip("-_").lower()
    return cleaned[:32] or "default"


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
