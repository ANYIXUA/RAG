# 人工签核归档与最终划分

2026-11-05（Asia/Shanghai）。本版完成内容签核归档，未运行正式Benchmark。

| 项目 | 数量 |
| --- | ---: |
| 保留原文件的Development | 22 |
| 新签核并冻结的Holdout | 28 |
| 本版评测内容总数 | 50 |
| 其他已填写决定但未纳入本版 | 18 |
| 其中无修订稿待澄清 | 2 |

28条Holdout中18条接受原题、10条接受修订。覆盖3份PDF、27个独立Chunk，与Development相关/证据Chunk并集交集为0；文档题数为{"智慧家庭装维工程与管理职业技能等级标准.pdf": 6, "电信基础设施维护规程.pdf": 12, "中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf": 10}。主选名单与原28条建议完全一致，没有利用Pilot排名或评测结果替换题目。

## 签核证据

原工作簿46条决定均有填写：接受原题26、接受修订20。人工已在本次对话确认审核标识`system`及固定签核日期`2026-11-05`，归档元数据采用该确认；原表的`=NOW()`公式和缓存值完整保留在audit副本中，不把动态公式当成固定签署时刻。

原工作簿的状态公式把`system`视为待补身份，因此缓存状态仍可能为“需补身份日期”。本版依据人工明确确认归档，不改写原表公式或人填字段。

本版仅导出28条主选。B31/B39虽填“接受修订”，但原包无修订题答，先保留待澄清，不把占位日期或不完整比较批准入集。其余16条只记录原始决定及角色原因，不追加到本版Development，也不自动混入Holdout。

## 原候选与新提案

B32、B33、B35改变检索目标，标为`new_proposal_retargeted`：保留原candidate_id、原题答、原证据、独立proposal_id及新gold_case_id。另7条修订也有独立Gold身份，未覆盖原候选或既有22条Gold。逐题见[candidate_proposal_gold_lineage.json](candidate_proposal_gold_lineage.json)。

## 冻结内容与边界

- 检索输入：[28条Holdout JSONL](retrieval_gold_holdout_28.jsonl)。与既有loader的query/expected/note格式兼容。
- 标准答案、人工签核、来源物理页、证据/相关ID与版本：[sidecar](retrieval_gold_holdout_metadata.json)。
- [Development角色清单](development_22_role_manifest.json)引用原22条文件；不将50条合并成“50条未见测试”。正式留出指标分母为28。
- expected的source/section_title/text_contains只用于旧入口兼容，相关ID集合是正式检索相关标签；生成答案评分须使用sidecar完整标准答案，不能靠短语命中代替完整性评分。
- 内容冻结不等于执行已就绪。正式执行前仍须确认四组配置/模型版本、数据库与快照等价、延迟与失败口径和运行授权；见[执行前门槛](benchmark_preflight_pending.md)。
- Holdout不得用于后续调参，原始语料和既有Gold不变。当前没有任何Holdout检索结果、模型回答或指标。

源工作簿SHA-256：`69209e555b9e70f396ce93551d48257b914eb8544bf3f9215bf77906ea0cae20`。文件级冻结哈希见[freeze_manifest.json](freeze_manifest.json)。该清单是内容版本归档，不宣称文件系统具有WORM写保护。
