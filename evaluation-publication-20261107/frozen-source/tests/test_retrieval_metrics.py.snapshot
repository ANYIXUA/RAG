"""Chunk ID 排序指标的回归测试。"""

from __future__ import annotations

import math
import unittest

from rag_app.operations.retrieval_metrics import (
    coverage_at_k,
    dedupe_preserving_order,
    first_relevant_rank,
    hit_at_k,
    ndcg_at_k,
    percentile,
    recall_at_k,
    reciprocal_rank_at_k,
)


class HitAtKTest(unittest.TestCase):
    def test_hit_inside_truncation(self) -> None:
        self.assertTrue(hit_at_k(["a", "b", "c"], {"c"}, 3))

    def test_miss_outside_truncation(self) -> None:
        self.assertFalse(hit_at_k(["a", "b", "c"], {"c"}, 2))

    def test_empty_relevant_is_miss(self) -> None:
        self.assertFalse(hit_at_k(["a"], set(), 10))

    def test_non_positive_k_is_zero(self) -> None:
        self.assertFalse(hit_at_k(["a"], {"a"}, 0))


class FirstRelevantRankTest(unittest.TestCase):
    def test_rank_is_one_based(self) -> None:
        self.assertEqual(first_relevant_rank(["a", "b"], {"b"}, 10), 2)

    def test_first_of_several_relevant_wins(self) -> None:
        self.assertEqual(first_relevant_rank(["a", "b", "c"], {"b", "c"}, 10), 2)

    def test_returns_none_when_absent(self) -> None:
        self.assertIsNone(first_relevant_rank(["a"], {"z"}, 10))

    def test_respects_truncation(self) -> None:
        self.assertIsNone(first_relevant_rank(["x", "a"], {"a"}, 1))


class ReciprocalRankTest(unittest.TestCase):
    def test_mrr_component(self) -> None:
        self.assertAlmostEqual(reciprocal_rank_at_k(["x", "y", "a"], {"a"}, 10), 1 / 3)

    def test_miss_is_zero(self) -> None:
        self.assertEqual(reciprocal_rank_at_k(["x"], {"a"}, 10), 0.0)


class NdcgTest(unittest.TestCase):
    def test_single_relevant_at_first_position_is_one(self) -> None:
        self.assertAlmostEqual(ndcg_at_k(["a", "b"], {"a"}, 10), 1.0)

    def test_single_relevant_second_position(self) -> None:
        self.assertAlmostEqual(
            ndcg_at_k(["x", "a"], {"a"}, 10),
            1.0 / math.log2(3),
        )

    def test_two_relevant_chunks_use_full_ideal(self) -> None:
        expected_dcg = 1.0 + 1.0 / math.log2(4)
        expected_idcg = 1.0 + 1.0 / math.log2(3)
        self.assertAlmostEqual(
            ndcg_at_k(["b", "x", "a"], {"a", "b"}, 10),
            expected_dcg / expected_idcg,
        )

    def test_ideal_hits_capped_by_k(self) -> None:
        # 三个相关但 k=2，IDCG 只能算两个位置。
        expected_idcg = 1.0 + 1.0 / math.log2(3)
        self.assertAlmostEqual(
            ndcg_at_k(["a", "b", "c"], {"a", "b", "c"}, 2),
            1.0,
        )
        self.assertAlmostEqual(
            ndcg_at_k(["a", "x"], {"a", "b", "c"}, 2),
            1.0 / expected_idcg,
        )

    def test_empty_inputs_return_zero(self) -> None:
        self.assertEqual(ndcg_at_k([], {"a"}, 10), 0.0)
        self.assertEqual(ndcg_at_k(["a"], set(), 10), 0.0)
        self.assertEqual(ndcg_at_k(["a"], {"a"}, 0), 0.0)


class RecallTest(unittest.TestCase):
    def test_partial_coverage(self) -> None:
        self.assertAlmostEqual(recall_at_k(["a", "x"], {"a", "b"}, 10), 0.5)

    def test_full_coverage(self) -> None:
        self.assertAlmostEqual(recall_at_k(["a", "b"], {"a", "b"}, 10), 1.0)

    def test_truncation_limits_recall(self) -> None:
        self.assertAlmostEqual(recall_at_k(["a", "b"], {"a", "b"}, 1), 0.5)

    def test_empty_relevant_is_zero(self) -> None:
        self.assertEqual(recall_at_k(["a"], set(), 10), 0.0)


class CoverageTest(unittest.TestCase):
    def test_required_evidence_all_present(self) -> None:
        self.assertAlmostEqual(coverage_at_k(["a", "b"], {"a", "b"}, 10), 1.0)

    def test_required_evidence_missing_one(self) -> None:
        self.assertAlmostEqual(coverage_at_k(["a"], {"a", "b"}, 10), 0.5)


class DedupeTest(unittest.TestCase):
    def test_first_occurrence_kept(self) -> None:
        self.assertEqual(dedupe_preserving_order(["a", "b", "a"]), ["a", "b"])

    def test_duplicates_do_not_inflate_ndcg(self) -> None:
        self.assertAlmostEqual(
            ndcg_at_k(["a", "a", "a"], {"a", "b"}, 10),
            1.0 / (1.0 + 1.0 / math.log2(3)),
        )


class PercentileTest(unittest.TestCase):
    def test_linear_interpolation(self) -> None:
        self.assertAlmostEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.5), 2.5)

    def test_p95_of_ten_values(self) -> None:
        values = [float(i) for i in range(1, 11)]
        self.assertAlmostEqual(percentile(values, 0.95), 9.55)

    def test_empty_is_zero(self) -> None:
        self.assertEqual(percentile([], 0.95), 0.0)


if __name__ == "__main__":
    unittest.main()
