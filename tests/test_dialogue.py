import sys
import types
import unittest
from unittest.mock import patch

from rag_app.retrieval.dialogue import (
    ConversationTurn,
    RedisConversationMemory,
    rewrite_query_with_context,
)


class DialogueMemoryTest(unittest.TestCase):
    def test_rule_coreference_resolves_pronoun_to_recent_topic(self) -> None:
        history = [
            ConversationTurn(
                question="光猫 LOS 红灯怎么处理？",
                rewritten_query="光猫 LOS 红灯怎么处理 现场处理建议",
                intent_label="recommend_solution",
                retrieved_titles=["光猫 LOS 红灯"],
                answer_summary="先检查尾纤和光功率。",
            )
        ]

        contextual_query, is_follow_up, context_terms = rewrite_query_with_context(
            "这个要先看什么？",
            history,
        )

        self.assertTrue(is_follow_up)
        self.assertIn("光猫 LOS 红灯", contextual_query)
        self.assertIn("要先看什么", contextual_query)
        self.assertIn("光猫 LOS 红灯", context_terms)

    def test_rule_coreference_prefixes_short_follow_up_without_pronoun(self) -> None:
        history = [
            ConversationTurn(
                question="地址校验失败怎么处理？",
                rewritten_query="地址校验失败怎么处理",
                intent_label="query_rule",
                retrieved_titles=["地址校验失败"],
                answer_summary="先核对标准地址。",
            )
        ]

        contextual_query, is_follow_up, context_terms = rewrite_query_with_context(
            "下一步呢？",
            history,
        )

        self.assertTrue(is_follow_up)
        self.assertTrue(contextual_query.startswith("地址校验失败"))
        self.assertIn("下一步", contextual_query)
        self.assertIn("地址校验失败", context_terms)

    def test_redis_conversation_memory_round_trips_turns_and_sets_ttl(self) -> None:
        fake_redis = _FakeRedisModule()
        with patch.dict(sys.modules, {"redis": fake_redis}):
            first = RedisConversationMemory(
                redis_url="redis://localhost:6379/0",
                max_turns_per_session=2,
                ttl_seconds=60,
            )
            first.append_turn(
                "s-1",
                ConversationTurn(
                    question="第一问",
                    rewritten_query="第一问 改写",
                    intent_label="recommend_solution",
                    retrieved_titles=["标题1"],
                    answer_summary="回答1",
                ),
            )
            first.append_turn(
                "s-1",
                ConversationTurn(
                    question="第二问",
                    rewritten_query="第二问 改写",
                    intent_label="recommend_solution",
                    retrieved_titles=["标题2"],
                    answer_summary="回答2",
                ),
            )
            first.append_turn(
                "s-1",
                ConversationTurn(
                    question="第三问",
                    rewritten_query="第三问 改写",
                    intent_label="recommend_solution",
                    retrieved_titles=["标题3"],
                    answer_summary="回答3",
                ),
            )

            second = RedisConversationMemory(
                redis_url="redis://localhost:6379/0",
                max_turns_per_session=2,
                ttl_seconds=60,
            )
            turns = second.get_recent_turns("s-1", limit=5)

        self.assertEqual([turn.question for turn in turns], ["第二问", "第三问"])
        self.assertEqual(fake_redis.client.expirations["rag:conversation:s-1"], 60)


class _FakeRedisModule:
    def __init__(self) -> None:
        self.client = _FakeRedisClient()
        self.Redis = types.SimpleNamespace(from_url=lambda *args, **kwargs: self.client)


class _FakeRedisClient:
    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}
        self.expirations: dict[str, int] = {}

    def rpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).append(value)

    def ltrim(self, key: str, start: int, end: int) -> None:
        values = self.lists.get(key, [])
        if start < 0:
            start = max(len(values) + start, 0)
        if end < 0:
            end = len(values) + end
        self.lists[key] = values[start : end + 1]

    def expire(self, key: str, ttl_seconds: int) -> None:
        self.expirations[key] = ttl_seconds

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        values = self.lists.get(key, [])
        if start < 0:
            start = max(len(values) + start, 0)
        if end < 0:
            end = len(values) + end
        return values[start : end + 1]


if __name__ == "__main__":
    unittest.main()
