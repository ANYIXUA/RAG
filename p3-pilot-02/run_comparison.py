"""Run the unchanged Pilot-01 evaluator against saved HEAD or the minimal fix.

Caches real query embeddings so every before/after/repeat run shares exact vectors.
Captures actual CrossEncoder inputs/scores without changing inference parameters.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / 'p3-pilot-02'
sys.path.insert(0, str(ROOT / 'p3-pilot-01'))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
import run_pilot as rp


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_inputs():
    protected = json.loads((HERE / 'baseline/input_hashes.json').read_text())
    mismatches = [p for p, h in protected.items() if not Path(p).is_file() or digest(p) != h]
    assert not mismatches, f'Protected input changed: {mismatches}'
    config = json.loads((ROOT / 'p3-pilot-01/pilot_config.json').read_text(encoding='utf-8'))
    assert digest(rp.CORPUS_JSONL) == config['frozen_inputs']['corpus']['sha256']
    for source in config['frozen_inputs']['gold_sources'].values():
        assert digest(source['path']) == source['sha256']
    settings, _ = rp.build_settings()
    assert settings.config_fingerprint == config['environment']['config_fingerprint']
    assert settings.retrieval_candidate_k == 20
    assert (settings.semantic_weight, settings.bm25_weight) == (.7, .3)
    assert (settings.min_similarity_score, settings.relative_score_threshold) == (.05, .35)
    assert settings.rerank_model == config['rerank']['model']
    return len(protected)


def install_embedding_cache():
    import rag_app.indexing.embeddings as embeddings
    original_factory = embeddings.create_embedder
    cache_path = HERE / 'runs/query_vectors.json'
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    def factory(settings):
        delegate = original_factory(settings)
        class CachedEmbedder:
            def __getattr__(self, name): return getattr(delegate, name)
            def embed(self, texts):
                vectors = []
                for text in texts:
                    if text not in cache:
                        cache[text] = delegate.embed([text])[0]
                        cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding='utf-8')
                    vectors.append(cache[text])
                return vectors
        return CachedEmbedder()
    embeddings.create_embedder = factory
    return cache_path


def install_rerank_capture(audits):
    from rag_app.retrieval.rerank import CrossEncoderReranker
    original = CrossEncoderReranker.rerank
    def rerank(self, query, results, top_k):
        predict = self.model.predict
        calls = []
        def capture(pairs, *args, **kwargs):
            assert pairs == [(query, r.chunk.text) for r in results]
            scores = predict(pairs, *args, **kwargs)
            assert len(scores) == len(results)
            calls.extend(float(score) for score in scores)
            return scores
        self.model.predict = capture
        try:
            output = original(self, query, results, top_k)
        finally:
            self.model.predict = predict
        assert len(calls) == len(results)
        expected = sorted(zip(results, calls), key=lambda pair: pair[1], reverse=True)[:top_k]
        assert [r.chunk.id for r in output] == [r.chunk.id for r, _ in expected]
        tokenizer = self.model.tokenizer
        audits.append({
            'query': query, 'top_k': top_k,
            'model_max_length': self.model.max_seq_length,
            'tokenizer_model_max_length': tokenizer.model_max_length,
            'truncation_side': tokenizer.truncation_side,
            'activation': str(self.model.activation_fn),
            'inputs': [{'chunk_id': r.chunk.id, 'query_sha256': rp.sha256_text(query),
                        'chunk_sha256': rp.sha256_text(r.chunk.text), 'score': s}
                       for r, s in zip(results, calls)],
            'output_ids': [r.chunk.id for r in output],
            'pairs_exact': True, 'scores_associated': True, 'descending_then_topk': True,
        })
        print(f'Reranked {len(results)} candidates: {rp.sha256_text(query)[:12]}', flush=True)
        return output
    CrossEncoderReranker.rerank = rerank


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['before', 'fixed'], required=True)
    parser.add_argument('--out-dir', required=True)
    args = parser.parse_args()
    out = Path(args.out_dir)
    assert not (out / 'metrics.json').exists(), 'Choose a new output directory; evidence is immutable'
    count = verify_inputs()
    source = ROOT / 'rag_app/indexing/vector_store.py'
    if args.variant == 'before':
        source = HERE / 'baseline/vector_store_before.py'
        name = 'rag_app.indexing.vector_store'
        spec = importlib.util.spec_from_file_location(name, source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    cache = install_embedding_cache()
    audits = []
    install_rerank_capture(audits)
    code = rp.run(argparse.Namespace(out_dir=str(out), label=f'P3-Pilot-02-{args.variant}',
                                     seed=0, skip_rerank=False))
    assert code == 0
    assert verify_inputs() == count
    preflight = json.loads((out / 'preflight.json').read_text(encoding='utf-8'))
    assert preflight['rerank_status']['available'], preflight['rerank_status']
    (out / 'rerank_inputs_scores.json').write_text(json.dumps(audits, ensure_ascii=False, indent=2), encoding='utf-8')
    metadata = {
        'pilot': 'P3-Pilot-02', 'variant': args.variant,
        'implementation_path': source.relative_to(ROOT).as_posix(),
        'implementation_sha256': digest(source), 'query_vectors_sha256': digest(cache),
        'protected_files_verified_before_and_after': count,
        'candidate_generation': ('original first 12 tokens, priority DESC / updated_at DESC LIMIT 20'
                                 if args.variant == 'before' else
                                 'all unique query tokens ILIKE OR, collection/status unchanged, chunk_id ASC, no early LIMIT; authorization then existing BM25 Top20'),
        'configuration_note': 'run_config.json is the original evaluator configuration; only candidate_generation above differs for fixed runs',
    }
    (out / 'comparison_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
