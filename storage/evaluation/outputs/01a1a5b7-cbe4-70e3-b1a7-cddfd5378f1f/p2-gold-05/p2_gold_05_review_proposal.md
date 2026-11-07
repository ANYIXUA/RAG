# P2-Gold-05 第二批候选初审与修订提案

2026-11-04 · B13–B27 · AI 初审。所有候选的原始状态均为 `pending_review`。

B13–B27 使用审核索引中前 12 条之后的第 13–27 个审核位置，按工作簿 B 列完整 ID 与原候选关联。页码先写 PDF 物理页，再写印刷页。修订以原 `candidate_id` 作父键，仅存在于本提案和签核包，未分配新 ID。

完整证据负责证明题答，包括必要的表头。检索相关证据只标评分命中的目标。Reject 的证据用于审计，检索相关列表为空。B14、B15 的完整覆盖各需两块；B25 的两个相关 Chunk 各自足够。当前评分器多目标为 OR，单一目标命中不能据此推导多块完整覆盖。

与首批 9 条逐条比对了题意、事实、来源与 Chunk，另在 B13–B27 内查重。B28–B57 留待后续审核。

| AI 建议 | 条数 | 编号 |
| --- | ---: | --- |
| Accept | 3 | B19, B25, B27 |
| Revise | 11 | B13, B14, B15, B16, B17, B18, B20, B21, B22, B23, B26 |
| Reject | 1 | B24 |
| Needs Verification | 0 | — |

## B13

```text
candidate_id: sha256:ba50e7af3e31659d88a2d0b4937eb510a09e19e2238d1c0e93a923a1aa42fe50
question_type: 标准条款／语义理解
original_question: 安全作业知识应包括哪些内容？
original_proposed_answer: a）安全生产操作规程基础知识； b）安全用电基础知识； c）防火防爆基础知识； d）自然灾害应急基础知识； e）有限空间作业基础知识
original_supporting_chunk_ids: [0eb4bd6e18d599063371f51b]
review_recommendation: Revise
recommended_question: 《智慧家庭装维工程与管理职业技能等级标准》第 5.7 节规定，安全作业知识包括哪五项？
recommended_proposed_answer: 安全生产操作规程基础知识、安全用电基础知识、防火防爆基础知识、自然灾害应急基础知识、有限空间作业基础知识。
evidence_chunk_ids: [0eb4bd6e18d599063371f51b]
retrieval_relevant_chunk_ids: [0eb4bd6e18d599063371f51b]
parent_candidate_id: sha256:ba50e7af3e31659d88a2d0b4937eb510a09e19e2238d1c0e93a923a1aa42fe50
```

- **问题及原因**　题面缺少标准范围。五项内容虽可部分猜测，完整清单依赖第 5.7 节。
- **原件核验**　物理页 10 的第 5.7 节正文列出 a–e 五项，均在同一 Chunk，排除上方第 5.6 节续文和下方实操技能内容。
- **证据定位**　0eb4bd6e18d599063371f51b（物理页 10）「有限空间作业基础知识」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与 B04 共享“安全作业”主题。B04 查高级实操权重，本题查通用基础知识清单，证据与答案不同。
- **来源版本**　智慧家庭装维工程与管理职业技能等级标准.pdf v_dcf78195a87f01f4
- **PDF 页码**　智慧家庭装维工程与管理职业技能等级标准.pdf 10（印刷 9）。[智慧家庭装维工程与管理职业技能等级标准.pdf 物理页 10](../../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=10)

- **修订差异**　保留原五项知识，仅统一列举格式。完整证据及直接检索目标沿用原引用。

## B14

```text
candidate_id: sha256:6b27f4cd6fb8a57d3ba3c96049bb0c8ce98b909be142ed809ab85a0bac89fba6
question_type: 等级表格定位／多证据／易混淆
original_question: 智能家居(控制)技术中，对智能家居系统架构的要求是什么？
original_proposed_answer: 1.熟悉智能家居系统架构
original_supporting_chunk_ids: [e010fe39879d92fa21dc59d9]
review_recommendation: Revise
recommended_question: 在《智慧家庭装维工程与管理职业技能等级标准》表 1 中，中级人员在“智能家居（控制）技术”项下对系统架构有什么要求？
recommended_proposed_answer: 熟悉智能家居系统架构。
evidence_chunk_ids: [0eb4bd6e18d599063371f51b, e010fe39879d92fa21dc59d9]
retrieval_relevant_chunk_ids: [e010fe39879d92fa21dc59d9]
parent_candidate_id: sha256:6b27f4cd6fb8a57d3ba3c96049bb0c8ce98b909be142ed809ab85a0bac89fba6
```

- **问题及原因**　缺少等级。中级和高级分别是系统架构与集中控制系统架构，题面只给出其中的考点，等级与掌握程度仍需查表。
- **原件核验**　物理页 10 表 1 列头依次是初级（三级）、中级（二级）、高级（一级）。物理页 11 同一续表中间列第 1 项是“熟悉智能家居系统架构”，右列是集中控制系统架构。物理页 15 第 6.4 节另列相关知识名词，未给出本题所问的“熟悉”要求。
- **证据定位**　e010fe39879d92fa21dc59d9（物理页 11）「熟悉智能家居系统架构」；0eb4bd6e18d599063371f51b（物理页 10）「初级 中级 高级 （三级） （二级） （一级）」
- **检索适用性**　页 10 为必需等级列头，页 11 为必需条目正文。检索相关列表只放直接作答的页 11。单独命中页 11 只计正文命中，不能证明中级列归属。 只有同一返回集合包含两块才算完整证据覆盖，当前 Hit@K/MRR 不提供这一判断。
- **与既有 Gold 及批内候选的关系**　与 B12 同为等级定位，职业功能和证据均不同。与 B15 是同一跨页表不同等级和业务行。
- **来源版本**　智慧家庭装维工程与管理职业技能等级标准.pdf v_dcf78195a87f01f4
- **PDF 页码**　智慧家庭装维工程与管理职业技能等级标准.pdf 10（印刷 9）, 11（印刷 10）, 15（印刷 14）。[智慧家庭装维工程与管理职业技能等级标准.pdf 物理页 10](../../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=10) · [智慧家庭装维工程与管理职业技能等级标准.pdf 物理页 11](../../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=11) · [智慧家庭装维工程与管理职业技能等级标准.pdf 物理页 15](../../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=15)

- **修订差异**　保留“熟悉智能家居系统架构”，移除条目编号。完整证据增加 0eb4bd6e18d599063371f51b，直接检索目标仍为原引用。

## B15

```text
candidate_id: sha256:029aaf51ce9894999917d4730c0682047e6aee33d34f15d1bbc64e1195361c91
question_type: 等级表格定位／多证据／易混淆
original_question: 物联网接入业务运维中，对网关组网方法的要求是什么？
original_proposed_answer: 1.掌握网关组网方法 2.熟悉路由协议等
original_supporting_chunk_ids: [1c317b1dd2cebfbf9647d03e]
review_recommendation: Revise
recommended_question: 在《智慧家庭装维工程与管理职业技能等级标准》表 1 中，高级人员在“物联网接入业务运维”项下对网关组网方法的要求是什么？
recommended_proposed_answer: 掌握网关组网方法。
evidence_chunk_ids: [0eb4bd6e18d599063371f51b, 1c317b1dd2cebfbf9647d03e]
retrieval_relevant_chunk_ids: [1c317b1dd2cebfbf9647d03e]
parent_candidate_id: sha256:029aaf51ce9894999917d4730c0682047e6aee33d34f15d1bbc64e1195361c91
```

- **问题及原因**　中级为了解，高级为掌握，原题缺少等级，原答案又带入同栏独立的路由协议要求。
- **原件核验**　物理页 10 表 1 明确右列为高级（一级），页 11 延续列序，页 12 目标行右列第 1 项为“掌握网关组网方法”，中列为“了解网关组网方法”。右列第 2 项另述路由协议。
- **证据定位**　1c317b1dd2cebfbf9647d03e（物理页 12）「掌握网关组网方法」；0eb4bd6e18d599063371f51b（物理页 10）「初级 中级 高级 （三级） （二级） （一级）」
- **检索适用性**　页 10 为必需等级列头，页 12 为必需条目正文。检索相关列表只放直接作答的页 12。单独命中页 12 只计正文命中，不能证明高级列归属。 只有同一返回集合包含两块才算完整证据覆盖，当前 Hit@K/MRR 不提供这一判断。
- **与既有 Gold 及批内候选的关系**　与 B12 同属等级定位，知识点和答案不同。与 B14 共享等级表头，直接作答 Chunk 不同。
- **来源版本**　智慧家庭装维工程与管理职业技能等级标准.pdf v_dcf78195a87f01f4
- **PDF 页码**　智慧家庭装维工程与管理职业技能等级标准.pdf 10（印刷 9）, 11（印刷 10）, 12（印刷 11）。[智慧家庭装维工程与管理职业技能等级标准.pdf 物理页 10](../../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=10) · [智慧家庭装维工程与管理职业技能等级标准.pdf 物理页 11](../../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=11) · [智慧家庭装维工程与管理职业技能等级标准.pdf 物理页 12](../../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=12)

- **修订差异**　保留“掌握网关组网方法”，删去独立的路由协议要求。完整证据增加 0eb4bd6e18d599063371f51b，直接检索目标仍为原引用。

## B16

```text
candidate_id: sha256:c0ee402dcbe543fe04df844c2c9d2134f4922a88177a166d82f0e2b2cdcd37c6
question_type: 维护作业条款／语义理解
original_question: 安装波分复用器的工作内容包括哪些？
original_proposed_answer: 1、安装波分复用器：开箱检验、复核定位、安装固定、清理现场； 2、波分复用器测试：连接仪表，测试插入衰耗值、填写测试表格等。
original_supporting_chunk_ids: [92108b5bb6dcc5b2227d531c]
review_recommendation: Revise
recommended_question: 《电信基础设施维护规程》表 10.3.3.4 中，安装波分复用器这一子项包含哪些工作？
recommended_proposed_answer: 开箱检验、复核定位、安装固定、清理现场。
evidence_chunk_ids: [92108b5bb6dcc5b2227d531c]
retrieval_relevant_chunk_ids: [92108b5bb6dcc5b2227d531c]
parent_candidate_id: sha256:c0ee402dcbe543fe04df844c2c9d2134f4922a88177a166d82f0e2b2cdcd37c6
```

- **问题及原因**　题面只问安装，原答案同时列出安装和测试。以安装子项为范围可形成唯一清单。
- **原件核验**　物理页 254 表 10.3.3.4 的工作内容分列安装与测试。安装为第 1 项四个动作，第 2 项另列连接仪表、测试插入衰耗值、填写测试表格等。
- **证据定位**　92108b5bb6dcc5b2227d531c（物理页 254）「开箱检验、复核定位、安装固定、清理现场」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与 B02、B21 共用同一 Chunk。B02 与 B21 查测试价格，本题查安装工序，事实和证据片段不同。三个问题的 Chunk 排名信号高度相关。
- **来源版本**　电信基础设施维护规程.pdf v_8ae9b63d869002c1
- **PDF 页码**　电信基础设施维护规程.pdf 254（印刷 248）。[电信基础设施维护规程.pdf 物理页 254](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=254)

- **修订差异**　保留四项安装动作，删除全部测试动作。完整证据及直接检索目标沿用原引用。

## B17

```text
candidate_id: sha256:8fcecc4204b0c7149f3d002b1b693d01b9be5a5e8930d621c5ef089f39e0585a
question_type: 精确编码／表格定位
original_question: WH23105001项目名称是什么？
original_proposed_answer: 安装防雷接地装置 室内防雷箱
original_supporting_chunk_ids: [03e5582a4a0f7d3c76a33e66]
review_recommendation: Revise
recommended_question: 《电信基础设施维护规程》表 10.3.3.5 中，编码 WH23105001 对应的防雷箱子项名称是什么？
recommended_proposed_answer: 室内防雷箱。
evidence_chunk_ids: [03e5582a4a0f7d3c76a33e66]
retrieval_relevant_chunk_ids: [03e5582a4a0f7d3c76a33e66]
parent_candidate_id: sha256:8fcecc4204b0c7149f3d002b1b693d01b9be5a5e8930d621c5ef089f39e0585a
```

- **问题及原因**　项目名称表头跨两列。原答案把合并的大类名和行内名称串在一起，题面未说明要哪一层。
- **原件核验**　物理页 255 的 WH23105001 行右侧子项格为“室内防雷箱”。“安装防雷接地装置”是纵向跨行合并的大类，室外塔下和塔上各有单独行。
- **证据定位**　03e5582a4a0f7d3c76a33e66（物理页 255）「WH23105001 安装防雷接地装置 室内防雷箱」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与首批 Gold 无同事实。B20 是同一行取价格，B18 是同列异行，B19 查表上方的作业说明。
- **来源版本**　电信基础设施维护规程.pdf v_8ae9b63d869002c1
- **PDF 页码**　电信基础设施维护规程.pdf 255（印刷 249）。[电信基础设施维护规程.pdf 物理页 255](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=255)

- **修订差异**　移除合并列的作业大类，保留行内子项。完整证据及直接检索目标沿用原引用。

## B18

```text
candidate_id: sha256:b36c80cc90660614833ec0bdf464df7b4d37db9064457a2d1e2c496856ced6ba
question_type: 数值及单位／表格定位／易混淆
original_question: 室外塔上防雷箱的综合单价是多少？
original_proposed_answer: 519.84
original_supporting_chunk_ids: [03e5582a4a0f7d3c76a33e66]
review_recommendation: Revise
recommended_question: 《电信基础设施维护规程》表 10.3.3.5 中，室外塔上防雷箱（WH23105003）的综合单价列标了多少元？
recommended_proposed_answer: 519.84 元。
evidence_chunk_ids: [03e5582a4a0f7d3c76a33e66]
retrieval_relevant_chunk_ids: [03e5582a4a0f7d3c76a33e66]
parent_candidate_id: sha256:b36c80cc90660614833ec0bdf464df7b4d37db9064457a2d1e2c496856ced6ba
```

- **问题及原因**　原答案缺货币单位，题面缺规范和项目定位。表头统一列“套、个”，没有给该行单独指定其中一项。
- **原件核验**　物理页 255，WH23105003 室外塔上防雷箱 × 综合单价（元）为 519.84。相邻 WH23105002 塔下为 302.78，WH23105001 室内为 271.78。表头计量单位并列套、个，本题按金额列回答。
- **证据定位**　03e5582a4a0f7d3c76a33e66（物理页 255）「WH23105003 室外塔上防雷箱 519.84」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与首批 Gold 无同事实。B20 同表同价格列的相邻子项；保留塔上、塔下对照所需的精确行定位。
- **来源版本**　电信基础设施维护规程.pdf v_8ae9b63d869002c1
- **PDF 页码**　电信基础设施维护规程.pdf 255（印刷 249）。[电信基础设施维护规程.pdf 物理页 255](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=255)

- **修订差异**　保留 519.84，补充元。完整证据及直接检索目标沿用原引用。

## B19

```text
candidate_id: sha256:4f4129854aedf46810ac9654b5e918be591a55ffb3a8bd01c24ca7aa787237de
question_type: 维护作业条款／语义理解
original_question: 安装防雷接地装置的工作内容有哪些？
original_proposed_answer: 1、安装防雷箱：开箱检验、清洁搬运、定位、安装固定、连接连线、清理现场； 2、安装接地排：开箱检验、清洁搬运、划线定位、安装固定、清理现场； 3、安装防雷器：开箱检验、安装固定、连接连线、清理现场； 4、接地电阻测试：接线、测量等。
original_supporting_chunk_ids: [03e5582a4a0f7d3c76a33e66]
review_recommendation: Accept
recommended_question: 安装防雷接地装置的工作内容有哪些？
recommended_proposed_answer: 1、安装防雷箱：开箱检验、清洁搬运、定位、安装固定、连接连线、清理现场； 2、安装接地排：开箱检验、清洁搬运、划线定位、安装固定、清理现场； 3、安装防雷器：开箱检验、安装固定、连接连线、清理现场； 4、接地电阻测试：接线、测量等。
evidence_chunk_ids: [03e5582a4a0f7d3c76a33e66]
retrieval_relevant_chunk_ids: [03e5582a4a0f7d3c76a33e66]
```

- **问题及原因**　题面给出明确作业名称，答案完整对应四类工作及操作细节。完整流程需要按原文核查。
- **原件核验**　物理页 255 表 10.3.3.5 上方的工作内容依次列安装防雷箱、安装接地排、安装防雷器和接地电阻测试。原答案与四项细目一致，证据在一块内。
- **证据定位**　03e5582a4a0f7d3c76a33e66（物理页 255）「接地电阻测试：接线、测量」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与首批 Gold 无同事实。与 B17、B18、B20 共用 Chunk，但本题定位表上方说明。
- **来源版本**　电信基础设施维护规程.pdf v_8ae9b63d869002c1
- **PDF 页码**　电信基础设施维护规程.pdf 255（印刷 249）。[电信基础设施维护规程.pdf 物理页 255](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=255)

## B20

```text
candidate_id: sha256:0c141695e2654b721a2a70e712bfdd9cc951d132b823ef8b710b0f07c17d7f73
question_type: 数值及单位／表格定位／易混淆
original_question: 室内防雷箱的安装综合单价是多少？
original_proposed_answer: 271.78
original_supporting_chunk_ids: [03e5582a4a0f7d3c76a33e66]
review_recommendation: Revise
recommended_question: 《电信基础设施维护规程》表 10.3.3.5 中，室内防雷箱（WH23105001）的综合单价列标了多少元？
recommended_proposed_answer: 271.78 元。
evidence_chunk_ids: [03e5582a4a0f7d3c76a33e66]
retrieval_relevant_chunk_ids: [03e5582a4a0f7d3c76a33e66]
parent_candidate_id: sha256:0c141695e2654b721a2a70e712bfdd9cc951d132b823ef8b710b0f07c17d7f73
```

- **问题及原因**　初审曾因与 B17 同行、与 B18 同价列且共享检索 Chunk，担心重复计量。复审按实体、所问属性和答案区分。B17 查 WH23105001 的子项名称，B20 查该行综合单价，事实不同。B18 是同类价格题，但对应塔上行 WH23105003。保留 B20，补表号、编码和金额单位。
- **原件核验**　重看物理页 255（印刷 249）。WH23105001 行子项列为室内防雷箱，综合单价（元）列为 271.78。相邻塔下及塔上行为 302.78 和 519.84。表头并列套、个，无逐行单位分配。
- **证据定位**　03e5582a4a0f7d3c76a33e66（物理页 255）「WH23105001 安装防雷接地装置 室内防雷箱 271.78」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与首批 9 条 Gold 无同事实或完全重复。与 B17 同实体、不同属性；与 B18 同类、不同子项；三题共享 Chunk，排名结果可能相关。
- **来源版本**　电信基础设施维护规程.pdf v_8ae9b63d869002c1
- **PDF 页码**　电信基础设施维护规程.pdf 255（印刷 249）。[电信基础设施维护规程.pdf 物理页 255](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=255)

- **修订差异**　保留 271.78，补充元。完整证据及直接检索目标沿用原引用。

## B21

```text
candidate_id: sha256:af261cdb97be35e69dd294aff4351ed7ec7477048b2377adaee100697c1809d3
question_type: 数值及单位／表格定位／易混淆
original_question: 波分复用器1:6以下的测试综合单价是多少？
original_proposed_answer: 62.02
original_supporting_chunk_ids: [92108b5bb6dcc5b2227d531c]
review_recommendation: Revise
recommended_question: 《电信基础设施维护规程》表 10.3.3.4 中，测试波分复用器 1:6 以下（WH23104004）的综合单价是多少（元/个）？
recommended_proposed_answer: 62.02 元/个。
evidence_chunk_ids: [92108b5bb6dcc5b2227d531c]
retrieval_relevant_chunk_ids: [92108b5bb6dcc5b2227d531c]
parent_candidate_id: sha256:af261cdb97be35e69dd294aff4351ed7ec7477048b2377adaee100697c1809d3
```

- **问题及原因**　初审曾因与首批 B02 同测试大类、同价格列、同目标 Chunk，担心重复计量。复审确认两题同类但分别查不同编码与分光比，答案不同。保留 B21，明确 1:6 以下及项目编码，补元/个。
- **原件核验**　重看物理页 254（印刷 248）。表头计量单位为个，综合单价列为元。测试大类下 WH23104004（1:6 以下）为 62.02，首批 B02 的 WH23104003（1:2）为 29.18。WH23104001 为同价的室内安装行，须按测试大类和项目编码定位。
- **证据定位**　92108b5bb6dcc5b2227d531c（物理页 254）「WH23104004 波分复用器1:6 以下 62.02」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与首批 B02 同类、不同事实、无完全重复。两者分别定位 1:6 以下及 1:2 的测试行，使用同一 Chunk，排名结果可能相关，单次 Chunk 命中无法区分两行。
- **来源版本**　电信基础设施维护规程.pdf v_8ae9b63d869002c1
- **PDF 页码**　电信基础设施维护规程.pdf 254（印刷 248）。[电信基础设施维护规程.pdf 物理页 254](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=254)

- **修订差异**　保留 62.02，补充元/个。完整证据及直接检索目标沿用原引用。

## B22

```text
candidate_id: sha256:474ea2ea4e472386215819df6edeb7f88ca3c1af3abae6259f11972588f52812
question_type: 设备安全条款／语义理解
original_question: 设备在出厂后不应预留哪些类型的账号？
original_proposed_answer: 设备中除为用户提供的唯一账号外，在设备出厂后不应以任何形式在设备中预留任 何其他账号。
original_supporting_chunk_ids: [81951fb8b5e157346ed83d77]
review_recommendation: Revise
recommended_question: 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0 第 4.8.2 节，全光组网终端出厂后可以保留什么账号？
recommended_proposed_answer: 仅可保留为用户提供的唯一账号，禁止以任何形式预留其他账号。
evidence_chunk_ids: [81951fb8b5e157346ed83d77]
retrieval_relevant_chunk_ids: [81951fb8b5e157346ed83d77]
parent_candidate_id: sha256:474ea2ea4e472386215819df6edeb7f88ca3c1af3abae6259f11972588f52812
```

- **问题及原因**　“设备”缺少对象和规范范围。“哪些类型”容易只答调试账号，条款实际禁止用户唯一账号以外的全部预留账号。
- **原件核验**　物理页 52 第 4.8.2 节第 1 项标题是“禁用调试账号”，正文明确唯一用户账号的例外和禁止范围。物理页 1 封面确认版本 V2.0.0。
- **证据定位**　81951fb8b5e157346ed83d77（物理页 52）「为用户提供的唯一账号」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　首批仅共享规范来源，事实与目标页不同。与 B23 同 Chunk、不同条款。
- **来源版本**　中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf v_ab72ce00c904f060
- **PDF 页码**　中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 1（封面）, 52（印刷 47）。[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 物理页 1](../../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=1) · [中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 物理页 52](../../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=52)

- **修订差异**　保留用户唯一账号例外与禁止其他账号的原意，整理断行。完整证据及直接检索目标沿用原引用。

## B23

```text
candidate_id: sha256:0f3b338e277722ef4de67a59096d7e8c931138eb05c300808fc9d2ea9a186468
question_type: 接入安全条款／易混淆
original_question: WLAN应支持哪些链路层鉴权方式？
original_proposed_answer: WLAN 应支持Open System 和Pre-Shared Key 两种链路层鉴权方式。
original_supporting_chunk_ids: [81951fb8b5e157346ed83d77]
review_recommendation: Revise
recommended_question: 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0 第 4.8.4 节，全光组网终端的 WLAN 应支持哪两种链路层鉴权方式？
recommended_proposed_answer: Open System 和 Pre-Shared Key。
evidence_chunk_ids: [81951fb8b5e157346ed83d77]
retrieval_relevant_chunk_ids: [81951fb8b5e157346ed83d77]
parent_candidate_id: sha256:0f3b338e277722ef4de67a59096d7e8c931138eb05c300808fc9d2ea9a186468
```

- **问题及原因**　原题将产品规范要求问成一般 WLAN 知识。需限定 LAN 侧条款并区分鉴权与下一条的加密模式。
- **原件核验**　物理页 52 第 4.8.4 节第 1 项列出两种鉴权。紧随其后的第 2 项另列 WPA 系列及 AES、TKIP+AES。物理页 1 封面确认版本 V2.0.0。
- **证据定位**　81951fb8b5e157346ed83d77（物理页 52）「WLAN 应支持Open System 和Pre-Shared Key」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与首批 B05 同为 WLAN 主题，B05 查 802.11ax 的 RU 调度，事实和目标不同。与 B22 共用 Chunk，证据句不同。
- **来源版本**　中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf v_ab72ce00c904f060
- **PDF 页码**　中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 1（封面）, 52（印刷 47）。[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 物理页 1](../../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=1) · [中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 物理页 52](../../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=52)

- **修订差异**　保留两种鉴权方式名称，精简答句。完整证据及直接检索目标沿用原引用。

## B24

```text
candidate_id: sha256:d049bb19337a6de2e27a654729cdbfc8b84ef5e4b93dd4f31606dc51f4a0c6dd
question_type: 术语释义／常识泄漏
original_question: 3.2 OLT（Optical Line Terminal）的定义是什么？
original_proposed_answer: 光线路终端。
original_supporting_chunk_ids: [5ab56d780f65ff344900b1a2]
review_recommendation: Reject
recommended_question:
recommended_proposed_answer:
evidence_chunk_ids: [5ab56d780f65ff344900b1a2, 469978708f9fe4506fc1fa7f]
retrieval_relevant_chunk_ids: []
```

- **问题及原因**　原题已展开 OLT 的英文全称，中文释义可直接翻译，检索必要性低；改去英文全称仍属于常见缩写释义。
- **原件核验**　职业技能标准物理页 6 第 3.2 节确实给出“光线路终端”。全光规范物理页 9 的缩略语表同样给出 OLT、Optical Line Terminal、光线路终端，证明有跨文档同义答案。
- **证据定位**　5ab56d780f65ff344900b1a2（物理页 6）「3.2 OLT（Optical Line Terminal） 光线路终端」；469978708f9fe4506fc1fa7f（物理页 9）「OLT Optical Line Terminal 光线路终端」
- **检索适用性**　原题审计证据。驳回建议不设检索目标。
- **与既有 Gold 及批内候选的关系**　与 B06 共用职业技能标准第 6 页 Chunk，但 B06 查职业编码。建议驳回的原因是常识泄漏及低检索必要性。
- **来源版本**　中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf v_ab72ce00c904f060；智慧家庭装维工程与管理职业技能等级标准.pdf v_dcf78195a87f01f4
- **PDF 页码**　中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 9（印刷 4）；智慧家庭装维工程与管理职业技能等级标准.pdf 6（印刷 5）。[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 物理页 9](../../../../../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=9) · [智慧家庭装维工程与管理职业技能等级标准.pdf 物理页 6](../../../../../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=6)

## B25

```text
candidate_id: sha256:2fa4c3c7182110647ed797c132138313300e447227199131a9731a8acd4a1afa
question_type: 维护作业条款／等价证据
original_question: 铁塔专项维修的工作内容包括哪些？
original_proposed_answer: 塔体结构检查、螺丝紧固、漆面除锈刷漆、塔基强度测试等。
original_supporting_chunk_ids: [611a9eb6554a2b482561c775]
review_recommendation: Accept
recommended_question: 铁塔专项维修的工作内容包括哪些？
recommended_proposed_answer: 塔体结构检查、螺丝紧固、漆面除锈刷漆、塔基强度测试等。
evidence_chunk_ids: [611a9eb6554a2b482561c775]
retrieval_relevant_chunk_ids: [611a9eb6554a2b482561c775, 4931f1a7b903ba2672bbb512]
```

- **问题及原因**　题面指向铁塔专项维修，四项答案在两个原件位置均完整。详细作业清单有文档依赖，原题和原引用可用。
- **原件核验**　物理页 286 表 10.3.3.29 的工作内容列四项。物理页 141 的 WH23123 行独立列出相同四项；两处为替代证据。页 286 原件表题标 WH23126，明细行编码为 WH23129001 等，本题只取作业内容。
- **证据定位**　611a9eb6554a2b482561c775（物理页 286）「塔基强度测试」；4931f1a7b903ba2672bbb512（物理页 141）「塔体结构检查。 2.螺丝紧固、 3.漆面除锈刷漆。 4.塔基强度测试。」
- **检索适用性**　页 286 和页 141 是独立充分的替代证据，任一页可支持四项答案。完整证据列出原引用页 286，检索相关收录两页。
- **与既有 Gold 及批内候选的关系**　与首批 Gold 无同事实。与 B26 同属维护作业，但对象和工作不同。
- **来源版本**　电信基础设施维护规程.pdf v_8ae9b63d869002c1
- **PDF 页码**　电信基础设施维护规程.pdf 141（印刷 135）, 286（印刷 280）。[电信基础设施维护规程.pdf 物理页 141](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=141) · [电信基础设施维护规程.pdf 物理页 286](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=286)

## B26

```text
candidate_id: sha256:6535e6f78dc8eeb10b933e995f8321cd01ed80d90f405c5042b7fbfccf08ac95
question_type: 维护范围／易混淆
original_question: 机房室外环境清理的工作内容是什么？
original_proposed_answer: 机房、铁塔、院墙、护网外内部以及周边一米杂草、杂物集中清除等。
original_supporting_chunk_ids: [a264a91966d85e2ec3b52e02]
review_recommendation: Revise
recommended_question: 《电信基础设施维护规程》表 10.3.3.30（WH23130）规定，机房室外环境清理的工作内容是什么？
recommended_proposed_answer: 机房、铁塔、院墙、护网外内部以及周边一米杂草、杂物集中清除等。
evidence_chunk_ids: [a264a91966d85e2ec3b52e02]
retrieval_relevant_chunk_ids: [a264a91966d85e2ec3b52e02]
parent_candidate_id: sha256:6535e6f78dc8eeb10b933e995f8321cd01ed80d90f405c5042b7fbfccf08ac95
```

- **问题及原因**　不同章节有同名作业。页 287、315 的明细答案一致，页 141、149 的概述分别省略部分对象或杂物，原题未指明采用哪张表。
- **原件核验**　物理页 287 表 10.3.3.30 的工作内容与原答案一致。物理页 315 表 10.4.3.15 同句，但作业编码 WH33115。物理页 141 同名概述未列杂物，页 149 同名概述未列铁塔。推荐答案保留原件“护网外内部”的措辞。 本轮重看物理页 287 的放大渲染图并用独立 PDF 文本提取交叉核对，两处均为「护网外内部」。该措辞是 PDF 原文，语义不够顺畅，推荐答案沿用原文，不推定边界。
- **证据定位**　a264a91966d85e2ec3b52e02（物理页 287）「表10.3.3.30 WH23130 机房室外环境清理」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与首批 Gold 无同事实。与 B25 同为维护作业，证据和答案不同。按推荐题面只标页 287 为检索目标。
- **来源版本**　电信基础设施维护规程.pdf v_8ae9b63d869002c1
- **PDF 页码**　电信基础设施维护规程.pdf 141（印刷 135）, 149（印刷 143）, 287（印刷 281）, 315（印刷 309）。[电信基础设施维护规程.pdf 物理页 141](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=141) · [电信基础设施维护规程.pdf 物理页 149](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=149) · [电信基础设施维护规程.pdf 物理页 287](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=287) · [电信基础设施维护规程.pdf 物理页 315](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=315)

- **修订差异**　原答案逐字保留。完整证据及直接检索目标沿用原引用。

## B27

```text
candidate_id: sha256:0412887e0c24cae711a326d0032a59e8cce8c7618478be6748fd98c2cfc9f4bf
question_type: 精确编码／表格定位／易混淆
original_question: WH23131004项目对应的防水处理范围是什么？
original_proposed_answer: 地面墙面防水
original_supporting_chunk_ids: [95cb40813342a7e91c27e7d3]
review_recommendation: Accept
recommended_question: WH23131004项目对应的防水处理范围是什么？
recommended_proposed_answer: 地面墙面防水
evidence_chunk_ids: [95cb40813342a7e91c27e7d3]
retrieval_relevant_chunk_ids: [95cb40813342a7e91c27e7d3]
```

- **问题及原因**　编码唯一，答案完整对应防水范围。需要检索规程完成编码到范围的映射。
- **原件核验**　物理页 288 表 10.3.3.31 的 WH23131004 行为“地面墙面防水”，WH23131003 行为“顶面防水”。工作内容第 3 项复核地板及墙面的处理范围。
- **证据定位**　95cb40813342a7e91c27e7d3（物理页 288）「WH23131004 地面墙面防水」
- **检索适用性**　目标条文或行在同一个 Chunk 内，足以证明推荐题答。
- **与既有 Gold 及批内候选的关系**　与首批 Gold 无同事实。B17 同为编码查表，作业及证据均不同。
- **来源版本**　电信基础设施维护规程.pdf v_8ae9b63d869002c1
- **PDF 页码**　电信基础设施维护规程.pdf 288（印刷 282）。[电信基础设施维护规程.pdf 物理页 288](../../../../../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=288)
