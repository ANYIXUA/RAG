from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_app.operations.evaluation import (
    EvaluationThresholds,
    compare_rerank_runs,
    evaluate_release_gate,
    load_retrieval_eval_cases,
    save_evaluation_report,
)
from rag_app.indexing.offline import OfflineKnowledgeBuilder
from rag_app.retrieval.online import OnlineQueryProcessor
from tests.helpers import (
    DeterministicEmbedder,
    MemoryQueryLogStore,
    MemoryVectorStore,
    SimpleAnswerGenerator,
    production_settings,
)


class EvaluationTest(unittest.TestCase):
    def test_load_retrieval_eval_cases(self) -> None:
        with TemporaryDirectory() as temp_dir:
            dataset = Path(temp_dir) / "eval.jsonl"
            dataset.write_text(
                (
                    '{"query":"光猫红灯咋办",'
                    '"expected":[{"source":"fault.md","section_title":"光猫 LOS 红灯"}],'
                    '"intent_label":"recommend_solution",'
                    '"business_module":"故障处理",'
                    '"source_type":"故障案例",'
                    '"tags":["口语化","LOS"]}\n'
                ),
                encoding="utf-8",
            )

            cases = load_retrieval_eval_cases(dataset)

            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0].query, "光猫红灯咋办")
            self.assertEqual(cases[0].expected[0].source, "fault.md")
            self.assertEqual(cases[0].expected[0].section_title, "光猫 LOS 红灯")
            self.assertEqual(cases[0].intent_label, "recommend_solution")
            self.assertEqual(cases[0].business_module, "故障处理")
            self.assertEqual(cases[0].source_type, "故障案例")
            self.assertEqual(cases[0].tags, ["口语化", "LOS"])

    def test_compare_rerank_runs_with_noop_provider(self) -> None:
        with TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            data_dir = base_dir / "data"
            storage_dir = base_dir / "storage"
            data_dir.mkdir()
            (data_dir / "fault.md").write_text(
                "# 故障案例\n\n## 光猫 LOS 红灯\n\n光猫 LOS 红灯处理建议。",
                encoding="utf-8",
            )
            dataset = base_dir / "eval.jsonl"
            dataset.write_text(
                (
                    '{"query":"光猫红灯咋办","expected":[{"source":"fault.md","section_title":"光猫 LOS 红灯"}]}\n'
                ),
                encoding="utf-8",
            )
            settings = production_settings(
                base_dir,
                data_dir=data_dir,
                storage_dir=storage_dir,
                chunk_size=80,
                chunk_overlap=10,
                top_k=1,
                min_similarity_score=-1.0,
                relative_score_threshold=0.0,
                rerank_provider="none",
                rerank_candidate_k=5,
            )
            embedder = DeterministicEmbedder(settings.embedding_dimension)
            vector_store = MemoryVectorStore()
            answer_generator = SimpleAnswerGenerator()
            OfflineKnowledgeBuilder(
                settings,
                embedder=embedder,
                vector_store=vector_store,
            ).refresh(reset=True)
            cases = load_retrieval_eval_cases(dataset)

            def processor_factory(settings):
                return OnlineQueryProcessor(
                    settings=settings,
                    embedder=embedder,
                    vector_store=vector_store,
                    answer_generator=answer_generator,
                    query_log_store=MemoryQueryLogStore(),
                )

            with patch(
                "rag_app.operations.evaluation.OnlineQueryProcessor",
                side_effect=processor_factory,
            ):
                report = compare_rerank_runs(
                    settings=settings,
                    cases=cases,
                    top_k=1,
                    with_rerank_provider="none",
                )

            self.assertEqual(report["cases"], 1)
            self.assertEqual(report["runs"][0]["hit_at_k"], 1.0)
            self.assertEqual(report["runs"][1]["hit_at_k"], 1.0)
            self.assertEqual(report["runs"][1]["no_result_rate"], 0.0)
            self.assertIn("bucket_metrics", report["runs"][1])
            self.assertEqual(report["delta"]["hit_at_k"], 0.0)
            self.assertEqual(report["delta"]["no_result_rate"], 0.0)

    def test_release_gate_fails_when_absolute_metric_is_too_low(self) -> None:
        report = {
            "runs": [
                {
                    "name": "with_rerank",
                    "hit_at_k": 0.5,
                    "mrr": 0.5,
                    "no_result_rate": 0.0,
                    "avg_latency_ms": 10.0,
                    "p95_latency_ms": 15.0,
                }
            ]
        }

        gate = evaluate_release_gate(
            report,
            thresholds=EvaluationThresholds(
                min_hit_at_k=0.8,
                min_mrr=0.7,
                max_no_result_rate=0.2,
            ),
        )

        self.assertFalse(gate["passed"])
        self.assertTrue(
            any(check["name"] == "min_hit_at_k" for check in gate["checks"])
        )

    def test_release_gate_compares_with_baseline_report(self) -> None:
        current = {
            "runs": [
                {
                    "name": "with_rerank",
                    "hit_at_k": 0.9,
                    "mrr": 0.85,
                    "no_result_rate": 0.0,
                    "avg_latency_ms": 10.0,
                    "p95_latency_ms": 15.0,
                }
            ]
        }
        baseline = {
            "runs": [
                {
                    "name": "with_rerank",
                    "hit_at_k": 1.0,
                    "mrr": 0.95,
                    "no_result_rate": 0.0,
                    "avg_latency_ms": 10.0,
                    "p95_latency_ms": 15.0,
                }
            ]
        }

        gate = evaluate_release_gate(
            current,
            baseline_report=baseline,
            thresholds=EvaluationThresholds(
                min_hit_at_k=0.8,
                min_mrr=0.7,
                max_no_result_rate=0.2,
                max_hit_at_k_drop=0.05,
                max_mrr_drop=0.05,
            ),
        )

        self.assertFalse(gate["passed"])
        self.assertEqual(gate["baseline_delta"]["hit_at_k"], -0.1)

    def test_save_evaluation_report_creates_report_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            reports_dir = Path(temp_dir) / "reports"
            path = save_evaluation_report(
                {"report_type": "retrieval_evaluation", "runs": []},
                reports_dir=reports_dir,
            )

            self.assertTrue(path.exists())
            self.assertTrue(path.name.startswith("retrieval_eval_"))


if __name__ == "__main__":
    unittest.main()
