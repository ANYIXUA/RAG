# RAG 离线解析：1 天 Demo 快速开发手册

> 适用仓库：`D:\AgentAIProgect\RAG`
>
> 依据：`docs/offline_parsing_review_handoff.md`（2026-09-01）
>
> Demo 代码：`demo/offline_parsing/`

## 0. 先定边界：今天做什么，绝不混写什么

本手册实现一条独立教学链路：

```text
发现 PDF / DOCX / TXT
  → 按格式分配进程池/线程池
  → 单文件失败隔离
  → 保守清洗与统一 ParsedDocument
  → 按页、标题和段落切成 800/120 Chunk
  → Hash 替身或本地 Sentence Transformer 批量向量化
  → SQLite 验收索引或 Chroma 批量 upsert
  → Top-K 查询并核对 source + page_number
```

这不是对生产 `rag_app` 主链路的改造。当前生产代码已有 `ParsedBlock`、质量门禁、`800/120` Chunk、稳定 ID、增量 manifest 和 pgvector upsert；但目录加载仍是串行的，PDF 仍按整篇选择主要复杂解析路线，也没有通用跨页表格、分层缓存、进程级 OCR 超时、版本化发布或 DLQ。Demo 中的并行池、Chroma、Hash Embedding 和跨页表格启发式均不得描述成当前生产能力。

一天排期建议：

| 时间 | 交付物 | 完成标志 |
| --- | --- | --- |
| 09:00–10:00 | Python 3.12 环境、依赖、样例 | TXT 样例能读取；重型依赖可选安装 |
| 10:00–12:00 | 并行解析、清洗、失败隔离 | PDF 进程池、DOCX/TXT 线程池；坏文件不阻断批次 |
| 13:00–14:00 | 结构切片与 metadata | 1200 个中文字符得到 `[0,800)`、`[680,1200)` |
| 14:00–16:00 | 批量 embedding、动态降级、写库 | 130 chunks 按 `64/64/2` 写入；OOM 自动减半 |
| 16:00–17:00 | `ingest_demo.py`、`search_test.py` | 输出分阶段耗时、`chunks/sec`、Top-K 来源页 |
| 17:00–18:00 | 固定 badcase、跨页续表与回归 | 字段—值错配被拦截；续表行保留真实页码 |

目录如下：

```text
demo/offline_parsing/
├── requirements.txt          # 完整：Chroma + Sentence Transformers
├── requirements-chroma.txt   # Chroma + Hash，不装 Torch
├── requirements-lite.txt     # PDF/DOCX + Hash + SQLite，不装 Chroma/Torch
├── parsing.py                # 并行池、格式路由、清洗、独立页批次示例
├── chunking.py               # 结构优先 + 800/120
├── embedding_store.py        # 批量 encode、OOM 降级、Chroma/SQLite
├── pipeline.py               # 端到端分批编排与统计
├── ingest_demo.py            # 主入口
├── search_test.py            # Top-K 验收入口
├── table_continuation.py     # 固定跨页表格启发式
├── quality.py                # 字段—值配对质量门禁
├── quality_demo.py           # 固定错配 badcase 可执行验收
├── make_sample_data.py       # 混合 PDF/文本样例生成器
└── sample_docs/              # 无额外依赖即可运行的 TXT 样例
```

---

## 阶段一：环境搭建与核心依赖定义

### 1.1 推荐环境

仓库声明 Python `>=3.10`，但本机当前默认 Python 是 3.14.7，`dev` 环境是 3.13.15。一天 Demo 推荐单独使用 **CPython 3.12 x64**，因为 Chroma、ONNX Runtime、Torch、SciPy 与 scikit-learn 的 Windows wheel 组合更稳，避免现场编译 C/C++。

```powershell
conda create -n rag-demo312 python=3.12 -y
conda activate rag-demo312
python -m pip install --upgrade pip

# 先强制只用 wheel：若某个包想现场编译，立即失败，尽早暴露环境问题。
python -m pip install --only-binary=:all: `
  -r demo/offline_parsing/requirements.txt
```

完整 [`requirements.txt`](../demo/offline_parsing/requirements.txt)：

```text
PyMuPDF==1.28.2
python-docx==1.2.0
lxml==6.1.2
chromadb==1.5.9
onnxruntime==1.29.0
numpy==2.5.2
sentence-transformers==5.5.1
transformers==4.57.6
torch==2.13.0
scikit-learn==1.9.0
scipy==1.18.1
```

版本策略：

- `sentence-transformers==5.5.1` 配 `transformers==4.57.6`，避开刚升级到 Transformers 5 体系的新主版本，降低一天 Demo 的破坏性变更风险。
- `PyMuPDF==1.28.2` 提供页面、bbox 和 `find_tables()` 能力。`pypdf` 可作为普通文本场景的另一个方案，但当前代码没有它的适配器，不能只改 requirements 就直接替换。
- `python-docx` 只读 `.docx`，不能读老式 `.doc`；`.doc` 应先由 LibreOffice 批量转换。
- Chroma 默认 embedding 可能触发模型下载。代码在 `PersistentClient` collection 上显式使用 `embedding_function=None`，并始终传入自己的 `embeddings=` / `query_embeddings=`。
- 模型权重不受 `requirements.txt` 锁定。真实 BGE 模型应固定 `model_name + revision + cache_folder`，并在离线环境使用 `--local-files-only`。

### 1.2 重型依赖失败点与当天替代方案

| 风险项 | 现场症状 | 当天方案 | 能证明什么 |
| --- | --- | --- | --- |
| Torch + Transformers | 下载大、CUDA/驱动不匹配、无对应 wheel | `--embedding hash`；只跑标准库 Hash Embedding | 证明批处理、持久化和检索链路，不证明语义质量 |
| Chroma + ONNX Runtime | 依赖树大、gRPC/OpenTelemetry 安装慢 | `--store sqlite`；使用标准库 SQLite + Python 余弦检索 | 证明本地持久化、upsert 和 Top-K 协议，不证明 Chroma 性能 |
| PyMuPDF | wheel/许可证审查失败 | TXT/DOCX 先跑通；若选 `pypdf`，需另写适配器 | 不再证明 bbox/表格检测 |
| Tesseract/OCR | 还需要独立二进制和语言包 | 一天 Demo 不默认加入扫描件 OCR | 扫描 PDF 标为 `needs_review`，不假装已解析 |
| C/C++ 源码编译 | pip 长时间卡在 `Building wheel` | 使用 Python 3.12 x64 + `--only-binary=:all:` | 缺 wheel 立即失败，避免浪费半天 |

最轻安装（PDF/DOCX + Hash + SQLite）：

```powershell
python -m pip install --only-binary=:all: `
  -r demo/offline_parsing/requirements-lite.txt
```

如果连轻量依赖都不安装，仍可用 TXT + Hash + SQLite 完成主链路验收。

若要验收 Chroma 但不安装 Torch/BGE：

```powershell
python -m pip install --only-binary=:all: `
  -r demo/offline_parsing/requirements-chroma.txt
```

---

## 阶段二：多线程/多进程并行文档解析

### 2.1 分格式队列

规则很简单：

- PDF：解析、表格检测、图片/字体解码偏 CPU，放 `ProcessPoolExecutor`。
- DOCX/TXT：主要等待磁盘和 ZIP/XML 读取，放 `ThreadPoolExecutor`。
- 任务按规范化 `source` 排序后提交；`Future` 的完成顺序不能改变 Chunk 顺序和稳定 ID。
- 每个文件由 `_safe_parse()` 捕获异常，坏文件写 `source/error_type/error_message`，其他文件继续。

核心实现见 [`parsing.py`](../demo/offline_parsing/parsing.py)：

```python
def recommended_worker_counts(cpu_count: int | None = None) -> tuple[int, int]:
    cores = max(1, cpu_count or os.cpu_count() or 1)
    process_limit = 61 if os.name == "nt" else cores
    cpu_workers = min(max(1, cores - 1), process_limit)  # Windows 上限 61
    io_workers = max(4, min(32, cores * 4))
    return cpu_workers, io_workers


def iter_parsed_documents(paths, *, source_dir, parse_batch_size=8,
                          cpu_workers=None, io_workers=None):
    ordered_paths = sorted(paths, key=lambda p: str(p).casefold())
    pdf_paths, io_paths = partition_paths(ordered_paths)
    default_cpu, default_io = recommended_worker_counts()

    with ExitStack() as stack:
        pdf_pool = stack.enter_context(ProcessPoolExecutor(
            max_workers=min(cpu_workers or default_cpu, len(pdf_paths)))) if pdf_paths else None
        io_pool = stack.enter_context(ThreadPoolExecutor(
            max_workers=min(io_workers or default_io, len(io_paths)))) if io_paths else None

        # 关键：最多只挂起 parse_batch_size 个文件，避免 Future 和大文档一起堆积。
        for path_batch in batched(ordered_paths, parse_batch_size):
            futures = []
            for path in path_batch:
                pool = pdf_pool if path.suffix.lower() == ".pdf" else io_pool
                futures.append(pool.submit(_safe_parse, str(path), str(source_dir)))
            for future in futures:       # 提交顺序稳定；异常已在单文件内部隔离
                yield future.result()
```

### 2.2 单个超大 PDF 的多页并行示例（未接入主 CLI）

多文件进程池对“100 个 PDF”有效；如果只有一个 1000 页 PDF，需要按页范围拆分。不能把同一个 `fitz.Document` 跨线程共享，而是让每个子进程重新打开文件：

```python
def iter_pdf_page_batches(path: Path, *, page_batch_size=16, workers=None):
    with fitz.open(path) as document:
        page_count = document.page_count
    ranges = [(str(path), start, min(start + page_batch_size, page_count))
              for start in range(0, page_count, page_batch_size)]
    actual_workers = min(workers or max(1, (os.cpu_count() or 1) - 1), len(ranges))
    with ProcessPoolExecutor(max_workers=actual_workers) as executor:
        # 再限制在途页范围，避免一次提交所有页任务。
        for range_batch in batched(ranges, actual_workers * 2):
            for pages in executor.map(_parse_pdf_page_range, range_batch):
                yield pages
```

`iter_pdf_page_batches()` 是可运行的页范围解析函数，但当前 `ingest_demo.py` **没有调用它**：主 CLI 仍会把单个 PDF 的全部 `ParsedPage` 放入一个 `ParsedDocument`。因此它只展示超大 PDF 的扩展实现思路，不能作为主 CLI 已解决单文件 OOM 的证据。若要接入，应让父进程拿到一个页批次后立刻清洗、切片、向量化、写入 staging generation 并释放；跨页页眉页脚则需要先收集页边缘签名的第一遍扫描。

### 2.3 清洗规则

Demo 执行以下保守规则：

1. 删除 Unicode replacement character `\ufffd` 和不可见控制符。
2. 统一行内空白、连续空行和纯装饰符号行。
3. 只在每页第一/最后一条非空行中识别跨页重复模板；动态页码先将数字规范化再比较。
4. 删除动作不做全文全局替换，所以正文中的同名标题和“安全警告”会保留。
5. 连续 `！！！`/`!!!` 规范为 `!!!`，不删除句子本身。

生产目标应在仍有 bbox 时先圈定页顶/页底候选区，再组合“位置 + 跨页重复 + 文本模式 + 保留规则”。当前字符串首尾行规则只是 Demo 启发式。

### 2.4 CPU、IO 与 OOM 参数

| 参数 | 默认 | 调整条件 |
| --- | --- | --- |
| `cpu_workers` | `max(1, CPU-1)`，Windows 封顶 61 | PDF 同时打开后内存高时减到 2–4；容器还要看 CPU quota |
| `io_workers` | `min(32, CPU*4)`，至少 4 | 网络盘慢可增加；本地机械盘随机读过多应减小 |
| `parse_batch_size` | 8 | 单文件数百 MB 时降到 2–4 |
| `page_batch_size` | 16 页 | 图片密集页降到 4–8 页 |

文件 Future 由 [`batched()`](../demo/offline_parsing/parsing.py) 限制在当前批次，`iter_document_chunks()` 又逐个产生 Chunk，Pipeline 只保留一个向量写入批次。这个设计避免“整份 chunk 列表 + 全部向量”同时驻留，但当前主 CLI 仍物化单个 PDF 的全部页面。它也不能把 OCR 卡死强制终止；真正的 OCR 超时仍需“单文档独立子进程 + 父进程计时 + 终止进程树”。

---

## 阶段三：文本切片与 Metadata 标记

### 3.1 结构优先切片

[`chunking.py`](../demo/offline_parsing/chunking.py) 的 `iter_document_chunks()` 逐个产出 Chunk：先按真实页分开，再识别 Markdown 标题或“第 N 章/节”，合并过短段落，最后才对超长内容做滑窗。兼容函数 `split_document()` 仅在单测或小数据场景把该生成器转成列表：

```python
step = chunk_size - chunk_overlap  # 800 - 120 = 680
for start in range(0, len(units), step):
    end = min(start + chunk_size, len(units))
    chunk_text = joiner.join(units[start:end]).strip()
```

默认 `chunk_size=800`、`chunk_overlap=120`：

```text
第一片：[0, 800)   → 人类计数第 1～800 个字符
第二片：[680,1200) → 人类计数第 681～1200 个字符
```

这里的单位是“连续中文按字符、其他内容按空白单元”，不是模型 tokenizer token。若模型有明确 token 上限，生产版还要用同一 tokenizer 再做长度检查。

### 3.2 必须携带的 metadata

| 字段 | 用途 |
| --- | --- |
| `chunk_id` | `document_id + page + chunk_index + text` 的稳定 SHA-256 前 24 位 |
| `document_id` | 本次 Demo 的文档版本身份 |
| `source` | 相对输入目录路径，便于展示和搬迁 |
| `source_path` | 本机绝对路径，只用于排障，不应直接暴露给外部用户 |
| `page_number` | 真实 PDF 页；TXT/DOCX 无分页时为 1 |
| `page` | 为满足简单 Demo/外部脚本保留的别名；内部统一读取 `page_number` |
| `chunk_index` | 文档内稳定顺序 |
| `section_title` / `section_index` | 结构定位 |
| `start_unit` / `end_unit` | 800/120 边界复核 |
| `parser` / `parser_version` | 解析器追溯 |
| `source_hash` / `cleaner_version` | 失效判断的最小证据 |

避免索引爆炸的四条线：

- 不为每一句话单独建向量；同页同节的短段先合并到约 120 字符。
- `overlap` 不超过 `chunk_size` 的 15%～20%；当前 `120/800=15%`。
- 表格优先按“表头 + 若干数据行”组成检索单元，而不是每个单元格一个向量。
- 入库前打印 `chunks_created / files_succeeded`。若普通文档平均数异常跳升，先检查切片规则再扩容数据库。

---

## 阶段四：批量向量化与向量库写入

### 4.1 真实 Batch Processing

[`SentenceTransformerEmbedding.encode()`](../demo/offline_parsing/embedding_store.py) 不是逐条循环调用模型，而是一次把句子矩阵交给模型：

```python
matrix = self.model.encode(
    list(sentences),
    batch_size=batch_size,              # 显式 64 或 128
    show_progress_bar=show_progress_bar,
    convert_to_numpy=True,
    normalize_embeddings=True,
)
```

推荐中文轻量模型 `BAAI/bge-small-zh-v1.5`。先在可联网环境预热一次缓存：

```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5', cache_folder=r'D:\Models\huggingface')"
```

随后在 Hugging Face 模型页记录本次使用的 commit SHA，并通过 `--model-revision <commit-sha>` 固定它。空缓存时直接加 `--local-files-only` 必然失败；该参数只用于缓存已准备好的离线演示：

```powershell
python -m demo.offline_parsing.ingest_demo `
  --input demo/offline_parsing/sample_docs `
  --persist-dir .demo_data/bge_chroma `
  --embedding sentence-transformers `
  --model BAAI/bge-small-zh-v1.5 `
  --model-revision <commit-sha> `
  --model-cache D:\Models\huggingface `
  --local-files-only `
  --device cpu `
  --store chroma `
  --batch-size 64
```

### 4.2 Dynamic Batch Scaling

单个 batch OOM 后不能跳过这批文本。代码将同一批按 `128→64→32→...→1` 减半重试；batch=1 仍失败或错误并非 OOM 时原样抛出：

```python
while offset < len(texts):
    batch = list(texts[offset: offset + current_batch_size])
    try:
        encoded = encoder.encode(
            batch,
            batch_size=current_batch_size,
            show_progress_bar=show_progress_bar,
        )
    except (MemoryError, RuntimeError) as exc:
        if not _is_oom(exc) or current_batch_size <= min_batch_size:
            raise
        current_batch_size = max(min_batch_size, current_batch_size // 2)
        _release_accelerator_cache()
        continue                         # offset 不变：重试同一批
    embeddings.extend(encoded)
    offset += len(batch)
```

降级后的较小 batch 会沿用到后续写入批次，避免每批都先 OOM 一次。监控字段是 `effective_batch_size` 和 `oom_retries`。

### 4.3 Chroma 本地持久化与批量 upsert

持久化目录由 CLI 显式传入，不能依赖当前工作目录：

```python
client = chromadb.PersistentClient(path=str(persist_dir.resolve()))
collection = client.get_or_create_collection(
    name=collection_name,
    metadata={"hnsw:space": "cosine"},
    embedding_function=None,
)

# 每 64 个 Chunk 只调用一次 upsert。
collection.upsert(
    ids=[chunk.id for chunk in chunks],
    documents=[chunk.text for chunk in chunks],
    embeddings=embeddings,
    metadatas=[to_scalar_metadata(chunk.metadata) for chunk in chunks],
)
```

Chroma metadata 只能稳定保存标量，因此列表/字典会编码为 JSON 字符串；查询后再恢复。Manifest 记录 `embedding_model / embedding_dimension / model_revision / embedding_fingerprint`。每次导入写入新的 `generations/<generation_id>` 目录，完整计数和质量检查通过后才原子替换 active manifest，因此修改/删除源文件不会与旧向量混在同一 active 索引中；旧 generation 暂留用于回滚。

Pipeline 外层再按 `batch_size` 分块，130 个 chunks、`batch_size=64` 时传给 store 的批次形状应为：

```text
64 + 64 + 2
```

真实 Chroma、Hash Embedding 的轻量验收命令是：

```powershell
python -m demo.offline_parsing.ingest_demo `
  --input demo/offline_parsing/sample_docs `
  --persist-dir .demo_data/hash_chroma `
  --embedding hash `
  --store chroma `
  --batch-size 64 `
  --no-progress
```

当前仓库自动测试用 recording store 验证 `64/64/2`，并用 fake collection 验证 Chroma payload；只有在安装 `requirements-chroma.txt` 后运行上面命令，才算真实 Chroma 持久化验收。若要实测 Chroma 的 `64/64/2`，输入集必须实际产生至少 130 个 chunks。

---

## 交接加验：跨页表格与质量 badcase

### 加验 A：固定跨页表格

交接要求的固定案例是：第一页有表头，第二页没有表头，第二页表格结束后还有普通正文。运行：

```powershell
python -m demo.offline_parsing.make_sample_data `
  --output .demo_data/mixed_samples

python -m demo.offline_parsing.table_demo `
  .demo_data/mixed_samples/mixed_manual.pdf
```

[`table_continuation.py`](../demo/offline_parsing/table_continuation.py) 只在以下条件同时成立时认为是续表：相邻页、前页表格靠近页尾、后页表格靠近页首、列数一致；相同表头会去重，无表头则直接接续。输出必须满足：

- 两页使用同一个稳定 `table_id`；
- 不丢行、不重复行；
- 每行保留真实 `source_page`；当前 PyMuPDF `table.extract()` 只给出整表 bbox，所以输出字段明确叫 `table_bbox`，不冒充行级 bbox；
- 第二页表格后的普通段落不属于表格 bbox，不被吞入；
- 不虚构“逻辑第 3 页”等新 PDF 页码。

输出同时包含类似 ParsedBlock 的 `block_id / block_type / page_number / bbox / section_path / table_id`，以及由 `table_to_chunk()` 生成的表格 Chunk；Chunk metadata 保存 `source_pages=[1,2]`。这条固定表格旁路没有接入通用 `ingest_demo.py` 的 PDF 解析器，不能声称主检索链路已经具备通用跨页表格能力。生产设计还应取得真实行 bbox，比较列宽、对齐、列类型、表头相似度、续表标记和明确停止条件。

### 加验 B：字段—值质量门禁

只检查关键词会产生假通过。下面四个词都出现了，但配对是错的：

```text
E203 下游接口超时
E504 地址校验失败
```

[`quality.validate_expected_pairs()`](../demo/offline_parsing/quality.py) 要求 key 和期望值出现在同一行；错配时返回 `needs_review`。质量 badcase 进入待复核隔离，不进入 DLQ，也不应删除上一版已发布知识。执行任务因 503/超时重试耗尽才进入 DLQ。

```powershell
python -m demo.offline_parsing.quality_demo
```

该命令只有在固定错配样例得到 `accepted=false / status=needs_review / disposition=review_quarantine` 时才退出 0。主 ingest 还会把空文本或需要 OCR 的 PDF 标为 `needs_review`，Pipeline 不写入这些文档；默认只要存在解析失败或质量拒绝，新 staging generation 就不会激活，旧 active manifest 保持不变。

---

## 阶段五：Pipeline、基准与验收

### 5.1 零重型依赖的当天首跑

```powershell
python -m demo.offline_parsing.ingest_demo `
  --input demo/offline_parsing/sample_docs `
  --persist-dir .demo_data/offline_acceptance `
  --store sqlite `
  --embedding hash `
  --batch-size 64 `
  --parse-batch-size 8 `
  --no-progress
```

`ingest_demo.py` 会打印：

```json
{
  "files_seen": 2,
  "files_succeeded": 2,
  "files_failed": 0,
  "files_rejected": 0,
  "pages_parsed": 2,
  "chunks_created": 2,
  "chunks_written": 2,
  "parse_seconds": 0.0,
  "chunk_seconds": 0.0,
  "embedding_seconds": 0.0,
  "write_seconds": 0.0,
  "total_seconds": 0.0,
  "chunks_per_second": 0.0,
  "effective_batch_size": 64,
  "oom_retries": 0
}
```

上面的数值只是输出结构示意，不是性能承诺。真实值以每次命令输出为准。

每次构建先写新的 staging generation。只有 `vector_count == chunks_written` 且默认不存在失败/质量拒绝时，CLI 才原子更新 `demo_index_manifest.json`；搜索脚本只读取 active manifest。`parse_seconds` 是并行 worker 内各文件解析耗时之和，用于比较解析工作量，可能大于墙钟 `total_seconds`；其他阶段和总耗时是协调进程的墙钟计时，不能把几项简单相加当作端到端时间。

### 5.2 Top-K 单命令验收

```powershell
python -m demo.offline_parsing.search_test `
  --persist-dir .demo_data/offline_acceptance `
  --query "E203 地址为什么校验失败" `
  --top-k 2 `
  --expected-source incident_codes.txt `
  --expected-page 1
```

脚本打印每个 Top-K 的 `rank/score/source/page_number/chunk_id/text`，最后打印：

```json
{"metric":"source_page_hit_at_k","top_k":2,"hit":1}
```

`hit=1` 且进程退出码为 0，才表示这个黄金查询的“来源文件 + 页码”命中。它是单条样例的 Hit@K，不应写成整个数据集准确率。要计算正式 Recall@K/MRR，应建立多条人工标注 query—source—page 黄金集。

### 5.3 测试与完成定义

```powershell
# 不依赖 pytest，使用仓库现有 unittest 风格。
python -B -m unittest tests.test_offline_parsing_demo -v

# 回归原有离线解析相关测试。
python -B -m unittest `
  tests.test_parsing `
  tests.test_deepdoc_adapter `
  tests.test_mineru_adapter `
  tests.test_chunking `
  tests.test_embeddings `
  tests.test_governance `
  tests.test_offline_refresh
```

Demo 完成必须同时满足：

- [ ] PDF/DOCX/TXT 被正确路由到进程池/线程池；单文件失败不阻断后续文件。
- [ ] worker 数受 CPU 核心数和任务数共同限制，Windows 进程池不超过 61。
- [ ] 文件 Future 和 Chunk 通过 Generator/批次消费；明确主 CLI 仍会物化单个 PDF 的全部页面。
- [ ] 重复页眉页脚和乱码被清理，安全警告保留。
- [ ] `800/120` 边界准确，稳定 `chunk_id` 可复现。
- [ ] 每个 Chunk 有 `source + page_number + chunk_id`，并能反查原文件。
- [ ] 130 chunks、batch 64 的写入批次为 `64/64/2`。
- [ ] OOM 后 batch 减半、同一批重试、无漏/无重；batch=1 仍 OOM 时失败退出。
- [ ] `ingest_demo.py` 输出解析、切片、embedding、写入和总耗时及 `chunks/sec`。
- [ ] 新 generation 完整后才切 active manifest；重复导入不让旧向量继续出现在 active 索引。
- [ ] `search_test.py` 的黄金查询得到 `source_page_hit_at_k=1`。
- [ ] 跨页续表同一 `table_id`，行级真实页码保留，表后正文未吞入；整表 bbox 不冒充行 bbox。
- [ ] 字段和值互换即使关键词齐全也得到 `needs_review`。
- [ ] 明确 Hash/SQLite/fake 测试不证明真实 BGE、Chroma、OCR、MinerU 或生产数据库已验收。

### 5.4 常见失败快速定位

| 现象 | 先检查 | 处理 |
| --- | --- | --- |
| `No matching distribution found` | Python 小版本/架构 | 切到 CPython 3.12 x64，使用 `--only-binary=:all:` |
| 首次查询突然下载模型 | Chroma 默认 embedding 未禁用 | `embedding_function=None`，显式传 embedding |
| CUDA OOM | `batch_size`、显存占用 | 从 128 降到 64/32；确认动态降级没有吞非 OOM 错误 |
| 内存随文件数线性上涨 | 是否先 `list(all_documents)` | 使用 `iter_parsed_documents` 与 `iter_document_chunks`，写完一个 batch 立即释放 |
| 单个超大 PDF 仍 OOM | 主 CLI 仍物化全部页面 | 先单独使用 `iter_pdf_page_batches()`；接入主 CLI 是明确未完成项 |
| PDF CPU 100% 且系统卡顿 | `cpu_workers == CPU` | 留 1–2 核；图片密集 PDF 降低页批次 |
| Word 解析为空 | 输入是否为 `.doc` | 先转换为 `.docx`；不要把 `.doc` 当作 python-docx 支持 |
| Top-K 命中词但页码错 | metadata 在哪一层丢失 | 沿 `ParsedPage → Chunk → Chroma metadata → SearchResult` 逐层打印 |
| 四个关键词都有却门禁失败 | 是否字段—值配错 | 这是正确行为；逐对核对，不以关键词集合判通过 |

完成这份 Demo 后，下一步才是生产改造：优先修复主链路中“质量门禁拒绝可能把旧发布版本当成删除”，再设计分层缓存和完整文档版本状态。独立 Demo 已用 generation + active manifest 避免半成品暴露，但这不等于生产 pgvector 已获得同样语义。不要直接把 Demo 的 Chroma 或跨页启发式接到生产流程。

## 参考的官方资料

- [PyMuPDF 包与 Python/Windows wheel 信息](https://pypi.org/project/PyMuPDF/)
- [python-docx 包信息](https://pypi.org/project/python-docx/)
- [Chroma PersistentClient](https://docs.trychroma.com/docs/run-chroma/cloud-client?lang=python)
- [Chroma 直接提交 query embeddings](https://docs.trychroma.com/docs/querying-collections/query-and-get)
- [Sentence Transformer encode 参数](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html)
- [BAAI/bge-small-zh-v1.5 模型卡](https://huggingface.co/BAAI/bge-small-zh-v1.5)
