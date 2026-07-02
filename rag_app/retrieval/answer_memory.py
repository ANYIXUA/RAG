"""Redis/manual answer overrides and feedback hot-cache support."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import uuid4

from rag_app.core.config import Settings


TRANSIENT_CATEGORIES = {"incident", "outage", "maintenance", "notice", "campaign"}


@dataclass(frozen=True)
class AnswerOverrideInput:
    question: str
    answer: str
    tenant_id: str
    permission_tags: tuple[str, ...] | list[str] | str | None = ("public",)
    category: str = "manual"
    ttl_seconds: int | None = None
    created_by: str | None = None
    enabled: bool = True
    priority: int = 100
    promote_to_long_term: bool = False


@dataclass(frozen=True)
class AnswerOverridePatch:
    answer: str | None = None
    permission_tags: tuple[str, ...] | list[str] | str | None = None
    category: str | None = None
    ttl_seconds: int | None = None
    enabled: bool | None = None
    priority: int | None = None
    promote_to_long_term: bool | None = None
    updated_by: str | None = None


@dataclass(frozen=True)
class AnswerMemoryRecord:
    override_id: str
    question: str
    normalized_question: str
    answer: str
    tenant_id: str
    permission_tags: tuple[str, ...]
    source: str
    category: str
    enabled: bool
    priority: int
    ttl_seconds: int | None
    created_at: str
    updated_at: str
    created_by: str | None = None
    updated_by: str | None = None
    promote_to_long_term: bool = False
    request_id: str | None = None
    feedback_id: str | None = None
    hit_count: int = 0
    expires_at: float | None = None


@dataclass(frozen=True)
class AnswerMemoryHit:
    override_id: str
    answer: str
    source: str
    answer_source: str
    category: str
    tenant_id: str
    permission_tags: tuple[str, ...]
    promote_to_long_term: bool = False


@dataclass(frozen=True)
class NegativeFeedbackStats:
    question: str
    normalized_question: str
    tenant_id: str
    permission_tags: tuple[str, ...]
    count: int = 0
    labels: tuple[str, ...] = ()
    last_request_id: str | None = None
    last_feedback_id: str | None = None
    updated_at: str | None = None


class AnswerMemoryStore(Protocol):
    def lookup(
        self,
        question: str,
        tenant_id: str | None,
        permission_tags: tuple[str, ...] | list[str] | str | None,
    ) -> AnswerMemoryHit | None:
        ...

    def upsert_override(self, payload: AnswerOverrideInput) -> AnswerMemoryRecord:
        ...

    def patch_override(
        self,
        override_id: str,
        patch: AnswerOverridePatch,
    ) -> AnswerMemoryRecord:
        ...

    def delete_override(self, override_id: str) -> bool:
        ...

    def list_overrides(
        self,
        tenant_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[AnswerMemoryRecord]:
        ...


class NullAnswerMemoryStore:
    """No-op answer memory used when the feature is disabled."""

    def lookup(self, question, tenant_id=None, permission_tags=None):
        del question, tenant_id, permission_tags
        return None

    def upsert_override(self, payload: AnswerOverrideInput) -> AnswerMemoryRecord:
        raise RuntimeError("answer memory is disabled")

    def patch_override(self, override_id: str, patch: AnswerOverridePatch) -> AnswerMemoryRecord:
        del override_id, patch
        raise RuntimeError("answer memory is disabled")

    def delete_override(self, override_id: str) -> bool:
        del override_id
        return False

    def list_overrides(self, tenant_id: str | None = None, enabled: bool | None = None):
        del tenant_id, enabled
        return []


class MemoryAnswerMemoryStore:
    """Deterministic in-memory implementation for unit tests."""

    def __init__(self) -> None:
        self._manual: dict[tuple[str, str], AnswerMemoryRecord] = {}
        self._hot: dict[tuple[str, str], AnswerMemoryRecord] = {}
        self._by_id: dict[str, tuple[str, str]] = {}
        self._negative: dict[tuple[str, str], NegativeFeedbackStats] = {}

    def lookup(
        self,
        question: str,
        tenant_id: str | None,
        permission_tags: tuple[str, ...] | list[str] | str | None,
    ) -> AnswerMemoryHit | None:
        tenant = normalize_tenant_id(tenant_id)
        normalized = normalize_answer_question(question)
        request_tags = normalize_permission_tags(permission_tags)
        key = (tenant, _question_hash(normalized))
        for records, answer_source in (
            (self._manual, "redis_manual_override"),
            (self._hot, "redis_hot_cache"),
        ):
            record = records.get(key)
            if not _record_available(record, request_tags):
                continue
            assert record is not None
            records[key] = replace(record, hit_count=record.hit_count + 1)
            return AnswerMemoryHit(
                override_id=record.override_id,
                answer=record.answer,
                source=record.source,
                answer_source=answer_source,
                category=record.category,
                tenant_id=record.tenant_id,
                permission_tags=record.permission_tags,
                promote_to_long_term=record.promote_to_long_term,
            )
        return None

    def upsert_override(self, payload: AnswerOverrideInput) -> AnswerMemoryRecord:
        now = utc_now()
        normalized = normalize_answer_question(payload.question)
        tenant = normalize_tenant_id(payload.tenant_id)
        category = _normalize_category(payload.category)
        record = AnswerMemoryRecord(
            override_id=f"ovr_{uuid4().hex}",
            question=payload.question.strip(),
            normalized_question=normalized,
            answer=payload.answer.strip(),
            tenant_id=tenant,
            permission_tags=normalize_permission_tags(payload.permission_tags),
            source="manual",
            category=category,
            enabled=payload.enabled,
            priority=payload.priority,
            ttl_seconds=payload.ttl_seconds,
            created_by=payload.created_by,
            updated_by=payload.created_by,
            created_at=now,
            updated_at=now,
            promote_to_long_term=_promotable(category, payload.promote_to_long_term),
            expires_at=_expires_at(payload.ttl_seconds),
        )
        key = (tenant, _question_hash(normalized))
        previous = self._manual.get(key)
        if previous is not None:
            self._by_id.pop(previous.override_id, None)
        self._manual[key] = record
        self._by_id[record.override_id] = key
        return record

    def patch_override(
        self,
        override_id: str,
        patch: AnswerOverridePatch,
    ) -> AnswerMemoryRecord:
        key = self._by_id.get(override_id)
        if key is None or key not in self._manual:
            raise KeyError(override_id)
        current = self._manual[key]
        category = _normalize_category(patch.category or current.category)
        updated = replace(
            current,
            answer=(patch.answer.strip() if patch.answer is not None else current.answer),
            permission_tags=(
                normalize_permission_tags(patch.permission_tags)
                if patch.permission_tags is not None
                else current.permission_tags
            ),
            category=category,
            ttl_seconds=patch.ttl_seconds if patch.ttl_seconds is not None else current.ttl_seconds,
            enabled=patch.enabled if patch.enabled is not None else current.enabled,
            priority=patch.priority if patch.priority is not None else current.priority,
            promote_to_long_term=_promotable(
                category,
                patch.promote_to_long_term
                if patch.promote_to_long_term is not None
                else current.promote_to_long_term,
            ),
            updated_by=patch.updated_by or current.updated_by,
            updated_at=utc_now(),
            expires_at=(
                _expires_at(patch.ttl_seconds)
                if patch.ttl_seconds is not None
                else current.expires_at
            ),
        )
        self._manual[key] = updated
        return updated

    def delete_override(self, override_id: str) -> bool:
        key = self._by_id.pop(override_id, None)
        if key is None:
            return False
        return self._manual.pop(key, None) is not None

    def list_overrides(
        self,
        tenant_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[AnswerMemoryRecord]:
        tenant = normalize_tenant_id(tenant_id) if tenant_id else None
        records = []
        for record in self._manual.values():
            if tenant is not None and record.tenant_id != tenant:
                continue
            if enabled is not None and record.enabled is not enabled:
                continue
            records.append(record)
        return sorted(records, key=lambda item: item.updated_at, reverse=True)

    def upsert_hot_cache(
        self,
        *,
        question: str,
        answer: str,
        tenant_id: str,
        permission_tags: tuple[str, ...] | list[str] | str | None,
        request_id: str | None,
        feedback_id: str | None,
        ttl_seconds: int | None,
    ) -> AnswerMemoryRecord:
        now = utc_now()
        normalized = normalize_answer_question(question)
        tenant = normalize_tenant_id(tenant_id)
        key = (tenant, _question_hash(normalized))
        record = AnswerMemoryRecord(
            override_id=f"hot_{uuid4().hex}",
            question=question.strip(),
            normalized_question=normalized,
            answer=answer.strip(),
            tenant_id=tenant,
            permission_tags=normalize_permission_tags(permission_tags),
            source="hot_cache",
            category="feedback",
            enabled=True,
            priority=10,
            ttl_seconds=ttl_seconds,
            created_at=now,
            updated_at=now,
            request_id=request_id,
            feedback_id=feedback_id,
            promote_to_long_term=False,
            expires_at=_expires_at(ttl_seconds),
        )
        self._hot[key] = record
        return record

    def record_negative_feedback(
        self,
        *,
        question: str,
        tenant_id: str,
        permission_tags: tuple[str, ...] | list[str] | str | None,
        request_id: str | None,
        feedback_id: str | None,
        labels: tuple[str, ...] | list[str] | None = None,
    ) -> NegativeFeedbackStats:
        normalized = normalize_answer_question(question)
        tenant = normalize_tenant_id(tenant_id)
        key = (tenant, _question_hash(normalized))
        current = self._negative.get(key)
        next_labels = tuple(sorted(set((current.labels if current else ()) + tuple(labels or ()))))
        stats = NegativeFeedbackStats(
            question=question.strip(),
            normalized_question=normalized,
            tenant_id=tenant,
            permission_tags=normalize_permission_tags(permission_tags),
            count=(current.count if current else 0) + 1,
            labels=next_labels,
            last_request_id=request_id,
            last_feedback_id=feedback_id,
            updated_at=utc_now(),
        )
        self._negative[key] = stats
        return stats

    def get_negative_stats(
        self,
        question: str,
        tenant_id: str,
        permission_tags: tuple[str, ...] | list[str] | str | None,
    ) -> NegativeFeedbackStats | None:
        del permission_tags
        key = (normalize_tenant_id(tenant_id), _question_hash(normalize_answer_question(question)))
        return self._negative.get(key)

    def has_transient_manual_override(
        self,
        question: str,
        tenant_id: str,
        permission_tags: tuple[str, ...] | list[str] | str | None,
    ) -> bool:
        record = self._manual.get(
            (normalize_tenant_id(tenant_id), _question_hash(normalize_answer_question(question)))
        )
        return bool(record and record.category in TRANSIENT_CATEGORIES and _record_available(record, normalize_permission_tags(permission_tags)))


class RedisAnswerMemoryStore:
    """Redis implementation for production; lookup is deterministic key access."""

    def __init__(
        self,
        redis_url: str,
        *,
        timeout_ms: int = 50,
        key_prefix: str = "rag:answer",
    ) -> None:
        try:
            import redis
        except ModuleNotFoundError as exc:
            raise RuntimeError("Redis answer memory requires dependency: pip install redis") from exc
        timeout_seconds = max(timeout_ms, 1) / 1000
        self._client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=timeout_seconds,
            socket_connect_timeout=timeout_seconds,
        )
        self.key_prefix = key_prefix.rstrip(":")

    def lookup(self, question: str, tenant_id: str | None, permission_tags) -> AnswerMemoryHit | None:
        tenant = normalize_tenant_id(tenant_id)
        normalized = normalize_answer_question(question)
        request_tags = normalize_permission_tags(permission_tags)
        for source, answer_source in (("manual", "redis_manual_override"), ("hot", "redis_hot_cache")):
            record = self._load_record(self._record_key(source, tenant, normalized))
            if not _record_available(record, request_tags):
                continue
            assert record is not None
            return AnswerMemoryHit(
                override_id=record.override_id,
                answer=record.answer,
                source=record.source,
                answer_source=answer_source,
                category=record.category,
                tenant_id=record.tenant_id,
                permission_tags=record.permission_tags,
                promote_to_long_term=record.promote_to_long_term,
            )
        return None

    def upsert_override(self, payload: AnswerOverrideInput) -> AnswerMemoryRecord:
        record = MemoryAnswerMemoryStore().upsert_override(payload)
        key = self._record_key("manual", record.tenant_id, record.normalized_question)
        self._save_record(key, record)
        self._client.set(self._id_key(record.override_id), key)
        self._client.sadd(self._index_key(record.tenant_id), record.override_id)
        return record

    def patch_override(self, override_id: str, patch: AnswerOverridePatch) -> AnswerMemoryRecord:
        key = self._client.get(self._id_key(override_id))
        if not key:
            raise KeyError(override_id)
        record = self._load_record(key)
        if record is None:
            raise KeyError(override_id)
        memory = MemoryAnswerMemoryStore()
        memory._manual[(record.tenant_id, _question_hash(record.normalized_question))] = record
        memory._by_id[record.override_id] = (record.tenant_id, _question_hash(record.normalized_question))
        updated = memory.patch_override(override_id, patch)
        self._save_record(key, updated)
        return updated

    def delete_override(self, override_id: str) -> bool:
        key = self._client.get(self._id_key(override_id))
        if not key:
            return False
        self._client.delete(key)
        self._client.delete(self._id_key(override_id))
        return True

    def list_overrides(self, tenant_id: str | None = None, enabled: bool | None = None) -> list[AnswerMemoryRecord]:
        tenants = [normalize_tenant_id(tenant_id)] if tenant_id else []
        if not tenants:
            return []
        records: list[AnswerMemoryRecord] = []
        for tenant in tenants:
            for override_id in self._client.smembers(self._index_key(tenant)):
                key = self._client.get(self._id_key(str(override_id)))
                record = self._load_record(key) if key else None
                if record is None:
                    continue
                if enabled is not None and record.enabled is not enabled:
                    continue
                records.append(record)
        return sorted(records, key=lambda item: item.updated_at, reverse=True)

    def upsert_hot_cache(self, **kwargs) -> AnswerMemoryRecord:
        record = MemoryAnswerMemoryStore().upsert_hot_cache(**kwargs)
        self._save_record(self._record_key("hot", record.tenant_id, record.normalized_question), record)
        return record

    def record_negative_feedback(self, **kwargs) -> NegativeFeedbackStats:
        stats = MemoryAnswerMemoryStore().record_negative_feedback(**kwargs)
        self._client.set(self._negative_key(stats.tenant_id, stats.normalized_question), _json_dumps(asdict(stats)))
        return stats

    def get_negative_stats(self, question: str, tenant_id: str, permission_tags=None) -> NegativeFeedbackStats | None:
        del permission_tags
        raw = self._client.get(self._negative_key(normalize_tenant_id(tenant_id), normalize_answer_question(question)))
        if not raw:
            return None
        return NegativeFeedbackStats(**json.loads(raw))

    def has_transient_manual_override(self, question: str, tenant_id: str, permission_tags) -> bool:
        record = self._load_record(self._record_key("manual", normalize_tenant_id(tenant_id), normalize_answer_question(question)))
        return bool(record and record.category in TRANSIENT_CATEGORIES and _record_available(record, normalize_permission_tags(permission_tags)))

    def _record_key(self, source: str, tenant: str, normalized_question: str) -> str:
        return f"{self.key_prefix}:{source}:{tenant}:{_question_hash(normalized_question)}"

    def _id_key(self, override_id: str) -> str:
        return f"{self.key_prefix}:id:{override_id}"

    def _index_key(self, tenant: str) -> str:
        return f"{self.key_prefix}:index:{tenant}"

    def _negative_key(self, tenant: str, normalized_question: str) -> str:
        return f"{self.key_prefix}:negative:{tenant}:{_question_hash(normalized_question)}"

    def _save_record(self, key: str, record: AnswerMemoryRecord) -> None:
        self._client.set(key, _record_to_json(record))
        if record.ttl_seconds and record.ttl_seconds > 0:
            self._client.expire(key, record.ttl_seconds)

    def _load_record(self, key: str) -> AnswerMemoryRecord | None:
        try:
            raw = self._client.get(key)
            if not raw:
                return None
            return _record_from_dict(json.loads(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return None


def create_answer_memory_store(settings: Settings) -> AnswerMemoryStore:
    if not settings.redis_answer_override_enabled:
        return NullAnswerMemoryStore()
    if not settings.redis_url:
        return NullAnswerMemoryStore()
    return RedisAnswerMemoryStore(
        settings.redis_url,
        timeout_ms=settings.redis_answer_override_timeout_ms,
    )


def normalize_answer_question(question: str) -> str:
    normalized = " ".join((question or "").strip().split()).lower()
    return normalized.rstrip(" ?？。.!！")


def normalize_tenant_id(value: str | None) -> str:
    return (value or "default").strip() or "default"


def normalize_permission_tags(value: tuple[str, ...] | list[str] | set[str] | str | None) -> tuple[str, ...]:
    if value is None:
        raw_values = ["public"]
    elif isinstance(value, str):
        raw_values = value.replace("，", ",").replace("；", ",").replace(";", ",").split(",")
    else:
        raw_values = [str(item) for item in value]
    tags = tuple(dict.fromkeys(item.strip() for item in raw_values if item and item.strip()))
    return tags or ("public",)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_available(record: AnswerMemoryRecord | None, request_tags: tuple[str, ...]) -> bool:
    if record is None or not record.enabled:
        return False
    if record.expires_at is not None and record.expires_at <= time.time():
        return False
    return bool(set(record.permission_tags) & set(request_tags))


def _normalize_category(value: str | None) -> str:
    return (value or "manual").strip().lower() or "manual"


def _promotable(category: str, requested: bool) -> bool:
    if category in TRANSIENT_CATEGORIES:
        return False
    return bool(requested)


def _expires_at(ttl_seconds: int | None) -> float | None:
    if ttl_seconds is None or ttl_seconds <= 0:
        return None
    return time.time() + ttl_seconds


def _question_hash(normalized_question: str) -> str:
    return hashlib.sha256(normalized_question.encode("utf-8")).hexdigest()[:32]


def _record_to_json(record: AnswerMemoryRecord) -> str:
    return _json_dumps(asdict(record))


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _record_from_dict(payload: dict[str, Any]) -> AnswerMemoryRecord:
    payload = dict(payload)
    payload["permission_tags"] = tuple(payload.get("permission_tags") or ("public",))
    return AnswerMemoryRecord(**payload)
