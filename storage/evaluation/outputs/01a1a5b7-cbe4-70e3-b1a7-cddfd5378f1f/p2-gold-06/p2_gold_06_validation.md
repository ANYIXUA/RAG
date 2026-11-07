# P2-Gold-06 第二批 Gold 静态验收

生成于 2026-11-04T23:06:14+08:00，Gold 版本 `p2-gold-06-batch02-v1`，Git 基线 `7810bfb54d43a1e5ffb4b6428bd30c0b4b0161a5`（分支 `codex/eval-corpus-export-v1`，已跟踪工作区干净）。

## 摘要

第二批签核包共 15 条（B13–B27）。按人工签核字段逐条判定：13 条纳入 Gold，其中接受原题 3 条（B19、B25、B27）、接受修订 10 条；驳回 1 条（B24），生成独立审计记录；1 条不构成完整签核（B23，`human_decision` 为「保留测试」），既不纳入 Gold，也不按驳回归档。

| 项目 | 数量 |
| --- | ---: |
| 签核包记录 | 15 |
| 第二批 Gold | 13 |
| 　接受原题 | 3 |
| 　接受修订 | 10 |
| 驳回（独立审计） | 1 |
| 未签核（待澄清） | 1 |
| 累计 Gold（首批 9 + 第二批 13） | 22 |
| 距 50 条目标差额 | 28 |

本轮共执行 643 项静态断言，全部通过。未运行 Benchmark，未连接数据库或检索服务，未执行 Git commit/push。

## 签核读取与判定规则

- **只读取人工字段。** 每条记录的 `human_decision`、`human_reviewer`、`human_reviewed_at`、`human_comment` 必须全部非空，且 `human_decision` 必须属于「接受原题／接受修订／驳回」三种已定义取值，才进入判定。缺项或取值不在词表内的记录一律不纳入。
- **AI 建议不作为批准。** `review_recommendation` 只用于与签核包逐字比对（确认人工字段追加之前的 AI 内容未被改写），从不参与入库判定。B23 的 AI 建议是 Revise，但人工字段未给出合法决定，因此按未签核处理；B24 的驳回依据取自人工 `human_decision` 与 `human_comment`，AI 建议只作旁证。
- **接受原题**（B19、B25、B27）逐字采用签核包的 `original_question`、`original_answer` 与 `retrieval_relevant_chunk_ids`。三者与冻结候选的 `question`、`proposed_answer`、`supporting_chunk_ids` 逐字节一致，候选文件未被改写。
- **接受修订**（B13–B18、B20–B22、B26）逐字采用人工确认的 `revised_question`、`revised_answer`、`evidence_chunk_ids` 与 `retrieval_relevant_chunk_ids`，并与冻结的 P2-Gold-05 修订提案逐条相等。
- **驳回**（B24）只保留原题、原答案与两处审计证据，`retrieval_relevant_chunk_ids` 为空，不进入 Gold，也不分配 Gold ID。
- **未签核**（B23）单独落盘，保留 AI 推荐题答备查，但 `status=unsigned_pending_clarification`、`gold_case_id=null`。

签核包的 SHA-256 为 `5c9f5feaff9a281236d5ba680bf609c22c4a0c2f6355c349b3a0d10a3dd906a8`。P2-Gold-05 冻结记录中的签核前哈希为 `e7719369abd01d741e65b717aa4d61e965a92b1d50e51fe8fec2ef6150f313d0`；差异仅来自本轮之前追加的人工字段，因为包内 15 条 AI 字段已与冻结修订提案（`8811414d…`）逐条比对相等。

## 通过与未纳入

| 批次 | 人工决定 | 结果 | 变体 | 物理页 / 证据 Chunk | 检索目标 Chunk |
| --- | --- | --- | --- | --- | --- |
| B13 | 接受修订 | Gold | signed_revision | 10 / 0eb4bd6e18d599063371f51b | 0eb4bd6e18d599063371f51b |
| B14 | 接受修订 | Gold | signed_revision | 10 / 0eb4bd6e18d599063371f51b, 11 / e010fe39879d92fa21dc59d9 | e010fe39879d92fa21dc59d9 |
| B15 | 接受修订 | Gold | signed_revision | 10 / 0eb4bd6e18d599063371f51b, 12 / 1c317b1dd2cebfbf9647d03e | 1c317b1dd2cebfbf9647d03e |
| B16 | 接受修订 | Gold | signed_revision | 254 / 92108b5bb6dcc5b2227d531c | 92108b5bb6dcc5b2227d531c |
| B17 | 接受修订 | Gold | signed_revision | 255 / 03e5582a4a0f7d3c76a33e66 | 03e5582a4a0f7d3c76a33e66 |
| B18 | 接受修订 | Gold | signed_revision | 255 / 03e5582a4a0f7d3c76a33e66 | 03e5582a4a0f7d3c76a33e66 |
| B19 | 接受原题 | Gold | original | 255 / 03e5582a4a0f7d3c76a33e66 | 03e5582a4a0f7d3c76a33e66 |
| B20 | 接受修订 | Gold | signed_revision | 255 / 03e5582a4a0f7d3c76a33e66 | 03e5582a4a0f7d3c76a33e66 |
| B21 | 接受修订 | Gold | signed_revision | 254 / 92108b5bb6dcc5b2227d531c | 92108b5bb6dcc5b2227d531c |
| B22 | 接受修订 | Gold | signed_revision | 52 / 81951fb8b5e157346ed83d77 | 81951fb8b5e157346ed83d77 |
| B23 | 保留测试（非法取值） | 未签核，不纳入 | — | 52 / 81951fb8b5e157346ed83d77 | 未采用 |
| B24 | 驳回 | 独立审计，不纳入 Gold | — | 6 / 5ab56d780f65ff344900b1a2, 9 / 469978708f9fe4506fc1fa7f | 无 |
| B25 | 接受原题 | Gold | original | 286 / 611a9eb6554a2b482561c775, 141 / 4931f1a7b903ba2672bbb512 | 611a9eb6554a2b482561c775, 4931f1a7b903ba2672bbb512 |
| B26 | 接受修订 | Gold | signed_revision | 287 / a264a91966d85e2ec3b52e02 | a264a91966d85e2ec3b52e02 |
| B27 | 接受原题 | Gold | original | 288 / 95cb40813342a7e91c27e7d3 | 95cb40813342a7e91c27e7d3 |

B24 的驳回理由（签核包 `review_reason`）：原题已展开 OLT 的英文全称，中文释义可直接翻译，检索必要性低；改去英文全称仍属于常见缩写释义。两处证据分别来自职业技能标准物理页 6 与全光规范物理页 9。

B23 的未签核理由：`human_decision` 为「保留测试」，不属于三种已定义取值；`human_comment` 是待确认问题「鉴权方式和加密方式是同一个吗？」。该记录需要人工重新签核并明确决定后才可入库，本轮不自动批准。

## 静态检查结果

| 检查项 | 结果 | 验证依据 |
| --- | --- | --- |
| Gold ID 唯一且可重算 | 通过 | 13 个 ID 互不相同。每个 ID 由 `batch_id`、`parent_candidate_id`、`corpus_snapshot_id`、`review_decision`、`question`、`reference_answer`、`evidence_chunk_ids`、`retrieval_relevant_chunk_ids` 八个字段的规范化 JSON（UTF-8、`sort_keys`、紧凑分隔符）取 SHA-256，前缀 `gold-batch02-sha256:`。逐条从落盘元数据重算，13/13 相等；JSONL 的 `note` 与元数据 `gold_case_id` 逐行一致。配方见 [Manifest](gold_batch02_manifest.json#L1)。 |
| 父候选存在 | 通过 | 15 条记录的 `candidate_id` 全部能在冻结的 57 条候选中唯一命中，且候选的 `question`、`proposed_answer`、`supporting_chunk_ids` 与签核包原题字段逐字相等，状态均为 `pending_review`。13 条 Gold 对应 13 个不同父候选；Gold 与驳回集合的父候选不相交。 |
| 引用 Chunk 存在 | 通过 | Gold 证据共 16 个条目（签核 `evidence_chunk_ids` 15 个，另有 1 条等价证据），覆盖 10 个不同 Chunk；驳回审计 2 个 Chunk；合计 12 个不同 Chunk，全部存在于冻结快照的 447 个 Chunk 中。逐条核对了来源文档、物理页、页级节名与 Chunk 文本哈希。 |
| 评测 Schema 兼容 | 通过 | 直接调用 `rag_app.operations.evaluation.load_retrieval_eval_cases` 加载新 JSONL，13 条全部解析成功；`query` 非空，`expected` 为非空对象数组，每个目标三字段齐全，`note` 被接受。未启动评测。 |
| 与第一批 9 条不重复 | 通过 | 规范化（NFKC + casefold + 仅保留字母数字）后与首批 9 条比较，无完全相同题面；最高相似度 0.6486（B21 对首批 B02，同一测试价格表的不同编码行），其余均低。跨批共享目标 Chunk 仅 `92108b5bb6dcc5b2227d531c`（首批 B02 与 B16、B21），已在逐条元数据中记录区分依据。 |
| B20/B21 与已有题目的区别有明确记录 | 通过 | 见下节，逐题写明比较对象、所查事实与区分依据，并写入 `distinctness_from_existing` 与 `scoring_limit`。 |
| 多证据题目的评分限制得到披露 | 通过 | B14、B15、B25 三条已披露，见「多证据与评分口径」；Manifest 的 `known_scoring_limits` 汇总同一口径。 |
| 目标唯一性（静态重放） | 通过 | 对 14 个检索目标各扫描全部 447 个 Chunk，按 `_matches_target` 的同一判定（source 相等、section_title 相等、text_contains 为子串）重放 6,258 次比对；每个目标只命中其绑定 Chunk，0 次同文档误命中，0 次跨文档误命中。 |
| 答案与证据的一致性信号 | 通过 | 13 条答案中的数字与拉丁实体全部出现在证据文本内（B18 519.84、B20 271.78、B21 62.02 等）。最长公共子串诊断 13 条均达到设定阈值；其中 B22 为改写答案（LCS 10 字，比率 0.37），其语义支撑来自 P2-Gold-05 原件核验与人工签核，本轮不重复做语义判定。 |
| 文件冻结与只读边界 | 通过 | 修订提案、两版工作簿、候选 JSONL、语料清单、语料 JSONL、首批 Gold JSONL、首批元数据、首批驳回 JSONL、首批 Manifest、P2-Gold-05 验收报告共 11 份输入的字节哈希与冻结记录逐一相等。首批 Gold 文件字节未变。本轮未连接数据库、未调用检索服务、未修改检索代码。 |
| 工作簿映射 | 通过 | `review.xlsx` 第 17–31 行的 B 列候选 ID 与 B13–B27 逐行对应。草稿工作簿同范围记录的 G 列仍为模板占位 `human`，说明人工字段只写在签核包 Markdown 中，两版工作簿均未被改写。 |

## 多证据与评分口径

- **B14、B15（需两块，但只设一个检索目标）。** 完整证据由页 10 表头（`0eb4bd6e…`，初级／中级／高级列序）与续页正文（页 11 `e010fe39…`／页 12 `1c317b1d…`）共同构成。`evidence_chunk_ids` 两块齐全，但 `retrieval_relevant_chunk_ids` 只放直接作答的正文块。因此现有 Hit@K/MRR 只能证明正文被找到，不能证明等级列归属；是否「同一返回集合同时含两块」需要独立断言，当前实现不提供该指标。
- **B25（两块等价证据，OR）。** 页 286 表 10.3.3.29 工作内容列与页 141 的 WH23123 行各自独立、完整支持四项答案，两个目标任一命中即可计 Hit，指标不要求同一 Top-K 同时含两页。签核 `evidence_chunk_ids` 只列原引用页 286，第 141 页按签核的 `retrieval_relevant_chunk_ids` 补充为 `equivalent_evidence`，并在元数据中单列 `equivalent_evidence_chunk_ids` 与 `evidence_scope_note`。
- **同 Chunk 多题。** B16、B17、B18、B19、B20、B21 中，254 页由 B16、B21 共用，255 页由 B17、B18、B19、B20 共用。目标只能验证 Chunk 级命中，无法区分行或段落；同 Chunk 的题会得到高度相关的命中与排名，单次 Chunk 命中不能作为行级证据。
- **通用口径。** 目标内字段为 AND、目标之间为 OR；Hit@K 看首个命中、MRR 取首个匹配名次倒数；现有实现没有 NDCG、Chunk ID 直配和完整证据覆盖指标；`text_contains` 对空白与标点敏感；三字段组合的唯一性只在本冻结快照内成立。

## B20 与 B21 的查重结论

- **B20（室内防雷箱 WH23105001 综合单价 271.78 元）对 B17。** 同一表 10.3.3.5 的同一行，但所问属性不同：B17 问子项名称「室内防雷箱」，B20 问该行综合单价。事实不同，不构成重复。
- **B20 对 B18。** 同为价格题，但 B18 对应塔上行 WH23105003（519.84 元），B20 对应室内行 WH23105001（271.78 元），对象与答案不同。
- **B21（测试波分复用器 1:6 以下 WH23104004，62.02 元/个）对首批 B02。** 同测试大类、同综合单价列、同目标 Chunk，但 B02 查 WH23104003（1:2，29.18 元/个），B21 查 WH23104004（1:6 以下，62.02 元/个）；项目编码、分光比与金额三项均不同。
- **B21 对 B16。** 同 Chunk，但 B16 问安装子项的四项动作，B21 问测试子项单价。
- **B20 与首批题目的关系。** 《电信基础设施维护规程》物理页 255 属本批章节，首批 9 条均未覆盖该表；B20 与首批无同事实、无同问题。
- 需要披露的残留风险：B16、B21 与首批 B02 共享 254 页 Chunk，B17–B20 共享 255 页 Chunk，命中与排名会相关；该 Chunk 内另有同价行（如 WH23104001 室内安装亦为 62.02 元/个），仅凭 Chunk 命中无法区分，需在人工判读时按项目编码核对。

## 数据质量告警

1. **B27 的 `human_reviewer` 值为 `systemsystem`**（疑似重复输入）。该字段非空且决定、日期、备注齐全，故本轮按原值保留并入库，同时在元数据写入 `signoff_warnings`。建议在最终 50 条定稿前更正。
2. **人工字段只写在签核包 Markdown 中**，`review.xlsx` 与 `review_batch02_15_draft.xlsx` 的 G 列仍为模板占位 `human`。签核以 Markdown 为唯一依据，工作簿仅用于核验候选映射。
3. **B23 待重新签核。** 需要明确「接受原题／接受修订／驳回」之一，并回答「鉴权方式与加密方式是否同一」的问题。在补齐前不得计入 Gold。
4. **审核人标识 `system`** 为模板占位，需在定稿前映射真实审核人。B21 的人工备注含换行，已按原文保留。
5. **B22 的版本佐证依赖封面页（物理页 1）**，但封面不是 Chunk 证据，`evidence_chunk_ids` 只有第 52 页；版本信息由 `source_verification` 与冻结文档版本共同承载。

## 冻结标识与交付哈希

- 语料快照 `sha256:eedd1783956ca582c1cdfbbdad486fdf1554c7dab79681bba0675eec47089fce`，3 份文档、447 个 Chunk；语料 JSONL `5995ee6be2871ee7c553ce5fe2f3002a7938dbffedf0ec2b8fed28af8107f4d6`。
- 候选 JSONL `31df78af2c96afd25f9221034ab47bbd965f7cb1a5e182dc8c1560cc3f9cf120`（57 条，未改动）。
- 签核包 `5c9f5feaff9a281236d5ba680bf609c22c4a0c2f6355c349b3a0d10a3dd906a8`；修订提案 `8811414d2c6447662a0ab4cbad45d60524b475543003fc5af575c32fe3cc8dc2`。
- 首批 Gold `0ee8bbcd963f09c9b300209e8f1edcd93eb27ece1a077af877a37473568ec73a`；首批驳回 `3bbeec82efe9ad5fc646479056cf189985314fadb8f5670ea164e28869c1ed91`；首批 Manifest `f1384386520a69e48ef9038faf7a108a11fa5288a17a709282a7d68816398493`（均未改动）。

| 本批输出 | SHA-256 |
| --- | --- |
| [retrieval_gold_batch02_13.jsonl](retrieval_gold_batch02_13.jsonl) | `5bfc8df96edd9574954fdb70c874a1fae186b3f442f077dcf92b478f9d103db9` |
| [retrieval_gold_batch02_metadata.json](retrieval_gold_batch02_metadata.json) | `a12a31ab2f69c163b6053e66f503d4c28ce48d9322dcebaca9065a996d5211a3` |
| [rejected_batch02_1.jsonl](rejected_batch02_1.jsonl) | `aa0e784949e0d3ff535e57b510b8111fbbe6d869752292a613f80836409aff73` |
| [unsigned_batch02_1.jsonl](unsigned_batch02_1.jsonl) | `4cd8ddc233c9a3f54b10fca609f388bf616d7653665d8a9accc5e69ca04e1cee` |

其余输入的哈希与全部输出（含本报告与静态校验结果）的哈希见 [Manifest](gold_batch02_manifest.json#L1)；Manifest 为避免自引用不登记自身哈希，其字节哈希另存于 [gold_batch02_manifest.sha256](gold_batch02_manifest.sha256)。

## 累计与目标差额

第二批通过 13 条，驳回 1 条，未签核 1 条；首批已有 9 条 Gold，累计 22 条，距 50 条目标还差 28 条。剩余候选 B28–B57 共 30 条尚未初审：若 30 条全部入库，累计可达 52 条；达到 50 条要求其中至少 28 条通过，也就是最多只能有 2 条被驳回或未签核。B23 未计入这 22 条：若后续澄清后被接受，可再增加 1 条；若被驳回，则维持现状。

## 边界声明

本轮只读本地文件并只写入 `storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06/`。未修改第一批 Gold，未修改 57 条原始候选，未修改数据库，未修改检索或评测代码，未运行 Benchmark，未执行 Git commit/push，未自动批准任何未签核样本。现有评分器与原始 PDF 均未改动；表格行列与跨页归属沿用 P2-Gold-05 的原件核验记录。
