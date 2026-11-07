"""Frozen Holdout adapter: reuses the verified Pilot evaluator and production search."""
import argparse, hashlib, json, os, sys, subprocess, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path[:0]=[str(ROOT),str(ROOT/'p3-pilot-02')]
import run_comparison as rc
rp=rc.rp
OUT=ROOT/'p5-benchmark-01'
F=ROOT/'p4-gold-completion-01/signed-final-20261105-v1'
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def lines(p): return [json.loads(s) for s in Path(p).read_text(encoding='utf-8').splitlines() if s.strip()]
def norm(s): return ''.join(c for c in unicodedata.normalize('NFKC',s).casefold() if c.isalnum())
def gate():
    pilot=read('p3-pilot-02/experiment_config.json')
    assert rc.verify_inputs()==161
    assert rc.digest('rag_app/indexing/vector_store.py')==pilot['implementation']['fixed2']['implementation_sha256']
    freeze=read(F/'freeze_manifest.json')
    assert all(rc.digest(F/p)==h for p,h in freeze['files'].items())
    meta=read(F/'retrieval_gold_holdout_metadata.json'); cases=meta['cases']
    data=lines(F/'retrieval_gold_holdout_28.jsonl')
    assert len(cases)==len(data)==28
    assert len({c['gold_case_id'] for c in cases})==28
    byid={c['gold_case_id']:c for c in cases}
    for row in data:
        c=byid[row['note']]; assert row['query']==c['query'] and row['expected']==c['expected']
    receipts={r['review_record_sha256']:r for r in lines(F/'human_signoff_receipt_46.jsonl')}
    confirm=read(F/'human_metadata_confirmation.json')
    corpus,ci=rp.load_corpus(); assert len(corpus)==447
    assert ci['sha256']==pilot['frozen_inputs']['corpus']['sha256']
    devmanifest=read(F/'development_22_role_manifest.json')
    assert rc.digest(devmanifest['source'])==devmanifest['sha256']
    dev=lines(devmanifest['source']); assert len(dev)==22
    assert not ({norm(c['query']) for c in cases}&{norm(c['query']) for c in dev})
    devcases=[]
    for key in ['batch01_metadata','batch02_metadata']:
        devcases.extend(read(pilot['frozen_inputs']['gold_sources'][key]['path'])['cases'])
    devchunks={x for c in devcases for x in c['retrieval_relevant_chunk_ids']+c['evidence_chunk_ids']}
    for c in cases:
        h=c['human_review']; r=receipts[c['review_record_sha256']]
        assert h==r['archived_review_metadata']
        assert h['human_decision'] in ('接受原题','接受修订')
        assert h['human_reviewer']==confirm['reviewer_alias'] and h['human_reviewed_at']==confirm['reviewed_date']
        assert c['dataset_role']=='Holdout' and c['is_frozen_holdout']
        ids=c['retrieval_relevant_chunk_ids']; assert ids and set(ids)<=corpus.keys()
        assert not (set(ids+c['evidence_chunk_ids'])&devchunks)
        for s in c['sources']: assert rp.sha256_text(corpus[s['chunk_id']]['chunk_text'])==s['chunk_text_sha256']
    settings,dsn=rp.build_settings()
    db=rp.verify_corpus_against_database(corpus,dsn)
    packages=rp.package_versions(); assert packages==pilot['environment']['packages'],packages
    rev=rp.hf_snapshot_revisions(settings.rerank_model)
    assert rev==pilot['rerank']['status']['hf_snapshot_revisions']
    files={str(p.relative_to(ROOT)).replace('\\','/'):rc.digest(p) for base in ['rag_app','p3-pilot-01','p3-pilot-02'] for p in (ROOT/base).rglob('*.py')}
    files.update({str(p.relative_to(ROOT)).replace('\\','/'):rc.digest(p) for p in F.rglob('*') if p.is_file()})
    files['p5-benchmark-01/run_benchmark.py']=rc.digest(__file__)
    config={k:pilot[k] for k in ['retrieval','rerank','models','environment']}
    config.update(benchmark='P5-Benchmark-01',gold_total=50,development=22,holdout=28,metrics_denominator=28,
        methods=pilot['methods'][:4],packages=packages,input_code_hashes=files,database_equivalence=db,
        git_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        embedding_revision='Provider exposes text-embedding-v4 alias, no immutable weight revision; exact returned vectors archived. No stronger version guarantee claimed.',
        latency_protocol='Serial query-major A/B/C/D; one non-Gold warmup per method; CPU rerank; excludes embedding, model load, DB initialization. Warm cache, no parallel probes. p50/p95 linear interpolation; 28 timings/method. Not end-to-end or controlled performance benchmark.',
        failure_policy='Any unavailable method or infrastructure exception aborts official run; no dropped queries or denominator changes.',
        query_rewriting=False,intent_routing=False,seed=0,rerank_max_length=512,rerank_activation='Identity',
        run_order=['run1','run2'],reporting_run='run1 fixed in advance; run2 consistency only',tuning_allowed=False)
    if (OUT/'preregistered_config.json').exists():
        old=read(OUT/'preregistered_config.json'); assert config==old,'Configuration/input drift'
    else:
        write(OUT/'preregistered_config.json',config)
        (OUT/'git_diff_entry.patch').write_bytes(subprocess.check_output(['git','diff','--','rag_app','tests']))
        (OUT/'git_status_entry.txt').write_bytes(subprocess.check_output(['git','status','--short']))
    return cases,config

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');ap.add_argument('--run',choices=['run1','run2']);a=ap.parse_args()
    try: cases,config=gate()
    except Exception as e:
        write(OUT/'preflight_failure.json',{'error':repr(e),'formal_run_started':False});raise
    write(OUT/'preflight_pass.json',{'checks':'28 signed cases, receipt equality, frozen hashes, corpus DB equivalence, no Development duplicate queries or evidence, exact Pilot implementation hash and packages','ok':True,'at':rp.utc_now()})
    if a.preflight: print('PRECHECK PASS; configuration preregistered; no Holdout retrieval');return
    assert a.run
    dest=OUT/'runs'/a.run;assert not dest.exists(),'Refuse overwrite'
    rp.METHODS=rp.METHODS[:4]
    rp.GOLD_SOURCES={'holdout_jsonl':str(F.relative_to(ROOT)/'retrieval_gold_holdout_28.jsonl'),'holdout_metadata':str(F.relative_to(ROOT)/'retrieval_gold_holdout_metadata.json')}
    rp.EXCLUDED_BATCH_IDS=set();rp.EXPECTED_BATCH01=[c['batch_id'] for c in cases];rp.EXPECTED_BATCH02=[]
    def load():
        rows=[dict(c,batch='holdout',relevant_chunk_ids=c['retrieval_relevant_chunk_ids'],review_decision=c['human_review']['human_decision']) for c in cases]
        return rows,{'dataset_role':'Holdout','merged_cases':28,'sources':{k:{'path':p,'sha256':rc.digest(p)} for k,p in rp.GOLD_SOURCES.items()}}
    rp.load_gold=load
    import rag_app.indexing.embeddings as em
    orig=em.create_embedder;cachepath=OUT/'query_vectors.json';cache=read(cachepath) if cachepath.exists() else {}
    warm='预热检索链路，不参与评测'
    prior=read('p3-pilot-02/runs/query_vectors.json');cache.setdefault(warm,prior[warm])
    def factory(settings):
        delegate=orig(settings)
        class Cached:
            def embed(self,texts):
                for text in texts:
                    if text not in cache:
                        assert a.run=='run1','Repeat must use frozen query vectors'
                        cache[text]=delegate.embed([text])[0];assert len(cache[text])==1024
                        write(cachepath,cache)
                        print('Embedded',rp.sha256_text(text)[:12],flush=True)
                return [cache[t] for t in texts]
        return Cached()
    em.create_embedder=factory
    from rag_app.retrieval.rerank import CrossEncoderReranker
    init=CrossEncoderReranker.__init__
    def strict(self,name):
        try: init(self,name)
        except Exception as e: raise SystemExit('Required reranker unavailable: '+repr(e))
        assert self.model.max_seq_length==512 and str(self.model.activation_fn)=='Identity()'
    CrossEncoderReranker.__init__=strict
    audits=[];rc.install_rerank_capture(audits)
    assert rp.run(argparse.Namespace(out_dir=str(dest),label=a.run,seed=0,skip_rerank=False))==0
    assert len(lines(dest/'rankings.jsonl'))==112
    write(dest/'rerank_inputs_scores.json',audits)
    # Correct inherited Pilot labels only; metric values and ranks remain untouched.
    for filename in ['metrics.json','run_config.json']:
        v=read(dest/filename);v['pilot']='P5-Benchmark-01'
        if filename=='run_config.json':
            v['evaluation_scope']='formal_frozen_holdout_28';v['dataset']['batches']=['Holdout(28)'];v['retrieval']=config['retrieval']
            v['metrics_definitions']={k:s.replace('22 题','28 题') for k,s in v['metrics_definitions'].items()}
        write(dest/filename,v)
    gate()
    write(dest/'fingerprints.json',{p.name:rc.digest(p) for p in dest.iterdir() if p.is_file() and p.name!='fingerprints.json'})
    write(dest/'complete.json',{'ok':True,'query_vectors_sha256':rc.digest(cachepath),'preregistered_config_sha256':rc.digest(OUT/'preregistered_config.json')})
if __name__=='__main__':main()

