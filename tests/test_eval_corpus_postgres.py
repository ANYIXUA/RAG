"""Opt-in integration: current checkout code, existing PostgreSQL, SELECT only.

Set RAG_TEST_POSTGRES_DSN and RAG_TEST_EVAL_COLLECTION/TENANT/TAGS explicitly.
No table/extension/index/fixture data is created. Synthetic SQL fixtures use CTEs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_app.core.config import Settings
from rag_app.eval_dataset.corpus import (
    _BODIES_SQL, _connect_readonly, export_active_chunks, load_corpus_snapshot,
)
from rag_app.eval_dataset.schemas import CorpusScope


_LIVE = all(os.getenv(key) for key in (
    "RAG_TEST_POSTGRES_DSN", "RAG_TEST_EVAL_COLLECTION",
    "RAG_TEST_EVAL_TENANT", "RAG_TEST_EVAL_TAGS",
))


@unittest.skipUnless(_LIVE, "Explicit existing read-only PostgreSQL test scope not configured")
class CorpusPostgresTest(unittest.TestCase):
    def setUp(self):
        self.dsn = os.environ["RAG_TEST_POSTGRES_DSN"]
        self.scope = CorpusScope(
            os.environ["RAG_TEST_EVAL_COLLECTION"], os.environ["RAG_TEST_EVAL_TENANT"],
            tuple(os.environ["RAG_TEST_EVAL_TAGS"].split(",")),
        )
        with patch.dict(os.environ, {"RAG_OPS_POSTGRES_DSN": self.dsn}):
            self.settings = Settings.from_env()
        self.assertEqual(self.settings.collection_name, self.scope.collection_name)

    def connect(self):
        c = _connect_readonly(
            self.dsn, autocommit=True,
            options="-c default_transaction_read_only=on -c statement_timeout=30000",
        )
        self.addCleanup(c.close)
        c.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        self.assertEqual(c.execute("SHOW transaction_read_only").fetchone()["transaction_read_only"], "on")
        return c

    def fingerprint(self):
        c = self.connect()
        result = {}
        for table in ("rag_documents", "rag_knowledge_chunks"):
            # Identifiers are this fixed allowlist, never environment/input values.
            result[table] = c.execute(
                "SELECT count(*) AS count, md5(string_agg(md5(to_jsonb(t)::text), ',' ORDER BY id)) AS hash "
                f"FROM public.{table} t WHERE collection_name=%s AND metadata->>'tenant_id'=%s",
                (self.scope.collection_name, self.scope.tenant_id),
            ).fetchone()
        for table in ("knowledge_active_versions", "knowledge_versions"):
            exists = c.execute("SELECT to_regclass(%s) AS name", ("public." + table,)).fetchone()["name"]
            if exists:
                result[table] = c.execute(
                    "SELECT count(*) AS count, md5(string_agg(md5(to_jsonb(t)::text), ',' ORDER BY to_jsonb(t)::text)) AS hash "
                    f"FROM public.{table} t"
                ).fetchone()
        c.execute("ROLLBACK")
        return result

    def test_current_checkout_exports_repeatably_without_changing_database(self):
        before = self.fingerprint()
        with TemporaryDirectory() as temp:
            first = export_active_chunks(self.settings, self.scope, Path(temp) / "one")
            second = export_active_chunks(self.settings, self.scope, Path(temp) / "two")
            manifest, rows = load_corpus_snapshot(first.manifest_path, expected_scope=self.scope)
            self.assertGreater(len(rows), 0)
            self.assertEqual(first.snapshot_id, second.snapshot_id)
            self.assertEqual(first.corpus_path.read_bytes(), second.corpus_path.read_bytes())
            expected_root = Path(__file__).resolve().parents[1] / "rag_app"
            self.assertEqual(Path(manifest["code_provenance"]["package_root"]), expected_root)
            self.assertTrue(all(r["tenant_id"] == self.scope.tenant_id for r in rows))
            self.assertTrue(all(set(r["permission_tags"]) & set(self.scope.permission_tags) for r in rows))
        self.assertEqual(before, self.fingerprint())

    def test_real_sql_filters_other_tenant_tags_inactive_or_missing_documents(self):
        c = self.connect()
        metadata = lambda tenant, tags: json.dumps({"tenant_id": tenant, "permission_tags": tags})
        chunks = [
            {"collection_name": "fixture", "chunk_id": key, "document_id": doc,
             "chunk_text": "fixture", "version": 1, "status": status,
             "metadata": json.loads(metadata(tenant, tags))}
            for key, doc, tenant, tags, status in (
                ("allowed", "d1", "tenant-a", ["public"], "active"),
                ("private", "d2", "tenant-a", ["ops"], "active"),
                ("other-tenant", "d3", "tenant-b", ["public"], "active"),
                ("inactive", "d1", "tenant-a", ["public"], "inactive"),
                ("missing-doc", "absent", "tenant-a", ["public"], "active"),
                ("bad-tags", "d1", "tenant-a", "public", "active"),
                ("inactive-doc", "d4", "tenant-a", ["public"], "active"),
                ("doc-tenant-mismatch", "d3", "tenant-a", ["public"], "active"),
                ("doc-tag-mismatch", "d2", "tenant-a", ["public"], "active"),
            )
        ]
        documents = [
            {"collection_name": "fixture", "document_id": key, "status": status,
             "source_name": "fixture.txt", "content_hash": "a" * 64,
             "metadata": json.loads(metadata(tenant, tags))}
            for key, tenant, tags, status in (
                ("d1", "tenant-a", ["public"], "active"),
                ("d2", "tenant-a", ["ops"], "active"),
                ("d3", "tenant-b", ["public"], "active"),
                ("d4", "tenant-a", ["public"], "inactive"),
            )
        ]
        cte = """
WITH fixture_chunks AS (
  SELECT * FROM jsonb_to_recordset(%s::jsonb) AS x(
    collection_name text,chunk_id text,document_id text,chunk_text text,
    version int,status text,metadata jsonb,error_code text)
), fixture_documents AS (
  SELECT * FROM jsonb_to_recordset(%s::jsonb) AS x(
    collection_name text,document_id text,status text,source_name text,
    content_hash text,metadata jsonb)
)
"""
        query = _BODIES_SQL.replace("public.rag_knowledge_chunks", "fixture_chunks").replace(
            "public.rag_documents", "fixture_documents"
        )
        rows = c.execute(cte + query, (
            json.dumps(chunks), json.dumps(documents), "fixture", "tenant-a", "tenant-a",
            ["public"], ["public"], [r["chunk_id"] for r in chunks],
        )).fetchall()
        self.assertEqual([r["chunk_id"] for r in rows], ["allowed"])
        c.execute("ROLLBACK")


if __name__ == "__main__":
    unittest.main()
