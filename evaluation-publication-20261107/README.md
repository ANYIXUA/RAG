# 评估数据 GitHub 归档（2026-11-07）

本次按仓库维护要求上传已有评估材料，并将未合并的开发工作汇入 `main`。没有重新运行模型评估，也没有改写历史指标或人工签核状态。

## 材料入口

| 材料 | 路径 |
|---|---|
| P1 冻结语料与 P2 候选/Gold 原始材料 | [storage/evaluation](../storage/evaluation/) |
| 原 PDF 与检索评估样例 | [data](../data/) |
| P3 探索实验与候选召回修复证据 | [pilot-01](../p3-pilot-01/README.md)、[pilot-02](../p3-pilot-02/README.md) |
| P4 签核与冻结的 28 条 Holdout | [签核归档](../p4-gold-completion-01/signed-final-20261105-v1/signoff_archive_report.md) |
| P5 正式检索基准 | [交付索引](../p5-benchmark-01/README.md) |
| P6 500 条 Silver、原始请求/响应、运行轨迹和历史快照 | [E2E 报告](../p6-silver-e2e-500/runs/p6-e2e-run-01-qwen-flash/FINAL_REPORT.md) |
| P7 人工待审材料与复算证据 | [审计索引](../p7-rag-final-audit-01/README.md) |
| 早期检索报告 | [reports](../reports/)、[根目录报告](../retrieval_eval_20261103_134741.json) |
| 签核工作簿 | [outputs](../outputs/p4-gold-completion-01/) |

P5 Gold 共 50 条（Development 22、Holdout 28）。P6 执行完成 500 条、自动评分完成 490 条；P7 的 94 条定向审查材料仍为 `HUMAN_REVIEW_PENDING`。这些状态沿用历史归档，不代表新增人工批准。

## 完整性与脱敏

上传准备前已核对 P7 的 6409 个受保护文件，哈希均与原归档一致。原目录、历史快照和已有清单保留，未将中间结果替换为最终结果。

唯一内容脱敏位于 `p6-silver-e2e-500/run_e2e.py`：删除写死的本地数据库连接凭据及端口覆盖，改由现有 `.env` / 环境变量提供连接设置。原件仅保存在仓库外的本地备份，未上传。原始和公开版本的 SHA-256 记录于 [publication_changes.json](publication_changes.json)；历史清单未重写，因此其中该脚本的原哈希与公开版本有一处有意差异。`.env`、运行数据库、模型缓存及运行日志目录不在本次上传范围。

[frozen-source](frozen-source/) 保存 P7 审计时应用与测试的原始字节。合并其他开发分支后，当前应用代码会继续变化；历史源代码哈希应与该快照对照。旧验收脚本记录的是当时工作区及运行路径，不能直接将当前 `main` 的代码差异或 Git 状态当成评估数据损坏。

`.gitattributes` 禁止对评估材料自动转换换行符。[sha256_manifest.json](sha256_manifest.json) 记录本次公开归档的路径、字节数和 SHA-256，自身不纳入自身。可在项目根目录离线核验：

```powershell
venv/Scripts/python.exe -X utf8 evaluation-publication-20261107/verify_archive.py
```

此命令只读取文件，不连接数据库，不调用模型，不重写 P3–P7 材料。
