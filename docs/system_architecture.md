# 系统架构

Ops RAG 当前按生产链路组织：

1. 文档进入 `data/` 或热上传目录。
2. 离线任务解析、治理、切片。
3. OpenAI 兼容 Embedding 服务生成向量。
4. PostgreSQL/pgvector 写入 `rag_documents` 和 `rag_knowledge_chunks`。
5. 在线查询调用 OpenAI 兼容 Embedding，使用 pgvector 召回语义候选。
6. 应用层补充 BM25 候选、执行权限过滤和可选重排。
7. 命中工单状态意图时，`query_order_status` 直接查询 PostgreSQL 业务表。
8. OpenAI 兼容 Chat Completions 基于增强上下文生成回答。
9. 查询日志、工具调用、反馈和知识版本状态写入 PostgreSQL。

默认部署不包含本地向量文件、文件型日志或独立向量数据库。
