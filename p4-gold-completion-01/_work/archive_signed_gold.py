"""Archive explicitly signed primary cases. Offline only; no evaluator invocation."""
import json,hashlib,collections,re,shutil
from pathlib import Path
from datetime import datetime,timezone,date
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[2]
PACK=ROOT/'p4-gold-completion-01'
OUT=PACK/'signed-final-20261105-v1'
BOOK=ROOT/'outputs/p4-gold-completion-01/human_signoff.xlsx'
REVIEWER='system'
SIGNED_DATE='2026-11-05'
CONFIRMATION='确认：审核标识 system，日期 2026-11-05'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(x):return hashlib.sha256(canon(x).encode()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dumpjl(p,rows):p.write_text(''.join(canon(r)+'\n' for r in rows),encoding='utf-8')
def serial(v):return v.isoformat() if isinstance(v,(datetime,date)) else v

assert not OUT.exists(),'Version already exists; validate it rather than overwrite an archive.'
original_hash=sha(BOOK)
inputs=read(PACK/'input_integrity.json')['hashes']
assert all((ROOT/p).exists() and sha(ROOT/p)==h for p,h in inputs.items()),'Original protected input drift'
oldmanifest=read(PACK/'packet_manifest.json')
allowed_book='outputs/p4-gold-completion-01/human_signoff.xlsx'
assert all(sha(ROOT/p)==h for p,h in oldmanifest['files'].items() if p!=allowed_book),'Review packet content drift'
records={r['review_id']:r for r in jl(PACK/'candidate_reviews.jsonl')}
primary=jl(PACK/'holdout_proposed_28.jsonl')
primary_ids={r['review_id'] for r in primary}
corpus_path=ROOT/'storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl'
corpus=jl(corpus_path);cm={c['chunk_id']:c for c in corpus}
dev_path=ROOT/'p3-pilot-01/data/gold_22_merged.jsonl'
devmeta=read(ROOT/'p3-pilot-01/data/gold_provenance.json')['cases']
devchunks={i for r in devmeta for i in r['evidence_chunk_ids']+r['relevant_chunk_ids']}
w=load_workbook(BOOK,data_only=False)['签核'];cached=load_workbook(BOOK,data_only=True)['签核']
receipt=[];byid={}
for row in range(11,57):
    b=w.cell(row,1).value;r=records[b]
    for col,key in {3:'ai_recommendation',4:'query',5:'reference_answer',14:'candidate_id',15:'proposal_id',16:'review_record_sha256'}.items():
        assert w.cell(row,col).value==r[key],f'{b} changed {key}'
    raw={k:serial(w.cell(row,col).value) for k,col in {'human_decision':6,'human_reviewer':7,'human_reviewed_at':8,'human_comment':9}.items()}
    assert raw['human_decision'] in {'接受原题','接受修订','驳回'},b
    assert raw['human_reviewer']==REVIEWER and raw['human_reviewed_at']=='=NOW()',b
    rec={'review_id':b,'candidate_id':r['candidate_id'],'proposal_id':r['proposal_id'],
         'review_record_sha256':r['review_record_sha256'],'worksheet':'签核','row':row,
         'recorded_human_fields':raw,'cached_reviewed_at_for_audit_only':serial(cached.cell(row,8).value),
         'cached_status_for_audit_only':cached.cell(row,10).value,
         'archived_review_metadata':{'human_decision':raw['human_decision'],'human_reviewer':REVIEWER,
                                     'human_reviewed_at':SIGNED_DATE,'human_comment':raw['human_comment']},
         'metadata_confirmation':CONFIRMATION,
         'selection_tier':r['selection_tier'],
         'dataset_membership':'Holdout' if b in primary_ids else 'not_exported',
         'resolution_status':'signed_primary' if b in primary_ids else 'recorded_nonprimary_not_promoted'}
    if b in {'B31','B39'}:
        rec['resolution_status']='pending_missing_revised_proposal'
        rec['resolution_reason']='接受修订，但原审核包无修订题答，且为AI Reject；不自动批准占位日期或不完整比较。'
    elif raw['human_decision']=='接受修订' and not r['is_revision']:
        rec['resolution_note']='题答与原题同版；保留原始选择，不虚构修订内容。未纳入本版28条Holdout。'
    elif b=='B23' and raw['human_decision']=='接受原题':
        rec['resolution_note']='明确接受原题，未替换为AI修订；与Development共用Chunk，未纳入本版Holdout。'
    receipt.append(rec);byid[b]=rec
assert len(receipt)==46 and len(primary)==28

# A short literal target preserves the legacy loader schema; IDs in the sidecar
# remain the authoritative retrieval labels. No numeric-only global matching.
oldanchors={
 'B32':'职业能力应具有学习、表达、计算、故障处置能力',
 'B33':'鉴定方式应分为理论知识考试、技能考核',
 'B34':'铁路 3.0 7.5',
 'B35':'产品类型 光网关 光路由 产品名称',
 'B40':'WH23120 安装、调试、断电检修变压器',
 'B41':'WH23121 安装与调试控制设备',
 'B42':'WH23122 发电设备专项检修',
 'B48':'原措施费中已有的措施项目，按原措施项目的组价方法调整',
 'B49':'维护分项作业费应依据双方确认的工作量、合同约定的综合单价计算',
 'B50':'承包人的维护用机械（仪表）设备损坏及停工损失，由承包人承担',
 'B53':'二维码应集成该设备的Wi-Fi 的SSID 和密码参数',
 'B54':'能使用红光光源、光功率计',
 'B57':'jtwlgl.nx.chinamobile.com:9005(TCP)',
}
def literal(text,anchor):
    positions=[i for i,c in enumerate(text) if not c.isspace()]
    flat=''.join(text[i] for i in positions);want=re.sub(r'\s+','',anchor)
    start=flat.find(want);assert start>=0,anchor
    return text[positions[start]:positions[start+len(want)-1]+1]
gold=[];cases=[];lineage=[]
for r in primary:
    b=r['review_id'];signed=byid[b];decision=signed['archived_review_metadata']['human_decision']
    assert decision==('接受修订' if r['is_revision'] else '接受原题'),b
    assert not(set(r['evidence_chunk_ids'])&devchunks)
    assert len(r['evidence_chunk_ids'])==1 and r['retrieval_relevant_chunk_ids']==r['evidence_chunk_ids']
    cid=r['evidence_chunk_ids'][0];c=cm[cid]
    anchor=oldanchors[b] if b in oldanchors else r['evidence_anchors'][0]
    expected=[{'source':c['source'],'section_title':c['metadata']['section_title'],'text_contains':literal(c['chunk_text'],anchor)}]
    matches=[x['chunk_id'] for x in corpus if x['source']==expected[0]['source'] and x['metadata']['section_title']==expected[0]['section_title'] and expected[0]['text_contains'] in x['chunk_text']]
    assert matches==[cid],(b,matches)
    caseid='gold-holdout-v1-sha256:'+digest({'candidate_id':r['candidate_id'],'proposal_id':r['proposal_id'],'decision':decision,'query':r['query'],'reference_answer':r['reference_answer'],'relevant_chunk_ids':r['retrieval_relevant_chunk_ids'],'snapshot_id':r['snapshot_id']})
    gold.append({'query':r['query'],'expected':expected,'note':caseid,'tags':['Holdout','P4-Gold-Completion-01']})
    changed_target=set(r['original_supporting_chunk_ids'])!=set(r['evidence_chunk_ids'])
    history={'review_id':b,'parent_candidate_id':r['candidate_id'],'accepted_proposal_id':r['proposal_id'],
             'gold_case_id':caseid,'is_revision':r['is_revision'],'changed_retrieval_target':changed_target,
             'revision_kind':'new_proposal_retargeted' if changed_target else 'content_revision' if r['is_revision'] else 'accepted_original',
             'original_question':r['original_question'],'original_answer':r['original_answer'],
             'original_supporting_chunk_ids':r['original_supporting_chunk_ids'],
             'accepted_question':r['query'],'accepted_reference_answer':r['reference_answer'],
             'accepted_evidence_chunk_ids':r['evidence_chunk_ids'],
             'human_comment':signed['archived_review_metadata']['human_comment']}
    lineage.append(history)
    cases.append({'batch_id':b,'gold_case_id':caseid,'parent_candidate_id':r['candidate_id'],
                  'proposal_id':r['proposal_id'],'review_record_sha256':r['review_record_sha256'],
                  'query':r['query'],'reference_answer':r['reference_answer'],'expected':expected,
                  'retrieval_relevant_chunk_ids':r['retrieval_relevant_chunk_ids'],
                  'relevant_chunk_ids':r['retrieval_relevant_chunk_ids'],'evidence_chunk_ids':r['evidence_chunk_ids'],
                  'requires_all_evidence':r['requires_all_evidence'],'question_type':r['question_type'],
                  'knowledge_topic':r['knowledge_topic'],'sources':r['sources'],
                  'snapshot_id':r['snapshot_id'],'dataset_role':'Holdout','is_frozen_holdout':True,
                  'human_review':signed['archived_review_metadata'],
                  'source_workbook_sha256':original_hash,'lineage':history})

OUT.mkdir(parents=True);(OUT/'audit').mkdir()
shutil.copyfile(BOOK,OUT/'audit/reviewed_source.xlsx')
assert sha(OUT/'audit/reviewed_source.xlsx')==original_hash
dumpjl(OUT/'human_signoff_receipt_46.jsonl',receipt)
dumpjl(OUT/'retrieval_gold_holdout_28.jsonl',gold)
dump(OUT/'retrieval_gold_holdout_metadata.json',{'dataset_version':'p4-holdout-v1-20261105','dataset_role':'Holdout','count':28,'status':'human_signed_content_frozen','human_reviewer':REVIEWER,'human_reviewed_at':SIGNED_DATE,'cases':cases,'use_restriction':'不得用于调参；Benchmark尚未运行。'})
dump(OUT/'candidate_proposal_gold_lineage.json',lineage)
dump(OUT/'development_22_role_manifest.json',{'dataset_role':'Development','count':22,'source':str(dev_path.relative_to(ROOT)).replace('\\','/'),'sha256':sha(dev_path),'cases':[{'batch_id':r['batch_id'],'gold_case_id':r['gold_case_id']} for r in devmeta],'note':'引用原文件，不复制、改写或重新编号22条。'})
dump(OUT/'nonprimary_dispositions_18.json',[r for r in receipt if r['dataset_membership']=='not_exported'])
doccounts=dict(collections.Counter(r['sources'][0]['document'] for r in cases))
dump(OUT/'source_integrity.json',{'source_workbook_sha256':original_hash,'protected_input_count':len(inputs),'protected_inputs':inputs,
                                 'review_packet_content_hashes':{p:h for p,h in oldmanifest['files'].items() if p!=allowed_book},
                                 'authorized_change':'仅人工填写签核表的F:I列；待签题答、意见及全部ID与原审核包一致。',
                                 'metadata_confirmation':CONFIRMATION,'date_precision':'day','cached_NOW_is_not_fixed_signature_time':True})
report=f'''# 人工签核归档与最终划分

2026-11-05（Asia/Shanghai）。本版完成内容签核归档，未运行正式Benchmark。

| 项目 | 数量 |
| --- | ---: |
| 保留原文件的Development | 22 |
| 新签核并冻结的Holdout | 28 |
| 本版评测内容总数 | 50 |
| 其他已填写决定但未纳入本版 | 18 |
| 其中无修订稿待澄清 | 2 |

28条Holdout中18条接受原题、10条接受修订。覆盖3份PDF、27个独立Chunk，与Development相关/证据Chunk并集交集为0；文档题数为{json.dumps(doccounts,ensure_ascii=False)}。主选名单与原28条建议完全一致，没有利用Pilot排名或评测结果替换题目。

## 签核证据

原工作簿46条决定均有填写：接受原题26、接受修订20。人工已在本次对话确认审核标识`system`及固定签核日期`2026-11-05`，归档元数据采用该确认；原表的`=NOW()`公式和缓存值完整保留在audit副本中，不把动态公式当成固定签署时刻。

原工作簿的状态公式把`system`视为待补身份，因此缓存状态仍可能为“需补身份日期”。本版依据人工明确确认归档，不改写原表公式或人填字段。

本版仅导出28条主选。B31/B39虽填“接受修订”，但原包无修订题答，先保留待澄清，不把占位日期或不完整比较批准入集。其余16条只记录原始决定及角色原因，不追加到本版Development，也不自动混入Holdout。

## 原候选与新提案

B32、B33、B35改变检索目标，标为`new_proposal_retargeted`：保留原candidate_id、原题答、原证据、独立proposal_id及新gold_case_id。另7条修订也有独立Gold身份，未覆盖原候选或既有22条Gold。逐题见[candidate_proposal_gold_lineage.json](candidate_proposal_gold_lineage.json)。

## 冻结内容与边界

- 检索输入：[28条Holdout JSONL](retrieval_gold_holdout_28.jsonl)。与既有loader的query/expected/note格式兼容。
- 标准答案、人工签核、来源物理页、证据/相关ID与版本：[sidecar](retrieval_gold_holdout_metadata.json)。
- [Development角色清单](development_22_role_manifest.json)引用原22条文件；不将50条合并成“50条未见测试”。正式留出指标分母为28。
- expected的source/section_title/text_contains只用于旧入口兼容，相关ID集合是正式检索相关标签；生成答案评分须使用sidecar完整标准答案，不能靠短语命中代替完整性评分。
- 内容冻结不等于执行已就绪。正式执行前仍须确认四组配置/模型版本、数据库与快照等价、延迟与失败口径和运行授权；见[执行前门槛](benchmark_preflight_pending.md)。
- Holdout不得用于后续调参，原始语料和既有Gold不变。当前没有任何Holdout检索结果、模型回答或指标。

源工作簿SHA-256：`{original_hash}`。文件级冻结哈希见[freeze_manifest.json](freeze_manifest.json)。该清单是内容版本归档，不宣称文件系统具有WORM写保护。
'''
(OUT/'signoff_archive_report.md').write_text(report,encoding='utf-8')
(OUT/'benchmark_preflight_pending.md').write_text('''# 正式Benchmark执行前门槛

- [x] 28条主选已人工接受，18原题、10修订；固定日级签核信息已由人工确认。
- [x] 内容、标准答案、人工签核、来源、相关ID及原候选关系已生成独立冻结版本；原Development22条仅引用。
- [ ] 复核运行时数据库447 Chunk与冻结快照的ID和文本等价；本次没有连接数据库。
- [ ] 预注册四组方法、K、候选池、阈值、权重、重排版本、query策略、随机性、延迟冷热缓存/并发及失败分母。
- [ ] 记录实际实现的Git提交与未提交diff哈希；P3修复目前仍未提交，不能只拿HEAD代表实现。
- [ ] 明确仅检索还是含答案生成；如含生成，固定sidecar标准答案要点、可接受变体及judge规则。
- [ ] 执行器读取相关Chunk集合，并正确区分命中和完整证据；多证据不以OR匹配冒充AND完整性。
- [ ] 仅用Development做执行器冒烟；Holdout不得试跑调参。
- [ ] 人工授权正式Benchmark运行。分别报告Development22和Holdout28，不混成50条未见测试。

本次没有运行正式Benchmark，没有改检索配置，也没有用新Holdout调用任何模型或检索入口。
''',encoding='utf-8')
# Validation report is emitted separately; the frozen file list is finalized after it passes.
assert sha(BOOK)==original_hash
print(canon({'archive':str(OUT),'holdout':len(cases),'development':22,'primary_decisions':dict(collections.Counter(c['human_review']['human_decision'] for c in cases)),'formal_benchmark_run':False}))
