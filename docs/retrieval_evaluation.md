# 检索评测

评测集由生产团队显式提供，不随项目携带内置评测数据。

```powershell
python -m rag_app.cli evaluate-retrieval --dataset <生产评测集.jsonl> --top-k 3 --with-rerank-provider none
```

评测样本格式：

```json
{"query":"光猫红灯咋办","expected":[{"source":"fault.md","section_title":"光猫 LOS 红灯"}]}
```

发布门禁：

```powershell
.\scripts\release_gate.ps1 -Dataset <生产评测集.jsonl>
```
