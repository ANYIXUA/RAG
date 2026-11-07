# P3-Pilot-01　RAG 检索评估全链路验证报告

- 项目：`D:\AgentAIProgect\RAG`
- 范围：22 条已签核 Gold × 447 个冻结 Chunk × 四组检索方式（另 1 组诊断）
- 性质：**探索性评估**，不是 50 条 Gold 的正式 Benchmark
- 主运行：`p3-pilot-01/runs/run1`（`run2` 用于可复现性复核）
- 机器生成的数据表：`p3-pilot-01/docs/generated_tables.md`

---

## 0. 六个问题的直接回答

**1）四组检索方案是否都成功运行？**
是。A（BM25 Only）、B（Vector Only）、C（Hybrid）、D（Hybrid + Cross-Encoder Rerank）
都在同一份冻结语料、同一批 22 条查询、同一套参数下真实跑完，没有降级、没有占位实现。
D 组的重排模型是本轮按项目 `pyproject.toml` 的 `rerank` 可选依赖真实安装并加载的
（`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`，HF commit `1427fd65…`），不是 mock。
另加一组 **A2（BM25 全库，诊断用，不计入四组对照）**，用于把「BM25 差」和
「BM25 的候选池差」区分开。

**2）22 条 Gold 实际加载了多少条？**
22 条（第一批 9 + 第二批 13），全部经 `rag_app.operations.evaluation.load_retrieval_eval_cases`
解析；query、expected、Gold ID 齐全；24 个相关 Chunk ID 全部存在于冻结语料；
不含 B23（未签核）、B24（已拒收）、B28–B42（未签核第三批）。

**3）各组真实 MRR@10 / Hit@K / NDCG@10？**

| 方案 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 | NDCG@10 | Recall@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A BM25 Only | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| B Vector Only | 0.727 | 0.864 | 0.909 | 0.955 | 0.802 | 0.835 | 0.955 |
| C Hybrid | 0.909 | 0.955 | 0.955 | 1.000 | 0.931 | 0.943 | 1.000 |
| D Hybrid + Rerank | 0.727 | 0.818 | 0.864 | 1.000 | 0.799 | 0.838 | 1.000 |
| *A2 BM25 全库（诊断）* | *0.727* | *0.818* | *0.955* | *0.955* | *0.802* | *0.841* | *0.955* |

A 组全 0 **不是脚本故障**：见 §7.1，生产 BM25 的候选池在本题库上退化，
22 题里只有 1 题的相关 Chunk 进得了池，那一题又被相对分数阈值切掉。

**4）Rerank 是否带来了可观察的排序改善？**
没有。相对 C 组：Hit@1 −0.182、MRR@10 −0.132、NDCG@10 −0.105、Recall@10 不变；
6 道题的首命中名次发生变化，其中 5 道变差、1 道变好（B03：7 → 2，仍未进第 1）。
唯一正向变化是 `required_evidence_coverage@10` 从 0.875 升到 1.0（4 道双证据题里
B14 的第 9 名仍落在 Top10 内），属于覆盖度而非排序质量提升。
代价是单次检索 p50 从 125 ms 涨到 3293 ms（run1 实测，CPU 推理）。

**5）实验能否重复运行并得到一致结果？**
能。两次完整运行（run1 / run2）的 **110 条逐题排序记录与全部分数逐条相同**，
canonical digest 均为 `3cbf93d00970c71cd4b23c939cbb6e6bb9b1b93e928c6bb3fdebbed8f238c8ce`，
除耗时外的所有指标逐位一致；语料哈希与 Gold 来源哈希一致。
**耗时不可复现**：同一台机器两次运行相差约 1.8–2.8 倍（run2 期间有其它负载），
所以耗时只能用于量级比较，不能当作 SLA 结论。

**6）距离正式 50 条 Gold Benchmark 还有哪些必要工作？**
见 §10：还缺 28 条已签核 Gold；相关性标注要从「页级/三元组」升级到「行级 Chunk」；
BM25 候选池缺陷必须先定性再定标（否则 BM25 基线没有可比性）；查询改写是否纳入评测需拍板；
评测入口要从独立脚本收进 `rag_cli`；重排模型与耗时需要重新选型/加 GPU；
延迟测量需要独立静默环境。

---

## 1. 评估入口审计（复用了什么，新增了什么）

| 能力 | 位置 | 本轮用法 |
| --- | --- | --- |
| Gold 装载 | `rag_app/operations/evaluation.py::load_retrieval_eval_cases` | 直接复用，两个批次各调一次 |
| BM25 | `rag_app/indexing/vector_store.py::_bm25_scores`（k1=1.5, b=0.75，中文二字组 + ASCII 词） | 生产路径直接调用；A2 诊断复用同一函数 |
| 向量检索 | `PostgresVectorStore._search_semantic_candidates`（pgvector `<=>`，1−余弦距离） | 复用 |
| 混合检索 | `PostgresVectorStore.search` → `_rank_vector_records` → `_combine_scores` | 复用，未改一行 |
| Cross-Encoder 重排 | `rag_app/retrieval/rerank.py::CrossEncoderReranker` | 复用 |
| 指标 | 原 `evaluation.py` 只有 `hit_at_k`/`mrr`/`no_result_rate`，且按 `source`/`section_title`/`text_contains` 判命中 | **新增** `rag_app/operations/retrieval_metrics.py`（Chunk ID 判定 + Hit@K/MRR@10/NDCG@10/Recall@10） |
| Benchmark 入口 | `python -m rag_app.cli evaluate-retrieval` | 未使用：它不含 Chunk ID 级判定与 NDCG，且会连带跑生成链路；本轮用独立脚本 `p3-pilot-01/run_pilot.py` 直接驱动检索层 |

**对生产代码的唯一改动是"新增"**：新指标模块 + 其单元测试。
`vector_store.py`、`rerank.py`、`online.py`、`evaluation.py`、Gold、PDF、Chunk **均未修改**。

---

## 2. 数据与预检

| 项 | 值 |
| --- | --- |
| Gold 第一批 | `…/p2-gold-04/retrieval_gold_batch01_9.jsonl`（9 条），sha256 `0ee8bbcd…` |
| Gold 第二批 | `…/p2-gold-06/retrieval_gold_batch02_13.jsonl`（13 条），sha256 `5bfc8df9…` |
| 合并快照 | `p3-pilot-01/data/gold_22_merged.jsonl`，22 行，sha256 `9a4768df…`（仅按字节拼接，内容未改） |
| 冻结语料 | `storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl`，447 Chunk / 3 文档 |
| 语料 sha256 | `5995ee6be2871ee7c553ce5fe2f3002a7938dbffedf0ec2b8fed28af8107f4d6` |
| 语料 snapshot_id | `sha256:eedd1783956ca582c1cdfbbdad486fdf1554c7dab79681bba0675eec47089fce` |
| 相关 Chunk 总数 | 24（22 题；B12、B25 各 2 个） |
| 双证据题 | 4 题（B07、B12、B14、B15） |

预检全部通过（机器可查：`p3-pilot-01/runs/run1/preflight.json`）：

- 22 条 Gold，query / expected / Gold ID 齐全，题号白名单
  `B01–B07,B09,B12` + `B13–B22,B25–B27` 完全匹配，无重复题、无重复题号；
- 24 个相关 Chunk ID 全部命中冻结语料，缺失 0；
- 排除项 `B23`、`B24`、`B28–B42` 出现次数为 0；
- 向量库（`127.0.0.1:15432/default`）active Chunk 447 个，与冻结语料 **ID 集合相同**、
  **正文 sha256 逐条相同（0 处不一致）**，因此"用向量库检索"等价于"在冻结语料上检索"。

> 说明：语料快照本身不含向量，向量存在 pgvector 中。为了避免重复调用 Embedding API
> 产生与索引时不同的向量，本轮直接读取向量库，并以上述等价性检查作为前提。

---

## 3. 实验配置（四组完全一致的部分）

| 参数 | 值 | 来源 |
| --- | --- | --- |
| Embedding 模型 | `text-embedding-v4`，1024 维，DashScope OpenAI 兼容端点 | `config/model.json` |
| Reranker 模型 | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`，HF commit `1427fd652930e4ba29e8149678df786c240d8825` | `config/retrieval.json` |
| 检索 TopK | 20（生产排序深度，四组相同） | 本轮固定 |
| 候选池 candidate_k | 20 | `RAG_RETRIEVAL_CANDIDATE_K` |
| 最终评估 K | Hit@1/3/5/10，MRR@10，NDCG@10，Recall@10（上限 10） | 本轮固定 |
| Rerank 候选数 | 20（= C 组 Top20 全量送入重排），重排后再取 20 供截断 | 本轮固定 |
| 融合算法 | **加权线性融合，非 RRF**：`score = (0.7/1.0)·cos + (0.3/1.0)·(bm25/max_bm25)` | `_combine_scores` |
| 语义权重 / BM25 权重 | 0.7 / 0.3 | `config/retrieval.json` |
| 分数过滤 | `min_similarity_score=0.05`、`relative_score_threshold=0.35`，四组相同 | 同上 |
| 查询改写 / 意图路由 | **未启用**，四组都用 Gold 原句 | 本轮决定（隔离变量） |
| 租户 / 权限标签 | `None` / `None`（与 `UserContext()` 默认一致） | 生产默认 |
| 随机性 | 检索为确定性打分；重排为 CPU 前向推理，无采样。`random.seed=0`、`PYTHONHASHSEED=0` | — |
| 配置指纹 | `a79ed9000b6114da` | `Settings.config_fingerprint` |

环境：Windows 11 (10.0.26200)，Python 3.12.14，psycopg 3.3.4，torch 2.15.0+cpu，
sentence-transformers 6.2.0，transformers 5.22.1，openai 2.41.1。
DSN 使用宿主机映射端口 `127.0.0.1:15432`（`.env` 里是容器名 `postgres`，未改 `.env`，
只在进程内替换主机与端口）。

### 为什么四组"检索返回 20 条"

- C 组若要作为 D 组的候选池，必须返回 20 条；
- 生产非重排路径的候选池同样是 `candidate_k=20`，所以 A/B 返回 20 条**不改变**其候选池，
  只改变最终截断长度；
- 指标统一在 K≤10 上截断计算，因此 A/B/C/D 的评估口径一致。

---

## 4. 指标口径（必须先说清楚的部分）

1. **相关性是二元的、以 Chunk 为单位**：`chunk_id ∈ retrieval_relevant_chunk_ids`
   即相关。相关集合来自已签核 metadata，本轮未做任何改写或补充。
2. **多相关 Chunk 的评分规则**：
   - `Hit@K`：Top-K 内**至少一个**相关 Chunk 记 1；
   - `MRR@10`：**首个**相关 Chunk 名次的倒数，Top10 内没有则记 0；
   - `NDCG@10`：二元增益 `DCG@10 = Σ rel_i / log2(i+1)`，
     `IDCG@10 = Σ_{i=1..min(|R|,10)} 1/log2(i+1)`，`NDCG = DCG/IDCG`；
   - `Recall@10` = `|Top10 ∩ R| / |R|`（本题库每題 |R| ∈ {1,2}，标注支持该指标）；
   - `required_evidence_coverage@10`（补充）：对 4 道双证据题，Top10 覆盖
     `evidence_chunk_ids` 的比例，1.0 才代表"两页证据同时在结果里"。
3. **TopK 截断方式**：先按生产排序取前 20 条，再按评估 K 截断；截断只丢尾部，
   不重排、不补位、不做分数平滑。重复 chunk_id 只按首次出现计分（生产返回本身无重复）。
4. **相对提升率公式**：`相对变化 = (候选指标 − 基线指标) / 基线指标 × 100%`，
   仅当基线 > 0 时给出；基线为 0 时只报绝对变化（本轮 A 组全 0，故多数相对变化为空）。

---

## 5. 四组结果

见表 1（`generated_tables.md`）与 §0 第 3 问。补充信息：

| 方案 | 平均返回条数 | 空结果率 | p50 (ms) | p95 (ms) |
| --- | ---: | ---: | ---: | ---: |
| A BM25 Only | 8.73 | 0.0 | 89.97 | 132.61 |
| B Vector Only | 20.0 | 0.0 | 76.27 | 92.71 |
| C Hybrid | 20.0 | 0.0 | 124.56 | 189.40 |
| D Hybrid + Rerank | 20.0 | 0.0 | 3292.83 | 3552.94 |
| *A2 BM25 全库* | *11.23* | *0.0* | *111.53* | *151.23* |

A 组平均只有 8.7 条，是 `relative_score_threshold=0.35` 把尾部切掉了——这也是
§7.1 里 B03 失手的直接原因。

### 指标差异（绝对变化）

| 对比 | ΔHit@1 | ΔHit@10 | ΔMRR@10 | ΔNDCG@10 | ΔRecall@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Vector vs BM25 | +0.727 | +0.955 | +0.802 | +0.835 | +0.955 |
| Hybrid vs BM25 | +0.909 | +1.000 | +0.931 | +0.943 | +1.000 |
| Hybrid+Rerank vs BM25 | +0.727 | +1.000 | +0.799 | +0.838 | +1.000 |
| **Hybrid+Rerank vs Hybrid** | **−0.182** | **0.000** | **−0.132** | **−0.105** | **0.000** |
| Hybrid vs Vector | +0.182 | +0.045 | +0.129 | +0.108 | +0.045 |
| BM25 全库 vs BM25 生产 | +0.727 | +0.955 | +0.802 | +0.841 | +0.955 |

相对提升率（基线为 Hybrid，仅列非 0）：`Rerank` 的 Hit@1 = −0.1818/0.9091 = −20.0%，
MRR@10 = −14.15%，NDCG@10 = −11.16%。Hybrid 相对 Vector：Hit@1 +25.0%，
MRR@10 +16.05%，NDCG@10 +12.98%，Recall@10 +4.76%。
BM25 基线为 0，按口径不给相对值。

---

## 6. 逐题排序

完整逐题表见 `generated_tables.md` 表 3（首命中名次）与表 4（Rerank 引起的名次变化），
逐条排序与分数见 `p3-pilot-01/runs/run1/rankings.jsonl`（110 条记录 = 22 题 × 5 方案）。

要点：

- **C 组 22/22 题在 Top10 命中，其中 20 题排第 1**；未排第 1 的只有 B03（第 7）与
  B14（第 3）。
- **D 组同样 22/22 命中 Top10，但只有 16 题排第 1**；新增 6 题掉出第 1：
  B03→2、B06→7、B07→2、B14→9、B15→5、B22→8。
- **B 组唯一漏题是 B06**：相关 Chunk 语义排名第 13，去阈值后本来在 Top20 内，
  被 `relative_score_threshold=0.35` 切断；C 组靠 BM25 分把它抬到第 1。
- **A2 组唯一漏题是 B14**：表 1 的"中级—智能家居（控制）—系统架构"要求，
  纯关键词（二字组）与该行文本重合度低。

---

## 7. 分析

### 7.1 生产 BM25（A 组）为什么是 0

这不是脚本 bug，是**生产候选池在当前数据库中退化**，可复现、可量化：

1. `_query_keyword_candidates` 的 SQL 是
   `WHERE chunk_text ILIKE '%token%' OR … ORDER BY priority DESC, updated_at DESC LIMIT 20`。
2. 本题库 447 个 Chunk 的 `priority` **全部为 50**、`updated_at` **全部是同一个时间戳**
   （`2026-06-23 14:53:31.581201+00`，一次批量导入）。于是 `ORDER BY` 完全无区分度，
   `LIMIT 20` 只是在"命中任一 token 的几百个 Chunk"里按物理顺序取 20 行。
3. 而 token 是 ASCII 词 + 中文二字组，`OR` 关系，命中面极大：
   22 题的 token 命中数在 **125–447**（满库 447）之间，B02/B07/B21 甚至命中全库。
4. 实测：22 题中只有 **B03** 的相关 Chunk 出现在这 20 行里；其余 21 题
   相关 Chunk 连候选池都没进（`generated_tables.md` 表 5）。
5. B03 的相关 Chunk 进了池，去掉阈值后本应排第 5（仍在 Top10 内），
   但它的分数低于榜首的 35%，被 `relative_score_threshold=0.35` 切掉——
   这也是 A 组平均只返回 8.7 条的原因。

**结论**：A 组的 0.000 度量的是"候选池 + 阈值"这条链路，而不是 BM25 打分能力。
把同一个 `_bm25_scores` 放到全部 447 个 Chunk 上重算（A2 诊断组），
Hit@1 0.727 / Hit@10 0.955 / MRR 0.802，与向量检索基本持平。
所以真正的结论是：**BM25 打分可用，BM25 的候选筛选不可用**。

这是本轮最重要的发现，也直接影响正式 Benchmark 的可比性——见 §10。

### 7.2 哪些查询 BM25 更好

按生产配置 A：**没有一题**（0/22）。

按 A2（全库 BM25）与 B（向量）逐题比较首命中名次：

| 更优方 | 题目 | 现象 |
| --- | --- | --- |
| BM25 更好 | B03（版本号）、B07（附录 A.2 尺寸）、B09（25±2℃ 表面温度）、B15（表1 高级/物联网网关）、B06（4.2 职业编码，向量掉出 Top10） | 查询含强字面锚点（版本号、编号、数值、专有名词），字面重合直接命中 |
| 向量更好 | B04（7.2 权重表）、B12（3.2.2/3.2.3 双条目）、B13（5.7 五项）、B14（表1 中级系统架构）、B22（4.8.2 账号） | 需要对表格行、章节语义做匹配，字面 token 与答案文本不成对 |
| 平手 | 其余 12 题（多为单页精确实体题，两路都第 1） | — |

### 7.3 混合检索相对单路的变化

- 相对**向量**：Hit@1 +0.182、Hit@10 +0.045、MRR +0.129、NDCG +0.108。
  收益集中在 2 题——B06（13 → 1）与 B15（9 → 1），都是"向量排名靠后、但关键词信号强"的场景。
  代价是 1 题变差：B03（5 → 7），因为融合把纯语义已经排对的封面块压后。
- 相对**BM25**：全面碾压（A 组为 0），但如上所述这个对比本身被候选池缺陷污染，参考价值有限。
- 融合方式确认：**加权线性融合，不是 RRF**，权重 0.7/0.3，BM25 先按候选池内最大值归一化。
  这意味着两路分数的量纲被强行拉平，`0.3` 的权重足以把语义第 13 名抬到第 1（B06），
  也足以把语义第 5 名压到第 7（B03）——融合权重对排序的杠杆比直觉大。

### 7.4 Rerank 对最终排序的影响

- 排序指标全面下降（Hit@1 −20.0%、MRR −14.1%、NDCG −11.2%），召回不变（Hit@10 / Recall@10 都是 1.0）。
- 6 题名次变化：**5 题变差、1 题变好**。

| 题号 | C | D | 说明 |
| --- | ---: | ---: | --- |
| B03 | 7 | 2 | 唯一改善，仍未到第 1 |
| B07 | 1 | 2 | 轻微变差 |
| B14 | 3 | 9 | 双证据题，仍留在 Top10 |
| B15 | 1 | 5 | 变差 |
| B06 | 1 | 7 | 变差 |
| B22 | 1 | 8 | 变差 |

失败原因（可直接从分数观察）：`mmarco-mMiniLMv2` 是 MS MARCO 多语种重排模型，
输入是「短查询 × 长 Chunk」。本语料一个 Chunk 往往是整页表格/整段条文（数百字），
`CrossEncoder` 又使用默认 512 token 截断；中文表格行与查询的字面/语序差异大，
模型给出的相关性分数与"这一页是否含答案行"并不一致，于是把原本靠融合分数排对的
页面整体压低。B14/B15/B22 都属"整页/整表"型目标，问题最集中。

- 唯一的正向信号是 `required_evidence_coverage@10` 0.875 → 1.0：
  B14 的第 9 名仍在 Top10，两块证据同时可见。这说明**重排改变的是次序，不是召回**，
  若下游生成对次序不敏感，重排的伤害会小于排序指标的降幅。
- 代价明确：p50 从 125 ms → 3293 ms（run1）/ 350 ms → 7204 ms（run2），
  即 **20–26 倍**延迟换一个更差的排序，本轮配置下不划算。

### 7.5 失败案例清单

| 题号 | 方案 | 失败阶段 | 直接原因 |
| --- | --- | --- | --- |
| 除 B03 外的 21 题 | A BM25 | `candidate_pool_miss` | 相关 Chunk 未进入 20 行候选池（priority/updated_at 无区分度 + ILIKE OR 全命中） |
| B03 | A BM25 | `filtered_by_threshold` | 进池，去阈值后本应排第 5；得分低于榜首 35%，被相对分数阈值切掉 |
| B06 | B Vector | `filtered_by_threshold` | 语义第 13，被相对阈值切掉（去阈值后在 Top20 内） |
| B14 | A2 BM25 全库 | `not_in_full_corpus_ranking` | 表格行语义与二字组重合度低，全库 BM25 也进不了 Top10 |
| B06、B14、B15、B22、B07 | D Rerank | 命中但排序下降 | 见 §7.4 |
| — | C Hybrid | 无 Top10 失败 | 2 题非第 1（B03=7、B14=3） |

---

## 8. 可复现性

| 检查项 | 结果 |
| --- | --- |
| 两次运行逐题排序是否一致 | **是**，110/110 条记录相同，0 处差异 |
| 两次运行分数是否一致 | **是**（分数保留 6 位小数后逐条相同，含重排分数） |
| 除耗时外指标是否一致 | **是** |
| canonical digest | `3cbf93d0…`（两次相同） |
| 语料哈希是否一致 | 是，`5995ee6b…` |
| Gold 来源哈希是否一致 | 是，6 个源文件全部一致 |
| 配置指纹是否一致 | 是，`a79ed9000b6114da` |
| 耗时是否一致 | **否**。run1 全流程 108.7 s，run2 232.3 s；C 组 p50 125→350 ms，D 组 3293→7204 ms |

耗时差异的原因：run2 期间机器上仍有其它进程（依赖安装/模型下载后的磁盘与 CPU 余波），
没有做静默环境控制。因此本报告的耗时**只用于量级比较**（重排比不重排慢 1～2 个数量级），
不作为延迟验收数据。

`run1` 与 `run2` 的原始产物都在 `p3-pilot-01/runs/` 下，`repeatability.json` 是逐条比对结果。

---

## 9. 限制与必须说明的偏差

1. **不是正式 Benchmark**：22 题、单一语料（3 份 PDF / 447 Chunk），样本量不足以支撑结论外推；
   1 道题的差别就能带来 ±0.045 的 Hit@10 波动。
2. **相关性是二元的**：Gold 只有 `retrieval_relevant_chunk_ids`，没有分级相关性，
   也没有"部分正确"的处理；B16/B21、B17–B20 共享同一页 Chunk，
   指标无法区分"命中同一页但不同行"。
3. **B14/B15 的完整证据口径**：metadata 已注明"完整证据需页 10 表头 + 续页正文，
   但检索目标只设正文块"。本轮用 `required_evidence_coverage@10` 做了补充观察，
   但没有把它并入主指标——这会高估这两题的"完整证据召回"。
4. **查询改写被刻意关闭**：生产链路会做意图识别与同义/语义扩展，本轮全部用原句，
   所以这里的绝对指标**低于**线上端到端表现，只适合做四组之间的相对比较。
5. **向量来自 pgvector 而非语料快照**：已用 ID 集合 + 正文 sha256 逐条验证等价，
   但索引时使用的 Embedding 版本无法从数据侧反证，只能依赖 `config/model.json` 记录。
6. **阈值是语义侧调过的**：`0.35` 的相对阈值对 BM25（归一化到 1.0）和语义（余弦）
   作用强度不同，这是 A 组被切掉 B03 的直接原因；四组沿用同一阈值保证了"条件相同"，
   但并不意味着这个阈值对每组都合理。
7. **构造 `PostgresVectorStore` 会执行幂等 DDL**（`CREATE TABLE/INDEX IF NOT EXISTS`），
   这是生产构造函数本身的行为，本轮未改动；对数据无写操作。
8. **未处理 B23/B27 审核人字段、未签核第三批**，按约束执行。

---

## 10. 距离正式 50 条 Gold Benchmark 的必要工作

按阻塞程度排序：

1. **补齐 28 条 Gold**：当前 22/50。B23 待澄清、B24 已拒收，需要 B28–B42 走完人工签核，
   并补足覆盖度缺口（现有 22 题集中在 3 份文档，题型以 exact_entity/semantic 为主）。
2. **先给 BM25 候选池定性（最高优先）**：当前 `priority`/`updated_at` 无区分度 +
   `ILIKE … OR` 命中全库，使 BM25 基线不可比。要么改成真正的全库 BM25（或 pg 全文索引），
   要么给 `priority`/`updated_at` 赋予语义并加 `LIMIT` 前的相关性排序。
   在这件事定案前，任何"BM25 vs 向量"的正式结论都不成立。
3. **相关性标注升级**：从"页级 Chunk + 三字段"升级到"行级/段落级 Chunk ID"，
   至少解决 B16–B21 共享同页导致的无法区分；同时给出分级相关性（0/1/2）以支持更稳的 NDCG。
4. **明确评测是否包含查询改写/意图路由**：本轮关闭；正式 Benchmark 需要二选一并固化，
   否则线上表现与离线指标不可比。
5. **评测入口收编**：把 `run_pilot.py` 的流程并入 `rag_app.cli evaluate-retrieval`
   （或新增子命令），统一报告 schema、门禁阈值与产物目录，避免一次性脚本分叉。
6. **重排模型重新选型**：当前 `mmarco-mMiniLMv2` 在中文长表格 Chunk 上排序变差且慢 20 倍；
   候选方向是中文/长文本重排模型、减小候选数、或只在低置信度时触发（生产已有
   `rerank_trigger=auto` 能力，本轮为可比性强制 `always`）。
7. **延迟测量独立化**：固定静默环境、固定 warmup、多次取中位数，当前数据只能看量级。
8. **指标口径固化**：把 `required_evidence_coverage@K` 与多相关 Chunk 规则写进正式口径，
   并补 NDCG 的分级增益版本，避免每次评测重新解释。

---

## 11. 本轮改动清单

新增（未修改任何既有生产文件）：

| 文件 | 作用 |
| --- | --- |
| `rag_app/operations/retrieval_metrics.py` | Chunk ID 级 Hit@K / MRR@K / NDCG@K / Recall@K / 覆盖率 / 分位数 |
| `tests/test_retrieval_metrics.py` | 上述指标的 26 项单元测试 |
| `p3-pilot-01/run_pilot.py` | 四组（+1 诊断组）评测运行器 |
| `p3-pilot-01/verify_repeatability.py` | 两次运行的逐条一致性比对 |
| `p3-pilot-01/analyze.py` | 候选池诊断 / 失败归因 / 生成表格 |
| `p3-pilot-01/build_gold_bundle.py` | 22 条 Gold 合并快照（只读拼接） |

未修改：22 条 Gold、3 份 PDF、447 个 Chunk、`vector_store.py`、`rerank.py`、`online.py`、
`evaluation.py`、`config/*.json`、`.env`。未执行 commit / push。
