# Evaluation Dataset V1：只读语料导出与快照

本文记录 Active Chunk Exporter 和 Corpus Snapshot。
P1 本地候选生成入口、覆盖度与代码审查见 [候选生成说明](eval_candidate_generation.md)。
快照导出使用只读事务，不创建数据库对象。

## 环境与代码来源

在 `D:\AgentAIProgect\RAG` 执行当前工作树代码，使用既有 `pgsql` 可选依赖
中的 psycopg。无需安装新依赖。不要在旧 `rag-api` 镜像内运行命令来验证
当前实现；其挂载来源为另一个 worktree。

CLI 使用现有 `Settings.from_env()`；不会自动加载 `.env`。调用前由现有
部署方式注入环境变量，特别是 `RAG_OPS_POSTGRES_DSN`。保持密码在环境
或受保护配置内，不放在命令参数、报告和 Git 中。配置 JSON 的现有优先级
保持不变，显式 `--collection` 必须与加载后的 `Settings.collection_name`
一致；不同则拒绝执行，不会自动切换配置或知识版本。

如果 `.env` 中的 DSN 使用容器网络主机名 `postgres`，本机 Python 通常
不能直接解析它。应在当前命令进程中使用实际已公布的宿主机端口；不要
修改生产 Compose。阶段验证使用现有 PostgreSQL 的 `127.0.0.1:15432`
映射，复用既有凭据，仅临时替换主机和端口。

## 导出

```powershell
.\venv\Scripts\python.exe -B -m rag_app.cli export-eval-chunks --help
.\venv\Scripts\python.exe -B -m rag_app.cli export-eval-chunks --collection default --tenant-id default --permission-tags public --output-dir storage/evaluation/corpus/manual-001 --json
```

所有权限参数必填。多个标签用空格分隔，例如 `--permission-tags public OPS_L2`；
它们表示操作者明确声明的授权标签集合，采用与现有检索一致的“标签有交集”
语义。CLI 是本地数据库运维工具，不提供新的身份认证或授权授予能力；只有
本来就有对应数据库与文档访问权限的操作者才能运行。

`--output-dir` 必须不存在，包括已有空目录也会拒绝。省略时在现有
`Settings.storage_dir/evaluation/corpus/` 下创建唯一子目录。可用
`--max-records` 设置单租户 ACL 预检上限（默认 100000），以及
`--statement-timeout-seconds` 设置单语句超时（默认 30 秒）。

数据库安全边界：

- 独立连接默认 `default_transaction_read_only=on`，开启
  `REPEATABLE READ READ ONLY`，执行 `SHOW` 核验真实事务状态后才读取行。
- 首先仅读取显式 collection/tenant 的 active Chunk 的身份和 ACL，核验
  同 collection/document_id 关联、文档 active 状态及双方权限数据。
- ACL 必须为显式 tenant 字符串和非空字符串标签数组。导出器不会套用
  生产链路的缺失 tenant/tag 默认值；当前租户内的异常关联/权限会阻断导出。
- 只对已通过检查且标签有交集的 ID 查询正文，SQL 再次限制 collection、
  双方 tenant、active 状态和双方标签；读取后再次检查身份和元数据一致性。
- 不构造 VectorStore 或知识生命周期 Store，不调用模型、Redis、索引刷新
  或知识版本激活。结束事务使用 ROLLBACK，任何阶段失败都不发布可用快照。

这里的 active 指显式 collection 中 Chunk 和 Document 的 `status='active'`。
不会自动跟随全局 active-version 指针；如需版本化 collection，应先明确
目标并通过既有配置机制配置该 collection。

## 文件与可复现性

产物为 `corpus.jsonl` 和最后写入的 `corpus.manifest.json`。

JSONL 保留 chunk_id、document_id、source、page_number、document_version、
chunk_text 和白名单 metadata；同时保存 collection、tenant、permission_tags、
文档内容哈希、Chunk 正文哈希和数据库 Chunk version。原文不做空白归一化。

document_version 优先取 Chunk metadata.version_id，其次取文档 metadata.version_id，
最后显式回退 `sha256:<document content_hash>`；`document_version_source` 记录来源。
两端版本或 source 冲突时停止。无分页文档的 page_number 可以为 null。

metadata 仅导出代码内 `METADATA_FIELDS` 指定的结构性字段。source_path、
未知字段等不会原样输出，manifest 记录排除的字段名，不记录这些字段值。
白名单字段还受类型校验：文本字段不能夹带对象；章节路径、标签和警告码
只能是字符串数组；页码和序号拒绝布尔值、浮点数及嵌套对象。
这并不是对知识正文的自动脱敏：正文和来源本身仍可能敏感，产物必须留在
授权本机目录内。

P1 导出的 schema v2 在白名单中加入可选 `error_code` 字符串和
`error_codes` 字符串数组。标量优先取生产精确检索使用的现有索引列，
缺失时沿用 Chunk metadata 中的标量。校验器仍按原白名单读取 schema v1。
异常码元数据是审计线索，候选题还需要有相应的正文证据。

manifest 包含：

- schema 版本、精确权限范围、UTC 采集时间、记录数及文档数；
- JSONL 字节 SHA-256、元数据策略、原文/JSON 编码规则；
- 内容寻址 snapshot_id，以及 manifest 自身的完整性哈希；
- 真实代码所在路径、源文件 SHA-256、Git HEAD、dirty 状态、Python 版本
  和脱敏配置指纹。未提交修改以源文件哈希区分，不能只看 Git HEAD。

JSONL 按 Chunk ID 排序，采用固定 UTF-8/LF 编码和 JSON 字段顺序。同一范围、
数据和导出策略生成相同 JSONL 与 snapshot_id；时间和代码来源单独记录，
所以两次 manifest 文件可以不同。哈希是完整性校验，不是签名或授权证明。

如果写文件中断，目录可能留下不完整文件；没有通过验证的 manifest 就不是
可消费快照。使用新目录重试，不会覆盖或删除现有文件。

默认 storage 目录已忽略；两个固定产物文件名也加入 `.gitignore` 和
`.dockerignore`，覆盖自定义目录。改名、复制或显式 force-add 仍需操作者
自行保护，不应提交原始语料。

## 本地完整性校验

```powershell
.\venv\Scripts\python.exe -B -c "from pathlib import Path; from rag_app.eval_dataset.corpus import load_corpus_snapshot; from rag_app.eval_dataset.schemas import CorpusScope; m,rows=load_corpus_snapshot(Path('storage/evaluation/corpus/manual-001/corpus.manifest.json'),expected_scope=CorpusScope('default','default',('public',))); print(m['snapshot_id'],len(rows))"
```

校验器检查 schema、manifest 哈希、JSONL 字节哈希、快照 ID、scope、计数、
重复 ID、规范化编码及每行字段的一致性。只打印摘要，避免把正文写进日志。

## 测试

```powershell
.\venv\Scripts\python.exe -B -m unittest tests.test_eval_corpus
.\venv\Scripts\python.exe -B -m unittest tests.test_eval_corpus tests.test_evaluation tests.test_rerank tests.test_vector_store tests.test_online_processing tests.test_config tests.test_deployment_config
```

新增测试也可由 pytest 收集；当前环境未安装 pytest，不以此跳过 unittest。
没有安装或升级任何依赖。

真实只读集成测试需要由当前 shell 注入已有凭据的 `RAG_TEST_POSTGRES_DSN`，
并显式设置以下范围，collection 必须与当前 Settings 一致：

```powershell
$env:RAG_TEST_EVAL_COLLECTION = 'default'
$env:RAG_TEST_EVAL_TENANT = 'default'
$env:RAG_TEST_EVAL_TAGS = 'public'
.\venv\Scripts\python.exe -B -m unittest tests.test_eval_corpus_postgres -v
```

未设置这些变量时，这两项集成测试会明确 skipped；只有实际运行通过才可
声称集成验证完成。测试不会写 fixture 表：跨租户、标签、非 active 和孤立
关联案例使用 SELECT-only CTE。端到端测试验证两次导出相同，并比较前后
文档、Chunk、知识版本和激活指针表的计数及摘要。其他进程并发修改数据
可能导致该前后比较失败，应据实排查，不应放宽断言。

## 本阶段实际验证记录（2026-11-03）

- 当前 checkout 的 28 项新增单元测试通过；连同既有重点回归共 86 项通过。
- `venv/Scripts/python.exe -B -m unittest discover`：209 项，201 通过、8 跳过。
  6 项为未配置可写测试库的既有 API 集成测试，2 项为未配置显式范围时的
  新只读集成测试。没有据此声称可写 API 集成通过。
- 新只读集成另在显式 `default/default/public` 范围运行：2 项通过、0 跳过。
  使用当前代码和既有 PostgreSQL 映射端口，前后数据库摘要一致。
- 实际当前代码 CLI 导出 447 个 Chunk / 3 份文档；完整性验证通过。
  本机产物：`storage/evaluation/corpus/stage1-20261103-79e33ff2/`。
- snapshot_id：
  `sha256:d9f1fa7851b10fba00665e0478b88f136dc50879afef489ca15fee51ff704051`。
- 独立代码审查发现的 Unicode 分行、嵌套元数据和 manifest schema 问题均已
  用失败回归复现并修复。当前未安装 pytest，未升级任何依赖。
- 沙箱下既有 TestClient 曾卡住；允许本机通信后原测试和全量回归正常结束。
  保留既有 Starlette/httpx 弃用警告；不在此阶段升级或修改生产依赖。
