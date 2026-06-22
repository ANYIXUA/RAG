import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class DeepDocAdapterTest(unittest.TestCase):
    def test_parse_pdf_with_deepdoc_converts_parser_output_to_markdown(self) -> None:
        from rag_app.ingestion.deepdoc_adapter import parse_pdf_with_deepdoc

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "complex.pdf"
            path.write_bytes(b"%PDF-1.4\n")
            parser_result = (
                [
                    {"text": "第一页正文", "page_number": 1},
                    {"content": "第二页正文", "page": 2},
                ],
                [
                    {"text": "表格：故障现象=LOS 红灯；处理建议=检查光路", "page_number": 1}
                ],
            )
            fake_parser_module = types.SimpleNamespace(
                PdfParser=lambda: _FakeDeepDocPdfParser(parser_result)
            )

            with patch.dict(
                sys.modules,
                {
                    "deepdoc": types.SimpleNamespace(parser=fake_parser_module),
                    "deepdoc.parser": fake_parser_module,
                },
            ):
                parsed = parse_pdf_with_deepdoc(path)

        self.assertIn("# complex", parsed.text)
        self.assertIn("## 第1页", parsed.text)
        self.assertIn("第一页正文", parsed.text)
        self.assertIn("## 第2页", parsed.text)
        self.assertIn("第二页正文", parsed.text)
        self.assertIn("### DeepDoc 表格 1", parsed.text)
        self.assertIn("LOS 红灯", parsed.text)
        self.assertEqual(parsed.metadata["parser_name"], "pdf")
        self.assertEqual(parsed.metadata["parser_strategy"], "deepdoc_complex_pdf")
        self.assertEqual(parsed.metadata["deepdoc_used"], True)


class _FakeDeepDocPdfParser:
    def __init__(self, result) -> None:
        self.result = result

    def __call__(self, path, **kwargs):
        self.path = path
        self.kwargs = kwargs
        return self.result


if __name__ == "__main__":
    unittest.main()
