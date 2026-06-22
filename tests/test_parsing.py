from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_app.core.models import Document
from rag_app.ingestion.loaders import DirectoryDocumentLoader
from rag_app.ingestion.parsing import (
    PARSER_VERSION,
    PdfOcrPageResult,
    PdfPageContent,
    PdfPageReport,
    _average_ocr_confidence,
    _classify_pdf_document,
    _merge_pdf_ocr_results,
    _normalize_pdf_page_text,
    _pdf_page_report,
    _pdf_pages_requiring_ocr,
    _pdf_quality_summary,
    _select_pdf_table_parser_route,
    _should_use_deepdoc_for_pdf,
    _try_parse_pdf_with_deepdoc,
    clean_text,
    parse_document_file,
)
from rag_app.ingestion.deepdoc_adapter import DeepDocParsedPdf
from rag_app.indexing.chunking import WhitespaceChunker


class ParsingTest(unittest.TestCase):
    def test_clean_text_normalizes_blank_lines_and_bom(self) -> None:
        text = clean_text("\ufeff第一行  \r\n\r\n\r\n第二行  ")

        self.assertEqual(text, "第一行\n\n第二行")

    def test_parse_markdown_extracts_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            path = source_dir / "fault_cases.md"
            path.write_text(
                "# 装维常见故障案例\n\n## 光猫 LOS 红灯\n\n处理建议：检查尾纤。",
                encoding="utf-8",
            )

            document = parse_document_file(path, source_dir=source_dir)

            self.assertIsNotNone(document)
            self.assertEqual(document.metadata["title"], "装维常见故障案例")
            self.assertEqual(document.metadata["source_type"], "fault_case")
            self.assertEqual(document.metadata["business_module"], "故障处理")
            self.assertEqual(document.metadata["parser_name"], "markdown")
            self.assertEqual(document.metadata["parser_version"], PARSER_VERSION)
            self.assertEqual(document.metadata["source"], "fault_cases.md")

    def test_parse_markdown_front_matter_overrides_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            path = source_dir / "manual.md"
            path.write_text(
                "---\n"
                "title: 地址校验规则\n"
                "source_type: address_rule\n"
                "business_module: 地址校验\n"
                "tenant_id: tenant-a\n"
                "permission_tags: OPS_L2,MAE_TEAM\n"
                "---\n"
                "# 原始标题\n\n地址需要转换为标准地址。",
                encoding="utf-8",
            )

            document = parse_document_file(path, source_dir=source_dir)

            self.assertIsNotNone(document)
            self.assertEqual(document.metadata["title"], "地址校验规则")
            self.assertEqual(document.metadata["source_type"], "address_rule")
            self.assertEqual(document.metadata["business_module"], "地址校验")
            self.assertEqual(document.metadata["tenant_id"], "tenant-a")
            self.assertEqual(document.metadata["permission_tags"], ["OPS_L2", "MAE_TEAM"])
            self.assertGreaterEqual(document.metadata["block_count"], 2)
            self.assertEqual(document.parsed_blocks[0].block_type, "heading")
            self.assertEqual(document.parsed_blocks[-1].section_path, ["原始标题"])
            self.assertNotIn("---", document.text)

    def test_parse_html_preserves_headings_paragraphs_and_table_rows(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            path = source_dir / "manual.html"
            path.write_text(
                (
                    "<html><head><title>接口排障手册</title></head><body>"
                    "<h1>接口异常</h1><p>接口超时时先检查下游。</p>"
                    "<table><tr><th>故障现象</th><th>处理建议</th></tr>"
                    "<tr><td>接口超时</td><td>检查下游接口状态</td></tr></table>"
                    "</body></html>"
                ),
                encoding="utf-8",
            )

            document = parse_document_file(path, source_dir=source_dir)

            self.assertIsNotNone(document)
            self.assertEqual(document.metadata["parser_name"], "html")
            self.assertEqual(document.metadata["title"], "接口排障手册")
            self.assertIn("# 接口异常", document.text)
            self.assertIn("表格列：故障现象；处理建议", document.text)
            self.assertIn("表格行：故障现象=接口超时；处理建议=检查下游接口状态", document.text)
            self.assertTrue(any(block.block_type == "table" for block in document.parsed_blocks))

    def test_parse_csv_converts_rows_to_markdown_text(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            path = source_dir / "error_codes.csv"
            path.write_text(
                "error_code,message,advice\nE203,地址不存在,核对标准地址\n",
                encoding="utf-8",
            )

            document = parse_document_file(path, source_dir=source_dir)

            self.assertIsNotNone(document)
            self.assertEqual(document.metadata["parser_name"], "csv")
            self.assertEqual(document.metadata["source_type"], "error_code")
            self.assertIn("## 记录 1", document.text)
            self.assertIn("- error_code: E203", document.text)
            self.assertIn("- advice: 核对标准地址", document.text)

    def test_parse_json_converts_records_to_markdown_text(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            path = source_dir / "error_codes.json"
            path.write_text(
                (
                    '{"title":"异常码说明","errors":['
                    '{"error_code":"E203","message":"地址不存在","advice":"核对标准地址"}'
                    ']}'
                ),
                encoding="utf-8",
            )

            document = parse_document_file(path, source_dir=source_dir)

            self.assertIsNotNone(document)
            self.assertEqual(document.metadata["parser_name"], "json")
            self.assertEqual(document.metadata["record_count"], 1)
            self.assertEqual(document.metadata["source_type"], "error_code")
            self.assertIn("# 异常码说明", document.text)
            self.assertIn("## E203", document.text)
            self.assertIn("- advice: 核对标准地址", document.text)

    def test_error_code_records_keep_exact_match_metadata_on_chunks(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            path = source_dir / "error_codes.json"
            path.write_text(
                (
                    '{"title":"异常码说明","errors":['
                    '{"error_code":"e203","message":"地址不存在","advice":"核对标准地址"}'
                    ']}'
                ),
                encoding="utf-8",
            )

            document = parse_document_file(path, source_dir=source_dir)
            chunks = WhitespaceChunker(chunk_size=200, chunk_overlap=20).split_documents(
                [document]
            )

            self.assertIsNotNone(document)
            self.assertEqual(document.metadata["error_codes"], ["E203"])
            self.assertEqual(chunks[0].metadata["error_code"], "E203")
            self.assertEqual(chunks[0].metadata["error_codes"], ["E203"])
            self.assertIn("explain_error", chunks[0].metadata["intent_labels"])

    def test_plain_document_codes_are_detected_but_not_error_codes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            path = source_dir / "manual.md"
            path.write_text(
                "# 维护规程\n\nI6540、T16、J949 是资料条目编号，不是异常码。",
                encoding="utf-8",
            )

            document = parse_document_file(path, source_dir=source_dir)
            chunks = WhitespaceChunker(chunk_size=200, chunk_overlap=20).split_documents(
                [document]
            )

            self.assertIsNotNone(document)
            self.assertEqual(document.metadata["detected_codes"], ["I6540", "T16", "J949"])
            self.assertEqual(document.metadata["error_codes"], [])
            self.assertEqual(chunks[0].metadata["detected_codes"], ["I6540", "T16", "J949"])
            self.assertEqual(chunks[0].metadata["error_codes"], [])
            self.assertNotIn("error_code", chunks[0].metadata)

    def test_directory_loader_uses_parser(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            (source_dir / "sample.md").write_text("# 标题\n\n正文", encoding="utf-8")

            documents = DirectoryDocumentLoader(source_dir).load()

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].metadata["title"], "标题")

    def test_directory_loader_passes_complex_pdf_parser_to_parser(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            path = source_dir / "complex.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            parsed = Document(
                id="doc-1",
                text="parsed",
                metadata={
                    "source": "complex.pdf",
                    "source_path": str(path),
                    "title": "complex",
                },
            )

            with patch(
                "rag_app.ingestion.loaders.parse_document_file",
                return_value=parsed,
            ) as parser:
                documents = DirectoryDocumentLoader(
                    source_dir,
                    pdf_complex_parser="deepdoc",
                ).load()

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].id, "doc-1")
            parser.assert_called_once_with(
                path,
                source_dir=source_dir,
                pdf_complex_parser="deepdoc",
                pdf_bordered_table_parser="deepdoc",
                pdf_borderless_table_parser="mineru",
                pdf_semistructured_table_parser="rules_ml",
            )

    def test_parse_srt_builds_transcript_sections(self) -> None:
        with TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir)
            path = source_dir / "training.srt"
            path.write_text(
                (
                    "1\n"
                    "00:00:00,000 --> 00:00:03,000\n"
                    "光猫红灯通常是光路异常。\n\n"
                    "2\n"
                    "00:00:03,500 --> 00:00:06,000\n"
                    "先检查尾纤再看光功率。\n"
                ),
                encoding="utf-8",
            )

            document = parse_document_file(path, source_dir=source_dir)

            self.assertIsNotNone(document)
            self.assertEqual(document.metadata["parser_name"], "srt")
            self.assertEqual(document.metadata["source_type"], "video_transcript")
            self.assertEqual(document.metadata["business_module"], "培训资料")
            self.assertIn("## 片段 1", document.text)
            self.assertIn("00:00:00,000-00:00:03,000", document.text)

    def test_pdf_page_text_normalization_preserves_table_rows(self) -> None:
        text, table_like_lines = _normalize_pdf_page_text(
            "故障现象    可能原因    处理建议\n"
            "接口超时    下游异常    检查下游状态\n"
            "CPU 高    慢 SQL    优化索引"
        )

        self.assertEqual(table_like_lines, 3)
        self.assertIn("表格列：故障现象；可能原因；处理建议", text)
        self.assertIn("表格行：故障现象=接口超时；可能原因=下游异常；处理建议=检查下游状态", text)
        self.assertIn("表格行：故障现象=CPU 高；可能原因=慢 SQL；处理建议=优化索引", text)

    def test_pdf_quality_summary_marks_scanned_candidate(self) -> None:
        summary = _pdf_quality_summary(
            page_reports=[
                PdfPageReport(
                    page_number=1,
                    raw_text_length=0,
                    clean_text_length=0,
                    status="empty",
                    warning_codes=["empty_page"],
                ),
                PdfPageReport(
                    page_number=2,
                    raw_text_length=4,
                    clean_text_length=4,
                    status="low_text",
                    warning_codes=["low_text_page"],
                ),
            ],
            page_count=2,
        )

        self.assertEqual(summary["status"], "needs_review")
        self.assertTrue(summary["ocr_required"])
        self.assertEqual(summary["scanned_page_candidates"], 2)

    def test_pdf_pages_requiring_ocr_returns_empty_and_low_text_pages(self) -> None:
        pages = _pdf_pages_requiring_ocr(
            [
                PdfPageReport(
                    page_number=1,
                    raw_text_length=0,
                    clean_text_length=0,
                    status="empty",
                    warning_codes=["empty_page"],
                ),
                PdfPageReport(
                    page_number=2,
                    raw_text_length=100,
                    clean_text_length=100,
                    status="parsed",
                    warning_codes=[],
                ),
                PdfPageReport(
                    page_number=3,
                    raw_text_length=4,
                    clean_text_length=4,
                    status="low_text",
                    warning_codes=["low_text_page"],
                ),
            ]
        )

        self.assertEqual(pages, [1, 3])

    def test_deepdoc_pdf_parser_is_selected_only_for_complex_pdf(self) -> None:
        bordered_report = PdfPageReport(
            page_number=1,
            raw_text_length=20,
            clean_text_length=20,
            status="parsed_with_warning",
            warning_codes=["bordered_table_detected"],
            bordered_table_lines=12,
        )
        borderless_report = PdfPageReport(
            page_number=1,
            raw_text_length=80,
            clean_text_length=80,
            status="parsed_with_warning",
            warning_codes=["table_like_text_detected"],
            table_like_lines=4,
        )
        semistructured_report = PdfPageReport(
            page_number=1,
            raw_text_length=80,
            clean_text_length=80,
            status="parsed_with_warning",
            warning_codes=["semi_structured_table_detected"],
            semistructured_table_markers=4,
        )
        simple_report = PdfPageReport(
            page_number=1,
            raw_text_length=80,
            clean_text_length=80,
            status="parsed",
            warning_codes=[],
        )

        self.assertEqual(
            _select_pdf_table_parser_route(
                [bordered_report],
                bordered_table_parser="deepdoc",
                borderless_table_parser="mineru",
                semistructured_table_parser="rules_ml",
            ),
            "deepdoc",
        )
        self.assertEqual(
            _select_pdf_table_parser_route(
                [borderless_report],
                bordered_table_parser="deepdoc",
                borderless_table_parser="mineru",
                semistructured_table_parser="rules_ml",
            ),
            "mineru",
        )
        self.assertEqual(
            _select_pdf_table_parser_route(
                [semistructured_report],
                bordered_table_parser="deepdoc",
                borderless_table_parser="mineru",
                semistructured_table_parser="rules_ml",
            ),
            "rules_ml",
        )
        self.assertIsNone(
            _select_pdf_table_parser_route(
                [simple_report],
                bordered_table_parser="deepdoc",
                borderless_table_parser="mineru",
                semistructured_table_parser="rules_ml",
            )
        )
        self.assertTrue(_should_use_deepdoc_for_pdf("deepdoc", {"table_route": "deepdoc"}))

    def test_try_parse_pdf_with_deepdoc_wraps_adapter_result(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "complex.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            with patch(
                "rag_app.ingestion.deepdoc_adapter.parse_pdf_with_deepdoc",
                return_value=DeepDocParsedPdf(
                    text="# complex\n\n## 第1页\nDeepDoc 文本",
                    metadata={
                        "parser_name": "pdf",
                        "parser_strategy": "deepdoc_complex_pdf",
                        "deepdoc_used": True,
                    },
                ),
            ):
                parsed = _try_parse_pdf_with_deepdoc(
                    path,
                    {"status": "needs_review", "warnings": ["low_text_page"]},
                )

        self.assertIsNotNone(parsed)
        self.assertIn("DeepDoc 文本", parsed.text)
        self.assertEqual(parsed.metadata["parser_strategy"], "deepdoc_complex_pdf")
        self.assertEqual(parsed.metadata["deepdoc_used"], True)

    def test_pdf_ocr_results_replace_low_quality_page_text(self) -> None:
        merged = _merge_pdf_ocr_results(
            [
                PdfPageContent(
                    page_number=1,
                    raw_text="",
                    text="",
                    table_like_lines=0,
                ),
                PdfPageContent(
                    page_number=2,
                    raw_text="这是一页完整文字 PDF 内容，包含足够长的业务说明和处理步骤。",
                    text="这是一页完整文字 PDF 内容，包含足够长的业务说明和处理步骤。",
                    table_like_lines=0,
                ),
            ],
            [
                PdfOcrPageResult(
                    page_number=1,
                    text="扫描页 OCR 识别出的处理步骤",
                    confidence=0.91,
                ),
                PdfOcrPageResult(
                    page_number=2,
                    text="短",
                    confidence=0.99,
                ),
            ],
        )

        self.assertEqual(merged[0].extraction_method, "ocr")
        self.assertIn("扫描页 OCR", merged[0].text)
        self.assertEqual(merged[0].ocr_confidence, 0.91)
        self.assertEqual(merged[1].extraction_method, "text")

    def test_pdf_classification_distinguishes_text_and_ocr_documents(self) -> None:
        text_report = _pdf_page_report(
            page_number=1,
            raw_text="接口超时时先检查下游接口状态，并结合请求日志、链路监控和重试配置判断故障范围。",
            clean_text_value="接口超时时先检查下游接口状态，并结合请求日志、链路监控和重试配置判断故障范围。",
            table_like_lines=0,
        )
        ocr_report = _pdf_page_report(
            page_number=1,
            raw_text="",
            clean_text_value="扫描页 OCR 文本",
            table_like_lines=0,
            extraction_method="ocr",
            ocr_confidence=0.9,
        )

        self.assertEqual(_classify_pdf_document([text_report], 1), "text_pdf")
        self.assertEqual(_classify_pdf_document([ocr_report], 1), "ocr_pdf")
        self.assertEqual(
            _average_ocr_confidence(
                [
                    PdfPageContent(
                        page_number=1,
                        raw_text="",
                        text="扫描页 OCR 文本",
                        table_like_lines=0,
                        extraction_method="ocr",
                        ocr_confidence=0.9,
                    )
                ]
            ),
            0.9,
        )


if __name__ == "__main__":
    unittest.main()
