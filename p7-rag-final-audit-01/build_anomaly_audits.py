"""Offline, read-only evidence extraction. Writes only its own audit directory."""
import json, re, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'p6-silver-e2e-500/runs/p6-e2e-run-01-qwen-flash'
CORPUS = ROOT / 'storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl'
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
cases_list = rows(ROOT / 'p6-silver-e2e-500/silver_cases_500.jsonl')
cases = {c['case_id']: c for c in cases_list}
scores = {c['case_id']: c for c in rows(RUN/'scores.jsonl')}
diags = {c['case_id']: c for c in rows(RUN/'failure_diagnostics.jsonl')}
attention = json.loads((RUN/'manual_attention.json').read_text(encoding='utf-8'))
corpus = rows(CORPUS)
corpus_map = {c.get('chunk_id', c.get('id')):(i+1,c) for i,c in enumerate(corpus)}
norm = lambda x: re.sub(r'\s+', '', x)
dims = ['answer_correctness','completeness','faithfulness','citation_correctness']
multi = [k for k,c in cases.items() if c['question_type']=='multi_condition']
multi_bad = [k for k in multi if scores[k]['score_state']!='success' or any((scores[k].get(d) or {}).get('score')!=1 for d in dims)]
retrieval = [k for k,d in diags.items() if d['primary_failure_bucket'].startswith(('1_','2_'))]
hall = attention['hallucination_suspected']
cit = attention['invalid_citation_index']
selected = sorted(set(multi_bad+retrieval+hall+cit))

# AI observations from direct reading of the retained generation request and frozen sources.
NOTES = {
'0036': ('引用错配；单位混淆', '0.24条；第192页表10.2.2.6', '实际[1]安装电杆地线直埋式行为0.24/0.24；[2]电杆地线直埋式为0.29/0.29。回答数值取[1]却标[2]，且把人工消耗量工日写成工程计量单位条。建议保留引用/单位疑点，非纯数值编造。', '人工需复核表格多级表头与消耗量的单位。', ['WH12019002','WH12006002','单位 工日']),
'0037': ('引用编号越界', '[6]（5次）', '实际只返回4个来源，保留prompt仅[1]至[3]；[6]不存在。核心MCS15必选、MCS14推荐在[1]第25页条目6有直接支持；兼容性扩展措辞仍需核对，条目6不是来源[6]。', '评分失败不能掩盖确定的编号越界；需人工分开确认内容与引用。', ['须支持覆盖增强','MCS15']),
'0088': ('引用编号越界；额外推断', '[6]（5次）；泄漏或堵塞；不得自行处理', '4个返回来源、实际prompt仅[1]至[3]，不存在[6]。核心“检测压力和制冷效果、及时上报、通知专业队伍补加”在[1]第72页空调条目6有支持；这是条目6，不是来源[6]。泄漏/堵塞与不得自行处理未见直接支持，不能以核心事实有据豁免所有扩展句。', '人工需逐句核验核心措施与额外建议，不能沿用Judge引用满分。', ['检测制冷剂压力','检测记录制冷剂压力','泄漏','堵塞']),
'0089': ('题干条件不足；标注污染；截断非充分原因', '7/2.2；1.00工日、0.50工日', '实际[1]WH12009010支持7/2.2平原1.00/0.50；[2]WH12009016保留7/3.0平原1.40/0.70。题干未给线径或技/普工，Silver只给0.70并混入木杆7/3.0证据。被截断的是木杆辅助证据，目标水泥杆7/3.0仍在prompt。因此不能把结果直接归因为关键上下文丢失，Judge“事实与上下文不符”亦需复核。', '人工先澄清线径、工种与木杆证据是否应属于本题，再裁决生成完整性。', ['WH12009010','WH12009016','WH12009043']),
'0090': ('例外条件遗漏；自相矛盾', '高速公路中人孔的检修周期为半年', '回答先写半年，继而写按需；Silver和来源的高速公路例外为按需。建议保留未正确应用特殊场景条件及答内矛盾疑点。', '人工复核一般周期与高速公路例外，按首句误导程度判定。', ['高速公路中人孔','半年']),
'0138': ('条件遗漏；参考答案范围疑点', '仅夜间维护作业增加费', '回答覆盖夜间条件，未整合城区条件对应的维护干扰费。Silver又列特殊地区等多项，不能自动认为城区夜间全部必收；应按项目适用条件逐项确认。', '人工核对城区和夜间两条件，以及Silver额外费用是否必要。', ['维护干扰费','夜间维护作业增加费']),
'0146': ('单位混淆；标注解析疑点', '计量单位为“个”', '来源出现法兰盘/法兰盘²次，未直接支持回答“个”；Silver上标²疑似乘号解析。回答又把日常维护改述为更换计费。', '人工查看原表单位，不能将解析字符直接当正确计量单位。', ['WH11013','法兰','计量单位']),
'0151': ('题干条件不足；单位错误；辅助证据缺失', '徒步巡回；73.29元/工日、14.66元/工日', '实际[1]有车辆山区24.43/4.89，[2]有徒步山区73.29/14.66。题干未限定车辆，回答选择徒步有数字支持；附加元/工日把工作量计价与人工单价混淆。两个未召回标注为巡查操作文本，并非数值所在chunk；数值证据已在prompt，故检索miss标签不能作为答错的充分原因。', '人工需先确定车辆/徒步范围，再核对计量单位；保留原分。', ['WH11003003','WH11004002','计量单位']),
'0157': ('条件混淆；题干拼接疑点；评分失败', '15m以上每增加1m为91.20元', 'prompt同页有WH23115060高度增量18.24和WH23115066扩装设备板件91.20，两行属于不同项目。题干把高度增量与扩装板件拼合，回答也把91.20当高度增量。不能自动以Silver18.24补评分。', '人工核对跨页项目归属、线性高度增量是否适用于板件。', ['WH23115060','WH23115066']),
'0180': ('引用格式错误；多条件整合', '[4.5.1]、[4.2.2]、[6.1.2]', '终端配置与安全条件都有回答，但把章节编号作为来源引用，实际来源标签仅整数[1]至[3]。仅检查整数正则会漏掉此类错误。', '人工需核对章节编号是否准确及每条是否由实际保留片段支持。', ['机顶盒配置','装维作业安全','用户信息安全']),
'0192': ('证据粒度不足；操作过程未覆盖', '具体操作流程未在上下文中明确说明', '来源主要是“能进行入户光缆热熔与冷接”的能力标准，并非终端操作步骤。回答承认流程缺失，不能把完整性不足直接等同于幻觉；操作前测试等时序也需支持。', '人工判断题干是否超出标注证据的粒度，并复核新增时序。', ['热熔与冷接','手持终端','光路达标']),
'0194': ('Silver表头错列；Judge疑似误判', '技工114元/工日，普工61元/工日', '实际[3]第158页明确给出114/61元每工日；[1]表头也支持工日单价。Silver的1.92是综合单价、1.30是人工费，不能当技工和普工单价。建议优先人工修订参考/Judge判断，不能将该主结论标为已证实幻觉。', '人工核对多级表头以及题干“单价”的含义。', ['WH12024001','人工费单价为']),
'0195': ('引用上下文缺失；跨能力推断；评分失败', '[4]；用光功率计检测；排除组网异常', '4个返回来源中[4]未进入实际prompt，编号范围有效不等于实际可引用；回答将能力标准整合为诊断步骤，需逐步核对推断是否获得来源支持。', '评分失败，人工需核验播放故障步骤及实际可见来源，不填自动补分。', ['光功率计','机顶盒','故障处理']),
'0222': ('标注检索未命中；替代支持；覆盖遗漏', '维护分项作业工作量清单费用由维护分项作业费、材料费等构成', '标注chunk不在返回Top4，但实际[3]第87页8.4.1.1列有费用构成，可替代支持部分答案。回答省略规费、安全生产费、其他项目费、销项税额等显式项，不能只因标注ID未命中就判知识不可得。', '人工比较参考范围和替代来源，并判遗漏是否影响完整性。', ['8.4.1.1','销项税额构成']),
'0230': ('费用概念混淆；跨来源整合；评分失败', '光缆引入、跳接与测试费用；未明确企业管理费及利润', '回答把操作工作内容描述为综合单价构成，未清楚列出人工费、企业管理费、利润和风险范围。需核对实际prompt是否保留定义；不能把Judge失败当执行失败或自动赋零。', '人工检查费用定义是否在prompt及回答能否等价覆盖。', ['综合单价','利润','风险']),
'0237': ('引用编号越界；可答性待审', '[7]；职业技能评价当员工绩效', '实际[7]不存在；核心“理论和实操”可由[3]职业技能等级权重表支持。技能评价可否回答企业绩效需要语义判断，Silver无答案标签未人工确认，Judge引用满分遗漏了[7]。', '人工区分来源编号错误与岗位绩效/技能评价的可答范围。', ['评价机制','理论和技能','安全作业知识 15']),
'0243': ('引用编号越界；目的推断', '[5]；提升用户满意度', '[5]不存在；[2]/[3]有沟通、交付、维护技巧，[1]有APP及Wi-Fi功能，但这些措施能提升满意度属于推断，不是来源直接规定的满意度方案。', '人工核对有据技能事实与未证实效果承诺、无答案标签。', ['沟通技巧','Wi-Fi质量分析','服务交付']),
'0247': ('引用编号越界；概念范围', '[8]；工具用具使用费', '[8]不存在；已返回来源存在工具费用相关概念，并不能修复错误编号。需区分企业管理费内工具用具使用费与措施费中的生产工具用具使用费，以及哪些内容实际保留在prompt。', '人工确认具体费用条目及其所属费用类别。', ['工具用具使用费','措施项目费']),
'0265': ('从技能事实外推满意度评估', '通过用户反馈判断满意度；贯穿全过程', '来源为技能等级及服务技巧，不直接规定满意度指标或全过程评估机制。回答把相关技能转换为确定评估流程，疑似外推；无答案标签也需人工确认。', '人工需核验是否为合理有限推断以及是否应明确证据不足。', ['服务能力','沟通技巧','评价']),
'0273': ('对象混淆；数值单位混淆；检索漏项', '配电柜红灯表示光路异常；防雷接地电阻≤100Ω', '目标配电/防雷chunk未返回；回答把配电柜故障当光路问题。实际[3]有OTDR，故Judge称OTDR无依据不准确；但ρ≤100的注释是土壤电阻率Ω·m，不是接地电阻阈值。', '人工需区分检索对象错误、错误迁移和数值单位误读。', ['OTDR','ρ≤100','土壤电阻率']),
'0276': ('Silver列错配；Judge疑似误判', '交越0.5米；平行1.5米', '实际[1]表D.0.4表头“平行时 交越时”，>500mm给水管行1.5/0.5，支持回答核心结论。Silver1.5取的是平行列。建议优先复核参考及Judge，勿把交越0.5当已确认幻觉。', '人工核对原表表头、单位和回答末句的泛化范围。', ['名称 平行时 交越时','给水管（管径大于500mm)']),
'0288': ('来源范围歧义；Judge疑似过判', '表—04；第166页表—03', '实际[1]第100页结算表写表—04，[2]第166页预算表写表—03，回答明确提示差异，两者都有来源。题干未限定预算/结算；不能只与Silver表—03比较即定幻觉。', '人工确认题干预期表的范围及回答首句是否造成误导。', ['维护分项作业费 1.1 表—04','维护分项作业费 1.1 表—03']),
'0310': ('引用编号越界；无答案标签待审', '[6]、[5]、[7]', '[5][6][7]均超出4来源；理论/实操60分在[2]有直接支持，逐级要求与安全作业在[3]，服务规范在[2]/[3]。Judge“无有效事实支持”概括过宽，编号错误与内容支持应分离。', '人工核对技能考核是否能回答绩效优化，不能将越界引用等同全部事实虚构。', ['60 分','依次递进','安全作业知识']),
'0312': ('技能标准外推市场计划', '销售技巧与交付能力以匹配市场需求', '实际片段有技能、交付和销售技巧，但没有市场趋势数据或计划对齐方法；各技能事实有据，市场适应性的因果连接缺乏直接证据。', '人工区分无答案问题的相关信息回答与越界确定性主张。', ['销售技巧','服务能力','光纤到户']),
'0313': ('跨设备/业务范围混淆；参考数值疑点', '太阳能29.64；文档中无直流拉远', '直流拉远标注chunk未返回，故不能据局部上下文声称整份文档没有。实际[1]另一业务表有太阳能山区29.64，[2]发电设备巡检表有58.14，Silver37.62却属固定燃油发电机组山区。同时存在检索缺项、范围选择和Silver数值污染。', '人工核对设备、业务章节、跨页项目编码及两个子问题的范围。', ['WH21111003','WH21111009','WH31107007']),
'0318': ('跨片段引用错配；条件省略', '两项指标均引用[1]', '[1]实际有直流高频开关电源季度及±5%，但交流输入380V±10%需对应其他来源；Judge说不平衡度的[1]不匹配不够精确。还需保留超过半载、节能模式除外等适用条件。', '人工逐项定位交流/直流两个条件，勿沿用Judge错误定位。', ['不平衡度','380','节能模式']),
'0321': ('编码层级混淆；题干歧义', '项目编码WH12029', 'WH12029在章节/清单中确实存在，明细计价行是WH12029001。回答选择上层编码，不能称该字符串凭空捏造；需明确题干要求清单项目还是明细计价编码。', '人工核对项目编码粒度、8.3.2.3规则与题干意图。', ['WH12029001','WH12029 更换井盖']),
'0331': ('来源范围歧义；Silver混入无关证据', '人工23.94、企业管理7.18', '实际[2]WH23110009打穿混凝土墙洞明确支持23.94/7.18；[1]宽带WH41101002为14.32/3.92。题干没有业务章节限定。Silver还附站址业主维系等无关证据，使all-retrieved判定失败；不能据此判定核心检索失败或幻觉。', '人工确认应采用移动设施还是宽带安装表，并清理无关标注。', ['WH23110009','WH41101002']),
'0360': ('跨设备工作内容迁移；Judge定位不精确', '附属设备运行、紧固连接线缆[2]', '[2]确实出现“检查附属设备运行情况、检查紧固连接线缆”，Judge说文字未支持不准确；但该段承接发电设备而非铁塔，存在把其他设备维护任务套入铁塔的疑点。', '人工需按跨页表格归属核对，不只做字符串包含判断。', ['检查紧固连接线缆','检查附属设备运行','铁塔']),
'0362': ('数值列混淆；题干设备混配', '人工费217.17；室内天线地面塔40m以下', '[1]WH23111003清楚给人工723.90、管理217.17、利润217.17，回答人工费取错列，目标行已在prompt。题干将移动定向通信天线的塔高条件与室内天线混配；未返回的室内证据不能解释已可见行的错列。', '人工同时复核题干设备类型和数值列，不只归因检索。', ['WH23111003','安装移动定','安装室内天线']),
'0363': ('算术/列混淆；Silver场景错配', '人工费与利润之和96.10', '[1]WH23111011拉线塔行人工320.34、利润96.10，若按该行应合416.44；回答仅取利润。Silver370.50来自铁塔20m以下行285+85.50，场景也错。标注缺的另页智慧灯杆行与本题无关，主要错误不能归检索。', '人工核对拉线塔场景与加法；不使用错误Silver自动补分。', ['WH23111011','WH23111009']),
'0420': ('题干合并类别；引用错配；评分失败', '直埋式延伸式安装62.42；所有来自第209页', '题干“直埋式延伸式”混合互斥类型。回答给出直埋62.42、延伸86.16两类，但都引更换页[1]而安装来源应另核。需分别审安装/更换和类型，不可依Silver单一86.16直接评分。', '人工先拆清作业与类型，再审引用和计量单位。', ['WH12020002','WH12020003','WH12019002','WH12019003']),
'0434': ('技能评价与绩效语义边界；Judge依据不足', '人员绩效评估基于理论知识与技能实操', '[3]职业技能权重表和[1]服务能力支持列举内容；缺的是把技能评价等同绩效评估的范围说明。Judge理由“部分事实有引用，但不完整”不足以单独证明幻觉。', '人工先判技能考核是否覆盖题意，再判确定性表述及无答案标签。', ['理论和技能','服务能力','权重']),
'0454': ('消耗量单位错误；工作范围推断；评分失败', '1.75个/台；不包含线缆连接且另计', '[1]人工199.50有据，1.75在人工工日列而非个/台。[1]配线架工作内容未列线缆连接；[2]安装机架柜列线缆连接，但不是同一项目。Silver的“包含”与回答“明确不含且另计”均需核对，不能从未列出推出排除。', '人工检查计量单位、工日消耗和作业边界；保留评分失败。', ['WH23103001','单位 工日','线缆连接']),
}

def rel(p): return p.relative_to(ROOT).as_posix()
def link(p,label=None): return f'[{label or p.name}](../{rel(p)})'
def quote(s): return '\n'.join('> '+x for x in str(s).splitlines())
def snippets(text, terms):
    out=[]
    for term in terms:
        for m in list(re.finditer(re.escape(term),text))[:2]:
            a=max(0,m.start()-80); b=min(len(text),m.end()+190)
            part=text[a:b]
            if part not in out: out.append(part)
    return out

findings={}
evidence_dir=OUT/'anomaly_evidence'; evidence_dir.mkdir(exist_ok=True)
for k in selected:
    t=json.loads((RUN/'cases'/f'{k}.json').read_text(encoding='utf8')); s=scores[k];c=cases[k]
    chat=[x for x in t['model_calls'] if x['kind']=='chat'][-1]
    prompt='\n'.join(m['content'] for m in chat['request']['messages'])
    context=prompt.split('检索到的相关文档：')[-1]
    labels=[int(n) for n in re.findall(r'^\[(\d+)\] 来源：',context,re.M)]
    source_rows=[]
    for i,x in enumerate(t['sources'],1):
        ch=x['chunk']; ci=ch['id']; frozen=corpus_map.get(ci)
        source_rows.append({'index':i,'chunk_id':ci,'document':ch['metadata'].get('source'),'page':ch['metadata'].get('page_number'), 'present_label_in_actual_prompt':i in labels,'full_source_text_in_actual_prompt':norm(ch['text']) in norm(context), 'frozen_corpus_exists':frozen is not None,'frozen_corpus_line':frozen[0] if frozen else None,'text':ch['text']})
    typ,suspect,note,human,terms=NOTES[k[-4:]]
    ev={'case_id':k,'question':c['question'],'answer':t['answer'],'silver_reference_answer':c.get('reference_answer'),'silver_source_evidence':c.get('source_evidence'), 'original_score':s,'original_diagnostic':diags[k], 'actual_generation_api_call_id':chat['api_call_id'],'actual_generation_prompt':prompt,'actual_source_labels':labels,'sources':source_rows,'retrieval_observation_summary':[{'kind':o['kind'],'request':{a:b for a,b in o['request'].items() if a!='query_embedding'},'results':o.get('results')} for o in t['retrieval_observation']], 'trace_path':rel(RUN/'cases'/f'{k}.json'),'trace_sha256':hashlib.sha256((RUN/'cases'/f'{k}.json').read_bytes()).hexdigest()}
    (evidence_dir/f'{k}.json').write_text(json.dumps(ev,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    findings[k]={'case_id':k,'ai_suggested_classification':typ,'suspected_excerpt':suspect,'ai_suggestion':note,'human_review_reason':human,'review_status':'pending','human_verdict':'','human_reviewer':'','human_reviewed_at':'','human_notes':'','audit_groups':[a for a,v in [('invalid_citation',cit),('suspected_hallucination',hall),('retrieval_context',retrieval),('multi_condition',multi_bad)] if k in v],'source_case_line':next(i+1 for i,x in enumerate(cases_list) if x['case_id']==k),'trace_path':ev['trace_path'],'score_path':rel(RUN/'scores'/f'{k}.json'),'evidence_path':rel(evidence_dir/f'{k}.json'),'actual_source_labels':labels,'answer_integer_citations':[int(n) for n in re.findall(r'\[(\d+)\]',t['answer'])],'returned_source_count':len(t['sources']),'actual_prompt_evidence_snippets':snippets(context,terms),'sources':[{a:b for a,b in x.items() if a!='text'} for x in source_rows]}

(OUT/'case_ai_findings.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

HEADER='审计日期：2026-11-06。状态：pending；全部结论为AI只读复核建议，人工判决/审核人/时间均留空。未调用模型、未改写原始分数或Silver标签，未改生产代码或参数。来源是冻结运行的真实生成请求，而不是仅看完整 augmented_context；prompt示例中的编号不算检索来源。分数展示读取最终汇总 [scores.jsonl](../p6-silver-e2e-500/runs/p6-e2e-run-01-qwen-flash/scores.jsonl)，逐case scores文件可能保留修复前记录，不应混用。冻结来源为 [447 corpus](../storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl)。完整实际请求和原分副本见各case证据包。\n\n'
def section(k):
    f=findings[k]; c=cases[k]; s=scores[k]; ev=json.loads((evidence_dir/f'{k}.json').read_text(encoding='utf8'))
    lines=[f'## {k}',f"问题：{c['question']}",f"Silver参考：{c.get('reference_answer')}",'实际回答：',quote(ev['answer']),f"原始评分：state={s['score_state']}；"+'；'.join(f"{d}={(s.get(d) or {}).get('score')}" for d in dims),f"AI建议分类：{f['ai_suggested_classification']}。",f"疑似片段：{f['suspected_excerpt']}",f"AI复核：{f['ai_suggestion']}", '实际prompt定位片段：']
    lines += [quote(x) for x in f['actual_prompt_evidence_snippets']]
    if not f['actual_prompt_evidence_snippets']:lines += ['本次关键词未抽到片段；完整请求见下方证据包，不能视作全文不存在。']
    lines += ['Silver原标注（用于对比，不预设正确）：']+[quote(x['chunk_id']+'：'+x['excerpt']) for x in c.get('source_evidence',[])]
    lines += [f"人工待确认原因：{f['human_review_reason']}", '人工判决：　审核人：　时间：　状态：pending', f"定位：{link(ROOT/'p6-silver-e2e-500/silver_cases_500.jsonl','Silver JSONL')} 第{f['source_case_line']}行；{link(RUN/'cases'/f'{k}.json','原始Trace')} `answer/model_calls[].request.messages/sources/retrieval_observation`；{link(RUN/'scores'/f'{k}.json','原始Score')}；[提取证据包](anomaly_evidence/{k}.json)。"]
    return '\n\n'.join(lines)+'\n'

citation=['# P7 引用异常审计\n',HEADER,'整数来源编号越界复算6例、16个出现次数。另有真实来源被prompt裁剪以及章节号伪装引用，均与整数越界分开。编号存在、chunk存在和语义支持是三个不同检查。\n','|case_id|实际整数引用（含重复）|返回来源|实际prompt标签|越界编号|\n|---|---|---:|---|---|']
for k in cit:
    f=findings[k]; bad=sorted({n for n in f['answer_integer_citations'] if not 1<=n<=f['returned_source_count']})
    citation += [f"|{k}|{f['answer_integer_citations']}|{f['returned_source_count']}|{f['actual_source_labels']}|{bad}|"]
citation += ['\n六例返回的真实来源均逐项与冻结447 corpus ID核验；明细见下表。不存在的编号没有对应来源，不能替换编号后宣称原引用有效。\n','|case_id|来源编号|chunk_id|文件/页|冻结corpus行|prompt标签存在|\n|---|---:|---|---|---:|---|']
for k in cit:
 for x in findings[k]['sources']:citation += [f"|{k}|{x['index']}|{x['chunk_id']}|{x['document']} / {x['page']}|{x['frozen_corpus_line']}|{x['present_label_in_actual_prompt']}|"]
citation += ['\n补充：p6s-0180引用[4.5.1]等章节号不属于本6例整数越界统计；p6s-0195的[4]在sources里但未进入prompt。没有越界也不能证明语义正确。\n']+[section(k) for k in cit]
(OUT/'citation_audit.md').write_text('\n'.join(citation),encoding='utf8')

hall_doc=['# P7 疑似幻觉审计\n',HEADER,'范围：原始 `hallucination_suspected=true` 的18例。标志来自同模型Judge，不是人工确认幻觉数。以下逐例区分错误引用、无证据外推、表格误读和Silver/Judge疑似错误，原分保持不变。0276、0194等需优先复核参考，0089、0151、0288、0331等需确认题干范围；不能将18直接报告为真实幻觉数量。\n']+[section(k) for k in hall]
(OUT/'hallucination_audit.md').write_text('\n'.join(hall_doc),encoding='utf8')

ret_doc=['# P7 检索与上下文审计\n',HEADER,'原始主桶7例 `1_retrieval_evidence_miss` + 1例 `2_context_evidence_miss`。原桶按全部标注chunk/引文命中判断，不等于人工根因。Trace `retrieval_observation[].results`保存4个最终search结果，request声明candidate_k=20、top_k=4；没有内部候选池20条或过滤前排名。因此不能区分候选不足、内部排名/阈值淘汰；不推测排名第5或reranker错误（本运行rerank禁用）。\n','目标标注块未返回，只能确定“未在可见Top4”，而非“全库不存在”。已返回与实际prompt对比可确认裁剪；已在prompt的核心证据却被错列/错加，才能讨论生成阶段误读。\n']
for k in retrieval:
    ev=json.loads((evidence_dir/f'{k}.json').read_text(encoding='utf8')); have={x['chunk_id'] for x in ev['sources']}; d=diags[k]
    ret_doc += [f'## {k} Trace阶段记录',f"原桶：{d['primary_failure_bucket']}；返回4来源：{', '.join(sorted(have))}",'|标注chunk|冻结corpus行|返回rank|完整标注引文在实际prompt|\n|---|---:|---:|---|']
    for e in cases[k].get('source_evidence',[]):
        ci=e['chunk_id']; rank=next((x['index'] for x in ev['sources'] if x['chunk_id']==ci),None); frozen=corpus_map.get(ci)
        ret_doc += [f"|{ci}|{frozen[0] if frozen else '缺失'}|{rank if rank else '未返回'}|{norm(e['excerpt']) in norm(ev['actual_generation_prompt'])}|"]
    ret_doc += ['候选不足：不可判；内部排名淘汰：不可判；最终Top4及prompt裁剪：见上述实测。LLM是否忽略或错读：仅按下述实际保留内容作AI建议，不以答案反推召回。',section(k)]
ret_doc += ['## 证据限制\n\n0089确有部分标注引文未保留，但缺的是木杆辅助行，核心水泥杆7/3.0行仍在；0151、0331、0362、0363的主要数值行也在实际prompt。7+1是探索性ID/引文规则标签，不能直接当8个检索/裁剪导致的最终失败。未请求新模型或重新检索。']
(OUT/'retrieval_context_audit.md').write_text('\n'.join(ret_doc),encoding='utf8')

mult_doc=['# P7 多条件100例审计\n',HEADER,'范围：100例；四维任一非满分或评分失败的并集16例，其中11例成功评分但至少一维非满分、5例评分失败。其余84例四维自动满分，不表示人工已通过；原主失败桶有17例不等于本16例，因为桶规则及维度并集不同。遗漏、条件混淆、数值单位、跨来源整合与引用逐例记录；不补分。\n']+[section(k) for k in multi_bad]
mult_doc += ['## 100例覆盖索引\n','|case_id|correctness|completeness|faithfulness|citation|score_state|本次详细分析|\n|---|---:|---:|---:|---:|---|---|']
for k in multi:
 s=scores[k]; mult_doc += ['|'+k+'|'+'|'.join(str((s.get(d) or {}).get('score')) for d in dims)+f"|{s['score_state']}|{'是' if k in multi_bad else '否；四维自动满分，仅列索引'}|"]
(OUT/'multi_condition_audit.md').write_text('\n'.join(mult_doc),encoding='utf8')
summary={'selected_union':len(selected),'invalid_citation_cases':len(cit),'invalid_citation_occurrences':sum(sum(not 1<=n<=findings[k]['returned_source_count'] for n in findings[k]['answer_integer_citations']) for k in cit),'hallucination_suspected':len(hall),'retrieval_context':len(retrieval),'multi_condition':len(multi),'multi_flagged':len(multi_bad),'multi_failed':sum(scores[k]['score_state']=='failed' for k in multi_bad),'corpus_count':len(corpus),'all_returned_sources_found_in_corpus':all(x['frozen_corpus_exists'] for k in cit for x in findings[k]['sources']),'human_verdicts_filled':sum(bool(f['human_verdict']) for f in findings.values())}
(OUT/'anomaly_audit_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(summary,ensure_ascii=False))
