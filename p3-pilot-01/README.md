# P3-Pilot-01　RAG 检索评估探索性验证

22 条已签核 Gold × 447 个冻结 Chunk × 四组检索方式（BM25 / Vector / Hybrid / Hybrid+Rerank）
的一轮**可复现探索性评估**。

> 这是探索性 Pilot，**不是** 50 条 Gold 的正式 Benchmark。结论只能用于指出问题与下一步工作，
> 不能作为验收指标。

## 结论先行

| 方案 | Hit@1 | Hit@10 | MRR@10 | NDCG@10 | Recall@10 | p50 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A BM25 Only | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 90 |
| B Vector Only | 0.727 | 0.955 | 0.802 | 0.835 | 0.955 | 76 |
| C Hybrid | **0.909** | **1.000** | **0.931** | **0.943** | **1.000** | 125 |
| D Hybrid + Rerank | 0.727 | 1.000 | 0.799 | 0.838 | 1.000 | 3293 |
| *A2 BM25 全库（诊断）* | *0.727* | *0.955* | *0.802* | *0.841* | *0.955* | *112* |

三个必须同时说的结论：

1. **A 组全 0 是真实缺陷，不是脚本 bug**：生产 BM25 的候选池用
   `ORDER BY priority DESC, updated_at DESC LIMIT 20` 取候选，而本题库 447 个 Chunk 的
   `priority` 全为 50、`updated_at` 完全相同，排序完全无区分度；再叠加
   `ILIKE … OR`（中文二字组）几乎命中全库，22 题里只有 1 题的相关 Chunk 进得了候选池。
   把同一套 BM25 放到全库重算（A2），Hit@1 就是 0.727。**问题在候选筛选，不在 BM25 打分。**
2. **混合优于单路**：相对向量检索 Hit@1 +0.182、MRR@10 +0.129、NDCG@10 +0.108，
   22/22 命中 Top10。
3. **本轮配置下重排是负收益**：相对 Hybrid，Hit@1 −0.182、MRR@10 −0.132、NDCG@10 −0.105，
   召回不变，延迟涨到 20–26 倍（CPU）。6 题名次变化里 5 题变差、1 题变好。

详细分析、失败归因与限制见 [`docs/report.md`](docs/report.md)。

## 目录

```
p3-pilot-01/
├── README.md                    本文件
├── pilot_config.json            Pilot 运行配置（固定参数 + 复现命令）
├── run_pilot.py                 四组（+A2 诊断）评测运行器
├── verify_repeatability.py      两次运行的逐条一致性比对
├── analyze.py                   候选池诊断 / 失败归因 / 生成表格
├── build_gold_bundle.py         22 条 Gold 合并快照（只读拼接）
├── data/
│   ├── gold_22_merged.jsonl     22 条 Gold 合并快照（内容未改）
│   └── gold_provenance.json     来源路径、sha256、逐题 Chunk ID
├── runs/
│   ├── run1/                    主运行：run_config / preflight / rankings / metrics / fingerprints
│   ├── run2/                    复核运行（同一配置）
│   ├── repeatability.json       run1 vs run2 逐条比对结果
│   ├── analysis.json            逐题候选池诊断与失败归因
│   └── _scratch/                一次性排查脚本与冒烟产物（过程证据）
├── docs/
│   ├── report.md                评估报告（结论 / 分析 / 失败案例 / 限制）
│   ├── generated_tables.md      机器生成的表 1–6
│   └── run_log.md               实际执行、静态检查、测试与环境记录
└── checks/                      unittest / py_compile 原始输出
```

## 复现（四条命令）

前置：PostgreSQL 已发布到 `127.0.0.1:15432`，`.env` 里的 `RAG_OPS_POSTGRES_DSN` 指向容器名
`postgres`（脚本只在本进程内替换主机/端口，不改 `.env`）；`venv` 中已安装 `rerank` 可选依赖。

```powershell
# 1. 主运行（22 题 × 4 组 + A2 诊断）
.\venv\Scripts\python.exe -B p3-pilot-01\run_pilot.py --out-dir p3-pilot-01\runs\run1 --label run1

# 2. 复核运行（可选，但结论成立需要它）
.\venv\Scripts\python.exe -B p3-pilot-01\run_pilot.py --out-dir p3-pilot-01\runs\run2 --label run2

# 3. 一致性比对
.\venv\Scripts\python.exe -B p3-pilot-01\verify_repeatability.py `
  --run-a p3-pilot-01\runs\run1 --run-b p3-pilot-01\runs\run2 --out p3-pilot-01\runs\repeatability.json

# 4. 失败归因 + 重生成表格
.\venv\Scripts\python.exe -B p3-pilot-01\analyze.py `
  p3-pilot-01\runs\run1 p3-pilot-01\runs\analysis.json p3-pilot-01\docs\generated_tables.md
```

`run_pilot.py` 在语料与向量库不一致时会**直接失败退出**，不会在不可信语料上出数；
重排不可用时会把原因写进 `preflight.json` 的 `rerank_status` 并跳过 D 组，不会伪造结果。

## 数据边界

- 22 条 Gold、3 份 PDF、447 个 Chunk **未修改**；`data/gold_22_merged.jsonl` 是逐字节拼接的只读快照。
- 未处理 B23/B27 审核人字段，未签核第三批候选。
- 相关性标签、阈值、查询**均未为提高指标而调整**。
- 生产检索代码未改；唯一新增的库代码是 `rag_app/operations/retrieval_metrics.py`（指标）及其测试。
- 未执行 `git commit` / `git push`。
