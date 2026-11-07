# P2-Gold-07 B27 审核人字段核对报告

2026-11-04 · 只核对与记录，**未修改任何已导出 Gold、Manifest 或签核包**。

## 一、问题来源

P2-Gold-06 在导出第二批 Gold 时已察觉一处异常：B27 的 `human_reviewer` 值为 `systemsystem`（疑似重复录入），其余记录为 `system`。本轮把范围从单条扩到「第一批 + 第二批 + 两版工作簿」，核对结论如下。

## 二、逐项核对

### 1. B27 原始人工签核记录

`p2-gold-05/p2_gold_05_signoff_packet.md` 第 395 行所属段落：

```text
human_decision: 接受原题
human_reviewer: systemsystem
human_reviewed_at: 2026/11/04
human_comment: 已核对原始PDF，确认原题。
```

`human_decision` 合法（`接受原题`），日期与备注齐全，唯一异常是审核人字段拼写。该值出现在 `human_reviewer` 冒号之后、无空格，`systemsystem` 只能读作 `system` 的重复拼接，无法读出具名身份。

### 2. 第二批 Gold 元数据

`p2-gold-06/retrieval_gold_batch02_metadata.json`：13 条 Gold 记录中，12 条 `human_reviewer: "system"`，B27 一条 `"systemsystem"`（第 738 行）。同一文件第 761–762 行已写入警告：

```json
"signoff_warnings": [
  "human_reviewer 值为 'systemsystem'，非规范值 system；按原样保留，建议在最终 50 条定稿前更正。"
]
```

即异常已被记录，未被静默修正。

### 3. `signoff_warnings` 覆盖面

- 只出现在 `retrieval_gold_batch02_metadata.json`，是对 B27 单条的说明。
- `p2-gold-04/retrieval_gold_batch01_metadata.json`（9 条）**没有** `signoff_warnings` 字段，但 9 条 `human_reviewer` 全为 `"system"`，同为占位值。
- `p2-gold-06/p2_gold_06_verify.json` 第 3815 行把 B27 的 `"reviewer": "systemsystem"` 原样固化进校验结果，未做归一化。

### 4. 两版工作簿中的人工字段

| 工作簿 | 审核人列（G） | 审核意见列（H） | 说明 |
| --- | --- | --- | --- |
| `review.xlsx`（57 条主工作簿，sheet「候选审核」） | 第 5–61 行全部为字面量 `human` | 第 5–16 行（B01–B12）有意见，第 17–61 行（B13–B57）为空 | `human` 是模板占位，不是审核人 |
| `p2-gold-05/review_batch02_15_draft.xlsx` | 同样全部为 `human` | B13–B27 行有 AI 草稿意见（如「B23 · AI Revise…」），B28–B57 为空 | 草稿意见来自 AI，不是人工签核 |

两版工作簿都**没有**任何具名审核人；`system`／`systemsystem` 只存在于 Markdown 签核包及其派生元数据。

### 5. 其他 Gold 是否有同类问题

| 集合 | 条数 | `human_reviewer` 取值 | 异常 |
| --- | ---: | --- | --- |
| 第一批 B01–B12（`p2-gold-03_signoff_packet.md`） | 12 | 全部 `system` | 占位值 |
| 第二批 B13–B27（`p2-gold-05_signoff_packet.md`） | 15 | 14× `system`，1× `systemsystem`（B27） | 占位值＋拼写异常 |
| 已导出 Gold 合计 | 22 | 21× `system`，1× `systemsystem` | 同上 |

结论：`systemsystem` 是 **B27 独有**的格式缺陷；但「审核人不可具名」是 **22 条 Gold 全体共有**的更深层问题。P2-Gold-04 的验收记录已明确写过「保留 12 条原始 `human_reviewer` 值 `system`」（`p2-gold-04/p2_gold_04_validation.md` 第 7 行），说明前序阶段是有意保留占位符的。

## 三、能否确认真实审核人

不能。核对范围内没有任何字段、备注、工作簿单元格或日志能指向具名个人：

- 工作簿只有 `human` 占位；
- 签核包只有 `system` 系列；
- `human_comment` 是内容备注（「已核对原始PDF」），不含身份信息；
- 元数据 `review_source` 只记录来源文件、章节、哈希与工作簿行号。

因此本轮**不推断、不编造**任何身份，也不把 AI／脚本／系统标记替换成人工审核人。**处理原则：保留原值，继续报告警告。**

## 四、影响范围

1. **对 Gold 内容：无影响。** 22 条的题、答、证据、目标块均不受审核人字段影响。
2. **对签核效力：有影响。** 22 条记录的 `human_reviewer` 都不是可核验的身份，若对外声称「逐条人工签核且可追溯至审核人」，目前的证据链只能证明「签核包里有决定、日期、备注」，不能证明「谁签的」。
3. **对 B27：仅字段格式。** `systemsystem` 不改变「接受原题」的决定，也不改变其 Gold 内容。
4. **对第二批 13 条入库判定：无影响。** 入库条件是四个人工字段非空且决定取值合法，审核人字段只要求非空。

## 五、最小修改方案（待授权，本轮未执行）

按代价从低到高排列，三者互斥：

**方案 A：零改动（建议默认）**
保留 `system`／`systemsystem` 原值，继续在元数据写 `signoff_warnings`，并在最终 50 条定稿报告里声明「审核人字段为占位值，不具备具名追溯」。代价 0；缺点是签核链仍然不可具名。

**方案 B：只修 B27 的拼写**
把签核包 B23…B27 段落中 B27 的 `human_reviewer:systemsystem` 改为 `human_reviewer:system`。**不建议**：这只是用占位符替换占位符，且会覆写原始签核记录，还要求同步重算 `p2_gold_05_signoff_packet.md` → `retrieval_gold_batch02_metadata.json` → `gold_batch02_manifest.json` → `gold_batch02_manifest.sha256` 的整条哈希链，改动面远大于收益。

**方案 C：补录真实审核人**
由用户提供真实身份后，统一改写两份签核包的 `human_reviewer`，再重新生成两份 metadata、两个 Manifest 与其 `.sha256`。影响：22 条记录元数据、4 个 Manifest 相关文件全部换哈希；需要重新跑一次与 P2-Gold-04／06 同规格的静态验收。**必须经用户明确授权后才能动手。**

无论选哪个方案，本轮都保持原样。

## 六、本轮新增的防回归记录

为避免后续「悄悄改掉」，本轮在本目录留下冻结哈希（同时写入 Manifest 的 `inputs_sha256`）：

| 文件 | SHA-256（本轮读取时） |
| --- | --- |
| `p2-gold-05/p2_gold_05_signoff_packet.md` | `5c9f5feaff9a281236d5ba680bf609c22c4a0c2f6355c349b3a0d10a3dd906a8` |
| `p2-gold-06/retrieval_gold_batch02_metadata.json` | `a12a31ab2f69c163b6053e66f503d4c28ce48d9322dcebaca9065a996d5211a3` |
| `p2-gold-04/retrieval_gold_batch01_metadata.json` | `6aa3b20a867be6c2718cc6621b57b10f42029f883e14ac6be314c44a4a703e39` |
| `review.xlsx` | `df13e2755786cfb7f4d30e44d6323463ce6cbfe49c99a2b5ae87dfeec369d5ea` |
| `p2-gold-05/review_batch02_15_draft.xlsx` | `12f4a4acbb176590de732a7c92c0c620f03ac8376edda10ade52989a96c060b7` |

（上表第二行为 `outputs_sha256` 中的既有登记值，本轮复算一致；其余为实际读取值。）
