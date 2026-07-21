import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DeploymentConfigTest(unittest.TestCase):
    def test_production_image_installs_rerank_extra(self) -> None:
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn('-e ".[commercial,rerank]"', dockerfile)

    def test_compose_persists_huggingface_model_cache(self) -> None:
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("rag-model-cache:/root/.cache/huggingface", compose)
        self.assertIn("rag-model-cache:", compose)

    def test_checked_in_retrieval_config_enables_cross_encoder(self) -> None:
        config = json.loads(
            (REPO_ROOT / "config" / "retrieval.json").read_text(encoding="utf-8")
        )
        self.assertEqual(config["retrieval_mode"], "hybrid")
        self.assertEqual(config["rerank_provider"], "cross-encoder")
        self.assertEqual(config["rerank_trigger"], "always")
        self.assertEqual(config["rerank_candidate_k"], 20)

    def test_example_environment_enables_cross_encoder(self) -> None:
        example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("RAG_RERANK_PROVIDER=cross-encoder", example)


if __name__ == "__main__":
    unittest.main()
