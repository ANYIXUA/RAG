# 性能、成本和稳定性设计

本文档说明在线问答链路如何记录耗时、控制重排成本，并在局部失败时保持可用。

## 分阶段耗时

每次在线查询都会在 `trace` 中记录这些耗时：

- `context_latency_ms`：多轮上下文读取和跟进问句改写耗时。
- `intent_latency_ms`：意图识别耗时。
- `rewrite_latency_ms`：Query 标准化、同义词扩展和语义扩展耗时。
- `embedding_latency_ms`：查询向量化耗时。
- `vector_search_latency_ms`：向量库和 BM25 混合召回耗时。
- `rerank_latency_ms`：Cross-Encoder 或其他重排器耗时。
- `generation_latency_ms`：回答生成耗时。
- `latency_ms`：端到端总耗时。

这样排查慢请求时，可以判断瓶颈来自 Embedding、向量库、重排还是生成。

## 查询向量缓存

默认开启查询 Embedding 缓存：

```powershell
RAG_QUERY_EMBEDDING_CACHE_ENABLED=true
RAG_QUERY_EMBEDDING_CACHE_SIZE=128
```

缓存只针对在线查询文本生效，用于减少重复问法的向量化开销。`trace.query_embedding_cache_hit` 会标记本次是否命中缓存。

## 重排按需触发

重排可以通过配置控制：

```powershell
RAG_RERANK_TRIGGER=always
RAG_RERANK_INTENTS=recommend_solution,explain_error,query_rule,similar_case,need_human
RAG_RERANK_MIN_INTENT_CONFIDENCE=0.75
```

- `always`：只要启用重排 provider，就对候选结果执行重排。
- `auto`：只在高风险意图、跟进问答或低置信度问题时执行重排。

低风险问题跳过重排时，`trace.rerank_skip_reason` 会记录原因，例如：

- `provider_disabled`
- `auto_trigger_not_matched`
- `not_enough_candidates`
- `rerank_failed`

## 降级策略

当前实现的降级策略：

- 重排异常：回退到第一阶段混合检索排序结果。
- 回答生成异常：返回可解释的降级回答，并保留召回来源，提示人工核验或转人工。

降级原因记录在：

```text
trace.degradation_reason
```

这样线上即使 Cross-Encoder 或 LLM 暂时异常，也不会让整个问答链路直接中断。

## 简单压测

本地可以执行：

```powershell
.\scripts\load_test.ps1 -Mode cli -Requests 20 -Concurrency 4 -Question "光猫红灯咋办"
```

脚本会输出：

- 请求总数
- 错误数
- 错误率
- 平均延迟
- P95 延迟

该脚本用于持续发布前的基准压测，帮助确认问答链路的错误率、吞吐和 P95 延迟是否满足门禁。

## 并发压测

如果需要更接近工程压测的统计，可以使用：

```powershell
.\scripts\load_test.ps1 -Mode api -Requests 50 -Concurrency 5 -Question "光猫红灯咋办"
```

API 模式要求本地服务已启动：

```powershell
.\scripts\start_api.ps1 -Port 8000 -Background
```

如果不想启动 API，也可以压 CLI：

```powershell
.\scripts\load_test.ps1 -Mode cli -Requests 20 -Concurrency 4 -Question "光猫红灯咋办"
```

脚本会输出：

- 请求数、并发数、错误率。
- 平均延迟、P50、P90、P95、P99、最大延迟。
- 吞吐量。
- 失败样本摘要。
- `reports/load_test_*.json` 压测报告。

也可以用评测集作为问题来源：

```powershell
.\scripts\load_test.ps1 -Mode cli -QuestionsFile <生产压测问题集.jsonl> -Requests 30 -Concurrency 3
```

设置门禁阈值：

```powershell
.\scripts\load_test.ps1 -Mode api -Requests 100 -Concurrency 10 -FailOnErrorRate 0.01 -FailOnP95Ms 1000
```
