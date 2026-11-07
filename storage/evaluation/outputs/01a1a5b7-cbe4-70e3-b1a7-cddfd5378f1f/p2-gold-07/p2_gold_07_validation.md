# P2-Gold-07 静态验收报告

2026-11-04 · 只读校验，未修改冻结候选、PDF、Chunk、第一批与第二批 Gold。

## 一、执行命令

```powershell
cd 'D:\AgentAIProgect\RAG'
$env:PYTHONIOENCODING='utf-8'
.\venv\Scripts\python.exe 'storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f\p2-gold-07\.p2-work\static_check.py'
```

脚本位置：`p2-gold-07/.p2-work/static_check.py`。结果同时写入 `p2_gold_07_verify.json`（含每条断言的 `check`／`passed`／`detail`）。

## 二、运行记录（实际结果，未经修饰）

**运行 1（2026-11-04 23:49）**

```text
{"checks_total": 380, "checks_passed": 378, "checks_failed": 2, "counts": {"Accept": 8, "Revise": 5, "Reject": 2, "Needs Verification": 0}, "records": 15, "evidence_chunks": 12}
FAILED:
 - page_in_source_pages:B31:71a4f239a4fd7b69fdc74486
 - deliverable_present:p2_gold_07_validation.md
```

两处失败均非内容问题：

1. `page_in_source_pages:B31` —— 断言写法要求页码后必须跟「（印刷 …）」，而 B31 的 `source_pages` 只有裸页码「…标准.pdf 1」（单页封面没有印刷页码）。属校验脚本缺陷，已把断言改为按页码 token 匹配。
2. `deliverable_present:p2_gold_07_validation.md` —— 本报告尚未生成，属预期失败。

**运行 2（2026-11-05 00:07，修正断言后）**

```text
{"checks_total": 380, "checks_passed": 379, "checks_failed": 1, "counts": {"Accept": 8, "Revise": 5, "Reject": 2, "Needs Verification": 0}, "records": 15, "evidence_chunks": 12}
FAILED:
 - deliverable_present:p2_gold_07_validation.md
```

**运行 3（本报告落盘后，2026-11-05 00:16）**

```text
{"checks_total": 381, "checks_passed": 381, "checks_failed": 0, "counts": {"Accept": 8, "Revise": 5, "Reject": 2, "Needs Verification": 0}, "records": 15, "evidence_chunks": 12}
EXIT=0
```

断言总数由 380 变为 381，是因为本报告落盘后 `deliverable_present:p2_gold_07_validation.md` 这一条也计入并通过。

## 三、检查覆盖（381 条断言）

| 类别 | 条数 | 内容 |
| --- | ---: | --- |
| 冻结输入哈希 | 18 | 候选、语料、3 份 PDF、两批 Gold／metadata／rejected／unsigned、两份签核包与提案、两版工作簿、第二批 Manifest 自哈希 |
| 基础计数与 B23 状态 | 9 | 57 条候选、447 Chunk、3 文档、9＋13 条 Gold；B23 未签核、`gold_case_id` 为 null、不在任何 Gold 文件 |
| 编号与映射 | 19 | 15 条、ID 精确等于 B28–B42、无重复、标题与 `batch_id` 一致、与 `review.xlsx` 第 32–46 行逐条相等 |
| 候选未篡改 | 60 | B28–B42 的原始题、原始答、原始 Chunk 引用逐条与冻结候选相等；`pending_review` 状态未变 |
| 分类完整性 | 32 | 每条分类在四值枚举内、理由非空；总数 15；8／5／2／0 与报告一致 |
| 证据可追溯 | 111 | Chunk 存在、`chunk_text_sha256` 复算一致、源文档一致、页码出现在 `source_pages`、命中集合是证据集合的子集 |
| PDF 页核对 | 17 | 逐页重新取文，PDF 该页正文包含 Chunk 正文前 160 字 |
| 结构规则 | 35 | Reject 无检索目标／无修订；Accept 无修订且原答逐字见于证据；Revise 修订题答与理由齐全；无空证据 |
| 实质结论支撑 | 7 | B34「7.5」、B32 两节原文、B33 两类名称、B35 四项名称、B38 两块、B31 占位符唯一且无真实日期 |
| 人工字段为空 | 60 | 15 条 × `human_decision`／`human_reviewer`／`human_reviewed_at`／`human_comment` 全部为空字符串 |
| 无虚构指标 | 7 | 6 份 md 中不存在 `MRR／NDCG／Hit@K／延迟` 的数值断言；本目录不存在任何 `retrieval_gold_*` 导出文件 |
| 交付文件齐全 | 6 | 6 份报告／签核包均存在 |

断言不含「Benchmark 已运行」类检查，因为本轮未运行任何检索或评测服务。

## 四、关键冻结哈希（本轮复算，与既有登记一致）

| 对象 | SHA-256 |
| --- | --- |
| `candidates.jsonl`（57 条原始候选） | `31df78af2c96afd25f9221034ab47bbd965f7cb1a5e182dc8c1560cc3f9cf120` |
| `corpus.jsonl`（447 Chunk） | `5995ee6be2871ee7c553ce5fe2f3002a7938dbffedf0ec2b8fed28af8107f4d6` |
| 第一批 Gold（9 条） | `0ee8bbcd963f09c9b300209e8f1edcd93eb27ece1a077af877a37473568ec73a` |
| 第二批 Gold（13 条） | `5bfc8df96edd9574954fdb70c874a1fae186b3f442f077dcf92b478f9d103db9` |
| 第二批未签核（B23） | `4cd8ddc233c9a3f54b10fca609f388bf616d7653665d8a9accc5e69ca04e1cee` |
| `p2_gold_05_signoff_packet.md` | `5c9f5feaff9a281236d5ba680bf609c22c4a0c2f6355c349b3a0d10a3dd906a8` |
| `review.xlsx` | `df13e2755786cfb7f4d30e44d6323463ce6cbfe49c99a2b5ae87dfeec369d5ea` |
| `review_batch02_15_draft.xlsx` | `12f4a4acbb176590de732a7c92c0c620f03ac8376edda10ade52989a96c060b7` |

三份 PDF 的哈希（`9c8962e6…`、`fa3d041f…`、`21584b7e…`）同样在断言中逐份复算通过。本轮全部交付文件的哈希见 `p2_gold_07_manifest.json` 与 `p2_gold_07_manifest.sha256`。

## 五、本轮交付文件哈希

| 文件 | SHA-256 |
| --- | --- |
| `p2_gold_07_review_proposal.md` | `9c7fa87d37c2825b5072304f3469aae34879774c1954d76d3a7873bbd8286928` |
| `p2_gold_07_signoff_packet.md` | `cbcab3efa5a4109e10427770cdada777b3e24b4bee98f574513c42f33c7b27ff` |
| `p2_gold_07_b23_recheck.md` | `359e6feea98fddc2d8f41676d76b65bf02fd0d37722c8965b85cb44f3c62c6ef` |
| `p2_gold_07_reviewer_audit.md` | `a9b511b8fedd62a878bd21502ad927d83fe18aa5049953efe5916ee0683cd37e` |
| `p2_gold_07_duplicate_check.md` | `fdf0c7271ef2ef00380255c09107c31db5f685b2dfe7cd0233983dc8b258e3f9` |
| `.p2-work/inspect_batch03.py` | `f8e2051bf76143f0832005e9806442b3cc3053be01bf7f236e7e16e24809f4c5` |
| `.p2-work/analyze_batch03.py` | `7ea570f2a1c417e78004e8b482f261680c7d3c9053b9c4b6a8e839a6b6b93450` |
| `.p2-work/checks_batch03.py` | `3bfd652c688c9634a06d7624cd65b86b8a51e631b034e741dd39b2904b773a83` |
| `.p2-work/static_check.py` | `c2bf6a46063f04cfb2f433aa0f4585005ca5c41721dca6bd61eed70f2484c357` |
| `p2_gold_07_verify.json` | `12077c86d7d70fa6f13f2573930b2cc0d1b5a26f82e6b864ec42aa47a874c2d8` |

**可复现性**：初版校验脚本用 `set` 迭代生成 `counts`，导致 `verify.json` 的键序在不同进程间变化、字节哈希不稳定（首次构建 Manifest 后复算即发现 `verify.json` 哈希不匹配）。已改为固定元组顺序，连续两次运行输出哈希完全相同（`12077c86…c2d8`），Manifest 据此重建。

## 六、未解决的问题与限制

1. **人工签核全部为空。** 15 条 `human_decision` 均为空，因此本轮新增正式 Gold 为 0；这是设计状态，不是失败。
2. **B23 仍未签核。** `gold_case_id` 为 `null`，未计入 Gold；需人工回答 `p2_gold_07_b23_recheck.md` 第五节的四个问题。
3. **审核人字段不可具名。** 22 条已导出 Gold 的 `human_reviewer` 为占位值（B27 另作 `systemsystem`），本轮未修改，详见 `p2_gold_07_reviewer_audit.md`。
4. **三条 Revise 改变检索目标页**（B32：2→7；B33：2→8；B35：3→15）。若人工只接受「不改变目标」的修订，应改判 Reject。
5. **B38 事实与 B40、B41 重叠**，且两目标为 OR，评分无法验证「同时命中」。
6. **多目标 OR 的固有限制**沿用既有披露：B14／B15／B25 与本轮 B38 同属此列。
7. **未运行检索或 Benchmark**，因此没有任何 MRR／Hit@K／NDCG／延迟结论；本报告不含性能数字。
8. **PDF 解析误差**：表格列归属仅对 B34 用文字坐标复原；其余表格题按块内文本顺序判断，仍存在解析顺序导致的误读可能，故 B28／B29 的「同值不同行」已单独披露。

## 七、结论

- 断言总数 **381**，最终通过 **381**，失败 **0**（运行 3，见第二节）。
- B28–B42 共 15 条，无遗漏、无重复 ID，分类 8 Accept／5 Revise／2 Reject／0 Needs Verification。
- 冻结数据与两批已导出 Gold 未被修改。
- 交付物为**待人工逐条签核的证据包**，不是已批准的 Gold 数据。
