# 离线解析模块复习交接

> 历史讨论快照：下文“暂停 demo / 尚未开始”指 2026-09-01 本次交接时的状态。后续独立教学 Demo 已保存在 [`demo/offline_parsing/`](../demo/offline_parsing/)，运行方式见[快速开发手册](offline_parsing_1day_demo_guide.md)。本交接中的生产链路与目标设计应结合当前源码重新核对。

更新时间：2026-09-01

仓库：`D:\AgentAIProgect\RAG`

基线分支与提交：`main` / `3aabd76`

本轮范围：只读代码复习、面试场景讨论、形成学习材料；暂停 demo，未修改业务代码。

## 1. 交接目标

这份文档用于下一次继续复习或开始教学 demo 时快速恢复上下文。它记录三类信息：

1. 当前仓库已经实现的行为；
2. 今天讨论并认可、但尚未实现的优化方案；
3. 后续 demo 必须覆盖的案例和验收标准。

后续继续时不要把第 2、3 类描述成项目现有能力，也不要把在线问答、回答缓存等内容混入离线解析范围。

## 2. 今天形成的标准主流程

面试中可以按下面的顺序回答：

```text
发现源文件
  → 知识治理预检查
  → 选择解析器并解析
  → 统一解析器输出
  → 文本/版面清洗
  → 生成 ParsedBlock
  → 解析质量门禁
  → 判断文档及各阶段是否失效
  → 按 ParsedBlock 切成 Chunk
  → 生成向量
  → 幂等写入存储
  → 写 manifest / refresh report
  → 标记本次构建完成
```

需要特别区分：

- **清洗**负责规范文本、去除已确认的噪声和保留结构。
- **质量门禁**负责判断结果能不能发布。
- **badcase / 待复核队列**保存内容质量不合格的样本。
- **死信队列**承接可重试任务耗尽次数后的执行失败，不应把所有质量 badcase 都当成死信。

## 3. 当前实现：入口与主链路

### 3.1 文件加载与失败隔离

`DirectoryDocumentLoader.load_with_report()` 串行扫描目录。单个文件解析抛异常时会记录 `source / reason / detail`，然后继续处理后面的文件，不会让整个批次立即终止。当前失败记录不包含解析器版本，也没有持久任务队列、超时终止或自动重试。

代码入口：

- [`loaders.py`](../rag_app/ingestion/loaders.py#L64)
- [`governance.py`](../rag_app/ingestion/governance.py#L43)

### 3.2 解析、清洗与 ParsedBlock

`parse_document_file()` 先通过 `_parse_file()` 按扩展名获得 `ParsedFile(text, metadata)`，随后补充来源、内容哈希、租户、权限和质量信息，再调用 `_build_parsed_blocks()` 生成 `Document.parsed_blocks`。

代码入口：

- [`parsing.py`](../rag_app/ingestion/parsing.py#L97)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L198)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L1402)
- [`models.py`](../rag_app/core/models.py#L13)

`ParsedBlock` 是解析后的结构中间层，包含段落、标题、表格等类型以及章节、父子和前后关系。它不是一棵真正嵌套的 AST，而是一组通过元数据表达层级关系的扁平 block。

### 3.3 PDF 当前路由

PDF 先用 PyMuPDF 逐页提取普通文本和页级特征，再为**整份 PDF**选择一条主要解析路线。路由优先检查有边框表格、半结构化字段和无边框表格；DeepDoc、rules_ml、MinerU 等路线一旦成功，结果会作为整份文档返回。当前没有按页或按区域混合路由。

代码入口：

- [`parsing.py`](../rag_app/ingestion/parsing.py#L451)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L507)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L1028)

已确认一个静态风险：`rules_ml` 只保留符合半结构化字段规则的行。如果它被选中并成功返回，这些字段行会替代整份 PDF 的普通正文，其他操作步骤和表格行可能丢失。

- [`parsing.py`](../rag_app/ingestion/parsing.py#L1096)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L1125)

### 3.4 OCR 与质量状态

外部/复杂表格路线没有成功接管后，普通文本为空、过短或乱码比例较高的页面会成为 OCR 候选。质量状态目前是：

- `parsed_success`
- `parsed_with_warning`
- `needs_review`
- `parse_failed`

全空页面会导致失败；空页和低文本页占比达到一半会进入待审核；其他告警通常得到 `parsed_with_warning`。质量判断是规则状态，不是一个统一的 0～100 分数。

代码入口：

- [`parsing.py`](../rag_app/ingestion/parsing.py#L531)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L990)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L1141)

### 3.5 ParsedBlock 到 Chunk

切片器优先使用 `Document.parsed_blocks`；没有 blocks 时才回退到 Markdown 标题切分。每个非标题 block 会独立切分，当前不会自动把多个很短的相邻 block 合并成父子检索单元。

默认配置为 `chunk_size=800`、`chunk_overlap=120`。对 1200 个字符的连续中文文本，窗口是：

- 第一片：1～800；
- 第二片：681～1200。

这里的单位不等于模型 tokenizer token：中文短词场景按字符，其他场景按空白分隔的单元。`chunk_id` 由 `document_id + chunk_index + chunk_text` 的 SHA-256 前 24 位生成，因此同一文档版本、同一切片结果可得到稳定 ID。

代码入口：

- [`chunking.py`](../rag_app/indexing/chunking.py#L70)
- [`chunking.py`](../rag_app/indexing/chunking.py#L132)
- [`chunking.py`](../rag_app/indexing/chunking.py#L198)
- [`chunking.py`](../rag_app/indexing/chunking.py#L217)

### 3.6 增量刷新

当前增量比较发生在文档已经完成加载、解析和质量门禁之后。因此“文件没变”只能节省后续切片、向量化和写库，不能避免本次重新解析。

当前比较项包括：

- 解析后正文的 `content_hash`；
- `parser_version`；
- PDF 解析配置指纹；
- `chunker_version`；
- embedding 模型指纹。

当前 `content_hash` 是 `parsed.text` 的 SHA-256，不是源文件字节哈希。

代码入口：

- [`offline.py`](../rag_app/indexing/offline.py#L64)
- [`offline.py`](../rag_app/indexing/offline.py#L81)
- [`offline.py`](../rag_app/indexing/offline.py#L98)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L119)

### 3.7 向量化、写库和 manifest

发生变化的文档会整篇重新切片，并把全部 chunk 文本交给 embedding 模型。当前没有离线 embedding cache，也没有按 chunk 文本复用旧向量。

PostgreSQL 存储使用确定性 `chunk_id` 和 `ON CONFLICT ... DO UPDATE` 实现幂等 upsert。一次 `upsert(records)` 在同一个连接事务中写所有 records；但“删除旧文档”和“写入新文档”分别使用两个连接事务。manifest 又在 upsert 返回后单独写本地 JSON。因此删除、写库和 manifest 之间没有一个总事务。

代码入口：

- [`offline.py`](../rag_app/indexing/offline.py#L126)
- [`offline.py`](../rag_app/indexing/offline.py#L135)
- [`offline.py`](../rag_app/indexing/offline.py#L151)
- [`offline.py`](../rag_app/indexing/offline.py#L205)
- [`vector_store.py`](../rag_app/indexing/vector_store.py#L122)
- [`vector_store.py`](../rag_app/indexing/vector_store.py#L133)
- [`vector_store.py`](../rag_app/indexing/vector_store.py#L296)

## 4. 当前实现必须注意的边界和风险

### 4.1 质量拒绝可能误删旧版本

当前代码先将通过质量门禁的文档组成 `documents_by_source`，再计算：

```text
removed_sources = manifest 中的来源 - 本轮通过门禁的来源
```

所以，一个以前已经入库的文件，如果本轮因为 `needs_review` 或 `ocr_required=true` 被门禁拒绝，会从 `documents_by_source` 消失，随后可能被当成“源文件已删除”并清除旧向量。

这与今天讨论的目标不同。目标行为是：

- 源文件真的删除：删除或停用旧版本；
- 新解析结果质量不合格：隔离新结果，保留上一个已发布版本；
- 只有新版本完成并通过验收后，才切换正式版本。

代码证据：

- [`offline.py`](../rag_app/indexing/offline.py#L72)
- [`offline.py`](../rag_app/indexing/offline.py#L76)
- [`offline.py`](../rag_app/indexing/offline.py#L86)
- [`offline.py`](../rag_app/indexing/offline.py#L126)

### 4.2 先删旧数据再生成新数据

当前流程在切片、向量化和 upsert 之前删除发生变化文档的旧数据。如果后续 embedding 或写库失败，当前 collection 可能暂时缺少这份文档。今天讨论的 PostgreSQL 改进方案是先准备新 chunks 和向量，再在一个数据库事务内切换；更完整的方案是版本化构建和激活。

### 4.3 manifest 与数据库不原子

数据库写入成功后，manifest 写入仍可能失败；反过来，旧数据删除也不与新数据写入同事务。下次任务可能重复处理。稳定 ID 和 upsert 能避免同一 chunk 产生重复行，但不能单独解决版本是否完整、是否应该激活的问题。

### 4.4 配置指纹不完整

当前 `chunker_version` 是常量，manifest 没有单独比较实际 `chunk_size` 和 `chunk_overlap`。如果只改配置而忘记更新版本常量，旧切片可能被跳过。元数据/权限单独变化也没有专门的“只更新元数据、不调用 embedding”路径。

### 4.5 PDF 版面能力有限

- 主 PDF 流程输出的 ParsedBlock 没有实际填入 `bbox`；
- 没有逐区域混合解析；
- 没有可靠的双栏阅读顺序重建；
- 没有同页“普通段落 + 表格”的区域合并；
- 没有跨页表格的 `table_id`、表头继承、续表关系、行级来源页码；
- `ParsedBlock` 的 `bbox` 字段只是模型预留，并不等于能力已经实现。

代码入口：

- [`models.py`](../rag_app/core/models.py#L20)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L569)
- [`parsing.py`](../rag_app/ingestion/parsing.py#L1523)

## 5. 今天讨论的目标设计（尚未实现）

### 5.1 分层缓存与失效判断

建议将失效判断拆成独立层级：

| 变化 | 可复用 | 必须重做 |
| --- | --- | --- |
| 源文件字节未变，所有版本未变 | 解析、清洗、blocks、chunks、向量 | 仅重新应用必须实时生效的治理规则 |
| 解析器/解析配置变化 | 无法复用最终解析结果 | 解析、清洗、blocks、chunks；chunk 文本变化时向量化 |
| 清洗规则变化 | 原始解析结果 | 清洗；结果变化后继续重建下游 |
| ParsedBlock 结构变化 | 原始解析和可能的清洗文本 | blocks、chunks；最终 chunk 文本变化时向量化 |
| chunk size/overlap/版本变化 | 解析、清洗、blocks | chunks 和发生变化的向量 |
| embedding 模型变化 | 解析、清洗、blocks、chunks | 全部向量 |
| 权限或治理 metadata 变化 | 文本与向量 | 更新数据库 metadata/过滤字段 |

建议的缓存身份包括：

- `source_hash`：源文件字节哈希；
- `parser_fingerprint`：解析器、适配器、模型/引擎版本及有效配置；
- `cleaner_version`；
- `parsed_output_hash`：文本和影响下游的结构；
- `chunker_fingerprint`：版本、size、overlap、单位规则；
- `embedding_fingerprint`：provider、model、dimension 以及实际影响向量的设置；
- `chunk_text_hash`：按 chunk 判断向量是否可复用。

如果外部解析服务不提供模型修订版本，本地无法自动识别服务方静默升级。此时只能明确标记版本未知，并通过固定版本接口（若服务支持）、人工提升适配器版本、缓存有效期或抽样重新解析降低风险，不能宣称完全可追溯。

### 5.2 PDF 按页、按区域混合路由

目标流程：

1. 先用 PyMuPDF 对所有页面做低成本提取；
2. 同时计算文本质量、图片占比、表格和版面特征；
3. 普通区域保留基础文本，扫描区域走 OCR，表格区域走对应表格解析器；
4. 复杂解析器失败时保留基础结果并记录告警；
5. 按真实 `page_number + bbox + reading_order` 合并，不能让表格解析结果替换整页或整篇正文。

页眉页脚不能只依赖全文正则。应先利用 bbox 圈定候选区域，再结合跨页重复和文本模式判断；正文中的同名标题以及安全警告需要保留规则。

### 5.3 跨页表格目标模型

跨页表格至少需要：

- 稳定 `table_id`；
- 列数量、列宽和对齐特征；
- 表头相似度或继承关系；
- 页相邻和页面边缘位置；
- 每一行的真实 `source_page`；
- 明确的结束判断，避免把表格后的正文合进去。

不能为表格虚构新的 PDF 页码。表格可以形成独立的逻辑 block，但所有行必须保留真实来源页。

### 5.4 任务可靠性

今天讨论的目标方案：

- 外部服务 `503`：2、5、10 分钟递增重试，并增加少量随机抖动；首次加三次重试共最多四次尝试；耗尽后进入死信队列。
- 文件确定损坏：记录文件、解析器版本、错误原因，不重复执行相同路线。
- 返回成功但质量不合格：进入 badcase/待复核队列，不发布；可以切换备用解析器或人工处理。
- 本地 OCR 卡死：线程或普通 `try/except` 不足以终止卡死调用。将单文档 OCR 放在可终止的独立子进程，由父进程计时；先请求协作取消，超时后终止整个进程树，确认退出后清理临时资源并释放并发名额。
- 任务幂等：确定性 ID、数据库唯一约束和 upsert 三者同时成立。
- 文档完成：`completed` 必须由协调者在确认本版本所有预期 chunk 均提交成功后设置；最后一个 chunk 的“结束标记”不能证明中间批次没有缺失。

以上任务队列、进程隔离、完成状态和 DLQ 都是设计讨论，不是当前 loader 已实现的能力。

### 5.5 PostgreSQL 与 Milvus 更新策略

PostgreSQL 可以在准备好新 chunks 和向量后，用一个数据库事务完成旧版本停用/删除和新版本写入。Milvus 不应假设具有与 PostgreSQL 相同的任意多语句事务；完整知识版本更适合写入新 collection，验收并加载完成后再切换稳定 alias，并保留旧 collection 用于回滚。

单纯 upsert 同主键不能自动删除新版本已经不存在的旧尾部 chunks；如果 chunk ID 随版本变化，也需要显式处理旧版本可见性。

## 6. badcase 与验收口径

badcase 不能只记录“某些词出现了”。表格至少要保存：

- 文档名称、来源页；
- 解析器、模型和配置版本；
- 错误码、含义、场景和相关 metadata；
- 期望的字段—值配对；
- 实际解析结果；
- 人工对照 PDF 的判断；
- 是否进入正式索引。

例如：

```text
E203 → 地址校验失败
E504 → 下游接口超时
```

即使结果同时包含 `E203`、`E504`、两个含义，配对发生交换也必须判失败。固定 badcase 通过后，还要跑正常样本回归，避免修复一个表格后破坏普通文档。

## 7. 后续 demo 清单

用户已明确要求先交接，demo 暂停。下一次只有用户再次要求时才开始。

建议 demo 独立于生产流程，重点让每一层结果可见，不先改主模块：

1. 构造一份小型混合 PDF；
2. 显示基础页面元素与 bbox；
3. 演示普通段落、同页表格、页眉页脚清洗和阅读顺序；
4. **必须加入跨页表格**：前页有表头，后页无表头，后页表格结束后还有普通段落；
5. 输出 ParsedBlock，展示 `block_type / page_number / section_path / table_id`；
6. 输出 chunk，演示 `800/120` 的窗口边界和稳定 chunk ID；
7. 构造一个质量 badcase，证明它被待复核门禁拦下；
8. 不默认调用真实 embedding API；如要展示入库，使用明确标注的本地替身或在用户授权真实环境后再接外部服务。

跨页表格 demo 的验收：

- 两页表格合并成一个逻辑表格；
- 后页没有表头也能识别为续表；
- 后页表格后的普通段落不会被吞入表格；
- 不丢行、不重复行；
- 每行保留真实来源页码；
- 输出可以追溯到原 PDF 页面和坐标。

## 8. 下一次恢复工作的建议顺序

1. 先读本交接和 [`offline_parsing_interview_guide.md`](offline_parsing_interview_guide.md)。
2. 再核对当前分支、提交和工作区，不能假设仍是 `3aabd76`。
3. 如果只是继续面试复习，保持只读，不写代码。
4. 如果用户明确开始 demo，先确认 demo 是独立练习还是要改生产模块；当前推荐独立练习。
5. demo 先写最小验收样例，再实现跨页表格规则；不要把启发式规则包装成通用生产能力。
6. 如果改生产模块，优先修复“质量门禁拒绝导致旧版本被当作删除”的状态建模问题，再考虑缓存和复杂版面能力。

## 9. 已做验证

本轮开始前已执行：

```powershell
python -B -m unittest tests.test_parsing tests.test_deepdoc_adapter tests.test_mineru_adapter tests.test_chunking tests.test_embeddings tests.test_governance tests.test_offline_refresh
```

结果：40 项测试通过。测试使用 fake adapter、fake embedding 和内存/替身存储；这不能证明真实 DeepDoc、MinerU、OCR、embedding API 或 PostgreSQL/Milvus 集成已经验收。

本轮暂停 demo 时，业务代码尚未修改。新增内容仅为学习交接和面试材料。
