# 工程运维

## 存储

长期知识、检索索引、查询日志、反馈和知识版本状态统一写入 PostgreSQL；多轮会话短期记忆默认写入 Redis：

```text
RAG_OPS_STORE_PROVIDER=postgresql
RAG_OPS_POSTGRES_DSN=postgresql://rag:rag_password@postgres:5432/rag
RAG_ORDER_STATUS_POSTGRES_DSN=postgresql://rag:rag_password@postgres:5432/rag
RAG_VECTOR_STORE_PROVIDER=postgresql
RAG_CONVERSATION_MEMORY_PROVIDER=redis
RAG_REDIS_URL=redis://redis:6379/0
```

## 常用检查

```powershell
python -m compileall rag_app tests
python -m unittest discover
python -m rag_app.cli version
python -m rag_app.cli ops-summary --limit 200
python -m rag_app.cli ops-trace <request_id>
```

## 发布检查

```powershell
.\scripts\release_check.ps1 -Dataset <生产评测集.jsonl>
```

接口集成测试需要真实 PostgreSQL：

```powershell
$env:RAG_TEST_POSTGRES_DSN="postgresql://rag:rag_password@127.0.0.1:15432/rag"
python -m unittest tests.test_api
```

管理接口上线时必须配置 `RAG_API_ADMIN_TOKEN`，并通过 `X-API-Key` 或 `Authorization: Bearer ...` 调用。
