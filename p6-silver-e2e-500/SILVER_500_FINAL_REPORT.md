# P6-Silver-E2E-500 增量补齐与最终自动验收报告

日期：2026-11-05（Asia/Shanghai）。最终交付恰好500条Silver，既有自动验收通过。人工语义签核未执行，Silver不等于Gold。本次未运行RAG E2E，未修改任何RAG参数、模型推理选项、Gold、冻结语料或原466条。

## 1. 补齐前后数量

| 题型 | 原有效数 | 净新增 | 最终 |
|---|---:|---:|---:|
| exact_fact | 180 | 20 | 200 |
| procedure | 96 | 4 | 100 |
| multi_condition | 99 | 1 | 100 |
| colloquial | 50 | 0 | 50 |
| unanswerable | 41 | 9 | 50 |
| TOTAL | 466 | 34 | 500 |

## 2. 候选、拒绝与去重

累计47个批次尝试，收到111条模型候选；最终净接受34条，拒绝77条。2个thin_packet批次未调用推理，不计入候选拒绝分母。

| 拒绝原因 | 数量 |
|---|---:|
| `bad_answer` | 1 |
| `bad_excerpt_length` | 3 |
| `duplicate_evidence_answer` | 1 |
| `duplicate_silver` | 41 |
| `excerpt_not_verbatim` | 22 |
| `missing_evidence` | 2 |
| `not_a_question` | 3 |
| `semantic_review:instrument_cost_confused_with_unit_count` | 1 |
| `semantic_review:labor_fee_confused_with_comprehensive_unit_price` | 1 |
| `semantic_review:period_question_answered_with_record_marker` | 1 |
| `semantic_review:unsupported_condition_sand_absent_from_frozen_corpus_and_no_joint_two_chunk_reasoning` | 1 |

去重拒绝42条，去重率37.8378%（42/111，分母为全部增量候选）。总拒绝率69.3694%。与Gold重复自动拒绝0条，规则已由测试覆盖。

4条原自动接受候选经agent检查后撤回：周期被答成“记录”、综合单价误作人工费、费用误作台数、以及含语料不存在的“砂质”条件的多条件题。撤回候选完整内容和原因保存在追加日志中。两版旧500条文件按SHA-256保存于topup_quarantine；没有静默覆盖。其余有效新增样本保持字段与ID不变。新增模型候选补入显式撤回的空号，不改写原候选。

## 3. 模型与生成参数

- 模型：`ollama/qwen3:4b-instruct-2507-q4_K_M`；仅loopback Ollama，无云端模型调用。
- digest：`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`。
- 原生成版本：`p6-silver-generate-v1`；独立补齐版本：`p6-silver-topup-v1`。
- 基础seed：20261106；增量第n批seed=20261106+10000+n，实际20271107至20271153。
- temperature=0.6，top_p=0.9，num_ctx=8192，num_predict=1800；复用原Prompt、schema和LocalOllama适配器。
- 累计最多200批；中断调用消耗尝试但不占用配额。每次恢复重放校验，重新计算有效缺口。

## 4. 基线与最终SHA-256

- 原466条 `silver_cases.jsonl`：`ce4a5d9b42ac3786e049ac331047150245b8431745badfd75512fb0119e5346f`。
- 最终500条：`03f7955b144e31081c778f533322ff68b560459f60ab94bb9699b2ea7a35c410`。
- 增量JSONL：`e779493c7b9cda39aed103fdf3b269ea9ad5093f6d141f72e1afc4292211f791`。
- 完整基线清单：[silver_baseline_sha256.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_baseline_sha256.json)。

基线原始候选506条、去重拒绝39条、最终466条、Gold50条、Chunk447条均核对通过。原466条可由原候选确定性重建，逐字段匹配。所有11个冻结文件哈希再次核对一致；最终文件以原silver_cases.jsonl完整字节为前缀，新样本ID覆盖p6s-0467至p6s-0500。

## 5. pytest与构建验收

- 72 passed，67 subtests passed，0 failed，0 skipped；包含29项新增补齐测试及已有候选/语料相关测试。未运行全仓业务测试或RAG E2E。
- 1条第三方anyio插件的pytest弃用警告，无测试失败。pytest 9.2.0安装在项目venv；未改依赖清单。
- JSONL解析、500总量、精确配额、唯一顺序ID、原466条字段/字节、证据/来源/页码/Chunk、逐字引文、双Chunk、两层去重及模型来源检查均通过。
- 独立审查指出恢复时逐请求来源校验不足，已补充精确请求重建；seed、options、Prompt及哈希、语料哈希、版本异常均拒绝，6项回归测试先失败再通过。
- 中断、输出冲突、并发锁、最大尝试耗尽、语义撤回及归档中断恢复均有测试。
- 最终版连续运行两次build和一次已完成generate，数据、增量日志、统计、验收报告全部SHA-256不变。generate在配额已满时不调用模型。

测试记录：[silver_500_pytest.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_500_pytest.json)；JUnit：[pytest_topup_final.xml](D:/AgentAIProgect/RAG/p6-silver-e2e-500/pytest_topup_final.xml)；幂等证据：[silver_500_reproducibility.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_500_reproducibility.json)。

## 6. 未解决的数据质量风险

50条unanswerable（含原41条及新9条）的不可回答性均未获得全语料语义或人工确认。新9条逐条记录not_semantically_verified；原41条不改字段，统一风险记录在旁车报告。特别是泛化体验/设备组合题可能部分可回答。

原自动校验对数字/型号、逐字引用和字符相似度作检查，不能证明完整语义蕴含、真正跨Chunk推理或排除近义重复。表格解析存在列/单位歧义。`p6s-0473`忠实引用冻结语料的“消耗量114.00”，数值/单位异常仍应人工核查；`p6s-0500`周期依赖完整Chunk表格上下文，措辞也待人工复核。

具体待核查项与50条ID：[silver_500_quality_risks.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_500_quality_risks.json)。这些是agent检查记录，不是伪造的人工审核记录。

## 7. 下一步RAG E2E建议（本次未执行）

人工确认后，冻结本最终SHA、447 Chunk SHA、检索/Embedding/Rerank/生成Prompt/推理参数与运行环境；同一500查询比较BM25、Vector、Hybrid、Hybrid+Rerank。分题型报告Recall@k、MRR、nDCG与证据召回；再分别报告答案正确性/忠实性、引用准确性、拒答/部分回答行为及p50/p95延迟。Gold与Silver结果分开，未确认unanswerable单列。保留逐题检索、生成、引用与计时日志，不用本轮结果直接调参后重报同一测试集。

## 8. 文件路径

- [topup_silver.py](D:/AgentAIProgect/RAG/p6-silver-e2e-500/topup_silver.py)
- [test_topup_silver.py](D:/AgentAIProgect/RAG/p6-silver-e2e-500/test_topup_silver.py)
- [silver_topup_raw.jsonl](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_topup_raw.jsonl)
- [silver_topup_summary.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_topup_summary.json)
- [silver_cases_500.jsonl](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_cases_500.jsonl)
- [silver_500_validation.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_500_validation.json)
- [silver_baseline_sha256.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_baseline_sha256.json)
- [silver_500_pytest.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_500_pytest.json)
- [pytest_topup_final.xml](D:/AgentAIProgect/RAG/p6-silver-e2e-500/pytest_topup_final.xml)
- [silver_500_reproducibility.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_500_reproducibility.json)
- [silver_500_quality_risks.json](D:/AgentAIProgect/RAG/p6-silver-e2e-500/silver_500_quality_risks.json)

- 权威事件目录：`D:\AgentAIProgect\RAG\p6-silver-e2e-500\topup_events`。
- 历史投影：`D:\AgentAIProgect\RAG\p6-silver-e2e-500\topup_history`。
- 语义撤回的旧数据集：`D:\AgentAIProgect\RAG\p6-silver-e2e-500\topup_quarantine`。

## 9. 可复现命令

以下PowerShell命令使用现有追加事件日志重建，已完成generate不会重复生成。保留topup_events与基线清单；不要删除它们来“重新开始”。仅seed相同不保证不同硬件上的模型输出字节相同。

```powershell
& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/topup_silver.py' --check
& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/topup_silver.py' --build --max-batches 200
& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/topup_silver.py' --generate --max-batches 200 --timeout 240
& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' -m pytest 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/test_topup_silver.py' 'D:/AgentAIProgect/RAG/tests/test_eval_candidates.py' 'D:/AgentAIProgect/RAG/tests/test_eval_corpus.py' -q
```

已停止后续评测，等待人工确认。
