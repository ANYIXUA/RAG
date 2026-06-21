# 检索召回评测

检索评测用于确认手动调参后的召回率、排序质量和延迟是否变好。入口命令是：

```powershell
python -m rag_app.cli evaluate-retrieval --dataset <评测集.jsonl> --top-k 3 --with-rerank-provider none
```

评测集不建议写入正式知识目录。如果必须放在 `data/` 下，文件名保留 `retrieval_eval`，治理策略会跳过它，避免被写进 `rag_knowledge_chunks`。

## 样本格式

每行一个 JSON：

```json
{"query":"T9254 是什么错误","expected":[{"source":"中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf","text_contains":"T9254"}]}
```

可用命中条件：

- `source`：必须命中指定来源文件。
- `section_title`：必须命中指定章节标题。
- `text_contains`：召回切片正文必须包含指定文本。

## 关键指标

- `hit@k`：Top K 内是否命中正确文档，最直接反映召回率。
- `mrr`：正确结果排得越靠前，分数越高。
- `no_result_rate`：无结果比例，越低越好。
- `avg_latency_ms` / `p95_latency_ms`：平均和 P95 检索延迟。

## 手动调参对比

1. 修改 `config/retrieval.json`。
2. 访问 `/health` 确认 `config_fingerprint` 已变化。
3. 运行评测并保存报告：

```powershell
python -m rag_app.cli evaluate-retrieval `
  --dataset data/retrieval_eval.jsonl `
  --top-k 3 `
  --with-rerank-provider none `
  --reports-dir reports
```

4. 调整另一组参数后再次运行，比较 `reports/retrieval_eval_*.json` 中的 `runs` 与 `release_gate`。

常用调参项：

- 提高 `retrieval_candidate_k`：增加候选池，通常提升召回，但延迟会上升。
- 调整 `semantic_weight` / `bm25_weight`：控制语义相似度和关键词匹配的融合比例。
- 降低 `min_similarity_score`：可能提升召回，也可能引入噪声。
- 降低 `relative_score_threshold`：保留更多低分候选，适合先排查漏召回。
- 开启 `rerank_provider`：可能提升排序质量，但需要本地或服务端重排模型可用。
