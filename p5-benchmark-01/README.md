# P5-Benchmark-01 交付索引

- [正式指标报告](report.md)
- [四组两轮完整指标](four_group_results.json)、[指标CSV](metrics.csv)、[相对/绝对变化](deltas.json)
- [首轮完整排名](runs/run1/rankings.jsonl)、[重复排名](runs/run2/rankings.jsonl)、[逐题命中CSV](per_query.csv)
- [失败案例](failure_analysis.md)、[简历指标核实](resume_verification.md)
- [运行前检查](preflight_report.md)、[预注册配置与版本](preregistered_config.json)
- [复现说明](reproduction.md)、[独立审计](verification.json)
- [依赖](dependencies.txt)、[环境及模型文件哈希](environment_details.json)、[实际语料向量](database_vectors.json)、[查询向量](query_vectors.json)
- [文件SHA-256总清单](sha256_manifest.json)、[原保护输入哈希](protected_input_hashes.json)

Gold总数50，Development22，正式Holdout28。所有正式指标分母为28。结果仅适用于当前冻结语料和任务分布，样本较小。未调参、未commit/push，不继续优化。
