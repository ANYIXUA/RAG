"""Fail-closed, read-only Active Chunk export and content-addressed snapshots.

No VectorStore, lifecycle Store, model client, Redis client or online Processor is
constructed here. Caller scope is an explicit local operator assertion, not a new
authentication gateway. Database permissions remain the operator's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable
from uuid import uuid4

from rag_app.core.config import Settings
from rag_app.eval_dataset.schemas import CorpusScope, permission_labels, required_label


SCHEMA_VERSION = 1
CORPUS_FILE = "corpus.jsonl"
MANIFEST_FILE = "corpus.manifest.json"
METADATA_FIELDS = frozenset({
    "source", "filename", "title", "source_type", "business_module",
    "page_number", "version_id", "tenant_id", "permission_tags",
    "section_title", "section_path", "heading_path", "chunk_index",
    "block_id", "block_type", "parser_name", "parser_version", "content_hash",
    "chunk_parse_quality_status", "chunk_parse_warning_codes",
})
NORMALIZATION = {"chunk_text": "none", "json": "utf8_sorted_keys_compact_lf_v1"}
_LIST_METADATA_FIELDS = frozenset({
    "permission_tags", "section_path", "heading_path", "chunk_parse_warning_codes",
})
_MANIFEST_FIELDS = frozenset({
    "schema_version", "corpus_file", "scope", "collection_resolution", "created_at",
    "record_count", "document_count", "corpus_sha256", "normalization",
    "metadata_policy", "database_access", "code_provenance", "snapshot_id", "manifest_sha256",
})

# Read only ACL headers in the explicit tenant first. LEFT JOIN is intentional:
# orphan/inactive/mis-associated documents must stop export, not disappear.
_HEADERS_SQL = """
SELECT c.collection_name, c.chunk_id, c.document_id,
       c.metadata->'tenant_id' AS tenant_id,
       c.metadata->'permission_tags' AS permission_tags,
       d.metadata->'tenant_id' AS document_tenant_id,
       d.metadata->'permission_tags' AS document_permission_tags,
       d.status AS document_status
FROM public.rag_knowledge_chunks c
LEFT JOIN public.rag_documents d
  ON d.collection_name = c.collection_name AND d.document_id = c.document_id
WHERE c.collection_name = %s AND c.status = 'active'
  AND c.metadata->>'tenant_id' = %s
ORDER BY c.chunk_id
LIMIT %s
"""

# Body selection repeats every scope predicate in SQL, before data leaves DB.
# CASE prevents jsonb array operators from accepting legacy malformed ACL types.
_BODIES_SQL = """
SELECT c.collection_name, c.chunk_id, c.document_id, c.chunk_text, c.metadata,
       c.version AS chunk_version,
       c.metadata->'tenant_id' AS tenant_id,
       c.metadata->'permission_tags' AS permission_tags,
       d.metadata->'tenant_id' AS document_tenant_id,
       d.metadata->'permission_tags' AS document_permission_tags,
       d.status AS document_status, d.source_name, d.content_hash AS document_content_hash,
       d.metadata->'version_id' AS document_version_id
FROM public.rag_knowledge_chunks c
JOIN public.rag_documents d
  ON d.collection_name = c.collection_name AND d.document_id = c.document_id
WHERE c.collection_name = %s AND c.status = 'active' AND d.status = 'active'
  AND c.metadata->>'tenant_id' = %s AND d.metadata->>'tenant_id' = %s
  AND CASE WHEN jsonb_typeof(c.metadata->'permission_tags') = 'array'
      THEN c.metadata->'permission_tags' ?| %s::text[] ELSE FALSE END
  AND CASE WHEN jsonb_typeof(d.metadata->'permission_tags') = 'array'
      THEN d.metadata->'permission_tags' ?| %s::text[] ELSE FALSE END
  AND c.chunk_id = ANY(%s::text[])
ORDER BY c.chunk_id
"""


class CorpusExportError(ValueError):
    """Safe-to-display export/integrity failure, without document contents/DSNs."""


@dataclass(frozen=True)
class CorpusExportResult:
    corpus_path: Path
    manifest_path: Path
    snapshot_id: str
    record_count: int
    document_count: int


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _connect_readonly(dsn: str, **kwargs):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        raise CorpusExportError("Export requires the existing pgsql extra (psycopg).") from None
    return psycopg.connect(dsn, row_factory=dict_row, **kwargs)


def _check_header(row: dict, scope: CorpusScope) -> bool:
    try:
        if not isinstance(row, dict):
            raise ValueError("Invalid header")
        required_label(row.get("chunk_id"), "chunk_id")
        required_label(row.get("document_id"), "document_id")
        if row.get("collection_name") != scope.collection_name:
            raise ValueError("Collection mismatch")
        if row.get("tenant_id") != scope.tenant_id or row.get("document_tenant_id") != scope.tenant_id:
            raise ValueError("Tenant mismatch")
        if row.get("document_status") != "active":
            raise ValueError("Missing or inactive document")
        chunk_tags = set(permission_labels(row.get("permission_tags")))
        doc_tags = set(permission_labels(row.get("document_permission_tags")))
        allowed = set(scope.permission_tags)
        selected = bool(chunk_tags & allowed)
        if selected and not doc_tags & allowed:
            raise ValueError("Inconsistent document/chunk ACL")
        return selected
    except (ValueError, TypeError):
        raise CorpusExportError("Permission/association validation failed; export stopped before publication.") from None


def _body_to_record(row: dict, scope: CorpusScope) -> tuple[dict, set[str]]:
    if not _check_header(row, scope):
        raise CorpusExportError("Database returned an unauthorized body; export stopped.")
    metadata = row.get("metadata")
    if not isinstance(metadata, dict):
        raise CorpusExportError("Chunk metadata must be a JSON object.")
    try:
        _validate_metadata_types(metadata)
        if metadata.get("tenant_id") != scope.tenant_id:
            raise ValueError("Metadata tenant mismatch")
        tags = permission_labels(metadata.get("permission_tags"))
        if tags != permission_labels(row.get("permission_tags")):
            raise ValueError("Metadata ACL mismatch")
        source = required_label(metadata.get("source"), "source")
        if row.get("source_name") not in (None, "", source):
            raise ValueError("Document/Chunk source mismatch")
        page = metadata.get("page_number")
        if page is not None and (type(page) is not int or page <= 0):
            raise ValueError("Invalid page")
        document_hash = row.get("document_content_hash")
        if not isinstance(document_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", document_hash):
            raise ValueError("Invalid document hash")
        chunk_version = row.get("chunk_version")
        if type(chunk_version) is not int or chunk_version < 1:
            raise ValueError("Invalid database chunk version")
        chunk_version_id = metadata.get("version_id")
        doc_version_id = row.get("document_version_id")
        for version in (chunk_version_id, doc_version_id):
            if version is not None:
                required_label(version, "version_id")
        if chunk_version_id and doc_version_id and chunk_version_id != doc_version_id:
            raise ValueError("Version mismatch")
        version = chunk_version_id or doc_version_id or f"sha256:{document_hash}"
        version_source = (
            "chunk_metadata.version_id" if chunk_version_id
            else "document_metadata.version_id" if doc_version_id else "document_content_hash"
        )
        text = row.get("chunk_text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Empty body")
        record = {
            "collection_name": scope.collection_name, "chunk_id": row["chunk_id"],
            "document_id": row["document_id"], "source": source, "page_number": page,
            "document_version": version, "document_version_source": version_source,
            "database_chunk_version": chunk_version, "document_content_hash": document_hash,
            "chunk_text": text, "chunk_text_sha256": _sha256(text.encode("utf-8")),
            "tenant_id": scope.tenant_id, "permission_tags": list(tags),
            "metadata": {k: v for k, v in metadata.items() if k in METADATA_FIELDS},
        }
        _canonical(record)  # Reject non-JSON metadata/NaN before writing any output.
        return record, set(metadata) - METADATA_FIELDS
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise CorpusExportError("Chunk identity/source/page/version/body validation failed; export stopped.") from None


def _validate_metadata_types(metadata: dict) -> None:
    # Structural fields have a closed, shallow type schema. A top-level key
    # allowlist alone would permit objects hiding arbitrary nested credentials.
    for key in METADATA_FIELDS & metadata.keys():
        value = metadata[key]
        if value is None:
            continue
        if key in _LIST_METADATA_FIELDS:
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise ValueError("Invalid structural list metadata")
        elif key in {"page_number", "chunk_index"}:
            minimum = 1 if key == "page_number" else 0
            if type(value) is not int or value < minimum:
                raise ValueError("Invalid structural integer metadata")
        elif not isinstance(value, str):
            raise ValueError("Invalid structural text metadata")


def _read_records(settings, scope, connector, timeout, max_records):
    connection = None
    try:
        connection = connector(
            settings.ops_postgres_dsn, autocommit=True,
            options=f"-c default_transaction_read_only=on -c statement_timeout={timeout * 1000}",
        )
        connection.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        readonly = connection.execute("SHOW transaction_read_only").fetchone()
        isolation = connection.execute("SHOW transaction_isolation").fetchone()
        if readonly.get("transaction_read_only") != "on" or isolation.get("transaction_isolation") != "repeatable read":
            raise CorpusExportError("Server did not confirm repeatable-read/read-only mode; no rows read.")
        headers = connection.execute(
            _HEADERS_SQL, (scope.collection_name, scope.tenant_id, max_records + 1)
        ).fetchall()
        if len(headers) > max_records:
            raise CorpusExportError("Tenant row limit exceeded; narrow scope or explicitly raise max_records.")
        selected = {}
        seen = set()
        for row in headers:
            granted = _check_header(row, scope)
            chunk_id = row["chunk_id"]
            if chunk_id in seen:
                raise CorpusExportError("Duplicate Chunk identity/association in database.")
            seen.add(chunk_id)
            if granted:
                selected[chunk_id] = row
        if not selected:
            raise CorpusExportError("No active chunks match the explicit collection/tenant/permission scope.")
        tags = list(scope.permission_tags)
        rows = connection.execute(
            _BODIES_SQL,
            (scope.collection_name, scope.tenant_id, scope.tenant_id, tags, tags, sorted(selected)),
        ).fetchall()
        records = []
        excluded_keys = set()
        body_ids = set()
        for row in rows:
            chunk_id = row.get("chunk_id")
            if chunk_id not in selected or chunk_id in body_ids:
                raise CorpusExportError("Unexpected/duplicate body identity in database response.")
            if any(row.get(k) != v for k, v in selected[chunk_id].items()):
                raise CorpusExportError("Body/header identity or permission mismatch.")
            record, excluded = _body_to_record(row, scope)
            records.append(record)
            excluded_keys.update(excluded)
            body_ids.add(chunk_id)
        if body_ids != set(selected):
            raise CorpusExportError("Missing selected chunk bodies; no snapshot published.")
        return sorted(records, key=lambda r: r["chunk_id"]), sorted(excluded_keys)
    except CorpusExportError:
        raise
    except Exception:
        # psycopg errors may contain connection strings or text values.
        raise CorpusExportError("Read-only database export failed; check connectivity/schema/permissions privately.") from None
    finally:
        if connection is not None:
            cleanup_failed = False
            try:
                connection.execute("ROLLBACK")
            except Exception:
                cleanup_failed = True
            try:
                connection.close()
            except Exception:
                cleanup_failed = True
            if cleanup_failed:
                raise CorpusExportError("Read-only connection cleanup failed; no snapshot published.") from None


def _snapshot_identity(manifest: dict) -> str:
    identity = {key: manifest[key] for key in (
        "schema_version", "scope", "corpus_sha256", "record_count", "document_count",
        "normalization", "metadata_policy",
    )}
    return "sha256:" + _sha256(_canonical(identity))


def _code_provenance(settings: Settings) -> dict:
    root = Path(__file__).resolve().parents[1]
    paths = [*Path(__file__).parent.glob("*.py"), root / "cli.py", root / "core" / "config.py"]
    result = {
        "package_root": str(root), "python_version": sys.version.split()[0],
        "config_fingerprint": settings.config_fingerprint,
        "source_sha256": {p.relative_to(root).as_posix(): _sha256(p.read_bytes()) for p in sorted(paths)},
        "git_head": None, "worktree_dirty": None,
    }
    try:
        def git(*args):
            return subprocess.run(
                ["git", "-C", str(root.parent), *args], check=True,
                capture_output=True, timeout=5,
            ).stdout
        result["git_head"] = git("rev-parse", "HEAD").decode("ascii").strip()
        result["worktree_dirty"] = bool(git("status", "--porcelain"))
    except (OSError, subprocess.SubprocessError):
        pass
    return result


def _write_manifest(path: Path, manifest: dict) -> None:
    with path.open("xb") as file:
        file.write(_canonical(manifest) + b"\n")


def export_active_chunks(
    settings: Settings, scope: CorpusScope, output_dir: Path,
    *, connect: Callable | None = None, statement_timeout_seconds: int = 30,
    max_records: int = 100_000,
) -> CorpusExportResult:
    """Export an exact explicit collection with active documents AND active chunks.

    Output must be a new directory. The manifest is the completion marker; a
    directory without a verified manifest is incomplete and must not be consumed.
    """
    if not isinstance(scope, CorpusScope):
        raise ValueError("An explicit CorpusScope is required")
    if scope.collection_name != settings.collection_name:
        raise ValueError("Explicit collection differs from current Settings.collection_name")
    if settings.vector_store_provider != "postgresql" or not settings.ops_postgres_dsn:
        raise ValueError("Existing PostgreSQL configuration is required")
    for value in (statement_timeout_seconds, max_records):
        if type(value) is not int or value <= 0:
            raise ValueError("Timeout and max_records must be positive integers")
    output_dir = Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("Output directory already exists; choose a new path")
    records, excluded_keys = _read_records(
        settings, scope, connect or _connect_readonly, statement_timeout_seconds, max_records
    )
    content = b"".join(_canonical(record) + b"\n" for record in records)
    manifest = {
        "schema_version": SCHEMA_VERSION, "corpus_file": CORPUS_FILE,
        "scope": scope.to_dict(), "collection_resolution": "explicit",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records), "document_count": len({r["document_id"] for r in records}),
        "corpus_sha256": _sha256(content), "normalization": NORMALIZATION,
        "metadata_policy": {"kind": "allowlist", "fields": sorted(METADATA_FIELDS), "excluded_keys": excluded_keys},
        "database_access": "repeatable_read_read_only", "code_provenance": _code_provenance(settings),
    }
    manifest["snapshot_id"] = _snapshot_identity(manifest)
    manifest["manifest_sha256"] = _sha256(_canonical(manifest))
    # Exclusive mkdir/open prevent overwriting even if another exporter races us.
    output_dir.mkdir(parents=True, exist_ok=False)
    corpus_path = output_dir / CORPUS_FILE
    with corpus_path.open("xb") as file:
        file.write(content)
    manifest_path = output_dir / MANIFEST_FILE
    _write_manifest(manifest_path, manifest)
    return CorpusExportResult(corpus_path, manifest_path, manifest["snapshot_id"], len(records), manifest["document_count"])


def _validate_record(record: dict, scope: CorpusScope) -> None:
    metadata = record["metadata"]
    if not isinstance(metadata, dict) or set(metadata) - METADATA_FIELDS:
        raise ValueError("Invalid exported metadata")
    # Reuse the same consistency checks on loaded records rather than trusting
    # hashes to imply valid types/ACLs. Hashes are integrity checks, not signatures.
    row = {
        **record, "chunk_version": record["database_chunk_version"],
        "document_status": "active", "document_tenant_id": record["tenant_id"],
        "document_permission_tags": record["permission_tags"], "source_name": record["source"],
        "document_version_id": (
            record["document_version"]
            if record["document_version_source"] == "document_metadata.version_id" else None
        ),
    }
    rebuilt, _ = _body_to_record(row, scope)
    if _canonical(record) != _canonical(rebuilt):
        raise ValueError("Record consistency mismatch")


def _validate_manifest_schema(manifest: dict) -> None:
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_FIELDS:
        raise ValueError("Missing/unsupported manifest fields")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported schema version")
    if manifest["corpus_file"] != CORPUS_FILE or manifest["collection_resolution"] != "explicit":
        raise ValueError("Invalid corpus/collection resolution")
    if manifest["database_access"] != "repeatable_read_read_only":
        raise ValueError("Invalid database access declaration")
    for key in ("record_count", "document_count"):
        if type(manifest[key]) is not int or manifest[key] < 1:
            raise ValueError("Invalid manifest counts")
    created_at = datetime.fromisoformat(manifest["created_at"])
    if created_at.tzinfo is None or created_at.utcoffset().total_seconds() != 0:
        raise ValueError("Manifest time must have UTC timezone")
    for key in ("corpus_sha256", "manifest_sha256"):
        if not isinstance(manifest[key], str) or not re.fullmatch(r"[a-f0-9]{64}", manifest[key]):
            raise ValueError("Invalid digest type")
    policy = manifest["metadata_policy"]
    if (
        not isinstance(policy, dict) or set(policy) != {"kind", "fields", "excluded_keys"}
        or policy["kind"] != "allowlist" or policy["fields"] != sorted(METADATA_FIELDS)
        or not isinstance(policy["excluded_keys"], list)
        or any(not isinstance(key, str) for key in policy["excluded_keys"])
        or policy["excluded_keys"] != sorted(set(policy["excluded_keys"]))
        or manifest["normalization"] != NORMALIZATION
    ):
        raise ValueError("Unsupported data policy")
    provenance = manifest["code_provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {
        "package_root", "python_version", "config_fingerprint", "source_sha256", "git_head", "worktree_dirty"
    }:
        raise ValueError("Missing code provenance")
    required_label(provenance["package_root"], "package_root")
    required_label(provenance["python_version"], "python_version")
    if not isinstance(provenance["config_fingerprint"], str):
        raise ValueError("Invalid configuration fingerprint")
    hashes = provenance["source_sha256"]
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("Missing source hashes")
    for name, digest in hashes.items():
        required_label(name, "source_file")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("Invalid source digest")
    if provenance["git_head"] is not None and (
        not isinstance(provenance["git_head"], str)
        or not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", provenance["git_head"])
    ):
        raise ValueError("Invalid Git revision")
    if provenance["worktree_dirty"] is not None and type(provenance["worktree_dirty"]) is not bool:
        raise ValueError("Invalid worktree state")


def load_corpus_snapshot(
    manifest_path: Path, *, expected_scope: CorpusScope | None = None,
) -> tuple[dict, list[dict]]:
    """Verify completion, schema, exact bytes, identities, counts and permissions."""
    try:
        manifest_path = Path(manifest_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        _validate_manifest_schema(manifest)
        supplied_hash = manifest["manifest_sha256"]
        if supplied_hash != _sha256(_canonical({k: v for k, v in manifest.items() if k != "manifest_sha256"})):
            raise ValueError("Manifest integrity mismatch")
        scope = CorpusScope.from_dict(manifest["scope"])
        if expected_scope is not None and scope != expected_scope:
            raise ValueError("Unexpected scope")
        if manifest["snapshot_id"] != _snapshot_identity(manifest):
            raise ValueError("Snapshot identity mismatch")
        content = (manifest_path.parent / CORPUS_FILE).read_bytes()
        if _sha256(content) != manifest["corpus_sha256"]:
            raise ValueError("Corpus integrity mismatch")
        if not content.endswith(b"\n"):
            raise ValueError("Missing canonical JSONL terminator")
        # JSONL uses LF, not Unicode's broader set of line separators. Those
        # characters can legitimately occur unescaped inside a JSON string.
        records = [json.loads(line) for line in content.decode("utf-8").split("\n")[:-1]]
        if not records or len(records) != manifest["record_count"]:
            raise ValueError("Record count mismatch")
        if len({r["document_id"] for r in records}) != manifest["document_count"]:
            raise ValueError("Document count mismatch")
        ids = [r["chunk_id"] for r in records]
        if ids != sorted(set(ids)):
            raise ValueError("Chunk order/uniqueness mismatch")
        for record in records:
            _validate_record(record, scope)
        if content != b"".join(_canonical(record) + b"\n" for record in records):
            raise ValueError("Noncanonical corpus encoding")
        return manifest, records
    except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeError):
        raise CorpusExportError("Snapshot verification failed (schema/hash/scope/record consistency).") from None


def run_export_command(args) -> int:
    try:
        scope = CorpusScope(args.collection, args.tenant_id, tuple(args.permission_tags))
        settings = Settings.from_env()
        output = args.output_dir or (
            settings.storage_dir / "evaluation" / "corpus"
            / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8])
        )
        result = export_active_chunks(
            settings, scope, output, max_records=args.max_records,
            statement_timeout_seconds=args.statement_timeout_seconds,
        )
    except CorpusExportError as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return 2
    except (ValueError, OSError):
        # Settings errors may include secret-bearing environment substitutions.
        print("Export failed: check explicit scope, existing PostgreSQL configuration, permissions and new output directory.", file=sys.stderr)
        return 2
    payload = {
        "snapshot_id": result.snapshot_id, "record_count": result.record_count,
        "document_count": result.document_count, "corpus_path": str(result.corpus_path),
        "manifest_path": str(result.manifest_path), "database_access": "repeatable_read_read_only",
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"Exported {result.record_count} active chunks from {result.document_count} documents (read-only).")
        print(f"Snapshot: {result.snapshot_id}\nManifest: {result.manifest_path}")
    return 0
