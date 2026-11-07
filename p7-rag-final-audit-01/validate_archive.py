"""Offline P7 acceptance checks; never imports the RAG runner or changes sources."""
from pathlib import Path
import ast
import csv
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
HUMAN = ['human_final_conclusion','human_notes','human_reviewer','human_review_date','human_signature']


def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def csv_read(name):
    with (OUT/name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    checks = {}
    details = {}
    required = ['README.md','integrity_check.json','audit_case_inventory.csv','audit_case_evidence.md','unanswerable_review_packet.md','citation_audit.md','score_failure_analysis.md','metrics_recalculation.json','metrics_definition.md','human_signoff_template.csv','resume_verified_facts.md','interview_materials.md','P7_FINAL_REPORT.md']
    checks['all_13_required_files_exist_nonempty'] = all((OUT/x).is_file() and (OUT/x).stat().st_size for x in required)
    baseline = read(OUT/'source_hashes_before.json')
    changed = [name for name,digest in baseline.items() if not (ROOT/name).is_file() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
    details['historical_files_compared'] = len(baseline)
    details['changed_or_missing_historical_files'] = changed
    checks['historical_sources_unchanged'] = not changed
    p5p6new = [p.relative_to(ROOT).as_posix() for folder in ['p5-benchmark-01','p6-silver-e2e-500'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.relative_to(ROOT).as_posix() not in baseline]
    details['new_files_in_p5_p6'] = p5p6new
    checks['no_new_p5_p6_files'] = not p5p6new
    i = read(OUT/'integrity_check.json')
    checks['silver500_unique_expected_hash'] = i['silver_count']==i['unique_case_ids']==500 and i['silver_sha256_matches']
    checks['exact_type_counts'] = i['question_type_counts']=={'exact_fact':200,'procedure':100,'multi_condition':100,'colloquial':50,'unanswerable':50}
    checks['frozen_corpus447_protected_hashes'] = i['corpus_count']==447 and all(x['matches'] for x in i['protected_historical_hash_checks'].values())
    checks['500_actual_responses_match'] = i['execution_success_count']==500 and i['all_requested_returned_models_qwen_flash'] and i['results_case_id_equal_dataset'] and i['filename_case_id_match']
    checks['score490_failed10_recovered8'] = i['score_success_count']==490 and i['score_failure_count']==10 and i['raw_score_failure_count']==18 and i['recovered_paid_response_count']==8
    checks['all_three_projections_exact'] = all(x['count']==x['unique']==500 and not any(x[k] for k in ['unknown_ids','missing_ids','mismatch_ids']) for x in i['projection_checks'].values())
    sel = read(OUT/'review_selection.json')
    pending = set(sel['expanded_pending_ids'])
    signoff = csv_read('human_signoff_template.csv')
    inventory = csv_read('audit_case_inventory.csv')
    checks['inventory500_unique'] = len(inventory)==len({x['case_id'] for x in inventory})==500
    checks['required82_expanded94_unique'] = sel['minimum_required_union_count']==82 and len(pending)==len(signoff)==94 and {x['case_id'] for x in signoff}==pending
    checks['required_sets_covered'] = all(set(v['case_ids'])<=pending for v in sel['sets'].values())
    checks['all50_unanswerable_in_signoff'] = len([x for x in signoff if x['question_type']=='unanswerable'])==50
    checks['human_fields_entirely_blank'] = all(x[k]=='' for x in signoff for k in HUMAN)
    checks['every_pending_case_has_md_json_index'] = all((OUT/'cases'/(cid+'.md')).is_file() and (OUT/'cases'/(cid+'.json')).is_file() for cid in pending)
    casecards = [read(OUT/'cases'/(cid+'.json')) for cid in sorted(pending)]
    checks['casecard_human_fields_entirely_blank'] = all(x[k]=='' for x in casecards for k in HUMAN)
    checks['casecard_required_evidence_populated'] = all(x['original_question'] and x['rag_actual_answer'] and x['sources'] and x['automatic_score'] and x['actual_chat_messages'] and x['ai_preliminary_recommendation'] and Path(x['original_trace_path']).is_file() and Path(x['original_score_path']).is_file() for x in casecards)
    checks['retrieved_casecard_text_matches_frozen'] = all(s['frozen_chunk_found'] and s['text_matches_frozen'] for x in casecards for s in x['sources'])
    m = read(OUT/'metrics_recalculation.json')
    checks['independent_metric_checks_all_true'] = all(m['verification_checks'].values())
    details['metric_checks'] = m['verification_checks']
    checks['metric_case_membership_no_denominator_leak'] = set(m['silver_full_correctness']['numerator_case_ids'])<=set(m['silver_full_correctness']['denominator_case_ids']) and len(set(m['silver_full_correctness']['denominator_case_ids']))==439
    failures = read(OUT/'score_failure_evidence.json')['cases']
    checks['ten_failure_attributions_and_raw_attempts'] = len(failures)==10 and all(x['primary_attribution'] and x['attribution_note'] and x['attempts'] for x in failures)
    ftext=(OUT/'score_failure_analysis.md').read_text(encoding='utf-8') if (OUT/'score_failure_analysis.md').exists() else ''
    checks['ten_failure_ids_documented'] = all(x['case_id'] in ftext for x in failures)
    ctext=(OUT/'citation_audit.md').read_text(encoding='utf-8') if (OUT/'citation_audit.md').exists() else ''
    checks['six_invalid_citation_ids_documented'] = all(cid in ctext for cid in sel['sets']['invalid_citation']['case_ids'])
    htext=(OUT/'hallucination_audit.md').read_text(encoding='utf-8') if (OUT/'hallucination_audit.md').exists() else ''
    checks['eighteen_hallucination_ids_documented'] = all(cid in htext for cid in sel['sets']['hallucination_suspected']['case_ids'])
    utext=(OUT/'unanswerable_review_packet.md').read_text(encoding='utf-8') if (OUT/'unanswerable_review_packet.md').exists() else ''
    checks['fifty_unanswerable_ids_documented'] = all(cid in utext for cid in sel['sets']['unanswerable']['case_ids'])
    checks['0473_pdf_report_and_render_exist'] = (OUT/'p6s-0473_pdf_audit.md').is_file() and (OUT/'pdf_pages/p6s-0473-324.png').is_file()
    resume=(OUT/'resume_verified_facts.md').read_text(encoding='utf-8').split('## 简历精简版（100–150字）')[1].strip().split('\n\n')[0]
    details['resume_unicode_character_count']=len(resume)
    checks['resume_100_to_150_characters'] = 100<=len(resume)<=150
    syntax_errors=[]
    for p in OUT.glob('*.py'):
        try: ast.parse(p.read_text(encoding='utf-8-sig'),filename=p.name)
        except SyntaxError as e: syntax_errors.append(str(e))
    details['python_syntax_errors']=syntax_errors
    checks['p7_analysis_script_syntax'] = not syntax_errors
    status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True,encoding='utf-8')
    (OUT/'git_status_after.txt').write_text(status,encoding='utf-8')
    before=(OUT/'git_status_before.txt').read_text(encoding='utf-8')
    checks['git_status_unchanged_outside_p7'] = [x for x in status.splitlines() if 'p7-rag-final-audit-01' not in x]==[x for x in before.splitlines() if 'p7-rag-final-audit-01' not in x]
    checks['no_new_model_run_declared'] = i['new_model_requests']==0 and not i['p5_holdout_executed'] and not p5p6new
    result={'status':'passed' if all(checks.values()) else 'failed','archive_status':'AUDIT_PREPARED / HUMAN_REVIEW_PENDING','passed_count':sum(bool(x) for x in checks.values()),'check_count':len(checks),'checks':checks,'details':details,'scope':'offline static acceptance only; no application integration test, no model request, no human signoff'}
    (OUT/'static_validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'passed':result['passed_count'],'total':result['check_count'],'failed':[k for k,v in checks.items() if not v]},ensure_ascii=False))
    if not all(checks.values()): raise SystemExit(1)
    manifest={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json' and '__pycache__' not in p.parts}
    (OUT/'sha256_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
