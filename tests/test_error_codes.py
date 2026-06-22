import unittest

from rag_app.core.error_codes import extract_detected_codes, extract_error_codes
from rag_app.retrieval.query import recognize_intent


class ErrorCodeExtractionTest(unittest.TestCase):
    def test_strict_error_codes_exclude_plain_document_codes(self) -> None:
        text = "本节引用 I6540、T16、J949 等普通资料编码，接口返回 E203 时按异常处理。"

        self.assertEqual(extract_detected_codes(text), ["I6540", "T16", "J949", "E203"])
        self.assertEqual(extract_error_codes(text), ["E203"])

    def test_error_context_promotes_non_e_prefix_codes(self) -> None:
        text = "错误码 A120 表示资源校验失败，处理建议为重新核对地址。"

        self.assertEqual(extract_detected_codes(text), ["A120"])
        self.assertEqual(extract_error_codes(text), ["A120"])

    def test_intent_does_not_treat_plain_document_code_as_error(self) -> None:
        result = recognize_intent("I6540 这一节讲的是什么？")

        self.assertNotEqual(result.intent_label, "explain_error")


if __name__ == "__main__":
    unittest.main()
