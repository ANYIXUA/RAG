"""Regressions for BM25 recall before candidate_k is applied."""
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from rag_app.core.models import Chunk
from rag_app.indexing.vector_store import PostgresVectorStore, VectorRecord


class KeywordCandidatesTest(unittest.TestCase):
    def store(self):
        store = object.__new__(PostgresVectorStore)
        store.collection_name = 'test-collection'
        store.dsn = 'unused'
        return store

    def test_bm25_scores_all_literal_matches_before_topk_and_authorization(self):
        # Relevant authorized candidate lies beyond BOTH historical 20 and draft 2000.
        noise = [VectorRecord(Chunk(str(i), 'noise', 'common', {}), []) for i in range(2001)]
        records = noise + [
            VectorRecord(Chunk('foreign', 'other', 'needle', {'tenant_id': 'b', 'permission_tags': ['ops']}), []),
            VectorRecord(Chunk('private', 'other', 'needle', {'tenant_id': 'a', 'permission_tags': ['secret']}), []),
            VectorRecord(Chunk('target', 'allowed', 'needle', {'tenant_id': 'a', 'permission_tags': ['ops']}), []),
        ]
        store = self.store()
        # Fake DB models only WHERE (literal OR) / ORDER BY / LIMIT. Scoring is real.
        @contextmanager
        def connect(*args, **kwargs):
            class Cursor:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def execute(self, sql, params):
                    self.rows = records[:params[-1]] if 'LIMIT' in sql.upper() else records
                def fetchall(self): return self.rows
            class Connection:
                def cursor(self): return Cursor()
            yield Connection()
        class Driver:
            pass
        driver = Driver()
        driver.connect = connect
        with patch.object(store, 'count', return_value=len(records)), \
             patch('rag_app.indexing.vector_store._import_psycopg', return_value=(driver, None, None)), \
             patch('rag_app.indexing.vector_store._postgres_chunk_row_to_record', side_effect=lambda row: row):
            results = store.search([], 'common needle', top_k=1, candidate_k=20,
                                   mode='bm25', tenant_id='a', permission_tags=['ops'])
        self.assertEqual([r.chunk.id for r in results], ['target'])

    def test_literal_predicate_includes_discriminating_term_after_token12(self):
        store = self.store()
        captured = []
        @contextmanager
        def connect(*args, **kwargs):
            class Cursor:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def execute(self, sql, params): captured.append((sql, params))
                def fetchall(self): return []
            class Connection:
                def cursor(self): return Cursor()
            yield Connection()
        class Driver: pass
        driver = Driver()
        driver.connect = connect
        with patch.object(store, 'count', return_value=3000), \
             patch('rag_app.indexing.vector_store._import_psycopg', return_value=(driver, None, None)):
            store.search([], 'one two three four five six seven eight nine ten eleven twelve needle',
                         top_k=1, candidate_k=20, mode='bm25')
        sql, params = captured[0]
        self.assertIn('%needle%', params)
        self.assertIn("status = 'active'", sql)
        self.assertIn('collection_name = %s', sql)
        self.assertEqual(params[0], 'test-collection')

    def test_empty_query_returns_no_candidates(self):
        store = self.store()
        with patch.object(store, 'count', return_value=3000), \
             patch('rag_app.indexing.vector_store._import_psycopg') as db:
            self.assertEqual(store.search([], '', mode='bm25'), [])
        db.assert_not_called()
