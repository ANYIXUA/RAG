"""Generate tables from actual saved runs; never edit queries or relevance labels."""
import csv
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / 'p3-pilot-02'
sys.path.insert(0, str(ROOT / 'p3-pilot-01'))
import run_pilot as rp


def load(path): return json.loads(path.read_text(encoding='utf-8'))


def rankings(name):
    return {(r['batch_id'], r['method']): r for r in map(json.loads,
        (HERE / 'runs' / name / 'rankings.jsonl').read_text(encoding='utf-8').splitlines())}


def main():
    before, fixed = rankings('before'), rankings('fixed2')
    cases, _ = rp.load_gold()
    bm, fm = [load(HERE / 'runs' / name / 'metrics.json') for name in ['before', 'fixed2']]
    metrics = []
    for scenario, block in [('before', bm), ('fixed', fm)]:
        for method, values in {**block['metrics'], **block['supplementary_metrics']}.items():
            metrics.append({'scenario': scenario, 'method': method,
                            **{k: values[k] for k in ['hit@1','hit@3','hit@5','hit@10','mrr@10',
                                'ndcg@10','recall@10','latency_p50_ms','latency_p95_ms']}})
    per_query = []
    for case in cases:
        bid = case['batch_id']
        row = {'batch_id': bid, 'gold_case_id': case['gold_case_id'], 'query': case['query']}
        for prefix, data in [('before', before), ('fixed', fixed)]:
            for method in ['bm25_only', 'vector_only', 'hybrid', 'hybrid_rerank', 'bm25_full_corpus']:
                record = data[bid, method]
                row[f'{prefix}_{method}_rank_at10'] = record['metrics']['first_relevant_rank']
                row[f'{prefix}_{method}_all_relevant_ranks'] = record['relevant_ranks']
        per_query.append(row)
    (HERE / 'runs/per_query.json').write_text(json.dumps(per_query, ensure_ascii=False, indent=2), encoding='utf-8')
    for name, rows in [('metrics', metrics), ('per_query', per_query)]:
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        (HERE / f'{name}.csv').write_text(stream.getvalue(), encoding='utf-8-sig')
    lines = ['| 运行 | 方法 | Hit@1 | Hit@10 | MRR@10 | NDCG@10 | Recall@10 | p50 ms | p95 ms |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for row in metrics:
        lines.append('| ' + ' | '.join([row['scenario'], row['method']] +
            [f'{row[k]:.6f}' for k in ['hit@1','hit@10','mrr@10','ndcg@10','recall@10']] +
            [f'{row[k]:.1f}' for k in ['latency_p50_ms','latency_p95_ms']]) + ' |')
    lines += ['', '名次为首个相关 Chunk 在 Top10 内的名次；— 表示 Top10 未命中。完整 Top20、多相关名次与原始分数见 runs/*/rankings.jsonl 和 runs/per_query.json。', '',
              '| 题号 | BM25 前 | BM25 后 | 全库诊断 | Hybrid 前 | Rerank 前 | Hybrid 后 | Rerank 后 |',
              '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    columns = ['before_bm25_only_rank_at10','fixed_bm25_only_rank_at10','fixed_bm25_full_corpus_rank_at10',
               'before_hybrid_rank_at10','before_hybrid_rerank_rank_at10','fixed_hybrid_rank_at10','fixed_hybrid_rerank_rank_at10']
    for row in per_query:
        lines.append('| ' + ' | '.join([row['batch_id']] + [str(row[k]) if row[k] else '—' for k in columns]) + ' |')
    (HERE / 'tables.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    config = load(ROOT / 'p3-pilot-01/pilot_config.json')
    config['pilot'] = 'P3-Pilot-02'
    config['retrieval']['candidate_pool_before'] = config['retrieval'].pop('candidate_pool')
    config['retrieval']['candidate_pool'] = 'all unique query tokens ILIKE OR without early LIMIT; existing authorization then BM25 Top20; union with semantic Top20 for hybrid'
    config['retrieval']['fusion_parameters']['normalized_by'] = 'BM25 / maximum BM25 over authorized merged input records; original normalization implementation unchanged'
    config['reporting_run'] = 'fixed2 (fixed1 encountered diagnostic read-transaction / concurrent initialization DDL lock waiting; fixed2 runs without concurrent probes)'
    config['implementation'] = {name: load(HERE / 'runs' / name / 'comparison_metadata.json')
                                for name in ['before','fixed1','fixed2']}
    config['commands'] = {
        'before': 'python -B p3-pilot-02/run_comparison.py --variant before --out-dir p3-pilot-02/runs/repro-before',
        'fixed': 'python -B p3-pilot-02/run_comparison.py --variant fixed --out-dir p3-pilot-02/runs/repro-fixed1',
        'repeat': 'python -B p3-pilot-02/run_comparison.py --variant fixed --out-dir p3-pilot-02/runs/repro-fixed2',
        'verify': 'python -B p3-pilot-02/verify_runs.py --run-a p3-pilot-02/runs/repro-fixed1 --run-b p3-pilot-02/runs/repro-fixed2 --out p3-pilot-02/runs/repro-repeatability.json',
        'audit': 'python -B p3-pilot-02/audit_rerank.py',
        'summarize': 'python -B p3-pilot-02/summarize.py',
        'tests': 'python -B -m unittest discover -v',
    }
    (HERE / 'experiment_config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Wrote metrics.csv, per_query.csv, runs/per_query.json, tables.md, experiment_config.json')


if __name__ == '__main__': main()
