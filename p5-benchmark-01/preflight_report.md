# 正式运行前冻结核验

2026-11-05。正式检索前 gate() 通过并落盘 preregistered_config.json。

| 检查 | 结论 |
|---|---|
| Holdout数量、唯一Gold ID | 恰好28条 |
| JSONL与sidecar | query、expected、Gold ID逐条一致 |
| 人工签核 | 全部为接受原题/接受修订，逐条与46条回执中对应记录完全一致 |
| 签核身份与日期 | system / 2026-11-05，与人工确认档案一致 |
| P4冻结SHA-256 | freeze_manifest列出的全部文件一致 |
| 冻结语料 | 3 PDF、447 Chunk，原corpus文件SHA-256一致 |
| 相关Chunk | 全部存在，来源正文SHA-256逐条一致 |
| Development隔离 | 22条原文件哈希一致；NFKC、大小写、空白标点归一化后的题目交集为空；相关/证据Chunk交集为空 |
| 数据库 | active Chunk ID与正文哈希与447条快照一致 |
| P3保护输入 | 161个保护文件全部一致，包含原评估器 |
| BM25修复实现 | SHA-256 caa94cb3b311e374035db69d1ea3ff1c0c8abed29f71c0b3a69cda1934811040，与P3 fixed2一致 |
| 依赖版本 | Python、平台、psycopg、torch、sentence_transformers、transformers、openai与P3记录一致 |
| 模型 | 原Embedding模型名、1024维；CrossEncoder原本地HF快照1427fd652930e4ba29e8149678df786c240d8825；禁止在线下载替换 |
| 参数 | 沿用P3，四组A/B/C/D；不运行A2全库诊断；Top20与评估截断10固定 |

源代码版本包含HEAD、未提交修复和各文件SHA-256，见preregistered_config.json及git_diff_entry.patch。配置在第一次Holdout检索前冻结；运行结束再次检查同一份清单。语料与模型参数没有依据Holdout成绩调整。

嵌入服务只公开text-embedding-v4别名，不公开不可变权重修订。因此只能锁定服务模型名/端点/维度和本次实际向量，不能宣称锁定服务内部权重版本。本地缓存与哈希支持本次精确向量重放。此限制在任何成绩产生前已记录。

格式适配错误与沙箱连接失败均发生在任何Holdout检索前；不是数据检查失败后跳过。自动审批曾拒绝查询外发，收到用户明确授权后才启动正式运行。
