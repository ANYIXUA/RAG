# P6-E2E-Run-01 失败分析

以下为同模型自动评审及Silver证据代理诊断，不是人工根因定论。每题仅有一个主分类；具体维度/引用/召回信息见failure_diagnostics.jsonl。检索证据未命中并不排除其他正确证据。

## 检索未召回Silver标注证据（代理诊断）：0/10

## 已召回但未完整进入LLM上下文（代理诊断）：0/10

## 证据进入上下文但答案错误：0/10

## 答案遗漏关键条件或步骤：0/10

## 生成内容缺乏证据支持/疑似幻觉：0/10

## 引用与实际证据不符：0/10

## 模型调用或执行异常/超时：10/10

- **p6s-0001**：计日工表中，综合单价（元）对应的表格列名称是什么？
  - RAG回答：回答生成失败，已保留本次检索到的知识来源。请根据来源片段人工核验处理建议，必要时转人工闭环。
  - 评分依据：{"answer_correctness": null, "faithfulness": null, "completeness": null, "citation_correctness": null, "no_answer_behavior": null}
  - Trace：cases/p6s-0001.json

- **p6s-0002**：索赔与现场签证计价汇总表中，签证及索赔依据的描述内容是什么？
  - RAG回答：回答生成失败，已保留本次检索到的知识来源。请根据来源片段人工核验处理建议，必要时转人工闭环。
  - 评分依据：{"answer_correctness": null, "faithfulness": null, "completeness": null, "citation_correctness": null, "no_answer_behavior": null}
  - Trace：cases/p6s-0002.json

- **p6s-0086**：在空调设备季度维护中，如何确保制冷剂压力和制冷效果正常？
  - RAG回答：回答生成失败，已保留本次检索到的知识来源。请根据来源片段人工核验处理建议，必要时转人工闭环。
  - 评分依据：{"answer_correctness": null, "faithfulness": null, "completeness": null, "citation_correctness": null, "no_answer_behavior": null}
  - Trace：cases/p6s-0086.json

## 自动评分无法可靠判断：0/10

## 未发现上述失败（不是人工正确性确认）：0/10
