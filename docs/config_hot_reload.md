# 配置文件与热加载

运行配置放在项目根目录的 `config/` 下，默认会按文件名顺序读取所有 `*.json` 文件，但不会把 `evaluation.json` 当成运行时配置加载。

## 文件职责

- `config/storage.json`：数据目录、存储目录、collection、切片大小、PostgreSQL/pgvector provider。
- `config/model.json`：向量模型、大模型、base URL、embedding 维度和批大小。
- `config/retrieval.json`：召回数量、检索模式、候选数量、语义/BM25 权重、阈值、重排策略。
- `config/knowledge.json`：知识审核、上传目录、构建目录、租户和权限标签。
- `config/api.json`：查询日志、会话短期记忆、管理 token、CORS。
- `config/evaluation.json`：手动评测参数记录，不参与在线运行。

## 生效顺序

`Settings.from_env()` 先读取环境变量，再叠加 `config/*.json`。因此：

- 手工调参优先改 `config/retrieval.json`。
- 密钥、DSN 和部署差异仍建议放环境变量。
- 配置文件里可以写 `${ENV_NAME}` 或 `${ENV_NAME:-default}`。
- 默认目录是 `config/`，也可以通过 `RAG_CONFIG_DIR` 指定目录，通过 `RAG_CONFIG_FILE` 追加单个文件。

## 热加载规则

API 每次处理请求前都会重新读取配置，并把配置指纹放进在线 pipeline 缓存键。修改 `config/retrieval.json` 后，下一次 `/query` 会自动重建检索 pipeline，无需重启服务。

可以热加载的常用项：

- `top_k`
- `retrieval_mode`
- `retrieval_candidate_k`
- `semantic_weight`
- `bm25_weight`
- `min_similarity_score`
- `relative_score_threshold`
- `rerank_provider`
- `rerank_trigger`
- `rerank_candidate_k`
- `query_embedding_cache_size`
- `conversation_memory_provider`
- `conversation_memory_max_turns`
- `conversation_memory_history_limit`
- `conversation_memory_ttl_seconds`
- `conversation_coreference_enabled`
- `redis_url`
- `embedding_timeout_seconds`
- `embedding_max_retries`
- `openai_max_tokens`
- `openai_timeout_seconds`
- `openai_max_retries`
- `generation_context_max_chars`

需要额外动作的项：

- `chunk_size`、`chunk_overlap`：需要重新执行 `offline-refresh`，否则旧切片不会改变。
- `embedding_dimension`、`openai_embedding_model`：需要确认 pgvector 列维度一致，并重建向量库。
- `collection_name`、`ops_postgres_dsn`：下一次请求会切换连接或 collection，但目标库必须已经存在并完成初始化。
- `api_cors_origins`：CORS 中间件在应用启动时注册，修改后建议重启 API。

## 手动调参流程

1. 修改 `config/retrieval.json`。
2. 访问 `GET /health`，检查 `config.config_sources` 和 `config.config_fingerprint` 是否变化。
3. 用前端页面或 CLI 发起同一批问题。
4. 运行检索评测，保存报告后对比 Hit@K、MRR、无结果率和延迟。

本机 PowerShell 示例：

```powershell
$env:RAG_OPS_POSTGRES_DSN="postgresql://rag:rag_password@127.0.0.1:15432/rag"
$env:DASHSCOPE_API_KEY="<your-key>"
Invoke-RestMethod http://127.0.0.1:18080/health | ConvertTo-Json -Depth 8
```
