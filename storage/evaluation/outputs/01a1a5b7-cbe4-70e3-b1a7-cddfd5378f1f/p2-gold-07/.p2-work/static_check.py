"""P2-Gold-07 static acceptance check.

Read-only over frozen inputs; reads this round's deliverables and asserts:
frozen hashes / B28-B42 completeness / evidence traceability / classification
completeness / Revise support / duplicate disclosure / empty human fields /
batch01+batch02 untouched / B23 not gold / no fabricated retrieval metrics.

Writes p2_gold_07_verify.json and prints a summary.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import fitz

ROOT = Path(r"D:\AgentAIProgect\RAG")
OUT = ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
G07 = OUT / "p2-gold-07"
G04 = OUT / "p2-gold-04"
G05 = OUT / "p2-gold-05"
G06 = OUT / "p2-gold-06"
CANDS = ROOT / "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl"
CORPUS = ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl"

checks: list[dict] = []


def check(name: str, passed: bool, detail=None) -> bool:
    checks.append({"check": name, "passed": bool(passed), "detail": detail})
    return bool(passed)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def parse_ids(s: str) -> list[str]:
    """Packet id lists are written as [id1, id2, ...] without quotes."""
    s = (s or "").strip().strip("[]")
    return [p.strip().strip("'\"") for p in re.split(r"[,\s]+", s) if p.strip(" '\"")]


def chunk_body(chunk_text: str) -> str:
    """Strip the exporter's 章节/页码 prefix and its 表格列 trailer."""
    t = re.sub(r"^章节：.*?页码：\d+\s*", "", chunk_text, flags=re.S)
    t = t.split("表格列：")[0]
    return t


# ---------------------------------------------------------------- frozen inputs
FROZEN = {
    "candidates.jsonl": (CANDS, "31df78af2c96afd25f9221034ab47bbd965f7cb1a5e182dc8c1560cc3f9cf120"),
    "corpus.jsonl": (CORPUS, "5995ee6be2871ee7c553ce5fe2f3002a7938dbffedf0ec2b8fed28af8107f4d6"),
    "batch01_gold": (G04 / "retrieval_gold_batch01_9.jsonl",
                     "0ee8bbcd963f09c9b300209e8f1edcd93eb27ece1a077af877a37473568ec73a"),
    "batch01_metadata": (G04 / "retrieval_gold_batch01_metadata.json",
                         "6aa3b20a867be6c2718cc6621b57b10f42029f883e14ac6be314c44a4a703e39"),
    "batch01_rejected": (G04 / "rejected_batch01_3.jsonl",
                         "3bbeec82efe9ad5fc646479056cf189985314fadb8f5670ea164e28869c1ed91"),
    "batch01_manifest": (G04 / "gold_batch01_manifest.json",
                         "f1384386520a69e48ef9038faf7a108a11fa5288a17a709282a7d68816398493"),
    "batch02_gold": (G06 / "retrieval_gold_batch02_13.jsonl",
                     "5bfc8df96edd9574954fdb70c874a1fae186b3f442f077dcf92b478f9d103db9"),
    "batch02_metadata": (G06 / "retrieval_gold_batch02_metadata.json",
                         "a12a31ab2f69c163b6053e66f503d4c28ce48d9322dcebaca9065a996d5211a3"),
    "batch02_rejected": (G06 / "rejected_batch02_1.jsonl",
                         "aa0e784949e0d3ff535e57b510b8111fbbe6d869752292a613f80836409aff73"),
    "batch02_unsigned": (G06 / "unsigned_batch02_1.jsonl",
                         "4cd8ddc233c9a3f54b10fca609f388bf616d7653665d8a9accc5e69ca04e1cee"),
    "packet_batch02": (G05 / "p2_gold_05_signoff_packet.md",
                       "5c9f5feaff9a281236d5ba680bf609c22c4a0c2f6355c349b3a0d10a3dd906a8"),
    "proposal_batch02": (G05 / "p2_gold_05_review_proposal.md",
                         "8811414d2c6447662a0ab4cbad45d60524b475543003fc5af575c32fe3cc8dc2"),
    "review_xlsx": (OUT / "review.xlsx",
                    "df13e2755786cfb7f4d30e44d6323463ce6cbfe49c99a2b5ae87dfeec369d5ea"),
    "draft_batch02_xlsx": (G05 / "review_batch02_15_draft.xlsx",
                           "12f4a4acbb176590de732a7c92c0c620f03ac8376edda10ade52989a96c060b7"),
    "pdf_dianxin": (ROOT / "data/电信基础设施维护规程.pdf",
                    "9c8962e69d08275318a4f3c2d3e3ed00b3f06a995a54ddabce4d21d48bd18d58"),
    "pdf_biaozhun": (ROOT / "data/智慧家庭装维工程与管理职业技能等级标准.pdf",
                     "fa3d041fb25b65ea0157e17b3d868e5a02e59e7ff677843ba2341af5262ae21c"),
    "pdf_quanguang": (ROOT / "data/中国移动智慧家庭全光组网产品技术规范V2.0.0.pdf",
                      "21584b7e257f02871291a6dc5d84955b6ae5dc74d7dfb8e020736f575d4c6032"),
}
for name, (path, expected) in FROZEN.items():
    actual = sha(path)
    check(f"frozen:{name}", actual == expected, {"expected": expected, "actual": actual})

sidecar = (G06 / "gold_batch02_manifest.sha256").read_text(encoding="utf-8").split()[0]
check("frozen:batch02_manifest_sidecar", sha(G06 / "gold_batch02_manifest.json") == sidecar,
      {"sidecar": sidecar})

# ---------------------------------------------------------------- inputs reloaded
cands = load_jsonl(CANDS)
chunks = {c["chunk_id"]: c for c in load_jsonl(CORPUS)}
cand_by_id = {c["candidate_id"]: c for c in cands}
check("candidate_count", len(cands) == 57, len(cands))
check("corpus_chunks", len(chunks) == 447, len(chunks))
check("corpus_documents", len({c["source"] for c in chunks.values()}) == 3,
      sorted({c["source"] for c in chunks.values()}))

gold1 = load_jsonl(G04 / "retrieval_gold_batch01_9.jsonl")
gold2 = load_jsonl(G06 / "retrieval_gold_batch02_13.jsonl")
check("gold_batch01_count", len(gold1) == 9, len(gold1))
check("gold_batch02_count", len(gold2) == 13, len(gold2))

unsigned = load_jsonl(G06 / "unsigned_batch02_1.jsonl")
check("b23_unsigned_present", len(unsigned) == 1 and unsigned[0]["batch_id"] == "B23",
      [u["batch_id"] for u in unsigned])
check("b23_still_null_gold_id", unsigned[0]["gold_case_id"] is None, unsigned[0]["gold_case_id"])
check("b23_status_unsigned", unsigned[0]["status"] == "unsigned_pending_clarification",
      unsigned[0]["status"])
check("b23_not_in_gold_files",
      "0f3b338e" not in (G04 / "retrieval_gold_batch01_9.jsonl").read_text(encoding="utf-8")
      and "0f3b338e" not in (G06 / "retrieval_gold_batch02_13.jsonl").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- packet parsing
PACKET = G07 / "p2_gold_07_signoff_packet.md"
text = PACKET.read_text(encoding="utf-8")


def parse_packet(md: str) -> list[dict]:
    recs = []
    for m in re.finditer(r"^## (B\d{2})\n(.*?)(?=^## B|\Z)", md, re.M | re.S):
        block = re.search(r"```text\n(.*?)\n```", m.group(2), re.S)
        rec = {"heading": m.group(1)}
        for line in block.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                rec[k.strip()] = v.strip()
        recs.append(rec)
    return recs


records = parse_packet(text)
ids = [r["batch_id"] for r in records]
expected_ids = [f"B{i:02d}" for i in range(28, 43)]
check("packet_record_count", len(records) == 15, len(records))
check("packet_ids_exact", ids == expected_ids, ids)
check("packet_ids_unique", len(set(ids)) == len(ids))
check("packet_heading_matches_batch_id", all(r["heading"] == r["batch_id"] for r in records))

mapping = json.loads((G07 / ".p2-work/b03_inputs.json").read_text(encoding="utf-8"))["mapping"]
map_by_b = {m["b"]: m for m in mapping}
for r in records:
    b = r["batch_id"]
    check(f"packet_id_matches_workbook:{b}",
          r["candidate_id"] == map_by_b[b]["candidate_id"],
          {"packet": r["candidate_id"][:20], "workbook": map_by_b[b]["candidate_id"][:20]})

# ---------------------------------------------------------------- candidate integrity
for r in records:
    b = r["batch_id"]
    src = cand_by_id[r["candidate_id"]]
    check(f"original_question_unchanged:{b}", r["original_question"] == src["question"])
    check(f"original_answer_unchanged:{b}", r["original_answer"] == src["proposed_answer"])
    listed = parse_ids(r["original_supporting_chunk_ids"])
    check(f"original_chunks_unchanged:{b}", listed == src["supporting_chunk_ids"],
          {"packet": listed, "candidate": src["supporting_chunk_ids"]})
    check(f"candidate_status_pending:{b}", src["review_status"] == "pending_review",
          src["review_status"])

# ---------------------------------------------------------------- classification
ALLOWED = ("Accept", "Revise", "Reject", "Needs Verification")
for r in records:
    check(f"classification_present:{r['batch_id']}", r.get("review_recommendation") in ALLOWED,
          r.get("review_recommendation"))
    check(f"review_reason_present:{r['batch_id']}", bool(r.get("review_reason")))

counts = {k: sum(1 for r in records if r["review_recommendation"] == k) for k in ALLOWED}
check("classification_counts_sum", sum(counts.values()) == 15, counts)
check("classification_counts_expected",
      counts == {"Accept": 8, "Revise": 5, "Reject": 2, "Needs Verification": 0}, counts)

# ---------------------------------------------------------------- evidence traceability
doc_versions = {}
for r in records:
    b = r["batch_id"]
    ev = parse_ids(r["evidence_chunk_ids"])
    rel = parse_ids(r["retrieval_relevant_chunk_ids"])
    for cid in ev:
        if not check(f"chunk_exists:{b}:{cid}", cid in chunks):
            continue
        ch = chunks[cid]
        check(f"chunk_sha:{b}:{cid}",
              hashlib.sha256(ch["chunk_text"].encode("utf-8")).hexdigest() == ch["chunk_text_sha256"])
        doc_versions.setdefault(b, set()).add(ch["document_version"])
        check(f"source_document_match:{b}:{cid}", ch["source"] == r["source_document"],
              {"chunk": ch["source"], "packet": r["source_document"]})
        check(f"page_in_source_pages:{b}:{cid}",
              re.search(rf"(?<![\d.]){ch['page_number']}(?![\d.])", r["source_pages"]) is not None,
              {"page": ch["page_number"], "source_pages": r["source_pages"]})
    check(f"evidence_nonempty:{b}", len(ev) > 0, ev)
    for cid in rel:
        check(f"relevant_chunk_exists:{b}:{cid}", cid in chunks)
        check(f"relevant_subset_of_evidence:{b}:{cid}", cid in ev)
    if r["review_recommendation"] == "Reject":
        check(f"reject_no_retrieval_target:{b}", rel == [], rel)
        check(f"reject_no_revision:{b}",
              not r.get("revised_question") and not r.get("revised_answer"))
    if r["review_recommendation"] == "Accept":
        check(f"accept_no_revision:{b}",
              not r.get("revised_question") and not r.get("revised_answer"))
        ans = re.sub(r"\s+", "", r["original_answer"])
        body = "".join(re.sub(r"\s+", "", chunks[c]["chunk_text"]) for c in ev)
        check(f"accept_answer_verbatim_in_evidence:{b}", ans in body,
              {"answer_head": ans[:24]})
    if r["review_recommendation"] == "Revise":
        check(f"revise_has_question:{b}", bool(r.get("revised_question")))
        check(f"revise_has_answer:{b}", bool(r.get("revised_answer")))
        check(f"revise_has_reason:{b}", bool(r.get("review_reason")))

# substantive corrections
check("b34_corrected_value_supported",
      "7.5" in chunks["d8dfa78cb9362f0d69cd659c"]["chunk_text"])
check("b32_revision_supported",
      "4.6 职业能力特征" in chunks["d70540614c288a2dc8b3066f"]["chunk_text"]
      and "4.7 受教育程度" in chunks["d70540614c288a2dc8b3066f"]["chunk_text"])
check("b33_revision_supported",
      "鉴定方式应分为理论知识考试、技能考核" in chunks["14da1c09b687f7b48896e03a"]["chunk_text"])
check("b35_revision_supported",
      all(x in chunks["e69ef87cafd302938c765e20"]["chunk_text"] for x in
          ["表4-1 设备形态", "Wi-Fi 7 光网关", "Wi-Fi 6 光网关", "Wi-Fi 7 光路由", "Wi-Fi 6 光路由"]))
check("b38_revision_supported",
      "器检修" in chunks["647c44016cd2e8fabe51f5de"]["chunk_text"]
      and "开箱检验、安装固定" in chunks["4a65d0d3ead0bc841b1b28f8"]["chunk_text"])
xxxx = [c for c in chunks.values() if "XXXX-XX-XX" in c["chunk_text"]]
check("b31_placeholder_is_only_date_source", len(xxxx) == 1 and xxxx[0]["page_number"] == 1,
      [(c["source"], c["page_number"]) for c in xxxx])
check("b31_no_real_date_in_doc",
      not any(re.search(r"20\d{2}\s*[-年.]\s*\d{1,2}\s*[-月.]", c["chunk_text"])
              for c in chunks.values() if c["source"].startswith("智慧家庭装维")))

# PDF page presence (physical page extracted again)
pdf_cache: dict[str, fitz.Document] = {}
for r in records:
    b = r["batch_id"]
    for cid in parse_ids(r["evidence_chunk_ids"]):
        ch = chunks[cid]
        doc = pdf_cache.setdefault(ch["source"], fitz.open(ROOT / "data" / ch["source"]))
        page = doc[ch["page_number"] - 1].get_text("text")
        head = re.sub(r"\s+", "", chunk_body(ch["chunk_text"]))[:160]
        check(f"pdf_page_contains_chunk_body:{b}:{cid}",
              bool(head) and head in re.sub(r"\s+", "", page),
              {"page": ch["page_number"], "head": head[:40]})

# ---------------------------------------------------------------- human fields empty
HUMAN = ["human_decision", "human_reviewer", "human_reviewed_at", "human_comment"]
for r in records:
    for f in HUMAN:
        check(f"human_field_empty:{r['batch_id']}:{f}", r.get(f, "") == "", r.get(f))

# ---------------------------------------------------------------- no fabricated metrics
METRIC = re.compile(r"(MRR|NDCG|Hit@\d+|latency|延迟)\s*[=:：]\s*[0-9]")
for md in sorted(G07.glob("*.md")):
    hits = METRIC.findall(md.read_text(encoding="utf-8"))
    check(f"no_metric_claims:{md.name}", not hits, hits[:3])
check("no_new_gold_exported", not list(G07.glob("retrieval_gold_*")),
      [p.name for p in G07.glob("retrieval_gold_*")])

# ---------------------------------------------------------------- deliverables present
REQUIRED = [
    "p2_gold_07_review_proposal.md",
    "p2_gold_07_signoff_packet.md",
    "p2_gold_07_b23_recheck.md",
    "p2_gold_07_reviewer_audit.md",
    "p2_gold_07_duplicate_check.md",
    "p2_gold_07_validation.md",
]
for name in REQUIRED:
    check(f"deliverable_present:{name}", (G07 / name).is_file())

# ---------------------------------------------------------------- summary
passed = sum(1 for c in checks if c["passed"])
failed = [c for c in checks if not c["passed"]]
summary = {
    "checks_total": len(checks),
    "checks_passed": passed,
    "checks_failed": len(failed),
    "failed": failed,
    "counts": counts,
    "records": len(records),
    "evidence_chunks": len({c for r in records for c in parse_ids(r["evidence_chunk_ids"])}),
}
(G07 / "p2_gold_07_verify.json").write_text(
    json.dumps({"summary": summary, "checks": checks}, ensure_ascii=False, indent=1),
    encoding="utf-8")

print(json.dumps({k: v for k, v in summary.items() if k != "failed"}, ensure_ascii=False))
if failed:
    print("FAILED:")
    for c in failed:
        print(" -", c["check"], json.dumps(c["detail"], ensure_ascii=False)[:300])
raise SystemExit(1 if failed else 0)
