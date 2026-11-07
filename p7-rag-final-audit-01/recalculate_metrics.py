"""P7 offline audit. Standard library only; no legacy imports, API, DB, or history writes."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import itertools
import csv
import json
import math
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
RUN = ROOT / 'p6-silver-e2e-500/runs/p6-e2e-run-01-qwen-flash'
DIMENSIONS = ['answer_correctness', 'faithfulness', 'completeness', 'citation_correctness', 'no_answer_behavior']
TYPES = ['exact_fact', 'procedure', 'multi_condition', 'colloquial', 'unanswerable']
BUCKETS = ['1_retrieval_evidence_miss','2_context_evidence_miss','3_wrong_with_evidence',
           '4_incomplete','5_unsupported_generation','6_citation_mismatch','7_execution_failure',
           '8_judge_unreliable','pass_or_no_detected_failure']
READ_HASHES = {}


def read(path):
    data = path.read_bytes()
    READ_HASHES[str(path.relative_to(ROOT)).replace('\\','/')] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def readlines(path):
    data = path.read_bytes()
    READ_HASHES[str(path.relative_to(ROOT)).replace('\\','/')] = hashlib.sha256(data).hexdigest()
    return [json.loads(line) for line in data.decode('utf-8-sig').splitlines() if line.strip()]


def write(name, value):
    target = (OUT / name).resolve()
    assert target.is_relative_to(OUT)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def members(ids):
    values = sorted(set(ids))
    return {'count': len(values), 'case_ids': values}


def ratio(numerator_ids, denominator_ids):
    n, d = sorted(set(numerator_ids)), sorted(set(denominator_ids))
    assert set(n) <= set(d)
    return {'numerator':len(n), 'denominator':len(d), 'ratio':len(n)/len(d) if d else None,
            'numerator_case_ids':n, 'denominator_case_ids':d}


def percentile(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    pos = (len(xs)-1)*p
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi]-xs[lo])*(pos-lo)


def stats(pairs):
    pairs = [(cid, value) for cid, value in pairs if value is not None]
    vals = [v for _,v in pairs]
    return {'denominator':len(vals), 'denominator_case_ids':sorted(cid for cid,_ in pairs),
            'mean':sum(vals)/len(vals) if vals else None, 'p50':percentile(vals,.5),
            'p95':percentile(vals,.95), 'unit':'milliseconds',
            'percentile_method':'linear interpolation at (n-1)*p, zero-based order statistics'}


def norm(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def main():
    cases_list = readlines(ROOT/'p6-silver-e2e-500/silver_cases_500.jsonl')
    cases = {r['case_id']:r for r in cases_list}
    results = {p.stem:read(p) for p in sorted((RUN/'cases').glob('*.json'))}
    original = {p.stem:read(p) for p in sorted((RUN/'scores').glob('*.json'))}
    recovered = {p.stem:read(p) for p in sorted((RUN/'scores_recovered').glob('*.json'))}
    scores = original | recovered
    answers = readlines(RUN/'answers.jsonl')
    traces = readlines(RUN/'traces.jsonl')
    score_projection = readlines(RUN/'scores.jsonl')
    universe = set(cases)
    assert len(cases_list) == len(cases) == 500
    assert universe == set(results) == set(original) == {r['case_id'] for r in answers} == {r['case_id'] for r in traces}
    assert all(r['case_id'] == cid for cid,r in results.items())
    assert all(results[r['case_id']]['answer'] == r['answer'] for r in answers)
    assert all(results[r['case_id']] == r for r in traces)
    assert scores == {r['case_id']:r for r in score_projection}
    succeeded = {cid for cid,r in results.items() if r['state']=='success'}
    judged = {cid for cid,s in scores.items() if s['score_state']=='success'}
    failed = {cid for cid,s in scores.items() if s['score_state']=='failed'}
    def val(cid, field):
        return scores[cid].get(field,{}).get('score')
    def metric(field, pool=universe):
        ids = sorted(cid for cid in pool & judged if val(cid,field) is not None)
        values = [val(cid,field) for cid in ids]
        return {'denominator':len(ids), 'denominator_case_ids':ids, 'score_sum':sum(values),
                'mean':sum(values)/len(values) if values else None,
                'distribution':dict(Counter(str(v) for v in values)),
                'full_score_ratio':ratio([cid for cid in ids if val(cid,field)==1], ids),
                'null_success_case_ids':sorted(cid for cid in pool & judged if val(cid,field) is None),
                'judge_failure_case_ids':sorted(pool & failed)}
    exclusion = defaultdict(list)
    for cid in sorted(universe):
        if cases[cid]['question_type']=='unanswerable': reason='unanswerable_label_not_human_verified'
        elif cid=='p6s-0473': reason='reference_source_ambiguity'
        elif cid not in succeeded: reason='execution_not_success'
        elif cid not in judged: reason='judge_not_success'
        elif val(cid,'answer_correctness') is None: reason='correctness_null'
        elif scores[cid].get('correctness_excluded'): reason='other_explicit_exclusion'
        else: continue
        exclusion[reason].append(cid)
    excluded = set(itertools.chain.from_iterable(exclusion.values()))
    eligible = universe-excluded
    correct = {cid for cid in eligible if val(cid,'answer_correctness')==1}
    historical_eligible = {cid for cid in judged if not scores[cid].get('correctness_excluded') and val(cid,'answer_correctness') is not None}
    assert eligible == historical_eligible
    unanswerable = {cid for cid,c in cases.items() if c['question_type']=='unanswerable'}
    diags = {}
    for cid,c in cases.items():
        r,s = results[cid],scores[cid]
        refs = set(c.get('source_chunk_ids') or [])
        retrieved = {x['chunk']['id'] for call in r.get('retrieval_observation',[]) for x in call.get('results',[])}
        chats = [x for x in r.get('model_calls',[]) if x['kind']=='chat' and x.get('response')]
        prompt = '\n'.join(m.get('content','') for m in chats[-1]['request']['messages']) if chats else ''
        quotes = c.get('source_evidence') or []
        hits = [e['chunk_id'] for e in quotes if norm(e['excerpt']) in norm(prompt)]
        indices = [int(a or b) for a,b in re.findall(r'\[(\d+)\]|【(\d+)】',r.get('answer') or '')]
        sources = r.get('sources',[])
        invalid = [i for i in indices if not 1<=i<=len(sources)]
        context_valid = sum(1<=i<=len(sources) and norm(sources[i-1]['chunk']['text'])[:35] in norm(prompt) for i in indices)
        retrieved_all = refs<=retrieved if refs else None
        prompt_all = len(hits)==len(quotes) if quotes else None
        bad = val(cid,'answer_correctness') is not None and val(cid,'answer_correctness')<1
        uncertain_refusal = cid in unanswerable and val(cid,'no_answer_behavior') in [0,.5] and not s.get('hallucination_suspected') and val(cid,'faithfulness')!=0
        if cid not in succeeded: bucket='7_execution_failure'
        elif cid not in judged or s.get('confidence')=='low' or cid=='p6s-0473': bucket='8_judge_unreliable'
        elif uncertain_refusal: bucket='8_judge_unreliable'
        elif cid not in unanswerable and bad and not retrieved_all: bucket='1_retrieval_evidence_miss'
        elif cid not in unanswerable and bad and not prompt_all: bucket='2_context_evidence_miss'
        elif s.get('hallucination_suspected') or val(cid,'faithfulness')==0: bucket='5_unsupported_generation'
        elif (val(cid,'citation_correctness') is not None and val(cid,'citation_correctness')<1) or invalid: bucket='6_citation_mismatch'
        elif val(cid,'completeness') is not None and val(cid,'completeness')<1: bucket='4_incomplete'
        elif bad: bucket='3_wrong_with_evidence'
        else: bucket='pass_or_no_detected_failure'
        diags[cid] = {'case_id':cid,'question_type':c['question_type'],'primary_failure_bucket':bucket,
                      'citation_markers':indices,'invalid_citation_markers':invalid,
                      'citation_index_valid_count':len(indices)-len(invalid),
                      'citation_index_and_context_valid_count':context_valid,
                      'reference_all_retrieved':retrieved_all,'reference_all_quotes_in_actual_prompt':prompt_all,
                      'uncertain_refusal_rule':uncertain_refusal,
                      'score_state':s['score_state'],'correctness_eligible':cid in eligible,
                      'dimensions':{f:val(cid,f) for f in DIMENSIONS}}
    history_diags = {r['case_id']:r for r in readlines(RUN/'failure_diagnostics.jsonl')}
    assert all(diags[cid]['primary_failure_bucket']==history_diags[cid]['primary_failure_bucket'] for cid in universe)
    sets = {
        'hallucination_suspected':{cid for cid in judged if scores[cid].get('hallucination_suspected')},
        'invalid_citation_index':{cid for cid,d in diags.items() if d['invalid_citation_markers']},
        'citation_source_not_present_in_prompt':{cid for cid,d in diags.items() if d['citation_index_and_context_valid_count']<len(d['citation_markers'])},
        'scoring_failed':failed,
        'judge_unreliable':{cid for cid,d in diags.items() if d['primary_failure_bucket']=='8_judge_unreliable'},
        'low_confidence':{cid for cid in judged if scores[cid].get('confidence')=='low'},
        'ambiguous_reference':{'p6s-0473'},
        'unanswerable_all_labels_pending':unanswerable,
        'correctness_not_full':eligible-correct,
        'citation_semantic_score_below_one':{cid for cid in judged if val(cid,'citation_correctness') is not None and val(cid,'citation_correctness')<1},
        'completeness_below_one':{cid for cid in judged if val(cid,'completeness') is not None and val(cid,'completeness')<1},
        'faithfulness_below_one':{cid for cid in judged if val(cid,'faithfulness') is not None and val(cid,'faithfulness')<1},
    }
    selected=[]
    selection_reasons={}
    for cid in ['p6s-0473','p6s-0088']:
        selected.append(cid);selection_reasons[cid]='历史脚本显式强制入选'
    for kind in TYPES:
        pool=sorted((cid for cid in cases if cases[cid]['question_type']==kind),
                    key=lambda cid:(not scores[cid].get('needs_human_review',True),
                                    diags[cid]['primary_failure_bucket']=='pass_or_no_detected_failure',cid))
        for cid in pool:
            if sum(cases[x]['question_type']==kind for x in selected)>=8: break
            if cid not in selected:
                selected.append(cid)
                selection_reasons[cid]='每题型补足8条；按needs_human_review优先、非pass优先、case_id字典序'
    history_selection = readlines(RUN/'human_spot_check_40.jsonl')
    assert selected == [r['case_id'] for r in history_selection]
    history_metrics=read(RUN/'metrics.json')
    performance={'successful_attempt_wall_ms':stats([(cid,results[cid]['wall_seconds']*1000) for cid in sorted(succeeded)])}
    for label,field in [('production_trace_total_ms','latency_ms'),('retrieval_ms','retrieval_latency_ms'),
                        ('generation_ms','generation_latency_ms'),('rewrite_ms','rewrite_latency_ms'),
                        ('intent_ms','intent_latency_ms'),('embedding_ms','embedding_latency_ms'),
                        ('context_preprocessing_ms','context_latency_ms')]:
        performance[label]=stats([(cid,results[cid].get('trace',{}).get(field)) for cid in sorted(succeeded)])
    p5=read(ROOT/'p5-benchmark-01/four_group_results.json')
    p5_csv_path=ROOT/'p5-benchmark-01/metrics.csv'
    p5_csv_bytes=p5_csv_path.read_bytes()
    READ_HASHES[str(p5_csv_path.relative_to(ROOT)).replace('\\','/')]=hashlib.sha256(p5_csv_bytes).hexdigest()
    p5_rows=list(csv.DictReader(p5_csv_bytes.decode('utf-8-sig').splitlines()))
    p5_equal=all(int(row['denominator'])==28 and all(
        math.isclose(float(row[key]),value,rel_tol=1e-12,abs_tol=1e-12)
        for key,value in p5[row['run']][row['method']].items()) for row in p5_rows)
    assert len(p5_rows)==8 and p5_equal
    metrics = {
        'status':'AUDIT_PREPARED','human_review_status':'HUMAN_REVIEW_PENDING',
        'run_id':RUN.name,'scope':'历史Silver同模型自动评审离线复算；不是人工准确率、不是P5 Gold重测',
        'method':'独立标准库脚本；未导入/执行历史脚本；scores_recovered按case_id覆盖原始scores；所有历史源只读',
        'source_projection_consistency':{'cases_answers_equal':True,'cases_traces_equal':True,'merged_scores_projection_equal':True,
                                         'failure_buckets_equal':True,'historical_40_exact_order_equal':True},
        'execution':ratio(succeeded,universe),
        'judge_success':ratio(judged,succeeded),'judge_failed':members(failed),
        'original_score_failures':members(cid for cid,s in original.items() if s['score_state']=='failed'),
        'recovered_scores':members(recovered),
        'silver_full_correctness':ratio(correct,eligible),
        'correctness_exclusions':{'total':members(excluded),'mutually_exclusive_priority':[
            'unanswerable_label_not_human_verified','reference_source_ambiguity','execution_not_success',
            'judge_not_success','correctness_null','other_explicit_exclusion'],
            'reasons':{reason:members(ids) for reason,ids in exclusion.items()}},
        'faithfulness':metric('faithfulness'),'completeness':metric('completeness'),
        'citation_correctness_judge':metric('citation_correctness'),
        'no_answer_behavior_provisional':metric('no_answer_behavior',unanswerable),
        'hallucination_suspected':ratio(sets['hallucination_suspected'],judged),
        'invalid_citation_cases':ratio(sets['invalid_citation_index'],universe),
        'citation_markers':{'total':sum(len(d['citation_markers']) for d in diags.values()),
                            'valid_index':sum(d['citation_index_valid_count'] for d in diags.values()),
                            'valid_index_and_prompt_prefix':sum(d['citation_index_and_context_valid_count'] for d in diags.values()),
                            'invalid_occurrences_by_case':{cid:diags[cid]['invalid_citation_markers'] for cid in sorted(sets['invalid_citation_index'])}},
        'judge_uncertainty':members(sets['judge_unreliable']),
        'judge_uncertainty_exclusive_components':{
            'judge_failure':members(failed),
            'low_confidence_after_failures':members(sets['low_confidence']-failed),
            'reference_ambiguity_after_above':members({'p6s-0473'}-failed-sets['low_confidence']),
            'unanswerable_rule_after_above':members(sets['judge_unreliable']-failed-sets['low_confidence']-{'p6s-0473'})},
        'primary_failure_buckets':{b:members(cid for cid,d in diags.items() if d['primary_failure_bucket']==b) for b in BUCKETS},
        'error_sets':{name:members(ids) for name,ids in sets.items()},
        'error_pairwise_overlap':{a+' AND '+b:members(sets[a]&sets[b]) for a,b in itertools.combinations(sets,2)},
        'risk_union_excluding_generic_dimension_scores':members(set.union(*(sets[k] for k in [
            'hallucination_suspected','invalid_citation_index','scoring_failed','low_confidence','ambiguous_reference','unanswerable_all_labels_pending']))),
        'by_type':{kind:{'case_count':sum(c['question_type']==kind for c in cases.values()),
                        'silver_full_correctness':ratio({cid for cid in correct if cases[cid]['question_type']==kind},
                                                       {cid for cid in eligible if cases[cid]['question_type']==kind})} for kind in TYPES},
        'performance':performance,
        'p5_readonly_crosscheck':{'scope':'只读取已有汇总并核对JSON/CSV一致；未执行检索、未重算或改写P5结果',
            'json_csv_equal':p5_equal,'row_count':len(p5_rows),'denominator_per_row':28,'historical_values':p5},
        'historical_spot_check_40':{'selection':'deterministic stratified risk-prioritized; not random and not a statistical accuracy sample',
            'case_ids_in_historical_order':selected,'per_type':dict(Counter(cases[cid]['question_type'] for cid in selected)),
            'selection_reasons':selection_reasons,
            'risk_sets_coverage':{name:{'selected':members(ids&set(selected)),'not_selected':members(ids-set(selected))} for name,ids in sets.items()},
            'all_human_fields_blank':all(not r.get(f) for r in history_selection for f in ['human_reviewer','human_decision','human_notes','human_reviewed_at'])},
        'per_case_audit':list(diags.values()),
    }
    checks={
        'execution_500':len(succeeded)==500,'judge_490':len(judged)==490,'correct_423_439':(len(correct),len(eligible))==(423,439),
        'excluded_61':len(excluded)==61,'faithfulness_489':metrics['faithfulness']['denominator']==489,
        'completeness_488':metrics['completeness']['denominator']==488,'hallucination_18':len(sets['hallucination_suspected'])==18,
        'invalid_citation_6':len(sets['invalid_citation_index'])==6,'judge_unreliable_20':len(sets['judge_unreliable'])==20,
        'multi_89_95':(metrics['by_type']['multi_condition']['silver_full_correctness']['numerator'],metrics['by_type']['multi_condition']['silver_full_correctness']['denominator'])==(89,95),
        'refusal_27_36':(metrics['no_answer_behavior_provisional']['full_score_ratio']['numerator'],metrics['no_answer_behavior_provisional']['denominator'])==(27,36),
    }
    for label,item in performance.items():
        checks['historical_latency_'+label]=all(math.isclose(item[k],history_metrics['performance'][label][k],rel_tol=1e-12,abs_tol=1e-9) for k in ['mean','p50','p95'])
    assert all(checks.values()), checks
    metrics['verification_checks']=checks
    write('metrics_recalculation.json',metrics)
    failure_audit(cases,results,original,scores,failed)
    # Only hash reading is performed for the legacy calculation/validation sources.
    for path in [ROOT/'p6-silver-e2e-500/e2e_run01.py',ROOT/'p6-silver-e2e-500/e2e_run01_report.py']:
        READ_HASHES[str(path.relative_to(ROOT)).replace('\\','/')]=hashlib.sha256(path.read_bytes()).hexdigest()
    write('metrics_source_hashes.json',READ_HASHES)
    print(json.dumps({'checks':checks,'sets':{k:v['count'] for k,v in metrics['error_sets'].items()},
                      'risk_union':metrics['risk_union_excluding_generic_dimension_scores']['count']},ensure_ascii=False,indent=2))


def failure_audit(cases, results, original, scores, failed):
    annotations={
        'p6s-0023':('格式错误','三次均finish_reason=length，JSON字符串未闭合；输出达到1600 token上限。'),
        'p6s-0037':('证据不足','三次JSON可解析，但Judge因不存在的[6]引用将正确性设null；与普通题必填分数校验冲突。其理由同时承认[1]有相关事实，证据不足是Judge判断，不是人工事实裁决。'),
        'p6s-0041':('格式错误','前两次length截断JSON；第三次只有请求、没有持久响应，追加标记调用证据缺失/中断，不据此断言网络或服务端故障。'),
        'p6s-0053':('评分逻辑问题','三次正确性null；第三次理由直接错引p6s-0473工日歧义，前两次声称本题利润歧义但未给证据。'),
        'p6s-0157':('评分逻辑问题','三次正确性null；后两次将114工日歧义写到p6s-0157。疑似全局0473例外提示串扰，不能当作本题已证实歧义。'),
        'p6s-0195':('证据不足','三次正确性null；一次明确称实际上下文未支持交互式网络电视处理步骤；另两次混入工日/参考不一致措辞，兼有评分逻辑可疑。'),
        'p6s-0230':('证据不足','三次正确性null，理由均指上下文未定义或未提及综合单价构成；普通题null触发校验失败。'),
        'p6s-0389':('证据不足','三次正确性null，理由均指上下文未提树叶遮挡处理；普通题null触发校验失败。'),
        'p6s-0420':('评分逻辑问题','前两次将p6s-0473工日歧义用于本题且正确性null；第三次正确性有值但no_answer_behavior.reason空字符串，触发字段校验失败，兼有格式错误。'),
        'p6s-0454':('评分逻辑问题','前两次将p6s-0473歧义用于本题；第三次说明本题数据一致但线缆连接判断错误却仍给正确性null。'),
    }
    requests=defaultdict(list)
    for p in sorted((RUN/'api_calls').glob('*.request.json')):
        req=read(p)
        if req['kind']=='judge' and req.get('metadata',{}).get('case_id') in failed:
            requests[req['metadata']['case_id']].append((p,req))
    output=[]
    for cid in sorted(failed):
        attempts=[]
        for path,req in sorted(requests[cid],key=lambda pair:pair[1]['metadata']['attempt']):
            rp=path.with_name(path.name.replace('.request.','.response.'))
            response=read(rp) if rp.exists() else None
            raw=(response or {}).get('response')
            choice=(raw or {}).get('choices',[None])[0]
            text=choice['message']['content'] if choice else None
            parsed=None;parse_error=None;validation=[]
            if text is not None:
                try: parsed=json.loads(text)
                except json.JSONDecodeError as exc: parse_error={'type':type(exc).__name__,'message':str(exc)}
            if isinstance(parsed,dict):
                for field in DIMENSIONS:
                    item=parsed.get(field)
                    if not isinstance(item,dict): validation.append({'field':field,'error':'judge field missing'});continue
                    evidence=item.get('evidence')
                    if field=='no_answer_behavior' and item.get('score') is None and evidence is None: evidence=''
                    if 'score' not in item or not item.get('reason') or not isinstance(evidence,str):
                        validation.append({'field':field,'error':'judge field missing'})
                    if field!='no_answer_behavior' and item.get('score') is None:
                        validation.append({'field':field,'error':'judge required score missing'})
            attempts.append({'attempt':req['metadata']['attempt'],'api_call_id':req['request_id'],
                'request_file':str(path.relative_to(ROOT)).replace('\\','/'),
                'request_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'response_file':str(rp.relative_to(ROOT)).replace('\\','/'),
                'response_exists':rp.exists(),'response_sha256':hashlib.sha256(rp.read_bytes()).hexdigest() if rp.exists() else None,
                'request_max_tokens':req['request'].get('max_tokens'),
                'request_instruction_before_payload':req['request']['messages'][-1]['content'].split('\n{',1)[0],
                'finish_reason':choice.get('finish_reason') if choice else None,
                'response_error':(response or {}).get('error'),
                'usage':(raw or {}).get('usage'),'raw_content_exact':text,'parsed_json':parsed,
                'json_parse_error':parse_error,'independent_validation_errors':validation,
                'missing_response_interpretation':'interrupted_request_without_durable_response; transport/root cause unknown' if not rp.exists() else None})
        category,reason=annotations[cid]
        output.append({'case_id':cid,'question':cases[cid]['question'],'question_type':cases[cid]['question_type'],
                       'execution_state':results[cid]['state'],'score_state':scores[cid]['score_state'],
                       'original_failure_record_exact':original[cid],'primary_attribution':category,
                       'attribution_note':reason,'attribution_status':'AI_PRELIMINARY_NOT_HUMAN_SIGNOFF',
                       'human_review_status':'HUMAN_REVIEW_PENDING','attempts':attempts})
    write('score_failure_evidence.json',{'status':'AUDIT_PREPARED','human_review_status':'HUMAN_REVIEW_PENDING',
                                       'categories':dict(Counter(x['primary_attribution'] for x in output)),
                                       'cases':output})


if __name__ == '__main__':
    main()
