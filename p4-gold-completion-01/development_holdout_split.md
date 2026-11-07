# Development / Holdout划分方案

## 角色

- Development：现有22条，源JSONL和metadata字节不变，清单见development_manifest.json。所有P3指标仅归此组。
- Holdout拟主选：holdout_proposed_28.jsonl中的28条，状态pending_human_review、is_frozen_holdout=false，不是正式Gold或运行输入。
- 备选：5条无Development证据块交集的题，可在评测前依人工裁决替换。8条共享Development证据块的候选默认作Development扩充备选。
- B38与B40/B41不能重复计入独立覆盖；B45/B46若替换B42，要重新评估数量、事实和证据簇覆盖。

## 冻结前程序（待人工确认后另行执行）

1. 按candidate_id、proposal_id、review_record_sha256收集有效人工决定及身份、日期。修订未被接受、被驳回或有争议的题不导出。
2. 再核对标准答案要点、否定/例外、单位、PDF物理页与Chunk一致性；B34铁路交越列、B35跨页表范围及所有Revise项重点复核。
3. 如主选不足28，可用备选替换；如果仍不足，接受较小Holdout或继续补题，禁止将Development改标或拆分同一事实凑数。
4. 对最终题目、答案、expected、relevant/evidence IDs、requires_all_evidence、语料快照、审核记录和人工签核生成不可变版本及SHA-256清单。预先固定检索与答案评分口径、配置、模型版本和报告模板。
5. 固定最终Holdout名单后再授权运行；后续调参只用Development。不得拿Holdout召回、逐题失败、候选排序、重排分数或答案反馈作参数/提示词选择。
6. 若已查看Holdout结果并据此改系统，该版本转入Development/诊断记录，需另建未用于调参的留出题，不能继续称同一Holdout为未见测试。

## 报告口径

22+28=50仅是内容总量目标，不是50条独立未见测试。Development与Holdout分别报告分母、指标和置信/抽样局限。Holdout的28条是目的性覆盖样本，不能称为生产分布无偏估计；共用证据页的题按证据簇额外披露。

本轮没有导出新Gold、冻结Holdout或运行评测。proposal文件的SHA-256用于审核版本完整性，不代表完成评测冻结。
