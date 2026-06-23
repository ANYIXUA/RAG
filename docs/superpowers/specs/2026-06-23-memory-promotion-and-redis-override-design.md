# Redis 快答与长期记忆自动沉淀设计

## 背景

当前在线问答链路已经具备三类存储：

- Redis 会话短期记忆：按 `session_id` 保存最近多轮摘要，用于追问改写，并按 TTL 过期。
- PostgreSQL 运行数据：保存 `query_logs`、`feedback`、知识版本和构建任务，便于追踪与运维。
- PostgreSQL/pgvector 长期知识库：通过离线刷新或热上传构建 `rag_documents`、`rag_knowledge_chunks`，供在线检索召回。

本设计在现有链路上新增两类记忆能力：

- 人工可控 Redis 快答：运维或客服可以直接写入临时答案，例如“系统故障，请稍后再试”，系统恢复后可更新、禁用或删除。
- 自动反馈沉淀：从高价值反馈中生成 Redis 热答缓存和长期知识候选，降低重复问题成本，同时避免错误答案被固化。

## 目标

1. 在线查询优先命中人工 Redis 应急答案，其次命中自动热答缓存，未命中再走现有 RAG 检索生成链路。
2. 支持管理员通过接口写入、更新、禁用和删除 Redis 快答。
3. 对多租户和权限标签做强隔离，避免不同租户或权限域之间共享应急答案。
4. 高价值正反馈可自动转为长期知识候选，并复用现有知识热上传和构建链路。
5. 低质量或负反馈只记录热度、标签和拦截线索，不直接用于回答。

## 非目标

- 不把所有短期会话自动写入长期知识库。
- 不把系统故障、维护公告、临时通知、运营应急口径等人工 Redis 快答沉淀为长期知识。
- 不让负反馈自动生成可直接回答的内容。
- 不重写现有 `query_logs`、`feedback`、`knowledge_build_jobs`、`rag_knowledge_chunks` 存储链路。
- 不在第一版引入复杂语义聚类服务；问题匹配先采用标准化文本 key，后续再扩展相似问法归并。

## 核心设计

### 1. Redis 快答层

新增 `AnswerOverrideService`，在线查询开始时先检查 Redis：

1. 按 `tenant_id`、`permission_tags`、标准化问题生成 lookup key。
2. 优先查人工 override。
3. 未命中时查自动 hot cache。
4. 命中后直接返回 `RAGAnswer`，trace 标记 `answer_source`、`override_id`、`override_type`、`override_hit=true`。
5. 未命中继续走现有 `OnlineQueryProcessor.process()`。

Redis 记录建议字段：

```json
{
  "override_id": "ovr_xxx",
  "question": "系统是不是故障了",
  "normalized_question": "系统是不是故障了",
  "answer": "系统当前故障，请稍后再试。",
  "tenant_id": "tenant-a",
  "permission_tags": ["public"],
  "source": "manual",
  "category": "incident",
  "promote_to_long_term": false,
  "enabled": true,
  "priority": 100,
  "ttl_seconds": 1800,
  "created_by": "admin",
  "created_at": "2026-06-23T00:00:00Z",
  "updated_at": "2026-06-23T00:00:00Z"
}
```

人工 override 优先级高于自动缓存。人工记录适合故障通知、临时业务口径、活动规则临时变更；自动缓存适合高频且已确认的标准问答。

人工 override 默认是临时答案，不参与长期知识沉淀。`category` 为 `incident`、`outage`、`maintenance`、`notice`、`campaign` 的记录必须保持 `promote_to_long_term=false`；系统恢复后通过更新、禁用、删除或 TTL 到期让它失效，不把历史故障状态写入 pgvector 长期知识库。

### 2. 管理接口

新增管理接口，沿用 `require_admin_token`：

- `POST /memory/overrides`：创建或更新人工 Redis 快答。
- `GET /memory/overrides`：按租户、权限标签、状态分页查看。
- `PATCH /memory/overrides/{override_id}`：启停、更新答案、更新 TTL 或优先级。
- `DELETE /memory/overrides/{override_id}`：删除人工快答。

创建和更新必须显式传入 `tenant_id`；`permission_tags` 为空时按 `public` 处理。`ttl_seconds` 可为空，表示不过期；故障公告推荐设置 TTL，恢复后可 `PATCH enabled=false` 或 `DELETE`。

### 3. 自动热答缓存

新增 `FeedbackMemoryService`，在 `/feedback` 写入 PostgreSQL 后触发：

- 正向反馈条件：`useful=true` 或 `rating>=4`。
- 可缓存条件：存在 `expected_answer`，或原答案被明确标记为可用。
- key 维度：`tenant_id + permission_tags + normalized_question`。
- Redis value 记录答案、来源 request_id、反馈 id、命中计数、最近更新时间和 TTL。

自动缓存不能覆盖人工 override；如果同 key 已存在人工 override，只累计统计，不改答案。

负反馈条件：`useful=false` 或 `rating<=2`。负反馈只累计到 Redis 热点统计，例如错误问题、标签、次数、最近 request_id，用于后续人工修正或长期知识补充，不会被在线查询直接返回。

### 4. 长期记忆沉淀

高价值正反馈进入长期知识候选：

1. 读取 `request_id` 对应的 `query_logs`，拿到原问题、改写查询、回答、来源快照、租户和权限上下文。
2. 与反馈里的 `expected_answer` 合并，优先使用人工期望答案。
3. 生成 Markdown 知识条目，带 front matter：

```markdown
---
knowledge_status: approved
source_type: feedback_promotion
business_module: feedback_memory
tenant_id: tenant-a
permission_tags: public
request_id: req_xxx
feedback_id: fb_xxx
---

# 问题

系统是不是故障了？

# 标准回答

系统当前故障，请稍后再试。
```

4. 复用现有 `save_uploaded_text()` 和 `create_knowledge_build_job()`，写入版本化知识构建任务。
5. 由现有 `run_knowledge_build_job()` 切片、向量化、写入 `rag_knowledge_chunks`，构建成功后按配置决定是否自动激活。

第一版建议默认不自动激活长期知识版本，先生成构建任务和候选记录，避免反馈噪声直接影响线上检索。需要自动激活时再通过配置开启。

长期记忆沉淀只从 `/feedback` 产生的 `feedback_promotion` 候选进入，不扫描人工 override。即使系统故障类 override 被大量命中，也只作为 Redis 临时答案和运行日志存在，不生成知识上传、不创建构建任务。

### 5. 多租户与权限边界

所有 Redis key 和长期知识 front matter 必须包含 `tenant_id`。在线命中规则：

- 请求未带 `tenant_id` 时使用 `settings.default_tenant_id`。
- Redis 记录的 `tenant_id` 必须与请求租户一致。
- Redis 记录的 `permission_tags` 为空时视为 `public`。
- 请求权限标签必须与记录标签有交集，或请求显式带 `public`。

这与当前 pgvector 检索的 `_filter_authorized_records()` 保持同一安全模型。

### 6. 配置

新增配置项：

- `RAG_REDIS_ANSWER_OVERRIDE_ENABLED=true`
- `RAG_REDIS_ANSWER_OVERRIDE_TTL_SECONDS=3600`
- `RAG_FEEDBACK_HOT_CACHE_ENABLED=true`
- `RAG_FEEDBACK_HOT_CACHE_TTL_SECONDS=86400`
- `RAG_FEEDBACK_HOT_CACHE_MIN_RATING=4`
- `RAG_FEEDBACK_PROMOTION_ENABLED=true`
- `RAG_FEEDBACK_PROMOTION_AUTO_BUILD=true`
- `RAG_FEEDBACK_PROMOTION_AUTO_ACTIVATE=false`

默认开启人工 override；自动长期沉淀可开启候选和构建，但默认不自动激活。

## 数据流

### 查询流

1. API 收到 `/query` 或 `/query/stream`。
2. 构造 `UserContext`。
3. `AnswerOverrideService.lookup()` 查 Redis 人工 override。
4. 未命中则查 Redis 自动 hot cache。
5. 命中则直接返回，并写 `query_logs`，状态可标记为 `override_answered`。
6. 未命中则执行现有 RAG 检索、重排、生成和短期会话记忆写入。

### 反馈流

1. `/feedback` 先写 PostgreSQL `feedback`。
2. `FeedbackMemoryService.handle_feedback()` 读取对应 `query_logs`。
3. 正反馈且有可信答案时写入 Redis hot cache。
4. 正反馈达到长期沉淀条件时生成知识上传和构建任务。
5. 负反馈写入 Redis 统计 key，不直接参与回答。

### 人工应急流

1. 管理员调用 `POST /memory/overrides` 写入故障答案。
2. 用户提问命中后直接返回故障公告。
3. 系统恢复后管理员 `PATCH enabled=false` 或 `DELETE`。
4. Redis TTL 到期时记录自动失效。

## 错误处理

- Redis 不可用：记录降级原因，继续走现有 RAG 链路。
- override payload 损坏：跳过该记录，并记录解析错误。
- 反馈沉淀失败：不影响 `/feedback` 主响应，但返回或记录 `promotion_status=failed`。
- 长期知识构建失败：保持现有 active version 不变。
- 权限不匹配：视为未命中，不暴露存在性。

## 测试计划

新增测试覆盖：

- Redis 人工 override 命中时跳过 RAG 检索并返回指定答案。
- 人工 override 高于自动 hot cache。
- 租户不一致或权限标签不匹配时不命中。
- Redis 不可用时查询降级到现有 RAG 链路。
- `/memory/overrides` 创建、更新、禁用、删除。
- 正向反馈写入 hot cache。
- 负反馈只累计统计，不生成直接答案。
- 系统故障、维护公告等人工 override 不会触发长期知识上传或构建任务。
- 高价值反馈生成长期知识上传和构建任务，且默认不自动激活。
- 配置项能从 env 和 config 文件读取。

## 实施顺序

1. 配置和模型：补齐配置项、trace 字段、请求/响应模型。
2. Redis 服务：实现人工 override 与 hot cache 的存取、权限匹配和降级。
3. 查询接入：在 API 查询入口接入 Redis 快答优先判断。
4. 管理接口：实现 `/memory/overrides` 系列接口。
5. 反馈接入：实现 hot cache 和长期知识候选沉淀。
6. 文档和测试：更新 README、在线处理文档、配置说明和单元测试。
