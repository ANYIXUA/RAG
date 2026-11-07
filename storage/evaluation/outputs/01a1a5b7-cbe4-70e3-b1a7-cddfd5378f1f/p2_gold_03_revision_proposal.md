# P2-Gold-03 修订方案

2026-11-04 · AI 修订建议，供人工签核

基线提交 `7810bfb`。候选使用 `p1-20261104-structured/candidates.jsonl`，证据来自 `p1-20261104-v2` 语料快照（`sha256:eedd1783956ca582c1cdfbbdad486fdf1554c7dab79681bba0675eec47089fce`，3 份文档、447 个 Chunk）。原始引文及定位见 [P2-Gold-01 证据包](first-batch-evidence.md)，既有初审见 [P2-Gold-02 初审](p2_gold_02_review_proposal.md)。

## B07 证据链

| PDF 物理页（印刷页） | Chunk ID | 证明内容 |
| --- | --- | --- |
| [61（56）](../../../../data/中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf#page=61) | `c120df3a569ae215d69183ac` | A.2 标题明确对象为光路由终端。页末“3. 二维码要求”列出（1）颜色和（2）黏贴位置。 |
| [62（57）](../../../../data/中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf#page=62) | `38ea5e749604f43f5f040901` | 无新节标题，接续（3）尺寸要求，明确最小尺寸、公差和正方形，附图标示 17.0 mm × 17.0 mm。 |

两块来自同一文档 `a2053ec18f1415e4912c510f`、版本 `v_ab72ce00c904f060`，快照 Chunk 索引 60、61。第 62 页原件、Chunk 全文和元数据均未写出“光路由终端”，单独只能证明尺寸条款。两块合读可证明对象及答案，现有快照无已知证据缺口，达到提交人工签核的准备条件。

- `evidence_chunk_ids` 建议为 `[c120df3a569ae215d69183ac, 38ea5e749604f43f5f040901]`。
- `retrieval_relevant_chunk_ids` 建议为 `[38ea5e749604f43f5f040901]`。第 61 页用于归属证明，可作为背景补充。它单独出现时无法回答尺寸题。

## B12 题面和证据

P2-Gold-02 的问题给出了两个知识类别，其中“网优”直接提示答案。题面按等级、工作内容和知识条目编号定位，两个答案短语均未出现在新问题中。限定编号还有一个原因，中级 3.2 同时列出 3.2.2 通用 WLAN 知识和 3.2.3 网优及软件知识。泛问中级对 WLAN 的知识要求时，只列 3.2.3 会遗漏 3.2.2。

| PDF 物理页（印刷页） | Chunk ID | 原件表格定位 |
| --- | --- | --- |
| [16（15）](../../../../data/智慧家庭装维工程与管理职业技能等级标准.pdf#page=16) | `48ecc091e26caaa3ccbd3be5` | 初级，3.2 基础网络质量检测，知识要求 3.2.2 为“无线局域网相关基础知识”。 |
| [18（17）](../../../../data/智慧家庭装维工程与管理职业技能等级标准.pdf#page=18) | `c10a8b3b89210595f9880fc6` | 中级，3.2 基础网络优化，知识要求 3.2.3 为“无线局域网网优及软件基础知识”。同号技能条目是覆盖优化能力。 |

两块来自同一文档 `5256824b6b72b3f03d9c7a2c`、版本 `v_dcf78195a87f01f4`。第 18 页快照把“知识”拆为“知 识”，按原件还原。第 18 页虽也含通用 WLAN 短语，无法证明该短语在初级 3.2 的归属。第 16 页也无法证明中级 3.2.3，故 `evidence_chunk_ids` 与 `retrieval_relevant_chunk_ids` 都建议用两块。

将最终题面与其他 56 条逐一比较。大小写归一并去除空白及标点后，字符二元组 Jaccard 最大为 0.1310，最近题问高级阶段业务开通与运维的实操权重。去掉固定文档引导语后最大为 0.0517，最近题问 WH23122 发电设备检修内容。另以 WLAN 相关术语及共享引文筛查，未发现同问点候选。结论限于本次候选池和上述查重方法。

## 检索评分口径与 Gold 构建建议

候选和审核表只有 `supporting_chunk_ids`。评测器使用独立的 `expected` 列表，`ExpectedTarget` 支持 `source`、`section_title`、`text_contains`，当前没有直接的 Chunk ID 或证据角色字段。单个目标内填写的字段需同时匹配，目标之间是任选其一。代码中 `_evaluate_once` 对 `answer.sources` 调用 `_first_match_rank`，首个匹配即返回，Hit 取是否存在匹配，MRR 取首个匹配名次的倒数再聚合。[评测代码](../../../../rag_app/operations/evaluation.py#L446)

- B07 进入后续 Gold 构建时，可在签核材料保留两块证据，只用第 62 页作为检索目标。沿用现有结构时，用文档、页级 section 和稳定的尺寸文本组合定位，避免只填文档名而命中背景页。签核证据集合与检索目标集合可在 Gold 审核材料中分别留档。
- B12 若登记两个 `expected` 目标，仅第 16 页或仅第 18 页匹配时都能记为 Hit。完整召回要求同一个 Top-K 同时包含这两个必需证据。应分别报告任一相关块命中与双证据覆盖。需要核查覆盖时，可在后续工作中按两个证据角色分别核对同一结果列表。若通过 `text_contains` 配置，需结合页级 section 或初级专属上下文，避免中级 3.2.2 误匹配初级目标。

## 修订版本记录

7 个修订提案以原 `candidate_id` 作为 `parent_candidate_id`，通过批次编号定位。此阶段无需分配新 ID。下方原问题、答案、引用来自候选 JSONL。除 B07、B12 外沿用 P2-Gold-02 方案，B06 采用该轮给出的规范与节号锚定版。

### B01

```text
batch_id: B01
parent_candidate_id: sha256:9631dde730749e95e2c74da24726dd1d8e743b1242d189ac76034732a01fa5e9
original_question: 管道线路的人（手）孔检修周期是多久？
original_answer: 半年
original_supporting_chunk_ids: [831af7c41fd776db6b5b3ff9]
question: 非高速公路场景下，管道线路的人（手）孔检修周期是多久？
proposed_answer: 半年（高速公路中人孔的检修按需进行，不适用半年周期）。
evidence_chunk_ids: [831af7c41fd776db6b5b3ff9]
```

### B02

```text
batch_id: B02
parent_candidate_id: sha256:6858125cbf5e8170a757c8a812aca9d1a9b2dd23347c59d5061af9a7c0d982f0
original_question: 波分复用器1:2的测试单价是多少？
original_answer: 29.18
original_supporting_chunk_ids: [92108b5bb6dcc5b2227d531c]
question: 在维护分项作业表 10.3.3.4（WH23104 安装、测试波分复用器）中，测试波分复用器 1:2（项目编码 WH23104003）的综合单价是多少（元/个）？
proposed_answer: 29.18 元/个。
evidence_chunk_ids: [92108b5bb6dcc5b2227d531c]
```

### B04

```text
batch_id: B04
parent_candidate_id: sha256:4d263ebb839f347941da0bd9c9d0c11533925443e6a26519593ad7628f6c29e6
original_question: 在实操技能权重表中，高级阶段的安全作业权重是多少？
original_answer: 10
original_supporting_chunk_ids: [02c18b66c8c7d17fa1fb910e]
question: 在 7.2 智慧家庭装维工程与管理实操技能权重表中，技能等级为高级时，“安全作业”项目的权重是多少（%）？
proposed_answer: 10%
evidence_chunk_ids: [02c18b66c8c7d17fa1fb910e]
```

### B06

```text
batch_id: B06
parent_candidate_id: sha256:bfd1eea2e2dfb6cd0dbda8053b95cae3aee6dc526998a08e1da1ee5458570a41
original_question: 智慧家庭工程师的职业编码是什么
original_answer: 4-04-02-012 智慧家庭装维方向的信息通信网络线务员。
original_supporting_chunk_ids: [5ab56d780f65ff344900b1a2]
question: 《智慧家庭装维工程与管理职业技能等级标准》4.2 节中，智慧家庭工程师的职业编码是什么？
proposed_answer: 4-04-02-012
evidence_chunk_ids: [5ab56d780f65ff344900b1a2]
```

### B07

```text
batch_id: B07
parent_candidate_id: sha256:50354083653ee2bf6b5811362051fffcabfb7895978e5d6d0004c77ad21b0622
original_question: 二维码的尺寸大小要求是多少？
original_answer: 不小于17×17mm（公差：±1mm)，正方形
original_supporting_chunk_ids: [38ea5e749604f43f5f040901]
question: 在《中国移动智慧家庭全光组网产品技术规范》附录 A.2 中，光路由终端二维码的尺寸大小要求是什么？
proposed_answer: 不小于17×17mm（公差：±1mm），正方形。
evidence_chunk_ids: [c120df3a569ae215d69183ac, 38ea5e749604f43f5f040901]
```

### B09

```text
batch_id: B09
parent_candidate_id: sha256:8d8e0f5cbd56fd6adb9ba5e09728cc911d24345d7a41f15ec0eaddc37717d1c8
original_question: 全光组网终端在室温25±2℃时，非嵌入式终端表面温度不得超过多少度
original_answer: 非嵌入式全光组网终端表面温度需不超过50℃
original_supporting_chunk_ids: [9b5d9b92dc528a1c594e3ec2]
question: 在室温 25±2℃ 的情况下，非嵌入式全光组网终端表面温度不得超过多少℃？
proposed_answer: 50℃
evidence_chunk_ids: [9b5d9b92dc528a1c594e3ec2]
```

### B12

```text
batch_id: B12
parent_candidate_id: sha256:70dc300fbcd568ccd4324dd4c6a93d6e438266da789c7865f0400d0c64547d24
original_question: 无线局域网相关基础知识与无线局域网网优及软件基础知 识哪个更侧重于网络优化设计？
original_answer: 能对无线局域网覆盖进行优化
original_supporting_chunk_ids: [48ecc091e26caaa3ccbd3be5, c10a8b3b89210595f9880fc6]
question: 根据《智慧家庭装维工程与管理职业技能等级标准》，初级“基础网络质量检测”的知识条目 3.2.2 和中级“基础网络优化”的知识条目 3.2.3，分别要求掌握哪些无线局域网知识？
proposed_answer: 初级要求无线局域网相关基础知识。中级要求无线局域网网优及软件基础知识。
evidence_chunk_ids: [48ecc091e26caaa3ccbd3be5, c10a8b3b89210595f9880fc6]
```
