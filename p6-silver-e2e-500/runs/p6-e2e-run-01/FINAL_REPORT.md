# P6-E2E-Run-01｜500条Silver真实RAG执行报告

输入SHA-256：`03f7955b144e31081c778f533322ff68b560459f60ab94bb9699b2ea7a35c410`。本轮不含P5正式Gold/Holdout指标，未运行Holdout。

## 执行

- 实际发起：10/500；成功：0；失败：10；未执行：490。
- **本轮未完成500条真实问答。Smoke未通过时正式批处理不会启动；未执行项不冒充失败问答或评分结果。**
- E2E完成率：0/500 = 0.00%。10条Smoke含五类各2条，计入同一500分母，不重复计数。
- 超时尝试：0；最终超时失败题：0；重试次数：20。
- 入口：OnlineQueryProcessor.process，真实Query Rewrite/Intent/Hybrid/Context/LLM/引用；真实PostgreSQL和Redis。
- top_k=4，candidate_k=20，权重0.7/0.3，min_score=.05，relative_threshold=.35；Cross-Encoder关闭。P5检索实验top_k=20且禁用改写/意图，本轮保留当前业务行为，不能视为P5指标复跑。
- 依赖修复：项目venv缺少pyproject已声明redis>=5.0.0，安装redis8.1.0；未修改生产代码、Prompt或参数文件。

## 性能与Token

- 成功最终尝试平均墙钟延迟：None ms；p50：None ms；p95：None ms；分母0。
- 检索/生成延迟：{"retrieval_ms": {"denominator": 0, "mean": null, "p50": null, "p95": null, "unit": "milliseconds"}, "generation_ms": {"denominator": 0, "mean": null, "p50": null, "p95": null, "unit": "milliseconds"}}。
- 失败最终尝试延迟（不等于成功E2E）：{"denominator": 10, "mean": 679.7025899868459, "p50": 597.1621500793844, "p95": 989.2258650506847, "unit": "milliseconds"}。
- Token：{"chat": {"input_tokens": 0, "output_tokens": 0, "calls": 31}, "embedding": {"input_tokens": 333, "output_tokens": 0, "calls": 10}}；含重试与Judge，按call kind分列。
- 已知Token公开单价估算：¥0.000166；保守预算占用：¥0.106909/20；未知用量调用：31。
- 实际账户扣费/免费额度无法从SDK确认，actual_billed_yuan=null，不将估算冒充实际账单。价格来源：[阿里云官方模型价格](https://help.aliyun.com/zh/model-studio/model-pricing?userCode=r3yteowb)。

## 自动质量（探索性，非人工准确率）

- Silver满分回答正确比例：0/0 (N/A)；排除50条未经人工确认unanswerable、p6s-0473、执行/评分失败及null。
- Faithfulness：{"denominator": 0, "mean": null, "distribution": {}, "full_score_ratio": {"numerator": 0, "denominator": 0, "ratio": null}}。
- 回答完整度：{"denominator": 0, "mean": null, "distribution": {}, "full_score_ratio": {"numerator": 0, "denominator": 0, "ratio": null}}。
- Citation自动语义评分：{"denominator": 0, "mean": null, "distribution": {}, "full_score_ratio": {"numerator": 0, "denominator": 0, "ratio": null}}。
- 引用编号有效比例：0/0 (N/A)；编号有效且来源起始文本进入真实Prompt：0/0 (N/A)。结构有效不等于语义正确。
- 暂定拒答行为：{"denominator": 0, "mean": null, "distribution": {}, "full_score_ratio": {"numerator": 0, "denominator": 0, "ratio": null}}。
- 疑似幻觉：0/0 (N/A)；低置信度：0/0 (N/A)。
- Judge成功：0/0 (N/A)；Judge失败0，与RAG执行失败分开。
- 生成与评分均使用qwen-turbo，评分是另一次独立调用；存在同模型自评偏差，未声称独立人工/模型真值。请求、返回model别名、usage、理由和证据完整归档；服务未暴露不可变权重版本。

## 错误分类与题型

- 检索未召回Silver标注证据（代理诊断）：0/10 = 0.00%。
- 已召回但未完整进入LLM上下文（代理诊断）：0/10 = 0.00%。
- 证据进入上下文但答案错误：0/10 = 0.00%。
- 答案遗漏关键条件或步骤：0/10 = 0.00%。
- 生成内容缺乏证据支持/疑似幻觉：0/10 = 0.00%。
- 引用与实际证据不符：0/10 = 0.00%。
- 模型调用或执行异常/超时：10/10 = 100.00%。
- 自动评分无法可靠判断：0/10 = 0.00%。
- 未发现上述失败（不是人工正确性确认）：0/10 = 0.00%。

| 题型 | 执行成功 | Silver满分正确（适用分母） |
|---|---|---|
| exact_fact | 0/200 = 0.00% | 0/0 (N/A) |
| procedure | 0/100 = 0.00% | 0/0 (N/A) |
| multi_condition | 0/100 = 0.00% | 0/0 (N/A) |
| colloquial | 0/50 = 0.00% | 0/0 (N/A) |
| unanswerable | 0/50 = 0.00% | 0/0 (N/A) |

归因具有优先级且互斥，完整理由/典型案例见failure_analysis.md；不能把Silver证据未命中直接当作人工确认检索错误。

## 人工抽查与风险

抽查清单40条，五种题型各8条，优先覆盖低置信度、失败与p6s-0473。未执行项明确标pending、无RAG答案。所有人工审核字段为空，未自动签核。
- 50条unanswerable标签待人工核查，拒答评分仅暂定；泛化问题可能部分可回答。
- p6s-0473的114工日存在来源解析歧义；正确性强制null，不依此判模型错。
- 表格列/单位、长上下文截断、同义答案、引用支撑范围、同模型Judge偏差均应重点抽查。

## 交付文件

run_config.json / authorization.json / input_preflight.json / database_after.json：冻结配置与边界证据。
execution_states.jsonl：完整500条状态；attempts/：逐次失败/重试；cases/与traces.jsonl：逐题完整Trace；answers.jsonl：原始回答。
api_calls/：模型原始请求、响应、usage、预留费用；scores/与scores.jsonl：逐条理由/证据及评分失败。
metrics.json / failure_diagnostics.jsonl / failure_analysis.md：分母、性能与归因；human_spot_check_40.jsonl/.csv：空白人工抽查；sha256_manifest.json：哈希。

## 复现命令

已有成功/终态case不会重复调用，评分已完成项不会重复评分；中断尝试占用最多3次尝试配额。以下命令从项目根目录执行：

```powershell
& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/e2e_run01.py' preflight
& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/e2e_run01.py' run
& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/e2e_run01.py' score
& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/e2e_run01_report.py'
```

已停止后续工作，等待验收。