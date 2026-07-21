import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_CACHE_MOUNT = "rag-model-cache:/root/.cache/huggingface"


def _yaml_block(lines: list[str], key: str, indent: int) -> list[str]:
    marker = f"{' ' * indent}{key}:"
    try:
        start = lines.index(marker)
    except ValueError as exc:
        raise AssertionError(f"missing YAML mapping: {key}") from exc

    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        block.append(line)
    return block


def _yaml_sequence_values(lines: list[str], key: str, indent: int) -> list[str]:
    item_indent = indent + 2
    return [
        line.strip()[2:].strip()
        for line in _yaml_block(lines, key, indent)
        if len(line) - len(line.lstrip()) == item_indent
        and line.strip().startswith("- ")
    ]


def _yaml_mapping_keys(lines: list[str], key: str, indent: int) -> set[str]:
    child_indent = indent + 2
    return {
        line.strip()[:-1]
        for line in _yaml_block(lines, key, indent)
        if len(line) - len(line.lstrip()) == child_indent
        and line.strip().endswith(":")
        and not line.strip().startswith("- ")
    }


def _service_volumes(compose: str, service_name: str) -> list[str]:
    lines = compose.splitlines()
    services = _yaml_block(lines, "services", 0)
    service = _yaml_block(services, service_name, 2)
    return _yaml_sequence_values(service, "volumes", 4)


def _named_volumes(compose: str) -> set[str]:
    return _yaml_mapping_keys(compose.splitlines(), "volumes", 0)


class DeploymentConfigTest(unittest.TestCase):
    def test_production_image_installs_rerank_extra(self) -> None:
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn('-e ".[commercial,rerank]"', dockerfile)

    def test_compose_persists_huggingface_model_cache(self) -> None:
        compose = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn(MODEL_CACHE_MOUNT, _service_volumes(compose, "rag-api"))
        self.assertIn(MODEL_CACHE_MOUNT, _service_volumes(compose, "rag-refresh"))
        self.assertIn("rag-model-cache", _named_volumes(compose))

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
