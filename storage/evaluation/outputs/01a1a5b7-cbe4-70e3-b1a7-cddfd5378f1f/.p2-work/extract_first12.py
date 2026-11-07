# -*- coding:utf-8 -*-
"""Extract the 12 first-batch candidate records + their corpus chunks (read-only)."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
BASE = r"D:\AgentAIProgect\RAG\storage\evaluation\outputs\01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
CAND = r"D:\AgentAIProgect\RAG\storage\evaluation\candidates\p1-20261104-structured\candidates.jsonl"
CORPUS = r"D:\AgentAIProgect\RAG\storage\evaluation\corpus\p1-20261104-v2\corpus.jsonl"

ids = {
    "B01": "9631dde730749e95e2c74da24726dd1d8e743b1242d189ac76034732a01fa5e9",
    "B02": "6858125cbf5e8170a757c8a812aca9d1a9b2dd23347c59d5061af9a7c0d982f0",
    "B03": "31d42a216450391763336ebbd7b38604cb50a3557831669e5b3371e63ef477ed",
    "B04": "4d263ebb839f347941da0bd9c9d0c11533925443e6a26519593ad7628f6c29e6",
    "B05": "e3783223e572063f0a3df106a6c1c6084c99e5f2943b788dc72a6996cb96b2bf",
    "B06": "bfd1eea2e2dfb6cd0dbda8053b95cae3aee6dc526998a08e1da1ee5458570a41",
    "B07": "50354083653ee2bf6b5811362051fffcabfb7895978e5d6d0004c77ad21b0622",
    "B08": "d5ab4e3c5473589238491da686184e9c651ecdbf317776b9454bc222b49ff81a",
    "B09": "8d8e0f5cbd56fd6adb9ba5e09728cc911d24345d7a41f15ec0eaddc37717d1c8",
    "B10": "b503d526e513f66d71916de151812a19403e51bbfd81956c88dee63adda7814a",
    "B11": "de1dd6ecf011fd92f5cbef969545f045b067fbc353123e327f2b8ce04527a0d3",
    "B12": "70dc300fbcd568ccd4324dd4c6a93d6e438266da789c7865f0400d0c64547d24",
}
rid = {v: k for k, v in ids.items()}

records = {}
corpus = {}
with open(CAND, encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        sha = rec.get("candidate_id", "")
        if sha.startswith("sha256:"):
            sha = sha[len("sha256:"):]
        if sha in rid:
            records[rid[sha]] = rec
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        rec = json.loads(line)
        cid = rec.get("chunk_id", "")
        corpus[cid] = rec

out = {"candidates": {}, "chunks": {}}
for k in ids:
    rec = records.get(k)
    out["candidates"][k] = rec
    chunks = rec.get("supporting_chunk_ids") or rec.get("supporting_chunks") or []
    if isinstance(chunks, str):
        chunks = chunks.split()
    for cid in chunks:
        if cid not in out["chunks"] and cid in corpus:
            out["chunks"][cid] = corpus.get(cid)
print("candidates found:", sorted(records.keys()))
print("missing:", [k for k in ids if k not in records])
print("chunks found:", sorted(out["chunks"].keys()))
missing_chunks = []
for k, rec in records.items():
    chunks = rec.get("supporting_chunk_ids") or []
    if isinstance(chunks, str):
        chunks = chunks.split()
    for cid in chunks:
        if cid not in corpus:
            missing_chunks.append((k, cid))
print("missing chunks:", missing_chunks)
with open(BASE + r"\.p2-work\first12.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("saved first12.json")
