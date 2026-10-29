# 运维 RAG

生产向 RAG 服务，默认链路直接连接 PostgreSQL/pgvector、Redis 短期会话记忆、PostgreSQL 业务表和 OpenAI 兼容模型服务。

## 生产默认链路

- 知识向量：PostgreSQL + pgvector，表 `rag_documents`、`rag_knowledge_chunks`。
- 多轮短期记忆：Redis，默认保存最近会话摘要并按 TTL 过期；缺失 `session_id` 时自动生成 `sess_YYYYMMDDHHMMSS_<tenant>_<source>_<random>`。
- 在线业务查询：PostgreSQL 业务表，当前工具为 `query_order_status`。
- 运行日志/反馈/处理轨迹：PostgreSQL。
- 查询和文档向量化：OpenAI 兼容向量化接口。
- 回答生成：OpenAI 兼容聊天补全接口。
- 热更新版本指针：PostgreSQL。

生产运行链路的长期知识、检索索引、日志和业务工具调用通过 PostgreSQL 或 OpenAI 兼容模型服务完成；会话短期记忆默认通过 Redis 完成。

## 离线解析教学 Demo

独立学习入口位于 [`demo/offline_parsing/`](demo/offline_parsing/)，不接入生产服务。使用标准库即可运行 TXT + Hash Embedding + SQLite 的导入与来源页码验收：

```powershell
python -m demo.offline_parsing.ingest_demo --input demo/offline_parsing/sample_docs --persist-dir .demo_data/offline_index --no-progress
python -m demo.offline_parsing.search_test --persist-dir .demo_data/offline_index --query "E203 地址校验失败" --top-k 2 --expected-source incident_codes.txt --expected-page 1
```

安装可选依赖后可练习 PDF/DOCX、Chroma 和本地 Sentence Transformer。完整步骤、跨页表格示例和能力边界见[快速开发手册](docs/offline_parsing_1day_demo_guide.md)；[复习交接](docs/offline_parsing_review_handoff.md)和[面试问答](docs/offline_parsing_interview_guide.md)保留了教学 Demo 开始前的讨论快照。`.demo_data/` 保存本地生成的索引与样例，已加入 Git 忽略规则。

## 配置

复制环境模板后填写真实生产配置：

```powershell
Copy-Item .env.example .env
```

关键变量：

```text
RAG_OPS_STORE_PROVIDER=postgresql
RAG_OPS_POSTGRES_DSN=postgresql://rag:rag_password@postgres:5432/rag
RAG_ORDER_STATUS_POSTGRES_DSN=postgresql://rag:rag_password@postgres:5432/rag
RAG_VECTOR_STORE_PROVIDER=postgresql
RAG_CONVERSATION_MEMORY_PROVIDER=redis
RAG_REDIS_URL=redis://redis:6379/0
RAG_EMBEDDING_PROVIDER=openai
RAG_LLM_PROVIDER=openai
DASHSCOPE_API_KEY=
OPENAI_API_KEY=
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_CHAT_MODEL=qwen-plus
OPENAI_MAX_TOKENS=800
OPENAI_EMBEDDING_MODEL=text-embedding-v4
RAG_EMBEDDING_DIMENSION=1024
RAG_EMBEDDING_BATCH_SIZE=10
```

本机用 Docker Compose 起 PostgreSQL/pgvector 和 Redis：

```powershell
docker compose up -d postgres redis
```

启动完整服务：

```powershell
docker compose build
docker compose --profile tools run --rm rag-refresh
docker compose up -d rag-api
```

## 常用命令

```powershell
python -m rag_app.cli offline-refresh --source data --reset
python -m rag_app.cli query "帮我查一下工单 WO202604290001 现在到哪了"
python -m rag_app.cli ops-summary --limit 200
python -m rag_app.cli evaluate-retrieval --dataset <生产评测集.jsonl> --top-k 3 --with-rerank-provider none
```

发布检查：

```powershell
.\scripts\release_check.ps1 -Dataset <生产评测集.jsonl>
```

## 接口列表

- `GET /health`
- `GET /ready`
- `POST /offline-refresh`
- `POST /query`
- `POST /feedback`
- `GET /ops/summary`
- `GET /ops/query-logs`
- `GET /ops/feedback`
- `GET /ops/trace/{request_id}`
- `POST /knowledge/uploads/text`
- `POST /knowledge/build-jobs`
- `GET /knowledge/build-jobs`
- `GET /knowledge/versions`
- `POST /knowledge/versions/{version}/activate`
- `POST /knowledge/rollback`

管理接口建议配置 `RAG_API_ADMIN_TOKEN`，调用时通过 `X-API-Key` 或 `Authorization: Bearer ...` 传入。`/ops/trace/{request_id}` 包含完整私有审计数据，必须配置该 Token；服务端未配置时固定返回 `503 ADMIN_TOKEN_NOT_CONFIGURED`。

## 查询测试页

本地浏览器打开 `web/index.html`，默认请求 `http://127.0.0.1:18080`，可直接测试 `/query`、`/health` 和 `/ready`。

## 数据库初始化

生产库需要 pgvector 扩展。表结构参考：

```text
docs/rag_business_schema_pgvector.sql
```

应用启动和写入时也会按需创建核心 RAG 表、运行日志表、反馈表、工具调用日志表和知识版本表。

## 测试

```powershell
python -m compileall rag_app tests
python -m unittest discover
```

接口集成测试需要真实 PostgreSQL DSN：

```powershell
$env:RAG_TEST_POSTGRES_DSN="postgresql://rag:rag_password@127.0.0.1:15432/rag"
python -m unittest tests.test_api
```
