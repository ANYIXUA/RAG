"""P7 static audit only: local JSON reads, literal corpus scan, evidence assembly.
No app imports, model/API calls, retrieval execution, or historical writes.
Editorial decisions below are AI preliminary notes, never human sign-off.
"""
import json, hashlib, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
CORPUS = ROOT / 'storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl'
CASES = ROOT / 'p6-silver-e2e-500/silver_cases_500.jsonl'
RUN = ROOT / 'p6-silver-e2e-500/runs/p6-e2e-run-01-qwen-flash'
def readj(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
corpus = [json.loads(x) for x in CORPUS.read_text(encoding='utf-8').splitlines() if x.strip()]
cases = [json.loads(x) for x in CASES.read_text(encoding='utf-8').splitlines() if x.strip()]
ci = {x['chunk_id']: dict(x, corpus_line=n) for n,x in enumerate(corpus,1)}
assert len(ci)==447 and sha(CORPUS)=='5995ee6be2871ee7c553ce5fe2f3002a7938dbffedf0ec2b8fed28af8107f4d6'

# Short evidence aliases are editorial navigation, not replacement chunk IDs.
E = {
 'service': ('f46c137628395834914932ea','要对施工的经济性'),
 'quality': ('33e38d557c3eacc533550efa','7.7.2 维护质量'),
 'appointment': ('4fce0b1cd8d9e372161536d0','7.4 宽带'),
 'scope': ('2eda6960dfbb194d0f84e4b0','本文件适用于'),
 'exam': ('14da1c09b687f7b48896e03a','4.9.2.1'),
 'weights': ('02c18b66c8c7d17fa1fb910e','7 权重表'),
 'scene': ('48ecc091e26caaa3ccbd3be5','4.5 智能家居'),
 'design': ('c10a8b3b89210595f9880fc6','3.2 基础网络优化'),
 'protocol': ('c10a8b3b89210595f9880fc6','4.3 物联网接入'),
 'sales': ('1c317b1dd2cebfbf9647d03e','服务能力'),
 'control': ('5d1e8fd617217ecea2afa2f1','5.5 全屋智能'),
 'mesh': ('3b1f839571de44bb1abd2f94','为确保多个'),
 'meshdetail': ('5183d18205e64c4836ba9020','允许通过光纤'),
 'shape': ('e69ef87cafd302938c765e20','4.2. 设备形态'),
 'product': ('4723262fed91f6b5026a5480','移动全家Wi-Fi'),
 'remote': ('d1d75534f8865f49c152b4dd','4.9.2.2.'),
 'cost': ('784c5042f0d4ecb73acfe695','9.2 电信'),
 'costdetail': ('375b8a8c8d53610084ffb7c3','综合单价包括'),
 'costdefinition': ('b113827b54593ec6085a7bbc','3.60 维护成本'),
 'wake': ('3c9c81f21d4df15d5cb812c4','Beacon'),
 'trigger': ('b656aa1e5d609e2de7a81a0d','通过平台触发'),
 'survey': ('2ec236820167f2d1a720a4a9','站址业主回访'),
 'partner': ('2a7f16b2864963c72902351f','产品推广案例'),
}
groups = {
 'price':['价格','定价','资费','月费','套餐','促销','账单','优惠','报价'],
 'staff':['绩效','考核','评价','权重','质量指标','及时率','聘用','人员'],
 'experience':['满意','服务质量','交付','投诉','沟通','故障','优化'],
 'scene':['触发','场景设置','联动','语音助手','唤醒','协议','智能家居'],
 'interop':['跨品牌','品牌','厂商','兼容','互操作','EasyMesh','协议','联调','协同'],
 'market':['市场','营销','推广','销售','渗透','计划','转化'],
 'subsidy':['补贴','补助','报销','申请','财务','费用'],
 'cost':['成本','费用','综合单价','人工费','材料','机械','维护分项'],
 'selection':['设备形态','光网关','光路由','设计','需求','方案','最优','组合'],
}
# id | group | proposal | reviewed aliases | rationale | ambiguity/missing | answer audit
DATA = [
('0236','price','retain_pending_human','product service','业务介绍只列终端、装维服务和线上应用组合，用户指导要求介绍资费；未给套餐目录、组合价格或最优比较。','“套餐”是资费套餐还是技术组合未明；需运营商、地区、预算、候选套餐。','现答把组网知识当套餐选择原则，未限定无价格依据。'),
('0237','staff','revise_partial_qualify','scope exam weights quality','职业标准明确可供人员聘用培训考核参照，给出理论/实操和等级权重；质量规程列及时率等。可提供限定的能力与服务质量评估依据。','职业技能鉴定不等于雇主薪酬绩效；组织KPI权重、周期仍缺。','现答直接把职业鉴定称员工绩效，需加适用范围限定。'),
('0243','experience','revise_bounded_answer','service quality remote','规范直接规定规范交付、用户使用指导、投诉处理与质量改进；远程诊断可支撑设备故障处理，能回答改善体验的受限措施。','不得承诺满意度增幅；需区分家庭设备体验和站址业主调查。','现答可有部分依据，但“提升掌控感”等因果解释不是原文实测。'),
('0244','price','retain_pending_human','product service','产品规范介绍业务和技术要求，服务规程要求解释资费，却未给智慧家庭产品线最新价格策略。','“最新”需要有效日期及运营商政策；冻结文本不证明当前策略。','现答拒绝提供价格策略合理；“所有文档不含价格”不能推广到含工程计价的全库。'),
('0255','scene','retain_pending_human','scene control trigger','职业标准要求具备场景设置能力，触发命中是无线快连指令开启热点4分钟，不能回答家居自动化条件配置步骤。','需具体平台/APP/设备及触发规则；原财务与报销分类错误。','现答重复能力要求，没有提供设置步骤；不能把知识要求当操作指南。'),
('0256','interop','retain_pending_human','shape mesh product','规范可列Wi-Fi与接口要求，但未给各品牌路由器实测、价格或排名，无法判哪个更值得推荐。','品牌、型号、预算、户型及需求缺失；可另给限定选型指标。','现答把入库要求改写为中国移动品牌推荐，不能支持最值得推荐。'),
('0264','interop','revise_partial_qualify','protocol mesh meshdetail','职业标准含常用协议联调适配，产品规范给互操作、Controller/Agent及回传规则，可回答规范范围的协同原则。','不支持任意跨品牌兼容承诺；需品牌型号、协议和平台。','现答统一协议与模型设计可作原则，但需明示不能保证任意品牌协同。'),
('0265','experience','revise_partial_qualify','service quality survey','家庭装维质量统计、安装及时率、故障修复及时率和重复故障率可作为服务评价依据；全文满意度调查命中多为站址业主。','未给家庭用户满意度问卷、采样、评分或阈值；站址业主不等于家庭用户。','现答将沟通技巧直接当满意度测量机制，证据不充分。'),
('0266','market','retain_pending_human','sales partner quality','语料有销售技巧、产品推广案例作为入库证明，以及服务质量改进；没有用户渗透率定义、目标或增长策略。','不能把维护技能推出用户转化效果；需市场目标、渠道与用户数据。','现答“提升转化率”缺直接支撑。'),
('0277','market','retain_pending_human','sales partner product','有销售技巧和推广案例材料要求，但没有营销渠道、客群、预算、投放及策略优化方法。','问题是市场策略，原“具体设备流程”理由错位。','现答技术技能清单无法作为市场推广优化策略证据。'),
('0278','price','retain_pending_human','shape costdetail','设备规格表没有品牌价格；维护人工单价不是不同品牌智慧家庭产品售价。','虽是一般性“是否存在差异”，也不能用常识替代冻结语料中的品牌价格证据。','现答限定缺价格对比依据适当。'),
('0279','staff','retain_pending_human','scope exam weights','职业标准可提供技能考核流程和合格线，却没有“近期”企业绩效制度版本。','需企业、岗位、考核期；草案职业标准不能当最新薪酬KPI。','现答区分职业技能鉴定与具体绩效细则，限定较合理。'),
('0291','scene','retain_pending_human','wake control scene','“唤醒”命中为STA省电及TWT，不是语音助手唤醒词；场景能力要求无唤醒词菜单或配置方法。','需具体语音助手及型号；原价格促销类别错误。','现答“场景设置包含唤醒词配置”无直接证据，需删除或待核实。'),
('0292','interop','revise_partial_qualify','mesh meshdetail protocol','全光终端通过Multi-AP/EasyMesh互操作，角色、WPS/DPP、光纤优先回传都有明确内容。','“设备”可指家电，也可指FTTR；无缝互联不可推广为所有设备。','现答前四点在全光终端限定下可答，不能泛化整个家居生态。'),
('0293','subsidy','retain_pending_human','costdetail appointment','费用章节有人工费和夜间作业补助费定义、材料管理有手续，但未给家庭安装补贴的员工申请资格和发放流程。','费用补偿构成不等于员工安装补贴；需具体单位政策。','现答拒答方向合理，不能用全库无任何补助条款作理由。'),
('0310','staff','revise_partial_qualify','quality scope weights','质量规程要求企业制定质量考核办法，定期统计并分析改进；职业等级维度可供考核设计参考。','能提出有来源的设计维度，不能生成现行企业绩效权重和奖惩。','现答把职业合格线替代绩效标准；且“60分以上”应为60分及以上。'),
('0311','market','retain_pending_human','sales partner','销售能力及提供推广案例不构成产品线促销策略、优惠幅度或调整流程。','需具体活动、价目、预算、授权政策。','现答拒绝制定促销调整较适当。'),
('0312','market','retain_pending_human','quality product','月度生产质量分析和新业务规范更新可支撑维护计划调整，但无市场趋势数据或市场对齐机制。','生产工作计划不等于市场计划；须补充趋势与需求证据。','现答将技能清单称为匹配市场需求，因果和流程依据不足。'),
('0324','price','retain_pending_human','service costdetail product','用户指导提及资费与缴费渠道，工程人工单价则为维护计价；均无设备月费计费公式。','需套餐、计费周期、租购方式；不能用工程费用替换月费。','现答第4点猜测服务包/订阅应移除，其余限定有依据。'),
('0325','subsidy','retain_pending_human','costdetail scope','费用构成可含补助和财务费用，职业文件可供人员考核，但未提供员工家庭设备补贴申请流程。','员工福利与施工费用补偿不同；需雇主政策。','现答保持未知较合理。'),
('0338','scene','revise_partial_qualify','design protocol scene','高级要求包括网络优化、常用协议联调适配和系统故障处理，中级含场景设置，可构成优化检查方向。','仅能力要求和原则，没有特定家居平台联动参数及逐步操作。','现答部分基于能力要求；模型搭建并非自动证明联动体验变好。'),
('0339','experience','revise_bounded_answer','service appointment quality','预约敬语、规范安装交付、用户指导、投诉优先级与质量统计改进都直接覆盖装维服务。','不能将完工签字等同满意度测量，也无提升幅度保证。','现答大部分是可支持的规范措施，原无答案理由过宽。'),
('0340','interop','revise_partial_qualify','protocol mesh remote','语料有协议适配、终端故障诊断与全光终端统一控制要求，可限定说明协同维护方式。','缺具体品牌兼容矩阵，平台接口存在不代表任意跨品牌均可。','现答“统一接口实现跨品牌”推断需要限定设备范围。'),
('0348','price','retain_pending_human','cost costdetail','全库存在维护计价标准和费用构成，但并未按服务品牌提供装维报价差异。','品牌/地区/工程量需确定；费用标准不是零售价比较。','现答“所有文档非定价内容”仅对检索集可能成立，全库有工程计价，需缩窄表述。'),
('0349','staff','revise_partial_qualify','quality scope weights','可基于服务质量指标及职业能力维度提供评价参考，原“人事不在范围”与适用范围文字相冲突。','员工绩效评分权重、周期与奖惩仍不在已读证据。','现答技能维度有依据，但不宜称已规定的员工绩效制度。'),
('0364','interop','revise_partial_qualify','mesh meshdetail protocol','EasyMesh互操作及常用协议联调适配为局部答案，不应将跨品牌主题整项排除。','仅适用遵循规范的终端；任意品牌家电兼容未证实。','现答将全光终端规范直接宣称跨品牌通用机制，需范围限定。'),
('0365','staff','retain_pending_human','quality scope sales','服务质量指标和人员能力考核可供参考，但没有绩效与家庭服务的绑定关系、公式或奖惩。','“绑定”可能是工单、薪酬或绩效挂钩，需明确。','现答提示具体机制缺失正确，列出的可能关系不能算正式制度。'),
('0379','staff','revise_partial_qualify','scope weights design','职业标准把全屋智能、智能组网及运维列为考核维度，可解释设备相关技能如何进入人员能力评价。','设备本身如何影响人事KPI没有因果或权重制度；应明确能力评价与HR绩效之别。','现答“设备能力影响岗位绩效”是推断，须限定为可参照的技能考核。'),
('0380','experience','revise_partial_qualify','quality service survey','规程给服务质量指标且要求制定质量考核评定办法；但满意度调查命中属于站址业主，未给家庭用户满意度评分标准。','服务及时率、完工确认、主观满意度是不同指标；需所问评分制度。','现答把完工确认单当满意度评估标准，证据不成立。'),
('0381','market','retain_pending_human','quality partner product','运维质量分析支持月度工作计划；产品文档有推广案例要求，但没有运维与市场组织协同流程。','产品平台“策略”是网络管理策略，不能替代市场策略。','现答QoS和平台策略下发答非所问。'),
('0393','price','retain_pending_human','cost costdetail','规程提供统一维护费用类别与单价；缺品牌维度报价数据，不能输出跨品牌费用标准比较。','需相同工程量、地区、服务范围和含税口径。','现答拒绝品牌对比合理，但“无费用明细”不能外推全库。'),
('0394','staff','revise_partial_qualify','quality service weights','装维质量指标与质量考核规定可支持服务评价参考，但没有员工绩效中满意度的计分转换。','服务质量与用户满意度不能等同；需问卷和绩效权重。','现答将服务质量统计当满意度评定依据，需指出非完整评分法。'),
('0407','selection','revise_partial_qualify','service appointment design','规范要求按住宅环境和线路条件综合考虑施工经济性、安全、维护便利与用户满意度；技能标准覆盖组网方案设计。','最优需要用户约束；问题未提品牌，原跨品牌理由凭空增加限定。','现答可给受限设计依据，但不是唯一最优方案。'),
('0408','experience','revise_bounded_answer','service quality design','用户指导、投诉闭环、维护质量指标改进以及网络覆盖优化能支撑运维改善体验的规范措施。','无满意度实测增幅，也不能把技能要求当完整操作步骤。','现答已有部分支持，原市场策略排除理由过宽。'),
('0409','cost','revise_partial_qualify','cost costdetail costdefinition','费用编制章节明确列维护作业、材料备件、机械仪表、措施、规费、安全生产、其他项目和税；综合单价包含人工、管理和利润。','该结构适用电信基础设施维护，不能声称覆盖全部智能家电或具体企业实际成本占比。','现答只列施工活动而漏费用结构；全库存在比检索结果更直接的答案。'),
('0418','price','retain_pending_human','partner product costdetail','入库材料含推广案例，维护文件给人工单价，但没有各品牌市场定价方法。','技术入库统一规范不意味着统一售价。','现答缺市场定价依据的限定合理。'),
('0434','staff','revise_partial_qualify','scope exam weights quality','职业标准明示可参照进行人员考核，理论/实操与职级权重、服务质量指标足以给限定参考。','不能把职业鉴定权重作为企业正式绩效权重。','现答将技能鉴定等同人员绩效，需修订边界。'),
('0435','price','retain_pending_human','service product partner','规范要求指导资费与缴费渠道，但无促销活动、折扣规则、账单计算或时间条件。','原“无直接关联”不是被证实事实，应写资料未给关联规则。','现答保持未知较合理。'),
('0447','price','retain_pending_human','cost costdetail protocol','联动技术要求及统一维护费用构成均不提供不同品牌装维报价。','需品牌、地区、服务内容和计价口径；不能由跨品牌技术协同推导价格。','现答限定缺品牌价格资料较合理。'),
('0448','subsidy','retain_pending_human','scope costdetail quality','人员考核与费用章节分别存在，但没有绩效结果和财务报销审批的联动条款。','财务费用类别不等于报销流程；需组织制度和审批权限。','现答保持未知较合理。'),
('0458','staff','revise_partial_qualify','scope weights quality','职业能力分级及服务质量评价可以提供员工考核参考；“不在财务报销范围”与问题无关。','应确认问职业能力还是雇主人事绩效。','现答技能和安全维度有依据，但应标为可参照而非既定KPI。'),
('0478','price','retain_pending_human','shape costdetail','产品规范列设备类别与接口，费用文件列维护人工单价；没有不同品牌智能设备售价比较。','需具体品牌型号、日期及报价。','现答拒绝编造价格合理。'),
('0480','staff','revise_partial_qualify','quality exam weights','质量统计、分析、改进和企业制定考核办法，以及理论/实操鉴定方式，可支撑流程设计参考。','没有绩效结果应用、复核、申诉、奖金流程；不能把职业考核流程视为完整团队绩效流程。','现答只列权重项目，未提供完整流程，且需说明参考性质。'),
('0483','experience','revise_bounded_answer','design protocol remote service','网络接入/带宽/覆盖优化、故障诊断、协议适配及用户指导都是直接相关能力和规范措施。','优化效果需具体环境验证；原理由把体验优化归为人事绩效不成立。','现答主要措施在限定范围内有证据，不宜仅因无拒答打失败。'),
('0484','price','retain_pending_human','partner costdetail product','推广案例只是资质材料，工程计价不是设备市场策略；没有品牌间价格策略对比依据。','需品牌市场定位和活动政策。','现答限定信息不足合理。'),
('0486','experience','revise_bounded_answer','appointment service quality','预约联系、规范交付、使用指导、投诉处理及持续质量改进直接支持用户服务体验优化。','具体业务、用户痛点及目标未给，可先给规范内原则；与人事考核不是同一问题。','现答有部分技能依据，全文还提供更直接的服务流程证据。'),
('0487','experience','retain_pending_human','appointment quality','规程规定按时预约并统计安装/修复及时率，但没有不同品牌响应时效样本或SLA比较值。','响应速度不是价格；需品牌、地区、服务事件及统一时效定义。','现答拒绝品牌速度比较合理，原价格促销类别应修。'),
('0488','staff','retain_pending_human','weights quality product','语料覆盖人员职业能力和装维质量，未给产品线业务绩效指标、营收/转化/留存或权重。','产品线绩效与员工能力不同；若实际想问人员，应改写问题。','现答明确未提产品线绩效，避免把职业标准替代业务绩效。'),
('0496','price','retain_pending_human','shape costdetail','全光设备规格与维护费用资料不含跨品牌智慧家庭产品价格表。','需型号、配置、报价日期、安装服务是否包含。','现答缺少具体价格依据的限定合理。'),
('0499','selection','revise_partial_qualify','shape mesh design service','全光组网规范可说明光网关/光路由、接口与互操作要求，装维规范可提供住宅条件和布线设计依据。','最适合需户型、带宽、预算及已有设备；问题未说跨品牌，原标签理由过宽。','现答可支持受限技术组合，不能断言唯一最适合或任意品牌兼容。'),
]

evidence = {}
for alias,(cid,anchor) in E.items():
    c=ci[cid]; start=c['chunk_text'].find(anchor); assert start>=0,(alias,anchor)
    evidence[alias]={'chunk_id':cid,'source':c['source'],'page_number':c['page_number'],'corpus_line':c['corpus_line'],'excerpt':c['chunk_text'][start:start+700],'full_text':c['chunk_text']}
records=[]
case_index={c['case_id']:(n,c) for n,c in enumerate(cases,1)}
for suffix,group,proposal,aliases,rationale,ambiguity,answer_note in DATA:
    cid='p6s-'+suffix; line,c=case_index[cid]; r=readj(RUN/'cases'/f'{cid}.json'); score=readj(RUN/'scores'/f'{cid}.json')
    terms=groups[group]
    scan={term:[x['chunk_id'] for x in corpus if term.casefold() in x['chunk_text'].casefold()] for term in terms}
    retrieved=[s.get('chunk',{}).get('id') for s in r.get('sources',[])]
    refs=[]
    for alias in aliases.split():
        e=evidence[alias]
        refs.append({k:v for k,v in dict(e,alias=alias,was_in_original_retrieved_sources=e['chunk_id'] in retrieved).items() if k!='full_text'})
    records.append({'case_id':cid,'question':c['question'],'original_label':c['question_type'],'original_reason':c.get('assumed_out_of_scope_reason'),'original_category':c.get('out_of_scope_category'),'ai_proposed_label_action':proposal,'ai_preliminary_conclusion':rationale,'ambiguity_and_missing_information':ambiguity,'current_answer_audit':answer_note,'corpus_evidence':refs,'full_corpus_literal_scan':{'chunks_scanned':447,'terms_and_all_hit_chunk_ids':scan,'candidate_reading':'人工式逐例AI阅读本记录corpus_evidence所指全文及相关相邻段落；关键词命中全集并不等于已逐字阅读所有命中。'},'original_evidence_index':{'silver_cases_path':str(CASES.relative_to(ROOT)).replace('\\','/'),'silver_cases_line':line,'run_case_path':str((RUN/'cases'/f'{cid}.json').relative_to(ROOT)).replace('\\','/'),'run_score_path':str((RUN/'scores'/f'{cid}.json').relative_to(ROOT)).replace('\\','/'),'original_retrieved_chunk_ids':retrieved,'case_sha256':sha(RUN/'cases'/f'{cid}.json'),'score_sha256':sha(RUN/'scores'/f'{cid}.json')},'current_answer':r['answer'],'original_no_answer_behavior':score.get('no_answer_behavior'),'human_final_label':'','human_final_answerability':'','human_final_verdict':'','human_reviewer':'','human_reviewed_at':'','human_review_notes':''})
assert len(records)==50 and {r['case_id'] for r in records}=={c['case_id'] for c in cases if c['question_type']=='unanswerable'}
counts=dict(collections.Counter(r['ai_proposed_label_action'] for r in records))
summary={'audit_type':'offline_read_only_AI_preliminary_review','formal_gold_added':0,'human_final_fields_completed':0,'corpus':{'path':str(CORPUS.relative_to(ROOT)).replace('\\','/'),'sha256':sha(CORPUS),'chunk_count':447,'documents':dict(collections.Counter(c['source'] for c in corpus))},'cases_sha256':sha(CASES),'reviewed_count':50,'ai_proposal_counts':counts,'limits':['全文关键词扫描不能证明无答案；未执行全语义穷尽证明。','扫描全部447 Chunk，对逐例列出的候选证据进行了AI阅读；并未声称逐字读完447 Chunk所有内容。','未调用模型、重跑检索、修改历史标签或生产代码；原答案与评分仅作为待审计输入。','所有结论为AI初步建议，最终标签、可答性、裁决、签名及日期留空。'],'records':records}
(OUT/'unanswerable_findings.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'unanswerable_evidence_catalog.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
md=['# P7 无答案候选复核包','',f'核查对象：50 条原 unanswerable Silver。冻结语料为 447 Chunk / {len(set(c["source"] for c in corpus))} PDF；SHA-256 `{sha(CORPUS)}`。','',
'本包为只读离线 AI 初审，不是人工签字或 Gold。全文关键词扫描不能证明无答案。对所有 447 Chunk 做逐例词面扫描，再阅读候选全文和相关相邻段落；未运行检索算法、模型或在线请求。现有 TopK 未召回答案不是无答案证据。关键词全命中清单见 `unanswerable_findings.json`，所读证据全文见 `unanswerable_evidence_catalog.json`。','',
'审阅者需逐条确认“问题范围—所需事实—证据覆盖”，尤其区分职业鉴定与企业绩效、工程计价与零售价格、服务质量与主观满意度、全光终端互操作与任意品牌家电兼容。','',
'## AI 建议汇总','',f'- 暂留无答案/待补信息（仍待人工）：{counts.get("retain_pending_human",0)}。',f'- 改为可部分回答、需限定范围/澄清：{counts.get("revise_partial_qualify",0)}。',f'- 改为有范围约束的可回答：{counts.get("revise_bounded_answer",0)}。','- 正式标签修订：0；人类最终字段填写：0；新增 Gold：0。','',
'这些是候选标签建议计数，不能作为新的成功率或正式无答案率。每条均保留原 P6 路径和行号；原检索之外的证据通过“原召回中”字段明确标记。','']
for r in records:
    md += [f'## {r["case_id"]} — {r["question"]}','',f'原理由：{r["original_reason"]}；原类别：{r["original_category"]}。',f'**AI 初步建议：`{r["ai_proposed_label_action"]}`**。{r["ai_preliminary_conclusion"]}',f'问题歧义/未覆盖事实：{r["ambiguity_and_missing_information"]}',f'现有回答核查：{r["current_answer_audit"]}','',f'原样本索引：`{r["original_evidence_index"]["silver_cases_path"]}` 第 {r["original_evidence_index"]["silver_cases_line"]} 行。原答案/召回：`{r["original_evidence_index"]["run_case_path"]}`；原评分：`{r["original_evidence_index"]["run_score_path"]}`。','', '全文扫描词与命中 Chunk 数：'+ '；'.join(f'`{t}`={len(ids)}' for t,ids in r['full_corpus_literal_scan']['terms_and_all_hit_chunk_ids'].items())+'。','']
    for e in r['corpus_evidence']:
        md += [f'- `{e["chunk_id"]}` / {e["source"]} / PDF 第 {e["page_number"]} 页 / corpus.jsonl 第 {e["corpus_line"]} 行 / 原召回中：{e["was_in_original_retrieved_sources"]}',f'  > {e["excerpt"].replace(chr(10)," ")}']
    md += ['','人类最终标签：','人类最终可答性：','人类最终裁决：','审阅人：','审阅日期：','人工意见：','']
(OUT/'unanswerable_review_packet.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps({'count':len(records),'ai_proposal_counts':counts,'corpus_hash':sha(CORPUS)},ensure_ascii=False))
