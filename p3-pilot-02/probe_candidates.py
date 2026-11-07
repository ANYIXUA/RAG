"""Read-only SQL candidate recall evidence; no unthresholded metrics."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'p3-pilot-01'))
sys.path.insert(0, str(ROOT))
import run_pilot as rp
import psycopg
from rag_app.core.text_utils import tokenize_for_keyword_search
from rag_app.indexing.vector_store import PostgresVectorStore


def main():
    settings, dsn = rp.build_settings()
    cases, _ = rp.load_gold()
    # Reading existing schema only; don't initialize/create a separate collection.
    store = object.__new__(PostgresVectorStore)
    store.dsn, store.collection_name = dsn, settings.collection_name
    out = {'cases': [], 'collection': store.collection_name}
    # Avoid holding a read transaction across the store's separate connections.
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT COUNT(*), COUNT(DISTINCT priority), COUNT(DISTINCT updated_at), '
                        'MIN(priority), MAX(priority) FROM rag_knowledge_chunks '
                        "WHERE collection_name=%s AND status='active'", (store.collection_name,))
            out['counts_priority_updated_at'] = cur.fetchone()
            for case in cases:
                tokens = tokenize_for_keyword_search(case['query'])
                predicates = ' OR '.join(['chunk_text ILIKE %s'] * len(tokens[:12]))
                sql = ("SELECT chunk_id FROM rag_knowledge_chunks WHERE collection_name=%s "
                       "AND status='active' AND (" + predicates + ')')
                params = (store.collection_name, *[f'%{t}%' for t in tokens[:12]])
                cur.execute(sql, params)
                all12 = [r[0] for r in cur.fetchall()]
                cur.execute(sql + ' ORDER BY priority DESC, updated_at DESC LIMIT %s', (*params, 20))
                old = [r[0] for r in cur.fetchall()]
                fixed = [r.chunk.id for r in store._query_keyword_candidates(case['query'])]
                rel = set(case['relevant_chunk_ids'])
                out['cases'].append({'batch_id': case['batch_id'], 'query': case['query'],
                                     'token_count': len(tokens), 'first12_match_count': len(all12),
                                     'old_pool_count': len(old), 'old_pool_relevant': sorted(rel.intersection(old)),
                                     'fixed_pool_count': len(fixed), 'fixed_pool_relevant': sorted(rel.intersection(fixed)),
                                     'new_ids_from_late_query_tokens': sorted(set(fixed)-set(all12)),
                                     'old_pool_ids': old, 'fixed_pool_ids': fixed})
    path = ROOT / 'p3-pilot-02/runs/candidate_recall.json'
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'old_cases_with_relevant': sum(bool(r['old_pool_relevant']) for r in out['cases']),
                      'fixed_cases_with_relevant': sum(bool(r['fixed_pool_relevant']) for r in out['cases']),
                      'pool_min_max': [min(r['fixed_pool_count'] for r in out['cases']),
                                       max(r['fixed_pool_count'] for r in out['cases'])]}))


if __name__ == '__main__': main()
