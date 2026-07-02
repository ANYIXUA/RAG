import unittest

from rag_app.retrieval.answer_memory import (
    AnswerOverrideInput,
    AnswerOverridePatch,
    MemoryAnswerMemoryStore,
)


class AnswerMemoryTest(unittest.TestCase):
    def test_manual_override_round_trips_with_tenant_and_permission_checks(self) -> None:
        store = MemoryAnswerMemoryStore()
        record = store.upsert_override(
            AnswerOverrideInput(
                question="系统是不是故障了？",
                answer="系统当前故障，请稍后再试。",
                tenant_id="tenant-a",
                permission_tags=("public",),
                category="incident",
                ttl_seconds=1800,
                created_by="ops",
            )
        )

        hit = store.lookup(
            " 系统是不是故障了 ",
            tenant_id="tenant-a",
            permission_tags=("public",),
        )
        tenant_miss = store.lookup(
            "系统是不是故障了？",
            tenant_id="tenant-b",
            permission_tags=("public",),
        )
        permission_miss = store.lookup(
            "系统是不是故障了？",
            tenant_id="tenant-a",
            permission_tags=("OPS_L2",),
        )

        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit.answer, "系统当前故障，请稍后再试。")
        self.assertEqual(hit.source, "manual")
        self.assertEqual(hit.override_id, record.override_id)
        self.assertEqual(hit.answer_source, "redis_manual_override")
        self.assertFalse(record.promote_to_long_term)
        self.assertIsNone(tenant_miss)
        self.assertIsNone(permission_miss)

    def test_manual_override_beats_hot_cache_and_can_be_disabled(self) -> None:
        store = MemoryAnswerMemoryStore()
        store.upsert_hot_cache(
            question="系统是不是故障了？",
            answer="自动缓存答案",
            tenant_id="tenant-a",
            permission_tags=("public",),
            request_id="req-1",
            feedback_id="fb-1",
            ttl_seconds=600,
        )
        manual = store.upsert_override(
            AnswerOverrideInput(
                question="系统是不是故障了？",
                answer="人工应急答案",
                tenant_id="tenant-a",
                permission_tags=("public",),
                category="incident",
            )
        )

        first = store.lookup("系统是不是故障了？", "tenant-a", ("public",))
        store.patch_override(manual.override_id, AnswerOverridePatch(enabled=False))
        second = store.lookup("系统是不是故障了？", "tenant-a", ("public",))

        self.assertIsNotNone(first)
        assert first is not None
        self.assertEqual(first.answer, "人工应急答案")
        self.assertEqual(first.answer_source, "redis_manual_override")
        self.assertIsNotNone(second)
        assert second is not None
        self.assertEqual(second.answer, "自动缓存答案")
        self.assertEqual(second.answer_source, "redis_hot_cache")

    def test_transient_categories_are_never_promotable(self) -> None:
        store = MemoryAnswerMemoryStore()
        for category in ("incident", "outage", "maintenance", "notice", "campaign"):
            record = store.upsert_override(
                AnswerOverrideInput(
                    question=f"{category} 临时通知",
                    answer="临时口径",
                    tenant_id="tenant-a",
                    permission_tags=("public",),
                    category=category,
                    promote_to_long_term=True,
                )
            )
            self.assertFalse(record.promote_to_long_term)

    def test_negative_feedback_stats_do_not_create_answer_hit(self) -> None:
        store = MemoryAnswerMemoryStore()
        stats = store.record_negative_feedback(
            question="系统是不是故障了？",
            tenant_id="tenant-a",
            permission_tags=("public",),
            request_id="req-1",
            feedback_id="fb-1",
            labels=("bad_answer",),
        )
        hit = store.lookup("系统是不是故障了？", "tenant-a", ("public",))

        self.assertEqual(stats.count, 1)
        self.assertEqual(stats.last_request_id, "req-1")
        self.assertIn("bad_answer", stats.labels)
        self.assertIsNone(hit)


if __name__ == "__main__":
    unittest.main()
