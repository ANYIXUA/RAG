# P4-Gold-Completion-01

本轮交付已完成，等待人工确认。当前正式Gold仍为22条，全部Development；新增批准0条，冻结Holdout 0条，正式Benchmark未运行。

优先打开[人工签核包](human_signoff_packet.md)及`outputs/p4-gold-completion-01/human_signoff.xlsx`。工作簿“签核”页前28条为Holdout主选，人工字段全空；后18条为备选、替换或驳回裁决。

- [数量与覆盖报告](gold_coverage_report.md)
- [B28–B42简洁汇总](b28_b42_signoff_summary.md)
- [B43–B57独立审核](b43_b57_independent_review.md)
- [新候选及全量待审汇总](new_candidate_review_summary.md)
- [Development/Holdout方案](development_holdout_split.md)
- [Benchmark准备清单](benchmark_readiness_checklist.md)
- [证据全文](evidence_catalog.md)
- [验证记录](validation.md)

机器可读材料：candidate_reviews.jsonl、new_candidates_15.jsonl、holdout_proposed_28.jsonl、development_manifest.json、candidate_inventory_72.json、evidence_catalog.jsonl、input_integrity.json、packet_manifest.json。它们都是审核/划分材料，不是运行用Gold导出。

原始57候选、冻结447 Chunk、3份PDF、既有22 Gold与P3文件保持不动。本轮仅新建此目录与相应outputs子目录；不修改生产代码、数据库、检索配置，不commit/push。
