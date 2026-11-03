"""Read-only corpus export tests; unittest and pytest compatible, no LLM required."""

from __future__ import annotations

import copy
import hashlib
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from rag_app.cli import build_parser, main
from rag_app.eval_dataset.corpus import (
    CorpusExportError,
    export_active_chunks,
    load_corpus_snapshot,
)
from rag_app.eval_dataset.schemas import CorpusScope
from tests.helpers import production_settings


def header(chunk_id="c1", tenant="tenant-a", tags=None):
    tags = ["public"] if tags is None else tags
    return {
        "collection_name": "test", "chunk_id": chunk_id, "document_id": "d1",
        "tenant_id": tenant, "permission_tags": tags,
        "document_tenant_id": tenant, "document_permission_tags": tags,
        "document_status": "active",
    }


def body(chunk_id="c1", text="原始证据 GB/T9254.1\n第二行。", tags=None):
    row = header(chunk_id, tags=tags)
    row.update({
        "chunk_text": text, "chunk_version": 1,
        "document_content_hash": "a" * 64,
        "source_name": "standard.pdf",
        "document_version_id": "v_" + "a" * 16,
        "metadata": {
            "tenant_id": "tenant-a", "permission_tags": row["permission_tags"],
            "source": "standard.pdf", "page_number": 7,
            "version_id": "v_" + "a" * 16,
            "section_title": "标准", "source_path": "private/path.pdf",
            "api_key": "SENSITIVE_METADATA_CANARY", "unknown": "private",
        },
    })
    return row


class FakeDatabase:
    """External I/O substitute; deliberately does not implement SQL filtering."""

    def __init__(self, headers=None, bodies=None, readonly="on", isolation="repeatable read"):
        self.headers = [header()] if headers is None else headers
        self.bodies = [body()] if bodies is None else bodies
        self.readonly = readonly
        self.isolation = isolation
        self.calls = []
        self.closed = False
        self.connection = MagicMock()
        self.connection.execute.side_effect = self.execute
        self.connection.close.side_effect = self.close
        self.connect = MagicMock(return_value=self.connection)

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        result = MagicMock()
        if sql == "SHOW transaction_read_only":
            result.fetchone.return_value = {"transaction_read_only": self.readonly}
        elif sql == "SHOW transaction_isolation":
            result.fetchone.return_value = {"transaction_isolation": self.isolation}
        elif "chunk_text" in sql:
            result.fetchall.return_value = self.bodies
        elif "SELECT" in sql:
            result.fetchall.return_value = self.headers
        return result

    def close(self):
        self.closed = True


class CorpusScopeTest(unittest.TestCase):
    def test_scope_requires_explicit_nonempty_fields(self):
        for collection, tenant, tags in [
            ("", "t", ("public",)), ("c", "", ("public",)),
            ("c", "t", ()), ("c", "t", ("",)),
            ("*", "t", ("public",)), ("c", "*", ("public",)),
            ("c", "t", ("*",)), ("c", "t", "public"),
            ("c", "t", (123,)), ("c", 123, ("public",)),
        ]:
            with self.subTest(collection=collection, tenant=tenant, tags=tags):
                with self.assertRaises(ValueError):
                    CorpusScope(collection, tenant, tags)

    def test_scope_tags_are_canonical(self):
        scope = CorpusScope("test", "tenant-a", ("ops", "public", "ops"))
        self.assertEqual(scope.permission_tags, ("ops", "public"))


class CorpusExportTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = production_settings(self.root)
        self.scope = CorpusScope("test", "tenant-a", ("public",))
        self.output = self.root / "snapshot"

    def export(self, db=None, output=None, **kwargs):
        db = db or FakeDatabase()
        return export_active_chunks(
            self.settings, self.scope, output or self.output, connect=db.connect, **kwargs
        )

    def test_export_preserves_ids_text_evidence_and_safe_metadata(self):
        result = self.export()
        manifest, chunks = load_corpus_snapshot(result.manifest_path, expected_scope=self.scope)
        self.assertEqual(manifest["record_count"], 1)
        self.assertEqual(manifest["document_count"], 1)
        self.assertEqual(chunks[0]["chunk_id"], "c1")
        self.assertEqual(chunks[0]["document_id"], "d1")
        self.assertEqual(chunks[0]["source"], "standard.pdf")
        self.assertEqual(chunks[0]["page_number"], 7)
        self.assertEqual(chunks[0]["document_version"], "v_" + "a" * 16)
        self.assertEqual(chunks[0]["chunk_text"], body()["chunk_text"])
        content = result.corpus_path.read_text(encoding="utf-8")
        for forbidden in ("SENSITIVE_METADATA_CANARY", "private/path.pdf", "private", "postgresql://"):
            self.assertNotIn(forbidden, content)
        self.assertIn("source_path", manifest["metadata_policy"]["excluded_keys"])
        self.assertEqual(manifest["database_access"], "repeatable_read_read_only")
        self.assertEqual(Path(manifest["code_provenance"]["package_root"]), Path(__file__).resolve().parents[1] / "rag_app")
        self.assertIn("eval_dataset/corpus.py", manifest["code_provenance"]["source_sha256"])

    def test_connection_and_transaction_are_readonly_and_always_closed(self):
        db = FakeDatabase()
        self.export(db)
        kwargs = db.connect.call_args.kwargs
        self.assertTrue(kwargs["autocommit"])
        self.assertIn("default_transaction_read_only=on", kwargs["options"])
        self.assertEqual(db.calls[0][0], "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        self.assertTrue(db.closed)
        self.assertEqual(db.calls[-1][0], "ROLLBACK")
        for sql, _ in db.calls:
            self.assertNotRegex(sql.upper(), r"\b(CREATE|ALTER|INSERT|UPDATE|DELETE|REFRESH|TRUNCATE|GRANT)\b")

    def test_sql_parameterizes_scope_and_filters_before_body_read(self):
        db = FakeDatabase()
        self.export(db)
        selects = [(sql, params) for sql, params in db.calls if "SELECT" in sql]
        self.assertEqual(len(selects), 2)
        for sql, params in selects:
            self.assertNotIn("tenant-a", sql)
            self.assertIn("tenant-a", params)
            self.assertIn("collection_name = %s", sql)
            self.assertIn("status = 'active'", sql)
        sql, params = selects[1]
        self.assertIn("?|", sql)
        self.assertIn(["public"], params)
        self.assertIn(["c1"], params)

    def test_refuses_non_readonly_or_wrong_isolation_before_reading_rows(self):
        for kwargs in ({"readonly": "off"}, {"isolation": "read committed"}):
            db = FakeDatabase(**kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(CorpusExportError):
                self.export(db)
            self.assertFalse(any("SELECT" in sql for sql, _ in db.calls))
            self.assertTrue(db.closed)
            self.assertFalse(self.output.exists())

    def test_invalid_headers_stop_before_any_body_is_read(self):
        bad_updates = [
            {"tenant_id": "tenant-b"}, {"tenant_id": None},
            {"permission_tags": []}, {"permission_tags": "public"},
            {"permission_tags": ["public", 1]},
            {"document_tenant_id": "tenant-b"},
            {"document_permission_tags": None},
            {"document_permission_tags": ["ops"]},
            {"document_status": None}, {"document_status": "inactive"},
            {"collection_name": "other"},
        ]
        for updates in bad_updates:
            row = header()
            row.update(updates)
            db = FakeDatabase(headers=[row])
            with self.subTest(updates=updates), self.assertRaises(CorpusExportError):
                self.export(db)
            self.assertFalse(any("chunk_text" in sql for sql, _ in db.calls))
            self.assertFalse(self.output.exists())

    def test_valid_but_ungranted_tags_are_not_exported(self):
        db = FakeDatabase(headers=[header(), header("private", tags=["ops"])])
        result = self.export(db)
        self.assertEqual(result.record_count, 1)
        body_params = [p for sql, p in db.calls if "chunk_text" in sql][0]
        self.assertNotIn("private", str(body_params))

    def test_body_revalidates_scope_and_metadata_consistency(self):
        for change in (
            {"tenant_id": "tenant-b"}, {"source_name": "other.pdf"},
            {"document_version_id": "v_other"}, {"chunk_id": "unselected"},
        ):
            row = body()
            row.update(change)
            with self.subTest(change=change), self.assertRaises(CorpusExportError):
                self.export(FakeDatabase(bodies=[row]))
            self.assertFalse(self.output.exists())
        for field, value in (("tenant_id", "tenant-b"), ("permission_tags", ["ops"]),
                             ("page_number", True), ("source", ""), ("version_id", 123)):
            row = body()
            row["metadata"][field] = value
            with self.subTest(field=field), self.assertRaises(CorpusExportError):
                self.export(FakeDatabase(bodies=[row]))

    def test_structural_metadata_rejects_nested_objects_and_invalid_types(self):
        for field, value in (
            ("title", {"api_key": "NESTED_SECRET", "source_path": "private/path"}),
            ("section_path", ["normal", {"api_key": "NESTED_SECRET"}]),
            ("heading_path", {"secret": "NESTED_SECRET"}),
            ("chunk_index", True), ("chunk_parse_warning_codes", [1]),
        ):
            row = body()
            row["metadata"][field] = value
            with self.subTest(field=field), self.assertRaises(CorpusExportError):
                self.export(FakeDatabase(bodies=[row]))
            self.assertFalse(self.output.exists())

    def test_document_content_hash_fallback_is_explicit(self):
        row = body()
        del row["metadata"]["version_id"]
        row["document_version_id"] = None
        result = self.export(FakeDatabase(bodies=[row]))
        _, chunks = load_corpus_snapshot(result.manifest_path)
        self.assertEqual(chunks[0]["document_version"], "sha256:" + "a" * 64)
        self.assertEqual(chunks[0]["document_version_source"], "document_content_hash")

    def test_unicode_line_separators_are_preserved_and_roundtrip(self):
        text = "evidence\u0085next\u2028paragraph\u2029end\nnormal line"
        result = self.export(FakeDatabase(bodies=[body(text=text)]))
        _, chunks = load_corpus_snapshot(result.manifest_path, expected_scope=self.scope)
        self.assertEqual(chunks[0]["chunk_text"], text)

    def test_missing_pages_are_allowed_for_non_paginated_documents(self):
        row = body()
        del row["metadata"]["page_number"]
        result = self.export(FakeDatabase(bodies=[row]))
        _, chunks = load_corpus_snapshot(result.manifest_path)
        self.assertIsNone(chunks[0]["page_number"])

    def test_empty_duplicate_or_missing_rows_fail_without_publishing(self):
        fixtures = [
            FakeDatabase(headers=[], bodies=[]),
            FakeDatabase(headers=[header(), header()]),
            FakeDatabase(bodies=[]), FakeDatabase(bodies=[body(), body()]),
        ]
        for db in fixtures:
            with self.subTest(headers=db.headers, bodies=len(db.bodies)), self.assertRaises(CorpusExportError):
                self.export(db)
            self.assertFalse(self.output.exists())

    def test_limits_and_config_mismatch_fail_before_connection(self):
        db = FakeDatabase()
        for kwargs in ({"max_records": 0}, {"statement_timeout_seconds": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.export(db, **kwargs)
        with self.assertRaises(ValueError):
            export_active_chunks(self.settings, CorpusScope("other", "tenant-a", ("public",)), self.output, connect=db.connect)
        db.connect.assert_not_called()
        db = FakeDatabase(headers=[header(), header("c2")])
        with self.assertRaises(CorpusExportError):
            self.export(db, max_records=1)

    def test_existing_output_is_never_overwritten_or_read_from_database(self):
        self.output.mkdir()
        marker = self.output / "user-file.txt"
        marker.write_text("keep", encoding="utf-8")
        db = FakeDatabase()
        with self.assertRaises(FileExistsError):
            self.export(db)
        self.assertEqual(marker.read_text(), "keep")
        db.connect.assert_not_called()

    def test_database_error_is_sanitized_and_connection_is_closed(self):
        db = FakeDatabase()
        db.connection.execute.side_effect = RuntimeError("postgresql://SECRET@host/db")
        with self.assertRaises(CorpusExportError) as caught:
            self.export(db)
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertTrue(db.closed)
        self.assertFalse(self.output.exists())

    def test_connection_close_failure_is_sanitized_without_publication(self):
        db = FakeDatabase()
        db.connection.close.side_effect = RuntimeError("SECRET_CLOSE_ERROR")
        with self.assertRaises(CorpusExportError) as caught:
            self.export(db)
        self.assertNotIn("SECRET_CLOSE_ERROR", str(caught.exception))
        self.assertFalse(self.output.exists())

    def test_snapshot_identity_and_jsonl_are_reproducible_despite_order_and_time(self):
        db1 = FakeDatabase(headers=[header("c2"), header()], bodies=[body("c2"), body()])
        db2 = FakeDatabase(headers=[header(), header("c2")], bodies=[body(), body("c2")])
        r1 = self.export(db1, output=self.root / "one")
        r2 = self.export(db2, output=self.root / "two")
        self.assertEqual(r1.snapshot_id, r2.snapshot_id)
        self.assertEqual(r1.corpus_path.read_bytes(), r2.corpus_path.read_bytes())
        m1, _ = load_corpus_snapshot(r1.manifest_path)
        m2, _ = load_corpus_snapshot(r2.manifest_path)
        self.assertEqual(m1["corpus_sha256"], m2["corpus_sha256"])
        changed = self.export(FakeDatabase(bodies=[body(text="changed")]), output=self.root / "changed")
        self.assertNotEqual(r1.snapshot_id, changed.snapshot_id)

    def test_verifier_detects_corrupted_corpus_manifest_and_scope(self):
        result = self.export()
        original = result.corpus_path.read_bytes()
        result.corpus_path.write_bytes(original.replace(b"GB/T9254.1", b"T9254"))
        with self.assertRaises(CorpusExportError):
            load_corpus_snapshot(result.manifest_path)
        result.corpus_path.write_bytes(original)
        with self.assertRaises(CorpusExportError):
            load_corpus_snapshot(result.manifest_path, expected_scope=CorpusScope("test", "other", ("public",)))
        original_manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        for field, value in (("record_count", 99), ("snapshot_id", "wrong"),
                             ("corpus_file", "../user.jsonl"), ("schema_version", 999)):
            manifest = copy.deepcopy(original_manifest)
            manifest[field] = value
            result.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.subTest(field=field), self.assertRaises(CorpusExportError):
                load_corpus_snapshot(result.manifest_path)

    def test_partial_publication_has_no_valid_manifest(self):
        with patch("rag_app.eval_dataset.corpus._write_manifest", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.export()
        self.assertFalse((self.output / "corpus.manifest.json").exists())

    def test_verifier_rejects_rehashed_boolean_counts(self):
        from rag_app.eval_dataset.corpus import _canonical, _snapshot_identity

        result = self.export()
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        manifest["record_count"] = True
        manifest["snapshot_id"] = _snapshot_identity(manifest)
        del manifest["manifest_sha256"]
        manifest["manifest_sha256"] = hashlib.sha256(_canonical(manifest)).hexdigest()
        result.manifest_path.write_bytes(_canonical(manifest) + b"\n")
        with self.assertRaises(CorpusExportError):
            load_corpus_snapshot(result.manifest_path)

    def test_verifier_requires_provenance_time_and_access_schema_even_when_rehashed(self):
        from rag_app.eval_dataset.corpus import _canonical, _snapshot_identity

        result = self.export()
        original = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        for field in ("code_provenance", "created_at", "database_access", "collection_resolution"):
            manifest = copy.deepcopy(original)
            del manifest[field]
            del manifest["manifest_sha256"]
            manifest["manifest_sha256"] = hashlib.sha256(_canonical(manifest)).hexdigest()
            result.manifest_path.write_bytes(_canonical(manifest) + b"\n")
            with self.subTest(field=field), self.assertRaises(CorpusExportError):
                load_corpus_snapshot(result.manifest_path)
        for field, value in (("created_at", "not-a-time"), ("database_access", "read_write"),
                             ("collection_resolution", "auto"), ("code_provenance", {})):
            manifest = copy.deepcopy(original)
            manifest[field] = value
            del manifest["manifest_sha256"]
            manifest["manifest_sha256"] = hashlib.sha256(_canonical(manifest)).hexdigest()
            result.manifest_path.write_bytes(_canonical(manifest) + b"\n")
            with self.subTest(field=field, value=value), self.assertRaises(CorpusExportError):
                load_corpus_snapshot(result.manifest_path)
        manifest = copy.deepcopy(original)
        manifest["metadata_policy"]["kind"] = "unrestricted"
        manifest["snapshot_id"] = _snapshot_identity(manifest)
        del manifest["manifest_sha256"]
        manifest["manifest_sha256"] = hashlib.sha256(_canonical(manifest)).hexdigest()
        result.manifest_path.write_bytes(_canonical(manifest) + b"\n")
        with self.assertRaises(CorpusExportError):
            load_corpus_snapshot(result.manifest_path)

    def test_verifier_checks_exact_top_level_json_types_not_python_numeric_equality(self):
        from rag_app.eval_dataset.corpus import _canonical, _snapshot_identity

        result = self.export()
        original_manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        original_record = json.loads(result.corpus_path.read_text(encoding="utf-8"))
        for page in (7.0, True):
            record = copy.deepcopy(original_record)
            if page is True:
                record["metadata"]["page_number"] = 1
            record["page_number"] = page
            content = _canonical(record) + b"\n"
            result.corpus_path.write_bytes(content)
            manifest = copy.deepcopy(original_manifest)
            manifest["corpus_sha256"] = hashlib.sha256(content).hexdigest()
            manifest["snapshot_id"] = _snapshot_identity(manifest)
            del manifest["manifest_sha256"]
            manifest["manifest_sha256"] = hashlib.sha256(_canonical(manifest)).hexdigest()
            result.manifest_path.write_bytes(_canonical(manifest) + b"\n")
            with self.subTest(page=page), self.assertRaises(CorpusExportError):
                load_corpus_snapshot(result.manifest_path)


class CorpusCliTest(unittest.TestCase):
    def test_help_requires_no_database_settings(self):
        with redirect_stdout(io.StringIO()) as output, self.assertRaises(SystemExit) as exit_info:
            main(["export-eval-chunks", "--help"])
        self.assertEqual(exit_info.exception.code, 0)
        for option in ("--collection", "--tenant-id", "--permission-tags", "--output-dir"):
            self.assertIn(option, output.getvalue())

    def test_cli_requires_explicit_scope(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["export-eval-chunks"])

    def test_cli_dispatch_uses_current_settings_and_explicit_scope(self):
        with TemporaryDirectory() as temp:
            settings = production_settings(Path(temp))
            with patch("rag_app.cli.Settings.from_env", return_value=settings), patch(
                "rag_app.eval_dataset.corpus._connect_readonly", side_effect=FakeDatabase().connect
            ), redirect_stdout(io.StringIO()) as output:
                status = main(["export-eval-chunks", "--collection", "test", "--tenant-id", "tenant-a", "--permission-tags", "public", "--output-dir", str(Path(temp) / "out"), "--json"])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue())["record_count"], 1)

    def test_cli_reports_permission_failure_without_sensitive_values(self):
        with patch("rag_app.eval_dataset.corpus.Settings.from_env", return_value=production_settings(Path.cwd())), patch(
            "rag_app.eval_dataset.corpus.export_active_chunks",
            side_effect=CorpusExportError("Permission/association validation failed; export stopped before publication."),
        ), redirect_stderr(io.StringIO()) as error:
            status = main(["export-eval-chunks", "--collection", "test", "--tenant-id", "tenant-a", "--permission-tags", "public"])
        self.assertEqual(status, 2)
        self.assertIn("Permission/association validation failed", error.getvalue())


if __name__ == "__main__":
    unittest.main()
