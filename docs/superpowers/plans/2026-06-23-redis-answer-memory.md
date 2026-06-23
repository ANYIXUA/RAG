# Redis Answer Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Redis-backed manual answer overrides, feedback hot cache, and safe long-term feedback promotion without promoting transient outage notices.

**Architecture:** Add a focused memory service module that owns Redis keying, tenant/permission checks, manual overrides, hot cache records, and feedback promotion decisions. Wire query paths through the service before the existing RAG processor, and wire feedback paths after PostgreSQL feedback persistence. Reuse existing query logs and knowledge lifecycle APIs for observability and long-term knowledge builds.

**Tech Stack:** Python dataclasses, FastAPI, existing `Settings`, Redis client already used by conversation memory, PostgreSQL-backed `query_logs`/`feedback`, existing `save_uploaded_text()` and `create_knowledge_build_job()`.

---

### Task 1: Settings And Trace Fields

**Files:**
- Modify: `rag_app/core/config.py`
- Modify: `rag_app/core/models.py`
- Modify: `config/api.json`
- Modify: `.env.example`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing config test**

Add a test that sets:

```python
{
    "RAG_REDIS_ANSWER_OVERRIDE_ENABLED": "true",
    "RAG_REDIS_ANSWER_OVERRIDE_TTL_SECONDS": "120",
    "RAG_REDIS_ANSWER_OVERRIDE_TIMEOUT_MS": "50",
    "RAG_FEEDBACK_HOT_CACHE_ENABLED": "true",
    "RAG_FEEDBACK_HOT_CACHE_TTL_SECONDS": "600",
    "RAG_FEEDBACK_HOT_CACHE_MIN_RATING": "4",
    "RAG_FEEDBACK_PROMOTION_ENABLED": "true",
    "RAG_FEEDBACK_PROMOTION_AUTO_BUILD": "true",
    "RAG_FEEDBACK_PROMOTION_AUTO_ACTIVATE": "false",
}
```

Assert the corresponding `Settings` fields exist and are coerced to bool/int values.

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m unittest tests.test_config
```

Expected: fail because the new settings fields do not exist or config file rejects unsupported keys.

- [ ] **Step 3: Implement minimal settings fields**

Add bool/int config support for:

```python
redis_answer_override_enabled: bool = True
redis_answer_override_ttl_seconds: int = 3600
redis_answer_override_timeout_ms: int = 50
feedback_hot_cache_enabled: bool = True
feedback_hot_cache_ttl_seconds: int = 86400
feedback_hot_cache_min_rating: int = 4
feedback_promotion_enabled: bool = True
feedback_promotion_auto_build: bool = True
feedback_promotion_auto_activate: bool = False
```

Validate `redis_answer_override_timeout_ms` as positive, and validate TTL fields as non-negative so `0` can mean no Redis expiry.

- [ ] **Step 4: Add trace fields**

Extend `OnlineProcessingTrace` with defaults:

```python
answer_source: str = "rag"
override_hit: bool = False
override_id: str | None = None
override_type: str | None = None
override_degradation_reason: str | None = None
```

- [ ] **Step 5: Run config tests**

Run:

```powershell
python -m unittest tests.test_config
```

Expected: pass.

### Task 2: Redis Answer Memory Service

**Files:**
- Create: `rag_app/retrieval/answer_memory.py`
- Test: `tests/test_answer_memory.py`

- [ ] **Step 1: Write failing service tests**

Cover:

```python
service.upsert_override(AnswerOverrideInput(
    question="系统是不是故障了",
    answer="系统当前故障，请稍后再试。",
    tenant_id="tenant-a",
    permission_tags=("public",),
    category="incident",
    ttl_seconds=1800,
    created_by="ops",
))
hit = service.lookup("系统是不是故障了", tenant_id="tenant-a", permission_tags=("public",))
assert hit.answer == "系统当前故障，请稍后再试。"
assert hit.source == "manual"
assert hit.promote_to_long_term is False
```

Also assert:

- tenant mismatch returns `None`
- permission mismatch returns `None`
- manual override beats hot cache for the same question
- disabled override returns `None`
- corrupt Redis payload is skipped

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m unittest tests.test_answer_memory
```

Expected: fail because module does not exist.

- [ ] **Step 3: Implement service types**

Create dataclasses:

```python
AnswerMemoryRecord
AnswerMemoryHit
AnswerOverrideInput
AnswerOverridePatch
```

Add helpers:

```python
normalize_answer_question(question: str) -> str
normalize_permission_tags(tags) returns an ordered tuple of non-empty permission tag strings
```

- [ ] **Step 4: Implement in-memory and Redis stores**

Implement `MemoryAnswerMemoryStore` for tests and `RedisAnswerMemoryStore` for runtime. Redis keys:

```text
rag:answer:manual:{tenant}:{hash}
rag:answer:hot:{tenant}:{hash}
rag:answer:index:{tenant}
rag:answer:negative:{tenant}:{hash}
```

No key scanning is required on lookup.

- [ ] **Step 5: Run service tests**

Run:

```powershell
python -m unittest tests.test_answer_memory
```

Expected: pass.

### Task 3: Query Path Override Hook

**Files:**
- Modify: `rag_app/retrieval/online.py`
- Test: `tests/test_online_processing.py`

- [ ] **Step 1: Write failing query tests**

Add tests that inject an answer memory service into `OnlineQueryProcessor`:

```python
result = processor.process("系统是不是故障了", user_context=UserContext(tenant_id="tenant-a", permission_tags=("public",)))
assert result.answer == "系统当前故障，请稍后再试。"
assert result.sources == []
assert result.trace.answer_source == "redis_manual_override"
assert result.trace.override_hit is True
```

Also assert Redis lookup failure falls back to existing RAG behavior and records `override_degradation_reason`.

- [ ] **Step 2: Run failing focused tests**

Run:

```powershell
python -m unittest tests.test_online_processing
```

Expected: fail because processor has no answer memory hook.

- [ ] **Step 3: Implement hook**

Add optional `answer_memory` dependency to `OnlineQueryProcessor`. At the start of `process()`, after `session_id` and `UserContext` are available, call lookup. On hit, build `RAGAnswer` with an `OnlineProcessingTrace` that marks override source and appends a query log record when logging is enabled.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
python -m unittest tests.test_online_processing
```

Expected: pass.

### Task 4: Management API For Manual Overrides

**Files:**
- Modify: `rag_app/api.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Patch `create_answer_memory_store()` to a memory store and test:

```python
POST /memory/overrides
GET /memory/overrides
PATCH /memory/overrides/{override_id}
DELETE /memory/overrides/{override_id}
```

Assert admin token protection works by reusing `require_admin_token`.

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m unittest tests.test_api
```

Expected: fail because endpoints do not exist.

- [ ] **Step 3: Implement request models and endpoints**

Add Pydantic models for create/patch. Require explicit `tenant_id`; default missing `permission_tags` to `["public"]`; force `promote_to_long_term=false` for categories `incident`, `outage`, `maintenance`, `notice`, `campaign`.

- [ ] **Step 4: Run API tests**

Run:

```powershell
python -m unittest tests.test_api
```

Expected: pass or skip PostgreSQL integration tests when DSN is absent.

### Task 5: Feedback Hot Cache And Long-Term Promotion

**Files:**
- Modify: `rag_app/operations/ops.py`
- Create: `rag_app/operations/feedback_memory.py`
- Modify: `rag_app/api.py`
- Test: `tests/test_feedback_memory.py`

- [ ] **Step 1: Write failing feedback memory tests**

Cover:

- `rating=5` and `expected_answer` writes hot cache.
- `useful=false` writes negative stats only.
- manual transient override is never promoted.
- promotion uses `expected_answer` before generated answer.
- `auto_activate` defaults false when creating build job.

- [ ] **Step 2: Run failing test**

Run:

```powershell
python -m unittest tests.test_feedback_memory
```

Expected: fail because module does not exist.

- [ ] **Step 3: Implement feedback memory service**

After feedback persistence, read query log by `request_id`. For positive feedback, write hot cache when trusted answer exists. For long-term promotion, generate Markdown and call existing lifecycle functions only for `source_type=feedback_promotion`.

- [ ] **Step 4: Wire `/feedback`**

Call `FeedbackMemoryService.handle_feedback()` after `store.append(record)`. Return the feedback record plus optional `memory` status:

```json
{"feedback_id": "fb_123", "memory": {"hot_cache": "written", "promotion": "queued"}}
```

Existing clients still see the top-level feedback fields.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m unittest tests.test_feedback_memory tests.test_api
```

Expected: pass or integration-skip as configured.

### Task 6: Docs And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/online_processing.md`
- Modify: `docs/config_hot_reload.md`
- Modify: `docs/engineering_operations.md`

- [ ] **Step 1: Update docs**

Document:

- manual Redis override is transient
- outage/maintenance/notice/campaign categories do not promote
- Redis lookup uses short timeout and failure-open fallback
- feedback positive path can hot-cache and promote
- negative feedback never directly answers

- [ ] **Step 2: Run full verification**

Run:

```powershell
python -m compileall rag_app tests
python -m unittest discover
```

Expected: compile succeeds; unit tests pass, with PostgreSQL integration tests skipped if no `RAG_TEST_POSTGRES_DSN`.

- [ ] **Step 3: Merge**

After tests pass:

```powershell
git switch main
git merge --no-ff codex/redis-answer-memory
```

Expected: merge succeeds and `main` contains the implementation.
