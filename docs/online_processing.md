# 在线问答处理流程

在线处理模块只参与用户实时交互。它不扫描知识目录，不做文档清洗，不做知识切片，也不刷新向量库；这些工作都在离线处理阶段完成。

在线阶段的目标是：每次接收用户问题时，都实时执行查询向量化和混合检索，从已经构建好的最新向量库中召回相关知识，再把“用户原始问题 + 召回文档”组合成增强上下文，交给大语言模型生成回答。

## 核心链路

```text
1. 用户查询
   接收一线人员输入的自然语言问题。

2. 意图识别
   对用户问题做规则识别，判断是业务规则查询、异常原因解释、工单状态查询、处理建议、相似案例还是转人工兜底。

3. Query 改写 / 扩写
   将口语化、不完整的用户查询改写成更标准的业务表达，同时补充同义词扩展和语义扩展。例如“光猫红灯咋办”会扩展出“LOS 红灯、光路异常、ONU、排查步骤、现场处理建议”等检索词。
   对于“这个/它/那”这类跟进问句，会结合会话历史做上下文 Query Rewriting，把上轮关键术语拼入当前查询，再进入检索。

4. 工具调用
   当意图识别为 `query_order_status` 且问题中包含工单号时，在线链路会调用 `query_order_status` 工具查询工单主状态、最近流转和派单信息。工具结果会进入增强上下文、trace 和查询日志。

5. 查询向量化
   使用扩展后的检索查询生成向量，而不是只使用用户原话，从而扩大召回范围。

6. 混合检索
   在线处理器会在每次查询前重新读取向量库，确保使用离线刷新后的最新知识数据；随后根据用户的 `tenant_id` 和 `permission_tags` 过滤可访问知识，再分别执行向量相似度召回和 BM25 关键词召回，各自获取候选结果，按 chunk_id 合并去重，再对 BM25 分数做归一化并按权重合成综合分。最后通过固定阈值和相对阈值过滤低分结果，得到候选文档集合。

7. Cross-Encoder 重排（可选）
   当 `RAG_RERANK_PROVIDER=cross-encoder` 时，系统会对候选集合执行二阶段重排。重排模型逐条评估 `query + chunk` 相关性，重新排序并截断到 top_k，减少弱相关文档进入增强上下文。
   可通过 `RAG_RERANK_TRIGGER=auto` 按意图、跟进问题和低置信度场景按需触发，降低低风险问题的在线成本。

8. 增强上下文生成
   将用户原始查询、归一化查询、改写查询、检索查询、识别意图、工具调用结果、召回文档、来源信息和相似度分数拼接成增强上下文。

9. 大语言模型回答
   大语言模型基于增强上下文回答问题，并输出来源引用（如 `[1]`、`[2]`），确保答案可溯源。
```

## 当前代码入口

在线处理器：

```text
rag_app/retrieval/online.py
```

查询理解模块：

```text
rag_app/retrieval/query.py
```

核心类：

```python
OnlineQueryProcessor
```

意图识别方法：

```python
recognize_intent(query: str)
```

Query 改写和扩展方法：

```python
rewrite_query(query: str, intent: IntentRecognitionResult | None = None)
```

命令行调用：

```powershell
python -m rag_app.cli query "光猫 LOS 红灯怎么处理？"
```

打印增强上下文：

```powershell
python -m rag_app.cli query "光猫 LOS 红灯怎么处理？" --show-context
```

检索评测（对比重排前后）：

```powershell
python -m rag_app.cli evaluate-retrieval --dataset <生产评测集.jsonl> --top-k 3
python -m rag_app.cli evaluate-retrieval --dataset <生产评测集.jsonl> --top-k 3 --show-failures
```

API 调用：

```text
POST /query
```

请求示例：

```json
{
  "question": "光猫 LOS 红灯怎么处理？",
  "top_k": 4,
  "session_id": "tech-001",
  "user_id": "u-1001",
  "tenant_id": "tenant-a",
  "permission_tags": ["OPS_L2"]
}
```

## 在线与离线的边界

在线处理会做：

- 接收用户原始问题。
- 识别用户查询意图。
- 将口语化查询改写成标准业务表达。
- 进行同义词扩展和语义扩展。
- 使用扩展后的检索查询生成查询向量。
- 每次查询前使用 active collection 查询 PostgreSQL/pgvector。
- 从向量库做混合检索，并过滤低于 `RAG_MIN_SIMILARITY_SCORE` 的结果。
- 按租户和权限标签过滤用户无权访问的 chunk。
- 使用 `RAG_RELATIVE_SCORE_THRESHOLD` 过滤明显弱于首条结果的候选。
- 可选执行 Cross-Encoder 重排，把候选集合精排后再截断到 top_k。
- 记录各阶段耗时、重排触发状态、查询向量缓存命中状态和降级原因。
- 构造增强上下文。
- 调用回答生成器。

在线处理不会做：

- 扫描资料目录。
- 清洗原始文件。
- 文档切片。
- 文档向量化。
- 刷新向量库。
- 更新 manifest。

## 返回结果

在线问答返回 `RAGAnswer`，包含：

- `question`：用户原始问题。
- `answer`：生成答案。
- `sources`：召回到的知识切片和相似度。
- `trace`：在线处理轨迹。

`trace` 中会记录：

- `request_id`：单次请求追踪 ID，用于查询日志、反馈和排查串联。
- `created_at`：请求创建时间。
- `original_query`：用户原始问题。
- `normalized_query`：归一化后的查询。
- `contextual_query`：结合会话历史后的上下文改写查询。
- `is_follow_up`：是否识别为跟进问句。
- `context_terms`：用于跟进问句改写的上下文关键术语。
- `rewritten_query`：标准化后的查询。
- `retrieval_query`：最终用于向量化和混合检索的扩展查询。
- `synonym_expansions`：同义词扩展结果。
- `semantic_expansions`：按意图补充的语义扩展结果。
- `query_rewrite_rules`：命中的改写规则。
- `intent_label`：识别出的用户意图。
- `intent_confidence`：意图识别置信度。
- `intent_reason`：意图识别原因。
- `top_k`：召回数量。
- `min_similarity_score`：最小相似度阈值，低于或等于该阈值的结果不会进入增强上下文。
- `relative_score_threshold`：相对分数阈值，例如 `0.35` 表示低于第一名综合分 35% 的结果会被过滤。
- `retrieval_mode`：检索模式，默认 `hybrid`，也可以配置为 `semantic` 或 `keyword`。
- `semantic_weight`：混合检索中的语义分权重。
- `bm25_weight`：混合检索中的 BM25 归一化分权重。
- `retrieval_candidate_k`：向量召回和 BM25 召回各自保留的候选数量。
- `rerank_provider`：重排提供方，默认 `none`，可选 `cross-encoder`。
- `rerank_model`：重排模型名称或路径。
- `rerank_candidate_k`：重排阶段输入候选上限。
- `reranked_count`：重排后返回的最终文档数。
- `rerank_applied`：本次是否真正执行重排。
- `rerank_skip_reason`：未执行重排的原因，例如 provider 关闭、自动触发条件未命中、候选不足或重排失败。
- `degradation_reason`：重排或生成失败后的降级原因。
- `context_latency_ms`、`intent_latency_ms`、`rewrite_latency_ms`、`embedding_latency_ms`、`vector_search_latency_ms`、`rerank_latency_ms`：各阶段耗时。
- `query_embedding_cache_hit`：本次查询向量化是否命中缓存。
- `query_embedding_dimensions`：查询向量维度。
- `retrieved_count`：实际召回数量。
- `user_id`、`tenant_id`、`permission_tags`：本次检索使用的用户权限上下文。
- `authorized_source_count`：权限过滤和重排后进入增强上下文的来源数量。
- `latency_ms`：在线问答总耗时。
- `retrieval_latency_ms`：查询向量化、召回和重排耗时。
- `generation_latency_ms`：回答生成耗时。
- `augmented_context`：交给大语言模型使用的增强上下文。

## 工程化运行

在线查询默认会写入结构化日志，便于后续排查问题：

```powershell
python -m rag_app.cli query-logs --limit 5
python -m rag_app.cli ops-summary --limit 200
```

如果人工质检发现回答有问题，可以基于 `request_id` 写入反馈：

```powershell
python -m rag_app.cli feedback --request-id <request_id> --rating 2 --useful false --comment "召回到了错误文档" --label bad_retrieval
```

## 重排配置

默认关闭重排：

```powershell
$env:RAG_RERANK_PROVIDER="none"
```

启用 Cross-Encoder 重排：

```powershell
pip install -e ".[rerank]"
$env:RAG_RERANK_PROVIDER="cross-encoder"
$env:RAG_RERANK_MODEL="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
$env:RAG_RERANK_CANDIDATE_K="20"
```

按需触发重排：

```powershell
$env:RAG_RERANK_TRIGGER="auto"
$env:RAG_RERANK_INTENTS="recommend_solution,explain_error,query_rule,similar_case,need_human"
$env:RAG_RERANK_MIN_INTENT_CONFIDENCE="0.75"
```

查询向量缓存：

```powershell
$env:RAG_QUERY_EMBEDDING_CACHE_ENABLED="true"
$env:RAG_QUERY_EMBEDDING_CACHE_SIZE="128"
```
