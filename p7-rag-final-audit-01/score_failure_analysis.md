# P7 十条最终评分失败逐条归因

状态：`AUDIT_PREPARED`；人工状态：`HUMAN_REVIEW_PENDING`。这是AI对已保存记录的初步归因，不是人工签核，不修改原始分数，也不将失败评分raw中的部分分数补入正式汇总。

## 结论与证据

十题的RAG执行均成功，失败发生在后续评分阶段。原始评分失败18条中有8条历史恢复，最终仍失败的10条才是本文分母。每题3次Judge请求，共30次；29份持久响应，其中5份因`finish_reason=length`造成JSON截断，23份可解析JSON因普通题正确性`null`被校验器拒绝，1份因不适用维度理由为空被拒绝；另外1次只有请求、没有持久响应。

按本文互斥主归因：格式错误2题、评分逻辑问题4题、Judge声称证据不足4题、可确认的纯调用错误0题。p6s-0041另有1次调用结果证据缺失，不能据此认定服务端故障、超时或请求未执行。类别是审计解释，不是历史系统新增状态；混合原因如下逐题保留。

`score_failure_evidence.json` 对每条失败记录保存：原始failure对象（包含原始errors数组）、30次request ID与历史路径、request/response SHA-256、真实prompt说明、max_tokens、finish_reason、usage、response.error、完整未经删节的`raw_content_exact`、可解析JSON及独立校验错误。缺失响应明确为null，不补造响应。历史完整请求及响应仍在原 `api_calls/`。

评分器的关键冲突是：评分prompt允许“确实无法判断用null”，但`validate_judge`对普通可回答题的四个质量维度要求非null，只豁免unanswerable和p6s-0473正确性。该契约冲突导致“模型返回了有理由的null”被记成技术评分失败。它与答案本身是否错误是两件事。

## 逐题归因

| case_id | 主归因 | 原始errors | 原始响应支持的解释 |
|---|---|---|---|
| p6s-0023 | 格式错误 | JSONDecodeError×3 | 三次均length，JSON字符串未闭合；输出达到1600 token上限 |
| p6s-0037 | Judge声称证据不足 | ValueError×3 | 三次正确性null，理由是答案引用不存在的[6]；理由同时承认上下文[1]存在MCS15/MCS14事实 |
| p6s-0041 | 格式错误，兼调用证据缺失 | 空数组`[]` | 前两次length截断；第三次请求637b4720ef444598809dab2eb5155cfd无持久响应。原始errors为空不等于从未发生错误 |
| p6s-0053 | 评分逻辑问题 | ValueError×3 | 前两次无证据声称利润歧义，第三次将p6s-0473工日歧义套入本题，三次正确性null |
| p6s-0157 | 评分逻辑问题 | ValueError×3 | 前一次称本题费用歧义，后两次将114工日歧义写到p6s-0157，三次正确性null |
| p6s-0195 | Judge声称证据不足，兼逻辑可疑 | ValueError×3 | 一次称实际上下文未支持交互式网络电视故障步骤；另两次混入工日/参考不一致措辞，三次正确性null |
| p6s-0230 | Judge声称证据不足 | ValueError×3 | 三次认为上下文未定义/未提综合单价构成，正确性null |
| p6s-0389 | Judge声称证据不足 | ValueError×3 | 三次认为上下文未直接提树叶遮挡处理，正确性null |
| p6s-0420 | 评分逻辑问题，兼格式错误 | ValueError×3 | 前两次错引p6s-0473工日歧义、正确性null；第三次正确性有值，但no_answer_behavior.reason为空字符串 |
| p6s-0454 | 评分逻辑问题 | ValueError×3 | 前两次错引p6s-0473歧义；第三次说本题数据一致但线缆连接判断错误，却仍给正确性null |

“Judge声称证据不足”仅转述失败响应，不等于人工确认实际没有证据。尤其0037的响应把引用编号失效混同为答案事实不可判断，不能据其null认定内容错误。0053、0157、0420、0454的跨题歧义理由显示疑似提示词例外串扰；本审计没有改变prompt或重评分来验证因果。

### p6s-0023：三次格式截断

- judge-1 `8278daada6bb46f08e2a494d65930919`：`Unterminated string starting at: line 10 column 17 (char 1713)`。
- judge-2 `db64044171bb41a1bfbc59c657099f35`：`Unterminated string starting at: line 10 column 17 (char 1724)`。
- judge-3 `51d01cb6b0d9431ba48b51e6654ea6e2`：`Unterminated string starting at: line 10 column 17 (char 1730)`。

三次finish_reason均为length；这是格式可用性失败，不能根据截断JSON推导整题评分。

### p6s-0037：引用错误触发null

- judge-1 `63f748c469ac455fbd6d6164ca338343`：理由承认“实际上下文[1]明确指出‘须支持MCS15，推荐支持MCS14’”，但因回答引用[6]而不给正确性结论。
- judge-2 `38a47c5e217842138cc2835153d5b913`：仍以不存在的[6]导致事实来源不可靠为由给null。
- judge-3 `de5ff4ff32da4bed901d5fe1faa95edf`：仍以[6]未映射到任何chunk为由给null。

三次stop，JSON可解析；独立校验均为`answer_correctness: judge required score missing`。这题实际有5个[6]标记、sources只有4条，所以同时属于无效引用风险；raw中疑似幻觉标志不纳入18条已成功评分集合。

### p6s-0041：截断与第三次结果缺失

- judge-1 `b18e9f60a5704b5c94fa0c882dc3ffc8`：length；`Unterminated string starting at: line 20 column 17 (char 1668)`。
- judge-2 `0f5d418fea6645ba9c8e729791c4a349`：length；`Unterminated string starting at: line 14 column 15 (char 2306)`。
- judge-3 `637b4720ef444598809dab2eb5155cfd`：有request，无response文件；没有可读raw、usage、finish_reason或调用异常对象。

不得将第三次补记为超时、预算错误或HTTP错误。可确认的是持久化证据缺失；根因未判定。

### p6s-0053：歧义理由跨题

- judge-1 `f6d1855657d04b1ea5a2e50c0dd3801d`：“p6s-0053利润值存在歧义，无法判断”，evidence为空。
- judge-2 `1dc098bb5b6c4e6bb7835c3f30b78d3c`：“p6s-0053利润值歧义，无法判断”，evidence为空。
- judge-3 `7517c9891c824c9e964183632517797b`：“p6s-0473工日歧义，无法判断”，evidence为空。

三次stop、正确性null，被普通题规则拒绝。0473例外不能自动扩展到0053。

### p6s-0157：114工日例外串入本题

- judge-1 `d7a62d4820a544d6bdac8d4d2736ec33`：“p6s-0157费用歧义，无法判断”。
- judge-2 `4ae701c0e8de411eb8ea6ba3cebdfc2d`：“p6s-0157的114工日存在解析歧义，不得因与此参考不一致而判错”。
- judge-3 `e00f6389d98348eba3e5b45df89d4347`：“p6s-0157的114工日存在解析歧义”。

三次stop、正确性null且evidence为空。后两条的措辞复用了全局0473提示中的特殊豁免，属于疑似评分逻辑串扰。

### p6s-0195：证据不足与不相干措辞混合

- judge-1 `c41afbc4289f4c54a22ebe0d9dc3f570`：“p6s-0195工日无解析歧义，但参考不一致”。
- judge-2 `b1f718ea027e47e5a004d25b8897cf0e`：“上下文未明确支持‘交互式网络电视’故障处理步骤”。
- judge-3 `0a7c707c1d4043a889eac863a78cb1b6`：“p6s-0195无解析歧义，但实际答案未完全匹配参考”。

三次stop、正确性null且evidence为空。这里不以“未匹配参考”直接判答案错误，因为Silver参考不是人工真值。

### p6s-0230：构成定义未得到Judge确认

- judge-1 `e09e316399054d55922a69b7a6fb8d14`：“上下文未直接定义综合单价构成”。
- judge-2 `c6e5cb21714041d9895d68c4466c4f52`：“未提及综合单价构成”。
- judge-3 `40c3db2a5f2249a99e2bb16a5954b032`：“未提及综合单价构成”。

三次stop、正确性null且evidence为空。该评分失败由null与校验必填冲突直接解释，实际证据充分性仍待人工复核。

### p6s-0389：树叶遮挡内容未得到Judge确认

- judge-1 `2dd94b0ef69b4de9b8eb6f4a1cda5b16`：“上下文未直接提及树叶遮挡处理”。
- judge-2 `79df1dcb518545bb80a635f6ce9c84fc`：“上下文未提树叶遮挡处理”。
- judge-3 `29e2ffe68d3d49ad937666ed4ac6f0b5`：“上下文未直接提及树叶遮挡处理”。

三次stop、正确性null且evidence为空。同样不能从评分未完成自动得出答案失败。

### p6s-0420：两次例外串扰后一次空理由

- judge-1 `d98413f4698d456fa15ee2e8948926ea`：“p6s-0473工日歧义，无法判断”；正确性null。
- judge-2 `5e989e6eca71494aa3e47397e20bb455`：相同跨题理由；正确性null。
- judge-3 `cf4e5d34f3ca4cab87f357599b1dc897`：正确性已非null，但no_answer_behavior为`{"score":null,"reason":"","evidence":""}`。

第三次JSON语法正确，失败是对象字段契约要求reason非空；因此历史错误为`judge field missing`。不能把第三次原始分数偷偷并入490条有效评分。

### p6s-0454：跨题理由与判分逻辑不一致

- judge-1 `4f850ef3187b4d0bb1c66e5c5bc0d666`：“p6s-0473工日存在解析歧义”。
- judge-2 `471d8c5fb078465f9b60dc3b63826b99`：“p6s-0473工日歧义，无法判断”。
- judge-3 `bbb6f71cde0e491787b6209b3acc22b6`：“p6s-0454人工费与消耗量数据一致，但线缆连接判断错误”，并提供WH23103001表格摘录。

三次stop且正确性null。第三次已给出具体判断却仍不给分，不应将其等同于传输调用失败或人工证据结论。

## 接受与不接受的推论

可确认的技术事实是5次截断、23次必需维度null、1次空reason、1次响应未持久化，以及原始490/500评分成功率。跨题歧义、引用事实混同和证据不足属于有raw支持的AI初步解释；实际答案质量及证据支撑范围必须进入人工审核。没有新增重试、恢复、重新评分、改模型或修改历史评分文件。
