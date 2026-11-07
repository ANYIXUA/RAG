import copy
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('topup_silver', HERE / 'topup_silver.py')
t = importlib.util.module_from_spec(spec) if spec else None
if spec and Path(spec.origin).exists():
    spec.loader.exec_module(t)


def api():
    assert hasattr(t, 'Engine'), 'Independent topup Engine has not been implemented'
    return t


@pytest.fixture
def data():
    corpus = [
        {'chunk_id': 'a', 'chunk_text': '设备安装完成后应进行线路检查并确认接地连接牢固可靠。', 'source': 'manual', 'page_number': 1},
        {'chunk_id': 'b', 'chunk_text': '告警恢复后必须登记处理结果并通知相关负责人安排复查。', 'source': 'manual', 'page_number': 2},
    ]
    raw = {'question': '安装完成以后应如何检查接地连接？', 'question_type': 'procedure',
           'answer': '应检查线路并确认接地连接牢固可靠。',
           'evidence': [{'passage_id': 'a', 'excerpt': corpus[0]['chunk_text']}]}
    return corpus, raw


def engine(data, baseline=(), gold=(), targets=None):
    m = api()
    return m.Engine(list(baseline), data[0], list(gold), targets or {'procedure': 1}, 'd' * 64)


def test_feature_available():
    api()


def test_accept_then_quota_does_not_reassign_id(data):
    e = engine(data)
    r = e.consider(data[1], 'procedure', 1, 20271107, ['a', 'b'])
    assert r['status'] == 'accepted'
    assert r['case']['case_id'] == 'p6s-0001'
    assert e.consider(data[1], 'procedure', 1, 20271107, ['a', 'b'])['reason'] == 'quota_full'
    assert len(e.rows) == 1 and e.remaining() == {'procedure': 0}


@pytest.mark.parametrize('gold,baseline,reason', [(True, False, 'duplicate_gold'), (False, True, 'duplicate_silver')])
def test_duplicate_rejected(data, gold, baseline, reason):
    first = engine(data).consider(data[1], 'procedure', 1, 20271107, ['a'])['case']
    e = engine(data, baseline=[first] if baseline else [], gold=[data[1]['question']] if gold else [], targets={'procedure': 2})
    assert e.consider(data[1], 'procedure', 2, 20271108, ['a'])['reason'] == reason


@pytest.mark.parametrize('mutation,reason', [('quote', 'excerpt_not_verbatim'), ('unknown', 'unknown_chunk'), ('missing', 'missing_evidence')])
def test_bad_evidence_rejected(data, mutation, reason):
    raw = copy.deepcopy(data[1])
    if mutation == 'quote': raw['evidence'][0]['excerpt'] = '这是编造出来的证据内容完全不存在于语料。'
    if mutation == 'unknown': raw['evidence'][0]['passage_id'] = 'missing'
    if mutation == 'missing': raw['evidence'] = []
    assert engine(data).consider(raw, 'procedure', 1, 1, ['a', 'b'])['reason'] == reason


def test_two_distinct_chunks_required(data):
    raw = copy.deepcopy(data[1]); raw['question_type'] = 'multi_condition'
    raw['evidence'] *= 2
    e = engine(data, targets={'multi_condition': 1})
    assert e.consider(raw, 'multi_condition', 1, 1, ['a', 'b'])['reason'] == 'multi_condition_needs_two_chunks'
    raw['evidence'][1] = {'passage_id': 'b', 'excerpt': data[0][1]['chunk_text']}
    assert e.consider(raw, 'multi_condition', 2, 2, ['a', 'b'])['status'] == 'accepted'


def test_unanswerable_explicit_risk(data):
    e = engine(data, targets={'unanswerable': 1})
    r = e.consider({'question': '装维人员申请差旅报销时需要提供哪些发票？', 'category': '财务与报销', 'assumed_out_of_scope': '财务规则超出设备操作范围'}, 'unanswerable', 1, 1, [])
    assert r['status'] == 'accepted'
    assert r['case']['answerability_verification'] == 'not_semantically_verified'
    assert 'human_review' not in r['case']


def test_resume_and_repeated_build(data, tmp_path):
    m = api(); store = m.Store(tmp_path)
    start = m.make_start(engine(data), 1)
    store.append(start)  # Simulate exit during model call.
    e = engine(data); assert m.replay(store, e) == 1
    start2 = m.make_start(e, 2); store.append(start2)
    decision = e.consider(data[1], 'procedure', 2, start2['seed'], start2['packet_chunk_ids'])
    store.append({'event': 'result', 'batch': 2, 'candidates': [data[1]], 'decisions': [decision]})
    fresh = engine(data); assert m.replay(m.Store(tmp_path), fresh) == 2
    assert fresh.rows == e.rows
    store.project(); raw = (tmp_path / 'silver_topup_raw.jsonl').read_bytes(); store.project()
    assert raw == (tmp_path / 'silver_topup_raw.jsonl').read_bytes()
    payload = m.encode_rows(fresh.rows)
    m.immutable_write(tmp_path / 'silver_cases_500.jsonl', payload)
    m.immutable_write(tmp_path / 'silver_cases_500.jsonl', payload)
    with pytest.raises(ValueError, match='conflict'): m.immutable_write(tmp_path / 'silver_cases_500.jsonl', b'changed')


def test_tampered_journal_rejected(data, tmp_path):
    m = api(); s = m.Store(tmp_path)
    s.append(m.make_start(engine(data), 1))
    s.append({'event':'result', 'batch':1, 'candidates':[data[1]], 'decisions':[]})
    with pytest.raises(ValueError, match='decision'): m.replay(s, engine(data))


@pytest.mark.parametrize('field', ['options', 'seed', 'corpus_sha256', 'prompt_sha256', 'prompt', 'topup_version'])
def test_inconsistent_inference_provenance_rejected(data, tmp_path, field):
    m=api(); e=engine(data); start=m.make_start(e,1)
    if field=='options': start[field]={**start[field], 'temperature':999}
    elif field=='seed': start[field]+=1
    else: start[field]='wrong'
    s=m.Store(tmp_path);s.append(start)
    with pytest.raises(ValueError,match='provenance'): m.replay(s,engine(data))


def test_baseline_466_unchanged_and_final_500():
    m = api(); baseline, corpus, gold, digest = m.load_inputs()
    before = copy.deepcopy(baseline)
    e = m.Engine(baseline, corpus, gold, m.g.TARGETS, digest)
    assert e.rows == before and len(e.rows) == 466
    assert e.remaining() == {'exact_fact':20,'procedure':4,'multi_condition':1,'colloquial':0,'unanswerable':9}
    report = m.validate(e, baseline)
    assert report['status'] == 'failed' and 'total_not_500' in report['errors']
    assert baseline == before


def test_exhaustion_is_explicit(data, tmp_path):
    m = api(); e = engine(data)
    report = m.summarize(m.Store(tmp_path), e, max_batches=0)
    assert report['status'] == 'exhausted'
    assert report['shortfall'] == {'procedure':1}


def test_exhausted_generation_does_not_call_model(data, tmp_path, monkeypatch):
    m = api()
    def forbidden(*args, **kwargs):
        raise AssertionError('exhausted run must not call model')
    monkeypatch.setattr(m.g, 'LocalOllama', forbidden)
    e = engine(data); store = m.Store(tmp_path)
    m.generate(store, e, max_batches=0, timeout=1)
    assert not store.events() and len(e.rows) == 0


def test_second_duplicate_rule_retained(data):
    e = engine(data, targets={'procedure':2})
    assert e.consider(data[1], 'procedure', 1, 1, ['a'])['status'] == 'accepted'
    raw = copy.deepcopy(data[1]); raw['question'] = '施工结束之后应该如何检查接地连接？'
    assert e.consider(raw, 'procedure', 2, 2, ['a'])['reason'] == 'duplicate_evidence_answer'


def test_incomplete_build_exit_and_reports(tmp_path, monkeypatch):
    m = api()
    for name in ['silver_baseline_sha256.json','silver_cases.jsonl','generation_summary.json']:
        (tmp_path/name).write_bytes((HERE/name).read_bytes())
    monkeypatch.setattr(m, 'HERE', tmp_path)
    monkeypatch.setattr(m.os.sys, 'argv', ['topup_silver.py','--build','--max-batches','0'])
    assert m.main() == 3
    assert not (tmp_path/'silver_cases_500.jsonl').exists()
    summary=json.loads((tmp_path/'silver_topup_summary.json').read_text(encoding='utf-8'))
    validation=json.loads((tmp_path/'silver_500_validation.json').read_text(encoding='utf-8'))
    assert summary['status']=='exhausted' and summary['new_accepted']==0
    assert validation['status']=='failed' and validation['final_sha256'] is None


def test_changed_baseline_hash_stops(tmp_path, monkeypatch):
    m = api()
    manifest=json.loads((HERE/'silver_baseline_sha256.json').read_text(encoding='utf-8'))
    manifest['sha256'][str(tmp_path/'changed.jsonl')]='0'*64
    (tmp_path/'changed.jsonl').write_bytes(b'tampered')
    (tmp_path/'silver_baseline_sha256.json').write_text(json.dumps(manifest),encoding='utf-8')
    monkeypatch.setattr(m,'HERE',tmp_path)
    with pytest.raises(ValueError,match='baseline hash mismatch'):m.load_inputs()


def test_concurrent_writers_refused(tmp_path):
    m=api()
    with m.writer_lock(tmp_path):
        with pytest.raises(ValueError,match='another topup writer'):
            with m.writer_lock(tmp_path): pass


def test_semantic_rejection_is_audited_and_restores_quota(data,tmp_path):
    m=api(); e=engine(data); store=m.Store(tmp_path); start=m.make_start(e,1)
    store.append(start)
    accepted=e.consider(data[1],start['kind'],1,start['seed'],start['packet_chunk_ids'])
    store.append({'event':'result','batch':1,'candidates':[data[1]],'decisions':[accepted]})
    final=tmp_path/'silver_cases_500.jsonl'; payload=m.encode_rows(e.rows)
    final.write_bytes(payload)
    m.quarantine_last(store,e,'p6s-0001','unsupported_condition')
    assert e.remaining()=={'procedure':1} and not final.exists()
    assert list((tmp_path/'topup_quarantine').glob('*.jsonl'))[0].read_bytes()==payload
    fresh=engine(data);m.replay(store,fresh)
    assert fresh.rows==[]
    report=m.summarize(store,fresh,200)
    assert report['new_accepted']==0 and report['rejections']['semantic_review:unsupported_condition']==1


def test_baseline_cannot_be_quarantined(data,tmp_path):
    m=api(); row=engine(data).consider(data[1],'procedure',1,1,['a'])['case']
    e=engine(data,baseline=[row],targets={'procedure':2})
    with pytest.raises(ValueError,match='baseline'):m.quarantine_last(m.Store(tmp_path),e,row['case_id'],'bad')


def test_quarantine_recovers_after_archive_interruption(data,tmp_path,monkeypatch):
    m=api(); e=engine(data); store=m.Store(tmp_path); start=m.make_start(e,1)
    store.append(start)
    accepted=e.consider(data[1],start['kind'],1,start['seed'],start['packet_chunk_ids'])
    store.append({'event':'result','batch':1,'candidates':[data[1]],'decisions':[accepted]})
    final=tmp_path/'silver_cases_500.jsonl';payload=m.encode_rows(e.rows);final.write_bytes(payload)
    reconcile=m.reconcile_quarantine
    def disk_error(store):raise OSError('simulated interrupted archive')
    monkeypatch.setattr(m,'reconcile_quarantine',disk_error)
    with pytest.raises(OSError):m.quarantine_last(store,e,'p6s-0001','unsupported_condition')
    fresh=engine(data);m.replay(store,fresh)
    assert fresh.rows==[] and final.exists()
    reconcile(store)
    assert not final.exists()
    assert list((tmp_path/'topup_quarantine').glob('*.jsonl'))[0].read_bytes()==payload


def test_reject_new_case_preserves_other_ids_and_fills_vacancy(data):
    m=api(); e=engine(data,targets={'procedure':3})
    first=e.consider(data[1],'procedure',1,1,['a'])['case']
    raw2={'question':'告警恢复以后应当向哪些人员通知处理结果？','answer':'登记处理结果并通知相关负责人安排复查。','evidence':[{'passage_id':'b','excerpt':data[0][1]['chunk_text']}]}
    second=e.consider(raw2,'procedure',2,2,['b'])['case']
    raw3=copy.deepcopy(data[1]);raw3['question']='巡检人员需要怎样确认线路状态？';raw3['answer']='确认接地连接牢固可靠。'
    third=e.consider(raw3,'procedure',3,3,['a'])['case']
    e.reject_case(second)
    assert e.rows==[first,third]
    assert e.consider(raw2,'procedure',4,4,['b'])['reason']=='previous_semantic_rejection'
    raw4=copy.deepcopy(data[1]);raw4['question']='线路施工结束后需核验哪些安全事项？';raw4['answer']='应进行线路检查。'
    replacement=e.consider(raw4,'procedure',5,5,['a'])['case']
    assert replacement['case_id']=='p6s-0002'
    assert e.rows[0]==first and e.rows[2]==third


def test_final_real_artifact_when_present():
    m = api(); path = HERE / 'silver_cases_500.jsonl'
    if not path.exists(): pytest.skip('Real local generation not yet complete')
    baseline, corpus, gold, digest = m.load_inputs()
    e = m.Engine(baseline, corpus, gold, m.g.TARGETS, digest)
    m.replay(m.Store(HERE), e)
    assert len(e.rows) == 500
    assert Counter(r['question_type'] for r in e.rows) == m.g.TARGETS
    assert e.rows[:466] == baseline
    assert m.validate(e, baseline)['status'] == 'passed'
    assert path.read_bytes() == (HERE/'silver_cases.jsonl').read_bytes() + m.encode_rows(e.rows[466:])
