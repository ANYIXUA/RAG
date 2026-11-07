from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rag_app.eval_dataset.candidates import run_generation
from rag_app.eval_dataset.corpus import CorpusExportError, export_active_chunks
from rag_app.eval_dataset.ollama import LocalOllama, ModelError
from rag_app.eval_dataset.schemas import CorpusScope
from tests.helpers import production_settings
from tests.test_eval_corpus import FakeDatabase, body, header


PUBLIC = "For optical alarms, error code E123 indicates a disconnected fibre."
PRIVATE = "Reset the private controller to restore its dedicated management channel."


def proposed(question="What does error code E123 indicate?", **overrides):
    return {
        "question": question, "question_type": "exact_entity", "difficulty": "easy",
        "proposed_answer": "a disconnected fibre", "exact_entity": "E123",
        "evidence": [{"passage_id": "p1"}], **overrides,
    }


class CandidateGenerationTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.scope = CorpusScope("test", "tenant-a", ("public", "ops"))
        rows = [body(text=PUBLIC), body("c2", text=PRIVATE, tags=["ops"])]
        rows[0]["metadata"]["error_codes"] = ["E123", "E777"]
        rows[1]["metadata"]["error_code"] = "T9254"
        db = FakeDatabase(headers=[header(), header("c2", tags=["ops"])], bodies=rows)
        self.snapshot = export_active_chunks(
            production_settings(self.root), self.scope, self.root / "snapshot", connect=db.connect,
        ).manifest_path
        transport = patch.object(LocalOllama, "_request")
        self.transport = transport.start()
        self.addCleanup(transport.stop)

    def local_model(self, replies):
        pending = iter(replies)

        def request(path, payload=None):
            if path == "/api/tags":
                return {"models": [{"model": "mock:local", "digest": "a" * 64,
                                    "details": {"format": "gguf"}, "size": 100}]}
            if path == "/api/show":
                return {"model_info": {"general.architecture": "qwen"}, "details": {"format": "gguf"}}
            self.assertEqual(path, "/api/generate")
            reply = next(pending)
            if isinstance(reply, Exception):
                raise reply
            return reply

        self.transport.side_effect = request

    def run_to(self, name, max_batches=2, **kwargs):
        result = run_generation(
            self.snapshot, self.scope, self.root / name, endpoint="http://127.0.0.1:11434",
            model="mock:local", seed=123, max_batches=max_batches, **kwargs,
        )
        return result, {
            f.name: f.read_bytes() for f in (self.root / name).iterdir()
        }

    @staticmethod
    def reply(*items):
        return {"done": True, "model": "mock:local", "response": json.dumps({"candidates": items})}

    def test_generation_is_reproducible_and_never_accepts_model_review_status(self):
        reply = self.reply(
            proposed(review_status="approved", evidence=[{"passage_id": "p1", "excerpt": PRIVATE}]),
            proposed("What does error code E123 indicate !"),
        )
        for name in ("first", "second"):
            self.local_model([reply, self.reply()])
            result, files = self.run_to(name)
            self.assertEqual(result["candidate_count"], 1)
            if name == "first":
                first = files
            else:
                self.assertEqual(files, first)
        candidate = json.loads(files["candidates.jsonl"])
        self.assertEqual(candidate["review_status"], "pending_review")
        self.assertEqual(candidate["supporting_chunk_ids"], ["c1"])
        self.assertEqual(candidate["evidence_excerpt"], {"c1": PUBLIC})
        self.assertEqual(candidate["chunk_permission_tags"], ["public"])
        self.assertEqual(candidate["scope"]["permission_tags"], ["ops", "public"])
        manifest = json.loads(files["generation_manifest.json"])
        self.assertEqual(manifest["seed"], 123)
        self.assertEqual(manifest["model_digest"], "a" * 64)
        request = next(call.args[1] for call in self.transport.call_args_list
                       if call.args[0] == "/api/generate")
        schema = request["format"]["properties"]["candidates"]["items"]
        self.assertIn("exact_entity", schema["required"])
        self.assertEqual(schema["properties"]["evidence"]["items"]["properties"]["passage_id"]["enum"], ["p1"])

    def test_rejects_unknown_cross_scope_and_hallucinated_evidence(self):
        self.local_model([self.reply(
            proposed(evidence=[{"passage_id": "missing"}]),
            proposed(evidence=[{"chunk_id": "c2", "excerpt": PRIVATE}]),
            proposed(proposed_answer="reboot the unit"),
            proposed("What does error code E123 indicate after 15 minutes?"),
        ), self.reply(), self.reply(), self.reply()])
        result, files = self.run_to("reject", max_batches=4)
        self.assertEqual(result["candidate_count"], 0)
        quality = json.loads(files["candidate_quality_report.json"])
        self.assertEqual(quality["rejected"], {
            "invalid_passage_reference": 2,
            "unanchored_answer": 1, "unsupported_question_token": 1,
        })
        prompts = [call.args[1]["prompt"] for call in self.transport.call_args_list
                   if call.args[0] == "/api/generate"]
        self.assertTrue(any(PUBLIC in prompt for prompt in prompts))
        self.assertTrue(any(PRIVATE in prompt for prompt in prompts))
        self.assertTrue(all((PUBLIC in prompt) != (PRIVATE in prompt) for prompt in prompts))

    def test_wrong_snapshot_scope_stops_before_model_io(self):
        with self.assertRaises(CorpusExportError):
            run_generation(
                self.snapshot, CorpusScope("test", "tenant-b", ("public",)), self.root / "wrong",
                endpoint="http://127.0.0.1:11434", model="mock:local",
            )
        self.transport.assert_not_called()
        self.assertFalse((self.root / "wrong").exists())

    def test_missing_explicit_scope_stops_before_model_io(self):
        with self.assertRaises(ValueError):
            run_generation(
                self.snapshot, None, self.root / "missing-scope",
                endpoint="http://127.0.0.1:11434", model="mock:local",
            )
        self.transport.assert_not_called()

    def test_invalid_unicode_is_rejected_without_losing_reports(self):
        self.local_model([self.reply(proposed("What does error code E123 indicate \ud800?")), self.reply()])
        result, files = self.run_to("invalid-unicode")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(json.loads(files["candidate_quality_report.json"])["rejected"],
                         {"invalid_candidate_schema": 1})

    def test_malformed_model_output_and_transport_failure_are_reported(self):
        self.local_model([
            {"done": True, "model": "mock:local", "response": "invalid-json"},
            ModelError("model_unreachable"),
        ])
        result, files = self.run_to("failed")
        self.assertEqual(result["status"], "model_failed")
        self.assertEqual(files["candidates.jsonl"], b"")
        quality = json.loads(files["candidate_quality_report.json"])
        self.assertEqual(quality["model_errors"], {"invalid_model_output": 1, "model_unreachable": 1})
        gaps = json.loads(files["coverage_gap_report.json"])
        self.assertEqual(gaps["supported_error_code_count"], 1)
        self.assertEqual(gaps["metadata_only_error_code_count"], 2)

    def test_standard_fragments_are_neither_evidence_nor_exact_entities(self):
        text = (
            "The specification GB/T9254.1 applies to emissions. Reference E123.4 is a section.\n"
            "Error code X567 is a spurious standard identifier fragment and does not exist.\n"
            "F123 was extracted from GB/T9254.1 as a fragment and is not an error code."
        )
        db = FakeDatabase(bodies=[body(text=text)])
        self.snapshot = export_active_chunks(
            production_settings(self.root), CorpusScope("test", "tenant-a", ("public",)),
            self.root / "standard", connect=db.connect,
        ).manifest_path
        self.scope = CorpusScope("test", "tenant-a", ("public",))
        self.local_model([self.reply(
            proposed(
                "What does T9254 govern?", exact_entity="T9254",
                proposed_answer="emissions",
            ),
            proposed(
                "What does error code X567 refer to?", exact_entity="X567",
                proposed_answer="a spurious standard identifier fragment",
            ),
            proposed(
                "Which standard does F123 the error code come from?", exact_entity="F123",
                proposed_answer="GB/T9254.1",
            ),
            proposed(
                "F123异常码对应哪项标准？", exact_entity="F123", proposed_answer="GB/T9254.1",
            ),
        ), self.reply()])
        result, files = self.run_to("standard-check")
        self.assertEqual(result["candidate_count"], 0)
        self.assertEqual(json.loads(files["coverage_gap_report.json"])["supported_error_code_count"], 0)

    def test_multi_condition_requires_two_question_anchors(self):
        second = "The optical alarm indicator is enabled only in manual mode."
        db = FakeDatabase(headers=[header(), header("c3")], bodies=[body(text=PUBLIC), body("c3", text=second)])
        self.scope = CorpusScope("test", "tenant-a", ("public",))
        self.snapshot = export_active_chunks(
            production_settings(self.root), self.scope, self.root / "multi", connect=db.connect,
        ).manifest_path
        citations = [{"passage_id": "p1", "anchor": "optical alarms"},
                     {"passage_id": "p2", "anchor": "manual mode"}]
        self.local_model([self.reply(), self.reply(), self.reply(
            proposed("What applies to optical alarms alone?", question_type="multi_condition", evidence=citations),
            proposed("For optical alarms during manual mode, what fault is indicated?",
                     question_type="multi_condition", evidence=citations),
        )])
        result, files = self.run_to("multi-check", max_batches=3)
        self.assertEqual(result["candidate_count"], 1)
        candidate = json.loads(files["candidates.jsonl"])
        self.assertEqual(candidate["question_anchors"], {"c1": "optical alarms", "c3": "manual mode"})
        schema = self.transport.call_args_list[-2].args[1]["format"]["properties"]["candidates"]["items"]
        self.assertEqual(schema["properties"]["evidence"]["minItems"], 2)
        self.assertIn("anchor", schema["properties"]["evidence"]["items"]["required"])

    def test_numeric_answer_cannot_use_a_fragment_at_a_passage_boundary(self):
        text = "甲" * 352 + "设备数不得超过50台。"
        self.scope = CorpusScope("test", "tenant-a", ("public",))
        self.snapshot = export_active_chunks(
            production_settings(self.root), self.scope, self.root / "number",
            connect=FakeDatabase(bodies=[body(text=text)]).connect,
        ).manifest_path
        self.local_model([self.reply(), self.reply(
            proposed("设备数量的上限是多少？", proposed_answer="5"),
            proposed("设备数量的上限是多少？", proposed_answer="50"),
        )])
        result, files = self.run_to("number-check")
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(json.loads(files["candidates.jsonl"])["proposed_answer"], "50")
        self.assertEqual(json.loads(files["candidate_quality_report.json"])["rejected"], {"unanchored_answer": 1})


class LocalOllamaTest(unittest.TestCase):
    def test_rejects_cloud_and_non_loopback_before_network(self):
        for endpoint, model in (
            ("https://ollama.com", "mock:local"), ("http://192.168.1.2", "mock:local"),
            ("http://127.0.0.1@external.invalid", "mock:local"),
            ("http://127.0.0.1:11434/api", "mock:local"),
            ("http://127.0.0.1:11434", "qwen:4b-cloud"),
            ("http://127.0.0.1:11434", "ollama.com/model:local"),
        ):
            with self.subTest(endpoint=endpoint, model=model), self.assertRaises(ValueError):
                LocalOllama(endpoint, model)

    def test_missing_or_remote_model_never_reaches_generation(self):
        remote = {"model": "mock:local", "remote_host": "https://ollama.com",
                  "size": 100, "digest": "a" * 64, "details": {"format": "gguf"}}
        for models in ([], [remote]):
            client = LocalOllama("http://localhost:11434", "mock:local")
            with patch.object(client, "_request", return_value={"models": models}) as request:
                with self.assertRaises(ModelError):
                    client.local_digest()
                self.assertEqual([call.args[0] for call in request.call_args_list], ["/api/tags"])

    def test_redirect_is_rejected_without_following_location(self):
        client = LocalOllama("http://localhost:11434", "mock:local")
        with patch("rag_app.eval_dataset.ollama.HTTPConnection") as connection:
            connection.return_value.getresponse.return_value.status = 307
            with self.assertRaises(ModelError):
                client.local_digest()
            self.assertEqual(connection.call_count, 1)
            self.assertEqual(connection.call_args.args[:2], ("127.0.0.1", 11434))

    def test_changed_model_digest_stops_before_sending_prompt(self):
        client = LocalOllama("http://localhost:11434", "mock:local")
        replacement = {"model": "mock:local", "digest": "b" * 64,
                       "size": 100, "details": {"format": "gguf"}}
        with patch.object(client, "_request", return_value={"models": [replacement]}) as request:
            with self.assertRaisesRegex(ModelError, "model_digest_changed"):
                client.generate(PUBLIC, {"seed": 123}, "a" * 64)
            self.assertEqual([call.args[0] for call in request.call_args_list], ["/api/tags"])


if __name__ == "__main__":
    unittest.main()
