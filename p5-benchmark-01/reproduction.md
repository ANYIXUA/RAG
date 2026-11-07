# P5-Benchmark-01 复现说明

在项目根目录使用原 venv。只做检索，不做生成评分。正式配置在任何 Holdout 检索前写入 preregistered_config.json；不得按结果调整。run1 是事前指定的正式报告运行；run2 仅检验一致性，不择优。

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:PYTHONHASHSEED='0'
.\venv\Scripts\python.exe -B p5-benchmark-01/run_benchmark.py --preflight
.\venv\Scripts\python.exe -B p5-benchmark-01/run_benchmark.py --run run1
.\venv\Scripts\python.exe -B p5-benchmark-01/run_benchmark.py --run run2
.\venv\Scripts\python.exe -B p5-benchmark-01/summarize.py
```

需要项目原配置及凭据、本机 127.0.0.1:15432 PostgreSQL、原冻结语料与本地 CrossEncoder 快照。首次运行会将 28 条查询发送到原 DashScope text-embedding-v4 接口生成向量。后续共用 query_vectors.json 中的精确向量；远端服务未暴露不可变权重版本，不能保证未来重新向量化产生相同值。缓存和输入哈希用于精确重放。

runner 拒绝覆盖已有运行目录。异机复现应在独立副本保留冻结输入及向量缓存，并使用新的输出根目录；本次交付目录视为归档。生产检索与指标函数直接复用 P3；适配器仅更换数据加载/角色检查、移除 A2 诊断组、缓存向量、截获重排调用并修正继承的 Pilot 文案。算法和计分公式不变。

延迟是预热后、串行、每题依次 A/B/C/D 的检索耗时；D 包含检索和重排，不含查询 Embedding、模型加载或初始化。每组28次，p50/p95线性插值；不是端到端延迟，不是严格控制硬件/缓存顺序的性能实验。模型初始化和向量生成包含在 wall_seconds 中，但不包含在检索分位数中。重复运行不要求延迟相等。

遇到基础设施失败立即终止，不删题、不调整分母；所有有效方案均须28题。预检脚本早期格式适配错误及沙箱本机连接限制记录在 preflight_failure.json，均发生在任何 Holdout 检索前；成功预检另存 preflight_pass.json。

补充审计：environment_details.json保存数据库/pgvector版本、CPU信息和本地模型文件哈希；database_vectors.json保存两轮结束后的447条实际语料向量。历史P3未保存语料向量哈希，本次不声称历史远端权重或数据库向量逐位相同。两个定时运行期间未并行执行数据库探针。

run*.log保留原评估器控制台输出，控制台中的Pilot标识和fingerprints对应适配器修正文案前的中间文件。最终文件以各run目录内fingerprints.json及根目录sha256_manifest.json为准；适配器只修正文案与元数据，没有改动指标数值或排序。该处理逻辑完整保存在run_benchmark.py。
