# P4-Gold-Completion-01 集中人工签核包

2026-11-05（Asia/Shanghai）。先处理28条主选；其余18条留作备选、替换或驳回裁决。AI建议不是批准，当前新增Gold=0，正式Holdout=0。

建议统一填写同目录工作簿“签核”页黄色的人工决定、审核人、审核日期、备注四列；下方空白字段仅供纯文本方式使用，不要两处分别填写。若两处冲突，必须先人工消解，禁止自动挑选。

人工决定只选“接受原题 / 接受修订 / 驳回”。接受原题绑定原题答及原证据；接受修订绑定下方待签题答、相关Chunk及proposal_id。标为Revise的题若选择接受原题，不能自动导出，须先处理本报告指出的问题。姓名/身份和日期由人工填写，备注可空；B23若继续“保留测试”仍是未签核。

任何接受均是本轮内容裁决；Holdout冻结、运行授权是后续独立步骤。本轮不生成运行用Gold，不读取签核表来自动执行导出或Benchmark。引用的原候选ID保持不动，修订由独立proposal_id与记录哈希绑定。

## 主选28条

| 编号 | AI建议 | 待签题目 | 来源物理页 | 筛选 |
| --- | --- | --- | --- | --- |
| B32 | Revise | 《智慧家庭装维工程与管理职业技能等级标准》第 4.6、4.7 节分别对职业能力特征和受教育程度提出了什么要求？ | 7 | holdout_primary_proposed |
| B33 | Revise | 《智慧家庭装维工程与管理职业技能等级标准》第 4.9.2.1 节规定，职业技能鉴定的鉴定方式应分为哪两类？ | 8 | holdout_primary_proposed |
| B34 | Revise | 《电信基础设施维护规程》表 D.0.2 中，铁路与架空通信线路交越时，最低缆线到轨面的最小垂直净距是多少米？ | 343 | holdout_primary_proposed |
| B35 | Revise | 《中国移动智慧家庭全光组网产品技术规范》V2.0.0 表 4-1 中，全光组网终端的产品类型和设备形态名称分别有哪些？ | 15 | holdout_primary_proposed |
| B40 | Accept | WH23120 安装、调试、断电检修变压器的工作内容包括哪些？ | 277 | holdout_primary_proposed |
| B41 | Accept | WH23121 安装与调试控制设备的工作内容是什么？ | 278 | holdout_primary_proposed |
| B42 | Accept | WH23122 发电设备专项检修的工作内容包括哪些？ | 279 | holdout_primary_proposed |
| B48 | Revise | 按《电信基础设施维护规程》第8.4.7.5条，清单漏项或非承包人原因的作业变更导致措施项目变化时，原措施费中已有项目和没有的项目分别如何调整？ | 91 | holdout_primary_proposed |
| B49 | Revise | 按《电信基础设施维护规程》第8.4.8.4条，维护分项作业费在综合单价未调整与已调整时，分别依据什么计算？ | 92 | holdout_primary_proposed |
| B50 | Revise | 按《电信基础设施维护规程》第8.4.7.8条，因不可抗力事件导致承包人的维护用机械（仪表）设备损坏及停工损失，由谁承担？ | 91 | holdout_primary_proposed |
| B53 | Revise | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.1，光网关零配置二维码必须集成设备的哪两项Wi-Fi参数？ | 60 | holdout_primary_proposed |
| B54 | Revise | 《智慧家庭装维工程与管理职业技能等级标准》初级等级“3.3 光路达标测试”的技能要求3.3.1和3.3.2分别是什么？ | 14 | holdout_primary_proposed |
| B57 | Revise | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.3的省级平台预置表，宁夏平台的TCP和UDP域名、端口各是什么？ | 64 | holdout_primary_proposed |
| P4-N01 | Accept | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.3.1.3节，光网关建立多条WAN连接时，连接间的数据应如何处理？路由WAN下两侧ARP报文又有何要求？ | 17 | holdout_primary_proposed |
| P4-N02 | Accept | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.3.4.3节，支持WPS Push-Button的客户端应在多长时间内完成协商并连接？WPS过程对已连接客户端有什么限制？ | 21 | holdout_primary_proposed |
| P4-N03 | Accept | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0的智能重启要求，已支持并开启该功能的终端能否采用固定重启时间？原文规定了什么例外？ | 30 | holdout_primary_proposed |
| P4-N04 | Accept | 在《中国移动智慧家庭全光组网产品技术规范》V2.0.0“Wi-Fi 7链路时延要求”的MLD链路测试场景中，UDP单向的链路平均时延与TP99时延分别须满足什么阈值？ | 43 | holdout_primary_proposed |
| P4-N05 | Accept | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.6.1.1节“光网关指示灯要求”，上行光信号状态灯熄灭和闪烁分别表示什么？ | 46 | holdout_primary_proposed |
| P4-N06 | Accept | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.8.10节，终端每个启动阶段何时才可执行下一阶段？安全签名校验未通过时怎么办？ | 54 | holdout_primary_proposed |
| P4-N07 | Accept | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.9.2.4节，全光组网终端升级软件时应具备什么校验功能？升级失败后应支持哪两种处理路径？ | 56 | holdout_primary_proposed |
| P4-N08 | Accept | 《智慧家庭装维工程与管理职业技能等级标准》第1章对人员培训、考核评价与人员聘用分别规定了怎样的适用或参照关系？ | 5 | holdout_primary_proposed |
| P4-N09 | Accept | 《智慧家庭装维工程与管理职业技能等级标准》第5.4节列出的智能组网专业基础知识有哪八项？ | 9 | holdout_primary_proposed |
| P4-N10 | Accept | 《智慧家庭装维工程与管理职业技能等级标准》第6.5节高级等级“2.4 智能家居技术”的两项技能要求是什么？ | 17 | holdout_primary_proposed |
| P4-N11 | Accept | 《电信基础设施维护规程》第4.3.4.2 b）规定，普通水线与海缆两侧各多大范围内禁止抛锚、捕鱼、炸鱼、挖砂等危及水线安全的活动？ | 23 | holdout_primary_proposed |
| P4-N12 | Accept | 《电信基础设施维护规程》第4.5.0.5 f）中，《光缆线路维护方案》的“四新”技术指哪四项？ | 28 | holdout_primary_proposed |
| P4-N13 | Accept | 《电信基础设施维护规程》第4.8.2.6 d）要求，进行光缆割接操作前与割接完毕离开现场前，分别须取得谁的什么确认？ | 34 | holdout_primary_proposed |
| P4-N14 | Accept | 《电信基础设施维护规程》第6.3.2.1规定，小型局站有线设备与传输线路专业以什么为维护界面？成端以内尾纤、传输设备和光缆成端及以外部分分别由谁负责？ | 63 | holdout_primary_proposed |
| P4-N15 | Accept | 按《电信基础设施维护规程》第3.35、3.36条，MSTP基于什么平台提供统一网管的多业务接入处理传送？ASON基于什么网络，并引入什么来按需分配资源？ | 12 | holdout_primary_proposed |

## 主选完整题答与证据

## B32

- 候选ID：`sha256:86abb5904cd3b7241c6bd1baa9dc3888ec11fa28135c1fcb518ec9b19a51ddf1`
- 待签版本ID：`p4-proposal-sha256:29988c1f182457553508da84bde4a0d5903274e45e6673fd6b38133622b33378`
- 审核记录SHA-256：`dde93eefa72efb52595a08a841e73428c7a8f55502685dab0e78b5425cc4a653`
- 题型／知识点：条款内容／语义／职业能力与学历
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：智慧家庭装维工程与管理职业技能等级标准.pdf：物理7，印刷6；文档版本：v_dcf78195a87f01f4。
- 原题：职业能力特征和受教育程度分别在哪个章节中说明？
- 原答：4.6 职业能力特征 .................................................................... 6 4.7 受教育程度 ...................................................................... 6
- **待签题目**：《智慧家庭装维工程与管理职业技能等级标准》第 4.6、4.7 节分别对职业能力特征和受教育程度提出了什么要求？
- **标准答案**：职业能力应具有学习、表达、计算、故障处置能力，动手能力和安全意识；受教育程度为高中、中等专业技术学校毕业及同等或以上学历。
- 审核理由：原题是目次定位题，答案直接复制目录行（含点线与页码），不是干净的答案；且物理页 2 的目录与物理页 7 的正文都写明 4.6／4.7，单 Chunk 唯一性不成立。改为问两节的实际要求，证据收敛到正文一块。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`d70540614c288a2dc8b3066f`
- 证据Chunk：`d70540614c288a2dc8b3066f`；全部证据要求：False。
- PDF入口：[智慧家庭装维工程与管理职业技能等级标准.pdf 第7物理页](../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=7)
- 全文证据：[证据目录](evidence_catalog.md#d70540614c288a2dc8b3066f)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B33

- 候选ID：`sha256:85516c936d8fe455b05be5cb507eabbdaf7aec41e0339101b9f7e34b688b65fc`
- 待签版本ID：`p4-proposal-sha256:aa85e47d7780dd977c86b5733af082eadaa607115e283230db8db3ed457d158e`
- 审核记录SHA-256：`d55f76a2bd97b31adcd027338d5371a62b4524a480bfb103104bc96935a2b428`
- 题型／知识点：条款内容／语义／职业技能鉴定
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：智慧家庭装维工程与管理职业技能等级标准.pdf：物理8，印刷7；文档版本：v_dcf78195a87f01f4。
- 原题：职业技能鉴定的申报条件和鉴定方式分别在哪个部分描述？
- 原答：4.9.1 申报条件 .................................................................... 6 4.9.2 鉴定方式 .................................................................... 6
- **待签题目**：《智慧家庭装维工程与管理职业技能等级标准》第 4.9.2.1 节规定，职业技能鉴定的鉴定方式应分为哪两类？
- **标准答案**：理论知识考试、技能考核。
- 审核理由：原题同样问「在哪个部分」，答案只有章节号；而 4.9.1 正文在物理页 7、4.9.2 正文在物理页 8，加上目次页共三块都与该问相关，证据无法收敛。改问 4.9.2.1 规定的鉴定方式类别，证据收敛到物理页 8 单块。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`14da1c09b687f7b48896e03a`
- 证据Chunk：`14da1c09b687f7b48896e03a`；全部证据要求：False。
- PDF入口：[智慧家庭装维工程与管理职业技能等级标准.pdf 第8物理页](../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=8)
- 全文证据：[证据目录](evidence_catalog.md#14da1c09b687f7b48896e03a)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B34

- 候选ID：`sha256:a9065f265727f73d5987f18a1b45172702509127e36212b003dfbcf857a24434`
- 待签版本ID：`p4-proposal-sha256:724ab60a6832f336236db13679e97ab28bd63de985c49c15dbb5f71a7000b9b5`
- 审核记录SHA-256：`5981f3f126ff927e62ff3749693a158c407b0e1632a7d013deec0c87954dc0dc`
- 题型／知识点：净距表／列错位／架空线路铁路净距
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理343，印刷337；文档版本：v_8ae9b63d869002c1。
- 原题：铁路与架空通信线路交越时的最小垂直净距是多少米？
- 原答：3.0
- **待签题目**：《电信基础设施维护规程》表 D.0.2 中，铁路与架空通信线路交越时，最低缆线到轨面的最小垂直净距是多少米？
- **标准答案**：7.5 m
- 审核理由：表 D.0.2 把「与线路方向平时时」与「与线路方向交越时」并列两列，铁路行的 3.0 属平时列，交越列为 7.5（备注「最低缆线到轨面」）。原答取了错误的列。题问本身可修，最小修订只改答案并补备注列限定。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`d8dfa78cb9362f0d69cd659c`
- 证据Chunk：`d8dfa78cb9362f0d69cd659c`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第343物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=343)
- 全文证据：[证据目录](evidence_catalog.md#d8dfa78cb9362f0d69cd659c)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B35

- 候选ID：`sha256:64e18eda64f9eb7f2bea1fd707d05c637ed7e13c0bec0c586200017cd4e7c894`
- 待签版本ID：`p4-proposal-sha256:4daf37a75b4a0af2d3070626e4470ebff2ea2befb3094e542b76bae17ab25a18`
- 审核记录SHA-256：`7fd155c51199c48e86ba62af98873022abc9dd85841418d855f294ccd99217ac`
- 题型／知识点：表格定位／语义／终端产品形态
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理15，印刷10；文档版本：v_ab72ce00c904f060。
- 原题：产品入库要求中包含哪些设备形态要求？
- 原答：设备形态
- **待签题目**：《中国移动智慧家庭全光组网产品技术规范》V2.0.0 表 4-1 中，全光组网终端的产品类型和设备形态名称分别有哪些？
- **标准答案**：产品类型分为光网关、光路由两类；产品名称分别为 Wi-Fi 7 光网关、Wi-Fi 6 光网关、Wi-Fi 7 光路由、Wi-Fi 6 光路由。
- 审核理由：原答复述目录小节标题「设备形态」，等于把问题原样返回，不构成答案；原引用证据是物理页 3 的目录，不是 4.2 节正文。改为问表 4-1 所列产品类型与形态名称，证据改到物理页 15 正文。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`e69ef87cafd302938c765e20`
- 证据Chunk：`e69ef87cafd302938c765e20`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第15物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=15)
- 全文证据：[证据目录](evidence_catalog.md#e69ef87cafd302938c765e20)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B40

- 候选ID：`sha256:bc83c840f1e8d89aa0229f2e8e30c808cbad720e93970135313bb16204ef083c`
- 待签版本ID：`p4-proposal-sha256:781f0debdb7943a99d5623f5f2e88347f4ae63afddebac433c1057991f213f95`
- 审核记录SHA-256：`a0025e6bb8390178d97a0664d10587309ac9dc9477c3032121e3546d20c53693`
- 题型／知识点：表级工作内容／精确实体／变压器维护工作
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理277，印刷271；文档版本：v_8ae9b63d869002c1。
- 原题：WH23120 安装、调试、断电检修变压器的工作内容包括哪些？
- 原答：工作内容：1、器检修：断电外观检查、接线柱及绝缘套管瓷瓶检查更换、呼吸器（吸湿器）硅胶检查更换、变压器油质检查更换； 2、变压器：开箱检验、体位固定、主件与配件清洗、附件检查与安装、补充注油、接地检查、接地、密封与电器实验； 3、变压器：开箱检验、体位固定、附件安装、接地、电气实验等。
- **待签题目**：WH23120 安装、调试、断电检修变压器的工作内容包括哪些？
- **标准答案**：工作内容：1、器检修：断电外观检查、接线柱及绝缘套管瓷瓶检查更换、呼吸器（吸湿器）硅胶检查更换、变压器油质检查更换； 2、变压器：开箱检验、体位固定、主件与配件清洗、附件检查与安装、补充注油、接地检查、接地、密封与电器实验； 3、变压器：开箱检验、体位固定、附件安装、接地、电气实验等。
- 审核理由：答案与表 10.3.3.20 表头「工作内容」三段逐字一致，编码 WH23120 唯一指向该表。原文「1、器检修」为 PDF 本身文字，非生成噪声，保留原样。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`647c44016cd2e8fabe51f5de`
- 证据Chunk：`647c44016cd2e8fabe51f5de`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第277物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=277)
- 全文证据：[证据目录](evidence_catalog.md#647c44016cd2e8fabe51f5de)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B41

- 候选ID：`sha256:b4948d39941b4842ce1cec733083400393f944fb78b0a646fb187b3468ccfce5`
- 待签版本ID：`p4-proposal-sha256:700bcbf118a5fb2d69726115f858255432c87fdaa462ea87ae3aae501c2b57a1`
- 审核记录SHA-256：`35a8619962ed48d16fc2f331d611a959e59f8752934030c2fe09082ea9600d11`
- 题型／知识点：表级工作内容／精确实体／控制设备维护工作
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理278，印刷272；文档版本：v_8ae9b63d869002c1。
- 原题：WH23121 安装与调试控制设备的工作内容是什么？
- 原答：工作内容：开箱检验、安装固定、附件检查与安装、连接线、清理现场等。
- **待签题目**：WH23121 安装与调试控制设备的工作内容是什么？
- **标准答案**：工作内容：开箱检验、安装固定、附件检查与安装、连接线、清理现场等。
- 审核理由：答案与表 10.3.3.21 表头「工作内容」逐字一致，编码 WH23121 唯一。与 B38、B40 属相邻表同构模板，但事实与目标 Chunk 均不同。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`4a65d0d3ead0bc841b1b28f8`
- 证据Chunk：`4a65d0d3ead0bc841b1b28f8`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第278物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=278)
- 全文证据：[证据目录](evidence_catalog.md#4a65d0d3ead0bc841b1b28f8)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B42

- 候选ID：`sha256:8b2d213a6a85dbee5975b9cc800f3c119222f1dd612bc93892999817cef85871`
- 待签版本ID：`p4-proposal-sha256:47749ec8b3196b6a2a7bfcf45cea8ae4be62f5acc1336912f0c7db56da87f69e`
- 审核记录SHA-256：`8e1f247939c0cfb2848fa809d726a43bdd71c56e02742e5befa99b8acb01b811`
- 题型／知识点：表级工作内容／精确实体／发电设备维护工作
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理279，印刷273；文档版本：v_8ae9b63d869002c1。
- 原题：WH23122 发电设备专项检修的工作内容包括哪些？
- 原答：工作内容：1、发电机组：检查清洁发动机和发电机外观、启动电池；检查补充燃油、润滑油和冷冻液；发电机空载试机；测试输出电压； 2、离网风力发电机组：停车检查；检修回转体；清洁添加设备轴承润滑油；发电机输电线插接头清洁更换； 3、能光伏离网发电系统：检查清洁太阳能光伏板阵列、检修防雹保护设施、光伏板支架和基础、密封胶条；清理排水系统、检查设置设备参数等。
- **待签题目**：WH23122 发电设备专项检修的工作内容包括哪些？
- **标准答案**：工作内容：1、发电机组：检查清洁发动机和发电机外观、启动电池；检查补充燃油、润滑油和冷冻液；发电机空载试机；测试输出电压； 2、离网风力发电机组：停车检查；检修回转体；清洁添加设备轴承润滑油；发电机输电线插接头清洁更换； 3、能光伏离网发电系统：检查清洁太阳能光伏板阵列、检修防雹保护设施、光伏板支架和基础、密封胶条；清理排水系统、检查设置设备参数等。
- 审核理由：答案与表 10.3.3.22「工作内容」三项逐字一致，编码 WH23122 唯一。第三项原文为「3、能光伏离网发电系统」，为 PDF 自身文字（同表行名作「太阳能光伏离网发电系统」），答案保留原文不改写。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`d2df450647a1e967aa910201`
- 证据Chunk：`d2df450647a1e967aa910201`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第279物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=279)
- 全文证据：[证据目录](evidence_catalog.md#d2df450647a1e967aa910201)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B48

- 候选ID：`sha256:1cb66bac6381fa7f068e3c89a5469e939babb508ee62c54f3b6ff24ee0272ca0`
- 待签版本ID：`p4-proposal-sha256:25fb17b4ee52178dea764c67bcc3d5bd7cd25edc8e76b32773c8b1971975b757`
- 审核记录SHA-256：`a8bacc6f84a01e1f8b822c1102c406f01a83fddf7ad7ef23b2c7d03d4abcc8b3`
- 题型／知识点：条件对照／措施项目变更
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理91，印刷85；文档版本：v_8ae9b63d869002c1。
- 原题：因维护分项作业工作量清单漏项或非承包人原因的维护作业变更，引起措施项目发生变化，原措施费中已有的措施项目，按原措施项目的组价方法如何调整？
- 原答：按原措施项目的组价方法调整
- **待签题目**：按《电信基础设施维护规程》第8.4.7.5条，清单漏项或非承包人原因的作业变更导致措施项目变化时，原措施费中已有项目和没有的项目分别如何调整？
- **标准答案**：已有项目按原措施项目的组价方法调整；没有的项目由承包人根据措施项目变更情况提出适当的措施费变更，经发包人确认后调整。
- 审核理由：原问已给出“按原措施项目的组价方法”，直接泄露答案。修订去掉提示，并对照条款的已有/没有两种情况，保留发包人确认条件。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`48e4aa1fce9c20c3d6f6339f`
- 证据Chunk：`48e4aa1fce9c20c3d6f6339f`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第91物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=91)
- 全文证据：[证据目录](evidence_catalog.md#48e4aa1fce9c20c3d6f6339f)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B49

- 候选ID：`sha256:b3cb46209708867debeabfffc91132b4d88fd613ee9017f7959edaa1a71a120f`
- 待签版本ID：`p4-proposal-sha256:ecb4839cc9b50349bf97ec93be80b15981dd32ad0beb7c184ce4b77d8cfe90c8`
- 审核记录SHA-256：`96f19e493ae47b2f1f3db49702885afa6b33fd0969639dfb7ab6b7f55a15f0e8`
- 题型／知识点：条件对照／维护作业费结算
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理92，印刷86；文档版本：v_8ae9b63d869002c1。
- 原题：维护分项作业费应依据什么进行计算？
- 原答：依据双方确认的工作量、合同约定的综合单价计算
- **待签题目**：按《电信基础设施维护规程》第8.4.8.4条，维护分项作业费在综合单价未调整与已调整时，分别依据什么计算？
- **标准答案**：未调整时依据双方确认的工作量、合同约定的综合单价计算；发生调整时，以发、承包双方确认调整的综合单价计算。
- 审核理由：原答只覆盖分号前的常规情况，泛化问法没有排除调整情形。修订纳入同条款后半句，不把普通情况当成完整规则。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`847ed8afec9fe78a708ad65f`
- 证据Chunk：`847ed8afec9fe78a708ad65f`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第92物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=92)
- 全文证据：[证据目录](evidence_catalog.md#847ed8afec9fe78a708ad65f)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B50

- 候选ID：`sha256:a20b570f5a28d69b3e7aebf3083c0cfe0b1913c34693320496fa4e5f345ac2e0`
- 待签版本ID：`p4-proposal-sha256:c6c54d473a64d73bc009f6b756730e19453d4ec566e6ee9604fc91e449b8a279`
- 审核记录SHA-256：`76c7e1297c6ce4ec0e430fab3e2c2bec7b2024f3787268cc7c303409714edb87`
- 题型／知识点：条件责任归属／不可抗力费用分担
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理91，印刷85；文档版本：v_8ae9b63d869002c1。
- 原题：承包人维护用机械（仪表）设备损坏及停工损失应由谁承担？
- 原答：由承包人承担；
- **待签题目**：按《电信基础设施维护规程》第8.4.7.8条，因不可抗力事件导致承包人的维护用机械（仪表）设备损坏及停工损失，由谁承担？
- **标准答案**：由承包人承担。
- 审核理由：原问缺少上位条款“因不可抗力事件导致”的前提，可能被误读为所有致损原因。补齐前提；不能将此答案当成现实合同责任咨询。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`48e4aa1fce9c20c3d6f6339f`
- 证据Chunk：`48e4aa1fce9c20c3d6f6339f`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第91物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=91)
- 全文证据：[证据目录](evidence_catalog.md#48e4aa1fce9c20c3d6f6339f)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B53

- 候选ID：`sha256:38376d247fabd496f655addd308a80ce91e133aa70c3d6108bb93404f33d0d2c`
- 待签版本ID：`p4-proposal-sha256:7ef45b339043fb53a9ba9ae54335bfc3e5cb54b635591346c3fabd0ef1608292`
- 审核记录SHA-256：`45e052574b5bc138d883842d36836191252d4588eab3db58b98cecc1616b20d4`
- 题型／知识点：参数集合／零配置二维码参数
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理60，印刷55；文档版本：v_ab72ce00c904f060。
- 原题：光网关终端通过二维码实现零配置功能时，二维码需要集成哪些参数
- 原答：二维码应集成该设备的Wi-Fi 的SSID 和密码参数
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.1，光网关零配置二维码必须集成设备的哪两项Wi-Fi参数？
- **标准答案**：该设备Wi-Fi的SSID和密码参数。
- 审核理由：两项参数在同一句中完整出现；补文档和A.1范围，避免与A.2光路由二维码的四字段格式混淆。SSID和密码两项均须答出。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`3a3f2c0bc27d1815ea693a4a`
- 证据Chunk：`3a3f2c0bc27d1815ea693a4a`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第60物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=60)
- 全文证据：[证据目录](evidence_catalog.md#3a3f2c0bc27d1815ea693a4a)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B54

- 候选ID：`sha256:1c41c10613d8867a8469f80d9d506a49a58357bcd7030fa9b1a07d4655c5386c`
- 待签版本ID：`p4-proposal-sha256:f6d2809e3597cc042108f7fa8f4569f618779a799920499862d5ae4e6697a3c7`
- 审核记录SHA-256：`a128dc2f03bbc96c78bd9ee8277c607328f59214b681c0e787d542e150de158f`
- 题型／知识点：等级技能枚举／初级光路测试能力
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：智慧家庭装维工程与管理职业技能等级标准.pdf：物理14，印刷13；文档版本：v_dcf78195a87f01f4。
- 原题：能使用红光光源、光功率计进行光路达标测试的具体要求是什么？
- 原答：3.3.1 能使用红光光源、光功率计
- **待签题目**：《智慧家庭装维工程与管理职业技能等级标准》初级等级“3.3 光路达标测试”的技能要求3.3.1和3.3.2分别是什么？
- **标准答案**：3.3.1：能使用红光光源、光功率计；3.3.2：能掌握手持终端的使用。
- 审核理由：原题的“具体要求”可被理解成操作步骤或阈值，但原表只列能力条目。修订限定初级、技能要求列和两项编号，不添加步骤、不混用相关知识列。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`95ae763cde2f43aec2cb7d14`
- 证据Chunk：`95ae763cde2f43aec2cb7d14`；全部证据要求：False。
- PDF入口：[智慧家庭装维工程与管理职业技能等级标准.pdf 第14物理页](../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=14)
- 全文证据：[证据目录](evidence_catalog.md#95ae763cde2f43aec2cb7d14)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B57

- 候选ID：`sha256:75f444c4a8d849e38771a34c0a5ad510d8b399a5381829f102e7632eb272a392`
- 待签版本ID：`p4-proposal-sha256:017f6ee5daa6caaeb13e3124e017cd762e8cdb1c44d46915ff7cfcc81c4abd4f`
- 审核记录SHA-256：`6442f5f43bd79c840fe7fb2c38a12333dde3d859c0340b6c0cf5be366a0f1ed7`
- 题型／知识点：实体协议映射／省级平台域名端口
- AI建议：Revise；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理64，印刷59；文档版本：v_ab72ce00c904f060。
- 原题：宁夏省级数字家庭管理平台智能组网模块的域名和端口是什么？
- 原答：jtwlgl.nx.chinamobile.com:9005(TCP) jtwlgl.nx.chinamobile.com:9007(UDP)
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.3的省级平台预置表，宁夏平台的TCP和UDP域名、端口各是什么？
- **标准答案**：TCP：jtwlgl.nx.chinamobile.com:9005；UDP：jtwlgl.nx.chinamobile.com:9007。
- 审核理由：原答两行正确；补冻结规范与预置表范围，要求域名、端口和协议对应完整。这里只核对冻结表，不验证网络可用性。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`9f8fb549d52c59eafb4ce394`
- 证据Chunk：`9f8fb549d52c59eafb4ce394`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第64物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=64)
- 全文证据：[证据目录](evidence_catalog.md#9f8fb549d52c59eafb4ce394)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N01

- 候选ID：`p4-candidate-sha256:dd6b70333689eace549807042500f8d50da44c9dfe46d4116c81128036b4ebed`
- 待签版本ID：`p4-proposal-sha256:a39463e72711fcbe304dc99448824be495a966121ca46aec9f32ad2ab387cdff`
- 审核记录SHA-256：`513ff4610b122b97519386687c80ad2fb78e14952db20993af68f94d1e30edd1`
- 题型／知识点：场景规则／WAN隔离
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理17，印刷12；文档版本：v_ab72ce00c904f060。
- 原题：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.3.1.3节，光网关建立多条WAN连接时，连接间的数据应如何处理？路由WAN下两侧ARP报文又有何要求？
- 原答：不同WAN连接之间的数据（包括DNS、ARP、管理应用数据等）应支持完全隔离；路由WAN连接下，应支持网络侧和用户侧ARP报文的隔离。
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.3.1.3节，光网关建立多条WAN连接时，连接间的数据应如何处理？路由WAN下两侧ARP报文又有何要求？
- **标准答案**：不同WAN连接之间的数据（包括DNS、ARP、管理应用数据等）应支持完全隔离；路由WAN连接下，应支持网络侧和用户侧ARP报文的隔离。
- 审核理由：两层隔离对象明确，同页两个完整句子；不把路由WAN的ARP限制扩展为所有网络流量。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`2d70309c35065f6a38c507ed`
- 证据Chunk：`2d70309c35065f6a38c507ed`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第17物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=17)
- 全文证据：[证据目录](evidence_catalog.md#2d70309c35065f6a38c507ed)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N02

- 候选ID：`p4-candidate-sha256:34439beb6b7301520ec3ef0800d2e9e30b94502b6894c6caf578d876e6565ccf`
- 待签版本ID：`p4-proposal-sha256:a70a061fdb85d4c296f34af00adfe5abc73234ce46ede89854e9ceb94a1793fc`
- 审核记录SHA-256：`cf03685133c89f146435149f28cd6679137ae2f6a1fdcd9af7916f82ed0c1857`
- 题型／知识点：时限与约束／WPS协商
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理21，印刷16；文档版本：v_ab72ce00c904f060。
- 原题：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.3.4.3节，支持WPS Push-Button的客户端应在多长时间内完成协商并连接？WPS过程对已连接客户端有什么限制？
- 原答：应在2分钟内协商好加密算法、分发密钥、配置好相关参数并建立连接；WPS过程不应影响已连接客户端的连接状态和数据传送。
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.3.4.3节，支持WPS Push-Button的客户端应在多长时间内完成协商并连接？WPS过程对已连接客户端有什么限制？
- **标准答案**：应在2分钟内协商好加密算法、分发密钥、配置好相关参数并建立连接；WPS过程不应影响已连接客户端的连接状态和数据传送。
- 审核理由：保留Push-Button适用范围，不把可选支持说成所有设备强制具备；时间与不干扰约束均有同页原文。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`84139f0d408339d51910bb1e`
- 证据Chunk：`84139f0d408339d51910bb1e`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第21物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=21)
- 全文证据：[证据目录](evidence_catalog.md#84139f0d408339d51910bb1e)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N03

- 候选ID：`p4-candidate-sha256:0dd1efdad9dc0232e3dbb02f955541f0c4330c0bffd862bc6e83376acffcf976`
- 待签版本ID：`p4-proposal-sha256:e6c4cc5720e12498b409525406711c6af9ef45bfd9ab37f46d0e1138de91cd12`
- 审核记录SHA-256：`80ef5cf9c7e76936e2389323a2ebd0553364a81ba7d15c773ec1db6650843785`
- 题型／知识点：例外条件／智能重启
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理30，印刷25；文档版本：v_ab72ce00c904f060。
- 原题：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0的智能重启要求，已支持并开启该功能的终端能否采用固定重启时间？原文规定了什么例外？
- 原答：智能重启功能禁止采用固定重启时间；用户通过和家亲APP或本地Web设置定时重启任务除外。
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0的智能重启要求，已支持并开启该功能的终端能否采用固定重启时间？原文规定了什么例外？
- **标准答案**：智能重启功能禁止采用固定重启时间；用户通过和家亲APP或本地Web设置定时重启任务除外。
- 审核理由：禁止规则与括号例外一起保留；不把出厂可选功能误作强制要求。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`38fdd5ab96a7a1c7db0c03c0`
- 证据Chunk：`38fdd5ab96a7a1c7db0c03c0`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第30物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=30)
- 全文证据：[证据目录](evidence_catalog.md#38fdd5ab96a7a1c7db0c03c0)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N04

- 候选ID：`p4-candidate-sha256:6dc4237449258788fc01e6e2ac54a60b9abc5e20800ee2cca950588de1dae44a`
- 待签版本ID：`p4-proposal-sha256:1b19ca3ea47985e536bd96015bb321fa1452f88b53419a995a4b10a75c12f1ad`
- 审核记录SHA-256：`24fa40e6ca6cb62c2c8690502da8c6c72a884c8f5e3b3271e8cd3996c10e8e52`
- 题型／知识点：双阈值辨析／Wi-Fi7链路时延
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理43，印刷38；文档版本：v_ab72ce00c904f060。
- 原题：在《中国移动智慧家庭全光组网产品技术规范》V2.0.0“Wi-Fi 7链路时延要求”的MLD链路测试场景中，UDP单向的链路平均时延与TP99时延分别须满足什么阈值？
- 原答：链路平均时延须小于5ms；链路TP99时延须小于25ms。
- **待签题目**：在《中国移动智慧家庭全光组网产品技术规范》V2.0.0“Wi-Fi 7链路时延要求”的MLD链路测试场景中，UDP单向的链路平均时延与TP99时延分别须满足什么阈值？
- **标准答案**：链路平均时延须小于5ms；链路TP99时延须小于25ms。
- 审核理由：明确链路时延测试场景，与紧邻的干扰周期变化测试分开；保留严格小于和ms单位。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`c9798c374ba5448e95e08c22`
- 证据Chunk：`c9798c374ba5448e95e08c22`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第43物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=43)
- 全文证据：[证据目录](evidence_catalog.md#c9798c374ba5448e95e08c22)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N05

- 候选ID：`p4-candidate-sha256:12dc07345e2a0ee36b202efad9553b4c74e58cf9954e684f693c6de794623484`
- 待签版本ID：`p4-proposal-sha256:7ad048d15ac3998e9b252f74c3d68712c4b8296aeb0f62446907ce323b940830`
- 审核记录SHA-256：`8af3664a434de384132d8b1172159b7a608e5c9b2bfc858d2a6c2cb616068def`
- 题型／知识点：状态映射／上行光信号指示灯
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理46，印刷41；文档版本：v_ab72ce00c904f060。
- 原题：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.6.1.1节“光网关指示灯要求”，上行光信号状态灯熄灭和闪烁分别表示什么？
- 原答：熄灭表示接收光功率正常；闪烁表示接收光功率异常。
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.6.1.1节“光网关指示灯要求”，上行光信号状态灯熄灭和闪烁分别表示什么？
- **标准答案**：熄灭表示接收光功率正常；闪烁表示接收光功率异常。
- 审核理由：按上行灯对应行核对，不套用电源灯或下行灯的熄灭含义。正文引用表4-12而该页实际表题为4-11，题面使用章节及表题避免错号。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`d60c3992acb84d003c25c027`
- 证据Chunk：`d60c3992acb84d003c25c027`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第46物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=46)
- 全文证据：[证据目录](evidence_catalog.md#d60c3992acb84d003c25c027)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N06

- 候选ID：`p4-candidate-sha256:d29f7757ee8f42f0525101b5a0a37c7706e1fb95e02b09148a6615d63012ddc1`
- 待签版本ID：`p4-proposal-sha256:6a887a494a46de75fad46483e8974ad011e540579c3fb8a80bf2510f0117645d`
- 审核记录SHA-256：`28c9fa930a3002227d5f814f33b3090b5a2c41cec8a1f7a4806d24f47a2bc7bd`
- 题型／知识点：失败分支／安全启动
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理54，印刷49；文档版本：v_ab72ce00c904f060。
- 原题：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.8.10节，终端每个启动阶段何时才可执行下一阶段？安全签名校验未通过时怎么办？
- 原答：每个启动阶段须校验下一个启动阶段的安全签名，校验通过后方可执行下一启动过程；否则设备停止启动或进入修复流程。
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.8.10节，终端每个启动阶段何时才可执行下一阶段？安全签名校验未通过时怎么办？
- **标准答案**：每个启动阶段须校验下一个启动阶段的安全签名，校验通过后方可执行下一启动过程；否则设备停止启动或进入修复流程。
- 审核理由：原文是“停止启动或进入修复流程”二选一，不增加自动重试或强制刷机。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`d74f298bf424e80db33f40c0`
- 证据Chunk：`d74f298bf424e80db33f40c0`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第54物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=54)
- 全文证据：[证据目录](evidence_catalog.md#d74f298bf424e80db33f40c0)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N07

- 候选ID：`p4-candidate-sha256:afb86e337d717969a9232ad176d53164f66c91b0fbefcb0ffa537bb93b049d55`
- 待签版本ID：`p4-proposal-sha256:e51b91599c4aa943de2131ce4b717898daa0480e4013246d5fcb31940d7b2cdb`
- 审核记录SHA-256：`c1a1e457d1849890d6ea10d7bc6520337963a1bdafb1e8eecebda6a020c8d8bb`
- 题型／知识点：失败恢复／软件远程升级
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理56，印刷51；文档版本：v_ab72ce00c904f060。
- 原题：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.9.2.4节，全光组网终端升级软件时应具备什么校验功能？升级失败后应支持哪两种处理路径？
- 原答：应具有容错校验功能；升级失败时应能恢复到原来的软件版本，或者连接管理平台接受再次升级。
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.9.2.4节，全光组网终端升级软件时应具备什么校验功能？升级失败后应支持哪两种处理路径？
- **标准答案**：应具有容错校验功能；升级失败时应能恢复到原来的软件版本，或者连接管理平台接受再次升级。
- 审核理由：保留两条可替代路径的“或者”关系，不要求两条依次执行。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`d1d75534f8865f49c152b4dd`
- 证据Chunk：`d1d75534f8865f49c152b4dd`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第56物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=56)
- 全文证据：[证据目录](evidence_catalog.md#d1d75534f8865f49c152b4dd)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N08

- 候选ID：`p4-candidate-sha256:0256829aae95d224589020ce66aa97cdcfae24c06c736b20d4130c49b61ced1e`
- 待签版本ID：`p4-proposal-sha256:e43c5f3ec8afe5c571bdd40d036fc3e9be611f7848485edcfe9aa8227ef74b0f`
- 审核记录SHA-256：`8bb3681e3d7356bb2a224479910d8f830d2a02a2b6da47c6f3fcb23ca9c7af44`
- 题型／知识点：适用范围／职业标准使用场景
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：智慧家庭装维工程与管理职业技能等级标准.pdf：物理5，印刷4；文档版本：v_dcf78195a87f01f4。
- 原题：《智慧家庭装维工程与管理职业技能等级标准》第1章对人员培训、考核评价与人员聘用分别规定了怎样的适用或参照关系？
- 原答：本文件适用于智慧家庭装维人员职业技能培训、考核与评价；人员聘用、培训与考核可参照执行。
- **待签题目**：《智慧家庭装维工程与管理职业技能等级标准》第1章对人员培训、考核评价与人员聘用分别规定了怎样的适用或参照关系？
- **标准答案**：本文件适用于智慧家庭装维人员职业技能培训、考核与评价；人员聘用、培训与考核可参照执行。
- 审核理由：区分“适用于”和“可参照执行”的措辞，不将征求意见稿解释为现行强制资质要求。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`2eda6960dfbb194d0f84e4b0`
- 证据Chunk：`2eda6960dfbb194d0f84e4b0`；全部证据要求：False。
- PDF入口：[智慧家庭装维工程与管理职业技能等级标准.pdf 第5物理页](../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=5)
- 全文证据：[证据目录](evidence_catalog.md#2eda6960dfbb194d0f84e4b0)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N09

- 候选ID：`p4-candidate-sha256:d316178fce530744b30cf51de524a5bd488fc52942e6454ad7dfb1bf636d79d7`
- 待签版本ID：`p4-proposal-sha256:ce059a32a795b9905f93a75db27c4130d780170cbd850915211782daa5fe9b2c`
- 审核记录SHA-256：`f4125337e08c74a5c38254a1bf8e308b2d827329644f03c9745e314703deff8a`
- 题型／知识点：知识集合／智能组网知识
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：智慧家庭装维工程与管理职业技能等级标准.pdf：物理9，印刷8；文档版本：v_dcf78195a87f01f4。
- 原题：《智慧家庭装维工程与管理职业技能等级标准》第5.4节列出的智能组网专业基础知识有哪八项？
- 原答：综合布线知识；通信网络技术及光纤到户业务知识；无线局域网技术知识；视听业务技术知识；智能控制技术知识；智能组网及家庭总线（数据、视听、控制）技术知识；智能家居、智能家电及联网、联动技术知识；家庭业务云平台及智能门户技术知识。
- **待签题目**：《智慧家庭装维工程与管理职业技能等级标准》第5.4节列出的智能组网专业基础知识有哪八项？
- **标准答案**：综合布线知识；通信网络技术及光纤到户业务知识；无线局域网技术知识；视听业务技术知识；智能控制技术知识；智能组网及家庭总线（数据、视听、控制）技术知识；智能家居、智能家电及联网、联动技术知识；家庭业务云平台及智能门户技术知识。
- 审核理由：同一页a-h八项闭合，不能拿紧邻第5.5节的全屋智能七项替代；与Development第5.7安全知识不同。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`5d1e8fd617217ecea2afa2f1`
- 证据Chunk：`5d1e8fd617217ecea2afa2f1`；全部证据要求：False。
- PDF入口：[智慧家庭装维工程与管理职业技能等级标准.pdf 第9物理页](../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=9)
- 全文证据：[证据目录](evidence_catalog.md#5d1e8fd617217ecea2afa2f1)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N10

- 候选ID：`p4-candidate-sha256:904c2b45e4d6fc1c015400d7cbbd1ca5f78638a598ff0f741801cd67c240ba20`
- 待签版本ID：`p4-proposal-sha256:394d92893892329f76d908e590df79cd3d197f944fef85db0db076d771ecec22`
- 审核记录SHA-256：`7df4f801f7779595383231ae25a3eceb9105890557230da69031befa0a2d1d03`
- 题型／知识点：等级技能枚举／高级智能家居技能
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：智慧家庭装维工程与管理职业技能等级标准.pdf：物理17，印刷16；文档版本：v_dcf78195a87f01f4。
- 原题：《智慧家庭装维工程与管理职业技能等级标准》第6.5节高级等级“2.4 智能家居技术”的两项技能要求是什么？
- 原答：2.4.1：能进行智能家居集中控制；2.4.2：能进行有线系统和无线系统拓展应用。
- **待签题目**：《智慧家庭装维工程与管理职业技能等级标准》第6.5节高级等级“2.4 智能家居技术”的两项技能要求是什么？
- **标准答案**：2.4.1：能进行智能家居集中控制；2.4.2：能进行有线系统和无线系统拓展应用。
- 审核理由：核对高级/技能要求列；不混用相关知识列的“系统架构”“家庭复合总线综合控制方式”，也不与中级架构题等同。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`f86d4474f6f6b987d29ada4c`
- 证据Chunk：`f86d4474f6f6b987d29ada4c`；全部证据要求：False。
- PDF入口：[智慧家庭装维工程与管理职业技能等级标准.pdf 第17物理页](../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=17)
- 全文证据：[证据目录](evidence_catalog.md#f86d4474f6f6b987d29ada4c)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N11

- 候选ID：`p4-candidate-sha256:65430c07a057e087a72eef9a588782399ea315ea60bdd9758d2ded7b0be77ec8`
- 待签版本ID：`p4-proposal-sha256:373132dd5a58bae0bbdf5c4f855e54af84bfda9c888c7b27adfb471a3560162a`
- 审核记录SHA-256：`e07ef11f436169ab18ff78ee3f7442b9964b45bccda076f38257414c0d55c7b4`
- 题型／知识点：范围与单位辨析／水线保护范围
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理23，印刷17；文档版本：v_8ae9b63d869002c1。
- 原题：《电信基础设施维护规程》第4.3.4.2 b）规定，普通水线与海缆两侧各多大范围内禁止抛锚、捕鱼、炸鱼、挖砂等危及水线安全的活动？
- 原答：普通水线两侧各100米；海缆两侧各2海里。
- **待签题目**：《电信基础设施维护规程》第4.3.4.2 b）规定，普通水线与海缆两侧各多大范围内禁止抛锚、捕鱼、炸鱼、挖砂等危及水线安全的活动？
- **标准答案**：普通水线两侧各100米；海缆两侧各2海里。
- 审核理由：保留“两侧各”与不同单位；不擅自换算海里或把海缆条件用于普通水线。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`002a1b9d6ade401fd6b92575`
- 证据Chunk：`002a1b9d6ade401fd6b92575`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第23物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=23)
- 全文证据：[证据目录](evidence_catalog.md#002a1b9d6ade401fd6b92575)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N12

- 候选ID：`p4-candidate-sha256:519d58d8c79cae8c81f666f92170f05f827687cc1e6d78e728a9317a1a020de1`
- 待签版本ID：`p4-proposal-sha256:2028f2cc5ef3ca0cbf5ad091ba5f3147cf09bd46ab09210856d2e7b1eb468a0f`
- 审核记录SHA-256：`ad3904e4cea51bbfa64d7fcb6d61c28374905121cbd936270f0e1080ade37bf9`
- 题型／知识点：术语集合／四新技术
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理28，印刷22；文档版本：v_8ae9b63d869002c1。
- 原题：《电信基础设施维护规程》第4.5.0.5 f）中，《光缆线路维护方案》的“四新”技术指哪四项？
- 原答：新技术、新材料、新工艺、新设备。
- **待签题目**：《电信基础设施维护规程》第4.5.0.5 f）中，《光缆线路维护方案》的“四新”技术指哪四项？
- **标准答案**：新技术、新材料、新工艺、新设备。
- 审核理由：条款、方案名称与四项闭合；不添加质量目标或安全措施等其他编制内容。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`ac65d74597a1d491a319475a`
- 证据Chunk：`ac65d74597a1d491a319475a`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第28物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=28)
- 全文证据：[证据目录](evidence_catalog.md#ac65d74597a1d491a319475a)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N13

- 候选ID：`p4-candidate-sha256:cfe761369558854150b13d1a16342db701b61abe59a4acf13e1a0f03736e03f5`
- 待签版本ID：`p4-proposal-sha256:c2d66637972892c7afa1b4c4b61339c4f5b28a7235222d68f2903142c71164dd`
- 审核记录SHA-256：`44158674ca2fb977fdc313be1d97b589d46b08a103b20bbc504ad5ef905ced61`
- 题型／知识点：操作前后条件／光缆割接确认
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理34，印刷28；文档版本：v_8ae9b63d869002c1。
- 原题：《电信基础设施维护规程》第4.8.2.6 d）要求，进行光缆割接操作前与割接完毕离开现场前，分别须取得谁的什么确认？
- 原答：割接操作前必须经运营企业网管人员确认，方可割接；割接完毕后必须经运营企业网管人员确认，方可离开现场。
- **待签题目**：《电信基础设施维护规程》第4.8.2.6 d）要求，进行光缆割接操作前与割接完毕离开现场前，分别须取得谁的什么确认？
- **标准答案**：割接操作前必须经运营企业网管人员确认，方可割接；割接完毕后必须经运营企业网管人员确认，方可离开现场。
- 审核理由：两个时点同为网管人员确认；不得用其他项的业务主管到场指挥代替。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`6f33bafc20e0ad09486add1b`
- 证据Chunk：`6f33bafc20e0ad09486add1b`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第34物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=34)
- 全文证据：[证据目录](evidence_catalog.md#6f33bafc20e0ad09486add1b)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N14

- 候选ID：`p4-candidate-sha256:1034d2e63b5dee4465460b56a8ad10af6fbae49d314f33815756db7fc2044cee`
- 待签版本ID：`p4-proposal-sha256:1c8f02290b77a14bca53b6d8b2125aa707dbfb753783d868a61284a9c94b8300`
- 审核记录SHA-256：`7ce8143b68f1c863db04008f7d63bf90c0ecb8a4aeea3d89d58eafd2712d39fa`
- 题型／知识点：责任边界／有线设备与线路专业界面
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理63，印刷57；文档版本：v_8ae9b63d869002c1。
- 原题：《电信基础设施维护规程》第6.3.2.1规定，小型局站有线设备与传输线路专业以什么为维护界面？成端以内尾纤、传输设备和光缆成端及以外部分分别由谁负责？
- 原答：以局站内ODF架或ODF单元成端为界；成端以内尾纤、传输设备等由本专业（小型局站有线设备）负责；光缆线路成端（含终端盒、法兰盘等）及成端以外的传输线路部分由线路专业负责。
- **待签题目**：《电信基础设施维护规程》第6.3.2.1规定，小型局站有线设备与传输线路专业以什么为维护界面？成端以内尾纤、传输设备和光缆成端及以外部分分别由谁负责？
- **标准答案**：以局站内ODF架或ODF单元成端为界；成端以内尾纤、传输设备等由本专业（小型局站有线设备）负责；光缆线路成端（含终端盒、法兰盘等）及成端以外的传输线路部分由线路专业负责。
- 审核理由：保留成端本身属于线路专业的包含关系；不混用下一条无线专业的ODF/DDF框界面。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`6bf394ec756103a82e9f6e9c`
- 证据Chunk：`6bf394ec756103a82e9f6e9c`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第63物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=63)
- 全文证据：[证据目录](evidence_catalog.md#6bf394ec756103a82e9f6e9c)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## P4-N15

- 候选ID：`p4-candidate-sha256:99a7d854e627e650d9ae0dcefef78d70ec0560c62d8ab52948cd4055b4e19140`
- 待签版本ID：`p4-proposal-sha256:9dabe3bae6dc2baa0029a6c52b7b15a4fec8b0add1a427671bd3a316411194df`
- 审核记录SHA-256：`8e1480d8d26b9ed605a27a556040c921e3395579e4517a588d97316bcd94a7bb`
- 题型／知识点：相近术语对照／MSTP与ASON
- AI建议：Accept；筛选：holdout_primary_proposed。
- 来源：电信基础设施维护规程.pdf：物理12，印刷6；文档版本：v_8ae9b63d869002c1。
- 原题：按《电信基础设施维护规程》第3.35、3.36条，MSTP基于什么平台提供统一网管的多业务接入处理传送？ASON基于什么网络，并引入什么来按需分配资源？
- 原答：MSTP基于SDH平台；ASON以光传送网（OTN）为基础，在光传送网中引入控制平面，实现网络资源按需分配。
- **待签题目**：按《电信基础设施维护规程》第3.35、3.36条，MSTP基于什么平台提供统一网管的多业务接入处理传送？ASON基于什么网络，并引入什么来按需分配资源？
- **标准答案**：MSTP基于SDH平台；ASON以光传送网（OTN）为基础，在光传送网中引入控制平面，实现网络资源按需分配。
- 审核理由：同页相邻术语对照，三个要点均有原文，避免把SDH与OTN或管理平面与控制平面混淆。
- Holdout选择说明：事实独立、无Development证据Chunk交集；拟优先集中签核
- 相关Chunk：`258ef2b78ff022814a5dd780`
- 证据Chunk：`258ef2b78ff022814a5dd780`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第12物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=12)
- 全文证据：[证据目录](evidence_catalog.md#258ef2b78ff022814a5dd780)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```


## 备选与需裁决记录

## B23

- 候选ID：`sha256:0f3b338e277722ef4de67a59096d7e8c931138eb05c300808fc9d2ea9a186468`
- 待签版本ID：`p4-proposal-sha256:a433cbe72f160fcb4bc499fa586e50c39f58b8bd42198251edcf7f4a509ec026`
- 审核记录SHA-256：`99b04f59b23b5fb747a7ec313d9dad1023743dc9adf4c678c5be561e166e67e0`
- 题型／知识点：术语辨析／WLAN链路层鉴权
- AI建议：Revise；筛选：reserve_development_overlap。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理52，印刷47；文档版本：v_ab72ce00c904f060。
- 原题：WLAN应支持哪些链路层鉴权方式？
- 原答：WLAN 应支持Open System 和Pre-Shared Key 两种链路层鉴权方式。
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.8.4节第1项，全光组网终端的WLAN应支持哪两种链路层鉴权方式？
- **标准答案**：Open System和Pre-Shared Key。
- 审核理由：沿用P2-Gold-07复核：只限第1项的两种链路层鉴权，不纳入第2项WPA系列及AES/TKIP加密模式；旧“保留测试”不构成有效批准。
- Holdout选择说明：与Development证据Chunk重叠；可扩充Development，默认不进入本轮Holdout
- 相关Chunk：`81951fb8b5e157346ed83d77`
- 证据Chunk：`81951fb8b5e157346ed83d77`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第52物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=52)
- 全文证据：[证据目录](evidence_catalog.md#81951fb8b5e157346ed83d77)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B28

- 候选ID：`sha256:9a72d01ef8f3b71904144877056fb2cf2f9ee7b02801140c14be922bb5fd8e9f`
- 待签版本ID：`p4-proposal-sha256:eb111d18e66b2e9d74262f59c5c1ed6419ec5a6c0c818ee92361037aec465715`
- 审核记录SHA-256：`e92507c7ba8c3d3103be097ab98d919aaffc467b06420333ed39c682f02fa9dc`
- 题型／知识点：价格表定位／精确实体／铁塔维修单价
- AI建议：Accept；筛选：reserve_development_overlap。
- 来源：电信基础设施维护规程.pdf：物理286，印刷280；文档版本：v_8ae9b63d869002c1。
- 原题：角钢塔、三管塔、四管塔35m以下铁塔专项维修的综合单价是多少？
- 原答：291.84
- **待签题目**：角钢塔、三管塔、四管塔35m以下铁塔专项维修的综合单价是多少？
- **标准答案**：291.84
- 审核理由：表 10.3.3.29 中 WH23129001 行名称即「角钢塔、三管塔、四管塔35m 以下」，综合单价列 291.84，与相邻 35m 以上行 395.81 可区分。问句自带范围限定，答案唯一。
- Holdout选择说明：与Development证据Chunk重叠；可扩充Development，默认不进入本轮Holdout
- 相关Chunk：`611a9eb6554a2b482561c775`
- 证据Chunk：`611a9eb6554a2b482561c775`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第286物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=286)
- 全文证据：[证据目录](evidence_catalog.md#611a9eb6554a2b482561c775)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B29

- 候选ID：`sha256:2769ae9af89aab01bd8aead8897e96ebbe6e4f64ef305bcd59780fb192171860`
- 待签版本ID：`p4-proposal-sha256:edb3fa6e8c74e9d8be8b6b879043c3efa2465cf2e32fa447dc1f9bfaed2b0fc3`
- 审核记录SHA-256：`da7d5a099263299110ecc38064133cdc5b4624c8356c78325da8bfb4fde017f0`
- 题型／知识点：价格表定位／语义／环境清理单价
- AI建议：Accept；筛选：reserve_development_overlap。
- 来源：电信基础设施维护规程.pdf：物理287，印刷281；文档版本：v_8ae9b63d869002c1。
- 原题：机房室外环境清理中，一体化机柜的综合单价是多少？
- 原答：18.24
- **待签题目**：机房室外环境清理中，一体化机柜的综合单价是多少？
- **标准答案**：18.24
- 审核理由：表 10.3.3.30（WH23130 机房室外环境清理）WH23130002 行名「一体化机柜」，综合单价 18.24。同名「一体化机柜」在其它表价格不同，本题靠表名限定消歧，成立。
- Holdout选择说明：与Development证据Chunk重叠；可扩充Development，默认不进入本轮Holdout
- 相关Chunk：`a264a91966d85e2ec3b52e02`
- 证据Chunk：`a264a91966d85e2ec3b52e02`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第287物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=287)
- 全文证据：[证据目录](evidence_catalog.md#a264a91966d85e2ec3b52e02)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B30

- 候选ID：`sha256:0691d0137cbe702a2ec0ed5fa33ab55628575d96781bf456d853a7d6d10191fe`
- 待签版本ID：`p4-proposal-sha256:9660cfa56deb0e63fab7bfdba1e6b137d044a19e69078b164859e39a398efe85`
- 审核记录SHA-256：`2c24625376fbeacd3908e89de9c1142b794bc3dbe7dd0f63b30cccbde5b3d6fa`
- 题型／知识点：附录条款／字段映射／二维码字段映射
- AI建议：Accept；筛选：reserve_development_overlap。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理61，印刷56；文档版本：v_ab72ce00c904f060。
- 原题：二维码内容中，Wi-Fi名称需要与设备背面板的哪个字段一致？
- 原答：默认无线网络名称
- **待签题目**：二维码内容中，Wi-Fi名称需要与设备背面板的哪个字段一致？
- **标准答案**：默认无线网络名称
- 审核理由：附录 A.2 二维码内容第（1）项 ssid1 明文规定「需与设备背面板的“默认无线网络名称”一致」，答案逐字可核，且与该页 wifipwd／username／userpwd 四项字段各自对应的取值互不混淆。
- Holdout选择说明：与Development证据Chunk重叠；可扩充Development，默认不进入本轮Holdout
- 相关Chunk：`c120df3a569ae215d69183ac`
- 证据Chunk：`c120df3a569ae215d69183ac`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第61物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=61)
- 全文证据：[证据目录](evidence_catalog.md#c120df3a569ae215d69183ac)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B31

- 候选ID：`sha256:e74e6386379043f840835ab6571daade945ae870605a1d5f46da3dae7a977264`
- 待签版本ID：`p4-proposal-sha256:6e8978927961a3979a98c61b2e8862fb68d07b5eaba5eaed3b1cbaaa295eb128`
- 审核记录SHA-256：`c2fd2e481b672f496f2d7cbc8af1a6528c38ae3d82a75ff1496ba5104f48d794`
- 题型／知识点：封面著录／语义／占位日期
- AI建议：Reject；筛选：exclude_ai_reject。
- 来源：智慧家庭装维工程与管理职业技能等级标准.pdf：物理1，未标印刷页；文档版本：v_dcf78195a87f01f4。
- 原题：该标准的发布和实施日期是什么？
- 原答：XXXX-XX-XX 发布 XXXX-XX-XX 实施
- **待签题目**：该标准的发布和实施日期是什么？
- **标准答案**：XXXX-XX-XX 发布 XXXX-XX-XX 实施
- 审核理由：该文件封面标注「（征求意见稿）」，发布与实施日期均为未填写的模板占位符 XXXX-XX-XX，全语料不存在任何真实日期；问句要求的是日期，答案只能复述占位符，不构成可验证事实。且「该标准」无题面先行词。
- Holdout选择说明：既有AI建议驳回；待人工最终裁决
- 相关Chunk：空（AI建议驳回）
- 证据Chunk：`71a4f239a4fd7b69fdc74486`；全部证据要求：False。
- PDF入口：[智慧家庭装维工程与管理职业技能等级标准.pdf 第1物理页](../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=1)
- 全文证据：[证据目录](evidence_catalog.md#71a4f239a4fd7b69fdc74486)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B36

- 候选ID：`sha256:5d42c5b4ccd006231d17ae08a942cef1de654e37e64092884cae899a372110b4`
- 待签版本ID：`p4-proposal-sha256:a749061be8e49f7f646d52355412465b09eb27e516af7889a98062b106d63e46`
- 审核记录SHA-256：`4025a344fd2ac5b4d277c92ddfa3f19f0ca70d01c8345f1f881610122cb1f321`
- 题型／知识点：权重表定位／精确实体／实操权重
- AI建议：Accept；筛选：reserve_development_overlap。
- 来源：智慧家庭装维工程与管理职业技能等级标准.pdf：物理19，印刷18；文档版本：v_dcf78195a87f01f4。
- 原题：智慧家庭装维工程与管理实操技能权重表中，业务开通和业务运维在高级阶段的权重是多少？
- 原答：35
- **待签题目**：智慧家庭装维工程与管理实操技能权重表中，业务开通和业务运维在高级阶段的权重是多少？
- **标准答案**：35
- 审核理由：7.2 实操技能权重表中「业务开通和业务运维」行高级列为 35；问句已限定表名与技能等级，未与 7.1 理论表同项混淆。
- Holdout选择说明：与Development证据Chunk重叠；可扩充Development，默认不进入本轮Holdout
- 相关Chunk：`02c18b66c8c7d17fa1fb910e`
- 证据Chunk：`02c18b66c8c7d17fa1fb910e`；全部证据要求：False。
- PDF入口：[智慧家庭装维工程与管理职业技能等级标准.pdf 第19物理页](../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=19)
- 全文证据：[证据目录](evidence_catalog.md#02c18b66c8c7d17fa1fb910e)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B37

- 候选ID：`sha256:7fe4ebfaf574ebd0825e8f2d4541c494239212b9c9f0c0dac94fb989a2eecf2d`
- 待签版本ID：`p4-proposal-sha256:4a916af76cbabe6e194023a8fdb0ce9b044f8fd254e771e6a1183ad0204ba01d`
- 审核记录SHA-256：`0526ea0ddf685f14a25286e9f6364875f2e0d34dd2a94fb680a7001268c6522d`
- 题型／知识点：权重表定位／精确实体／理论权重
- AI建议：Accept；筛选：reserve_development_overlap。
- 来源：智慧家庭装维工程与管理职业技能等级标准.pdf：物理19，印刷18；文档版本：v_dcf78195a87f01f4。
- 原题：初级等级中，通信基础知识在理论知识权重表中的占比是多少
- 原答：25
- **待签题目**：初级等级中，通信基础知识在理论知识权重表中的占比是多少
- **标准答案**：25
- 审核理由：7.1 理论知识权重表中「通信基础知识」行初级列为 25；问句已限定等级与表名。题面缺问号属格式瑕疵，不影响可答性。
- Holdout选择说明：与Development证据Chunk重叠；可扩充Development，默认不进入本轮Holdout
- 相关Chunk：`02c18b66c8c7d17fa1fb910e`
- 证据Chunk：`02c18b66c8c7d17fa1fb910e`；全部证据要求：False。
- PDF入口：[智慧家庭装维工程与管理职业技能等级标准.pdf 第19物理页](../data/%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E8%A3%85%E7%BB%B4%E5%B7%A5%E7%A8%8B%E4%B8%8E%E7%AE%A1%E7%90%86%E8%81%8C%E4%B8%9A%E6%8A%80%E8%83%BD%E7%AD%89%E7%BA%A7%E6%A0%87%E5%87%86.pdf#page=19)
- 全文证据：[证据目录](evidence_catalog.md#02c18b66c8c7d17fa1fb910e)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B38

- 候选ID：`sha256:2bbfb4a82fec1d093c88df135fb2f44eae2c0a27dcfd428bd8b7db7788180a76`
- 待签版本ID：`p4-proposal-sha256:e0f275ec01884e905cb0fb7bc46fc66bd64992acfb7ddc1e8f9ed6d1734ca365`
- 审核记录SHA-256：`54cacedb79c76130e931cd8ae4ff6e408f7aff4210a7ba25e13cea38c56264e5`
- 题型／知识点：易混淆／多证据／工作内容合并
- AI建议：Revise；筛选：exclude_fact_union。
- 来源：电信基础设施维护规程.pdf：物理277，印刷271；电信基础设施维护规程.pdf：物理278，印刷272；文档版本：v_8ae9b63d869002c1。
- 原题：安装、调试、断电检修变压器和安装与调试控制设备的工作内容分别是什么？
- 原答：开箱检验、安装固定、附件检查与安装、连接线、清理现场等。
- **待签题目**：《电信基础设施维护规程》表 10.3.3.20（WH23120）与表 10.3.3.21（WH23121）的工作内容分别是什么？
- **标准答案**：表 10.3.3.20（WH23120 安装、调试、断电检修变压器）：1、器检修：断电外观检查、接线柱及绝缘套管瓷瓶检查更换、呼吸器（吸湿器）硅胶检查更换、变压器油质检查更换；2、变压器：开箱检验、体位固定、主件与配件清洗、附件检查与安装、补充注油、接地检查、接地、密封与电器实验；3、变压器：开箱检验、体位固定、附件安装、接地、电气实验等。表 10.3.3.21（WH23121 安装与调试控制设备）：开箱检验、安装固定、附件检查与安装、连接线、清理现场等。
- 审核理由：题问「分别」，原答只给出安装与调试控制设备（WH23121）一项，漏掉安装、调试、断电检修变压器（WH23120）的三段工作内容，属答案不完整。两块证据都在冻结语料内，可最小修订补齐。
- Holdout选择说明：修订后的事实集合=B40∪B41；不作为额外独立题计数
- 相关Chunk：`647c44016cd2e8fabe51f5de`, `4a65d0d3ead0bc841b1b28f8`
- 证据Chunk：`647c44016cd2e8fabe51f5de`, `4a65d0d3ead0bc841b1b28f8`；全部证据要求：True。
- PDF入口：[电信基础设施维护规程.pdf 第277物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=277)；[电信基础设施维护规程.pdf 第278物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=278)
- 全文证据：[证据目录](evidence_catalog.md#647c44016cd2e8fabe51f5de)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B39

- 候选ID：`sha256:d2bbc8a14069a7efff2b77ffee9522792c095fafbdfdad8ee4e8fa53a21a6f39`
- 待签版本ID：`p4-proposal-sha256:0055eb49cf5e16f713338997988c0f46b1d14dded0654b81e4c44597f17d37ad`
- 审核记录SHA-256：`1ea01a91000a5b90bc1121b054d1538e0c89788bee0e74654c16df1901417613`
- 题型／知识点：易混淆／多证据／不对称比较
- AI建议：Reject；筛选：exclude_ai_reject。
- 来源：电信基础设施维护规程.pdf：物理277，印刷271；电信基础设施维护规程.pdf：物理279，印刷273；文档版本：v_8ae9b63d869002c1。
- 原题：发电设备专项检修和安装油浸电力100kVA以下变压器在工作内容上有什么不同？
- 原答：发电机组：检查清洁发动机和发电机外观、启动电池；检查补充燃油、润滑油和冷冻液；发电机空载试机；测试输出电压；
- **待签题目**：发电设备专项检修和安装油浸电力100kVA以下变压器在工作内容上有什么不同？
- **标准答案**：发电机组：检查清洁发动机和发电机外观、启动电池；检查补充燃油、润滑油和冷冻液；发电机空载试机；测试输出电压；
- 审核理由：比较对象不对称——「安装油浸电力100kVA以下变压器」是表 10.3.3.20 内的一行项目，本身没有独立工作内容，其工作内容只能取整表三段；把它与表 10.3.3.22 的整表工作内容并列比较，前提不成立。原答又只列发电机组一项，既未给变压器侧也未给差异。且该表事实已被 B40、B42 覆盖。
- Holdout选择说明：既有AI建议驳回；待人工最终裁决
- 相关Chunk：空（AI建议驳回）
- 证据Chunk：`647c44016cd2e8fabe51f5de`, `d2df450647a1e967aa910201`；全部证据要求：True。
- PDF入口：[电信基础设施维护规程.pdf 第277物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=277)；[电信基础设施维护规程.pdf 第279物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=279)
- 全文证据：[证据目录](evidence_catalog.md#647c44016cd2e8fabe51f5de)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B43

- 候选ID：`sha256:e13b3e08b91f8ecc93a8f721859cde4e7d28675abb53ff5249a4334925abce47`
- 待签版本ID：`p4-proposal-sha256:983f9bfc932b378c167626940eba9dc4fe290dc3fe0a72f45571fe83a34eab36`
- 审核记录SHA-256：`7cd305d5530314ad544112db57ba6a7b82ab69be4bc89e6a7e2918f598732c5d`
- 题型／知识点：价格表定位／控制设备更换单价
- AI建议：Accept；筛选：holdout_reserve_proposed。
- 来源：电信基础设施维护规程.pdf：物理278，印刷272；文档版本：v_8ae9b63d869002c1。
- 原题：WH23121004 带电更换熔断器/空开的综合单价是多少？
- 原答：175.10
- **待签题目**：WH23121004 带电更换熔断器/空开的综合单价是多少？
- **标准答案**：175.10
- 审核理由：WH23121004 在表10.3.3.21 的综合单价列为175.10；人工费109.44 是另一列，计量单位为只。
- Holdout选择说明：题答可核且无Development证据块交集；价格或同块简短题暂列备选
- 相关Chunk：`4a65d0d3ead0bc841b1b28f8`
- 证据Chunk：`4a65d0d3ead0bc841b1b28f8`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第278物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=278)
- 全文证据：[证据目录](evidence_catalog.md#4a65d0d3ead0bc841b1b28f8)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B44

- 候选ID：`sha256:450131450e1fd2c9b087c8d9990ec5667dc54c25c979b4fb5929307174570c36`
- 待签版本ID：`p4-proposal-sha256:6a1b6f931fa3d68a50f60097862e349af77bf683296b6655e434c8fb5ae22ef3`
- 审核记录SHA-256：`d68f698da86d46936a68fa083d974185444f045bee6f6856f1eac1136ffcf5d8`
- 题型／知识点：价格表定位／控制设备安装单价
- AI建议：Accept；筛选：holdout_reserve_proposed。
- 来源：电信基础设施维护规程.pdf：物理278，印刷272；文档版本：v_8ae9b63d869002c1。
- 原题：WH23121002 带电安装熔断器的综合单价是多少？
- 原答：120.38
- **待签题目**：WH23121002 带电安装熔断器的综合单价是多少？
- **标准答案**：120.38
- 审核理由：WH23121002 行综合单价120.38；相邻断路器行105.79 不可替代，计量单位为只。
- Holdout选择说明：题答可核且无Development证据块交集；价格或同块简短题暂列备选
- 相关Chunk：`4a65d0d3ead0bc841b1b28f8`
- 证据Chunk：`4a65d0d3ead0bc841b1b28f8`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第278物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=278)
- 全文证据：[证据目录](evidence_catalog.md#4a65d0d3ead0bc841b1b28f8)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B45

- 候选ID：`sha256:de211868b35c7ce7c3fc759a17333f5829c97542cbfdafcadbb0445afc020266`
- 待签版本ID：`p4-proposal-sha256:be9cd5f8c712e98c66702e141b3e3ed9ba2aa0b74fc1e44c878d14d57083322f`
- 审核记录SHA-256：`353ba131447a9087e431f34f8bd703476e0ada8fd90dad52c292211d47ede1d0`
- 题型／知识点：作业内容枚举／离网风机检修
- AI建议：Accept；筛选：alternative_subset。
- 来源：电信基础设施维护规程.pdf：物理279，印刷273；文档版本：v_8ae9b63d869002c1。
- 原题：发电设备专项检修中，离网风力发电机组的检修内容有哪些？
- 原答：停车检查；检修回转体；清洁添加设备轴承润滑油；发电机输电线插接头清洁更换；
- **待签题目**：发电设备专项检修中，离网风力发电机组的检修内容有哪些？
- **标准答案**：停车检查；检修回转体；清洁添加设备轴承润滑油；发电机输电线插接头清洁更换；
- 审核理由：表10.3.3.22 工作内容第2项逐项包含原答四个动作；事实是B42答案的子集，签核可选其一，不累计为新增独立覆盖。
- Holdout选择说明：题答可核，但事实是B42子集；可替换B42，不与其重复累计覆盖
- 相关Chunk：`d2df450647a1e967aa910201`
- 证据Chunk：`d2df450647a1e967aa910201`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第279物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=279)
- 全文证据：[证据目录](evidence_catalog.md#d2df450647a1e967aa910201)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B46

- 候选ID：`sha256:d3109d6f7c5c9e35cef41bc51a466b88a5710a071e90e19c393e7ec18be79879`
- 待签版本ID：`p4-proposal-sha256:c009f90915cb5e72c63fc13fe2ae77a1e574ecaf52d5ff77367fe7efd0829388`
- 审核记录SHA-256：`f9e768461ef6c75ee29eb986cbf90d1589060db494f3081e060df79cffdbb643`
- 题型／知识点：作业内容枚举／光伏发电检修
- AI建议：Accept；筛选：alternative_subset。
- 来源：电信基础设施维护规程.pdf：物理279，印刷273；文档版本：v_8ae9b63d869002c1。
- 原题：太阳能光伏离网发电系统专项检修包括哪些工作内容？
- 原答：检查清洁太阳能光伏板阵列、检修防雹保护设施、光伏板支架和基础、密封胶条；清理排水系统、检查设置设备参数等。
- **待签题目**：太阳能光伏离网发电系统专项检修包括哪些工作内容？
- **标准答案**：检查清洁太阳能光伏板阵列、检修防雹保护设施、光伏板支架和基础、密封胶条；清理排水系统、检查设置设备参数等。
- 审核理由：工作内容第3项列出原答；原件该项题头漏“太阳”二字，同表WH23122003行名完整，不能把源文件笔误误判成模型补造。事实为B42子集。
- Holdout选择说明：题答可核，但事实是B42子集；可替换B42，不与其重复累计覆盖
- 相关Chunk：`d2df450647a1e967aa910201`
- 证据Chunk：`d2df450647a1e967aa910201`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第279物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=279)
- 全文证据：[证据目录](evidence_catalog.md#d2df450647a1e967aa910201)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B47

- 候选ID：`sha256:be11ad9c57042e53066edc836c22ea22c1df359c8f46d7bc09e5beca283fdef2`
- 待签版本ID：`p4-proposal-sha256:8b9e92d293c3a87c909a66909aa25d954928bf7e89cd2eba461f146038bf05f9`
- 审核记录SHA-256：`71a8b1b40e6743b04591a26890beade4bcbbbefdb1dc626000c463024283311d`
- 题型／知识点：协议参数辨析／802.11be调制
- AI建议：Accept；筛选：reserve_development_overlap。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理25，印刷20；文档版本：v_ab72ce00c904f060。
- 原题：全光组网终端支持IEEE 802.11be协议时，须支持什么调制方式？
- 原答：须支持4096 QAM
- **待签题目**：全光组网终端支持IEEE 802.11be协议时，须支持什么调制方式？
- **标准答案**：须支持4096 QAM
- 审核理由：物理页25 的4.3.4.9 第1项明确须支持4096 QAM；相邻802.11ax条款为1024-QAM，协议限定可消歧。与Development B05共用证据块。
- Holdout选择说明：与Development证据Chunk重叠；可扩充Development，默认不进入本轮Holdout
- 相关Chunk：`4812f97659f77c46891223fa`
- 证据Chunk：`4812f97659f77c46891223fa`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第25物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=25)
- 全文证据：[证据目录](evidence_catalog.md#4812f97659f77c46891223fa)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B51

- 候选ID：`sha256:7b3828d049462c38db624dc89d1733b296d18c8673d71242117f95c3413f7e8c`
- 待签版本ID：`p4-proposal-sha256:36fdee4eadd77d3cd656e2668bd0ab291a8ce366ccf9c2c38f3afd311a7d8b30`
- 审核记录SHA-256：`84915e4c25cc9d2394dfe2b95d085631b5a5fcdff5d96a7191aec58191afa016`
- 题型／知识点：可靠性约束／MTBF与长期运行
- AI建议：Revise；筛选：reserve_development_overlap。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理58，印刷53；文档版本：v_ab72ce00c904f060。
- 原题：MTBF（平均无故障工作时间）至少应达到多少小时以上？
- 原答：30000 小时以上
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.11.1节，MTBF的时长要求及长时间运行的业务表现要求分别是什么？
- **标准答案**：MTBF至少应达到30000小时以上；长时间运行时不应出现业务中断或性能下降。
- 审核理由：原答数值正确；修订明确文档范围并保留原文“至少…以上”，不擅改为严格大于关系。与Development B09共块，作扩充Development备选。
- Holdout选择说明：与Development证据Chunk重叠；可扩充Development，默认不进入本轮Holdout
- 相关Chunk：`9b5d9b92dc528a1c594e3ec2`
- 证据Chunk：`9b5d9b92dc528a1c594e3ec2`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第58物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=58)
- 全文证据：[证据目录](evidence_catalog.md#9b5d9b92dc528a1c594e3ec2)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B52

- 候选ID：`sha256:8d25da17cd828fdd5a472d80f1de41390f9e26616d31ff42715c6436e79fff2b`
- 待签版本ID：`p4-proposal-sha256:4ccb2e148e7eb3158c97df2c70b24336cbffcda3fa98aef14f61022851f5e4e5`
- 审核记录SHA-256：`a616e18701836315d1586695ddc6847d584656041680c16f53ba358e1f79a91f`
- 题型／知识点：功能定位／二维码零配置功能
- AI建议：Revise；筛选：holdout_reserve_proposed。
- 来源：中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf：物理60，印刷55；文档版本：v_ab72ce00c904f060。
- 原题：光网关终端应支持通过二维码实现什么功能？
- 原答：放装零配置功能
- **待签题目**：按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.1，光网关终端应支持通过二维码实现什么功能？
- **标准答案**：放装零配置功能。
- 审核理由：原件与Chunk均为“放装零配置”，不擅自改成“安装”；补文档范围，与B53是同块不同属性，简短功能题作备选。
- Holdout选择说明：题答可核且无Development证据块交集；价格或同块简短题暂列备选
- 相关Chunk：`3a3f2c0bc27d1815ea693a4a`
- 证据Chunk：`3a3f2c0bc27d1815ea693a4a`；全部证据要求：False。
- PDF入口：[中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf 第60物理页](../data/%E4%B8%AD%E5%9B%BD%E7%A7%BB%E5%8A%A8%E6%99%BA%E6%85%A7%E5%AE%B6%E5%BA%AD%E5%85%A8%E5%85%89%E7%BB%84%E7%BD%91%E4%BA%A7%E5%93%81%E6%8A%80%E6%9C%AF%E8%A7%84%E8%8C%83V2.0.0.pdf#page=60)
- 全文证据：[证据目录](evidence_catalog.md#3a3f2c0bc27d1815ea693a4a)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B55

- 候选ID：`sha256:672fe784fc33b88b4fb7660dcda841815d3c30a876eb39164ce3909a9d765374`
- 待签版本ID：`p4-proposal-sha256:4b72f68e2fb5c90c6210bac3ad2c4605888e374609ff56b36ac70ac27879b0cd`
- 审核记录SHA-256：`027fdf9e080c218fed2bdcbd8d71643bc26dd5126c0e87e16a930675f858555b`
- 题型／知识点：价格表定位／UPS安装单价
- AI建议：Accept；筛选：holdout_reserve_proposed。
- 来源：电信基础设施维护规程.pdf：物理281，印刷275；文档版本：v_8ae9b63d869002c1。
- 原题：WH23124001 安装调试交流不间断电源 10kVA 以下的综合单价是多少？
- 原答：970.37
- **待签题目**：WH23124001 安装调试交流不间断电源 10kVA 以下的综合单价是多少？
- **标准答案**：970.37
- 审核理由：表10.3.3.24 WH23124001 的综合单价为970.37元/台；606.48 是人工费；相邻模块化UPS机柜为419.52。
- Holdout选择说明：题答可核且无Development证据块交集；价格或同块简短题暂列备选
- 相关Chunk：`596a9b3e94b415e67eba817e`
- 证据Chunk：`596a9b3e94b415e67eba817e`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第281物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=281)
- 全文证据：[证据目录](evidence_catalog.md#596a9b3e94b415e67eba817e)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```

## B56

- 候选ID：`sha256:5972f5480aeed3b4b705cc948d70c8ac5034cd30cb5c1ca0f9c2c08206a17c99`
- 待签版本ID：`p4-proposal-sha256:af9ae495db1ad6f80ce447d0a5138baf3c1d3c17b394ec826d6697054732fdc2`
- 审核记录SHA-256：`14b3d415befaf292022194379bfe482aefa21889e293a2f9093f1133617e54a0`
- 题型／知识点：价格表定位／开关电源安装单价
- AI建议：Accept；筛选：holdout_reserve_proposed。
- 来源：电信基础设施维护规程.pdf：物理282，印刷276；文档版本：v_8ae9b63d869002c1。
- 原题：安装开关电源设备中，一体化壁挂式型号的综合单价是多少？
- 原答：747.84
- **待签题目**：安装开关电源设备中，一体化壁挂式型号的综合单价是多少？
- **标准答案**：747.84
- 审核理由：表10.3.3.25 WH23125003 一体化壁挂式综合单价747.84元/台；落地式510.72、组合式1123.58，行列可区分。
- Holdout选择说明：题答可核且无Development证据块交集；价格或同块简短题暂列备选
- 相关Chunk：`1559140c5ae20df70e73c42a`
- 证据Chunk：`1559140c5ae20df70e73c42a`；全部证据要求：False。
- PDF入口：[电信基础设施维护规程.pdf 第282物理页](../data/%E7%94%B5%E4%BF%A1%E5%9F%BA%E7%A1%80%E8%AE%BE%E6%96%BD%E7%BB%B4%E6%8A%A4%E8%A7%84%E7%A8%8B.pdf#page=282)
- 全文证据：[证据目录](evidence_catalog.md#1559140c5ae20df70e73c42a)。

```text
human_decision:
human_reviewer:
human_reviewed_at:
human_comment:
```
