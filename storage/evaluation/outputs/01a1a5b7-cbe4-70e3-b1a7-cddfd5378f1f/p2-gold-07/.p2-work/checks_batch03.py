"""P2-Gold-07 stage 3: cross-checks for B28-B42 (duplicates, shared chunks, ambiguity).

Read-only. Emits batch03_checks.json.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(r"D:\AgentAIProgect\RAG")
OUT = ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"

facts = json.loads((HERE / "batch03_facts.json").read_text(encoding="utf-8"))
data = json.loads((HERE / "b03_inputs.json").read_text(encoding="utf-8"))
corpus = [json.loads(x) for x in (ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl")
          .read_text(encoding="utf-8").splitlines() if x.strip()]
by_id = {c["chunk_id"]: c for c in corpus}

batch01 = data["gold_batch01"]
batch02 = data["gold_batch02"]
mapping = data["mapping"]

# gold evidence chunk ids (batch01 metadata holds them; batch02 resolved by target match)
g04 = json.loads((OUT / "p2-gold-04/retrieval_gold_batch01_metadata.json").read_text(encoding="utf-8"))
gold1_chunks = set()
for rec in g04.get("records", g04 if isinstance(g04, list) else []):
    for ev in rec.get("evidence", []):
        gold1_chunks.add(ev["chunk_id"])

gold2_chunks = set()
for item in batch02:
    for t in item["expected"]:
        for c in corpus:
            if c["source"] == t["source"] and c["metadata"].get("section_title") == t["section_title"] \
                    and t["text_contains"] in c["chunk_text"]:
                gold2_chunks.add(c["chunk_id"])

gold_q = [{"b": "B01-B12", "q": g["query"]} for g in batch01] + \
         [{"b": "B13-B27", "q": g["query"]} for g in batch02]


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


checks = {}
targets = [f"B{i:02d}" for i in range(28, 43)]
chunk_owner: dict[str, list[str]] = {}

for b in targets:
    f = facts[b]
    cand = f
    ans = cand["proposed_answer"]
    chunk_ids = cand["supporting_chunk_ids"]
    for cid in chunk_ids:
        chunk_owner.setdefault(cid, []).append(b)

    # answer appears in at least one supporting chunk?
    ans_any = any(norm(ans) in norm(by_id[c]["chunk_text"]) for c in chunk_ids)
    # how many distinct rows share the same leading number inside the evidence chunk
    first_tok = ans.split()[0] if ans.split() else ans
    dup_in_chunk = []
    if re.fullmatch(r"[\d.]+", first_tok):
        for cid in chunk_ids:
            n = by_id[cid]["chunk_text"].count(first_tok)
            if n > 1:
                dup_in_chunk.append({"chunk_id": cid, "value": first_tok, "occurrences": n})

    gold_sims = sorted(
        ({"ratio": round(difflib.SequenceMatcher(None, cand["question"], q["q"]).ratio(), 4),
          "gold_group": q["b"], "gold_query": q["q"]} for q in gold_q),
        key=lambda x: -x["ratio"])[:3]

    checks[b] = {
        "answer_in_any_supporting_chunk": ans_any,
        "answer_value_repeated_in_evidence_chunk": dup_in_chunk,
        "shared_chunks_with_gold": sorted(set(chunk_ids) & (gold1_chunks | gold2_chunks)),
        "gold_similarity_top3": gold_sims,
    }

# batch-internal shared chunks
peers = {}
for cid, owners in chunk_owner.items():
    if len(owners) > 1:
        peers[cid] = owners
for b in targets:
    mine = set(facts[b]["supporting_chunk_ids"])
    checks[b]["shared_chunks_in_batch"] = {
        cid: [o for o in owners if o != b] for cid, owners in peers.items() if cid in mine
    }

(HERE / "batch03_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=1), encoding="utf-8")

print("gold1_chunks", len(gold1_chunks), "gold2_chunks", len(gold2_chunks))
for b in targets:
    c = checks[b]
    print(b,
          "ans_any", c["answer_in_any_supporting_chunk"],
          "dupval", [(d["value"], d["occurrences"]) for d in c["answer_value_repeated_in_evidence_chunk"]],
          "shared_gold", len(c["shared_chunks_with_gold"]),
          "shared_batch", list(c["shared_chunks_in_batch"]),
          "maxgold", c["gold_similarity_top3"][0]["ratio"])
