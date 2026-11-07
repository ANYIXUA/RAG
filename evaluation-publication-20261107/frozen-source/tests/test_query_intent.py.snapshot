import unittest

from rag_app.retrieval.query import recognize_intent, rewrite_query


class QueryIntentTest(unittest.TestCase):
    def test_recognizes_order_status_intent(self) -> None:
        result = recognize_intent("帮我查一下工单 WO202604290001 现在到哪了")

        self.assertEqual(result.intent_label, "query_order_status")
        self.assertGreaterEqual(result.confidence, 0.9)
        self.assertIn("WO202604290001", result.matched_keywords)

    def test_recognizes_error_explanation_intent(self) -> None:
        result = recognize_intent("接口返回 E203 是什么意思？")

        self.assertEqual(result.intent_label, "explain_error")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_recognizes_solution_intent(self) -> None:
        result = recognize_intent("用户说光猫红灯，现场怎么处理？")

        self.assertEqual(result.intent_label, "recommend_solution")
        self.assertIn("怎么处理", result.matched_keywords)

    def test_recognizes_colloquial_address_solution_intent(self) -> None:
        result = recognize_intent("地址不对装不了机咋办")

        self.assertEqual(result.intent_label, "recommend_solution")
        self.assertIn("咋办", result.matched_keywords)

    def test_recognizes_rule_intent(self) -> None:
        result = recognize_intent("跨区装机能不能派单，有什么规则？")

        self.assertEqual(result.intent_label, "query_rule")

    def test_falls_back_to_general_knowledge(self) -> None:
        result = recognize_intent("装维系统是什么")

        self.assertEqual(result.intent_label, "general_knowledge")
        self.assertLess(result.confidence, 0.5)

    def test_rewrites_colloquial_solution_query(self) -> None:
        intent = recognize_intent("光猫红灯咋办")
        result = rewrite_query("光猫红灯咋办", intent=intent)

        self.assertEqual(result.rewritten_query, "光猫 LOS 红灯怎么处理")
        self.assertIn("ONU", result.synonym_expansions)
        self.assertIn("光路异常", result.synonym_expansions)
        self.assertIn("排查步骤", result.semantic_expansions)
        self.assertIn("现场处理建议", result.retrieval_query)

    def test_rewrites_error_code_query(self) -> None:
        intent = recognize_intent("接口返回 e203 是啥意思")
        result = rewrite_query("接口返回 e203 是啥意思", intent=intent)

        self.assertIn("E203", result.rewritten_query)
        self.assertIn("接口返回说明", result.semantic_expansions)
        self.assertIn("错误码说明", result.retrieval_query)


if __name__ == "__main__":
    unittest.main()
