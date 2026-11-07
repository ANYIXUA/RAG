import json, hashlib, re
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'p4-gold-completion-01'
BASE = ROOT / 'storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def jl(p): return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
chunks=jl(ROOT/'storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl')
candidates=jl(ROOT/'storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl')
mapping=read(BASE/'p2-gold-07/.p2-work/b03_inputs.json')['mapping']
byid={c['candidate_id']:c for c in candidates}
cm={c['chunk_id']:c for c in chunks}
packet=(BASE/'p2-gold-07/p2_gold_07_signoff_packet.md').read_text(encoding='utf-8')
old=[]
for block in re.findall(r'```text\n(.*?)```',packet,re.S):
    d=dict(line.split(':',1) for line in block.strip().splitlines() if ':' in line)
    old.append({k:v.strip() for k,v in d.items()})
(OUT/'_work/old_review.json').write_text(json.dumps(old,ensure_ascii=False,indent=2),encoding='utf-8')
paths=[p for p in (ROOT/'storage/evaluation').rglob('*') if p.is_file()]
paths += [p for p in (ROOT/'data').glob('*.pdf')]
paths += [p for p in (ROOT/'p3-pilot-01').rglob('*') if p.is_file()]
paths += [p for p in (ROOT/'p3-pilot-02').rglob('*') if p.is_file()]
paths += [ROOT/p for p in ['rag_app/indexing/vector_store.py','tests/test_rerank.py','rag_app/operations/retrieval_metrics.py','tests/test_keyword_candidates.py','tests/test_retrieval_metrics.py']]
hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(OUT/'_work/input_hashes_before.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2),encoding='utf-8')
pages={}
for x in mapping[42:]:
    c=byid[x['candidate_id']]
    for i in c['supporting_chunk_ids']:
        ch=cm[i]; pages.setdefault(ch['source'],set()).add(ch['page_number'])
lines=[]
for src,nums in pages.items():
    doc=fitz.open(ROOT/'data'/src)
    for n in sorted(nums):
        lines += [f'\n=== {src} PHYSICAL {n} ===',doc[n-1].get_text(sort=True)]
(OUT/'_work/b43_b57_pdf_pages.txt').write_text('\n'.join(lines),encoding='utf-8')
for x in mapping[42:]:
    c=byid[x['candidate_id']]
    print(x['b'],c['question'],'ANSWER:',c['proposed_answer'])
print('chunks_by_source', {s:sum(c['source']==s for c in chunks) for s in sorted({c['source'] for c in chunks})})
print('old_records',len(old),'protected_files',len(hashes))
