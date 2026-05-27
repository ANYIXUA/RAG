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


if __name__ == "__main__":
    unittest.main()
