from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from demo.offline_parsing.embedding_store import (  # noqa: E402
    ChromaVectorStore,
    HashEmbedding,
    SentenceTransformerEmbedding,
    SQLiteVectorStore,
)
from demo.offline_parsing.parsing import (  # noqa: E402
    discover_files,
    iter_parsed_documents,
    recommended_worker_counts,
)
from demo.offline_parsing.pipeline import ingest_documents  # noqa: E402


DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="离线解析 + 批量向量化 Demo")
    parser.add_argument("--input", type=Path, required=True, help="PDF/DOCX/TXT 输入目录")
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=Path(".demo_data/offline_index"),
        help="本地向量索引与 manifest 目录",
    )
    parser.add_argument("--collection", default="offline_demo")
    parser.add_argument("--store", choices=["sqlite", "chroma"], default="sqlite")
    parser.add_argument(
        "--embedding",
        choices=["hash", "sentence-transformers"],
        default="hash",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--model-cache", type=Path)
    parser.add_argument("--model-revision")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--device", default=None, help="例如 cpu、cuda")
    parser.add_argument("--hash-dimension", type=int, default=384)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--chunk-overlap", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--min-batch-size", type=int, default=1)
    parser.add_argument("--parse-batch-size", type=int, default=8)
    parser.add_argument("--cpu-workers", type=int)
    parser.add_argument("--io-workers", type=int)
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="允许有失败/质量拒绝时激活新 generation；默认 fail closed",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_console()
    args = build_parser().parse_args(argv)
    source_dir = args.input.resolve()
    persist_dir = args.persist_dir.resolve()
    persist_dir.mkdir(parents=True, exist_ok=True)
    generation_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    index_dir = persist_dir / "generations" / generation_id
    paths = list(discover_files(source_dir))
    if not paths:
        print(f"未发现 PDF/DOCX/TXT: {source_dir}", file=sys.stderr)
        return 2

    default_cpu, default_io = recommended_worker_counts()
    outcomes = iter_parsed_documents(
        paths,
        source_dir=source_dir,
        parse_batch_size=args.parse_batch_size,
        cpu_workers=args.cpu_workers or default_cpu,
        io_workers=args.io_workers or default_io,
    )
    failures = []
    failure_parse_seconds = 0.0

    def successful_documents():
        nonlocal failure_parse_seconds
        for outcome in outcomes:
            if outcome.document is not None:
                yield outcome.document
                continue
            failure_parse_seconds += outcome.parse_seconds
            failures.append(
                {
                    "source": outcome.source,
                    "error_type": outcome.error_type or "UnknownError",
                    "error_message": outcome.error_message or "",
                }
            )

    encoder = _create_encoder(args)
    embedding_fingerprint = _embedding_fingerprint(args, encoder)
    store = _create_store(args, index_dir)
    try:
        stats = ingest_documents(
            successful_documents(),
            encoder=encoder,
            store=store,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            batch_size=args.batch_size,
            min_batch_size=args.min_batch_size,
            show_progress_bar=not args.no_progress,
        )
        stats.files_failed = len(failures)
        stats.parse_seconds += failure_parse_seconds
        stats.errors.extend(failures)
        vector_count = store.count()
    finally:
        close = getattr(store, "close", None)
        if callable(close):
            close()

    manifest = {
        "schema_version": 1,
        "generation_id": generation_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "persist_dir": str(persist_dir),
        "index_dir": str(index_dir),
        "collection": args.collection,
        "store": args.store,
        "embedding": args.embedding,
        "embedding_model": getattr(encoder, "model_name", args.model),
        "embedding_dimension": int(encoder.dimension),
        "embedding_fingerprint": embedding_fingerprint,
        "hash_dimension": args.hash_dimension if args.embedding == "hash" else None,
        "model_cache": str(args.model_cache.resolve()) if args.model_cache else None,
        "model_revision": args.model_revision,
        "local_files_only": args.local_files_only,
        "device": args.device,
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "batch_size": args.batch_size,
        "stats": stats.to_dict(),
    }
    print(json.dumps(stats.to_dict(), ensure_ascii=False, indent=2))
    print(f"staging_generation={index_dir}")
    print(f"vector_count={vector_count}")
    if stats.files_succeeded == 0:
        print("未激活：没有通过质量门禁的文档", file=sys.stderr)
        return 1
    if vector_count != stats.chunks_written:
        print(
            f"未激活：向量计数不完整 expected={stats.chunks_written} actual={vector_count}",
            file=sys.stderr,
        )
        return 5
    if not args.allow_partial and (stats.files_failed or stats.files_rejected):
        print("未激活：存在解析失败或质量拒绝；旧 generation 保持 active", file=sys.stderr)
        return 4

    generation_manifest = index_dir / "generation_manifest.json"
    generation_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest_path = persist_dir / "demo_index_manifest.json"
    _atomic_write_json(manifest_path, manifest)
    print(f"active_manifest={manifest_path}")
    return 0


def _create_encoder(args):
    if args.embedding == "hash":
        return HashEmbedding(dimension=args.hash_dimension)
    return SentenceTransformerEmbedding(
        args.model,
        device=args.device,
        cache_folder=str(args.model_cache.resolve()) if args.model_cache else None,
        revision=args.model_revision,
        local_files_only=args.local_files_only,
    )


def _create_store(args, persist_dir: Path):
    if args.store == "sqlite":
        return SQLiteVectorStore(persist_dir / "vectors.sqlite3", args.collection)
    return ChromaVectorStore(persist_dir / "chroma", args.collection)


def _embedding_fingerprint(args, encoder) -> str:
    identity = {
        "backend": args.embedding,
        "model": getattr(encoder, "model_name", args.model),
        "dimension": int(encoder.dimension),
        "revision": args.model_revision,
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _atomic_write_json(path: Path, payload: dict) -> None:
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_path.replace(path)


def _configure_utf8_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
