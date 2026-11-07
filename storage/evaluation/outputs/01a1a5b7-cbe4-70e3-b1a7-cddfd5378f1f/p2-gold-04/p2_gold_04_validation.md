# P2-Gold-04 首批 Gold 静态验收

生成于 2026-11-04T21:58:42+08:00，Gold 版本 p2-gold-04-batch01-v1，基线 7810bfb54d43a1e5ffb4b6428bd30c0b4b0161a5。

## 签核与来源

签核包的 human_decision 是用户确认由本人填写的最终决定。12 条决定与本阶段预期逐条一致。保留 12 条原始 human_reviewer 值 system、日期和备注。两份工作簿用于核验候选映射、原题和原引用，其中 pending_review、human 及草稿意见属于此前流程。草稿仍有早期措辞或备选题面。最终修订题答逐字取自签核包，并与 P2-Gold-03 修订方案的最终记录逐条相等。签核包页首说明沿用签核前模板，逐条人工字段已填写。

| 实际读取文件 | SHA-256 |
| --- | --- |
| [p2_gold_03_signoff_packet.md](../p2_gold_03_signoff_packet.md) | 62c3e0e0ec30beea57b8fa43d0a2bb9e298687571ed85d815d02b221afcef6fc |
| [review.xlsx](../review.xlsx) | df13e2755786cfb7f4d30e44d6323463ce6cbfe49c99a2b5ae87dfeec369d5ea |
| [review_p2_gold_03_draft.xlsx](../review_p2_gold_03_draft.xlsx) | 359a12bb9923326b7dc738eb5575411ec55cca25946751c98aab6a72b40211a0 |
| [p2_gold_03_revision_proposal.md](../p2_gold_03_revision_proposal.md) | 766e882d9065020376fa4383d1b89ec25b00e1e35be89c24eb8d17f537b26b94 |
| [p2_gold_02_review_proposal.md](../p2_gold_02_review_proposal.md) | cb22b75e2cead9e1595a2c1271e77fc08721db57a76772afa81e4691bbfbb3fa |
| [first-batch-evidence.md](../first-batch-evidence.md) | 0a55423f56f8313343d022ba0e2b7a34d9d714877e6146621d02c2813331b111 |
| [review-index.md](../review-index.md) | b2b99c19365768ecec88933197e57ce4db589f2ffa9f2923a0fba125f2e06bd3 |

冻结语料 sha256:eedd1783956ca582c1cdfbbdad486fdf1554c7dab79681bba0675eec47089fce，包含 3 份文档、447 个 Chunk。现有语料验证器复算了清单及数据哈希、快照身份、范围和记录一致性。候选生成清单绑定同一快照及清单内部哈希。57 条候选 ID 均可复算，所有原始引文均位于对应 Chunk。候选、语料、工作簿、Markdown 签核资料及 PDF 的文件哈希在导出前后复核一致。完整哈希见 [冻结清单](gold_batch01_manifest.json)。

三个本地 PDF 的字节哈希与 P2-Gold-02 原件核验记录一致。冻结文档版本从解析文本哈希派生，PDF 字节哈希独立保存。本轮核对冻结 Chunk、页码、文本及来源版本，表格行列和跨页归属沿用签核包记录的原件核验。

## 通过与驳回

| 批次编号 | 决定 | 快照文档版本 | 物理页 / 签核证据 Chunk | 检索目标 Chunk |
| --- | --- | --- | --- | --- |
| B01 | 接受修订 | v_8ae9b63d869002c1 | 29 / 831af7c41fd776db6b5b3ff9 | 831af7c41fd776db6b5b3ff9 |
| B02 | 接受修订 | v_8ae9b63d869002c1 | 254 / 92108b5bb6dcc5b2227d531c | 92108b5bb6dcc5b2227d531c |
| B03 | 接受原题 | v_ab72ce00c904f060 | 1 / 4f32247f7a6d7526df77bddd | 4f32247f7a6d7526df77bddd |
| B04 | 接受修订 | v_dcf78195a87f01f4 | 19 / 02c18b66c8c7d17fa1fb910e | 02c18b66c8c7d17fa1fb910e |
| B05 | 接受原题 | v_ab72ce00c904f060 | 25 / 4812f97659f77c46891223fa | 4812f97659f77c46891223fa |
| B06 | 接受修订 | v_dcf78195a87f01f4 | 6 / 5ab56d780f65ff344900b1a2 | 5ab56d780f65ff344900b1a2 |
| B07 | 接受修订 | v_ab72ce00c904f060 | 61 / c120df3a569ae215d69183ac, 62 / 38ea5e749604f43f5f040901 | 38ea5e749604f43f5f040901 |
| B09 | 接受修订 | v_ab72ce00c904f060 | 58 / 9b5d9b92dc528a1c594e3ec2 | 9b5d9b92dc528a1c594e3ec2 |
| B12 | 接受修订 | v_dcf78195a87f01f4 | 16 / 48ecc091e26caaa3ccbd3be5, 18 / c10a8b3b89210595f9880fc6 | 48ecc091e26caaa3ccbd3be5, c10a8b3b89210595f9880fc6 |

7 条修订逐字采用最终签核题答，2 条原题逐字采用原候选题答。9 条题答非空，Gold ID 唯一且可复算。评测 JSONL 的 note 对应元数据中的 gold_case_id，计算规则见冻结清单。12 条记录可定位到 12 个不同父候选。Gold 与驳回集合不相交。

| 批次编号 | 原始候选 ID | 驳回理由（签核包 review_reason） |
| --- | --- | --- |
| B08 | sha256:d5ab4e3c5473589238491da686184e9c651ecdbf317776b9454bc222b49ff81a | 市内街道行与房屋建筑物的屋脊备注被拼接。1.5 m 属于房屋平顶，屋脊对应 0.6 m。若人工决定重出题，先选定一个有效场景。 |
| B10 | sha256:b503d526e513f66d71916de151812a19403e51bbfd81956c88dee63adda7814a | 题面合并了两个独立作业子项。0.69 工日只属于抗震架子项。 |
| B11 | sha256:de1dd6ecf011fd92f5cbef969545f045b067fbc353123e327f2b8ce04527a0d3 | 题面问两项单价，答案只给一个值，且控制设备分类无唯一总单价。若人工决定重出题，先查重 WH23121002 和 WH23121004。 |

## 评测器兼容性

- 现有 evaluate-retrieval 的 --dataset 参数解析成功，其入口使用的 load_retrieval_eval_cases 加载全部 9 条。CLI 加载后会启动评测，本次仅调用同一参数解析器及数据加载器。
- 当前 JSONL 需要非空 query 和有效目标。expected 接受非空对象数组，单目标至少配置 source、section_title、text_contains 之一。源码还支持 expected_source 等简写，以及 note、intent_label、business_module、source_type、tags 等选填字段。答案、签核与证据角色单列于元数据。
- 10 个目标都配置文档、页级 section 和证据原文子串。实际 _matches_target 扫描全部 447 个 Chunk，共 4470 次比对，每个目标唯一命中其绑定 Chunk，其中 1058 次同文档非目标比对均未误匹配。另用 _first_match_rank 执行 4,023 次单 Chunk 样本判定，结果与逐题目标集一致。
- 11 个 Gold 签核证据和 4 个驳回引用均能定位。已核验物理页、来源文件、文档 ID、版本及原始证据包中的 Chunk 哈希。B07 新增的归属 Chunk 由 P2-Gold-03 修订记录和冻结记录共同绑定。
- 目标内字段是 AND，多个目标是 OR。Hit@K 取返回来源列表中是否出现任一匹配，MRR 平均首个匹配名次的倒数，未命中贡献 0。当前实现没有 NDCG、Chunk ID 直配和完整证据覆盖指标。单独用 source 会误把同文档其他 Chunk 判为相关。三字段组合的唯一性验证限于当前冻结快照，原文匹配对空白和标点敏感。
- 本轮静态验收使用本地文件和现有评测匹配器。未运行正式 Benchmark，未调用检索服务、数据库或 LLM。生产代码未改动。

## 多证据样本

- **B07** 第 61 页证明二维码属于光路由终端，第 62 页提供尺寸。两块均保留为签核证据，检索目标只有第 62 页。第 61 页单独出现时无命中，第 62 页紧随其后时首命中排名为 2。
- **B12** 第 16 页支持初级 3.2.2 的无线局域网相关基础知识，第 18 页支持中级 3.2.3 的无线局域网网优及软件基础知识。单页命中均计现有 Hit，两页不会交叉命中另一角色。只有同一 Top-K 同时含两块才算完整覆盖。元数据记录 requires_all_evidence=true 和 required_evidence_count=2，完整覆盖以独立静态断言验证。

## 待确认与适用范围

当前导出没有待确认的阻塞项。审核人标识 system 可由用户在后续补充身份映射。语料版本、切分或元数据变化时需复验目标匹配。本次交付为首批 9 条，最终 50 条评测集仍待后续阶段。如果样本将用于开发调参，需要记录用途并在最终报告披露。
