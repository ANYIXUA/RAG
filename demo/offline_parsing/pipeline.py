from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Iterable, Protocol, Sequence

from .chunking import iter_document_chunks
from .embedding_store import Encoder, embed_with_dynamic_batch
from .models import ParsedDocument, TextChunk


class BatchStore(Protocol):
    def upsert(
        self,
        chunks: Sequence[TextChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> int:
        ...


@dataclass
class IngestStats:
    files_succeeded: int = 0
    files_failed: int = 0
    files_rejected: int = 0
    pages_parsed: int = 0
    chunks_created: int = 0
    chunks_written: int = 0
    parse_seconds: float = 0.0
    chunk_seconds: float = 0.0
    embedding_seconds: float = 0.0
    write_seconds: float = 0.0
    total_seconds: float = 0.0
    oom_retries: int = 0
    effective_batch_size: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)

    @property
    def files_seen(self) -> int:
        return self.files_succeeded + self.files_failed + self.files_rejected

    @property
    def chunks_per_second(self) -> float:
        if self.total_seconds <= 0:
            return 0.0
        return self.chunks_written / self.total_seconds

    def to_dict(self) -> dict:
        result = asdict(self)
        result["files_seen"] = self.files_seen
        result["chunks_per_second"] = round(self.chunks_per_second, 3)
        for key in [name for name in result if name.endswith("_seconds")]:
            result[key] = round(float(result[key]), 4)
        return result


def ingest_documents(
    documents: Iterable[ParsedDocument],
    *,
    encoder: Encoder,
    store: BatchStore,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    batch_size: int = 64,
    min_batch_size: int = 1,
    show_progress_bar: bool = True,
) -> IngestStats:
    """逐文档切片，只在内存中保留一个写库 batch。"""

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")
    stats = IngestStats(effective_batch_size=batch_size)
    started = time.perf_counter()
    buffer: list[TextChunk] = []
    current_batch_size = batch_size

    for document in documents:
        stats.pages_parsed += len(document.pages)
        stats.parse_seconds += document.parse_seconds
        if document.quality_status not in {"parsed_success", "parsed_with_warning"}:
            stats.files_rejected += 1
            stats.errors.append(
                {
                    "source": document.source,
                    "error_type": "quality_rejected",
                    "error_message": ",".join(document.quality_warnings),
                }
            )
            continue
        stats.files_succeeded += 1
        chunk_iterator = iter_document_chunks(
            document,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        while True:
            chunk_started = time.perf_counter()
            try:
                chunk = next(chunk_iterator)
            except StopIteration:
                stats.chunk_seconds += time.perf_counter() - chunk_started
                break
            stats.chunk_seconds += time.perf_counter() - chunk_started
            stats.chunks_created += 1
            buffer.append(chunk)
            if len(buffer) == batch_size:
                current_batch_size = _embed_and_write(
                    buffer,
                    encoder=encoder,
                    store=store,
                    current_batch_size=current_batch_size,
                    min_batch_size=min_batch_size,
                    show_progress_bar=show_progress_bar,
                    stats=stats,
                )
                buffer.clear()

    if buffer:
        current_batch_size = _embed_and_write(
            buffer,
            encoder=encoder,
            store=store,
            current_batch_size=current_batch_size,
            min_batch_size=min_batch_size,
            show_progress_bar=show_progress_bar,
            stats=stats,
        )
    stats.effective_batch_size = current_batch_size
    stats.total_seconds = time.perf_counter() - started
    return stats


def _embed_and_write(
    chunks: Sequence[TextChunk],
    *,
    encoder: Encoder,
    store: BatchStore,
    current_batch_size: int,
    min_batch_size: int,
    show_progress_bar: bool,
    stats: IngestStats,
) -> int:
    embedding_started = time.perf_counter()
    result = embed_with_dynamic_batch(
        encoder,
        [chunk.text for chunk in chunks],
        initial_batch_size=current_batch_size,
        min_batch_size=min_batch_size,
        show_progress_bar=show_progress_bar,
    )
    stats.embedding_seconds += time.perf_counter() - embedding_started
    stats.oom_retries += result.oom_retries

    write_started = time.perf_counter()
    written = store.upsert(chunks, result.embeddings)
    stats.write_seconds += time.perf_counter() - write_started
    stats.chunks_written += written
    return result.effective_batch_size
