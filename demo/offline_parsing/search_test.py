from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from demo.offline_parsing.embedding_store import (  # noqa: E402
    ChromaVectorStore,
    HashEmbedding,
    SentenceTransformerEmbedding,
    SQLiteVectorStore,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Top-K 来源/页码验收")
    parser.add_argument("--persist-dir", type=Path, required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=_positive_int, default=5)
    parser.add_argument("--expected-source")
    parser.add_argument("--expected-page", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_console()
    args = build_parser().parse_args(argv)
    persist_dir = args.persist_dir.resolve()
    manifest_path = persist_dir / "demo_index_manifest.json"
    if not manifest_path.is_file():
        print(f"缺少索引 manifest: {manifest_path}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    encoder = _encoder_from_manifest(manifest)
    store = _store_from_manifest(manifest, persist_dir)
    try:
        query_vector = encoder.encode(
            [args.query],
            batch_size=1,
            show_progress_bar=False,
        )[0]
        results = store.query(query_vector, top_k=args.top_k)
    finally:
        close = getattr(store, "close", None)
        if callable(close):
            close()
    for rank, result in enumerate(results, start=1):
        page = result.metadata.get("page_number")
        print(
            json.dumps(
                {
                    "rank": rank,
                    "score": round(result.score, 6),
                    "source": result.metadata.get("source"),
                    "page_number": page,
                    "chunk_id": result.id,
                    "text": result.text[:160],
                },
                ensure_ascii=False,
            )
        )

    if args.expected_source is None and args.expected_page is None:
        return 0
    hit = any(
        _matches_expected(
            result.metadata,
            expected_source=args.expected_source,
            expected_page=args.expected_page,
        )
        for result in results
    )
    print(
        json.dumps(
            {
                "metric": "source_page_hit_at_k",
                "top_k": args.top_k,
                "hit": int(hit),
                "expected_source": args.expected_source,
                "expected_page": args.expected_page,
            },
            ensure_ascii=False,
        )
    )
    return 0 if hit else 3


def _encoder_from_manifest(manifest: dict):
    if manifest["embedding"] == "hash":
        return HashEmbedding(dimension=int(manifest["hash_dimension"]))
    return SentenceTransformerEmbedding(
        manifest["embedding_model"],
        device=manifest.get("device"),
        cache_folder=manifest.get("model_cache"),
        revision=manifest.get("model_revision"),
        local_files_only=bool(manifest.get("local_files_only")),
    )


def _store_from_manifest(manifest: dict, persist_dir: Path):
    index_dir = Path(manifest.get("index_dir") or persist_dir)
    if manifest["store"] == "sqlite":
        return SQLiteVectorStore(
            index_dir / "vectors.sqlite3",
            manifest["collection"],
        )
    return ChromaVectorStore(index_dir / "chroma", manifest["collection"])


def _matches_expected(
    metadata: dict,
    *,
    expected_source: str | None,
    expected_page: int | None,
) -> bool:
    source = str(metadata.get("source") or "").replace("\\", "/")
    page = metadata.get("page_number")
    source_matches = expected_source is None or source.endswith(
        expected_source.replace("\\", "/")
    )
    page_matches = expected_page is None or page == expected_page
    return source_matches and page_matches


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _configure_utf8_console() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
