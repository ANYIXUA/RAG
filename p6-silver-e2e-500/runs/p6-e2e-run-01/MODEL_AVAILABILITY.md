# 当前 qwen-turbo 可用性诊断

2026-11-05（Asia/Shanghai）。当前配置的精确模型ID `qwen-turbo` 在本账号不能调用。

## 直接证据

- 10条Smoke（五类各2条），30次生成尝试全部429 limit_requests，无真实LLM成功输出。
- 后续单次最小请求仍429，无Retry-After；Request ID见service_diagnostic.json。
- 同一Key的GET /models成功，返回183项，精确qwen-turbo缺席；qwen3.8-flash等在列表内。
- text-embedding-v4实际调用成功。不能把此故障说成模型回答错误、检索质量失败或账号鉴权全部失效。

## 官方资料及证据边界

1. [阿里云OpenSearch官方下线公告](https://help.aliyun.com/zh/open-search/search-platform/product-overview/announcement-intelligent-open-search-opensearch-ai-search-open-platform-partial)：明确qwen-turbo列入下线范围，推荐qwen3.8-flash。该文针对OpenSearch且提及百炼下线，不用其自动路由规则推断本项目DashScope也会自动路由。
2. [百炼模型下线机制](https://help.aliyun.com/zh/model-studio/model-depreciation)：下线过程中会缩减QPM/TPM，停止服务后不能返回结果。公告列表近期多次调整，未从公告正文核实本账号具体生效日期。
3. [百炼错误码](https://help.aliyun.com/zh/model-studio/error-code)：limit_requests通常对应请求频率限制。单独429不足以证明全球模型下线；本报告结合模型清单缺席和官方公告判断当前旧配置不可继续依赖。

## 可供确认的后续方案（未执行）

允许迁移时，以列表中的qwen3.8-flash为候选，先核实其当前价格和最小真实调用。仅评测运行选择生成模型，保留Hybrid/Embedding/Prompt/推理上限与所有冻结数据；如目标模型不兼容原参数，先明确报告，不静默调参。重新保存独立运行配置和Smoke分组，原失败30次及10个终态保留，不清空、不覆盖、不追加到已耗尽的单题尝试。总预算仍¥20。

此方案会改变本轮生成模型，需要用户明确确认。当前未改模型，正式500条尚未执行。
