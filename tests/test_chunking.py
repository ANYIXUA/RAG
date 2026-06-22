import unittest

from rag_app.indexing.chunking import WhitespaceChunker
from rag_app.core.models import Document, ParsedBlock


class ChunkingTest(unittest.TestCase):
    def test_markdown_headings_create_separate_chunks(self) -> None:
        document = Document(
            id="doc-1",
            text=(
                "# 装维常见故障案例\n\n"
                "## 光猫 LOS 红灯\n\n"
                "光猫 LOS 红灯通常表示光路异常，需要检查尾纤和光功率。\n\n"
                "## 地址校验失败\n\n"
                "地址校验失败通常与标准地址不存在或资源未覆盖有关。"
            ),
            metadata={"source": "fault_cases.md"},
        )

        chunks = WhitespaceChunker(chunk_size=500, chunk_overlap=20).split_documents([document])

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].metadata["section_title"], "光猫 LOS 红灯")
        self.assertEqual(chunks[1].metadata["section_title"], "地址校验失败")
        self.assertEqual(chunks[0].metadata["business_module"], "设备维护")
        self.assertEqual(chunks[1].metadata["business_module"], "地址校验")
        self.assertIn("光猫 LOS 红灯", chunks[0].text)
        self.assertNotIn("地址校验失败", chunks[0].text)

    def test_parsed_blocks_keep_source_and_permission_metadata(self) -> None:
        document = Document(
            id="doc-1",
            text="# 接口异常\n\n接口超时时先检查下游。",
            metadata={
                "source": "manual.md",
                "tenant_id": "tenant-a",
                "permission_tags": ["OPS_L2"],
            },
            parsed_blocks=[
                ParsedBlock(
                    block_id="blk-1",
                    document_id="doc-1",
                    version_id="v1",
                    block_type="heading",
                    text="接口异常",
                    section_path=["接口异常"],
                ),
                ParsedBlock(
                    block_id="blk-2",
                    document_id="doc-1",
                    version_id="v1",
                    block_type="paragraph",
                    text="接口超时时先检查下游。",
                    section_path=["接口异常"],
                    parent_block_id="blk-1",
                    previous_block_id="blk-1",
                ),
            ],
        )

        chunks = WhitespaceChunker(chunk_size=500, chunk_overlap=20).split_documents([document])

        self.assertEqual(len(chunks), 1)
        self.assertIn("章节：接口异常", chunks[0].text)
        self.assertEqual(chunks[0].metadata["block_id"], "blk-2")
        self.assertEqual(chunks[0].metadata["source_block_ids"], ["blk-2"])
        self.assertEqual(chunks[0].metadata["tenant_id"], "tenant-a")
        self.assertEqual(chunks[0].metadata["permission_tags"], ["OPS_L2"])

    def test_parsed_block_chunks_keep_lightweight_parse_metadata(self) -> None:
        document = Document(
            id="doc-1",
            text="# PDF\n\nTable text",
            metadata={
                "source": "manual.pdf",
                "source_path": "D:/knowledge/manual.pdf",
                "filename": "manual.pdf",
                "extension": ".pdf",
                "title": "Manual",
                "source_type": "manual",
                "business_module": "Operations",
                "content_hash": "hash-1",
                "version_id": "v_hash_1",
                "tenant_id": "tenant-a",
                "permission_tags": ["OPS_L2"],
                "parser_name": "pdf",
                "parser_version": "parser-v1",
                "parser_strategy": "pymupdf_text_with_page_quality_report",
                "pdf_document_class": "mixed_text_table",
                "page_count": 10,
                "extracted_page_count": 8,
                "empty_page_count": 1,
                "low_text_page_count": 1,
                "scanned_page_candidates": 2,
                "table_like_page_count": 3,
                "parse_quality_status": "needs_review",
                "parse_warnings": ["ocr_disabled", "borderless_table_detected"],
                "ocr_required": True,
                "ocr_candidate_pages": [1],
                "ocr_applied": False,
                "ocr_provider": None,
                "ocr_page_count": 0,
                "ocr_pages": [],
                "ocr_confidence_avg": None,
                "ocr_unavailable_reason": "ocr is disabled",
                "table_parser_route": "mineru",
                "external_parser_attempted": True,
                "external_parser_used": True,
                "deepdoc_attempted": False,
                "deepdoc_used": False,
                "mineru_attempted": True,
                "mineru_used": True,
                "mineru_online_api_base": "https://mineru.example/api/v1/agent",
                "mineru_online_state": "done",
                "mineru_online_task_id": "task-1",
                "mineru_online_used": True,
                "rules_ml_attempted": False,
                "rules_ml_used": False,
                "block_count": 12,
                "pdf_page_reports": [
                    {
                        "page_number": 1,
                        "status": "parsed_with_warning",
                        "warning_codes": [
                            "table_like_text_detected",
                            "borderless_table_detected",
                        ],
                    }
                ],
            },
            parsed_blocks=[
                ParsedBlock(
                    block_id="blk-1",
                    document_id="doc-1",
                    version_id="v_hash_1",
                    block_type="table",
                    text="A | B\n1 | 2",
                    page_number=1,
                    section_path=["PDF"],
                    metadata={
                        "detected_codes": ["I6540", "T16", "J949"],
                        "error_codes": [],
                    },
                    quality_status="parsed_success",
                )
            ],
        )

        chunks = WhitespaceChunker(chunk_size=500, chunk_overlap=20).split_documents([document])

        metadata = chunks[0].metadata
        self.assertEqual(metadata["source"], "manual.pdf")
        self.assertEqual(metadata["parser_name"], "pdf")
        self.assertEqual(metadata["parser_strategy"], "pymupdf_text_with_page_quality_report")
        self.assertEqual(metadata["content_hash"], "hash-1")
        self.assertEqual(metadata["document_parse_quality_status"], "needs_review")
        self.assertEqual(metadata["chunk_parse_quality_status"], "parsed_success")
        self.assertEqual(metadata["document_ocr_status"], "required_disabled")
        self.assertEqual(metadata["document_ocr_page_count"], 0)
        self.assertEqual(metadata["table_parser_route"], "mineru")
        self.assertEqual(metadata["table_parse_status"], "applied")
        self.assertTrue(metadata["table_parse_applied"])
        self.assertNotIn("table_parse_skip_reason", metadata)
        self.assertEqual(
            metadata["page_warning_codes"],
            ["table_like_text_detected", "borderless_table_detected"],
        )
        self.assertEqual(
            metadata["chunk_parse_warning_codes"],
            ["table_like_text_detected", "borderless_table_detected"],
        )
        self.assertEqual(metadata["detected_codes"], ["I6540", "T16", "J949"])
        self.assertEqual(metadata["error_codes"], [])
        self.assertNotIn("parse_quality_status", metadata)
        self.assertNotIn("ocr_required", metadata)
        for heavy_key in (
            "parse_warnings",
            "ocr_candidate_pages",
            "ocr_pages",
            "ocr_confidence_avg",
            "ocr_unavailable_reason",
            "pdf_document_class",
            "page_count",
            "extracted_page_count",
            "empty_page_count",
            "low_text_page_count",
            "scanned_page_candidates",
            "table_like_page_count",
            "external_parser_attempted",
            "external_parser_used",
            "deepdoc_attempted",
            "deepdoc_used",
            "mineru_attempted",
            "mineru_used",
            "mineru_online_api_base",
            "mineru_online_state",
            "mineru_online_task_id",
            "mineru_online_used",
            "rules_ml_attempted",
            "rules_ml_used",
            "block_count",
            "pdf_page_reports",
        ):
            self.assertNotIn(heavy_key, metadata)

    def test_paragraph_chunks_record_table_parse_skip_reason(self) -> None:
        document = Document(
            id="doc-1",
            text="# PDF\n\nParagraph text",
            metadata={
                "source": "manual.pdf",
                "table_parser_route": "deepdoc",
                "external_parser_used": False,
                "parse_quality_status": "parsed_with_warning",
                "parse_warnings": ["bordered_table_detected"],
                "pdf_page_reports": [
                    {
                        "page_number": 147,
                        "warning_codes": ["bordered_table_detected"],
                    }
                ],
            },
            parsed_blocks=[
                ParsedBlock(
                    block_id="blk-1",
                    document_id="doc-1",
                    version_id="v1",
                    block_type="paragraph",
                    text="I6540、T16、J949 是普通资料编码。",
                    page_number=147,
                    section_path=["Manual", "第147页"],
                    quality_status="parsed_with_warning",
                    metadata={
                        "detected_codes": ["I6540", "T16", "J949"],
                        "error_codes": [],
                    },
                )
            ],
        )

        chunks = WhitespaceChunker(chunk_size=500, chunk_overlap=20).split_documents([document])

        metadata = chunks[0].metadata
        self.assertEqual(metadata["table_parser_route"], "deepdoc")
        self.assertFalse(metadata["table_parse_applied"])
        self.assertEqual(metadata["table_parse_status"], "skipped")
        self.assertEqual(metadata["table_parse_skip_reason"], "block_type_is_paragraph")
        self.assertEqual(metadata["page_warning_codes"], ["bordered_table_detected"])
        self.assertEqual(metadata["chunk_parse_warning_codes"], ["bordered_table_detected"])
        self.assertEqual(metadata["detected_codes"], ["I6540", "T16", "J949"])
        self.assertEqual(metadata["error_codes"], [])


if __name__ == "__main__":
    unittest.main()
