# PostgreSQL/pgvector 存储设计

当前项目将结构化业务数据、RAG 运行数据、知识版本状态和知识向量统一放在 PostgreSQL 中。

## 存储职责

- `work_orders`、`work_order_flow_logs`、`dispatch_records`：真实业务表，供在线工具直接查询。
- `rag_documents`：进入知识库的文档元数据。
- `rag_knowledge_chunks`：知识切片、metadata 和 pgvector embedding。
- `query_logs`、`feedback`：在线问答日志和人工反馈。
- `rag_tool_call_logs`：工具调用审计。
- `knowledge_uploads`、`knowledge_build_jobs`、`knowledge_versions`、`knowledge_active_versions`：热上传、构建任务和 active 指针。

## 配置

```text
RAG_OPS_STORE_PROVIDER=postgresql
RAG_OPS_POSTGRES_DSN=postgresql://rag:rag_password@postgres:5432/rag
RAG_ORDER_STATUS_POSTGRES_DSN=postgresql://rag:rag_password@postgres:5432/rag
RAG_VECTOR_STORE_PROVIDER=postgresql
```

## 检索策略

在线检索先用 pgvector cosine 距离召回语义候选，再用应用层 BM25 分数补充关键词候选并融合排序。租户和权限标签在召回结果进入增强上下文前统一过滤。

如果后续需要更强的倒排索引能力，可以在 PostgreSQL 外接企业搜索服务；默认生产链路以 PostgreSQL/pgvector 为唯一知识向量存储。
