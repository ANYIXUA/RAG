# 模型配置

项目只保留 OpenAI 兼容模型链路。

```text
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

阿里云百炼 DashScope 通过 OpenAI 兼容模式接入。`OPENAI_API_KEY` 可以留空，服务会从 `DASHSCOPE_API_KEY` 读取密钥。

调整 embedding 模型或维度后，需要重新执行：

```powershell
python -m rag_app.cli offline-refresh --source data --reset
```

pgvector 表的 `embedding VECTOR(n)` 维度必须与 `RAG_EMBEDDING_DIMENSION` 一致。

DashScope 的 embedding 兼容接口单次请求最多 10 条输入，`RAG_EMBEDDING_BATCH_SIZE` 默认保持为 10。
