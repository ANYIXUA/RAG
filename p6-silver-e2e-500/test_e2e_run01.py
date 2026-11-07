import importlib.util
from pathlib import Path

import pytest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('e2e_run01',HERE/'e2e_run01.py')
m=importlib.util.module_from_spec(spec)
if Path(spec.origin).exists():spec.loader.exec_module(m)


def api():
    assert hasattr(m,'Budget'),'Run01 runner is not implemented'
    return m


def test_smoke_covers_five_types():
    a=api();cases=[{'case_id':f'{k}-{i}','question_type':k} for k in ['exact_fact','procedure','multi_condition','colloquial','unanswerable'] for i in range(100)]
    chosen=a.smoke_cases(cases)
    assert len(chosen)==10 and len({c['case_id'] for c in chosen})==10
    assert all(sum(x['question_type']==k for x in chosen)==2 for k in a.TYPES)


def test_unknown_call_usage_remains_charged_on_resume(tmp_path):
    a=api();b=a.Budget(tmp_path,cap=0.01)
    token=b.reserve('chat',{'messages':[{'role':'user','content':'hello'}],'max_tokens':100})
    assert b.committed()>0
    assert a.Budget(tmp_path,cap=0.01).committed()==b.committed()
    assert (tmp_path/'api_calls'/f'{token}.request.json').exists()


def test_budget_blocks_before_network(tmp_path):
    a=api();b=a.Budget(tmp_path,cap=0)
    with pytest.raises(a.BudgetExceeded):b.reserve('chat',{'messages':[],'max_tokens':1})
    assert not list((tmp_path/'api_calls').glob('*.request.json'))


def test_prior_variant_spend_counts_toward_total_cap(tmp_path):
    a=api();(tmp_path/'prior_budget.json').write_bytes(a.jbytes({'conservative_committed_yuan':20}))
    b=a.Budget(tmp_path,cap=20)
    with pytest.raises(a.BudgetExceeded):b.reserve('chat',{'messages':[],'max_tokens':1})


def test_qwen_flash_price_used(tmp_path):
    a=api();b=a.Budget(tmp_path,cap=20)
    token=b.reserve('chat',{'model':'qwen-flash','messages':[],'max_tokens':220})
    b.finish(token,{'model':'qwen-flash','usage':{'prompt_tokens':1000,'completion_tokens':100}},1)
    value=a.read(tmp_path/'api_calls'/f'{token}.response.json')
    assert value['list_price_estimate_yuan']==pytest.approx(.0003)


def test_observer_preserves_kwargs_and_response(tmp_path):
    a=api();b=a.Budget(tmp_path,cap=20);seen=[]
    class Response:
        def model_dump(self,mode='json'):return {'model':'qwen-turbo','usage':{'prompt_tokens':5,'completion_tokens':3},'choices':[{'message':{'content':'ok'},'finish_reason':'stop'}]}
    response=Response()
    def real(**kwargs):seen.append(kwargs);return response
    observer=a.Observer(tmp_path,b);observer.begin('p6s-0001',1)
    wrapped=observer.wrap_create(real,'chat')
    kwargs={'model':'qwen-turbo','messages':[{'role':'user','content':'真实问题'}],'temperature':.2,'max_tokens':220,'timeout':8}
    assert wrapped(**kwargs) is response and seen==[kwargs]
    assert observer.calls[0]['response']['usage']['completion_tokens']==3


def test_fallback_does_not_count_as_real_generation():
    a=api()
    trace={'degradation_reason':'generation_failed: timeout','retrieval_mode':'hybrid'}
    assert a.execution_error(trace,'fallback text',[])=='generation_not_completed'
    assert a.execution_error({'degradation_reason':None,'retrieval_mode':'bm25'},'ok',[{'kind':'chat','response':{'choices':[{'message':{'content':'ok'}}]}}])=='hybrid_degraded'


def test_budget_stop_survives_production_fallback():
    a=api()
    assert a.execution_error({'degradation_reason':'generation_failed: BudgetExceeded','retrieval_mode':'hybrid'},'fallback',[])=='BudgetExceeded'


def test_report_correctness_excludes_ambiguous_and_unanswerable():
    a=api()
    report_spec=importlib.util.spec_from_file_location('e2e_run01_report',HERE/'e2e_run01_report.py')
    assert Path(report_spec.origin).exists(),'reporting module missing'
    report=importlib.util.module_from_spec(report_spec);report_spec.loader.exec_module(report)
    values=[{'score_state':'success','correctness_excluded':False,'answer_correctness':{'score':1}},
            {'score_state':'success','correctness_excluded':True,'answer_correctness':{'score':0}},
            {'score_state':'failed','correctness_excluded':False,'answer_correctness':{'score':1}}]
    assert report.correctness_ratio(values)=={'numerator':1,'denominator':1,'ratio':1}


def test_unanswerable_zero_refusal_not_classified_as_pass():
    a=api();s=importlib.util.spec_from_file_location('report_noanswer',HERE/'e2e_run01_report.py')
    report=importlib.util.module_from_spec(s);s.loader.exec_module(report)
    judged={k:{'score':1} for k in a.DIMENSIONS};judged.update(score_state='success',confidence='high',hallucination_suspected=False)
    judged['no_answer_behavior']['score']=0;judged['answer_correctness']['score']=None
    value=report.diagnostics({'case_id':'x','question_type':'unanswerable'}, {'state':'success','answer':'Some answer','sources':[]}, judged)
    assert value['primary_failure_bucket']=='8_judge_unreliable'
    assert value['unanswerable_provisional']


def test_attempt_number_consumed_after_interruption(tmp_path):
    a=api();d=tmp_path/'attempts'/'p6s-0001'/'01';d.mkdir(parents=True)
    (d/'started.json').write_text('{}')
    assert a.next_attempt(tmp_path,'p6s-0001')==2


def test_durable_success_recovered_before_another_paid_attempt(tmp_path):
    a=api();d=tmp_path/'attempts'/'p6s-0001'/'01';d.mkdir(parents=True)
    value={'case_id':'p6s-0001','state':'success','attempt':1}
    (d/'result.json').write_bytes(a.jbytes(value))
    assert a.recover_case(tmp_path,'p6s-0001')==value
    assert a.read(tmp_path/'cases/p6s-0001.json')==value


def test_judge_attempt_budget_survives_restart(tmp_path):
    a=api();b=a.Budget(tmp_path,20)
    for n in range(1,4):b.reserve('judge',{'messages':[],'max_tokens':1},{'case_id':'p6s-0001','attempt':f'judge-{n}'})
    assert a.next_judge_attempt(tmp_path,'p6s-0001')==4


def test_judge_cannot_override_identity():
    a=api();value={k:{'score':1,'reason':'reason','evidence':'quote'} for k in a.DIMENSIONS}
    value.update(confidence='high',hallucination_suspected=False,flags=[],case_id='evil',score_state='evil')
    result=a.normalize_score({'case_id':'p6s-0001','question_type':'exact_fact'},value)
    assert result['case_id']=='p6s-0001' and result['score_state']=='success'


def test_judge_requires_explicit_scores_and_flags():
    a=api();value={k:{'score':1,'reason':'reason','evidence':'quote'} for k in a.DIMENSIONS}
    value.update(confidence='high',hallucination_suspected=False,flags=[])
    del value['no_answer_behavior']['score']
    with pytest.raises(ValueError):a.validate_judge(value,True)


def test_not_applicable_noanswer_null_evidence_is_not_a_score_failure():
    a=api();value={k:{'score':1,'reason':'reason','evidence':'quote'} for k in a.DIMENSIONS}
    value.update(confidence='high',hallucination_suspected=False,flags=[])
    value['no_answer_behavior']={'score':None,'reason':'Normal answerable question; not applicable','evidence':None}
    validated=a.validate_judge(value,False)
    assert validated['no_answer_behavior']['score'] is None
    assert validated['no_answer_behavior']['evidence']==''


def test_duplicate_final_result_refused(tmp_path):
    a=api();path=tmp_path/'cases'/'p6s-0001.json';a.immutable_write(path,a.jbytes({'case_id':'p6s-0001','state':'success'}))
    a.immutable_write(path,a.jbytes({'case_id':'p6s-0001','state':'success'}))
    with pytest.raises(ValueError):a.immutable_write(path,a.jbytes({'case_id':'p6s-0001','state':'failed'}))


def test_judge_missing_fields_is_score_failure():
    a=api()
    with pytest.raises(ValueError):a.validate_judge({'confidence':'high'},False)


def test_ambiguous_reference_cannot_be_automatic_wrong():
    a=api();judged={k:{'score':0,'reason':'参考不一致','evidence':'114工日'} for k in a.DIMENSIONS}
    judged.update(confidence='high',hallucination_suspected=False,flags=[])
    score=a.normalize_score({'case_id':'p6s-0473','question_type':'exact_fact'},judged)
    assert score['answer_correctness']['score'] is None
    assert score['correctness_excluded'] and score['needs_human_review']


def test_unanswerable_is_provisional():
    a=api();judged={k:{'score':1,'reason':'证据支持','evidence':'未提供'} for k in a.DIMENSIONS}
    judged.update(confidence='medium',hallucination_suspected=False,flags=[])
    score=a.normalize_score({'case_id':'p6s-0001','question_type':'unanswerable'},judged)
    assert score['no_answer_provisional'] and score['correctness_excluded']


def test_percentile_and_ratio_denominators():
    a=api();assert a.percentile([1,2,3,4],.95)==pytest.approx(3.85)
    assert a.ratio(2,4)=={'numerator':2,'denominator':4,'ratio':.5}
    assert a.ratio(0,0)['ratio'] is None
