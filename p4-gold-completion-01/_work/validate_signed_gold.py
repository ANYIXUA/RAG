"""Validate frozen dataset files without importing retrieval or invoking a model."""
import ast,json,hashlib,re,collections,sys
from pathlib import Path
from dataclasses import dataclass
from types import SimpleNamespace
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];PACK=ROOT/'p4-gold-completion-01';OUT=PACK/'signed-final-20261105-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
checks=[]
def check(name,ok,details=None):checks.append({'check':name,'passed':bool(ok),'details':details})

receipt=jl(OUT/'human_signoff_receipt_46.jsonl');s=read(OUT/'source_integrity.json')
gold=jl(OUT/'retrieval_gold_holdout_28.jsonl');meta=read(OUT/'retrieval_gold_holdout_metadata.json');cases=meta['cases']
proposals={r['review_id']:r for r in jl(PACK/'holdout_proposed_28.jsonl')}
originals={r['review_id']:r for r in jl(PACK/'candidate_reviews.jsonl')}
corpus=jl(ROOT/'storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl');cm={c['chunk_id']:c for c in corpus}
dev=read(ROOT/'p3-pilot-01/data/gold_provenance.json')['cases'];devchunks={i for r in dev for i in r['evidence_chunk_ids']+r['relevant_chunk_ids']}
changed=[p for p,h in s['protected_inputs'].items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
check('236_protected_inputs_unchanged',not changed,{'count':len(s['protected_inputs']),'changed':changed})
check('signed_workbook_unchanged',sha(ROOT/'outputs/p4-gold-completion-01/human_signoff.xlsx')==s['source_workbook_sha256'])
check('signed_workbook_audit_copy_exact',sha(OUT/'audit/reviewed_source.xlsx')==s['source_workbook_sha256'])
check('review_packet_content_unchanged',all(sha(ROOT/p)==h for p,h in s['review_packet_content_hashes'].items()))
check('46_original_decisions_preserved',len(receipt)==46 and collections.Counter(r['recorded_human_fields']['human_decision'] for r in receipt)=={'接受原题':26,'接受修订':20})
check('user_confirmed_metadata',all(r['archived_review_metadata']['human_reviewer']=='system' and r['archived_review_metadata']['human_reviewed_at']=='2026-11-05' and r['metadata_confirmation']=='确认：审核标识 system，日期 2026-11-05' for r in receipt))
check('NOW_formula_preserved_as_evidence',all(r['recorded_human_fields']['human_reviewed_at']=='=NOW()' for r in receipt))
check('28_gold_and_sidecar',len(gold)==len(cases)==28)
check('22_development_exact_reference',read(OUT/'development_22_role_manifest.json')['sha256']==sha(ROOT/'p3-pilot-01/data/gold_22_merged.jsonl') and len(dev)==22)
check('exact_primary_membership',{c['batch_id'] for c in cases}==set(proposals))
check('unique_gold_ids',len({c['gold_case_id'] for c in cases})==28 and not {c['gold_case_id'] for c in cases}&{r['gold_case_id'] for r in dev})
check('no_development_evidence_overlap',all(not set(c['evidence_chunk_ids'])&devchunks for c in cases))
check('27_distinct_chunks',len({i for c in cases for i in c['evidence_chunk_ids']})==27)
check('3_document_coverage',collections.Counter(c['sources'][0]['document'] for c in cases)=={'电信基础设施维护规程.pdf':12,'中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf':10,'智慧家庭装维工程与管理职业技能等级标准.pdf':6})
check('18_original_10_revised',collections.Counter(c['human_review']['human_decision'] for c in cases)=={'接受原题':18,'接受修订':10})
check('accepted_content_matches_signed_proposal',all(c['query']==proposals[c['batch_id']]['query'] and c['reference_answer']==proposals[c['batch_id']]['reference_answer'] and c['proposal_id']==proposals[c['batch_id']]['proposal_id'] for c in cases))
check('lineage_original_content_preserved',all(c['lineage']['original_question']==originals[c['batch_id']]['original_question'] and c['lineage']['original_answer']==originals[c['batch_id']]['original_answer'] and c['lineage']['original_supporting_chunk_ids']==originals[c['batch_id']]['original_supporting_chunk_ids'] for c in cases))
check('B32_B33_B35_retargeted_new_proposals',{c['batch_id'] for c in cases if c['lineage']['revision_kind']=='new_proposal_retargeted'}=={'B32','B33','B35'})
check('retargeting_human_comments_preserved',all('不能把改变检索目标伪装成普通文字修正' in (c['human_review']['human_comment'] or '') for c in cases if c['batch_id'] in {'B32','B33','B35'}))
check('B31_B39_not_approved_or_exported',{r['review_id'] for r in receipt if r['resolution_status']=='pending_missing_revised_proposal'}=={'B31','B39'} and not {'B31','B39'}&{c['batch_id'] for c in cases})
check('18_nonprimary_not_promoted',len(read(OUT/'nonprimary_dispositions_18.json'))==18 and all(r['dataset_membership']=='not_exported' for r in read(OUT/'nonprimary_dispositions_18.json')))
check('all_chunk_ids_in_frozen_snapshot',all(i in cm for c in cases for i in c['evidence_chunk_ids']+c['retrieval_relevant_chunk_ids']))
check('roles_signed_and_frozen',all(c['dataset_role']=='Holdout' and c['is_frozen_holdout'] is True for c in cases))
check('single_chunk_complete_evidence',all(len(c['evidence_chunk_ids'])==1 and c['requires_all_evidence'] is False and c['retrieval_relevant_chunk_ids']==c['evidence_chunk_ids'] for c in cases))
check('no_single_price_queries',all('综合单价是多少' not in c['query'] for c in cases))

# Execute only the owning module's pure JSONL/schema helpers and target matcher.
# The online/evaluator imports are deliberately absent.
owner=ROOT/'rag_app/operations/evaluation.py';tree=ast.parse(owner.read_text(encoding='utf-8-sig'))
names={'ExpectedTarget','RetrievalEvalCase','load_retrieval_eval_cases','_case_from_payload','_parse_expected','_parse_tags','_optional_string','_matches_target'}
nodes=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
assert {n.name for n in nodes}==names
namespace={'__name__':'__main__','dataclass':dataclass,'Path':Path,'json':json}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(owner)+' [pure schema subset]','exec'),namespace)
loaded=namespace['load_retrieval_eval_cases'](OUT/'retrieval_gold_holdout_28.jsonl')
check('actual_loader_schema_helpers_accept_28',len(loaded)==28 and all(x.tags==['Holdout','P4-Gold-Completion-01'] for x in loaded))
matches=[]
for c,case,g in zip(cases,loaded,gold):
    ids=[]
    for chunk in corpus:
        fake=SimpleNamespace(chunk=SimpleNamespace(metadata=chunk['metadata'],text=chunk['chunk_text']))
        if any(namespace['_matches_target'](fake,t) for t in case.expected):ids.append(chunk['chunk_id'])
    matches.append({'batch_id':c['batch_id'],'matches':ids,'expected':c['retrieval_relevant_chunk_ids']})
check('legacy_targets_resolve_exact_related_ids',all(x['matches']==x['expected'] for x in matches))
check('gold_sidecar_alignment',all(g['note']==c['gold_case_id'] and g['query']==c['query'] and g['expected']==c['expected'] for g,c in zip(gold,cases)))
if (OUT/'freeze_manifest.json').exists():
    manifest=read(OUT/'freeze_manifest.json')
    check('freeze_manifest_hashes',all(sha(OUT/p)==h for p,h in manifest['files'].items()))
    check('no_formal_benchmark',manifest['formal_benchmark_run'] is False)
result={'status':'passed' if all(c['passed'] for c in checks) else 'failed','passed':sum(c['passed'] for c in checks),'total':len(checks),'checks':checks,'pure_schema_owner_sha256':sha(owner),'target_matches':matches,'scope':'No retrieval ranking, database, embedding, rerank, model inference, or Benchmark.'}
# Keep manifest-covered validation stable on reruns; do not mutate an archived report.
validation_path=OUT/'validation.json'
if not (OUT/'freeze_manifest.json').exists():
    dump(validation_path,result)
    (OUT/'validation.md').write_text(f'''# 签核Gold归档验证

本地文件、内容与格式检查 **{result['passed']}/{result['total']}通过**。完整检查见[validation.json](validation.json)。

236个受保护输入未变；原签核工作簿和审计副本字节一致。28条Gold及sidecar和签核版本逐条一致，18原题/10修订；原候选关系与B32/B33/B35目标变化均保留。

Development仍为原22条；新增Holdout28条覆盖27块、3文档，Development证据交集为0。B31/B39按人工确认保留待澄清，其他18条均未混入本版。

从现有evaluation.py仅提取纯JSONL解析/字段校验/目标匹配函数执行，28条均兼容现有schema，source/section_title/text_contains在447个冻结Chunk上各自唯一对应sidecar相关ID。这是格式与标签校验，没有进行检索排序或计算评测指标。

审核标识system与固定日期2026-11-05来自人工本次明确确认；原NOW公式仅作为审计证据保存。未伪造精确签署时间，未改写原表人工字段。

未连接数据库、调用模型、执行Embedding/Rerank、运行Development冒烟或正式Benchmark。也未commit/push。
''',encoding='utf-8')
    dump(OUT/'human_metadata_confirmation.json',{'source':'本次对话的人工明确回复','reviewer_and_date_confirmation':'确认：审核标识 system，日期 2026-11-05','nonprimary_confirmation':'保留待澄清，仅推进28条主选','reviewer_alias':'system','reviewed_date':'2026-11-05','timestamp_precision':'day','raw_workbook_untouched':True})
    assert result['status']=='passed',result
    files=[p for p in OUT.rglob('*') if p.is_file()]
    dump(OUT/'freeze_manifest.json',{'dataset_version':'p4-holdout-v1-20261105','status':'human_signed_content_frozen','created_at_utc':datetime.now(timezone.utc).isoformat(),'human_reviewed_date':'2026-11-05','development_count':22,'holdout_count':28,'total_content_count':50,'formal_benchmark_run':False,'frozen_scope':'题目、标准答案、来源、相关ID、人工签核与lineage；执行配置仍待预注册','files':{p.relative_to(OUT).as_posix():sha(p) for p in sorted(files)}})
print(json.dumps({'status':result['status'],'passed':result['passed'],'total':result['total'],'failed':[c['check'] for c in checks if not c['passed']]},ensure_ascii=False))
sys.exit(0 if result['status']=='passed' else 1)
