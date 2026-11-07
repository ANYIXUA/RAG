"""Offline review material only. Never import production retrieval or export Gold."""
import json, hashlib, re, csv, difflib, collections
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'p4-gold-completion-01'
BASE=ROOT/'storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f'
SNAP='sha256:eedd1783956ca582c1cdfbbdad486fdf1554c7dab79681bba0675eec47089fce'
TECH='中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf'
SKILL='智慧家庭装维工程与管理职业技能等级标准.pdf'
MAINT='电信基础设施维护规程.pdf'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def sha(b): return hashlib.sha256(b).hexdigest()
def digest(x): return sha(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
def write(name,x): (OUT/name).write_text(x,encoding='utf-8')
def dump(name,x): write(name,json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def dumpjl(name,x): write(name,''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in x))
chunks=jl(ROOT/'storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl')
cm={c['chunk_id']:c for c in chunks}
cp={(c['source'],c['page_number']):c for c in chunks}
candidates=jl(ROOT/'storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl')
byid={c['candidate_id']:c for c in candidates}
mapping=read(BASE/'p2-gold-07/.p2-work/b03_inputs.json')['mapping']
bm={r['b']:byid[r['candidate_id']] for r in mapping}
dev=read(ROOT/'p3-pilot-01/data/gold_provenance.json')['cases']
dev_ids={r['batch_id'] for r in dev}
devchunks=set(i for r in dev for i in r['evidence_chunk_ids']+r['relevant_chunk_ids'])
oldreview=read(OUT/'_work/old_review.json')
records=[]

def record(b,c,rec,q,a,ids,reason,typ,topic,origin,checks=None):
    effective={'query':q,'reference_answer':a,'evidence_chunk_ids':ids,'retrieval_relevant_chunk_ids':ids if rec!='Reject' else [],'snapshot_id':SNAP}
    is_revision=q!=c['question'] or a!=c['proposed_answer'] or ids!=c['supporting_chunk_ids']
    r={
      'review_id':b,'candidate_id':c['candidate_id'],'parent_candidate_id':c.get('parent_candidate_id'),
      'original_question':c['question'],'original_answer':c['proposed_answer'],
      'original_supporting_chunk_ids':c['supporting_chunk_ids'],
      'proposal_id':'p4-proposal-sha256:'+digest(effective),
      **effective,'is_revision':is_revision,'ai_recommendation':rec,'review_reason':reason,
      'question_type':typ,'knowledge_topic':topic,'review_origin':origin,
      'review_status':'pending_human_review','human_decision':None,'human_reviewer':None,
      'human_reviewed_at':None,'human_comment':None,'gold_case_id':None,
      'dataset_role':'Holdout_proposed','is_frozen_holdout':False,
      'requires_all_evidence':len(ids)>1,
      'development_chunk_overlap':sorted(set(ids)&devchunks),
      'sources':[{'chunk_id':i,'document':cm[i]['source'],'document_version':cm[i]['document_version'],
                  'physical_page':cm[i]['page_number'],
                  'printed_page':(cm[i]['page_number']-(5 if cm[i]['source']==TECH else 1 if cm[i]['source']==SKILL else 6)) if cm[i]['page_number']> (5 if cm[i]['source']==TECH else 1 if cm[i]['source']==SKILL else 6) else None,
                  'chunk_text_sha256':cm[i]['chunk_text_sha256']} for i in ids],
      'review_checks':checks or ['题答与所列证据相符','沿用既有审核；未重新宣称第二位独立审核人'],
    }
    records.append(r); return r

topics={28:'铁塔维修单价',29:'环境清理单价',30:'二维码字段映射',31:'占位日期',32:'职业能力与学历',33:'职业技能鉴定',34:'架空线路铁路净距',35:'终端产品形态',36:'实操权重',37:'理论权重',38:'工作内容合并',39:'不对称比较',40:'变压器维护工作',41:'控制设备维护工作',42:'发电设备维护工作'}
for d in oldreview:
    b=d['batch_id']; n=int(b[1:]); c=bm[b]
    ids=re.findall(r'[0-9a-f]{24}',d['evidence_chunk_ids'])
    r=record(b,c,d['review_recommendation'],d.get('revised_question') or c['question'],d.get('revised_answer') or c['proposed_answer'],ids,d['review_reason'],d['question_type'],topics[n],'P2-Gold-07 existing AI review')
    r['prior_review_source']=(BASE/'p2-gold-07/p2_gold_07_signoff_packet.md').relative_to(ROOT).as_posix()+f'#{b.lower()}'
    r['source_verification']=d['source_verification']

# B43-B57: source-first audit. Accept means AI opinion only.
audit={
43:('Accept',None,None,'WH23121004 在表10.3.3.21 的综合单价列为175.10；人工费109.44 是另一列，计量单位为只。','价格表定位','控制设备更换单价'),
44:('Accept',None,None,'WH23121002 行综合单价120.38；相邻断路器行105.79 不可替代，计量单位为只。','价格表定位','控制设备安装单价'),
45:('Accept',None,None,'表10.3.3.22 工作内容第2项逐项包含原答四个动作；事实是B42答案的子集，签核可选其一，不累计为新增独立覆盖。','作业内容枚举','离网风机检修'),
46:('Accept',None,None,'工作内容第3项列出原答；原件该项题头漏“太阳”二字，同表WH23122003行名完整，不能把源文件笔误误判成模型补造。事实为B42子集。','作业内容枚举','光伏发电检修'),
47:('Accept',None,None,'物理页25 的4.3.4.9 第1项明确须支持4096 QAM；相邻802.11ax条款为1024-QAM，协议限定可消歧。与Development B05共用证据块。','协议参数辨析','802.11be调制'),
48:('Revise','按《电信基础设施维护规程》第8.4.7.5条，清单漏项或非承包人原因的作业变更导致措施项目变化时，原措施费中已有项目和没有的项目分别如何调整？','已有项目按原措施项目的组价方法调整；没有的项目由承包人根据措施项目变更情况提出适当的措施费变更，经发包人确认后调整。','原问已给出“按原措施项目的组价方法”，直接泄露答案。修订去掉提示，并对照条款的已有/没有两种情况，保留发包人确认条件。','条件对照','措施项目变更'),
49:('Revise','按《电信基础设施维护规程》第8.4.8.4条，维护分项作业费在综合单价未调整与已调整时，分别依据什么计算？','未调整时依据双方确认的工作量、合同约定的综合单价计算；发生调整时，以发、承包双方确认调整的综合单价计算。','原答只覆盖分号前的常规情况，泛化问法没有排除调整情形。修订纳入同条款后半句，不把普通情况当成完整规则。','条件对照','维护作业费结算'),
50:('Revise','按《电信基础设施维护规程》第8.4.7.8条，因不可抗力事件导致承包人的维护用机械（仪表）设备损坏及停工损失，由谁承担？','由承包人承担。','原问缺少上位条款“因不可抗力事件导致”的前提，可能被误读为所有致损原因。补齐前提；不能将此答案当成现实合同责任咨询。','条件责任归属','不可抗力费用分担'),
51:('Revise','按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.11.1节，MTBF的时长要求及长时间运行的业务表现要求分别是什么？','MTBF至少应达到30000小时以上；长时间运行时不应出现业务中断或性能下降。','原答数值正确；修订明确文档范围并保留原文“至少…以上”，不擅改为严格大于关系。与Development B09共块，作扩充Development备选。','可靠性约束','MTBF与长期运行'),
52:('Revise','按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.1，光网关终端应支持通过二维码实现什么功能？','放装零配置功能。','原件与Chunk均为“放装零配置”，不擅自改成“安装”；补文档范围，与B53是同块不同属性，简短功能题作备选。','功能定位','二维码零配置功能'),
53:('Revise','按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.1，光网关零配置二维码必须集成设备的哪两项Wi-Fi参数？','该设备Wi-Fi的SSID和密码参数。','两项参数在同一句中完整出现；补文档和A.1范围，避免与A.2光路由二维码的四字段格式混淆。SSID和密码两项均须答出。','参数集合','零配置二维码参数'),
54:('Revise','《智慧家庭装维工程与管理职业技能等级标准》初级等级“3.3 光路达标测试”的技能要求3.3.1和3.3.2分别是什么？','3.3.1：能使用红光光源、光功率计；3.3.2：能掌握手持终端的使用。','原题的“具体要求”可被理解成操作步骤或阈值，但原表只列能力条目。修订限定初级、技能要求列和两项编号，不添加步骤、不混用相关知识列。','等级技能枚举','初级光路测试能力'),
55:('Accept',None,None,'表10.3.3.24 WH23124001 的综合单价为970.37元/台；606.48 是人工费；相邻模块化UPS机柜为419.52。','价格表定位','UPS安装单价'),
56:('Accept',None,None,'表10.3.3.25 WH23125003 一体化壁挂式综合单价747.84元/台；落地式510.72、组合式1123.58，行列可区分。','价格表定位','开关电源安装单价'),
57:('Revise','按《中国移动智慧家庭全光组网产品技术规范》V2.0.0附录A.3的省级平台预置表，宁夏平台的TCP和UDP域名、端口各是什么？','TCP：jtwlgl.nx.chinamobile.com:9005；UDP：jtwlgl.nx.chinamobile.com:9007。','原答两行正确；补冻结规范与预置表范围，要求域名、端口和协议对应完整。这里只核对冻结表，不验证网络可用性。','实体协议映射','省级平台域名端口'),
}
for n,(rec,q,a,reason,typ,topic) in audit.items():
    b=f'B{n}';c=bm[b]
    r=record(b,c,rec,q or c['question'],a or c['proposed_answer'],c['supporting_chunk_ids'],reason,typ,topic,'P4 source-first AI audit 2026-11-05',
             ['冻结Chunk原文已读','对应PDF物理页全文已读','行列/条款前提与答案完整性已核','与57候选及22 Development做事实与证据比较'])
    r['source_verification']='见 _work/b43_b57_pdf_pages.txt；对应物理页及冻结Chunk的完整证据见 evidence_catalog.jsonl。'

# Preserve B23's invalid historical decision as evidence, never as a new sign-off.
c=bm['B23'];u=jl(BASE/'p2-gold-06/unsigned_batch02_1.jsonl')[0]
r=record('B23',c,'Revise','按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.8.4节第1项，全光组网终端的WLAN应支持哪两种链路层鉴权方式？','Open System和Pre-Shared Key。',c['supporting_chunk_ids'],'沿用P2-Gold-07复核：只限第1项的两种链路层鉴权，不纳入第2项WPA系列及AES/TKIP加密模式；旧“保留测试”不构成有效批准。','术语辨析','WLAN链路层鉴权','P2-Gold-07 B23 recheck')
r['legacy_human_record']=u

# Deliberate non-price supplementation; one fact group per new evidence page.
new=[
(TECH,17,'场景规则','WAN隔离',
 '按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.3.1.3节，光网关建立多条WAN连接时，连接间的数据应如何处理？路由WAN下两侧ARP报文又有何要求？',
 '不同WAN连接之间的数据（包括DNS、ARP、管理应用数据等）应支持完全隔离；路由WAN连接下，应支持网络侧和用户侧ARP报文的隔离。',
 ['不同WAN 连接之间的数据','应支持完全隔离','网络侧和用户侧ARP 报文的隔离'],
 '两层隔离对象明确，同页两个完整句子；不把路由WAN的ARP限制扩展为所有网络流量。'),
(TECH,21,'时限与约束','WPS协商',
 '按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.3.4.3节，支持WPS Push-Button的客户端应在多长时间内完成协商并连接？WPS过程对已连接客户端有什么限制？',
 '应在2分钟内协商好加密算法、分发密钥、配置好相关参数并建立连接；WPS过程不应影响已连接客户端的连接状态和数据传送。',
 ['2 分钟内协商好加密算法','WPS 过程不应影响已连接无线客户端设备的连接状态和数据传送'],
 '保留Push-Button适用范围，不把可选支持说成所有设备强制具备；时间与不干扰约束均有同页原文。'),
(TECH,30,'例外条件','智能重启',
 '按《中国移动智慧家庭全光组网产品技术规范》V2.0.0的智能重启要求，已支持并开启该功能的终端能否采用固定重启时间？原文规定了什么例外？',
 '智能重启功能禁止采用固定重启时间；用户通过和家亲APP或本地Web设置定时重启任务除外。',
 ['智能重启功能禁止采用固定重启时间','用户通过和家亲APP 或本地Web 设置定时重启任务除外'],
 '禁止规则与括号例外一起保留；不把出厂可选功能误作强制要求。'),
(TECH,43,'双阈值辨析','Wi-Fi7链路时延',
 '在《中国移动智慧家庭全光组网产品技术规范》V2.0.0“Wi-Fi 7链路时延要求”的MLD链路测试场景中，UDP单向的链路平均时延与TP99时延分别须满足什么阈值？',
 '链路平均时延须小于5ms；链路TP99时延须小于25ms。',
 ['链路平均时延须小于5ms','链路TP99时延须小于25ms'],
 '明确链路时延测试场景，与紧邻的干扰周期变化测试分开；保留严格小于和ms单位。'),
(TECH,46,'状态映射','上行光信号指示灯',
 '按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.6.1.1节“光网关指示灯要求”，上行光信号状态灯熄灭和闪烁分别表示什么？',
 '熄灭表示接收光功率正常；闪烁表示接收光功率异常。',
 ['上行光信号状态灯','熄灭：接收光功率正常','闪烁：接收光功率异常'],
 '按上行灯对应行核对，不套用电源灯或下行灯的熄灭含义。正文引用表4-12而该页实际表题为4-11，题面使用章节及表题避免错号。'),
(TECH,54,'失败分支','安全启动',
 '按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.8.10节，终端每个启动阶段何时才可执行下一阶段？安全签名校验未通过时怎么办？',
 '每个启动阶段须校验下一个启动阶段的安全签名，校验通过后方可执行下一启动过程；否则设备停止启动或进入修复流程。',
 ['校验通过后方可执行下一个启动过程','否则设备停止启动或进入修复流程'],
 '原文是“停止启动或进入修复流程”二选一，不增加自动重试或强制刷机。'),
(TECH,56,'失败恢复','软件远程升级',
 '按《中国移动智慧家庭全光组网产品技术规范》V2.0.0第4.9.2.4节，全光组网终端升级软件时应具备什么校验功能？升级失败后应支持哪两种处理路径？',
 '应具有容错校验功能；升级失败时应能恢复到原来的软件版本，或者连接管理平台接受再次升级。',
 ['容错校验功能','恢复到原来的软件版本或者连接管理平台接受再次升级'],
 '保留两条可替代路径的“或者”关系，不要求两条依次执行。'),
(SKILL,5,'适用范围','职业标准使用场景',
 '《智慧家庭装维工程与管理职业技能等级标准》第1章对人员培训、考核评价与人员聘用分别规定了怎样的适用或参照关系？',
 '本文件适用于智慧家庭装维人员职业技能培训、考核与评价；人员聘用、培训与考核可参照执行。',
 ['职业技能培训、考核与评价','人员聘用、培训与考核可参照执行'],
 '区分“适用于”和“可参照执行”的措辞，不将征求意见稿解释为现行强制资质要求。'),
(SKILL,9,'知识集合','智能组网知识',
 '《智慧家庭装维工程与管理职业技能等级标准》第5.4节列出的智能组网专业基础知识有哪八项？',
 '综合布线知识；通信网络技术及光纤到户业务知识；无线局域网技术知识；视听业务技术知识；智能控制技术知识；智能组网及家庭总线（数据、视听、控制）技术知识；智能家居、智能家电及联网、联动技术知识；家庭业务云平台及智能门户技术知识。',
 ['5.4 智能组网专业知识','家庭业务云平台及智能门户技术知识'],
 '同一页a-h八项闭合，不能拿紧邻第5.5节的全屋智能七项替代；与Development第5.7安全知识不同。'),
(SKILL,17,'等级技能枚举','高级智能家居技能',
 '《智慧家庭装维工程与管理职业技能等级标准》第6.5节高级等级“2.4 智能家居技术”的两项技能要求是什么？',
 '2.4.1：能进行智能家居集中控制；2.4.2：能进行有线系统和无线系统拓展应用。',
 ['能进行智能家居集中控制','能进行有线系统和无线系统拓展应用'],
 '核对高级/技能要求列；不混用相关知识列的“系统架构”“家庭复合总线综合控制方式”，也不与中级架构题等同。'),
(MAINT,23,'范围与单位辨析','水线保护范围',
 '《电信基础设施维护规程》第4.3.4.2 b）规定，普通水线与海缆两侧各多大范围内禁止抛锚、捕鱼、炸鱼、挖砂等危及水线安全的活动？',
 '普通水线两侧各100米；海缆两侧各2海里。',
 ['水线两侧各100 米','海缆两侧各2 海里'],
 '保留“两侧各”与不同单位；不擅自换算海里或把海缆条件用于普通水线。'),
(MAINT,28,'术语集合','四新技术',
 '《电信基础设施维护规程》第4.5.0.5 f）中，《光缆线路维护方案》的“四新”技术指哪四项？',
 '新技术、新材料、新工艺、新设备。',
 ['新技术、新材料、新工艺、新设备'],
 '条款、方案名称与四项闭合；不添加质量目标或安全措施等其他编制内容。'),
(MAINT,34,'操作前后条件','光缆割接确认',
 '《电信基础设施维护规程》第4.8.2.6 d）要求，进行光缆割接操作前与割接完毕离开现场前，分别须取得谁的什么确认？',
 '割接操作前必须经运营企业网管人员确认，方可割接；割接完毕后必须经运营企业网管人员确认，方可离开现场。',
 ['进行割接操作前必须经运营企业网管人员确认','割接完毕后必须经运营企业网管人员确认后'],
 '两个时点同为网管人员确认；不得用其他项的业务主管到场指挥代替。'),
(MAINT,63,'责任边界','有线设备与线路专业界面',
 '《电信基础设施维护规程》第6.3.2.1规定，小型局站有线设备与传输线路专业以什么为维护界面？成端以内尾纤、传输设备和光缆成端及以外部分分别由谁负责？',
 '以局站内ODF架或ODF单元成端为界；成端以内尾纤、传输设备等由本专业（小型局站有线设备）负责；光缆线路成端（含终端盒、法兰盘等）及成端以外的传输线路部分由线路专业负责。',
 ['以传输线路局站内ODF 架或ODF 单元成端为界','光缆线路成端（含终端盒、法兰盘等）'],
 '保留成端本身属于线路专业的包含关系；不混用下一条无线专业的ODF/DDF框界面。'),
(MAINT,12,'相近术语对照','MSTP与ASON',
 '按《电信基础设施维护规程》第3.35、3.36条，MSTP基于什么平台提供统一网管的多业务接入处理传送？ASON基于什么网络，并引入什么来按需分配资源？',
 'MSTP基于SDH平台；ASON以光传送网（OTN）为基础，在光传送网中引入控制平面，实现网络资源按需分配。',
 ['基于SDH 平台','以光传送网（OTN）为基础','引入控制平面'],
 '同页相邻术语对照，三个要点均有原文，避免把SDH与OTN或管理平面与控制平面混淆。'),
]
for n,(src,page,typ,topic,q,a,anchors,reason) in enumerate(new,1):
    ch=cp[(src,page)];ids=[ch['chunk_id']]
    c={'candidate_id':'p4-candidate-sha256:'+digest({'snapshot':SNAP,'query':q,'answer':a,'ids':ids}),
       'question':q,'proposed_answer':a,'supporting_chunk_ids':ids}
    r=record(f'P4-N{n:02}',c,'Accept',q,a,ids,reason,typ,topic,'P4 AI authored + source verified 2026-11-05',
             ['从冻结PDF/Chunk选取事实，不依据Pilot排名选题','同页PDF全文与Chunk双向核对','答案完整、条件/单位/否定词检查','与全部57候选及22 Development做事实查重'])
    r['evidence_anchors']=anchors
    r['source_verification']='见 _work/new_pdf_pages.txt；表格行列另见 _work/evidence_images/。AI自检，不代表第二位独立审核人。'

primary_old={'B32','B33','B34','B35','B40','B41','B42','B48','B49','B50','B53','B54','B57'}
for r in records:
    b=r['review_id']
    if r['ai_recommendation']=='Reject': tier='exclude_ai_reject';why='既有AI建议驳回；待人工最终裁决'
    elif b=='B38': tier='exclude_fact_union';why='修订后的事实集合=B40∪B41；不作为额外独立题计数'
    elif b in {'B45','B46'}: tier='alternative_subset';why='题答可核，但事实是B42子集；可替换B42，不与其重复累计覆盖'
    elif r['development_chunk_overlap']: tier='reserve_development_overlap';why='与Development证据Chunk重叠；可扩充Development，默认不进入本轮Holdout'
    elif b in primary_old or b.startswith('P4-N'): tier='holdout_primary_proposed';why='事实独立、无Development证据Chunk交集；拟优先集中签核'
    else: tier='holdout_reserve_proposed';why='题答可核且无Development证据块交集；价格或同块简短题暂列备选'
    r['selection_tier']=tier;r['selection_reason']=why
    r['high_quality_after_proposed_revision']=r['ai_recommendation']!='Reject'
    r['independent_coverage_eligible']=tier not in {'exclude_ai_reject','exclude_fact_union','alternative_subset'}
    # Similarity is a triage signal, never a semantic duplicate verdict.
    others=[(x['review_id'],x['query']) for x in records if x is not r]+[(x['batch_id'],x['query']) for x in dev]+[(b,x['question']) for b,x in bm.items() if b!=r['review_id']]
    nearest=max(((difflib.SequenceMatcher(None,r['query'],q).ratio(),b) for b,q in others),default=(0,None))
    r['nearest_query_match']={'review_id':nearest[1],'sequence_similarity':round(nearest[0],4),'interpretation':'仅字符相似度筛查，事实判定见selection_reason/review_reason'}
    r['review_record_sha256']=digest({k:v for k,v in r.items() if not k.startswith('human_')})

records.sort(key=lambda r:(0,int(r['review_id'][1:])) if r['review_id'].startswith('B') else (1,int(r['review_id'][-2:])))
primary=[r for r in records if r['selection_tier']=='holdout_primary_proposed']
eligible=[r for r in records if r['selection_tier'] in {'holdout_primary_proposed','holdout_reserve_proposed'}]
assert len(primary)==28 and len(eligible)==33
assert all(not r['development_chunk_overlap'] for r in primary)
dumpjl('candidate_reviews.jsonl',records)
dumpjl('new_candidates_15.jsonl',[r for r in records if r['review_id'].startswith('P4-N')])
dumpjl('holdout_proposed_28.jsonl',primary)
dump('development_manifest.json',{'dataset_role':'Development','count':22,'source':'p3-pilot-01/data/gold_22_merged.jsonl','source_sha256':sha((ROOT/'p3-pilot-01/data/gold_22_merged.jsonl').read_bytes()),'case_ids':[{'batch_id':r['batch_id'],'gold_case_id':r['gold_case_id']} for r in dev],'note':'仅角色清单；原Gold字节保持不动，已用于Pilot，禁止标为未见Holdout。'})

evidence_ids=sorted({i for r in records for i in r['evidence_chunk_ids']+r['original_supporting_chunk_ids']})
evidence=[]
for i in evidence_ids:
    c=cm[i];n=c['page_number'];s=c['source']
    printed=n-(5 if s==TECH else 1 if s==SKILL else 6)
    if s==SKILL and n==2: printed='I'
    elif s==TECH and n==3: printed='ii'
    elif printed<=0: printed=None
    evidence.append({'chunk_id':i,'source':s,'physical_page':n,'printed_page':printed,
                     'document_version':c['document_version'],'document_content_hash':c['document_content_hash'],
                     'chunk_text_sha256':c['chunk_text_sha256'],'chunk_text':c['chunk_text'],
                     'used_by':[r['review_id'] for r in records if i in r['evidence_chunk_ids']],
                     'original_reference_used_by':[r['review_id'] for r in records if i in r['original_supporting_chunk_ids']]})
dumpjl('evidence_catalog.jsonl',evidence)

inventory=[]
for x in mapping:
    b=x['b'];r=next((r for r in records if r['review_id']==b),None)
    status='Development_approved' if b in dev_ids else 'previously_human_rejected' if b in {'B08','B10','B11','B24'} else 'pending_human_review'
    inventory.append({'review_id':b,'candidate_id':x['candidate_id'],'existing_status':status,'query':bm[b]['question'],'selection_tier':r['selection_tier'] if r else status})
inventory += [{'review_id':r['review_id'],'candidate_id':r['candidate_id'],'existing_status':'new_pending_human_review','query':r['query'],'selection_tier':r['selection_tier']} for r in records if r['review_id'].startswith('P4-N')]
dump('candidate_inventory_72.json',inventory)

def table(headers,rows):
    def clean(v): return str(v).replace('|','／').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(clean(v) for v in row)+' |' for row in rows])
def detail(r):
    srcs='；'.join(f"{s['document']}：物理{s['physical_page']}，"+(f"印刷{s['printed_page']}" if s['printed_page'] is not None else '未标印刷页') for s in r['sources'])
    return f"\n## {r['review_id']}\n\n- 候选ID：`{r['candidate_id']}`\n- 待签版本ID：`{r['proposal_id']}`\n- 审核记录SHA-256：`{r['review_record_sha256']}`\n- 题型／知识点：{r['question_type']}／{r['knowledge_topic']}\n- AI建议：{r['ai_recommendation']}；筛选：{r['selection_tier']}。\n- 来源：{srcs}；文档版本：{', '.join(sorted({s['document_version'] for s in r['sources']}))}。\n- 原题：{r['original_question']}\n- 原答：{r['original_answer']}\n- **待签题目**：{r['query']}\n- **标准答案**：{r['reference_answer']}\n- 审核理由：{r['review_reason']}\n- Holdout选择说明：{r['selection_reason']}\n- 相关Chunk：{', '.join('`'+i+'`' for i in r['retrieval_relevant_chunk_ids']) or '空（AI建议驳回）'}\n- 证据Chunk：{', '.join('`'+i+'`' for i in r['evidence_chunk_ids'])}；全部证据要求：{r['requires_all_evidence']}。\n- PDF入口："+'；'.join(f"[{s['document']} 第{s['physical_page']}物理页](../data/{quote(s['document'])}#page={s['physical_page']})" for s in r['sources'])+f"\n- 全文证据：[证据目录](evidence_catalog.md#{r['evidence_chunk_ids'][0]})。\n\n```text\nhuman_decision:\nhuman_reviewer:\nhuman_reviewed_at:\nhuman_comment:\n```\n"

write('evidence_catalog.md','# 冻结证据目录\n\n只读摘录；物理页从1开始。Chunk内容保持快照原文，未作纠错。\n'+''.join(f"\n## {e['chunk_id']}\n\n{e['source']}；物理页{e['physical_page']}；文档版本`{e['document_version']}`；待签证据使用题号：{', '.join(e['used_by']) or '无（仅原题审计）'}；原题引用：{', '.join(e['original_reference_used_by']) or '无'}。\n\n```text\n{e['chunk_text']}\n```\n" for e in evidence))

short=lambda rows:table(['编号','AI建议','待签题目','来源物理页','筛选'],[[r['review_id'],r['ai_recommendation'],r['query'],'; '.join(str(s['physical_page']) for s in r['sources']),r['selection_tier']] for r in rows])
write('b28_b42_signoff_summary.md','# B28–B42 简洁签核表\n\n沿用P2-Gold-07：Accept 8、Revise 5、Reject 2；均为AI建议。原审核结论未被本轮筛选意见覆盖。人工输入请统一在工作簿“签核”填写。\n\n'+short([r for r in records if r['review_id'].startswith('B') and 28<=int(r['review_id'][1:])<=42])+'\n\nB38保留原Revise记录，但与B40/B41的事实并集重复，不新增独立覆盖。B28/B29/B30/B36/B37共享Development证据块，默认列Development扩充备选。B34须核对铁路行“交越”列7.5m；B32/B33/B35修订改变证据目标页。\n')
write('b43_b57_independent_review.md','# B43–B57 独立审核\n\n2026-11-05（Asia/Shanghai）。本轮AI从冻结Chunk及对应PDF原文开始核对，未用Pilot排序或模型答案作判定依据。独立指源证据优先审核，不代表人工签核或第二名审核人。\n\nAccept 7、Revise 8、Reject 0。B45/B46可回答，但为B42事实子集，作为替换题而非新增独立覆盖。\n\n'+short([r for r in records if r['review_id'].startswith('B') and 43<=int(r['review_id'][1:])<=57])+'\n'+''.join(detail(r) for r in records if r['review_id'].startswith('B') and 43<=int(r['review_id'][1:])<=57))
write('new_candidate_review_summary.md','# 新候选与全量待审汇总\n\n原待签31条（B23及B28–B57），新增P4-N01–N15共15条，合计46条待人工处理。AI建议可签原题或修订题44条；AI建议驳回2条。人工批准新增0条，正式Holdout 0条。\n\n## 数量口径\n\n'+table(['口径','原候选','补充后','说明'],[
 ['待签全部',31,46,'含2条AI建议驳回'],['题答可核，按AI修订后口径',29,44,'未等同人工通过'],
 ['扣除事实并集/子集重叠',26,41,'B38不额外计数；B45/B46与B42互为替换'],
 ['再避开Development证据块',18,33,'8条已测证据块题作Development扩充备选'],
 ['优先签核Holdout',13,28,'5条价格/同块简短题列备用，新增15条均非价格题']])+
 '\n\n原可选18条不足28条，最低缺10条。为让主选不依赖4条新增价格查询和1条同块简短功能题，本轮补15个不同知识点，形成28主选＋5备选，不以降低质量换取50条。\n\n## 新增15条\n\n'+short([r for r in records if r['review_id'].startswith('P4-N')])+'\n\n## 其他待签候选\n\n'+short([r for r in records if r not in primary])+'\n\n所有候选可在集中签核工作簿按编号筛选。B23旧“保留测试/system”记录保存在candidate_reviews.jsonl的legacy_human_record，不写入本轮人工输入字段。\n')

devdoc=collections.Counter(cm[i]['source'] for i in [])
for r in dev:
    src={cm[i]['source'] for i in set(r['evidence_chunk_ids']+r['relevant_chunk_ids'])}
    for s in src: devdoc[s]+=1
primarydoc=collections.Counter(r['sources'][0]['document'] for r in primary)
classes={
 '条款事实／定义':['P4-N08','P4-N12'],
 '列表／集合':['B32','B33','B40','B41','B42','B53','B54','P4-N09','P4-N10'],
 '表格定位':['B34','B35','P4-N05'],
 '条件／例外':['B48','B49','B50','P4-N01','P4-N03'],
 '时限／阈值／单位':['P4-N02','P4-N04','P4-N11'],
 '失败恢复／操作流程':['P4-N06','P4-N07','P4-N13'],
 '映射／术语／责任边界':['B57','P4-N14','P4-N15'],
}
types=collections.Counter({k:len(v) for k,v in classes.items()})
assert {b for group in classes.values() for b in group}=={r['review_id'] for r in primary}
primarychunks=set(i for r in primary for i in r['evidence_chunk_ids'])
dump('summary_counts.json',{'approved_development':22,'approved_new':0,'frozen_holdout':0,'prior_human_rejected':4,'pending_original':31,'new_candidates':15,'pending_total':46,'ai_answerable_after_revision':44,'fact_distinct_after_exclusions':41,'development_overlap_reserves':8,'holdout_eligible_after_review':33,'holdout_primary_proposed':28,'holdout_reserve_proposed':5,'primary_unique_chunks':len(primarychunks),'primary_document_counts':dict(primarydoc),'primary_type_counts':dict(types)})
write('gold_coverage_report.md','# Gold数量与覆盖度报告\n\n2026-11-05（Asia/Shanghai）。本报告是建设进度，不是Benchmark结果。\n\n'+table(['状态','数量'],[['既有已导出Gold，全部Development',22],['本轮新增人工批准',0],['已冻结正式Holdout',0],['原始57候选中人工驳回',4],['原待签候选',31],['新增独立ID候选',15],['当前待人工处理',46],['Holdout主选（AI建议，未冻结）',28],['Holdout备选（AI建议，未冻结）',5]])+
 '\n\n57条原候选=22已导出＋4既有人工驳回（B08/B10/B11/B24）＋31待签；补15后共72个候选身份。只有28主选全部获有效人工批准并通过冻结前检查，才形成22 Development＋28 Holdout的50条总体；正式留出指标分母应为28，不把Development混成50条未见测试。\n\n## 文档覆盖\n\n'+table(['PDF','冻结Chunk','Development题数','拟Holdout主选题数'],[[s,sum(c['source']==s for c in chunks),devdoc[s],primarydoc[s]] for s in [MAINT,TECH,SKILL]])+
 f'\n\n拟主选覆盖{len(primarychunks)}个独立Chunk（28题），与Development的证据及相关Chunk集合交集为0。主选B48/B50同在物理91页但问不同条款/责任，故28题并非28个独立页面。未把同块视为自动重复；报告按证据簇披露集中度。\n\n## 题型覆盖\n\n'+table(['题型','主选数'],sorted(types.items()))+
 '\n\n主选不含综合单价查询；4条待签价格题保留为备选。新增15题覆盖：WAN隔离、WPS时限、重启例外、链路时延、灯态、安全启动、升级恢复、标准适用、组网知识、高级控制技能、水线保护、四新、割接确认、维护界面和传送网术语。\n\n## 边界与缺口\n\n- 样本是3份PDF的目的性抽样，并非按360/68/19个Chunk比例的随机抽样，不能外推生产总体。\n- 本轮主选均为单Chunk可完整取证，含同块多条款组合；跨Chunk完整证据任务暂未形成独立主选，不能据此宣称多跳能力。\n- 未包含无答案、时效更新和权限隔离题，冻结文档题不验证现实网络、价格或现行规范。\n- 引用页码/章节的精确定位题占有一定比例；按题型分层报告，避免只看总体均值。\n- Chunk无交集只降低直接证据重叠；PDF、规范主题已被开发者看过，无法证明知识点绝对未见。此为预注册Holdout方案，尚非已封存盲测集。\n- 既有Gold不做纠错；如发现历史Gold争议，另开审计记录，不在本轮改22条。\n')

signintro='''# P4-Gold-Completion-01 集中人工签核包

2026-11-05（Asia/Shanghai）。先处理28条主选；其余18条留作备选、替换或驳回裁决。AI建议不是批准，当前新增Gold=0，正式Holdout=0。

建议统一填写同目录工作簿“签核”页黄色的人工决定、审核人、审核日期、备注四列；下方空白字段仅供纯文本方式使用，不要两处分别填写。若两处冲突，必须先人工消解，禁止自动挑选。

人工决定只选“接受原题 / 接受修订 / 驳回”。接受原题绑定原题答及原证据；接受修订绑定下方待签题答、相关Chunk及proposal_id。标为Revise的题若选择接受原题，不能自动导出，须先处理本报告指出的问题。姓名/身份和日期由人工填写，备注可空；B23若继续“保留测试”仍是未签核。

任何接受均是本轮内容裁决；Holdout冻结、运行授权是后续独立步骤。本轮不生成运行用Gold，不读取签核表来自动执行导出或Benchmark。引用的原候选ID保持不动，修订由独立proposal_id与记录哈希绑定。

## 主选28条

'''
write('human_signoff_packet.md',signintro+short(primary)+'\n\n## 主选完整题答与证据\n'+''.join(detail(r) for r in primary)+'\n\n## 备选与需裁决记录\n'+''.join(detail(r) for r in records if r not in primary))

write('development_holdout_split.md','''# Development / Holdout划分方案

## 角色

- Development：现有22条，源JSONL和metadata字节不变，清单见development_manifest.json。所有P3指标仅归此组。
- Holdout拟主选：holdout_proposed_28.jsonl中的28条，状态pending_human_review、is_frozen_holdout=false，不是正式Gold或运行输入。
- 备选：5条无Development证据块交集的题，可在评测前依人工裁决替换。8条共享Development证据块的候选默认作Development扩充备选。
- B38与B40/B41不能重复计入独立覆盖；B45/B46若替换B42，要重新评估数量、事实和证据簇覆盖。

## 冻结前程序（待人工确认后另行执行）

1. 按candidate_id、proposal_id、review_record_sha256收集有效人工决定及身份、日期。修订未被接受、被驳回或有争议的题不导出。
2. 再核对标准答案要点、否定/例外、单位、PDF物理页与Chunk一致性；B34铁路交越列、B35跨页表范围及所有Revise项重点复核。
3. 如主选不足28，可用备选替换；如果仍不足，接受较小Holdout或继续补题，禁止将Development改标或拆分同一事实凑数。
4. 对最终题目、答案、expected、relevant/evidence IDs、requires_all_evidence、语料快照、审核记录和人工签核生成不可变版本及SHA-256清单。预先固定检索与答案评分口径、配置、模型版本和报告模板。
5. 固定最终Holdout名单后再授权运行；后续调参只用Development。不得拿Holdout召回、逐题失败、候选排序、重排分数或答案反馈作参数/提示词选择。
6. 若已查看Holdout结果并据此改系统，该版本转入Development/诊断记录，需另建未用于调参的留出题，不能继续称同一Holdout为未见测试。

## 报告口径

22+28=50仅是内容总量目标，不是50条独立未见测试。Development与Holdout分别报告分母、指标和置信/抽样局限。Holdout的28条是目的性覆盖样本，不能称为生产分布无偏估计；共用证据页的题按证据簇额外披露。

本轮没有导出新Gold、冻结Holdout或运行评测。proposal文件的SHA-256用于审核版本完整性，不代表完成评测冻结。
''')
write('benchmark_readiness_checklist.md','''# 最终Benchmark执行准备清单

本轮不运行。以下未勾选项是正式执行门槛，不能用AI建议自动完成。

## 数据与签核

- [x] 标识现有22条Development，并保持原文件不变。
- [x] 核对447 Chunk / 3 PDF的冻结快照身份；本轮只做本地文件校验，不连数据库。
- [x] B28–B42汇总、B43–B57独立源审核、15条新候选及完整证据已形成。
- [ ] 人工逐题裁决，填真实审核身份和日期；所有Revise与特殊问题已消解。
- [ ] 最终Holdout数量、主备替换及覆盖度由人工确认，目标28并非最低质量豁免。
- [ ] 导出独立Holdout Gold及sidecar；校验ID唯一、字节哈希、冻结语料内ID、expected与source/page/text_contains绑定。
- [ ] 每个relevant ID确实可支持答案；多证据采用明确AND完整性，相关集合命中与完整证据指标分别记录。

## 系统与预注册

- [ ] 检查并记录实际Git提交、未提交diff及哈希；当前P3修复未提交，不能只写HEAD冒充实现版本。
- [ ] 只读验证运行时数据库active Chunk ID/text与447冻结快照等价；若不等价先暂停，不重建/覆盖冻结语料。
- [ ] 预先固定四组BM25 Only / Vector Only / Hybrid / Hybrid+Rerank，参数、候选TopK、阈值、query原句/改写策略保持同一预注册口径。
- [ ] 记录实际embedding/rerank模型、修订版本、endpoint身份与环境；不抄Pilot配置当作当前实测。密钥不得入包。
- [ ] 固定评测K、延迟冷热缓存/超时/重试、空返回和失败计数、随机种子、并发、截断和稳定排序规则。
- [ ] 使用22条Development做执行器冒烟；不得以Holdout作试跑或参数选择。
- [ ] 明确正式运行是否只做检索；若含答案生成，预注册逐题标准要点、可接受变体、来源引用及人工/模型judge口径。
- [ ] 区分既有通用expected多目标OR匹配与sidecar的requires_all_evidence；正式执行器须读取签核后的ID相关集合，不能只匹配数值串。

## 报告与停止条件

- [ ] 人工授权正式运行；保存冻结配置、输入哈希、四组逐题TopK/分数、运行状态与时间。
- [ ] 分别报告Development与Holdout的Hit@K、MRR@10、NDCG@10、Recall@10、完整证据覆盖与p50/p95延迟，不混合为50条未见测试。
- [ ] 按文档、题型、证据簇披露结果；负收益、空返回、超时不得移除分母或改题规避。
- [ ] 哈希漂移、签核缺失、模型不可用、权限范围或数据库不等价时暂停，记录原因；修复执行问题后是否重跑须有清楚版本记录。
- [ ] 首次结果后不得继续用Holdout调参；需要改系统时重新界定Development与新Holdout。

正式Benchmark结果：未测量。当前只完成离线建设材料。
''')

# Workbooks receive a single editable sign-off row per candidate, no copied historical approvals.
sheetrows=[]
for r in sorted(records,key=lambda r:(r['selection_tier']!='holdout_primary_proposed',r['review_id'])):
    sheetrows.append([r['review_id'],r['selection_tier'],r['ai_recommendation'],r['query'],r['reference_answer'],None,None,None,None,
                      '；'.join(f"{s['document']} p{s['physical_page']}" for s in r['sources']),
                      '；'.join(r['evidence_chunk_ids']),r['review_reason'],r['candidate_id'],r['proposal_id'],r['review_record_sha256']])
dump('_work/workbook_data.json',{'rows':sheetrows,'summary':read(OUT/'summary_counts.json'),'dev':[[r['batch_id'],r['query'],r['gold_case_id'],'Development'] for r in dev]})

write('README.md','''# P4-Gold-Completion-01

本轮交付已完成，等待人工确认。当前正式Gold仍为22条，全部Development；新增批准0条，冻结Holdout 0条，正式Benchmark未运行。

优先打开[人工签核包](human_signoff_packet.md)及`outputs/p4-gold-completion-01/human_signoff.xlsx`。工作簿“签核”页前28条为Holdout主选，人工字段全空；后18条为备选、替换或驳回裁决。

- [数量与覆盖报告](gold_coverage_report.md)
- [B28–B42简洁汇总](b28_b42_signoff_summary.md)
- [B43–B57独立审核](b43_b57_independent_review.md)
- [新候选及全量待审汇总](new_candidate_review_summary.md)
- [Development/Holdout方案](development_holdout_split.md)
- [Benchmark准备清单](benchmark_readiness_checklist.md)
- [证据全文](evidence_catalog.md)
- [验证记录](validation.md)

机器可读材料：candidate_reviews.jsonl、new_candidates_15.jsonl、holdout_proposed_28.jsonl、development_manifest.json、candidate_inventory_72.json、evidence_catalog.jsonl、input_integrity.json、packet_manifest.json。它们都是审核/划分材料，不是运行用Gold导出。

原始57候选、冻结447 Chunk、3份PDF、既有22 Gold与P3文件保持不动。本轮仅新建此目录与相应outputs子目录；不修改生产代码、数据库、检索配置，不commit/push。
''')
print(json.dumps(read(OUT/'summary_counts.json'),ensure_ascii=False,indent=2))
