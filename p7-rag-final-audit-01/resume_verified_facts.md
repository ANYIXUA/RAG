# 可核验简历事实与使用边界

状态：AUDIT_PREPARED / HUMAN_REVIEW_PENDING。记录日期：2026-11-06（Asia/Shanghai）。本文件描述个人复现项目及指定实验，不是企业线上生产统计。

## 可以使用的事实

| 事实 | 数值与范围 | 证据 |
|---|---|---|
| 冻结知识语料 | 3份PDF、447个Chunk | `integrity_check.json`、`../storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl` |
| Gold方法 | 历史归档50条Gold，Development 22、Holdout 28；本轮不重新签核或改标签 | `../p4-gold-completion-01/signed-final-20261105-v1/signoff_archive_report.md`、`human_signoff_receipt_46.jsonl`、`development_22_role_manifest.json`（后两文件同目录） |
| 正式检索结果 | 28条Gold Holdout上BM25/Vector/Hybrid/Hybrid+Rerank MRR@10分别0.826531/0.863095/0.898810/0.734906 | `../p5-benchmark-01/report.md`、`runs/run1/rankings.jsonl`（P5目录下） |
| 相对变化 | Hybrid相对BM25 +8.74%、相对Vector +4.14%；Cross-Encoder相对Hybrid -18.24% | `../p5-benchmark-01/deltas.json`；相对百分比不是百分点 |
| 真实E2E执行 | qwen-flash完成500/500；表示非空真实响应与Trace存在，非回答正确率 | `execution_response_checks.json`、`integrity_check.json` |
| 自动评估覆盖 | 490/500；含复用已付费响应恢复的8条 | `metrics_recalculation.json`、`score_failure_analysis.md` |
| Silver自动满分比例 | 423/439=96.36%；排除50条unanswerable、0473、10条最终评分失败；不是人工准确率 | `metrics_definition.md`、`metrics_recalculation.json` |
| 指定实验延迟 | 平均2.236秒、p50 2.205秒、p95 2.879秒；检索平均0.787秒，生成平均1.408秒 | P6 `measurement_protocol.json`、`runtime_environment.json`、P7 `metrics_recalculation.json` |
| 负结果与质量闭环 | 保留重排负收益，准备94条去重人工审核材料，人工签核尚未完成 | `review_selection.json`、`human_signoff_template.csv` |

P5正式数值为历史固定结果。本轮读取、核验和归档，没有重新执行P5或使用Holdout选择配置。Gold签核事实沿用历史归档及回执，本轮没有新增人类签核。评分Judge和回答生成同为qwen-flash，模型别名不能证明不可变权重版本。

## 简历精简版（100–150字）

个人复现RAG项目，冻结3份PDF、447个Chunk，构建50条Gold并以28条Holdout对比检索，Hybrid的MRR@10为0.8988，较BM25提升8.74%。使用qwen-flash完成500条Silver端到端请求，归档负收益与异常证据，建立待人工签核的质量审计流程。

正文按Unicode字符计数（含数字、标点、英文字母），不含标题；精确长度见 `static_validation.json`。精简版省略自动正确比例，面试时可按上表完整说明96.36%的分母与限制。

## 必须停用或等待人工审核的说法

- 旧简历“MRR 0.51→0.69”未获得复现支持，不能继续使用，也不能把本次其他数值解释成已复现旧提升。
- “准确率96.36%”必须改成“在439条适用Silver样本上的自动满分比例96.36%”；没有人工验证正确率。
- “500条全部正确”不成立；500/500只代表请求执行完成。
- “拒答正确率75%”不成立；27/36仅是50条未确认unanswerable中获得非空分的暂定自动拒答满分比例。
- “幻觉率3.67%”“引用正确率99.39%”均不能省略自动/结构性口径：18/490是疑似标记；2590/2606是引用编号出现次数有效比例，不是语义正确率。
- 不得把延迟写成通用SLA、企业线上p95、压力测试结果或任意模型的性能保证。
- 人工验证准确率、真实不可回答比例、人工确认幻觉率、人工语义引用正确率均等待逐题裁决；本次定向抽查94条也不能无权重外推500条总体准确率。

## 延迟适用环境

P6独立qwen-flash运行，Windows 11、本地PostgreSQL/pgvector与Redis、并发3、top_k=4、candidate_k=20、Hybrid权重0.7/0.3、Cross-Encoder关闭、输出上限220 token。墙钟从已初始化processor后的单题请求计时，包含保存响应及日志等开销；检索与生成是Trace阶段耗时，二者相加不必等于整题墙钟。全部500题最终尝试进入延迟分母，分位数线性插值。未测吞吐上限、冷启动或不同网络条件，不能外推。

## 可讨论的改进方向（本轮未实施）

先解决表格行列/单位和标注证据歧义，再考虑逐事实引用校验、Judge空值适用性与业务案例特例隔离、实际prompt证据覆盖观测、明确无答案标签的语料边界。Cross-Encoder研究应在Development上做独立设计并另设未来测试集，不以现有Holdout反馈调参。上述是工程待办，不声称已带来任何指标提升。
