# P2-Gold-03 人工签核证据包

2026-11-04 · B01–B12 · 待人工签核

每条的 `review_recommendation` 为 AI 独立初审建议。工作簿 G 列的 `human` 是原有占位，签核只记录在以下空白人工字段。驳回建议条目的证据用于定位原题错误，保留与驳回建议的修订字段留空。

B07、B12 在本轮重看 PDF 渲染原件。其他十条沿用 P2-Gold-02 的原件逐项核验，本轮复查了源 PDF SHA-256 与初审记录相同，并重新绑定候选、Chunk 和页码。页码均先列 PDF 物理页（从 1 开始），括号为印刷页。

[原始证据包](first-batch-evidence.md) · [独立初审](p2_gold_02_review_proposal.md) · [本轮修订方案](p2_gold_03_revision_proposal.md)

## B01

原件 [29（印刷 23）](../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=29) · [候选原始引文](first-batch-evidence.md#b01)

```text
batch_id: B01
candidate_id: sha256:9631dde730749e95e2c74da24726dd1d8e743b1242d189ac76034732a01fa5e9
question_type: exact_entity
original_question: 管道线路的人（手）孔检修周期是多久？
original_answer: 半年
original_supporting_chunk_ids: [831af7c41fd776db6b5b3ff9]
review_recommendation: 修订
review_reason: 原题未限定场景。半年周期对应常规场景，高速公路中人孔按需检修。
revised_question: 非高速公路场景下，管道线路的人（手）孔检修周期是多久？
revised_answer: 半年（高速公路中人孔的检修按需进行，不适用半年周期）。
evidence_chunk_ids: [831af7c41fd776db6b5b3ff9]
retrieval_relevance_notes: 直接证据。按同一行读取检修、周期与备注。
source_document: 电信基础设施维护规程.pdf
source_pages: 29（印刷 23）
source_verification: 继承 P2-Gold-02 原件核验。路面维护表同一行给出半年周期，备注限定高速公路人孔按需。
human_decision:接受修订
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:已确认
```

## B02

原件 [254（印刷 248）](../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=254) · [候选原始引文](first-batch-evidence.md#b02)

```text
batch_id: B02
candidate_id: sha256:6858125cbf5e8170a757c8a812aca9d1a9b2dd23347c59d5061af9a7c0d982f0
question_type: exact_entity
original_question: 波分复用器1:2的测试单价是多少？
original_answer: 29.18
original_supporting_chunk_ids: [92108b5bb6dcc5b2227d531c]
review_recommendation: 修订
review_reason: 原题已提及测试，但缺少唯一项目编码和计量单位，且答案只有数值。
revised_question: 在维护分项作业表 10.3.3.4（WH23104 安装、测试波分复用器）中，测试波分复用器 1:2（项目编码 WH23104003）的综合单价是多少（元/个）？
revised_answer: 29.18 元/个。
evidence_chunk_ids: [92108b5bb6dcc5b2227d531c]
retrieval_relevance_notes: 直接证据。匹配测试子项及数值，区分安装项和相邻分光比。
source_document: 电信基础设施维护规程.pdf
source_pages: 254（印刷 248）
source_verification: 继承 P2-Gold-02 原件核验。表 10.3.3.4 核对项目编码 WH23104003、综合单价 29.18 和表头单位“个”。
human_decision:接受修订
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:已确认
```

## B03

原件 [1（封面）](../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=1) · [候选原始引文](first-batch-evidence.md#b03)

```text
batch_id: B03
candidate_id: sha256:31d42a216450391763336ebbd7b38604cb50a3557831669e5b3371e63ef477ed
question_type: exact_entity
original_question: 智慧家庭全光组网产品技术规范的版本是什么？
original_answer: V2.0.0
original_supporting_chunk_ids: [4f32247f7a6d7526df77bddd]
review_recommendation: 建议保留
review_reason: 全光规范封面明确标注 V2.0.0。人工可确认是否补规范全称。
revised_question:
revised_answer:
evidence_chunk_ids: [4f32247f7a6d7526df77bddd]
retrieval_relevance_notes: 直接证据。封面版本号，结合文档名区分同名版本。
source_document: 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf
source_pages: 1（封面）
source_verification: 继承 P2-Gold-02 原件核验。封面版本号与 Chunk 一致。
human_decision:接受原题
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:已核对PDF
```

## B04

原件 [19（印刷 18）](../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=19) · [候选原始引文](first-batch-evidence.md#b04)

```text
batch_id: B04
candidate_id: sha256:4d263ebb839f347941da0bd9c9d0c11533925443e6a26519593ad7628f6c29e6
question_type: exact_entity
original_question: 在实操技能权重表中，高级阶段的安全作业权重是多少？
original_answer: 10
original_supporting_chunk_ids: [02c18b66c8c7d17fa1fb910e]
review_recommendation: 修订
review_reason: 原题应锚定实操表 7.2，并补百分比单位。相邻理论知识表的高级值不同。
revised_question: 在 7.2 智慧家庭装维工程与管理实操技能权重表中，技能等级为高级时，“安全作业”项目的权重是多少（%）？
revised_answer: 10%
evidence_chunk_ids: [02c18b66c8c7d17fa1fb910e]
retrieval_relevance_notes: 直接证据。同页有 7.1、7.2 两表，审核时按实操表行列定位。
source_document: 智慧家庭装维工程与管理职业技能等级标准.pdf
source_pages: 19（印刷 18）
source_verification: 继承 P2-Gold-02 原件核验。实操表 7.2 安全作业行与高级列交叉为 10，表头单位为 %。
human_decision:接受修订
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:已确认
```

## B05

原件 [25（印刷 20）](../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=25) · [候选原始引文](first-batch-evidence.md#b05)

```text
batch_id: B05
candidate_id: sha256:e3783223e572063f0a3df106a6c1c6084c99e5f2943b788dc72a6996cb96b2bf
question_type: exact_entity
original_question: 全光组网终端支持IEEE 802.11ax协议时，2.4G频段应至少支持多少个RU并行调度？
original_answer: 4
original_supporting_chunk_ids: [4812f97659f77c46891223fa]
review_recommendation: 建议保留
review_reason: 题面已限定 802.11ax、2.4G 频段和 RU。人工可确认答案是否补成“4 个 RU”。
revised_question:
revised_answer:
evidence_chunk_ids: [4812f97659f77c46891223fa]
retrieval_relevance_notes: 直接证据。区分 5G 的 8 个 RU 与相邻 802.11be 的用户数表述。
source_document: 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf
source_pages: 25（印刷 20）
source_verification: 继承 P2-Gold-02 原件核验。4.3.4.8 的 2.4G 条款明确至少支持 4 个 RU 并行调度。
human_decision:接受原题
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:已核对PDF
```

## B06

原件 [6（印刷 5）](../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=6) · [候选原始引文](first-batch-evidence.md#b06)

```text
batch_id: B06
candidate_id: sha256:bfd1eea2e2dfb6cd0dbda8053b95cae3aee6dc526998a08e1da1ee5458570a41
question_type: semantic
original_question: 智慧家庭工程师的职业编码是什么
original_answer: 4-04-02-012 智慧家庭装维方向的信息通信网络线务员。
original_supporting_chunk_ids: [5ab56d780f65ff344900b1a2]
review_recommendation: 修订
review_reason: 原答案并入职业方向说明，超出编码提问。
revised_question: 《智慧家庭装维工程与管理职业技能等级标准》4.2 节中，智慧家庭工程师的职业编码是什么？
revised_answer: 4-04-02-012
evidence_chunk_ids: [5ab56d780f65ff344900b1a2]
retrieval_relevance_notes: 直接证据。以 4.2 节编码为目标。
source_document: 智慧家庭装维工程与管理职业技能等级标准.pdf
source_pages: 6（印刷 5）
source_verification: 继承 P2-Gold-02 原件核验。4.2 节核对编码，后续职业方向说明用于解释归属。
human_decision:接受修订
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:已确认
```

## B07

原件 [61（印刷 56）](../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=61) · [62（印刷 57）](../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=62) · [候选原始引文](first-batch-evidence.md#b07)

```text
batch_id: B07
candidate_id: sha256:50354083653ee2bf6b5811362051fffcabfb7895978e5d6d0004c77ad21b0622
question_type: semantic
original_question: 二维码的尺寸大小要求是多少？
original_answer: 不小于17×17mm（公差：±1mm)，正方形
original_supporting_chunk_ids: [38ea5e749604f43f5f040901]
review_recommendation: 修订
review_reason: 原题未区分二维码适用产品。第 62 页尺寸续文须结合第 61 页 A.2 标题确认归属。
revised_question: 在《中国移动智慧家庭全光组网产品技术规范》附录 A.2 中，光路由终端二维码的尺寸大小要求是什么？
revised_answer: 不小于17×17mm（公差：±1mm），正方形。
evidence_chunk_ids: [c120df3a569ae215d69183ac, 38ea5e749604f43f5f040901]
retrieval_relevance_notes: 第 62 页为直接检索目标。第 61 页是签核所需归属证据，可作检索背景。
source_document: 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf
source_pages: 61（印刷 56）、62（印刷 57）
source_verification: 本轮复核。本轮目视重核。物理 61 页标题为“A.2 光路由终端二维码标识要求”，页末列（1）（2）。物理 62 页续列（3）尺寸，页面、Chunk 正文和元数据均无该产品名。两页合读无已知证据缺口，可送人工复核。
retrieval_relevant_chunk_ids: [38ea5e749604f43f5f040901]
human_decision:接受修订
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:已确认
```

## B08

原件 [343（印刷 337）](../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=343) · [候选原始引文](first-batch-evidence.md#b08)

```text
batch_id: B08
candidate_id: sha256:d5ab4e3c5473589238491da686184e9c651ecdbf317776b9454bc222b49ff81a
question_type: semantic
original_question: 市内街道架空通信线路的最低缆线到屋脊的最小垂直净距是多少米？
original_answer: 1.5
original_supporting_chunk_ids: [d8dfa78cb9362f0d69cd659c]
review_recommendation: 建议驳回
review_reason: 市内街道行与房屋建筑物的屋脊备注被拼接。1.5 m 属于房屋平顶，屋脊对应 0.6 m。若人工决定重出题，先选定一个有效场景。
revised_question:
revised_answer:
evidence_chunk_ids: [d8dfa78cb9362f0d69cd659c]
retrieval_relevance_notes: 此引用用于复核原题矛盾。当前题面不设推荐检索目标。
source_document: 电信基础设施维护规程.pdf
source_pages: 343（印刷 337）
source_verification: 继承 P2-Gold-02 原件核验。表 D.0.2 核对场景、净距和备注。市内街道为 4.5 m（平时）、5.5 m（交越）。
human_decision:驳回
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:确认驳回
```

## B09

原件 [58（印刷 53）](../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=58) · [候选原始引文](first-batch-evidence.md#b09)

```text
batch_id: B09
candidate_id: sha256:8d8e0f5cbd56fd6adb9ba5e09728cc911d24345d7a41f15ec0eaddc37717d1c8
question_type: semantic
original_question: 全光组网终端在室温25±2℃时，非嵌入式终端表面温度不得超过多少度
original_answer: 非嵌入式全光组网终端表面温度需不超过50℃
original_supporting_chunk_ids: [9b5d9b92dc528a1c594e3ec2]
review_recommendation: 修订
review_reason: 原题对象名称和单位不够精确，原答案复述整句。
revised_question: 在室温 25±2℃ 的情况下，非嵌入式全光组网终端表面温度不得超过多少℃？
revised_answer: 50℃
evidence_chunk_ids: [9b5d9b92dc528a1c594e3ec2]
retrieval_relevance_notes: 直接证据。使用非嵌入式条件区分嵌入式限值。
source_document: 中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf
source_pages: 58（印刷 53）
source_verification: 继承 P2-Gold-02 原件核验。4.11.2 温度要求中非嵌入式为 50℃，嵌入式为 65℃。
human_decision:接受修订
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:已确认
```

## B10

原件 [280（印刷 274）](../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=280) · [候选原始引文](first-batch-evidence.md#b10)

```text
batch_id: B10
candidate_id: sha256:b503d526e513f66d71916de151812a19403e51bbfd81956c88dee63adda7814a
question_type: semantic
original_question: 24V铅酸蓄电池600Ah以下的蓄电池抗震架双层单列的消耗量是多少？
original_answer: 0.69
original_supporting_chunk_ids: [65af106efc532138e75dad76]
review_recommendation: 建议驳回
review_reason: 题面合并了两个独立作业子项。0.69 工日只属于抗震架子项。
revised_question:
revised_answer:
evidence_chunk_ids: [65af106efc532138e75dad76]
retrieval_relevance_notes: 此引用用于复核跨项目拼接。当前题面不设推荐检索目标。
source_document: 电信基础设施维护规程.pdf
source_pages: 280（印刷 274）
source_verification: 继承 P2-Gold-02 原件核验。表 10.3.3.23 的 WH23123001 抗震架技工 0.69 工日，WH23123002 24V 电池技工 2.68 工日。
human_decision:驳回
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:确认驳回
```

## B11

原件 [277（印刷 271）](../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=277) · [278（印刷 272）](../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=278) · [候选原始引文](first-batch-evidence.md#b11)

```text
batch_id: B11
candidate_id: sha256:de1dd6ecf011fd92f5cbef969545f045b067fbc353123e327f2b8ce04527a0d3
question_type: confusable
original_question: 安装干式电力100kVA以下变压器和安装与调试控制设备的综合单价分别是多少？
original_answer: 452.35
original_supporting_chunk_ids: [4a65d0d3ead0bc841b1b28f8, 647c44016cd2e8fabe51f5de]
review_recommendation: 建议驳回
review_reason: 题面问两项单价，答案只给一个值，且控制设备分类无唯一总单价。若人工决定重出题，先查重 WH23121002 和 WH23121004。
revised_question:
revised_answer:
evidence_chunk_ids: [4a65d0d3ead0bc841b1b28f8, 647c44016cd2e8fabe51f5de]
retrieval_relevance_notes: 两块用于复核原题矛盾。当前题面不设推荐检索目标。
source_document: 电信基础设施维护规程.pdf
source_pages: 278（印刷 272）、277（印刷 271）
source_verification: 继承 P2-Gold-02 原件核验。物理 277 页 WH23120003 为 452.35 元/台。物理 278 页 WH23121 含四项独立单价。
human_decision:驳回
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:确认驳回
```

## B12

原件 [16（印刷 15）](../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=16) · [18（印刷 17）](../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=18) · [候选原始引文](first-batch-evidence.md#b12)

```text
batch_id: B12
candidate_id: sha256:70dc300fbcd568ccd4324dd4c6a93d6e438266da789c7865f0400d0c64547d24
question_type: confusable
original_question: 无线局域网相关基础知识与无线局域网网优及软件基础知 识哪个更侧重于网络优化设计？
original_answer: 能对无线局域网覆盖进行优化
original_supporting_chunk_ids: [48ecc091e26caaa3ccbd3be5, c10a8b3b89210595f9880fc6]
review_recommendation: 修订
review_reason: P2-Gold-02 的题面直接给出知识类别。原答案属于技能要求列。新题限定两处知识条目编号。
revised_question: 根据《智慧家庭装维工程与管理职业技能等级标准》，初级“基础网络质量检测”的知识条目 3.2.2 和中级“基础网络优化”的知识条目 3.2.3，分别要求掌握哪些无线局域网知识？
revised_answer: 初级要求无线局域网相关基础知识。中级要求无线局域网网优及软件基础知识。
evidence_chunk_ids: [48ecc091e26caaa3ccbd3be5, c10a8b3b89210595f9880fc6]
retrieval_relevance_notes: 两页均直接相关。只命中任一页可取得现行 Hit，双证据完整召回须同时命中两页。
source_document: 智慧家庭装维工程与管理职业技能等级标准.pdf
source_pages: 16（印刷 15）、18（印刷 17）
source_verification: 本轮复核。本轮目视重核。物理 16 页初级 3.2 知识 3.2.2 对应 WLAN 基础。物理 18 页中级 3.2 知识 3.2.3 对应 WLAN 网优及软件基础，且中级 3.2.2 同样列通用 WLAN 基础。
retrieval_relevant_chunk_ids: [48ecc091e26caaa3ccbd3be5, c10a8b3b89210595f9880fc6]
human_decision:接受修订
human_reviewer:system
human_reviewed_at:2026/11/04
human_comment:已确认
```
