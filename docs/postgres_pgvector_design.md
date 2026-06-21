# PostgreSQL/pgvector 存储设计

当前项目把结构化业务数据、RAG 运行数据、知识版本状态和知识向量统一放在 PostgreSQL 中，向量列由 pgvector 提供。

## 在哪里查看

本机 Docker 容器名是 `rag-postgres`。如果用 DBeaver、pgAdmin 或 DataGrip 查看，连接信息如下：

```text
Host: 127.0.0.1
Port: 15432
Database: rag
User: rag
Password: rag_password
```

如果在 Docker Compose 服务内部连接，主机名用 `postgres`，端口用 `5432`。

命令行查看：

```powershell
docker exec -it rag-postgres psql -U rag -d rag
\dt
\d rag_knowledge_chunks
```

## 核心表

- `rag_documents`：进入知识库的文档元数据。
- `rag_knowledge_chunks`：知识切片、正文、元数据、权限标签和 pgvector 向量。
- `knowledge_uploads`：热上传文件记录。
- `knowledge_build_jobs`：知识构建任务记录。
- `knowledge_versions`：构建完成的知识版本。
- `knowledge_active_versions`：当前生效的知识版本指针。
- `query_logs`：在线问答结构化日志。
- `feedback`：人工反馈。
- `rag_tool_call_logs`：工具调用审计日志。

`rag_knowledge_chunks.embedding` 当前是 `vector(1024)`，必须与 `config/model.json` 中的 `embedding_dimension` 一致。

## 常用 SQL

查看当前 collection 记录数：

```sql
SELECT collection_name, status, COUNT(*) AS records
FROM rag_knowledge_chunks
GROUP BY collection_name, status
ORDER BY collection_name, status;
```

查看最新切片：

```sql
SELECT
  chunk_id,
  document_id,
  metadata->>'source' AS source,
  metadata->>'section_title' AS section_title,
  left(chunk_text, 120) AS preview,
  updated_at
FROM rag_knowledge_chunks
WHERE collection_name = 'default'
  AND status = 'active'
ORDER BY updated_at DESC
LIMIT 20;
```

查看当前激活的知识版本：

```sql
SELECT *
FROM knowledge_active_versions
ORDER BY updated_at DESC;
```

按来源文件统计切片数：

```sql
SELECT
  metadata->>'source' AS source,
  COUNT(*) AS chunks
FROM rag_knowledge_chunks
WHERE collection_name = 'default'
GROUP BY metadata->>'source'
ORDER BY chunks DESC;
```

## 修改原则

不要手工改 `embedding` 或 `chunk_text` 来修知识库。知识内容应从 `data/` 或上传接口进入，然后执行离线刷新或知识构建任务，让切片、向量、版本指针和审计信息保持一致。

调召回参数时优先改 `config/retrieval.json`；只有切片策略、向量模型或 embedding 维度变化时，才需要重建向量库。
