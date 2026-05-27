# 离线知识处理流程

离线处理负责构建知识文档库、文档向量化和向量数据库。它不参与用户实时交互，只在以下场景执行：

- 第一次初始化知识库。
- 业务手册、历史工单、故障案例、接口说明、异常码说明等资料发生更新后手动刷新。
- Embedding 模型、切片策略、清洗规则发生变化后全量重建。

在线问答阶段只读取已经构建好的向量库，不做文档扫描、切片和向量化。

## 流程位置

```text
离线阶段
  文档目录
    → 扫描文件
    → 知识治理过滤
    → 解析文件
    → 清洗文本
    → 生成 ParsedBlock 结构化中间层
    → 解析质量门禁
    → 提取标题 / 来源类型 / 业务模块
    → 计算内容哈希
    → 判断新增 / 修改 / 删除
    → 文档清洗
    → 结构化切片
    → Embedding 向量化
    → 写入向量数据库
    → 保存处理清单 manifest

在线阶段
  用户问题
    → 意图识别
    → Query 改写 / 扩写
    → 向量检索
    → 召回知识
    → 生成回答
```

## 输入目录

默认从 `data/` 目录读取知识文件。当前支持：

- `.txt`
- `.md`
- `.rst`
- `.csv`
- `.json`
- `.jsonl`（默认识别为训练集或评测集并跳过，不进入主知识库）
- `.html` / `.htm`
- `.docx`（需安装 `.[office]`）
- `.xlsx`（需安装 `.[office]`）
- `.srt`
- `.vtt`
- `.pdf`（需安装 `.[multimodal]`）
- `.pptx`（需安装 `.[multimodal]`）

其中视频文件建议先转字幕稿（SRT/VTT）再入库；PDF/PPT 会被解析为带分页/页号小节的结构化文本，Office 和 HTML 会尽量保留标题、段落、列表和表格行，便于检索时精确引用来源。

## 输出结果

离线处理的主输出直接写入 PostgreSQL：

- `rag_documents`：进入知识库的文档元数据、治理状态和解析质量。
- `rag_knowledge_chunks`：知识切片、权限元数据、关键词字段和 pgvector embedding。

刷新过程还会保留运维清单：

- `storage/<collection>_manifest.json`：离线处理清单，记录每个源文件的内容哈希、文档 ID、切片数量、解析质量摘要和刷新时间。
- `storage/<collection>_refresh_report.json`：本次刷新报告，记录候选文件、策略跳过、解析失败、入库数量和跳过原因。

manifest 只用于增量刷新判断，在线查询不读取本地向量文件。它的作用是：

- 文件内容没变：跳过，不重新向量化。
- 文件新增：读取、切片、向量化、写入向量库。
- 文件修改：删除旧文档对应切片，重新切片和向量化。
- 文件删除：删除旧文档对应切片。
- 解析器或切片器版本变化：自动识别为需要刷新，避免旧切片结构继续留在向量库中。

## 知识治理

离线刷新不会再把 `data/` 目录下所有可解析文件都直接入库。当前先经过治理策略：

- `knowledge_registry.json` 等系统配置文件不进入知识库。
- 外部评测集不进入知识库。
- 手工整理的业务知识文档默认按 `approved` 处理。
- 标记为 `web_crawl` 的外部资料默认按 `pending_review` 处理，必须在 `knowledge_registry.json` 中显式审核为 `approved` 才能进入主知识库。
- 解析失败的文件不会中断整个刷新流程，失败原因会写入刷新报告。
- 解析质量状态不在允许列表内，或标记为 `ocr_required=true` 的文档，会被发布门禁拦截，不进入正式向量索引。

可通过 `data/knowledge_registry.json` 显式管理知识状态：

```json
{
  "entries": [
    {
      "path": "fault_cases.md",
      "status": "approved",
      "review_status": "approved",
      "reviewer": "ops-rag-review",
      "reviewed_at": "2026-05-07",
      "version": "v1"
    }
  ]
}
```

常见状态含义：

- `approved`：允许进入主知识库。
- `draft` / `pending_review`：草稿或待审核，不入库。
- `rejected`：审核拒绝，不入库。
- `deprecated`：已废弃，不入库，并会在增量刷新时删除旧向量。

## 解析规则

解析模块会先把不同格式的原始资料转换成统一的文本和元数据：

- Markdown / RST / TXT：保留正文结构，清理 BOM、换行和多余空行。
- Markdown 元数据头：支持在文档开头使用 `---` 写入 `title`、`source_type`、`business_module`、`tenant_id`、`permission_tags` 等字段，用于覆盖自动推断结果。
- HTML：用 DOM 方式提取标题、段落、列表和表格，表格会转成“表格列 / 表格行”文本。
- DOCX：提取段落、标题层级和表格，保留 Word 手册里的章节结构。
- XLSX：按工作表读取数据，并把行转换成“列名=单元格值”的行级文本。
- CSV：将每一行数据转换成 `## 记录 N` 小节，字段名作为检索文本的一部分。
- JSON：支持数组、对象，以及对象中的 `records`、`items`、`data`、`rows`、`cases`、`orders`、`errors` 列表；每条记录会转成适合切片和召回的 Markdown 文本。
- SRT / VTT：按时间戳切分为“片段”小节，保留 `[开始-结束]` 时间范围元信息。
- PDF：按页提取文本，生成 `## 第N页` 小节；同时生成页级解析质量报告，记录空白页、低文本页、疑似扫描页、疑似表格页和是否需要 OCR 复核。对于 PDF 中由多空格或制表符分隔的疑似表格行，会转成“表格列 / 表格行”的行级文本，尽量保留列关系，避免表格内容被完全打平。
- PDF OCR：OCR 是保底机制。系统会先用 PyMuPDF 做文字解析，普通文字 PDF 不走 OCR；当页级报告发现空页、低文本页或疑似扫描页时，再用 PyMuPDF 渲染页面并调用 `pytesseract` 做 OCR。OCR 后会记录 `ocr_applied`、`ocr_pages`、`ocr_confidence_avg` 和 `ocr_provider`，便于灰度排查。
- PPTX：按幻灯片提取文本，生成 `## 第N页幻灯片` 小节。

解析后的元数据会记录标题、来源类型、业务模块、解析器名称、解析器版本、内容哈希、文档版本、租户、权限标签和解析质量状态。PDF 文档还会记录 `parse_quality_status`、`parse_warnings`、`ocr_required`、`scanned_page_candidates` 等字段，供灰度发布前排查低质量资料。

解析器不会直接产出最终 chunk，而是先生成 `ParsedBlock`：

```json
{
  "block_id": "blk_xxx",
  "document_id": "doc_xxx",
  "version_id": "v_xxx",
  "block_type": "paragraph/table/heading",
  "text": "接口超时时先检查下游接口状态。",
  "page_number": 3,
  "section_path": ["接口异常", "接口超时"],
  "metadata": {
    "tenant_id": "tenant-a",
    "permission_tags": ["OPS_L2"]
  }
}
```

切片器再基于 block 生成 chunk，并把 `source_block_ids`、`section_path`、`page_number`、`tenant_id`、`permission_tags` 一起写入向量库。

当前切片策略会优先识别 Markdown 标题，例如 `#`、`##`、`###`。同一篇文档中的不同业务小节会被拆成独立知识块，避免“光猫 LOS 红灯”和“地址校验失败”这类不同主题被放进同一个增强上下文。

当切片策略、Embedding 模型或 Query 扩展规则发生变化时，即使原始文件内容没变，也应该执行 `--force`，重新生成知识切片和向量。

## 命令

首次构建或全量重建：

```powershell
python -m rag_app.cli offline-refresh --source data --reset
```

普通增量刷新：

```powershell
python -m rag_app.cli offline-refresh --source data
```

文件未变化但需要重新向量化，例如更换 Embedding 模型后：

```powershell
python -m rag_app.cli offline-refresh --source data --force
```

如果需要解析 PDF / PPTX：

```powershell
pip install -e ".[multimodal]"
```

如果需要解析 DOCX / XLSX：

```powershell
pip install -e ".[office]"
```

如果需要启用 PDF OCR 兜底：

```powershell
pip install -e ".[ocr]"
$env:RAG_PDF_OCR_ENABLED="true"
$env:RAG_PDF_OCR_LANG="chi_sim+eng"
# 如 tesseract 不在 PATH 中，可配置：
# $env:RAG_TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
```

输出 JSON 结果：

```powershell
python -m rag_app.cli offline-refresh --source data --json
```

## 和在线问答的边界

离线处理做这些事：

- 扫描知识目录。
- 解析原始文档。
- 清洗文本并补充结构化元数据。
- 清洗和切片。
- 生成 Embedding。
- 写入向量库。
- 维护 manifest。

在线问答不做这些事。在线问答只做：

- 接收用户问题。
- 识别意图。
- 改写或扩写 Query。
- 从向量库检索相关知识。
- 必要时查询 PostgreSQL 业务表。
- 生成回答或触发转人工。

这样拆分后，用户请求不会被文档解析和向量化拖慢，也避免每次问答都重复处理知识文件。
