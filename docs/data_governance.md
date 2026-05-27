# 知识数据治理说明

本文档说明知识入库治理规则。目标是避免“只要放进 `data/` 就进入知识库”，让知识来源、审核状态、版本和刷新结果可追踪。

## 为什么需要治理

RAG 知识库质量直接影响回答质量。`data/` 目录里既有业务知识，也有系统配置、评测集和未审核外部网页资料。如果不做治理，系统可能把配置文件、评测样本或质量未知的外部文本当成正式知识，导致召回污染。

## 当前规则

当前离线刷新会先执行治理过滤：

- `knowledge_registry.json` 等系统文件跳过。
- `.jsonl` 训练集和评测集跳过。
- 手工维护的业务知识文档默认视为 `approved`。
- 标记为 `web_crawl` 的外部资料默认视为 `pending_review`，不会进入主知识库。
- 只有在 `knowledge_registry.json` 中显式标记为 `approved` 的外部网页资料才允许入库。

## 审核清单

审核清单路径由配置控制：

```text
RAG_KNOWLEDGE_REGISTRY_PATH=data/knowledge_registry.json
```

清单模板：

```json
{
  "version": 1,
  "entries": [
    {
      "path": "customer_fault_handbook.md",
      "status": "approved",
      "review_status": "approved",
      "reviewer": "ops-rag-review",
      "reviewed_at": "2026-05-07",
      "version": "v1"
    }
  ]
}
```

字段说明：

- `path`：相对于知识目录的文件路径。
- `status`：知识状态，常用值为 `approved`、`draft`、`pending_review`、`rejected`、`deprecated`。
- `review_status`：审核状态，可与 `status` 保持一致，也可以更细分。
- `reviewer`：审核人或审核角色。
- `reviewed_at`：审核时间。
- `version`：业务知识版本。

## 刷新报告

每次执行：

```powershell
python -m rag_app.cli offline-refresh --source data --reset
```

都会生成：

```text
storage/<collection>_refresh_report.json
```

报告包含：

- `files_seen`：候选文件数量。
- `documents_seen`：通过治理并成功解析的文档数量。
- `documents_skipped_by_policy`：被治理策略跳过的文件数量。
- `documents_failed`：解析失败数量。
- `skipped_files`：跳过文件明细和原因。
- `failed_files`：失败文件明细和异常原因。

这保证了知识库默认只包含已整理或已审核的正式知识；配置、评测集、训练集和未审核外部资料不会写入 `rag_documents` 与 `rag_knowledge_chunks`。
