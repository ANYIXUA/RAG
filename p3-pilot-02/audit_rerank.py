"""Read-only audit of real model inputs, encoding and degraded queries."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'p3-pilot-01'))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import run_pilot as rp
from rag_app.retrieval.rerank import CrossEncoderReranker


def load_rankings(folder):
    return {(r['query'], r['method']): r for r in
            map(json.loads, (folder / 'rankings.jsonl').read_text(encoding='utf-8').splitlines())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--before-run', type=Path, default=ROOT / 'p3-pilot-02/runs/before')
    parser.add_argument('--fixed-run', type=Path, default=ROOT / 'p3-pilot-02/runs/fixed2')
    parser.add_argument('--out', type=Path, default=ROOT / 'p3-pilot-02/runs/rerank_audit.json')
    args = parser.parse_args()
    cases, _ = rp.load_gold()
    corpus, _ = rp.load_corpus()
    by_query = {c['query']: c for c in cases}
    model = CrossEncoderReranker('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1').model
    tokenizer = model.tokenizer
    output = {'model': 'cross-encoder/mmarco-mMiniLMv2-L12-H384-v1',
              'revisions': rp.hf_snapshot_revisions('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1'),
              'max_seq_length': model.max_seq_length, 'truncation_side': tokenizer.truncation_side,
              'activation': str(model.activation_fn), 'scenarios': {}}
    for name, folder in [('before', args.before_run), ('fixed', args.fixed_run)]:
        rankings = load_rankings(folder)
        captures = json.loads((folder / 'rerank_inputs_scores.json').read_text(encoding='utf-8'))
        details = []
        for capture in captures:
            query = capture['query']
            if query not in by_query: continue  # warmup
            case = by_query[query]
            hybrid = rankings[query, 'hybrid']
            rerank = rankings[query, 'hybrid_rerank']
            inputs = capture['inputs']
            ids = [r['chunk_id'] for r in inputs]
            assert ids == hybrid['ranked_chunk_ids']
            assert len(ids) <= 20
            assert sorted(ids) == sorted(rerank['ranked_chunk_ids'])
            assert capture['output_ids'] == rerank['ranked_chunk_ids']
            pairs = [(query, corpus[cid]['chunk_text']) for cid in ids]
            for row, pair in zip(inputs, pairs):
                assert row['query_sha256'] == rp.sha256_text(pair[0])
                assert row['chunk_sha256'] == rp.sha256_text(pair[1])
            # Actual production preprocess, no new inference and no parameter override.
            features = model.preprocess(pairs)
            expected = tokenizer([p[0] for p in pairs], [p[1] for p in pairs],
                                 padding=True, truncation='longest_first',
                                 max_length=model.max_seq_length, return_tensors='pt')
            assert features['input_ids'].tolist() == expected['input_ids'].tolist()
            encoded = []
            for index, ((q, text), row) in enumerate(zip(pairs, inputs)):
                full = tokenizer(q, text, truncation=False)
                clipped = tokenizer(q, text, truncation='longest_first',
                                    max_length=model.max_seq_length, return_offsets_mapping=True)
                offsets = clipped['offset_mapping']
                sequences = clipped.sequence_ids()
                chunk_end = max((offset[1] for offset, seq in zip(offsets, sequences) if seq == 1), default=0)
                query_end = max((offset[1] for offset, seq in zip(offsets, sequences) if seq == 0), default=0)
                evidence = []
                if row['chunk_id'] in case['relevant_chunk_ids']:
                    for target in case['expected']:
                        phrase = target.get('text_contains')
                        if phrase and phrase in text:
                            start = text.index(phrase)
                            evidence.append({'text_contains': phrase, 'start': start,
                                             'end': start+len(phrase),
                                             'fully_retained': start+len(phrase) <= chunk_end})
                encoded.append({**row, 'full_pair_tokens': len(full['input_ids']),
                                'encoded_pair_tokens': int(features['attention_mask'][index].sum()),
                                'truncated': len(full['input_ids']) > model.max_seq_length,
                                'retained_query_char_end': query_end, 'query_chars': len(q),
                                'retained_chunk_char_end': chunk_end, 'chunk_chars': len(text),
                                'evidence_spans': evidence,
                                'hybrid_rank': index+1,
                                'rerank_rank': rerank['ranked_chunk_ids'].index(row['chunk_id'])+1})
            c = hybrid['metrics']['first_relevant_rank']
            d = rerank['metrics']['first_relevant_rank']
            details.append({'batch_id': case['batch_id'], 'gold_case_id': case['gold_case_id'],
                            'query': query, 'hybrid_first_rank_at10': c, 'rerank_first_rank_at10': d,
                            'degraded': (d or 11) > (c or 11),
                            'top_k': capture['top_k'], 'candidate_count': len(ids),
                            'inputs_and_hashes_exact': True, 'same_hybrid_candidate_order': True,
                            'actual_preprocess_matches_default_longest_first': True,
                            'descending_sort_then_topk': capture['descending_then_topk'],
                            'candidates': encoded})
        assert len(details) == 22
        output['scenarios'][name] = details
    target = args.out
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({n: {'cases': len(rows), 'degraded': [r['batch_id'] for r in rows if r['degraded']],
                         'truncated_pairs': sum(c['truncated'] for r in rows for c in r['candidates'])}
                      for n, rows in output['scenarios'].items()}, indent=2))


if __name__ == '__main__': main()
