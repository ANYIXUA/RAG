"""Read-only historical evidence projection. Standard library, no model/network calls."""
from pathlib import Path
import collections
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
RUN = ROOT / 'p6-silver-e2e-500/runs/p6-e2e-run-01-qwen-flash'
CORPUS = ROOT / 'storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl'
EXPECTED = '03f7955b144e31081c778f533322ff68b560459f60ab94bb9699b2ea7a35c410'
HUMAN = ['human_final_conclusion', 'human_notes', 'human_reviewer', 'human_review_date', 'human_signature']


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def rows(p):
    return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]


def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def csv_write(name, records):
    with (OUT/name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    silver = rows(ROOT/'p6-silver-e2e-500/silver_cases_500.jsonl')
    cases = {x['case_id']: x for x in silver}
    results = {p.stem: read(p) for p in sorted((RUN/'cases').glob('*.json'))}
    scores = {p.stem: read(p) for p in sorted((RUN/'scores').glob('*.json'))}
    recovered = {p.stem: read(p) for p in sorted((RUN/'scores_recovered').glob('*.json'))}
    scores.update(recovered)
    diagnostics = {x['case_id']: x for x in rows(RUN/'failure_diagnostics.jsonl')}
    corpus = {x['chunk_id']: x for x in rows(CORPUS)}
    historical40 = {x['case_id'] for x in rows(RUN/'human_spot_check_40.jsonl')}
    groups = {
        'historical_spot_check_40': historical40,
        'unanswerable': {cid for cid,c in cases.items() if c['question_type']=='unanswerable'},
        'p6s_0473': {'p6s-0473'},
        'score_failure': {cid for cid,s in scores.items() if s.get('score_state')!='success'},
        'invalid_citation': {cid for cid,r in results.items() if any(not 1 <= int(a or b) <= len(r['sources']) for a,b in re.findall(r'\[(\d+)\]|【(\d+)】',r['answer']))},
        'hallucination_suspected': {cid for cid,s in scores.items() if s.get('score_state')=='success' and s.get('hallucination_suspected')},
        'retrieval_evidence_miss': {cid for cid,d in diagnostics.items() if d['primary_failure_bucket']=='1_retrieval_evidence_miss'},
        'context_evidence_miss': {cid for cid,d in diagnostics.items() if d['primary_failure_bucket']=='2_context_evidence_miss'},
        'judge_unreliable': {cid for cid,d in diagnostics.items() if d['primary_failure_bucket']=='8_judge_unreliable'},
        'multi_condition_nonfull_or_unscored': {cid for cid,c in cases.items() if c['question_type']=='multi_condition' and (scores[cid].get('score_state')!='success' or any(scores[cid].get(f,{}).get('score')!=1 for f in ['answer_correctness','faithfulness','completeness','citation_correctness']))},
    }
    mandatory = set.union(*(groups[k] for k in list(groups)[:5]))
    pending = set.union(*groups.values())
    save('review_selection.json', {'status':'AUDIT_PREPARED / HUMAN_REVIEW_PENDING','historical_list_recovered':False,'historical_list_found':True,'historical_list_path':str(RUN/'human_spot_check_40.jsonl'),'minimum_required_union_count':len(mandatory),'minimum_required_ids':sorted(mandatory),'expanded_pending_count':len(pending),'expanded_pending_ids':sorted(pending),'additional_ids':sorted(pending-mandatory),'sets':{k:{'count':len(v),'case_ids':sorted(v)} for k,v in groups.items()},'pairwise_intersections':{a+' & '+b:sorted(groups[a]&groups[b]) for i,a in enumerate(groups) for b in list(groups)[i+1:] if groups[a]&groups[b]}})
    findings = read(OUT/'case_ai_findings.json') if (OUT/'case_ai_findings.json').exists() else {}
    noanswer = read(OUT/'unanswerable_findings.json') if (OUT/'unanswerable_findings.json').exists() else {}
    noanswer_by_id = {x['case_id']:x for x in noanswer.get('records',[])}
    # Preserve independently authored findings verbatim, without manufacturing human verdicts.
    inventory, signoff, index = [], [], []
    evidence_dir=OUT/'cases';evidence_dir.mkdir(exist_ok=True)
    for cid,c in sorted(cases.items()):
        r,s,d=results[cid],scores[cid],diagnostics[cid]
        reasons=[k for k,v in groups.items() if cid in v]
        source_path=RUN/('scores_recovered' if cid in recovered else 'scores')/(cid+'.json')
        base={'case_id':cid,'question_type':c['question_type'],'review_required':cid in pending,'selection_reasons':';'.join(reasons),'question':c['question'],'reference_answer_or_expected_refusal':c['reference_answer'],'expected_behavior':c['expected_behavior'],'execution_state':r['state'],'score_state':s['score_state'],'historical_primary_failure_bucket':d['primary_failure_bucket'],'evidence_index':f'cases/{cid}.md' if cid in pending else str(RUN/'cases'/(cid+'.json'))}
        inventory.append(base)
        if cid not in pending:
            continue
        suggestions=[]
        if c['question_type']=='unanswerable': suggestions.append('Needs Verification（AI建议）：核对完整冻结语料和问题边界；当前检索未命中不构成无答案证明。见 unanswerable_review_packet.md 对应case。')
        if cid=='p6s-0473': suggestions.append('Needs Verification（AI建议）：原PDF表格数值、单位及算术一致性待人工裁决，见 p6s-0473_pdf_audit.md。')
        if cid in groups['score_failure']: suggestions.append('Needs Verification（AI建议）：自动评分失败不代表回答错误；见 score_failure_analysis.md 逐attempt归因。')
        if cid in groups['invalid_citation']: suggestions.append('Revise（AI建议）：存在越界引用编号；来源语义支撑仍需人工逐句核查。')
        if cid in groups['hallucination_suspected']: suggestions.append('Needs Verification（AI建议）：历史Judge标疑似幻觉，不是人工确认；见 hallucination_audit.md。')
        if cid in groups['retrieval_evidence_miss'] or cid in groups['context_evidence_miss']: suggestions.append('Needs Verification（AI建议）：Silver参考证据代理诊断需检查候选、上下文和替代证据，见 retrieval_context_audit.md。')
        if cid in groups['multi_condition_nonfull_or_unscored']: suggestions.append('Needs Verification（AI建议）：核对每项条件、数值单位及来源，见 multi_condition_audit.md。')
        if not suggestions: suggestions.append('Needs Verification（AI建议）：历史定向抽查样本；自动高分不能替代逐项核对。')
        finding = findings.get(cid,{})
        if finding:
            suggestions += [f'逐题AI分类：{finding["ai_suggested_classification"]}。', f'逐题AI证据判断：{finding["ai_suggestion"]}', f'待人工原因：{finding["human_review_reason"]}']
        if cid in noanswer_by_id:
            u=noanswer_by_id[cid]
            suggestions += [f'无答案标签AI建议：{u["ai_proposed_label_action"]}；{u["ai_preliminary_conclusion"]}',f'歧义与缺失信息：{u["ambiguity_and_missing_information"]}',f'当前回答核查：{u["current_answer_audit"]}']
        chunks=[]
        for rank,x in enumerate(r['sources'],1):
            chunk=x['chunk'];meta=chunk['metadata'];frozen=corpus.get(chunk['id'])
            chunks.append({'source_number':rank,'chunk_id':chunk['id'],'document':meta.get('filename',meta.get('source')),'physical_page':meta.get('page_number'),'text':chunk['text'],'frozen_chunk_found':frozen is not None,'text_matches_frozen':bool(frozen and frozen['chunk_text']==chunk['text'])})
        chats=[x for x in r['model_calls'] if x['kind']=='chat']
        reference=[{'annotation':x,'frozen_chunk':corpus.get(x['chunk_id'])} for x in c.get('source_evidence',[])]
        ev={'case_id':cid,'question_type':c['question_type'],'selection_reasons':reasons,'original_question':c['question'],'silver_reference':c['reference_answer'],'expected_behavior':c['expected_behavior'],'rag_actual_answer':r['answer'],'sources':chunks,'reference_evidence':reference,'actual_citations':[int(a or b) for a,b in re.findall(r'\[(\d+)\]|【(\d+)】',r['answer'])],'automatic_score':s,'ai_preliminary_recommendation':suggestions,'anomaly_findings':findings.get(cid) if isinstance(findings,dict) else None,'unanswerable_findings':noanswer_by_id.get(cid),'original_trace_path':str(RUN/'cases'/(cid+'.json')),'original_score_path':str(source_path),'actual_chat_messages':chats[-1]['request']['messages'] if chats else [],**{k:'' for k in HUMAN}}
        save(f'cases/{cid}.json',ev)
        lines=[f'# {cid}｜{c["question_type"]}','', '状态：AUDIT_PREPARED / HUMAN_REVIEW_PENDING','',f'纳入原因：{", ".join(reasons)}','', '## 问题与回答','',f'原始问题：{c["question"]}','',f'Silver参考答案/预期拒答：{c["reference_answer"]}；expected_behavior={c["expected_behavior"]}。Silver标签尚非人工真值。','', 'RAG实际回答：','',r['answer'],'',f'实际引用序列：{ev["actual_citations"]}','', '## 原始证据与检索来源','']
        for x in chunks:
            lines += [f'### [{x["source_number"]}] {x["document"]}｜PDF物理页{x["physical_page"]}｜{x["chunk_id"]}','',f'冻结正文一致：{x["text_matches_frozen"]}','',x['text'],'']
        lines += ['### Silver标注证据（可能有标注偏差）','',json.dumps(c.get('source_evidence',[]),ensure_ascii=False,indent=2),'','## 自动评分（历史原值）','','```json',json.dumps(s,ensure_ascii=False,indent=2),'```','','## AI初步建议','',*['- '+x for x in suggestions],'','专项审计中的AI判断优先供人工核验；任何建议均未填写到人工结论。','',f'- [原始Trace]({(RUN/"cases"/(cid+".json")).as_posix()})',f'- [原始Score]({source_path.as_posix()})',f'- [完整结构化卡片与实际LLM请求]({cid}.json)','','## 人工签核','','允许结论：Accept / Revise / Reject / Needs Verification。以下字段留空。','','| 字段 | 人工填写 |','|---|---|',*[f'| {k} | |' for k in HUMAN],'']
        (evidence_dir/(cid+'.md')).write_text('\n'.join(lines),encoding='utf-8')
        signoff.append({'case_id':cid,'question_type':c['question_type'],'selection_reasons':';'.join(reasons),'original_question':c['question'],'reference_answer_or_expected_refusal':c['reference_answer'],'rag_actual_answer':r['answer'],'retrieved_chunk_ids':';'.join(x['chunk_id'] for x in chunks),'documents_and_physical_pages':';'.join(f'{x["document"]}:PDF{x["physical_page"]}' for x in chunks),'original_evidence':json.dumps(c.get('source_evidence'),ensure_ascii=False),'actual_citations':json.dumps(ev['actual_citations']),'automatic_score':json.dumps(s,ensure_ascii=False),'ai_preliminary_recommendation':'\n'.join(suggestions),'evidence_index':f'cases/{cid}.md',**{k:'' for k in HUMAN}})
        index.append(f'| [{cid}](cases/{cid}.md) | {c["question_type"]} | {", ".join(reasons)} |')
    csv_write('audit_case_inventory.csv',inventory)
    csv_write('human_signoff_template.csv',signoff)
    (OUT/'audit_case_evidence.md').write_text('\n'.join(['# P7逐题证据索引','','状态：AUDIT_PREPARED / HUMAN_REVIEW_PENDING。','',f'历史40条原清单已找到；任务指定集合去重后{len(mandatory)}条。为完整覆盖18条疑似幻觉、7条检索代理异常、1条上下文异常、20条评分不可靠与多条件非满分/失败案例，扩展后共{len(pending)}条待人工裁决。','', '每张卡片含原题、Silver参考或预期拒答、实际回答、全部返回来源编号及Chunk/文档/PDF物理页/完整正文、实际引用、原始评分与理由、AI建议、空白人工结论/备注/审核人/日期/签名；同名JSON还保存实际LLM请求与冻结参考全文。','', '人工签核唯一登记入口为 human_signoff_template.csv。多处空白模板仅为阅读便利，正式审核后应指定一个版本为准。', '', '| case_id | 题型 | 纳入原因 |','|---|---|---|',*index,'']),encoding='utf-8')
    protected=read(RUN/'protected_inputs_after.json')
    protected_checks={p:{'expected':v['expected'],'actual':sha(Path(p)),'matches':sha(Path(p))==v['expected']} for p,v in protected.items()}
    projection_checks={}
    for filename,expected_records in [('answers.jsonl',results),('traces.jsonl',results),('scores.jsonl',scores)]:
        projected=rows(RUN/filename);ids=[x['case_id'] for x in projected]
        mismatches=[x['case_id'] for x in projected if (x!=expected_records[x['case_id']] if filename!='answers.jsonl' else x['answer']!=expected_records[x['case_id']]['answer'] or x['sources']!=expected_records[x['case_id']]['sources'])]
        projection_checks[filename]={'count':len(ids),'unique':len(set(ids)),'unknown_ids':sorted(set(ids)-set(cases)),'missing_ids':sorted(set(cases)-set(ids)),'mismatch_ids':mismatches}
    chat_checks=[]
    for cid,r in results.items():
        calls=[x for x in r['model_calls'] if x['kind']=='chat' and x.get('response')]
        chat_checks.append({'case_id':cid,'state_success':r['state']=='success','nonempty_answer':bool(r['answer'].strip()),'raw_response_matches_answer':bool(calls and calls[-1]['response']['choices'][0]['message']['content']==r['answer']),'requested_model':calls[-1]['request']['model'] if calls else None,'returned_model':calls[-1]['response']['model'] if calls else None,'finish_reason':calls[-1]['response']['choices'][0]['finish_reason'] if calls else None,'request_id':r['trace'].get('request_id')})
    save('execution_response_checks.json',chat_checks)
    integrity={'status':'AUDIT_PREPARED / HUMAN_REVIEW_PENDING','silver_count':len(silver),'unique_case_ids':len(cases),'question_type_counts':dict(collections.Counter(x['question_type'] for x in silver)),'silver_sha256':sha(ROOT/'p6-silver-e2e-500/silver_cases_500.jsonl'),'expected_silver_sha256':EXPECTED,'silver_sha256_matches':sha(ROOT/'p6-silver-e2e-500/silver_cases_500.jsonl')==EXPECTED,'result_count':len(results),'results_case_id_equal_dataset':set(results)==set(cases),'filename_case_id_match':all(cid==r['case_id'] for cid,r in results.items()),'execution_success_count':sum(x['state_success'] and x['nonempty_answer'] and x['raw_response_matches_answer'] for x in chat_checks),'all_requested_returned_models_qwen_flash':all(x['requested_model']=='qwen-flash' and x['returned_model']=='qwen-flash' for x in chat_checks),'score_success_count':sum(s['score_state']=='success' for s in scores.values()),'score_failure_count':len(groups['score_failure']),'raw_score_failure_count':sum(read(p).get('score_state')!='success' for p in (RUN/'scores').glob('*.json')),'recovered_paid_response_count':len(recovered),'historical40_count':len(historical40),'minimum_required_review_count':len(mandatory),'expanded_review_count':len(pending),'all_human_fields_blank':all(not x[k] for x in signoff for k in HUMAN),'corpus_count':len(corpus),'protected_historical_hash_checks':protected_checks,'projection_checks':projection_checks,'run_provenance_files':[str(RUN/f) for f in ['run_config.json','runtime_environment.json','effective_settings_redacted.json','measurement_protocol.json','authorization.json']],'historical_preservation_verification':'source_hashes_before.json compared by validate_archive.py; see static_validation.json','new_model_requests':0,'p5_holdout_executed':False}
    save('integrity_check.json',integrity)
    print(json.dumps({'pending':len(pending),'minimum_required':len(mandatory),'sets':{k:len(v) for k,v in groups.items()},'execution_confirmed':integrity['execution_success_count'],'projection_mismatches':{k:v['mismatch_ids'] for k,v in projection_checks.items()}},ensure_ascii=False))


if __name__ == '__main__':
    main()
