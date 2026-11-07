"""Verify saved run identity with non-null frozen-input and cache hashes."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'p3-pilot-01'))
import verify_repeatability as original


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-a', required=True, type=Path)
    parser.add_argument('--run-b', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    report = original.compare(args.run_a, args.run_b)
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    a, b = [read(p / 'preflight.json') for p in [args.run_a, args.run_b]]
    expected = read(ROOT / 'p3-pilot-01/pilot_config.json')
    corpus_hash = expected['frozen_inputs']['corpus']['sha256']
    assert corpus_hash and a['corpus']['sha256'] == b['corpus']['sha256'] == corpus_hash
    for p in [a,b]:
        assert p['corpus_database_equivalence']['consistent']
        assert p['corpus_database_equivalence']['database_active_chunks'] == 447
        assert p['gold']['merged_cases'] == 22
    assert report['gold_sources_hash_match']
    assert report['config_fingerprint_run_a'] == report['config_fingerprint_run_b'] == expected['environment']['config_fingerprint']
    for p in [a,b]:
        for key, source in expected['frozen_inputs']['gold_sources'].items():
            assert p['gold']['sources'][key]['sha256'] == source['sha256']
    report['corpus_sha256_run_a'] = a['corpus']['sha256']
    report['corpus_sha256_run_b'] = b['corpus']['sha256']
    meta_paths = [p / 'comparison_metadata.json' for p in [args.run_a, args.run_b]]
    if all(p.exists() for p in meta_paths):
        ma, mb = map(read, meta_paths)
        assert ma['query_vectors_sha256'] == mb['query_vectors_sha256']
        if ma['variant'] == mb['variant']:
            assert ma['implementation_sha256'] == mb['implementation_sha256']
        report['shared_query_vectors_sha256'] = ma['query_vectors_sha256']
    assert report['rankings_identical']
    assert report['metrics_identical_excluding_latency']
    assert report['records_run_a'] == report['records_run_b'] == 110
    # Also compare the supplementary A2 metric block, absent from the original helper's metric loop.
    for field in ['supplementary_metrics']:
        ma, mb = [read(p / 'metrics.json')[field] for p in [args.run_a,args.run_b]]
        clean = lambda d: {name:{k:v for k,v in values.items() if not k.startswith('latency_')}
                           for name,values in d.items()}
        assert clean(ma) == clean(mb)
    report['supplementary_metrics_identical_excluding_latency'] = True
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['rankings_identical','metrics_identical_excluding_latency',
                      'corpus_sha256_run_a','corpus_sha256_run_b','supplementary_metrics_identical_excluding_latency']}, indent=2))


if __name__ == '__main__': main()
