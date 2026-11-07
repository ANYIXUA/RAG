# B28–B42 简洁签核表

沿用P2-Gold-07：Accept 8、Revise 5、Reject 2；均为AI建议。原审核结论未被本轮筛选意见覆盖。人工输入请统一在工作簿“签核”填写。

| 编号 | AI建议 | 待签题目 | 来源物理页 | 筛选 |
| --- | --- | --- | --- | --- |
| B28 | Accept | 角钢塔、三管塔、四管塔35m以下铁塔专项维修的综合单价是多少？ | 286 | reserve_development_overlap |
| B29 | Accept | 机房室外环境清理中，一体化机柜的综合单价是多少？ | 287 | reserve_development_overlap |
| B30 | Accept | 二维码内容中，Wi-Fi名称需要与设备背面板的哪个字段一致？ | 61 | reserve_development_overlap |
| B31 | Reject | 该标准的发布和实施日期是什么？ | 1 | exclude_ai_reject |
| B32 | Revise | 《智慧家庭装维工程与管理职业技能等级标准》第 4.6、4.7 节分别对职业能力特征和受教育程度提出了什么要求？ | 7 | holdout_primary_proposed |
| B33 | Revise | 《智慧家庭装维工程与管理职业技能等级标准》第 4.9.2.1 节规定，职业技能鉴定的鉴定方式应分为哪两类？ | 8 | holdout_primary_proposed |
| B34 | Revise | 《电信基础设施维护规程》表 D.0.2 中，铁路与架空通信线路交越时，最低缆线到轨面的最小垂直净距是多少米？ | 343 | holdout_primary_proposed |
| B35 | Revise | 《中国移动智慧家庭全光组网产品技术规范》V2.0.0 表 4-1 中，全光组网终端的产品类型和设备形态名称分别有哪些？ | 15 | holdout_primary_proposed |
| B36 | Accept | 智慧家庭装维工程与管理实操技能权重表中，业务开通和业务运维在高级阶段的权重是多少？ | 19 | reserve_development_overlap |
| B37 | Accept | 初级等级中，通信基础知识在理论知识权重表中的占比是多少 | 19 | reserve_development_overlap |
| B38 | Revise | 《电信基础设施维护规程》表 10.3.3.20（WH23120）与表 10.3.3.21（WH23121）的工作内容分别是什么？ | 277; 278 | exclude_fact_union |
| B39 | Reject | 发电设备专项检修和安装油浸电力100kVA以下变压器在工作内容上有什么不同？ | 277; 279 | exclude_ai_reject |
| B40 | Accept | WH23120 安装、调试、断电检修变压器的工作内容包括哪些？ | 277 | holdout_primary_proposed |
| B41 | Accept | WH23121 安装与调试控制设备的工作内容是什么？ | 278 | holdout_primary_proposed |
| B42 | Accept | WH23122 发电设备专项检修的工作内容包括哪些？ | 279 | holdout_primary_proposed |

B38保留原Revise记录，但与B40/B41的事实并集重复，不新增独立覆盖。B28/B29/B30/B36/B37共享Development证据块，默认列Development扩充备选。B34须核对铁路行“交越”列7.5m；B32/B33/B35修订改变证据目标页。
