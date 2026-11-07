# P7逐题证据索引

状态：AUDIT_PREPARED / HUMAN_REVIEW_PENDING。

历史40条原清单已找到；任务指定集合去重后82条。为完整覆盖18条疑似幻觉、7条检索代理异常、1条上下文异常、20条评分不可靠与多条件非满分/失败案例，扩展后共94条待人工裁决。

每张卡片含原题、Silver参考或预期拒答、实际回答、全部返回来源编号及Chunk/文档/PDF物理页/完整正文、实际引用、原始评分与理由、AI建议、空白人工结论/备注/审核人/日期/签名；同名JSON还保存实际LLM请求与冻结参考全文。

人工签核唯一登记入口为 human_signoff_template.csv。多处空白模板仅为阅读便利，正式审核后应指定一个版本为准。

| case_id | 题型 | 纳入原因 |
|---|---|---|
| [p6s-0023](cases/p6s-0023.md) | exact_fact | historical_spot_check_40, score_failure, judge_unreliable |
| [p6s-0024](cases/p6s-0024.md) | exact_fact | historical_spot_check_40 |
| [p6s-0036](cases/p6s-0036.md) | exact_fact | historical_spot_check_40, hallucination_suspected |
| [p6s-0037](cases/p6s-0037.md) | exact_fact | historical_spot_check_40, score_failure, invalid_citation, judge_unreliable |
| [p6s-0041](cases/p6s-0041.md) | exact_fact | historical_spot_check_40, score_failure, judge_unreliable |
| [p6s-0053](cases/p6s-0053.md) | exact_fact | historical_spot_check_40, score_failure, judge_unreliable |
| [p6s-0087](cases/p6s-0087.md) | procedure | historical_spot_check_40 |
| [p6s-0088](cases/p6s-0088.md) | multi_condition | historical_spot_check_40, invalid_citation |
| [p6s-0089](cases/p6s-0089.md) | multi_condition | historical_spot_check_40, hallucination_suspected, context_evidence_miss, multi_condition_nonfull_or_unscored |
| [p6s-0090](cases/p6s-0090.md) | exact_fact | historical_spot_check_40, hallucination_suspected |
| [p6s-0102](cases/p6s-0102.md) | procedure | historical_spot_check_40 |
| [p6s-0138](cases/p6s-0138.md) | multi_condition | historical_spot_check_40, multi_condition_nonfull_or_unscored |
| [p6s-0146](cases/p6s-0146.md) | exact_fact | hallucination_suspected |
| [p6s-0151](cases/p6s-0151.md) | multi_condition | hallucination_suspected, retrieval_evidence_miss, multi_condition_nonfull_or_unscored |
| [p6s-0157](cases/p6s-0157.md) | multi_condition | historical_spot_check_40, score_failure, judge_unreliable, multi_condition_nonfull_or_unscored |
| [p6s-0177](cases/p6s-0177.md) | procedure | historical_spot_check_40 |
| [p6s-0180](cases/p6s-0180.md) | multi_condition | multi_condition_nonfull_or_unscored |
| [p6s-0192](cases/p6s-0192.md) | multi_condition | multi_condition_nonfull_or_unscored |
| [p6s-0194](cases/p6s-0194.md) | procedure | historical_spot_check_40, hallucination_suspected |
| [p6s-0195](cases/p6s-0195.md) | multi_condition | historical_spot_check_40, score_failure, judge_unreliable, multi_condition_nonfull_or_unscored |
| [p6s-0222](cases/p6s-0222.md) | procedure | historical_spot_check_40, retrieval_evidence_miss |
| [p6s-0230](cases/p6s-0230.md) | multi_condition | historical_spot_check_40, score_failure, judge_unreliable, multi_condition_nonfull_or_unscored |
| [p6s-0236](cases/p6s-0236.md) | unanswerable | historical_spot_check_40, unanswerable, judge_unreliable |
| [p6s-0237](cases/p6s-0237.md) | unanswerable | historical_spot_check_40, unanswerable, invalid_citation, judge_unreliable |
| [p6s-0238](cases/p6s-0238.md) | colloquial | historical_spot_check_40 |
| [p6s-0239](cases/p6s-0239.md) | colloquial | historical_spot_check_40 |
| [p6s-0243](cases/p6s-0243.md) | unanswerable | historical_spot_check_40, unanswerable, invalid_citation, judge_unreliable |
| [p6s-0244](cases/p6s-0244.md) | unanswerable | unanswerable |
| [p6s-0245](cases/p6s-0245.md) | colloquial | historical_spot_check_40 |
| [p6s-0246](cases/p6s-0246.md) | colloquial | historical_spot_check_40 |
| [p6s-0247](cases/p6s-0247.md) | colloquial | historical_spot_check_40, invalid_citation |
| [p6s-0255](cases/p6s-0255.md) | unanswerable | historical_spot_check_40, unanswerable, judge_unreliable |
| [p6s-0256](cases/p6s-0256.md) | unanswerable | historical_spot_check_40, unanswerable, judge_unreliable |
| [p6s-0264](cases/p6s-0264.md) | unanswerable | unanswerable |
| [p6s-0265](cases/p6s-0265.md) | unanswerable | historical_spot_check_40, unanswerable, hallucination_suspected, judge_unreliable |
| [p6s-0266](cases/p6s-0266.md) | unanswerable | historical_spot_check_40, unanswerable, judge_unreliable |
| [p6s-0273](cases/p6s-0273.md) | colloquial | historical_spot_check_40, hallucination_suspected, retrieval_evidence_miss |
| [p6s-0276](cases/p6s-0276.md) | procedure | historical_spot_check_40, hallucination_suspected |
| [p6s-0277](cases/p6s-0277.md) | unanswerable | historical_spot_check_40, unanswerable |
| [p6s-0278](cases/p6s-0278.md) | unanswerable | unanswerable |
| [p6s-0279](cases/p6s-0279.md) | unanswerable | unanswerable |
| [p6s-0288](cases/p6s-0288.md) | exact_fact | hallucination_suspected |
| [p6s-0291](cases/p6s-0291.md) | unanswerable | unanswerable |
| [p6s-0292](cases/p6s-0292.md) | unanswerable | unanswerable |
| [p6s-0293](cases/p6s-0293.md) | unanswerable | unanswerable |
| [p6s-0310](cases/p6s-0310.md) | unanswerable | unanswerable, invalid_citation, hallucination_suspected |
| [p6s-0311](cases/p6s-0311.md) | unanswerable | unanswerable |
| [p6s-0312](cases/p6s-0312.md) | unanswerable | unanswerable, hallucination_suspected |
| [p6s-0313](cases/p6s-0313.md) | multi_condition | hallucination_suspected, retrieval_evidence_miss, multi_condition_nonfull_or_unscored |
| [p6s-0318](cases/p6s-0318.md) | multi_condition | multi_condition_nonfull_or_unscored |
| [p6s-0321](cases/p6s-0321.md) | exact_fact | hallucination_suspected |
| [p6s-0324](cases/p6s-0324.md) | unanswerable | unanswerable |
| [p6s-0325](cases/p6s-0325.md) | unanswerable | unanswerable |
| [p6s-0331](cases/p6s-0331.md) | multi_condition | hallucination_suspected, retrieval_evidence_miss, multi_condition_nonfull_or_unscored |
| [p6s-0333](cases/p6s-0333.md) | colloquial | historical_spot_check_40 |
| [p6s-0338](cases/p6s-0338.md) | unanswerable | unanswerable |
| [p6s-0339](cases/p6s-0339.md) | unanswerable | unanswerable |
| [p6s-0340](cases/p6s-0340.md) | unanswerable | unanswerable |
| [p6s-0348](cases/p6s-0348.md) | unanswerable | unanswerable |
| [p6s-0349](cases/p6s-0349.md) | unanswerable | unanswerable |
| [p6s-0360](cases/p6s-0360.md) | multi_condition | multi_condition_nonfull_or_unscored |
| [p6s-0362](cases/p6s-0362.md) | multi_condition | hallucination_suspected, retrieval_evidence_miss, multi_condition_nonfull_or_unscored |
| [p6s-0363](cases/p6s-0363.md) | multi_condition | hallucination_suspected, retrieval_evidence_miss, multi_condition_nonfull_or_unscored |
| [p6s-0364](cases/p6s-0364.md) | unanswerable | unanswerable, judge_unreliable |
| [p6s-0365](cases/p6s-0365.md) | unanswerable | unanswerable |
| [p6s-0372](cases/p6s-0372.md) | procedure | historical_spot_check_40 |
| [p6s-0379](cases/p6s-0379.md) | unanswerable | unanswerable |
| [p6s-0380](cases/p6s-0380.md) | unanswerable | unanswerable |
| [p6s-0381](cases/p6s-0381.md) | unanswerable | unanswerable |
| [p6s-0387](cases/p6s-0387.md) | procedure | historical_spot_check_40 |
| [p6s-0389](cases/p6s-0389.md) | colloquial | historical_spot_check_40, score_failure, judge_unreliable |
| [p6s-0393](cases/p6s-0393.md) | unanswerable | unanswerable |
| [p6s-0394](cases/p6s-0394.md) | unanswerable | unanswerable |
| [p6s-0407](cases/p6s-0407.md) | unanswerable | unanswerable |
| [p6s-0408](cases/p6s-0408.md) | unanswerable | unanswerable |
| [p6s-0409](cases/p6s-0409.md) | unanswerable | unanswerable |
| [p6s-0418](cases/p6s-0418.md) | unanswerable | unanswerable |
| [p6s-0420](cases/p6s-0420.md) | multi_condition | historical_spot_check_40, score_failure, judge_unreliable, multi_condition_nonfull_or_unscored |
| [p6s-0434](cases/p6s-0434.md) | unanswerable | unanswerable, hallucination_suspected |
| [p6s-0435](cases/p6s-0435.md) | unanswerable | unanswerable |
| [p6s-0447](cases/p6s-0447.md) | unanswerable | unanswerable |
| [p6s-0448](cases/p6s-0448.md) | unanswerable | unanswerable |
| [p6s-0454](cases/p6s-0454.md) | multi_condition | historical_spot_check_40, score_failure, judge_unreliable, multi_condition_nonfull_or_unscored |
| [p6s-0458](cases/p6s-0458.md) | unanswerable | unanswerable, judge_unreliable |
| [p6s-0473](cases/p6s-0473.md) | exact_fact | historical_spot_check_40, p6s_0473, judge_unreliable |
| [p6s-0478](cases/p6s-0478.md) | unanswerable | unanswerable |
| [p6s-0480](cases/p6s-0480.md) | unanswerable | unanswerable |
| [p6s-0483](cases/p6s-0483.md) | unanswerable | unanswerable |
| [p6s-0484](cases/p6s-0484.md) | unanswerable | unanswerable |
| [p6s-0486](cases/p6s-0486.md) | unanswerable | unanswerable |
| [p6s-0487](cases/p6s-0487.md) | unanswerable | unanswerable |
| [p6s-0488](cases/p6s-0488.md) | unanswerable | unanswerable |
| [p6s-0496](cases/p6s-0496.md) | unanswerable | unanswerable |
| [p6s-0499](cases/p6s-0499.md) | unanswerable | unanswerable |
