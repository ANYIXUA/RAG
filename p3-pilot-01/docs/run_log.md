# P3-Pilot-01　执行与环境记录

本文件记录本轮**实际执行过的命令、静态检查、运行时间与结果**，供验收复核。
所有命令都在 `D:\AgentAIProgect\RAG` 下、用项目自带 venv 执行。

## 1. 环境

| 项 | 值 |
| --- | --- |
| OS | Windows 11 (10.0.26200) |
| Python | 3.12.14（`venv/Scripts/python.exe`） |
| 关键包 | psycopg 3.3.4、openai 2.41.1、torch 2.15.0+cpu、sentence-transformers 6.2.0、transformers 5.22.1 |
| 向量库 | PostgreSQL + pgvector，`127.0.0.1:15432`，`collection=default` |
| Embedding | DashScope `text-embedding-v4`，1024 维（`config/model.json`） |
| Reranker | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`，HF commit `1427fd652930e4ba29e8149678df786c240d8825` |
| 配置指纹 | `a79ed9000b6114da` |

### 本轮对本机环境做过的唯一安装

```powershell
.\venv\Scripts\python.exe -m pip install --disable-pip-version-check --no-input "sentence-transformers>=3.0.0" "torch>=2.0.0"
```

- 理由：`pyproject.toml` 已声明 `rerank` 可选依赖，但 venv 里没有安装，
  导致 `CrossEncoderReranker` 不可用。为了真实运行 D 组（而不是用模拟结果代替），
  按项目文档的方式安装该可选依赖。
- 结果：成功安装 torch 2.15.0+cpu / sentence-transformers 6.2.0 / transformers 5.22.1 等。
- 副作用：`click` 由 8.4.1 升级到 8.5.0（`typer` 依赖）。安装后完整测试套件仍全绿（见 §3）。
- 未安装/未升级任何项目运行时必需依赖，未改动 `pyproject.toml`。

> 环境备注：本次会话最初所有 `pwsh` 调用都被 DSH 的 Windows 沙箱挡在
> `sandbox-local windows-acl temp grant materialization failed`（工作目录 ACL 诊断结果为
> `NOT_THIS_CLASS`，即不是权限问题）。会话切到完全权限后恢复正常执行。
> 这是 agent 侧的环境问题，与本项目代码、以及本报告的任何结论无关。

## 2. 执行序列（含真实时间）

| 步骤 | 命令 | 时间（UTC） | 结果 |
| --- | --- | --- | --- |
| 依赖安装 | `pip install sentence-transformers torch` | — | 成功，torch 2.15.0+cpu |
| 指标单测 | `python -B -m unittest tests.test_retrieval_metrics -v` | — | 26 项全过 |
| 冒烟运行（3 组） | `python -B p3-pilot-01/run_pilot.py --out-dir …\_scratch\smoke --skip-rerank` | — | 通过；暴露 A 组全 0，转入 §4 诊断 |
| 主运行 run1 | `python -B p3-pilot-01/run_pilot.py --out-dir p3-pilot-01/runs/run1 --label run1` | 16:42:49 → 16:44:38（108.7 s） | 5 组（含 A2）全部完成 |
| 复核运行 run2 | `python -B p3-pilot-01/run_pilot.py --out-dir p3-pilot-01/runs/run2 --label run2` | 16:45:04 → 16:48:56（232.3 s） | 同上 |
| 一致性比对 | `python -B p3-pilot-01/verify_repeatability.py --run-a …run1 --run-b …run2 --out …repeatability.json` | — | 排序/分数/指标全一致 |
| 失败归因与表格 | `python -B p3-pilot-01/analyze.py p3-pilot-01/runs/run1 …/analysis.json …/generated_tables.md` | — | 生成表 1–6 |
| Gold 合并快照 | `python -B p3-pilot-01/build_gold_bundle.py` | — | 22 行，sha256 `9a4768df…` |

## 3. 静态检查与实际测试

```powershell
.\venv\Scripts\python.exe -B -m py_compile `
  p3-pilot-01\run_pilot.py p3-pilot-01\verify_repeatability.py p3-pilot-01\analyze.py `
  rag_app\operations\retrieval_metrics.py tests\test_retrieval_metrics.py
# exit code 0

.\venv\Scripts\python.exe -B -m unittest tests.test_retrieval_metrics tests.test_evaluation -v
# Ran 31 tests ... OK

.\venv\Scripts\python.exe -B -m unittest discover -q
# Ran 250 tests in 14.093s
# OK (skipped=8)
```

原始输出保存在 `p3-pilot-01/checks/`：

- `unittest_targeted.txt`：新增指标 26 项 + 既有评测器 5 项，共 31 项通过；
- `unittest_discover.txt`：全量 250 项通过、8 项跳过（跳过项为需要外部 PostgreSQL 凭据的既有集成测试，与本轮改动无关）；
- `py_compile.txt`：语法检查通过。

## 4. 排查记录：A 组为什么是 0

冒烟运行后 A 组 22 题全 0，先按"是不是用法错了"排查，结论是**生产实现本身的行为**：

1. `p3-pilot-01/_scratch/debug_bm25.py`：复现生产 keyword 候选筛选，
   发现 22 题里只有 B03 的相关 Chunk 出现在那 20 行候选里。
2. 直接查库确认候选排序键失效：

```sql
SELECT count(DISTINCT updated_at), min(updated_at), max(updated_at), count(DISTINCT priority)
FROM rag_knowledge_chunks WHERE collection_name='default' AND status='active';
-- (1, 2026-06-23 14:53:31.581201+00, 2026-06-23 14:53:31.581201+00, 1)
```

447 个 Chunk 的 `priority` 全为 50、`updated_at` 完全相同，`ORDER BY priority DESC, updated_at DESC LIMIT 20`
因此没有任何区分度。

3. 为把"候选池问题"与"BM25 打分问题"分开，新增诊断组 A2：
   用同一个 `_bm25_scores` 在全部 447 个 Chunk 上重算，得 Hit@1 0.727 / MRR 0.802。
   A2 **不计入四组对照**，只在 `metrics.json` 的 `supplementary_metrics` 与报告 §7.1 出现。

`p3-pilot-01/_scratch/` 下保留了这三个一次性排查脚本（`probe_db.py`、`debug_bm25.py`）
和冒烟运行产物，仅作过程证据，不属于交付接口。

## 5. 本轮未执行的操作

- 未 `git commit` / `git push`；
- 未修改 22 条 Gold、3 份 PDF、447 个 Chunk、`config/*.json`、`.env`；
- 未修改 `vector_store.py` / `rerank.py` / `online.py` / `evaluation.py`；
- 未处理 B23/B27 的审核人字段，未签核第三批候选；
- 未为了让指标好看而调整任何标签、阈值或查询。
