# 离线解析学习版 Demo 设计

日期：2026-09-01

## 目标

在不改动现有 `demo/offline_parsing/` 和生产 `rag_app/` 的前提下，新建一条适合亲手学习的最小离线链路：

```text
TXT 目录
→ 解析为统一文档
→ 固定窗口切片
→ 生成确定性的 Hash 向量
→ SQLite 持久化
→ 余弦相似度 Top-K 查询
```

第一版只使用 Python 标准库，重点是理解数据如何流过各模块，不证明真实语义向量、生产数据库或大规模检索能力。

## 范围

### 第一版包含

- 递归发现并按路径排序 `.txt` 文件。
- 以 UTF-8 读取文本。
- 默认按 200 字符切片，重叠 40 字符；参数可配置。
- 使用 `hashlib.sha256` 生成确定性的 64 维 Hash 向量。
- 使用一张 SQLite `chunks` 表保存 Chunk 和 JSON 向量。
- 使用全表扫描和余弦相似度返回 Top-K。
- 使用 upsert 保证重复导入不产生重复记录。
- 提供 `ingest` 和 `search` 两个命令行子命令。

### 第一版不包含

- PDF、DOCX 或 OCR。
- 线程池、进程池或异步任务。
- 真实 Embedding 模型或模型下载。
- pgvector、Chroma 或其他向量数据库。
- 单文件失败隔离、重试、任务状态表或日志系统。
- 增量版本、Manifest、质量门禁、权限和生产 API 接入。

## 目录与职责

```text
demo/offline_parsing_learning/
├── __init__.py
├── models.py
├── parser.py
├── chunker.py
├── embedding.py
├── store.py
├── pipeline.py
├── cli.py
└── sample_docs/

tests/
└── test_offline_parsing_learning.py
```

- `models.py`：只定义 `ParsedDocument`、`TextChunk` 和 `SearchResult`。
- `parser.py`：发现 TXT，并读取成 `ParsedDocument`；不知道切片、向量或数据库。
- `chunker.py`：把 `ParsedDocument` 切成 `TextChunk`；不访问文件系统。
- `embedding.py`：把文本转成固定维度向量；不保存数据。
- `store.py`：负责 SQLite 建表、事务、upsert 和 Top-K 查询；不解析文件。
- `pipeline.py`：唯一负责连接解析、切片、向量和存储的业务编排模块。
- `cli.py`：只解析命令行参数并调用 Pipeline。

模块依赖只沿上述顺序向前，不允许 Parser、Chunker 或 Store 反向调用 Pipeline。
Pipeline 的导入函数返回一个简单计数字典，固定包含 `files_seen`、`files_skipped` 和 `chunks_written`，第一版不额外增加报告模型。

## 数据契约

### ParsedDocument

- `document_id`：根据相对输入目录的规范化路径生成的稳定 ID。
- `source`：相对输入目录的路径。
- `text`：完整 UTF-8 文本。

### TextChunk

- `chunk_id`：根据文档 ID、切片序号和切片文本生成的稳定 ID。
- `document_id`：所属文档 ID。
- `source`：原始文档相对路径。
- `chunk_index`：文档内从 0 开始的顺序。
- `start_offset`、`end_offset`：在原文中的字符区间。
- `text`：切片正文。

### SearchResult

- `chunk_id`：命中的 Chunk ID。
- `source`：来源文件。
- `text`：命中正文。
- `score`：余弦相似度。

## 主链路

### 导入

1. CLI 接收输入目录、SQLite 路径、切片大小和重叠量。
2. Pipeline 检查目录并调用 Parser 获取稳定排序的 TXT 文件。
3. Parser 将每个文件读取成 `ParsedDocument`。
4. Chunker 逐文档生成 `TextChunk`。
5. Embedding 模块为每个 Chunk 生成 64 维向量。
6. Store 在一个 SQLite 事务内 upsert Chunk 和 JSON 向量。
7. CLI 输出发现文件数、跳过文件数和写入 Chunk 数。

### 查询

1. CLI 接收 SQLite 路径、查询文本和 `top_k`。
2. Embedding 模块使用相同算法生成查询向量。
3. Store 读取全部 Chunk 向量并计算余弦相似度。
4. Store 按分数降序返回 Top-K `SearchResult`。
5. CLI 输出 `score`、`source` 和 `text`。

## 稳定性规则

- 不使用 Python 内置 `hash()`，避免跨进程随机种子导致向量和 ID 变化。
- Hash Embedding 先将英文和数字按连续单词、中文按单字拆成词项，再用每个词项的 SHA-256 结果选择向量槽位和正负号，累加后做 L2 归一化；不能直接对整段文本只计算一次摘要。
- `document_id` 只依赖规范化相对路径。
- `chunk_id` 依赖文档 ID、切片序号和切片文本。
- 相同输入与参数重复导入，SQLite 行数不增加。
- 切片窗口的步长为 `chunk_size - chunk_overlap`。
- 第一版向量保存在 JSON 文本列中，查询采用全表扫描；这是教学取舍，不作为性能方案。

SQLite 只建立一张表：

```text
chunks
├── chunk_id TEXT PRIMARY KEY
├── document_id TEXT NOT NULL
├── source TEXT NOT NULL
├── chunk_index INTEGER NOT NULL
├── start_offset INTEGER NOT NULL
├── end_offset INTEGER NOT NULL
├── text TEXT NOT NULL
└── embedding_json TEXT NOT NULL
```

## 错误处理

- 输入路径不存在或不是目录：立即失败并显示路径。
- 未发现 TXT：立即失败，不创建空索引。
- TXT 不是 UTF-8 或读取失败：显示具体文件并终止本次导入。
- 空文件：跳过并增加 `files_skipped`。
- `chunk_size <= 0`、`chunk_overlap < 0` 或 `chunk_overlap >= chunk_size`：抛出参数错误。
- 查询文本为空或 `top_k <= 0`：抛出参数错误。
- SQLite 导入使用单个事务；任一步写入失败则回滚。

## 测试与验收

使用仓库现有的 `unittest` 风格，至少覆盖：

1. Parser 能读取 TXT，并生成稳定 `document_id`。
2. Chunker 能生成正确的重叠区间和稳定 `chunk_id`。
3. 相同文本重复计算得到相同的 64 维向量。
4. Store 重复 upsert 后记录数不增加。
5. 两个固定样例经过完整导入后，查询 `E203 地址校验失败` 能命中预期来源。

人工验收入口：

```powershell
python -m demo.offline_parsing_learning.cli ingest --input <样例目录> --db <SQLite 文件>
python -m demo.offline_parsing_learning.cli search --db <SQLite 文件> --query "E203 地址校验失败" --top-k 2
```

完成标准：

- 单元测试全部通过。
- 导入命令退出码为 0，并输出文件与 Chunk 计数。
- 重复导入后 SQLite Chunk 数量不变。
- 查询命令退出码为 0，Top-K 包含预期来源、分数和正文。

## 后续扩展顺序

最小链路验收后，按以下顺序扩展，不在第一版提前实现：

1. 将字符切片调整为生产默认 `800/120` 并加入结构化切片。
2. 增加 PDF、DOCX Parser，但保持 `ParsedDocument` 契约不变。
3. 增加单文件失败隔离和批次报告。
4. 用真实 Embedding 替换 Hash 实现。
5. 用 pgvector 或 Chroma 替换教学 SQLite 扫描。
6. 再加入并发、增量版本、质量门禁和生产服务接线。
