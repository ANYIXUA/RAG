from __future__ import annotations

import tempfile
import unittest
import json
import os
import inspect
from pathlib import Path

from demo.offline_parsing.chunking import iter_document_chunks, split_document
from demo.offline_parsing.embedding_store import (
    ChromaVectorStore,
    HashEmbedding,
    SQLiteVectorStore,
    embed_with_dynamic_batch,
)
from demo.offline_parsing.models import ParsedDocument, ParsedPage, TableCandidate
from demo.offline_parsing.make_sample_data import _make_mixed_pdf
from demo.offline_parsing.ingest_demo import main as ingest_main
from demo.offline_parsing.parsing import (
    batched,
    clean_pages,
    iter_parsed_documents,
    parse_document_file,
    partition_paths,
    recommended_worker_counts,
)
from demo.offline_parsing.pipeline import ingest_documents
from demo.offline_parsing.quality import validate_expected_pairs
from demo.offline_parsing.table_continuation import (
    extract_table_candidates,
    merge_table_candidates,
    table_to_chunk,
)


class ParsingHelpersTest(unittest.TestCase):
    def test_clean_pages_removes_repeated_margins_and_garbled_characters(self) -> None:
        pages = [
            ParsedPage(
                page_number=index,
                text=(
                    "XX 公司运维手册\n"
                    f"第 {index} 章\n"
                    "安全警告：断电后再操作！！！\ufffd\x00\n"
                    f"第 {index} 页"
                ),
            )
            for index in range(1, 4)
        ]

        cleaned = clean_pages(pages, repeated_margin_ratio=0.66)

        self.assertTrue(all("XX 公司运维手册" not in page.text for page in cleaned))
        self.assertTrue(all(f"第 {page.page_number} 页" not in page.text for page in cleaned))
        self.assertTrue(all("安全警告：断电后再操作!!!" in page.text for page in cleaned))
        self.assertTrue(all("\ufffd" not in page.text and "\x00" not in page.text for page in cleaned))

    def test_paths_are_routed_by_format_and_workers_are_bounded(self) -> None:
        pdfs, io_files = partition_paths(
            [Path("a.PDF"), Path("b.docx"), Path("c.txt")]
        )

        self.assertEqual([path.name for path in pdfs], ["a.PDF"])
        self.assertEqual([path.name for path in io_files], ["b.docx", "c.txt"])
        cpu_workers, io_workers = recommended_worker_counts(cpu_count=8)
        self.assertEqual(cpu_workers, 7)
        self.assertEqual(io_workers, 32)
        high_cpu_workers, _ = recommended_worker_counts(cpu_count=64)
        self.assertEqual(high_cpu_workers, 61 if os.name == "nt" else 63)

    def test_numeric_business_lines_are_not_mistaken_for_page_numbers(self) -> None:
        pages = [
            ParsedPage(page_number=1, text="E101\n正文 1"),
            ParsedPage(page_number=2, text="E102\n正文 2"),
            ParsedPage(page_number=3, text="E103\n正文 3"),
        ]

        cleaned = clean_pages(pages, repeated_margin_ratio=0.66)

        self.assertEqual(
            [page.text for page in cleaned],
            ["E101\n正文 1", "E102\n正文 2", "E103\n正文 3"],
        )

    def test_batched_is_a_generator_and_never_materializes_all_input(self) -> None:
        consumed: list[int] = []

        def source():
            for value in range(5):
                consumed.append(value)
                yield value

        batches = batched(source(), 2)
        self.assertEqual(consumed, [])
        self.assertEqual(next(batches), [0, 1])
        self.assertEqual(consumed, [0, 1])
        self.assertEqual(list(batches), [[2, 3], [4]])

    def test_parallel_parser_yields_sorted_txt_results_and_isolates_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "b.txt").write_text("第二份文档", encoding="utf-8")
            (root / "a.txt").write_text("第一份文档", encoding="utf-8")
            missing = root / "missing.txt"

            outcomes = list(
                iter_parsed_documents(
                    [root / "b.txt", missing, root / "a.txt"],
                    source_dir=root,
                    parse_batch_size=2,
                    io_workers=2,
                )
            )

        successes = [outcome.document for outcome in outcomes if outcome.document]
        failures = [outcome for outcome in outcomes if outcome.error_type]
        self.assertEqual([document.source for document in successes], ["a.txt", "b.txt"])
        self.assertEqual(failures[0].source, "missing.txt")
        self.assertEqual(failures[0].error_type, "FileNotFoundError")


class ChunkingTest(unittest.TestCase):
    def test_chunk_iterator_is_lazy(self) -> None:
        document = ParsedDocument(
            document_id="lazy-doc",
            source="lazy.txt",
            source_path="C:/data/lazy.txt",
            pages=[ParsedPage(page_number=1, text="文" * 1200)],
            parser="txt",
        )

        iterator = iter_document_chunks(document, chunk_size=800, chunk_overlap=120)

        self.assertEqual(inspect.getgeneratorstate(iterator), inspect.GEN_CREATED)
        self.assertEqual(next(iterator).metadata["start_unit"], 0)
        self.assertEqual(next(iterator).metadata["start_unit"], 680)

    def test_uses_800_120_windows_and_keeps_trace_metadata(self) -> None:
        document = ParsedDocument(
            document_id="doc-stable",
            source="manual.txt",
            source_path="C:/data/manual.txt",
            pages=[ParsedPage(page_number=7, text="运" * 1200)],
            parser="txt",
        )

        chunks = split_document(document, chunk_size=800, chunk_overlap=120)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(
            [(chunk.metadata["start_unit"], chunk.metadata["end_unit"]) for chunk in chunks],
            [(0, 800), (680, 1200)],
        )
        for chunk in chunks:
            self.assertEqual(chunk.metadata["source"], "manual.txt")
            self.assertEqual(chunk.metadata["page"], 7)
            self.assertEqual(chunk.metadata["chunk_id"], chunk.id)
        self.assertEqual(
            [chunk.id for chunk in chunks],
            [
                chunk.id
                for chunk in split_document(
                    document,
                    chunk_size=800,
                    chunk_overlap=120,
                )
            ],
        )


class DynamicBatchTest(unittest.TestCase):
    def test_halves_batch_after_oom_and_retries_same_texts(self) -> None:
        encoder = _OOMEncoder(max_batch=2)
        texts = [f"文本 {index}" for index in range(5)]

        result = embed_with_dynamic_batch(
            encoder,
            texts,
            initial_batch_size=8,
            min_batch_size=1,
            show_progress_bar=False,
        )

        self.assertEqual(len(result.embeddings), len(texts))
        self.assertEqual(result.effective_batch_size, 2)
        self.assertEqual(encoder.batch_lengths[:3], [5, 4, 2])

    def test_hash_embeddings_and_sqlite_store_support_top_k_traceability(self) -> None:
        embedder = HashEmbedding(dimension=128)
        chunks = [
            _chunk("a", "E203 地址校验失败，请核对省市区。", "codes.txt", 1),
            _chunk("b", "E504 下游接口超时，请稍后重试。", "timeouts.txt", 2),
        ]
        embeddings = embedder.encode(
            [chunk.text for chunk in chunks],
            batch_size=64,
            show_progress_bar=False,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteVectorStore(Path(temp_dir) / "vectors.sqlite3", "demo")
            store.upsert(chunks, embeddings)
            query_vector = embedder.encode(
                ["E203 地址为什么校验失败"],
                batch_size=1,
                show_progress_bar=False,
            )[0]
            results = store.query(query_vector, top_k=1)

        self.assertEqual(results[0].metadata["source"], "codes.txt")
        self.assertEqual(results[0].metadata["page"], 1)

    def test_chroma_upsert_is_one_batch_and_metadata_is_scalar(self) -> None:
        collection = _FakeChromaCollection()
        store = ChromaVectorStore.from_collection(collection)
        chunks = [
            _chunk("a", "正文", "manual.pdf", 3, section_path=["第一章", "告警"]),
            _chunk("b", "另一段", "manual.pdf", 4),
        ]

        store.upsert(chunks, [[1.0, 0.0], [0.0, 1.0]])

        self.assertEqual(len(collection.upsert_calls), 1)
        payload = collection.upsert_calls[0]
        self.assertEqual(payload["ids"], ["a", "b"])
        self.assertIsInstance(payload["metadatas"][0]["section_path"], str)

    def test_pipeline_upserts_130_chunks_as_64_64_2(self) -> None:
        pages = [
            ParsedPage(page_number=index + 1, text=f"标题 {index}\n" + ("文" * 20))
            for index in range(130)
        ]
        document = ParsedDocument(
            document_id="many-pages",
            source="many.txt",
            source_path="C:/data/many.txt",
            pages=pages,
            parser="txt",
        )
        store = _RecordingStore()

        stats = ingest_documents(
            [document],
            encoder=HashEmbedding(dimension=64),
            store=store,
            chunk_size=800,
            chunk_overlap=120,
            batch_size=64,
            show_progress_bar=False,
        )

        self.assertEqual(store.batch_lengths, [64, 64, 2])
        self.assertEqual(stats.chunks_written, 130)
        self.assertGreaterEqual(stats.chunks_per_second, 0.0)

    def test_quality_rejected_document_is_not_written(self) -> None:
        document = ParsedDocument(
            document_id="badcase",
            source="scan.pdf",
            source_path="C:/data/scan.pdf",
            pages=[ParsedPage(page_number=1, text="")],
            parser="pymupdf",
            quality_status="needs_review",
            quality_warnings=["empty_text", "ocr_required"],
        )
        store = _RecordingStore()

        stats = ingest_documents(
            [document],
            encoder=HashEmbedding(dimension=64),
            store=store,
            show_progress_bar=False,
        )

        self.assertEqual(stats.files_rejected, 1)
        self.assertEqual(stats.chunks_written, 0)
        self.assertEqual(store.batch_lengths, [])

    def test_batch_one_oom_and_non_oom_errors_are_not_swallowed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "out of memory"):
            embed_with_dynamic_batch(
                _OOMEncoder(max_batch=0),
                ["文本"],
                initial_batch_size=1,
                min_batch_size=1,
                show_progress_bar=False,
            )
        with self.assertRaisesRegex(RuntimeError, "model unavailable"):
            embed_with_dynamic_batch(
                _BrokenEncoder(),
                ["文本"],
                initial_batch_size=8,
                min_batch_size=1,
                show_progress_bar=False,
            )


class QualityGateTest(unittest.TestCase):
    def test_keywords_present_but_swapped_pairs_still_fail(self) -> None:
        result = validate_expected_pairs(
            actual_text="E203 下游接口超时\nE504 地址校验失败",
            expected_pairs={
                "E203": "地址校验失败",
                "E504": "下游接口超时",
            },
        )

        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "needs_review")
        self.assertEqual(set(result.mismatched_keys), {"E203", "E504"})

    def test_cli_builds_new_generation_before_switching_active_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            persist_dir = root / "index"
            source_dir.mkdir()
            source = source_dir / "manual.txt"
            source.write_text("OLD_MARKER legacy text", encoding="utf-8")
            common_args = [
                "--input",
                str(source_dir),
                "--persist-dir",
                str(persist_dir),
                "--store",
                "sqlite",
                "--embedding",
                "hash",
                "--no-progress",
            ]
            self.assertEqual(ingest_main(common_args), 0)
            first = json.loads(
                (persist_dir / "demo_index_manifest.json").read_text(encoding="utf-8")
            )

            source.write_text("NEW_MARKER replacement text", encoding="utf-8")
            self.assertEqual(ingest_main(common_args), 0)
            second = json.loads(
                (persist_dir / "demo_index_manifest.json").read_text(encoding="utf-8")
            )

            self.assertNotEqual(first["generation_id"], second["generation_id"])
            active_store = SQLiteVectorStore(
                Path(second["index_dir"]) / "vectors.sqlite3",
                second["collection"],
            )
            self.assertEqual(active_store.count(), 1)
            query_vector = HashEmbedding(dimension=384).encode(
                ["NEW_MARKER"], batch_size=1, show_progress_bar=False
            )[0]
            self.assertIn("NEW_MARKER", active_store.query(query_vector, top_k=1)[0].text)

            source.write_text("UNPUBLISHED_MARKER", encoding="utf-8")
            (source_dir / "broken.docx").write_bytes(b"not-a-zip-package")
            self.assertEqual(ingest_main(common_args), 4)
            after_failed_build = json.loads(
                (persist_dir / "demo_index_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                after_failed_build["generation_id"],
                second["generation_id"],
            )


class CrossPageTableTest(unittest.TestCase):
    def test_empty_pdf_is_marked_needs_review_and_ocr_required(self) -> None:
        try:
            import fitz
        except ModuleNotFoundError:
            self.skipTest("PyMuPDF is not installed")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "scan.pdf"
            document = fitz.open()
            document.new_page()
            document.save(path)
            document.close()

            parsed = parse_document_file(path, source_dir=root)

        self.assertEqual(parsed.quality_status, "needs_review")
        self.assertIn("ocr_required", parsed.quality_warnings)

    def test_mixed_pdf_generator_keeps_page_handles_valid(self) -> None:
        try:
            import fitz
        except ModuleNotFoundError:
            self.skipTest("PyMuPDF is not installed")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "mixed.pdf"
            _make_mixed_pdf(path)
            with fitz.open(path) as document:
                self.assertEqual(document.page_count, 2)
                self.assertIn(
                    "Normal paragraph after the continued table.",
                    document.load_page(1).get_text("text"),
                )
            merged = merge_table_candidates(extract_table_candidates(path))
            cell_text = " ".join(
                cell
                for table in merged
                for row in table.rows
                for cell in row.values
            )
            self.assertNotIn("Normal paragraph after", cell_text)

    def test_merges_headerless_continuation_and_preserves_row_source_pages(self) -> None:
        tables = [
            TableCandidate(
                page_number=1,
                bbox=(40.0, 500.0, 550.0, 790.0),
                page_width=595.0,
                page_height=842.0,
                rows=[
                    ["错误码", "含义"],
                    ["E203", "地址校验失败"],
                ],
            ),
            TableCandidate(
                page_number=2,
                bbox=(40.0, 30.0, 550.0, 220.0),
                page_width=595.0,
                page_height=842.0,
                rows=[
                    ["E504", "下游接口超时"],
                    ["E601", "库存不足"],
                ],
            ),
        ]

        merged = merge_table_candidates(tables)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0].header, ["错误码", "含义"])
        self.assertEqual(
            [(row.values[0], row.source_page) for row in merged[0].rows],
            [("E203", 1), ("E504", 2), ("E601", 2)],
        )
        self.assertEqual(merged[0].source_pages, [1, 2])
        chunk = table_to_chunk(merged[0], source="mixed.pdf")
        self.assertEqual(chunk.metadata["source_pages"], [1, 2])
        self.assertEqual(chunk.metadata["table_id"], merged[0].table_id)
        self.assertIn("E504\t下游接口超时", chunk.text)


class _OOMEncoder:
    def __init__(self, max_batch: int) -> None:
        self.max_batch = max_batch
        self.batch_lengths: list[int] = []

    def encode(self, sentences, *, batch_size: int, show_progress_bar: bool):
        del batch_size, show_progress_bar
        self.batch_lengths.append(len(sentences))
        if len(sentences) > self.max_batch:
            raise RuntimeError("CUDA out of memory")
        return [[float(len(text))] for text in sentences]


class _FakeChromaCollection:
    def __init__(self) -> None:
        self.upsert_calls: list[dict] = []

    def upsert(self, **kwargs) -> None:
        self.upsert_calls.append(kwargs)

    def query(self, **kwargs):
        raise AssertionError(f"query should not be called: {kwargs}")


class _BrokenEncoder:
    def encode(self, sentences, *, batch_size: int, show_progress_bar: bool):
        del sentences, batch_size, show_progress_bar
        raise RuntimeError("model unavailable")


class _RecordingStore:
    def __init__(self) -> None:
        self.batch_lengths: list[int] = []

    def upsert(self, chunks, embeddings) -> int:
        self.batch_lengths.append(len(chunks))
        self.assert_lengths_equal = len(chunks) == len(embeddings)
        if not self.assert_lengths_equal:
            raise AssertionError("chunks and embeddings must align")
        return len(chunks)


def _chunk(
    chunk_id: str,
    text: str,
    source: str,
    page: int,
    **metadata,
):
    from demo.offline_parsing.models import TextChunk

    return TextChunk(
        id=chunk_id,
        document_id=f"doc-{source}",
        text=text,
        metadata={
            "chunk_id": chunk_id,
            "source": source,
            "page": page,
            **metadata,
        },
    )


if __name__ == "__main__":
    unittest.main()
