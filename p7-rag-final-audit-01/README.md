# P7 Silver E2E质量审计与实验归档

状态：**AUDIT_PREPARED / HUMAN_REVIEW_PENDING**。日期：2026-11-06（Asia/Shanghai）。

本目录只读消费历史P1/P4/P5/P6证据，保留原500条Silver及P5/P6结果。没有运行新模型请求、重做检索实验、调整参数、修改生产代码或commit/push。P7新增脚本仅用于本地证据提取、统计和静态验收。

先读 [最终报告](P7_FINAL_REPORT.md)，再从 [94条逐题索引](audit_case_evidence.md) 打开证据卡；人工结论统一填入 [签核模板](human_signoff_template.csv)。当前所有人工字段为空。

## 交付导航

| 文件 | 用途 |
|---|---|
| [integrity_check.json](integrity_check.json) | 500条、题型、唯一ID、指定哈希、原始响应与配置核验 |
| [audit_case_inventory.csv](audit_case_inventory.csv) | 全部500条库存，标记94条待审及纳入原因 |
| [audit_case_evidence.md](audit_case_evidence.md) | 94张证据卡索引；每张卡都有完整问题/参考/回答/来源/评分/AI建议/空白人工字段 |
| [unanswerable_review_packet.md](unanswerable_review_packet.md) | 全部50条无答案标签候选的全文词面扫描与候选证据核对 |
| [citation_audit.md](citation_audit.md) | 6条整数引用编号越界与来源语义审查 |
| [score_failure_analysis.md](score_failure_analysis.md) | 10条最终评分失败逐attempt归因 |
| [metrics_recalculation.json](metrics_recalculation.json) | 独立复算、分子/分母case_id与重叠集合 |
| [metrics_definition.md](metrics_definition.md) | 统计定义、排除规则、历史40抽查规则及限制 |
| [human_signoff_template.csv](human_signoff_template.csv) | 94条人工裁决登记模板，UTF-8 BOM；结论/备注/审核人/日期/签名为空 |
| [resume_verified_facts.md](resume_verified_facts.md) | 144字简历正文、可用数值与禁用说法 |
| [interview_materials.md](interview_materials.md) | 3分钟介绍、30分钟提纲与10组问答 |
| [P7_FINAL_REPORT.md](P7_FINAL_REPORT.md) | 本轮结论与结束条件 |

补充：[幻觉标记审计](hallucination_audit.md)、[检索/上下文审计](retrieval_context_audit.md)、[多条件审计](multi_condition_audit.md)、[0473原PDF专项](p6s-0473_pdf_audit.md)、[选择集合](review_selection.json)、[静态验收](static_validation.json)。`cases/`是94张可阅读卡片及结构化副本；`anomaly_evidence/`与`unanswerable_evidence_catalog.json`保存专项摘录；`pdf_pages/`保存原页渲染。

## 人工审核使用方式

1. 逐条打开签核表的`evidence_index`，核对原题、返回回答、实际LLM请求与原PDF/冻结Chunk。卡片列出的全部返回sources不保证全部进入裁剪后的实际prompt；实际请求见同名JSON及专项报告。
2. 将AI建议与人工结论分开；允许结论为Accept、Revise、Reject、Needs Verification。Revise需说明改问题、标签、答案还是引用；此表不授权覆盖冻结P6。
3. 填写`human_final_conclusion`、`human_notes`、`human_reviewer`、`human_review_date`、`human_signature`。最终结论不可由AI建议自动复制。
4. 对无答案题明确“全库无证据/部分可答/限定后可答/仍无法核实”；对0473明确原表数值和业务含义能否同时成立。若仍为Needs Verification，不能宣布最终批准。
5. 签核后应在独立版本记录裁决及后续统计，保留本包原貌。94条是定向风险集合，不构成500条随机代表性样本，不能直接外推人工总体准确率。

## 仅本地复算命令

在项目根目录执行。以下脚本不调用模型、数据库或在线检索，只读取历史文件并输出本目录；**不要运行P5/P6 runner**。

```powershell
venv/Scripts/python.exe -X utf8 p7-rag-final-audit-01/recalculate_metrics.py
venv/Scripts/python.exe -X utf8 p7-rag-final-audit-01/build_review_packet.py
venv/Scripts/python.exe -X utf8 p7-rag-final-audit-01/validate_archive.py
```

`source_hashes_before.json`为本轮入口6409个保护源文件哈希，包含P5/P6全目录、冻结语料/原PDF、签核Holdout、当前生产代码与测试；复核结果见`static_validation.json`。`sha256_manifest.json`是P7交付物清单，自身不纳入自身哈希。源配置和模型信息均引用P6已脱敏归档，不读取或复制密钥。

到P7停止。实验执行可结束，人工裁决尚未结束；不进入P8。
