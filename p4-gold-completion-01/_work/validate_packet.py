import json, hashlib, re, sys, collections
from pathlib import Path
from urllib.parse import unquote
from openpyxl import load_workbook
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'p4-gold-completion-01'
BASE=ROOT/'storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(t):return re.sub(r'\s+','',t)
checks=[]
def check(name,ok,details=None):
    checks.append({'check':name,'passed':bool(ok),'details':details})
    if not ok: print('FAIL',name,details)
before=read(OUT/'_work/input_hashes_before.json')
changed=[p for p,h in before.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
check('protected_files_unchanged',not changed,{'files_checked':len(before),'changed':changed})
cfg=read(ROOT/'p3-pilot-01/pilot_config.json')['frozen_inputs']
check('corpus_hash_matches_pilot',sha(ROOT/cfg['corpus']['path'])==cfg['corpus']['sha256'])
for name,item in cfg['gold_sources'].items():check('pilot_gold_source_'+name,sha(ROOT/item['path'])==item['sha256'])
corpus=jl(ROOT/cfg['corpus']['path']);cm={c['chunk_id']:c for c in corpus}
check('corpus_counts',len(cm)==447 and len({c['source'] for c in corpus})==3)
check('chunk_text_hashes',all(hashlib.sha256(c['chunk_text'].encode()).hexdigest()==c['chunk_text_sha256'] for c in corpus))
mapping=read(BASE/'p2-gold-07/.p2-work/b03_inputs.json')['mapping']
original=load_workbook(BASE/'review.xlsx',read_only=True,data_only=True)
os=original[original.sheetnames[0]]
check('B_ids_match_current_source_workbook',all(os.cell(r['row'],2).value==r['candidate_id'] for r in mapping),{'mapped':len(mapping)})
records=jl(OUT/'candidate_reviews.jsonl');new=jl(OUT/'new_candidates_15.jsonl');primary=jl(OUT/'holdout_proposed_28.jsonl')
inventory=read(OUT/'candidate_inventory_72.json')
check('candidate_counts_unique',len(records)==46 and len(new)==15 and len(inventory)==72 and len({r['candidate_id'] for r in inventory})==72)
check('review_scope_complete',{r['review_id'] for r in records}=={'B23'}|{f'B{i}' for i in range(28,58)}|{f'P4-N{i:02}' for i in range(1,16)})
check('B28_B42_prior_conclusions',collections.Counter(r['ai_recommendation'] for r in records if r['review_id'].startswith('B') and 28<=int(r['review_id'][1:])<=42)=={'Accept':8,'Revise':5,'Reject':2})
check('B43_B57_audit_conclusions',collections.Counter(r['ai_recommendation'] for r in records if r['review_id'].startswith('B') and 43<=int(r['review_id'][1:])<=57)=={'Accept':7,'Revise':8})
check('human_fields_blank_in_new_material',all(r[k] is None for r in records for k in ['human_decision','human_reviewer','human_reviewed_at','human_comment']))
check('no_new_gold_or_frozen_holdout',all(r['gold_case_id'] is None and r['is_frozen_holdout'] is False and r['review_status']=='pending_human_review' for r in records))
dev=read(ROOT/'p3-pilot-01/data/gold_provenance.json')['cases']
devchunks={i for r in dev for i in r['evidence_chunk_ids']+r['relevant_chunk_ids']}
check('primary_28_excludes_development_chunks',len(primary)==28 and all(not set(r['evidence_chunk_ids'])&devchunks for r in primary))
check('primary_27_unique_chunks',len({i for r in primary for i in r['evidence_chunk_ids']})==27)
check('all_evidence_in_frozen_corpus',all(i in cm for r in records for i in r['evidence_chunk_ids']+r['original_supporting_chunk_ids']))
check('source_and_page_metadata',all(s['document']==cm[s['chunk_id']]['source'] and s['physical_page']==cm[s['chunk_id']]['page_number'] for r in records for s in r['sources']))
check('new_no_price_queries',all('单价' not in r['query'] for r in new))
check('new_ids_reproducible',all(r['candidate_id']=='p4-candidate-sha256:'+hashlib.sha256(json.dumps({'snapshot':r['snapshot_id'],'query':r['query'],'answer':r['reference_answer'],'ids':r['evidence_chunk_ids']},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest() for r in new))
pdfs={s:PdfReader(ROOT/'data'/s) for s in {c['source'] for c in corpus}}
# Re-extract only required pages in the independent bundled PDF engine.
anchor_checks=[]
for r in new:
    s=r['sources'][0];p=pdfs[s['document']].pages[s['physical_page']-1]
    pt=norm(p.extract_text());ct=norm(cm[s['chunk_id']]['chunk_text'])
    for a in r['evidence_anchors']:
        ok=norm(a) in ct and norm(a) in pt
        anchor_checks.append({'review_id':r['review_id'],'anchor':a,'chunk':norm(a) in ct,'pdf':norm(a) in pt})
check('new_anchors_in_PDF_and_chunk',all(a['chunk'] and a['pdf'] for a in anchor_checks),{'anchors':len(anchor_checks),'failures':[a for a in anchor_checks if not a['chunk'] or not a['pdf']]})
evidence=jl(OUT/'evidence_catalog.jsonl')
check('evidence_catalog_byte_exact_text',all(e['chunk_text']==cm[e['chunk_id']]['chunk_text'] for e in evidence))
check('evidence_catalog_includes_original_and_revised',set(e['chunk_id'] for e in evidence)=={i for r in records for i in r['evidence_chunk_ids']+r['original_supporting_chunk_ids']})

book=ROOT/'outputs/p4-gold-completion-01/human_signoff.xlsx'
if book.exists():
    wb=load_workbook(book,data_only=False);w=wb['签核'];values=load_workbook(book,data_only=True)['签核']
    check('workbook_46_rows_unique',w.max_row==56 and len({w.cell(i,1).value for i in range(11,57)})==46)
    check('workbook_human_fields_blank',all(w.cell(i,j).value in [None,''] for i in range(11,57) for j in range(6,10)))
    check('workbook_no_test_identity_leak',not any('workflow-test' in str(c.value) for row in w for c in row))
    check('workbook_caches_initial_state',values['B6'].value==0 and all(values.cell(i,10).value=='待签核' for i in range(11,57)))
    check('workbook_original_and_proposal_ids_match',all(w.cell(i,14).value==next(r['candidate_id'] for r in records if r['review_id']==w.cell(i,1).value) and w.cell(i,15).value==next(r['proposal_id'] for r in records if r['review_id']==w.cell(i,1).value) for i in range(11,57)))
    check('workbook_human_decision_validation',any(str(v.sqref)=='F11:F56' and '接受原题' in (v.formula1 or '') for v in w.data_validations.dataValidation))
    check('workbook_freezes_headers',w.freeze_panes=='B11',str(w.freeze_panes))
    check('workbook_all_formulas_no_error',not any(c.data_type=='e' for sheet in load_workbook(book,data_only=True) for row in sheet for c in row))
else:check('workbook_export_exists',False)
broken=[]
for p in OUT.glob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#'):continue
        resolved=(p.parent/unquote(target.split('#')[0])).resolve()
        if not resolved.exists():broken.append({'file':p.name,'target':target})
check('markdown_link_targets',not broken,broken)
result={'status':'passed' if all(c['passed'] for c in checks) else 'failed','checks_passed':sum(c['passed'] for c in checks),'checks_total':len(checks),'checks':checks,'anchor_checks':anchor_checks,
        'scope':'Offline static/data and workbook validation only; no retrieval, models, database connection or Benchmark.'}
(OUT/'_work/validation_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':result['status'],'passed':result['checks_passed'],'total':len(checks),'failed':[c['check'] for c in checks if not c['passed']]},ensure_ascii=False,indent=2))
sys.exit(0 if result['status']=='passed' else 1)
