# 签核Gold归档验证

本地文件、内容与格式检查 **28/28通过**。完整检查见[validation.json](validation.json)。

236个受保护输入未变；原签核工作簿和审计副本字节一致。28条Gold及sidecar和签核版本逐条一致，18原题/10修订；原候选关系与B32/B33/B35目标变化均保留。

Development仍为原22条；新增Holdout28条覆盖27块、3文档，Development证据交集为0。B31/B39按人工确认保留待澄清，其他18条均未混入本版。

从现有evaluation.py仅提取纯JSONL解析/字段校验/目标匹配函数执行，28条均兼容现有schema，source/section_title/text_contains在447个冻结Chunk上各自唯一对应sidecar相关ID。这是格式与标签校验，没有进行检索排序或计算评测指标。

审核标识system与固定日期2026-11-05来自人工本次明确确认；原NOW公式仅作为审计证据保存。未伪造精确签署时间，未改写原表人工字段。

未连接数据库、调用模型、执行Embedding/Rerank、运行Development冒烟或正式Benchmark。也未commit/push。
