"""Final read-only re-verification of the P2-Gold-06 deliverables."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\AgentAIProgect\RAG")
sys.path.insert(0, str(ROOT))

from rag_app.eval_dataset.corpus import load_corpus_snapshot  # noqa: E402
from rag_app.operations.evaluation import load_retrieval_eval_cases  # noqa: E402

G06 = ROOT / ("storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06")
G04 = ROOT / ("storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04")
CORPUS_MANIFEST = ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.manifest.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = json.loads((G06 / "gold_batch02_manifest.json").read_text(encoding="utf-8"))
sidecar = (G06 / "gold_batch02_manifest.sha256").read_text(encoding="utf-8").split()[0]
assert sidecar == sha(G06 / "gold_batch02_manifest.json"), "manifest self hash mismatch"

for name, digest in manifest["outputs_sha256"].items():
    assert sha(G06 / name) == digest, name
for rel, digest in manifest["inputs_sha256"].items():
    assert sha(ROOT / rel) == digest, rel

assert sha(G04 / "retrieval_gold_batch01_9.jsonl") == \
    "0ee8bbcd963f09c9b300209e8f1edcd93eb27ece1a077af877a37473568ec73a"
assert sha(ROOT / "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl") == \
    "31df78af2c96afd25f9221034ab47bbd965f7cb1a5e182dc8c1560cc3f9cf120"

_, rows = load_corpus_snapshot(CORPUS_MANIFEST)
chunks = {row["chunk_id"]: row for row in rows}
cases = load_retrieval_eval_cases(G06 / "retrieval_gold_batch02_13.jsonl")
assert len(cases) == 13

gold = [json.loads(line) for line in
        (G06 / "retrieval_gold_batch02_13.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
hit_total = 0
for item in gold:
    for target in item["expected"]:
        matched = [cid for cid, chunk in chunks.items()
                   if chunk["source"] == target["source"]
                   and chunk["metadata"].get("section_title") == target["section_title"]
                   and target["text_contains"] in chunk["chunk_text"]]
        assert len(matched) == 1, (target, matched)
        hit_total += 1

print("manifest_self_hash", sidecar)
print("outputs_verified", len(manifest["outputs_sha256"]))
print("inputs_verified", len(manifest["inputs_sha256"]))
print("eval_cases_loaded", len(cases))
print("targets_resolved", hit_total)
print("counts", json.dumps(manifest["counts"], ensure_ascii=False))
print("checks", manifest["validation"]["static_checks"],
      "failed", manifest["validation"]["static_checks_failed"])
print("files", sorted(p.name for p in G06.iterdir() if p.is_file()))
