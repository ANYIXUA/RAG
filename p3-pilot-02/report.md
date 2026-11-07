# P3-Pilot-02｜BM25 候选池修复与 Rerank 最终诊断

日期：2026-11-05（Asia/Shanghai）。项目：`D:\AgentAIProgect\RAG`。

## 1. 结论与交付边界

本轮完成了候选召回的最小修复和真实复测。22 条原 Gold、3 份 PDF、447 个冻结 Chunk、人工审核记录及实验参数均未修改；没有 commit/push。

- BM25 Only 的 MRR@10 从 **0.000000 → 0.771970**；Hit@10 从 **0/22 → 21/22**。全库诊断 BM25 保持 **0.802273**。
- 修复后 Hybrid 的 MRR@10 为 **0.864448**，低于修复前 **0.930736**，下降 **0.066288**；Hit@1 从 20/22 降为 18/22，Hit@10 仍为 22/22。这个下降如实保留。
- Hybrid+Rerank 的 MRR@10 为 **0.799044**，与修复前相同；相对修复后 Hybrid 仍为负收益 **−0.065404**。Hit@1 为 16/22，Hit@10 为 22/22。
- 四项 Rerank 检查未发现实现错误；保留负收益，不改模型、分数方向、最大长度、候选 TopK、权重或阈值。
- 修复前重跑与 Pilot-01 的 **110 条排序/分数记录及质量指标完全一致**；修复后两次运行同样一致。原始分数以评测器写出的 6 位小数为比对口径，延迟不要求相等。

这是固定小样本上的探索性结果，不是正式 50 条 Benchmark，也不证明其他查询或生产总体上的提升。

## 2. 候选池根因与最小修复

实际入口是 `rag_app/indexing/vector_store.py` 的 `PostgresVectorStore.search()` → `_query_keyword_candidates()` → `_rank_vector_records()`。

旧 SQL 在 `collection_name`、`status='active'` 和前 12 个 token 的 `ILIKE … OR …` 命中集上，执行 `ORDER BY priority DESC, updated_at DESC LIMIT 20`。随后才进行租户/权限过滤、BM25 打分、Top20 选择、分数阈值过滤。

真实数据库诊断确认：447 条 active Chunk 的 priority 全是 50，updated_at 只有一个值（`2026-06-23T14:53:31.581201+00:00`）。旧前 12 token 的 OR 命中集有 125–447 条。通用中文二字组和数字等 token 会扩大 OR 命中范围；priority/update 又没有区分度，因此提前 LIMIT 把大多数相关 Chunk 挡在打分之前。即便这两个字段不相同，业务优先级和更新时间也不能代替 BM25 的相关性排序。

旧 20 条候选池仅 **1/22** 题含相关 Chunk（B03）；这不等于 Hit@10。B03 在该候选集的原始 BM25 排名之后还会受固定相对阈值过滤，最终旧 BM25 指标确为 0。取消提前截断后的字面命中集则 **22/22** 题含相关 Chunk。

最终修复仅改变字面候选获取：

1. 使用所有去重后的查询 token，避免第 12 个 token 后的判别词永远无法参与召回；分词器未改。
2. 保留参数化 `ILIKE OR`、原 collection 与 active 状态约束，取消按 priority/update 和 SQL LIMIT 提前选 20 条。
3. 以 `chunk_id ASC` 提供可重复的候选输入顺序；原有授权过滤先执行，再用原 BM25 打分及固定 candidate_k 选 Top20。

修复后每题字面候选为 **173–447** 条；14 题因纳入后续 token 得到额外字面命中项。没有修改 `_filter_authorized_records` / `_record_allowed`、文档 ID/metadata、其他检索入口的过滤条件、BM25 k1/b、归一化、融合公式或 Rerank 生产代码。当前 search 没有独立的 document_ids 参数；本轮没有新设或放宽文档访问规则。

本轮进入工作区时已有一份包含 2000 行扫描上限、命中数排序及归一化移动的未提交草稿。原草稿和入口 diff 均保存在 `baseline/`。最终修复移除了这个仍会丢候选的扫描上限，并恢复原 BM25 归一化位置；没有采用额外二阶段重打分来追求更高指标。原有 `_scratch/` 模拟结果不作为最终对照结果。

BM25 修复版与全库诊断并不要求完全相等：生产打分仍在该查询的字面命中集内计算 DF/平均长度，全库诊断则在全部 447 条上计算。两者首相关名次的差异集中在 B03（修复版第 3，全库第 1），解释了 MRR 差距 **0.030303**。B14 两组均未进 Top10。没有为了使两组相等而改变原打分统计口径。

候选证据：[`runs/candidate_recall.json`](runs/candidate_recall.json)。其中 old/fixed pool 数量及相关 ID 是 SQL 实际读数，未拿未施加阈值的候选排名冒充正式指标。

## 3. 实测指标与逐题变化

before 为保存的原 HEAD 实现重跑；fixed 为独立的 `fixed2` 运行。A2 全库 BM25 始终只是诊断组。指标均按原二元相关 Chunk ID 集合计算，未改 Gold。

| 运行 | 方法 | Hit@1 | Hit@10 | MRR@10 | NDCG@10 | Recall@10 | p50 ms | p95 ms |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| before | bm25_only | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 278.5 | 468.3 |
| before | vector_only | 0.727273 | 0.954545 | 0.802020 | 0.834976 | 0.954545 | 166.0 | 415.0 |
| before | hybrid | 0.909091 | 1.000000 | 0.930736 | 0.943321 | 1.000000 | 355.1 | 717.2 |
| before | hybrid_rerank | 0.727273 | 1.000000 | 0.799044 | 0.838090 | 1.000000 | 7909.9 | 9800.6 |
| before | bm25_full_corpus | 0.727273 | 0.954545 | 0.802273 | 0.841364 | 0.954545 | 214.9 | 337.1 |
| fixed | bm25_only | 0.681818 | 0.954545 | 0.771970 | 0.818637 | 0.954545 | 494.2 | 841.6 |
| fixed | vector_only | 0.727273 | 0.954545 | 0.802020 | 0.834976 | 0.954545 | 74.3 | 194.0 |
| fixed | hybrid | 0.818182 | 1.000000 | 0.864448 | 0.894761 | 1.000000 | 437.4 | 675.7 |
| fixed | hybrid_rerank | 0.727273 | 1.000000 | 0.799044 | 0.838090 | 1.000000 | 4382.8 | 7760.9 |
| fixed | bm25_full_corpus | 0.727273 | 0.954545 | 0.802273 | 0.841364 | 0.954545 | 138.8 | 205.6 |

名次为首个相关 Chunk 在 Top10 内的名次；— 表示 Top10 未命中。完整 Top20、多相关名次与原始分数见 runs/*/rankings.jsonl 和 runs/per_query.json。

| 题号 | BM25 前 | BM25 后 | 全库诊断 | Hybrid 前 | Rerank 前 | Hybrid 后 | Rerank 后 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B01 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B02 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B03 | — | 3 | 1 | 7 | 2 | 4 | 2 |
| B04 | — | 2 | 2 | 1 | 1 | 1 | 1 |
| B05 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B06 | — | 4 | 4 | 1 | 7 | 7 | 7 |
| B07 | — | 1 | 1 | 1 | 2 | 1 | 2 |
| B09 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B12 | — | 5 | 5 | 1 | 1 | 2 | 1 |
| B13 | — | 2 | 2 | 1 | 1 | 1 | 1 |
| B14 | — | — | — | 3 | 9 | 8 | 9 |
| B15 | — | 1 | 1 | 1 | 5 | 1 | 5 |
| B16 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B17 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B18 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B19 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B20 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B21 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B22 | — | 5 | 5 | 1 | 8 | 1 | 8 |
| B25 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B26 | — | 1 | 1 | 1 | 1 | 1 | 1 |
| B27 | — | 1 | 1 | 1 | 1 | 1 | 1 |

完整原句、Gold ID 和每个相关 Chunk 的全部返回名次见 [`per_query.csv`](per_query.csv)、[`runs/per_query.json`](runs/per_query.json)；所有返回 Chunk ID/分数见各次运行的 `rankings.jsonl`。表中的 — 只表示 Top10 未命中，不代表没有返回结果。

Hybrid 首相关名次变化集中在 B03（7→4）、B06（1→7）、B12（1→2）、B14（3→8）。候选扩展改变了 BM25 的统计总体及其与向量分数的融合结果。语义单路和全库诊断组不变；本轮没有据此调整 0.7/0.3 权重或阈值。

延迟仅为本机 CPU 的描述性单轮数据，含检索及适用时的重排，不含查询向量化。before 阶段有测试并行，机器负载不同，不据此宣称性能提升。`fixed1` 发生过诊断读事务与并发初始化 DDL 的锁等待，故上表没有采用其延迟。探针改为 autocommit 并结束后，`fixed2` 在无并行数据库探针的情况下独立执行；扩大字面候选扫描的开销仍应在更大语料上另行评估。

## 4. Rerank 最终诊断

模型保持 `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`，本地 HF revision 为 `1427fd652930e4ba29e8149678df786c240d8825`，CPU 推理，Identity 激活，默认最大序列长度 512。

| 检查项 | 真实证据与结论 |
| --- | --- |
| 分数方向 | 原始单标签 logits，数值越高排名越靠前；生产代码 `sort(..., reverse=True)` 正确。负分也按数值大小降序处理。方向与 [Sentence Transformers 官方用法](https://sbert.net/docs/cross_encoder/usage/usage.html) 一致。 |
| Query / Chunk | 截获真实 `predict()` 调用；before 和 fixed 各 22×20=440 对输入与原 Gold 原句、冻结 Chunk 正文的 SHA256 完全相符，没有标题替代正文、问句串位或预先字符截断。 |
| 分数对应与排序 | `predict` 输出数量等于输入数量；生产 `zip` 对应每条输入。已检查本地库 `cross_encoder/model.py` 的长度排序及逆置换，输出恢复原输入顺序。最终顺序等于真实分数降序后再取 TopK。 |
| 候选 TopK | 每题 20 条；D 的输入顺序与对应 C 的实际 Top20 完全相同；排序前后候选 ID 集合相同，没有先取更小 TopK、漏项或补位。 |
| 截断 | 实际 `model.preprocess()` 的 input_ids 与默认 `longest_first`、max_length=512 的 tokenizer 编码逐项相同；右侧截断。每组 440 对中 146 对超过模型长度，所有 Query 都完整保留。未改截断策略或长度。 |

逐个下降案例的相关 Chunk 结果如下；logit 是实际模型输出，不是融合分数：

| 题号 | 旧 Hybrid→Rerank | 修复后 Hybrid→Rerank | 相关 logit | 同题第一名 logit | 原 token 数→编码数 | 检查结果 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| B06 | 1→7 | 7→7 | 7.601420 | 9.314030 | 412→412 | 无截断，模型确实把其他候选排在前面。 |
| B07 | 1→2 | 1→2 | 8.888125 | 9.745404 | 152→152 | 无截断，分数与名次一致。 |
| B14 | 3→9 | 8→9 | 4.443545 | 7.564623 | 748→512 | 默认长度截断，Gold 的 text_contains 锚点仍在编码保留范围内。 |
| B15 | 1→5 | 1→5 | 5.817199 | 8.173324 | 577→512 | 默认长度截断，Gold 的 text_contains 锚点仍在编码保留范围内。 |
| B22 | 1→8 | 1→8 | 6.092885 | 8.783234 | 505→505 | 无截断，分数与名次一致。 |

修复前共 5 题下降、1 题改善（B03）；修复后共 4 题下降、2 题改善（B03、B12）。B06 修复后的 Hybrid 已为第 7，Rerank 保持第 7。

B14/B15 的锚点被保留，不足以证明被截掉的其他上下文没有影响；本轮没有做无截断反事实实验，不能把下降原因定量归因于截断或模型本身。可以确认的是：在所检查的方向、输入、候选深度、编码和排序实现上没有发现明显错误。负收益作为当前模型与配置在这些题目上的实测结果保留，停止调参。

审计证据：[`runs/rerank_audit.json`](runs/rerank_audit.json) 包含逐对输入哈希、实际分数、编码长度、保留字符位置与锚点范围；各运行的 `rerank_inputs_scores.json` 保留真实调用记录，预热记录不参与 22 题指标。

## 5. 固定输入、配置与可复现性

- Gold：原批次 9+13=22 条，原 query、相关 ID、requires_all_evidence 与人工审核字段不变；排除项与 Pilot-01 相同。
- Corpus：447 Chunk、3 文档；SHA256 `5995ee6be2871ee7c553ce5fe2f3002a7938dbffedf0ec2b8fed28af8107f4d6`。
- 每次运行均预检数据库 active Chunk ID 集合与冻结语料一致，正文 SHA256 差异为 0。
- 进入工作区时对 Pilot-01 全目录、storage/evaluation、data（含 3 PDF）、config/*.json 与 .env 共 161 个文件记录哈希，每次对照前后以及最终交付前核对。审核记录没有修改。
- PostgreSQL/pgvector，collection=default。tenant_id/permission_tags 均按原实验为 null；租户/权限规则另有回归测试，不能将此 Pilot 当作所有身份组合的集成验收。
- Query embedding：原 DashScope OpenAI-compatible `text-embedding-v4`，1024 维。用户本轮明确授权继续调用原接口；22 条 query 与原 1 条预热 query 的真实向量缓存到 `runs/query_vectors.json`，三个运行共用完全相同的向量。缓存 SHA256 `2eead8c09347b3ed31df3774b3a53a33ead5fec93275a2fd4062f144988cc062`。
- retrieval_top_k=20、retrieval_candidate_k=20、evaluation K=1/3/5/10；语义/BM25 权重 0.7/0.3；min_similarity_score=0.05、relative_score_threshold=0.35；BM25 k1=1.5、b=0.75。Query rewriting 关闭。
- 复用原评测器，seed 参数仍为 0，无采样；本轮未安装/升级依赖。模型、配置与实际代码哈希见 [`experiment_config.json`](experiment_config.json) 和每次 `comparison_metadata.json`。原评测器写出的 run_config/metrics 中保留 P3-Pilot-01 标识，Pilot-02 的有效候选生成差异以这两份扩展元数据为准。
- [`runs/baseline_identity_verified.json`](runs/baseline_identity_verified.json)：Pilot-01 run1 vs 本轮 before，110/110 记录排序及 6 位小数分数一致，质量指标一致。
- [`runs/repeatability.json`](runs/repeatability.json)：fixed1 vs fixed2 同样 110/110 一致，含 A2 的质量指标一致、预检非空语料哈希、Gold 哈希和共享向量哈希一致。延迟抖动独立记录。

## 6. 测试结果与复现命令

| 验证 | 结果 | 日志 |
| --- | --- | --- |
| 旧 HEAD 上的候选回归 | 3 项中 2 项按预期失败：早期上限丢候选、末尾关键 token 未入谓词；空 query 通过 | `checks/regression_head_red.txt` |
| 进入工作区的 2000 上限草稿 | 同样 2 项失败 | `checks/regression_red.txt` |
| 修复后针对性测试 | 43/43 通过，涵盖候选获取、授权、BM25 排序、Rerank 配对/负分/截断顺序和评测指标 | `checks/targeted_final.txt` |
| 全量 unittest | 运行 254 项：246 通过、8 跳过；跳过项为未配置专用 PostgreSQL 集成 DSN 的既有测试 | `checks/unittest_unsandboxed.txt` |
| 真实对照与重复 | before/fixed1/fixed2 均完成 22 题×5 组，Rerank 无跳过 | `checks/*_run.txt` |
| 实际编码审计 | before/fixed 每组 440 对通过匹配，下降题逐题检查完成 | `checks/rerank_audit_final.txt` |

沙箱内首次全量测试停在既有 FastAPI TestClient；有界复核在 45 秒超时处保存了堆栈，随后在沙箱外运行同一套全量测试通过。未修改 API 或测试以绕过问题。外部 Embedding 调用最初被自动审批阻止；用户明确授权原接口后才执行。真实测试及指标使用已授权成功运行的产物。

以下命令在项目根目录用原 venv 执行。前提：本机 PostgreSQL 已发布到 127.0.0.1:15432，项目 .env 和配置不变，本地原 CrossEncoder 快照可用。输出目录必须是新的，runner 会拒绝覆盖已有 metrics.json。现有向量缓存会直接复用；缓存缺失时会调用原 DashScope 接口。

```powershell
# 旧实现对照；读取 baseline/vector_store_before.py，原工作区文件不回滚
.\venv\Scripts\python.exe -B p3-pilot-02\run_comparison.py --variant before --out-dir p3-pilot-02\runs\repro-before

# 修复后主运行与独立重复（顺序执行，避免并发探针/DDL 干扰）
.\venv\Scripts\python.exe -B p3-pilot-02\run_comparison.py --variant fixed --out-dir p3-pilot-02\runs\repro-fixed1
.\venv\Scripts\python.exe -B p3-pilot-02\run_comparison.py --variant fixed --out-dir p3-pilot-02\runs\repro-fixed2

.\venv\Scripts\python.exe -B p3-pilot-02\verify_runs.py --run-a p3-pilot-02\runs\repro-fixed1 --run-b p3-pilot-02\runs\repro-fixed2 --out p3-pilot-02\runs\repro-repeatability.json

# 只读 Rerank 编码审计；使用本地模型，不重新推理分数
.\venv\Scripts\python.exe -B p3-pilot-02\audit_rerank.py --before-run p3-pilot-02\runs\repro-before --fixed-run p3-pilot-02\runs\repro-fixed2 --out p3-pilot-02\runs\repro-rerank-audit.json

# 候选 SQL 读数；在主运行外单独执行
.\venv\Scripts\python.exe -B p3-pilot-02\probe_candidates.py

# 重新汇总本次已保存的 before/fixed2 结果
.\venv\Scripts\python.exe -B p3-pilot-02\summarize.py

.\venv\Scripts\python.exe -B -m unittest tests.test_keyword_candidates tests.test_vector_store tests.test_rerank tests.test_retrieval_metrics tests.test_evaluation -v
.\venv\Scripts\python.exe -B -m unittest discover -v
git diff --check
```

全量测试不应配置为在本次冻结集合上执行可变更数据的集成测试。本轮没有设置专用集成 DSN，8 项依赖该变量的测试维持跳过。

## 7. 剩余限制与停止条件

最小修复取消了 relevance-blind 截断，代价是宽泛字面查询会扫描更多 Chunk 并在 Python 中计算 BM25。本轮只验证 447 条语料；没有引入倒排索引、数据库全文检索或其他复杂架构，不能据此声称大库性能已经可用。

本轮没有调整标签、模型超参数或筛选“更好看”的运行。工作区其他既有未提交内容与奇异未跟踪文件均保留；原 Gold/PDF/Chunk/审核文件均保持原字节。代码评审未发现阻断问题；评审提出的延迟来源问题已改为使用 fixed2，语料身份已额外通过非空预检哈希验证。

目标为确认所查检索实现正确并取得可信探索性结果，现已达到。本轮在此停止，不自动 commit/push，不继续调参。
