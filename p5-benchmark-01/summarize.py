"""Independent audit of archived ranks; never calls retrieval or changes parameters."""
import csv,hashlib,json,math,statistics
from datetime import datetime, timezone, timedelta
from pathlib import Path
P=Path(__file__).resolve().parent
R=P.parent
M=['bm25_only','vector_only','hybrid','hybrid_rerank']
KEYS=['hit@1','hit@3','hit@5','hit@10','mrr@10','ndcg@10','recall@10','latency_p50_ms','latency_p95_ms']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def lines(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s.strip()]
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pct(v,q):
    v=sorted(v);pos=(len(v)-1)*q;i=int(pos);return v[i]+(v[min(i+1,len(v)-1)]-v[i])*(pos-i)
def recompute(row):
    ids=list(dict.fromkeys(row['ranked_chunk_ids']));rel=set(row['relevant_chunk_ids']);ranks=[i+1 for i,c in enumerate(ids[:10]) if c in rel]
    dcg=sum(1/math.log2(i+1) for i in ranks);ideal=sum(1/math.log2(i+1) for i in range(1,min(len(rel),10)+1))
    return {**{f'hit@{k}':int(bool(set(ids[:k])&rel)) for k in [1,3,5,10]},'mrr@10':1/min(ranks) if ranks else 0,'ndcg@10':dcg/ideal,'recall@10':len(set(ids[:10])&rel)/len(rel)}
def main():
    runs={n:lines(P/'runs'/n/'rankings.jsonl') for n in ['run1','run2']}
    allmetrics={};audit={}
    for n,rows in runs.items():
        assert read(P/'runs'/n/'complete.json')['ok']
        assert len(rows)==112 and {r['method'] for r in rows}==set(M)
        calc={}
        for m in M:
            subset=[r for r in rows if r['method']==m];assert len(subset)==28 and len({r['gold_case_id'] for r in subset})==28
            vals=[recompute(r) for r in subset]
            calc[m]={k:sum(v[k] for v in vals)/28 for k in vals[0]}
            lat=[r['metrics']['retrieval_latency_ms'] for r in subset]
            calc[m].update(latency_p50_ms=pct(lat,.5),latency_p95_ms=pct(lat,.95))
            saved=read(P/'runs'/n/'metrics.json')['metrics'][m]
            for k,v in calc[m].items():assert abs(saved[k]-v)<(.0011 if k.startswith('latency') else .0000011),(n,m,k,saved[k],v)
        allmetrics[n]=calc
        calls=read(P/'runs'/n/'rerank_inputs_scores.json');assert len(calls)==29
        byquery={r['query']:{s['method']:s for s in rows if s['query']==r['query']} for r in rows}
        for call in calls:
            if call['query'] not in byquery:continue
            c=byquery[call['query']]['hybrid'];d=byquery[call['query']]['hybrid_rerank']
            assert [x['chunk_id'] for x in call['inputs']]==c['ranked_chunk_ids']
            assert call['output_ids']==d['ranked_chunk_ids']
        audit[n]={'records':112,'denominator_per_method':28,'independent_metrics_match':True,'rerank_inputs_match_hybrid':True}
    identity=lambda rows:{(r['method'],r['gold_case_id']):(r['ranked_chunk_ids'],r['results']) for r in rows}
    assert identity(runs['run1'])==identity(runs['run2']),'Rank or rounded score mismatch; report discrepancy without tuning'
    audit['repeatability']={'all_112_rankings_and_scores_equal':True,'quality_metrics_equal':all(allmetrics['run1'][m][k]==allmetrics['run2'][m][k] for m in M for k in KEYS[:7]),'precision':'scores archived to six decimals by original evaluator','latencies_expected_equal':False}
    write(P/'verification.json',audit)
    metrics=allmetrics['run1'];write(P/'four_group_results.json',allmetrics)
    with (P/'metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['run','method','denominator']+KEYS);w.writeheader()
        for n,calc in allmetrics.items():
            for m,v in calc.items():w.writerow(dict(run=n,method=m,denominator=28,**v))
    deltas={}
    for m in M:
        for base in M[:2]+(['hybrid'] if m=='hybrid_rerank' else []):
            if m==base:continue
            deltas[m+'_vs_'+base]={k:{'absolute':metrics[m][k]-metrics[base][k],'relative_percent':(metrics[m][k]/metrics[base][k]-1)*100 if metrics[base][k] else None} for k in KEYS}
    write(P/'deltas.json',deltas)
    cases={r['gold_case_id']:{s['method']:s for s in runs['run1'] if s['gold_case_id']==r['gold_case_id']} for r in runs['run1']}
    with (P/'per_query.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['batch_id','gold_case_id','query','method','relevant_chunk_ids','all_relevant_ranks','first_relevant_rank_at_10','required_evidence_complete_at_10']+KEYS[:7]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for rows in cases.values():
            for m,r in rows.items():
                ids=r['ranked_chunk_ids'];rel=r['relevant_chunk_ids'];required=r.get('required_evidence_chunk_ids',[])
                w.writerow(dict(batch_id=r['batch_id'],gold_case_id=r['gold_case_id'],query=r['query'],method=m,relevant_chunk_ids=json.dumps(rel),all_relevant_ranks=json.dumps({c:ids.index(c)+1 if c in ids else None for c in rel}),first_relevant_rank_at_10=r['metrics']['first_relevant_rank'],required_evidence_complete_at_10=set(required)<=set(ids[:10]) if required else '',**recompute(r)))
    failures=['# 失败与排序下降案例\n','按固定标签审计，未据此修改模型、标签或参数。Top10未命中与Top1未命中分别呈现；以下原因描述仅基于排序现象，不做未经实验的因果归因。\n','主要失败：BM25的B54相关Chunk在第15位，属于Top10截断未命中；P4-N01从Hybrid第1位被重排到第13位，说明此次漏出Top10由重排排序产生。按Top10首相关名次比较，重排5题改善、10题下降、13题不变；截断外名次统一按未命中处理。\n']
    for rows in cases.values():
        ranks={m:r['metrics']['first_relevant_rank'] for m,r in rows.items()}
        if any(v!=1 for v in ranks.values()):
            r=rows['hybrid'];failures.extend([f"## {r['batch_id']}\n",r['query']+'\n',f'首相关Top10名次（null表示未命中）：`{json.dumps(ranks)}`\n',f"相关Chunk：`{r['relevant_chunk_ids']}`。Hybrid首位：`{r['ranked_chunk_ids'][:1]}`；重排首位：`{rows['hybrid_rerank']['ranked_chunk_ids'][:1]}`。\n"])
            c=ranks['hybrid'];d=ranks['hybrid_rerank']
            if (d or 999)>(c or 999):failures.append('重排使首相关名次下降；其输入已经包含相关候选时，属于本配置下的排序负收益，不能归因于候选未召回。\n')
            if c is None:failures.append('Hybrid Top10未命中；完整Top20记录可区分截断外相关项与候选缺失，不能仅凭此断言语料缺失。\n')
    (P/'failure_analysis.md').write_text('\n'.join(failures),encoding='utf-8')
    table=['| 方法 | Hit@1 | Hit@3 | Hit@5 | Hit@10 | MRR@10 | NDCG@10 | Recall@10 | p50 ms | p95 ms |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for m in M:table.append('| '+m+' | '+' | '.join(f'{metrics[m][k]:.6f}' if not k.startswith('latency') else f'{metrics[m][k]:.1f}' for k in KEYS)+' |')
    summary=['# P5-Benchmark-01 正式 Holdout Benchmark\n','2026-11-05（Asia/Shanghai）。Gold总数50；Development 22；正式Holdout 28。以下全部正式指标仅基于28条Holdout，各组分母均为28。Development未混入分母。\n','样本量较小，结果仅代表当前3份PDF、447个冻结Chunk和评测任务分布；不能外推到生产查询总体或答案生成质量。\n','## 正式指标\n','run1为事前指定报告运行；run2仅做一致性验证，112条排序和六位小数分数全部一致，质量指标一致。\n',*table,'\n## 对照变化\n','绝对变化 = 候选指标−基线指标；相对变化百分比 = (候选指标−基线指标)/基线指标×100%。Hit绝对变化乘100为百分点。全部指标及延迟的对照值见 deltas.json；延迟变化不是质量提升。\n']
    for m,base in [('hybrid','bm25_only'),('hybrid','vector_only'),('hybrid_rerank','hybrid')]:
        d=deltas[m+'_vs_'+base]['mrr@10'];summary.append(f"- {m} 相比 {base}：MRR@10 {metrics[base]['mrr@10']:.6f}→{metrics[m]['mrr@10']:.6f}，绝对变化{d['absolute']:+.6f}，相对变化{d['relative_percent']:+.2f}%。")
    winner=max(M[:3],key=lambda m:metrics[m]['mrr@10']);d=metrics['hybrid_rerank']['mrr@10']-metrics['hybrid']['mrr@10']
    summary.extend(['\n## 判断与简历核实\n',f'BM25、Vector、Hybrid中按MRR@10最好的是 {winner}。各指标可能有不同排序，应同时读取上表。CrossEncoder相对Hybrid的MRR变化为{d:+.6f}，'+('呈改善。' if d>0 else '没有带来MRR改善。')+'不能将重排默认表述为有效提升。\n','MRR@10、Hit@K、NDCG@10可作为限定语料、标签和配置下的可审计离线项目结果；没有总体显著性或生产效果证明。\n','既有简历MRR 0.51→0.69未得到本实验复现支持。当前固定四组没有重现这对基线/改进值，旧数字的原始数据、配置及定义没有在本次提供可核验证据；不能把本次高低不同的成绩解释成旧数字已复现。\n',f"可替代描述：在3份PDF、447个冻结Chunk、人工签核的28条Holdout上，对比BM25、向量、混合及CrossEncoder重排；BM25/Vector/Hybrid的MRR@10分别为{metrics['bm25_only']['mrr@10']:.4f}/{metrics['vector_only']['mrr@10']:.4f}/{metrics['hybrid']['mrr@10']:.4f}，Hybrid Hit@10为{metrics['hybrid']['hit@10']:.2%}；重排MRR@10为{metrics['hybrid_rerank']['mrr@10']:.4f}，保留真实收益方向。\n",'## 指标、环境与审计\n','Hit@K为至少一个相关Chunk命中；MRR@10为Top10首相关名次倒数；NDCG@10使用二元相关与min(相关数,10)的理想排序；Recall@10逐题相关集合召回率再宏平均。多证据完整性另计，不能用Hit替代。\n','每组28次检索，延迟p50/p95线性插值；CPU、预热后串行，D含检索及重排，均不含Embedding/初始化。存在固定执行顺序和缓存影响，仅作描述性本机结果。\n'])
    for n in runs:
        cfg=read(P/'runs'/n/'run_config.json')
        local=lambda t:datetime.fromisoformat(t).astimezone(timezone(timedelta(hours=8))).isoformat()
        summary.append(f"- {n}：{local(cfg['started_at'])} 至 {local(cfg['finished_at'])}（Asia/Shanghai），runner wall_seconds={cfg['wall_seconds']}。")
    summary.append('\n本Holdout的requires_all_evidence题数为0，不能据此证明多证据完整性能力。主要漏出Top10案例：B54在BM25第15；P4-N01从Hybrid第1被重排到第13。重排5题改善、10题下降、13题不变。\n')
    summary.append('环境详表与本地模型文件哈希见environment_details.json；447条实际数据库向量另存database_vectors.json。历史P3未归档数据库向量哈希，因此不能额外证明远端Embedding内部权重或历史数据库向量逐位一致；已验证的是代码、配置、依赖、冻结正文与本次重复排序。两轮wall_seconds包含初始化、预热与查询向量阶段，不含进程启动及前置gate开销。\n')
    summary.extend(['\n配置/模型版本见 preregistered_config.json；代码版本含Git HEAD及未提交实现哈希，不能只用HEAD代表P3修复。完整依赖见 dependencies.txt。Embedding提供商未暴露不可变权重版本，记录text-embedding-v4别名及精确缓存向量哈希；本地CrossEncoder使用固定HF快照。\n','预检通过冻结哈希、28条人工签核回执、Development去重、相关Chunk存在性、数据库447条ID/正文等价、P3实现哈希与依赖版本一致性。适配器早期格式错误已在正式运行前修正；沙箱连接限制经审批后完成预检。外发28条查询经用户明确授权后执行。\n','主证据：runs/run1/rankings.jsonl（112条完整Top20排序、相关命中、分项延迟）；per_query.csv（每个相关Chunk名次或null）；runs/*/rerank_inputs_scores.json（实际重排输入/分数）；four_group_results.json；verification.json；sha256_manifest.json。复现命令见 reproduction.md。\n','未修改冻结Gold、语料、生产算法或检索参数；未commit/push。到此停止，不继续优化实验。'])
    report='\n'.join(summary);(P/'report.md').write_text(report,encoding='utf-8')
    (P/'resume_verification.md').write_text('# 简历指标核实\n\n'+'\n'.join(summary[summary.index('\n## 判断与简历核实\n')+1:summary.index('## 指标、环境与审计\n')])+'\n正式分母仅28条；Gold总数50，Development22。样本小，仅适用于当前冻结语料与任务分布。',encoding='utf-8')
    write(P/'sha256_manifest.json',{str(p.relative_to(P)):digest(p) for p in sorted(P.rglob('*')) if p.is_file() and p.name!='sha256_manifest.json'})
    print('\n'.join(table));print('AUDIT PASS: independent metrics, all 112 ranks/scores repeat identically')
if __name__=='__main__':main()
