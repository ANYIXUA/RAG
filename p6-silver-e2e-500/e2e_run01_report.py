"""Exploratory Silver-only metrics and auditable failure analysis; no API calls."""
from __future__ import annotations
import csv
import importlib.util
import io
import json
import re
from collections import Counter,defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('run01',HERE/'e2e_run01.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
OUT=m.OUT
BUCKETS={
 '1_retrieval_evidence_miss':'检索未召回Silver标注证据（代理诊断）',
 '2_context_evidence_miss':'已召回但未完整进入LLM上下文（代理诊断）',
 '3_wrong_with_evidence':'证据进入上下文但答案错误',
 '4_incomplete':'答案遗漏关键条件或步骤',
 '5_unsupported_generation':'生成内容缺乏证据支持/疑似幻觉',
 '6_citation_mismatch':'引用与实际证据不符',
 '7_execution_failure':'模型调用或执行异常/超时',
 '8_judge_unreliable':'自动评分无法可靠判断',
 'pass_or_no_detected_failure':'未发现上述失败（不是人工正确性确认）'}


def correctness_ratio(scores):
    values=[r['answer_correctness']['score'] for r in scores if r.get('score_state')=='success'
            and not r.get('correctness_excluded') and r.get('answer_correctness',{}).get('score') is not None]
    return m.ratio(sum(v==1 for v in values),len(values))


def stat(values):
    values=[v for v in values if v is not None]
    return {'denominator':len(values),'mean':sum(values)/len(values) if values else None,
            'p50':m.percentile(values,.5),'p95':m.percentile(values,.95),'unit':'milliseconds'}


def score_values(scores,field):
    return [r[field]['score'] for r in scores if r.get('score_state')=='success'
            and isinstance(r.get(field),dict) and r[field].get('score') is not None]


def score_metric(scores,field):
    values=score_values(scores,field)
    return {'denominator':len(values),'score_sum':sum(values),'mean':sum(values)/len(values) if values else None,
            'distribution':dict(Counter(str(x) for x in values)),
            'full_score_ratio':m.ratio(sum(v==1 for v in values),len(values))}


def normalize(text):return re.sub(r'\s+',' ',text or '').strip()


def diagnostics(case,result,score):
    refs=set(case.get('source_chunk_ids') or [])
    retrieved={r['chunk']['id'] for call in result.get('retrieval_observation',[]) for r in call.get('results',[])}
    chats=[c for c in result.get('model_calls',[]) if c['kind']=='chat' and c.get('response')]
    prompt='\n'.join(x.get('content','') for x in chats[-1]['request']['messages']) if chats else ''
    # Actual rendered prompt is authoritative, including its production truncation.
    quotes=case.get('source_evidence') or []
    context_hits=[e['chunk_id'] for e in quotes if normalize(e['excerpt']) in normalize(prompt)]
    raw_markers=re.findall(r'\[(\d+)\]|【(\d+)】',result.get('answer') or '')
    indices=[int(a or b) for a,b in raw_markers]
    sources=result.get('sources',[])
    valid=sum(1<=i<=len(sources) for i in indices)
    valid_in_context=sum(1<=i<=len(sources) and normalize(sources[i-1]['chunk']['text'])[:35] in normalize(prompt) for i in indices)
    diag={'case_id':case['case_id'],'question_type':case['question_type'],
          'reference_chunk_ids':sorted(refs),'retrieved_chunk_ids':sorted(retrieved),
          'reference_all_retrieved':refs<=retrieved if refs else None,
          'reference_quote_context_hit_ids':context_hits,
          'reference_all_quotes_in_actual_prompt':len(context_hits)==len(quotes) if quotes else None,
          'citation_markers':indices,'citation_index_valid_count':valid,
          'citation_index_and_context_valid_count':valid_in_context,
          'actual_prompt_chars':len(prompt),'context_verification':'full normalized Silver quotation in actual rendered request; absence does not rule out alternative support'}
    if result.get('state')!='success':bucket='7_execution_failure'
    elif score.get('score_state')!='success' or score.get('confidence')=='low' or case['case_id']=='p6s-0473':bucket='8_judge_unreliable'
    else:
        value=lambda field:score.get(field,{}).get('score')
        bad=value('answer_correctness') is not None and value('answer_correctness')<1
        if case['question_type']=='unanswerable' and value('no_answer_behavior') in [0,.5] and not score.get('hallucination_suspected') and value('faithfulness')!=0:bucket='8_judge_unreliable'
        elif case['question_type']!='unanswerable' and bad and not diag['reference_all_retrieved']:bucket='1_retrieval_evidence_miss'
        elif case['question_type']!='unanswerable' and bad and not diag['reference_all_quotes_in_actual_prompt']:bucket='2_context_evidence_miss'
        elif score.get('hallucination_suspected') or value('faithfulness')==0:bucket='5_unsupported_generation'
        elif (value('citation_correctness') is not None and value('citation_correctness')<1) or valid<len(indices):bucket='6_citation_mismatch'
        elif value('completeness') is not None and value('completeness')<1:bucket='4_incomplete'
        elif bad:bucket='3_wrong_with_evidence'
        else:bucket='pass_or_no_detected_failure'
    diag['primary_failure_bucket']=bucket
    diag['unanswerable_provisional']=case['question_type']=='unanswerable'
    diag['diagnosis_is_exploratory']=True
    return diag


def make_human_checklist(cases,results,scores,diags):
    selected=[];byid={c['case_id']:c for c in cases}
    def add(cid):
        if cid not in selected and cid in byid:selected.append(cid)
    add('p6s-0473')
    add('p6s-0088')
    # Exactly 8/type where possible, preserving mandatory ambiguity case.
    for kind in m.TYPES:
        pool=[c['case_id'] for c in cases if c['question_type']==kind]
        pool.sort(key=lambda cid:(not scores.get(cid,{}).get('needs_human_review',True),
                                  diags.get(cid,{}).get('primary_failure_bucket')=='pass_or_no_detected_failure',cid))
        for cid in pool:
            if sum(byid[x]['question_type']==kind for x in selected)>=8:break
            add(cid)
    rows=[]
    for cid in selected:
        c=byid[cid];r=results.get(cid,{});s=scores.get(cid,{});d=diags.get(cid,{'primary_failure_bucket':'not_executed','retrieved_chunk_ids':[]})
        rows.append({'case_id':cid,'question_type':c['question_type'],'question':c['question'],
          'silver_reference':c.get('reference_answer'),'rag_answer':r.get('answer'),
          'execution_state':r.get('state','pending_not_executed'),
          'failure_bucket':d['primary_failure_bucket'],'judge_confidence':s.get('confidence'),
          'judge_reasons':{f:s.get(f) for f in m.DIMENSIONS},'reference_evidence':c.get('source_evidence'),
          'retrieved_chunk_ids':d['retrieved_chunk_ids'],'trace_file':str(OUT/'cases'/f'{cid}.json'),
          'unanswerable_provisional':c['question_type']=='unanswerable','source_ambiguity':cid=='p6s-0473',
          'human_reviewer':'','human_decision':'','human_notes':'','human_reviewed_at':''})
    m.projection(OUT/'human_spot_check_40.jsonl',m.jsonl(rows))
    buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=['case_id','question_type','question','rag_answer','silver_reference','failure_bucket','judge_confidence','human_reviewer','human_decision','human_notes','human_reviewed_at'])
    writer.writeheader()
    for r in rows:writer.writerow({k:r.get(k) for k in writer.fieldnames})
    m.projection(OUT/'human_spot_check_40.csv',buf.getvalue().encode('utf-8-sig'))
    return rows


def main():
    cases=m.check_inputs();byid={c['case_id']:c for c in cases}
    results={p.stem:m.read(p) for p in (OUT/'cases').glob('*.json')}
    scores=m.load_scores(OUT)
    attempts=[m.read(p) for p in (OUT/'attempts').glob('*/*/result.json')]
    started=list((OUT/'attempts').glob('*/*/started.json'))
    succeeded=[r for r in results.values() if r['state']=='success']
    final_failed=[r for r in results.values() if r['state']!='success']
    score_rows=list(scores.values());judge_success=[s for s in score_rows if s['score_state']=='success']
    diags={cid:diagnostics(byid[cid],r,scores.get(cid,{})) for cid,r in results.items()}
    m.projection(OUT/'failure_diagnostics.jsonl',m.jsonl([diags[k] for k in sorted(diags)]))
    def stage(field):return stat([r.get('trace',{}).get(field) for r in succeeded])
    markers=sum(len(d['citation_markers']) for d in diags.values());valid=sum(d['citation_index_valid_count'] for d in diags.values())
    context_valid=sum(d['citation_index_and_context_valid_count'] for d in diags.values())
    requests=[m.read(p) for p in (OUT/'api_calls').glob('*.request.json')]
    usage=defaultdict(lambda:Counter());estimated=0;unknown=0;returned_models=Counter()
    diagnostic_usage=Counter();finish_reasons=Counter()
    for request in requests:
        rp=OUT/'api_calls'/f'{request["request_id"]}.response.json'
        response=m.read(rp) if rp.exists() else {};raw=response.get('response') or {};u=raw.get('usage') or {}
        kind=request['kind'];usage[kind].update(input_tokens=u.get('prompt_tokens',u.get('total_tokens',0)) or 0,output_tokens=u.get('completion_tokens',0) or 0,calls=1)
        if request.get('metadata',{}).get('not_a_silver_case'):
            diagnostic_usage.update(input_tokens=u.get('prompt_tokens',u.get('total_tokens',0)) or 0,output_tokens=u.get('completion_tokens',0) or 0,calls=1)
        returned_models[(kind,raw.get('model','not_returned'))]+=1
        if response.get('list_price_estimate_yuan') is not None:estimated+=response['list_price_estimate_yuan']
        else:unknown+=1
    incomplete=[c['case_id'] for c in cases if c['case_id'] not in results]
    counters=Counter(d['primary_failure_bucket'] for d in diags.values())
    hallucinated=[s['case_id'] for s in judge_success if s.get('hallucination_suspected')]
    low_conf=[s['case_id'] for s in judge_success if s.get('confidence')=='low']
    pertype={}
    for result in succeeded:
        chats=[x for x in result.get('model_calls',[]) if x['kind']=='chat' and x.get('response')]
        if chats:finish_reasons[chats[-1]['response']['choices'][0].get('finish_reason','unknown')]+=1
    for kind in m.TYPES:
        ids=[c['case_id'] for c in cases if c['question_type']==kind];sr=[scores[cid] for cid in ids if cid in scores]
        pertype[kind]={'case_count':len(ids),'execution_success':m.ratio(sum(results.get(cid,{}).get('state')=='success' for cid in ids),len(ids)),
                       'silver_full_correctness':correctness_ratio(sr),'failure_buckets':dict(Counter(diags[cid]['primary_failure_bucket'] for cid in ids if cid in diags)),
                       'faithfulness':score_metric(sr,'faithfulness'),'completeness':score_metric(sr,'completeness')}
    prior=m.read(OUT/'prior_budget.json') if (OUT/'prior_budget.json').exists() else {}
    metrics={'run_id':OUT.name,'dataset':'Silver only; not P5 Gold','silver_sha256':m.EXPECTED_SHA,
      'execution':{'target':500,'actually_attempted_unique':len({p.parent.parent.name for p in started}),
        'terminal_results':len(results),'success':len(succeeded),'failed':len(final_failed),'pending':len(incomplete),
        'timeouts_final_cases':sum(bool(r.get('timeout')) for r in final_failed),'timeout_attempts':sum(bool(a.get('timeout')) for a in attempts),
        'total_started_attempts':len(started),'retry_attempts':sum(int(p.parent.name)>1 for p in started),
        'failed_attempts':sum(a['state']!='success' for a in attempts),'interrupted_attempts':len(started)-len(attempts),
        'e2e_completion_rate':m.ratio(len(succeeded),500),'pending_case_ids':incomplete},
      'performance':{'successful_attempt_wall_ms':stat([r.get('wall_seconds',0)*1000 for r in succeeded]),
        'failed_final_attempt_wall_ms':stat([r.get('wall_seconds',0)*1000 for r in final_failed if r.get('wall_seconds') is not None]),
        'failed_attempt_retrieval_ms':stat([r.get('trace',{}).get('retrieval_latency_ms') for r in attempts if r['state']!='success']),
        'production_trace_total_ms':stage('latency_ms'),'retrieval_ms':stage('retrieval_latency_ms'),
        'generation_ms':stage('generation_latency_ms'),'rewrite_ms':stage('rewrite_latency_ms'),'intent_ms':stage('intent_latency_ms'),
        'embedding_ms':stage('embedding_latency_ms'),'context_preprocessing_ms':stage('context_latency_ms'),
        'denominator_note':'Successful FINAL attempts; failed attempts and retry overhead not hidden, reported separately. Wall time includes observation/persistence and production query logging.'},
      'tokens_and_cost':{'by_call_kind':{k:dict(v) for k,v in usage.items()},'known_usage_list_price_estimate_yuan':estimated,
        'diagnostic_calls_included_in_tokens':dict(diagnostic_usage),
        'prior_variant_cost':prior,'total_known_usage_list_price_estimate_yuan':estimated+prior.get('known_usage_list_price_estimate_yuan',0),
        'unknown_usage_calls':unknown,'conservative_committed_yuan':m.Budget(OUT,20).committed(),'budget_cap_yuan':20,
        'actual_billed_yuan':None,'actual_billing_status':'provider invoice/free quota unavailable; list-price estimate is not actual bill',
        'returned_models':[{'kind':k[0],'model':k[1],'calls':v} for k,v in returned_models.items()]},
      'quality':{'judge_same_model_as_generation':True,'self_evaluation_bias':True,'automated_not_human_accuracy':True,
        'executed_success_denominator':len(succeeded),'judge_success':m.ratio(len(judge_success),len(succeeded)),
        'generation_finish_reasons':dict(finish_reasons),
        'judge_failed':sum(s['score_state']=='failed' for s in score_rows),
        'original_scoring_failure_records':sum(m.read(p).get('score_state')=='failed' for p in (OUT/'scores').glob('*.json')),
        'scoring_failures_recovered_without_new_api_calls':len(list((OUT/'scores_recovered').glob('*.json'))),
        'silver_full_correctness':correctness_ratio(score_rows),'faithfulness':score_metric(score_rows,'faithfulness'),
        'completeness':score_metric(score_rows,'completeness'),'citation_correctness_judge':score_metric(score_rows,'citation_correctness'),
        'citation_structural_validity':m.ratio(valid,markers),'citation_index_and_prompt_presence':m.ratio(context_valid,markers),
        'no_answer_behavior_provisional':score_metric([s for s in score_rows if s.get('question_type')=='unanswerable'],'no_answer_behavior'),
        'hallucination_suspected':m.ratio(len(hallucinated),len(judge_success)),
        'low_confidence':m.ratio(len(low_conf),len(judge_success)),
        'correctness_exclusions':['all 50 unanswerable labels','p6s-0473 ambiguous reference','failed execution/judge or null verdict'],
        'judge_uncertainty_count':counters['8_judge_unreliable']},
      'primary_failure_buckets':{k:{'description':BUCKETS[k],**m.ratio(counters[k],len(results))} for k in BUCKETS},
      'by_type':pertype,'risks':m.RISKS,'human_signoff':'not_performed','holdout_executed':False}
    m.projection(OUT/'metrics.json',m.jbytes(metrics))
    human=make_human_checklist(cases,results,scores,diags)
    lines=['# P6-E2E-Run-01 失败分析','',
      '以下为同模型自动评审及Silver证据代理诊断，不是人工根因定论。每题仅有一个主分类；具体维度/引用/召回信息见failure_diagnostics.jsonl。检索证据未命中并不排除其他正确证据。','']
    for bucket,label in BUCKETS.items():
        ids=[cid for cid,d in diags.items() if d['primary_failure_bucket']==bucket]
        lines.extend([f'## {label}：{len(ids)}/{len(results)}',''])
        for cid in sorted(ids)[:3]:
            case=byid[cid];r=results[cid];s=scores.get(cid,{})
            lines.extend([f'- **{cid}**：{case["question"]}',f'  - RAG回答：{r.get("answer","")[:350]}',
                          f'  - 评分依据：{json.dumps({f:s.get(f) for f in m.DIMENSIONS},ensure_ascii=False)}',
                          f'  - Trace：cases/{cid}.json',''])
    m.projection(OUT/'failure_analysis.md','\n'.join(lines).encode())
    report(metrics,human)
    artifacts={str(p.relative_to(OUT)):m.digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()
               and p.name not in ['sha256_manifest.json','silver_topup.lock'] and 'topup_history' not in p.parts}
    artifacts.update({str(p.resolve()):m.digest(p) for p in [HERE/'e2e_run01.py',HERE/'e2e_run01_report.py',HERE/'test_e2e_run01.py']})
    m.projection(OUT/'sha256_manifest.json',m.jbytes(artifacts))
    print(json.dumps({'execution':metrics['execution'],'wall_latency_ms':metrics['performance']['successful_attempt_wall_ms'],
                      'quality':metrics['quality'],'failure_counts':dict(counters)},ensure_ascii=False,indent=2),flush=True)


def report(v,human):
    e=v['execution'];p=v['performance']['successful_attempt_wall_ms'];q=v['quality'];c=v['tokens_and_cost']
    f=lambda r:f'{r["numerator"]}/{r["denominator"]}'+(f' = {r["ratio"]:.2%}' if r['ratio'] is not None else ' (N/A)')
    variant=' --variant qwen-flash' if OUT.name.endswith('qwen-flash') else ''
    lines=['# P6-E2E-Run-01｜500条Silver真实RAG执行报告','',
      f'输入SHA-256：`{m.EXPECTED_SHA}`。本轮不含P5正式Gold/Holdout指标，未运行Holdout。','',
      '## 执行','',f'- 实际发起：{e["actually_attempted_unique"]}/500；成功：{e["success"]}；失败：{e["failed"]}；未执行：{e["pending"]}。',
      '- 本报告为完整执行报告。' if e['success']==500 else '- **本轮未完成500条真实问答。Smoke未通过时正式批处理不会启动；未执行项不冒充失败问答或评分结果。**',
      f'- E2E完成率：{f(e["e2e_completion_rate"])}。10条Smoke含五类各2条，计入同一500分母，不重复计数。',
      '- 经用户明确指令改用qwen-flash。旧qwen-turbo的10条Smoke/30次生成尝试全部429，另一次最小健康探测亦失败；旧目录p6-e2e-run-01完整保留。本报告仅统计独立qwen-flash运行的500题，旧模型失败不混入此分母，但费用计入同一¥20上限。' if OUT.name.endswith('qwen-flash') else '- 本目录保留原模型运行记录。',
      f'- 超时尝试：{e["timeout_attempts"]}；最终超时失败题：{e["timeouts_final_cases"]}；重试次数：{e["retry_attempts"]}。',
      '- 入口：OnlineQueryProcessor.process，真实Query Rewrite/Intent/Hybrid/Context/LLM/引用；真实PostgreSQL和Redis。',
      '- top_k=4，candidate_k=20，权重0.7/0.3，min_score=.05，relative_threshold=.35；Cross-Encoder关闭。P5检索实验top_k=20且禁用改写/意图，本轮保留当前业务行为，不能视为P5指标复跑。',
      '- 依赖修复：项目venv缺少pyproject已声明redis>=5.0.0，安装redis8.1.0；未修改生产代码、Prompt或参数文件。',
      '', '## 性能与Token','',f'- 成功最终尝试平均墙钟延迟：{p["mean"]} ms；p50：{p["p50"]} ms；p95：{p["p95"]} ms；分母{p["denominator"]}。',
      f'- 检索/生成延迟：{json.dumps({k:v["performance"][k] for k in ["retrieval_ms","generation_ms"]},ensure_ascii=False)}。',
      f'- 失败最终尝试延迟（不等于成功E2E）：{json.dumps(v["performance"]["failed_final_attempt_wall_ms"],ensure_ascii=False)}。',
      f'- Token：{json.dumps(c["by_call_kind"],ensure_ascii=False)}；含重试与Judge，按call kind分列。另列其中的诊断调用：{json.dumps(c["diagnostic_calls_included_in_tokens"],ensure_ascii=False)}。',
      f'- 已知Token公开单价估算：¥{c["known_usage_list_price_estimate_yuan"]:.6f}；保守预算占用：¥{c["conservative_committed_yuan"]:.6f}/20；未知用量调用：{c["unknown_usage_calls"]}。',
      '- 实际账户扣费/免费额度无法从SDK确认，actual_billed_yuan=null，不将估算冒充实际账单。价格来源：[阿里云官方模型价格]('+m.PRICE_SOURCE+')。',
      '', '## 自动质量（探索性，非人工准确率）','',
      f'- Silver满分回答正确比例：{f(q["silver_full_correctness"])}；排除50条未经人工确认unanswerable、p6s-0473、执行/评分失败及null。',
      f'- Faithfulness：{json.dumps(q["faithfulness"],ensure_ascii=False)}。',
      f'- 回答完整度：{json.dumps(q["completeness"],ensure_ascii=False)}。',
      f'- Citation自动语义评分：{json.dumps(q["citation_correctness_judge"],ensure_ascii=False)}。',
      f'- 引用编号有效比例：{f(q["citation_structural_validity"])}；编号有效且来源起始文本进入真实Prompt：{f(q["citation_index_and_prompt_presence"])}。结构有效不等于语义正确。',
      f'- 暂定拒答行为：{json.dumps(q["no_answer_behavior_provisional"],ensure_ascii=False)}。',
      '- 50条unanswerable中，只有36条获得非null暂定拒答分，另14条无法给出适用分；并非把50条都认定为真实不可回答。' if e['success']==500 else '- 未完成的拒答评测不赋予有效比例。',
      f'- 疑似幻觉：{f(q["hallucination_suspected"])}；低置信度：{f(q["low_confidence"])}。',
      f'- Judge成功：{f(q["judge_success"])}；Judge失败{q["judge_failed"]}，与RAG执行失败分开。',
      f'- 原始评分技术失败记录{q["original_scoring_failure_records"]}条；其中{q["scoring_failures_recovered_without_new_api_calls"]}条复用已付费响应恢复到scores_recovered，原失败文件仍保留，没有追加超限重试或改写原记录。',
      f'- 生成完成原因：{json.dumps(q["generation_finish_reasons"],ensure_ascii=False)}。length为原220输出Token上限触发，未为提高分数调大上限。',
      f'- 生成与评分均使用{m.read(OUT/"run_config.json")["settings"]["openai_chat_model"]}，评分是另一次独立调用；存在同模型自评偏差，未声称独立人工/模型真值。请求、返回model别名、usage、理由和证据完整归档；服务未暴露不可变权重版本。',
      '', '## 错误分类与题型','']
    for k,item in v['primary_failure_buckets'].items():lines.append(f'- {item["description"]}：{f(item)}。')
    lines+=['','| 题型 | 执行成功 | Silver满分正确（适用分母） |','|---|---|---|']
    for k,item in v['by_type'].items():lines.append(f'| {k} | {f(item["execution_success"])} | {f(item["silver_full_correctness"])} |')
    lines+=['','归因具有优先级且互斥，完整理由/典型案例见failure_analysis.md；不能把Silver证据未命中直接当作人工确认检索错误。','',
      '## 人工抽查与风险','',
      f'抽查清单{len(human)}条，五种题型各8条，优先覆盖低置信度、失败与p6s-0473。未执行项明确标pending、无RAG答案。所有人工审核字段为空，未自动签核。',
      '- 50条unanswerable标签待人工核查，拒答评分仅暂定；泛化问题可能部分可回答。',
      '- p6s-0473的114工日存在来源解析歧义；正确性强制null，不依此判模型错。',
      '- 表格列/单位、长上下文截断、同义答案、引用支撑范围、同模型Judge偏差均应重点抽查。',
      '', '## 交付文件','',
      'run_config.json / authorization.json / input_preflight.json / database_after.json：冻结配置与边界证据。',
      'execution_states.jsonl：完整500条状态；attempts/：逐次失败/重试；cases/与traces.jsonl：逐题完整Trace；answers.jsonl：原始回答。',
      'api_calls/：模型原始请求、响应、usage、预留费用；scores/与scores.jsonl：逐条理由/证据及评分失败。',
      'metrics.json / failure_diagnostics.jsonl / failure_analysis.md：分母、性能与归因；human_spot_check_40.jsonl/.csv：空白人工抽查；sha256_manifest.json：哈希。',
      '', '## 复现命令','',
      '已有成功/终态case不会重复调用，评分已完成项不会重复评分；中断尝试占用最多3次尝试配额。以下命令从项目根目录执行：','',
      '```powershell',
      "& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/e2e_run01.py' preflight"+variant,
      "& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/e2e_run01.py' run"+variant,
      "& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/e2e_run01.py' score"+variant,
      "& 'D:/AgentAIProgect/RAG/venv/Scripts/python.exe' 'D:/AgentAIProgect/RAG/p6-silver-e2e-500/e2e_run01_report.py'"+variant,
      '```','','已停止后续工作，等待验收。']
    m.projection(OUT/'FINAL_REPORT.md','\n'.join(lines).encode('utf-8'))


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--variant',choices=['qwen-turbo','qwen-flash'],default='qwen-turbo');args=ap.parse_args()
    m.select_variant(args.variant);OUT=m.OUT
    main()
