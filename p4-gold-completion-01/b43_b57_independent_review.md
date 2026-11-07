# B43–B57 独立审核

2026-11-05（Asia/Shanghai）。本轮AI从冻结Chunk及对应PDF原文开始核对，未用Pilot排序或模型答案作判定依据。独立指源证据优先审核，不代表人工签核或第二名审核人。

Accept 7、Revise 8、Reject 0。B45/B46可回答，但为B42事实子集，作为替换题而非新增独立覆盖。

| 编号 | AI建议 | 待签题目 | 来源物理页 | 筛选 |
| --- | --- | --- | --- | --- |
| B43 | Accept | WH23121004 带电更换熔断器/空开的综合单价是多少？ | 278 | holdout_reserve_proposed |
| B44 | Accept | WH23121002 带电安装熔断器的综合单价是多少？ | 278 | holdout_reserve_proposed |
| B45 | Accept | 发电设备专项检修中，离网风力发电机组的检修内容有哪些？ | 279 | alternative_subset |
| B46 | Accept | 太阳能光伏离网发电系统专项检修包括哪些工作内容？ | 279 | alternative_subset |
| B47 | Accept | 全光组网终端支持IEEE 802.11be协议时，须支持什么调制方式？ | 25 | reserve_development_overlap |
| B48 | Revise | 按《电信基础设施维护规程》第8.4.7.5条，清单漏项或非承包人原因的作业变更导致措施项目变化时，原措施费中已有项目和没有的项目分别如何调整？ | 91 | holdout_primary_proposed |
| B49 | Revise | 按《电信基础设施维护规程》第8.4.8.4条，维护分项作业费在综合单价未调整与已调整时，分别依据什么计算？ | 92 | holdout_primary_proposed |
| B50 | Revise | 按《电信基础设施维护规程》第8.4.7.8条，因不可抗力事件导致承包人的维护用机械（仪表）设备损坏及停工损失，由谁承担？ | 91 | holdout_primary_proposed |
| B51 | Revise | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.11.1节，MTBF的时长要求及长时间运行的业务表现要求分别是什么？ | 58 | reserve_development_overlap |
| B52 | Revise | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.1，光网关终端应支持通过二维码实现什么功能？ | 60 | holdout_reserve_proposed |
| B53 | Revise | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.1，光网关零配置二维码必须集成设备的哪两项Wi-Fi参数？ | 60 | holdout_primary_proposed |
| B54 | Revise | 《智慧家庭装维工程与管理职业技能等级标准》初级等级“3.3 光路达标测试”的技能要求3.3.1和3.3.2分别是什么？ | 14 | holdout_primary_proposed |
| B55 | Accept | WH23124001 安装调试交流不间断电源 10kVA 以下的综合单价是多少？ | 281 | holdout_reserve_proposed |
| B56 | Accept | 安装开关电源设备中，一体化壁挂式型号的综合单价是多少？ | 282 | holdout_reserve_proposed |
| B57 | Revise | 按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.3的省级平台预置表，宁夏平台的TCP和UDP域名、端口各是什么？ | 64 | holdout_primary_proposed |

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
