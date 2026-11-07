"""P2-Gold-06: export signed-off batch-02 Gold cases from the human signoff packet.

Static, one-off export. Reads only local files: the signed markdown packet, the frozen
AI review proposal, the frozen candidate JSONL, the frozen corpus snapshot, the two
review workbooks and the local PDFs. Writes only under p2-gold-06/.

No database, retrieval service, benchmark, git commit or AI approval is used.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(r"D:\AgentAIProgect\RAG")
sys.path.insert(0, str(ROOT))

from rag_app.eval_dataset.corpus import load_corpus_snapshot  # noqa: E402

OUT = ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
G06 = OUT / "p2-gold-06"
P05 = OUT / "p2-gold-05"
P04 = OUT / "p2-gold-04"
PACKET = P05 / "p2_gold_05_signoff_packet.md"
PROPOSAL = P05 / "p2_gold_05_review_proposal.md"
DRAFT_XLSX = P05 / "review_batch02_15_draft.xlsx"
REVIEW_XLSX = OUT / "review.xlsx"
CAND_FILE = ROOT / "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl"
CORPUS_DIR = ROOT / "storage/evaluation/corpus/p1-20261104-v2"
CORPUS_MANIFEST = CORPUS_DIR / "corpus.manifest.json"
B01_JSONL = P04 / "retrieval_gold_batch01_9.jsonl"
B01_META = P04 / "retrieval_gold_batch01_metadata.json"
B01_MANIFEST = P04 / "gold_batch01_manifest.json"

NEWLINE = "\n"
DECISION_ORIGINAL = "接受原题"
DECISION_REVISION = "接受修订"
DECISION_REJECT = "驳回"
VALID_DECISIONS = {DECISION_ORIGINAL, DECISION_REVISION, DECISION_REJECT}

# Frozen hashes recorded by P2-Gold-05 / P2-Gold-04 before this phase started.
FROZEN = {
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/p2_gold_05_review_proposal.md":
        "8811414d2c6447662a0ab4cbad45d60524b475543003fc5af575c32fe3cc8dc2",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/review_batch02_15_draft.xlsx":
        "12f4a4acbb176590de732a7c92c0c620f03ac8376edda10ade52989a96c060b7",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/review.xlsx":
        "df13e2755786cfb7f4d30e44d6323463ce6cbfe49c99a2b5ae87dfeec369d5ea",
    "storage/evaluation/candidates/p1-20261104-structured/candidates.jsonl":
        "31df78af2c96afd25f9221034ab47bbd965f7cb1a5e182dc8c1560cc3f9cf120",
    "storage/evaluation/corpus/p1-20261104-v2/corpus.manifest.json":
        "50bb2c71e205698ae8bee394231d961d19567117e03f489579a1f53b9bf1245f",
    "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl":
        "5995ee6be2871ee7c553ce5fe2f3002a7938dbffedf0ec2b8fed28af8107f4d6",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/retrieval_gold_batch01_9.jsonl":
        "0ee8bbcd963f09c9b300209e8f1edcd93eb27ece1a077af877a37473568ec73a",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/retrieval_gold_batch01_metadata.json":
        "6aa3b20a867be6c2718cc6621b57b10f42029f883e14ac6be314c44a4a703e39",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/rejected_batch01_3.jsonl":
        "3bbeec82efe9ad5fc646479056cf189985314fadb8f5670ea164e28869c1ed91",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/gold_batch01_manifest.json":
        "f1384386520a69e48ef9038faf7a108a11fa5288a17a709282a7d68816398493",
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-05/p2_gold_05_validation.md":
        "2d7454c7e50ea6e7aa83d0cb9a3e5200d2eb73b07a23f75b1119604b9646211f",
}

# Signoff packet hash recorded before the human fields were appended (P2-Gold-05).
PACKET_HASH_BEFORE_SIGNOFF = "e7719369abd01d741e65b717aa4d61e965a92b1d50e51fe8fec2ef6150f313d0"

# Per-case export configuration. Anchors are verified verbatim and unique below.
CASES = {
    "B13": {
        "evidence_roles": {"0eb4bd6e18d599063371f51b": "direct_answer"},
        "targets": [("0eb4bd6e18d599063371f51b", "有限空间作业基础知识")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。第 5.7 节五项清单在同一 Chunk，排除上方第 5.6 节续文。",
    },
    "B14": {
        "evidence_roles": {"0eb4bd6e18d599063371f51b": "level_header",
                           "e010fe39879d92fa21dc59d9": "direct_answer"},
        "targets": [("e010fe39879d92fa21dc59d9", "熟悉智能家居系统架构")],
        "requires_all_evidence": True,
        "evidence_completeness": "requires_both",
        "notes": "仅第 11 页设为检索目标。第 10 页为必需等级列头，单命中第 11 页只证明正文，"
                 "不能证明中级列归属；当前 Hit@K/MRR 不检查两块是否同在一个返回集合。",
    },
    "B15": {
        "evidence_roles": {"0eb4bd6e18d599063371f51b": "level_header",
                           "1c317b1dd2cebfbf9647d03e": "direct_answer"},
        "targets": [("1c317b1dd2cebfbf9647d03e", "掌握网关组网方法")],
        "requires_all_evidence": True,
        "evidence_completeness": "requires_both",
        "notes": "仅第 12 页设为检索目标。第 10 页为必需等级列头，单命中第 12 页只证明正文，"
                 "不能证明高级列归属；当前 Hit@K/MRR 不检查两块是否同在一个返回集合。",
    },
    "B16": {
        "evidence_roles": {"92108b5bb6dcc5b2227d531c": "direct_answer"},
        "targets": [("92108b5bb6dcc5b2227d531c", "开箱检验、复核定位、安装固定、清理现场")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。与 B02、B21 共用同一 Chunk，本题只问安装工序。",
    },
    "B17": {
        "evidence_roles": {"03e5582a4a0f7d3c76a33e66": "direct_answer"},
        "targets": [("03e5582a4a0f7d3c76a33e66", "WH23105001 安装防雷接地装置 室内防雷箱")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。同一 Chunk 同时含上方工作内容段和下方单价表，按编码行定位。",
    },
    "B18": {
        "evidence_roles": {"03e5582a4a0f7d3c76a33e66": "direct_answer"},
        "targets": [("03e5582a4a0f7d3c76a33e66", "WH23105003 室外塔上防雷箱 519.84")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。相邻塔下 302.78、室内 271.78 用于区分行。",
    },
    "B19": {
        "evidence_roles": {"03e5582a4a0f7d3c76a33e66": "direct_answer"},
        "targets": [("03e5582a4a0f7d3c76a33e66", "接地电阻测试：接线、测量")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。目标为表 10.3.3.5 上方的工作内容段，非下方单价表。",
    },
    "B20": {
        "evidence_roles": {"03e5582a4a0f7d3c76a33e66": "direct_answer"},
        "targets": [("03e5582a4a0f7d3c76a33e66", "WH23105001 安装防雷接地装置 室内防雷箱 271.78")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。与 B17 同行不同属性，与 B18 同价列不同行。",
    },
    "B21": {
        "evidence_roles": {"92108b5bb6dcc5b2227d531c": "direct_answer"},
        "targets": [("92108b5bb6dcc5b2227d531c", "WH23104004 波分复用器1:6 以下 62.02")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。与首批 B02 同类异行；同一 Chunk 内另有同价安装行，单 Chunk 命中无法区分行。",
    },
    "B22": {
        "evidence_roles": {"81951fb8b5e157346ed83d77": "direct_answer"},
        "targets": [("81951fb8b5e157346ed83d77", "设备中除为用户提供的唯一账号外")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。第 4.8.2 节正文明确唯一账号例外与禁止范围。",
    },
    "B25": {
        "evidence_roles": {"611a9eb6554a2b482561c775": "direct_answer",
                           "4931f1a7b903ba2672bbb512": "equivalent_evidence"},
        "targets": [("611a9eb6554a2b482561c775", "塔基强度测试"),
                    ("4931f1a7b903ba2672bbb512", "WH23123")],
        "requires_all_evidence": False,
        "evidence_completeness": "either_sufficient",
        "notes": "第 286 页与第 141 页是独立充分的替代证据，任一页可支持四项答案；"
                 "签核 evidence_chunk_ids 只列原引用第 286 页，第 141 页按检索目标补充为等价证据。",
    },
    "B26": {
        "evidence_roles": {"a264a91966d85e2ec3b52e02": "direct_answer"},
        "targets": [("a264a91966d85e2ec3b52e02", "护网外内部以及周边一米杂草、杂物集中清除")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。按推荐题面锁定表 10.3.3.30，同名作业在页 141、149、315 的表述不同。",
    },
    "B27": {
        "evidence_roles": {"95cb40813342a7e91c27e7d3": "direct_answer"},
        "targets": [("95cb40813342a7e91c27e7d3", "WH23131004 地面墙面防水")],
        "requires_all_evidence": False,
        "evidence_completeness": "single_sufficient",
        "notes": "直接证据。相邻 WH23131003 为顶面防水，按编码定位。",
    },
}

DISTINCTNESS = {
    "B14": {"compared_with": ["B12", "B15"],
            "basis": "与首批 B12 同为等级定位但职业功能和证据不同；与 B15 同一跨页表的不同等级和业务行。"},
    "B20": {"compared_with": ["B17", "B18", "B02"],
            "basis": "与批内 B17 同一行（WH23105001）但查不同属性：B17 问子项名称，B20 问综合单价；"
                     "与批内 B18 同类价格题但对应塔上行 WH23105003（519.84）；"
                     "与首批 B02 不同文档、不同事实。三题共享 Chunk，排名结果可能相关。"},
    "B21": {"compared_with": ["B02", "B16"],
            "basis": "与首批 B02 同测试大类、同综合单价列、同目标 Chunk，但 B02 查 WH23104003（1:2，29.18 元/个），"
                     "B21 查 WH23104004（1:6 以下，62.02 元/个），编码、分光比与金额均不同；"
                     "与批内 B16 同 Chunk 但 B16 查安装工序。单次 Chunk 命中无法区分两行。"},
    "B16": {"compared_with": ["B02", "B21"],
            "basis": "与 B02、B21 共用 Chunk，本题范围是安装子项四项动作，B02/B21 查测试价格。"},
    "B17": {"compared_with": ["B18", "B19", "B20"],
            "basis": "与 B18 同列异行、与 B19 同 Chunk 不同段落、与 B20 同行不同属性。"},
    "B25": {"compared_with": ["B26"],
            "basis": "与 B26 同为维护作业题，对象与工作内容不同。"},
    "B19": {"compared_with": ["B17", "B18", "B20"],
            "basis": "同 Chunk 但定位表上方作业说明，B17/B18/B20 定位下方单价表行。"},
}

RESULT = {"checks": [], "facts": {}}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def check(name: str, ok: bool, detail=None) -> None:
    RESULT["checks"].append({"check": name, "passed": bool(ok), "detail": detail})
    if not ok:
        raise SystemExit(f"CHECK FAILED: {name} :: {detail}")


def parse_block(text: str) -> dict:
    """Parse one indented key/value block; continuation lines extend the last value."""
    fields: dict[str, str] = {}
    current = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        match = re.match(r"^([a-z_]+):[ \t]?(.*)$", line)
        if match:
            current = match.group(1)
            fields[current] = match.group(2).strip()
        elif current is not None:
            fields[current] = (fields[current] + NEWLINE + line.strip()).strip()
    return fields


def parse_md(path: Path, fence_lang: str = "text") -> dict[str, dict]:
    text = path.read_text(encoding="utf-8")
    records: dict[str, dict] = {}
    pattern = re.compile(r"^## (B\d+)\s*$(.*?)^```" + fence_lang + r"\n(.*?)^```", re.M | re.S)
    for section, _body, block in pattern.findall(text):
        records[section] = parse_block(block)
    return records


def parse_id_list(value: str) -> list[str]:
    value = value.strip()
    if not value or value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    out = []
    for item in value.split(","):
        token = item.strip().strip("'\"")
        if token:
            out.append(token)
    return out


def normalize_text(value: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKC", value).casefold() if c.isalnum())


def longest_common_substring(a: str, b: str) -> int:
    if not a or not b:
        return 0
    best = 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def main() -> None:
    now = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")

    # ---------- frozen inputs ----------
    input_hashes = {}
    for rel, expected in FROZEN.items():
        actual = sha256_file(ROOT / rel)
        check(f"frozen_input:{rel}", actual == expected, {"expected": expected, "actual": actual})
        input_hashes[rel] = {"sha256": actual, "matches_frozen_record": True}

    packet_hash = sha256_file(PACKET)
    check("signoff_packet_changed_after_p05", packet_hash != PACKET_HASH_BEFORE_SIGNOFF,
          {"before": PACKET_HASH_BEFORE_SIGNOFF, "now": packet_hash,
           "reason": "人工字段在 P2-Gold-05 之后追加，哈希变化符合预期"})
    input_hashes["storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/"
                 "p2-gold-05/p2_gold_05_signoff_packet.md"] = {
        "sha256": packet_hash, "matches_frozen_record": False,
        "note": "P2-Gold-05 记录的签核前哈希已因追加人工字段而变化"}

    # ---------- parse packet + proposal ----------
    packet = parse_md(PACKET)
    proposal = parse_md(PROPOSAL)
    check("packet_record_count", len(packet) == 15, sorted(packet))
    check("proposal_record_count", len(proposal) == 15, sorted(proposal))
    check("packet_batch_ids", sorted(packet) == [f"B{i}" for i in range(13, 28)], sorted(packet))

    candidates = {}
    for line in CAND_FILE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            candidates[item["candidate_id"]] = item
    check("candidate_count", len(candidates) == 57, len(candidates))

    manifest, corpus_rows = load_corpus_snapshot(CORPUS_MANIFEST)
    chunks = {row["chunk_id"]: row for row in corpus_rows}
    check("corpus_chunks", len(chunks) == 447 and manifest["document_count"] == 3,
          {"chunks": len(chunks), "docs": manifest["document_count"]})

    pdf_hash = {}
    for path in sorted((ROOT / "data").glob("*.pdf")):
        pdf_hash[path.name] = sha256_file(path)

    # ---------- classifier ----------
    classifications = {}
    for batch_id in sorted(packet):
        record = packet[batch_id]
        human = {
            "decision": record.get("human_decision", ""),
            "reviewer": record.get("human_reviewer", ""),
            "reviewed_at": record.get("human_reviewed_at", ""),
            "comment": record.get("human_comment", ""),
        }
        complete = all(value.strip() for value in human.values())
        valid = complete and human["decision"] in VALID_DECISIONS
        if not complete:
            kind = "unsigned_missing_fields"
        elif not valid:
            kind = "unsigned_invalid_decision"
        elif human["decision"] == DECISION_ORIGINAL:
            kind = "gold_original"
        elif human["decision"] == DECISION_REVISION:
            kind = "gold_revision"
        else:
            kind = "rejected"
        classifications[batch_id] = {"kind": kind, "human": human, "complete": complete,
                                     "valid_decision": valid}

    check("B23_not_accepted_as_gold",
          classifications["B23"]["kind"].startswith("unsigned"),
          {"decision": classifications["B23"]["human"]["decision"],
           "comment": classifications["B23"]["human"]["comment"]})
    check("B24_rejected", classifications["B24"]["kind"] == "rejected")

    gold_ids = [b for b in sorted(classifications) if classifications[b]["kind"].startswith("gold_")]
    rejected_ids = [b for b in sorted(classifications) if classifications[b]["kind"] == "rejected"]
    unsigned_ids = [b for b in sorted(classifications) if classifications[b]["kind"].startswith("unsigned")]

    # ---------- field-level provenance checks ----------
    for batch_id, record in packet.items():
        prop = proposal[batch_id]
        check(f"proposal_candidate_id:{batch_id}",
              prop.get("candidate_id") == record.get("candidate_id")
              and prop.get("parent_candidate_id", record.get("candidate_id")) == record.get("candidate_id"),
              batch_id)
        check(f"original_question_unchanged:{batch_id}",
              record.get("original_question") == prop.get("original_question"), batch_id)
        check(f"original_answer_unchanged:{batch_id}",
              record.get("original_answer") == prop.get("original_proposed_answer"), batch_id)
        check(f"original_evidence_unchanged:{batch_id}",
              parse_id_list(record.get("original_supporting_chunk_ids", "")) ==
              parse_id_list(prop.get("original_supporting_chunk_ids", "")), batch_id)
        check(f"recommendation_unchanged:{batch_id}",
              record.get("review_recommendation") == prop.get("review_recommendation"), batch_id)
        decision = record.get("human_decision", "")
        if decision == DECISION_REVISION:
            check(f"revised_question_unchanged:{batch_id}",
                  record.get("revised_question", "") == prop.get("recommended_question", ""), batch_id)
            check(f"revised_answer_unchanged:{batch_id}",
                  record.get("revised_answer", "") == prop.get("recommended_proposed_answer", ""), batch_id)
        elif decision in (DECISION_ORIGINAL, DECISION_REJECT):
            # Accept/Reject leave the revised fields empty by packet design.
            check(f"proposal_recommendation_is_original:{batch_id}",
                  prop.get("recommended_question", "") in ("", record.get("original_question", ""))
                  and prop.get("recommended_proposed_answer", "") in ("", record.get("original_answer", "")),
                  batch_id)
        else:
            # Unsigned record: the revised fields still carry the frozen AI proposal.
            check(f"unsigned_record_keeps_proposal:{batch_id}",
                  record.get("revised_question", "") == prop.get("recommended_question", "")
                  and record.get("revised_answer", "") == prop.get("recommended_proposed_answer", ""),
                  batch_id)
        check(f"revised_evidence_unchanged:{batch_id}",
              parse_id_list(record.get("evidence_chunk_ids", "")) ==
              parse_id_list(prop.get("evidence_chunk_ids", "")), batch_id)
        check(f"revised_targets_unchanged:{batch_id}",
              parse_id_list(record.get("retrieval_relevant_chunk_ids", "")) ==
              parse_id_list(prop.get("retrieval_relevant_chunk_ids", "")), batch_id)

        # decision shape consistency
        kind = classifications[batch_id]["kind"]
        revised_q = record.get("revised_question", "").strip()
        revised_a = record.get("revised_answer", "").strip()
        targets = parse_id_list(record.get("retrieval_relevant_chunk_ids", ""))
        if kind == "gold_original":
            check(f"original_decision_has_no_revision:{batch_id}", not revised_q and not revised_a, batch_id)
            check(f"gold_targets_present:{batch_id}", bool(targets), batch_id)
        elif kind == "gold_revision":
            check(f"revision_decision_has_revision:{batch_id}", bool(revised_q and revised_a), batch_id)
            check(f"gold_targets_present:{batch_id}", bool(targets), batch_id)
        elif kind == "rejected":
            check(f"reject_has_no_retrieval_target:{batch_id}", not targets, batch_id)
            check(f"reject_has_no_revision:{batch_id}", not revised_q and not revised_a, batch_id)

    # ---------- candidate linkage ----------
    for batch_id, record in packet.items():
        cid = record["candidate_id"]
        cand = candidates.get(cid)
        check(f"parent_candidate_exists:{batch_id}", cand is not None, cid)
        check(f"parent_question_matches:{batch_id}", cand["question"] == record["original_question"], batch_id)
        check(f"parent_answer_matches:{batch_id}", cand["proposed_answer"] == record["original_answer"], batch_id)
        check(f"parent_evidence_matches:{batch_id}",
              cand["supporting_chunk_ids"] == parse_id_list(record["original_supporting_chunk_ids"]), batch_id)
        check(f"parent_status_pending:{batch_id}", cand["review_status"] == "pending_review", batch_id)

    # ---------- workbook mapping ----------
    workbook_rows = {}
    try:
        from openpyxl import load_workbook
        wb = load_workbook(REVIEW_XLSX, read_only=True, data_only=True)
        ws = wb[wb.sheetnames[0]]
        for batch_id in sorted(packet):
            expected_row = 16 + int(batch_id[1:]) - 12
            workbook_rows[batch_id] = {"row": expected_row,
                                       "batch_cell": ws.cell(row=expected_row, column=1).value,
                                       "candidate_cell": ws.cell(row=expected_row, column=2).value}
            check(f"workbook_row_candidate:{batch_id}",
                  ws.cell(row=expected_row, column=2).value == packet[batch_id]["candidate_id"],
                  {"row": expected_row, "found": ws.cell(row=expected_row, column=2).value})
            workbook_rows[batch_id]["batch_label_present"] = (
                ws.cell(row=expected_row, column=1).value == batch_id)
        wb_draft = load_workbook(DRAFT_XLSX, read_only=True, data_only=True)
        ws_draft = wb_draft[wb_draft.sheetnames[0]]
        check("draft_workbook_mapping",
              all(ws_draft.cell(row=workbook_rows[b]["row"], column=1).value == b for b in packet),
              "draft workbook A17:A31 matches B13-B27")
        placeholder = {ws_draft.cell(row=workbook_rows[b]["row"], column=7).value for b in packet}
        check("draft_workbook_human_column_is_placeholder",
              placeholder <= {"human", None}, sorted(str(p) for p in placeholder))
    except ImportError as exc:  # pragma: no cover
        check("openpyxl_available", False, str(exc))

    # ---------- build gold cases ----------
    batch01_jsonl = [json.loads(line) for line in B01_JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]
    batch01_meta = json.loads(B01_META.read_text(encoding="utf-8"))
    batch01_questions = {item["query"] for item in batch01_jsonl}
    batch01_norm = {normalize_text(item["query"]) for item in batch01_jsonl}

    corpus_snapshot_id = manifest["snapshot_id"]
    gold_cases = []
    jsonl_lines = []
    target_records = []
    anchor_checks = []
    support_checks = []

    for batch_id in gold_ids:
        record = packet[batch_id]
        info = classifications[batch_id]
        config = CASES[batch_id]
        kind = info["kind"]
        cand = candidates[record["candidate_id"]]
        variant = "original" if kind == "gold_original" else "signed_revision"

        question = record["original_question"] if kind == "gold_original" else record["revised_question"]
        answer = record["original_answer"] if kind == "gold_original" else record["revised_answer"]
        check(f"gold_question_nonempty:{batch_id}", bool(question.strip()), batch_id)
        check(f"gold_answer_nonempty:{batch_id}", bool(answer.strip()), batch_id)

        evidence_ids = parse_id_list(record["evidence_chunk_ids"])
        target_ids = parse_id_list(record["retrieval_relevant_chunk_ids"])
        check(f"evidence_ids_match_config:{batch_id}",
              all(cid in config["evidence_roles"] for cid in evidence_ids)
              and all(cid in evidence_ids for cid, role in config["evidence_roles"].items()
                      if role != "equivalent_evidence"),
              {"packet": evidence_ids, "config": list(config["evidence_roles"])})
        check(f"target_ids_match_config:{batch_id}",
              target_ids == [cid for cid, _ in config["targets"]], {"packet": target_ids})

        ordered_ids = list(dict.fromkeys(evidence_ids + target_ids))
        for chunk_id in ordered_ids:
            check(f"chunk_exists:{batch_id}:{chunk_id}", chunk_id in chunks, chunk_id)

        source = record["source_document"]
        check(f"source_document_single:{batch_id}", "；" not in source, source)
        doc_rows = [chunks[cid] for cid in ordered_ids if chunks[cid]["source"] == source]
        check(f"evidence_source_matches_document:{batch_id}",
              len(doc_rows) == len(ordered_ids), batch_id)
        first = chunks[ordered_ids[0]]
        source_pdf = pdf_hash[first["source"]]
        check(f"pdf_present:{batch_id}", source == first["source"], source)
        evidence = []
        for chunk_id in evidence_ids + [cid for cid in target_ids if cid not in evidence_ids]:
            row = chunks[chunk_id]
            evidence.append({
                "chunk_id": chunk_id,
                "pdf_page": row["page_number"],
                "section_title": row["metadata"].get("section_title"),
                "chunk_text_sha256": row["chunk_text_sha256"],
                "role": config["evidence_roles"].get(chunk_id, "equivalent_evidence"),
                "retrieval_relevant": chunk_id in target_ids,
            })
        check(f"evidence_roles_cover_all:{batch_id}",
              {item["chunk_id"] for item in evidence} == set(ordered_ids), batch_id)

        # targets and uniqueness
        expected = []
        for chunk_id, anchor in config["targets"]:
            row = chunks[chunk_id]
            check(f"anchor_verbatim:{batch_id}:{chunk_id}", anchor in row["chunk_text"],
                  {"anchor": anchor})
            matches = [cid for cid, chunk in chunks.items()
                       if chunk["source"] == row["source"]
                       and chunk["metadata"].get("section_title") == row["metadata"].get("section_title")
                       and anchor in chunk["chunk_text"]]
            check(f"anchor_unique_triple:{batch_id}:{chunk_id}", matches == [chunk_id],
                  {"matches": matches})
            target_records.append({
                "batch_id": batch_id, "chunk_id": chunk_id, "anchor": anchor,
                "match_count": len(matches), "matched_chunk_ids": matches,
            })
            expected.append({"source": row["source"],
                             "section_title": row["metadata"].get("section_title"),
                             "text_contains": anchor})

        # answer support signals: numbers and latin tokens must occur in evidence text;
        # longest common substring reported as a diagnostic.
        union_text = " ".join(chunks[cid]["chunk_text"] for cid in ordered_ids)
        numbers = re.findall(r"\d+(?:\.\d+)?", answer)
        latin = re.findall(r"[A-Za-z][A-Za-z0-9.]*(?: [A-Za-z][A-Za-z0-9.]*)*", answer)
        missing_numbers = [n for n in numbers if n not in union_text]
        missing_latin = [t.strip() for t in latin if t.strip() and t.strip() not in union_text]
        norm_answer = normalize_text(answer)
        lcs = longest_common_substring(norm_answer, normalize_text(union_text))
        support_checks.append({
            "batch_id": batch_id, "numbers": numbers, "missing_numbers": missing_numbers,
            "latin_tokens": missing_latin, "answer_norm_len": len(norm_answer),
            "lcs_len": lcs,
            "lcs_ratio": round(lcs / len(norm_answer), 4) if norm_answer else 0.0,
        })
        check(f"answer_numbers_in_evidence:{batch_id}", not missing_numbers, missing_numbers)
        check(f"answer_latin_in_evidence:{batch_id}", not missing_latin, missing_latin)
        threshold = max(3, min(6, len(norm_answer) // 2))
        check(f"answer_lcs_threshold:{batch_id}", lcs >= threshold,
              {"lcs": lcs, "threshold": threshold})

        gold_id_input = {
            "batch_id": batch_id,
            "parent_candidate_id": record["candidate_id"],
            "corpus_snapshot_id": corpus_snapshot_id,
            "review_decision": info["human"]["decision"],
            "question": question,
            "reference_answer": answer,
            "evidence_chunk_ids": evidence_ids,
            "retrieval_relevant_chunk_ids": target_ids,
        }
        gold_case_id = "gold-batch02-sha256:" + sha256_bytes(canonical(gold_id_input))

        case = {
            "batch_id": batch_id,
            "parent_candidate_id": record["candidate_id"],
            "question_type": cand["question_type"],
            "question_type_label": record["question_type"],
            "source_document": source,
            "document_id": first["document_id"],
            "document_version": first["document_version"],
            "corpus_snapshot_id": corpus_snapshot_id,
            "source_pdf_sha256": source_pdf,
            "document_content_hash": first["document_content_hash"],
            "evidence_chunk_ids": evidence_ids,
            "retrieval_relevant_chunk_ids": target_ids,
            "original_supporting_chunk_ids": parse_id_list(record["original_supporting_chunk_ids"]),
            "review_decision": info["human"]["decision"],
            "review_source": {
                "file": "p2_gold_05_signoff_packet.md",
                "section": batch_id,
                "sha256": packet_hash,
                "workbook_row": workbook_rows[batch_id]["row"],
                "workbook_file": "review.xlsx",
                "human_reviewer": info["human"]["reviewer"],
                "human_reviewed_at": info["human"]["reviewed_at"],
                "human_comment": info["human"]["comment"],
            },
            "source_verification": record["source_verification"],
            "evidence": evidence,
            "question": question,
            "reference_answer": answer,
            "answer_variant": variant,
            "retrieval_relevance_notes": config["notes"],
            "requires_all_evidence": config["requires_all_evidence"],
            "required_evidence_count": len(config["targets"]),
            "evidence_completeness": config["evidence_completeness"],
            "gold_case_id": gold_case_id,
        }
        if batch_id == "B25":
            case["equivalent_evidence_chunk_ids"] = ["4931f1a7b903ba2672bbb512"]
            case["evidence_scope_note"] = (
                "签核 evidence_chunk_ids 只列原引用页 286；第 141 页按 retrieval_relevant_chunk_ids "
                "补充为等价证据，两页各自独立充分。")
        if info["human"]["reviewer"] != "system":
            case["signoff_warnings"] = [
                f"human_reviewer 值为 {info['human']['reviewer']!r}，非规范值 system；"
                "按原样保留，建议在最终 50 条定稿前更正。"]
        if batch_id in DISTINCTNESS:
            case["distinctness_from_existing"] = DISTINCTNESS[batch_id]
        if batch_id == "B14" or batch_id == "B15":
            case["scoring_limit"] = (
                "完整证据需页 10 表头与续页正文两块，但检索目标只设正文块；"
                "Hit@K/MRR 无法判断两块是否同在一个返回集合。")
        if batch_id == "B25":
            case["scoring_limit"] = (
                "两个目标为等价证据（OR）。任一命中即计 Hit，指标不要求同一 Top-K 同时含两页。")
        if batch_id in {"B16", "B17", "B18", "B19", "B20", "B21"}:
            case["scoring_limit"] = (
                "同一 Chunk 承载多个 Gold 题，命中与排名高度相关；目标只验证 Chunk 级命中，"
                "不区分行或段落。")

        gold_cases.append(case)
        jsonl_lines.append(json.dumps(
            {"query": question, "expected": expected, "note": gold_case_id},
            ensure_ascii=False, separators=(",", ":")) + NEWLINE)

    check("gold_count", len(gold_cases) == 13, [c["batch_id"] for c in gold_cases])
    check("rejected_count", len(rejected_ids) == 1, rejected_ids)
    check("unsigned_count", len(unsigned_ids) == 1, unsigned_ids)

    # id uniqueness + recomputation from the case payload
    ids = [case["gold_case_id"] for case in gold_cases]
    check("gold_id_unique", len(set(ids)) == len(ids), len(set(ids)))
    for case in gold_cases:
        recomputed = "gold-batch02-sha256:" + sha256_bytes(canonical({
            "batch_id": case["batch_id"],
            "parent_candidate_id": case["parent_candidate_id"],
            "corpus_snapshot_id": case["corpus_snapshot_id"],
            "review_decision": case["review_decision"],
            "question": case["question"],
            "reference_answer": case["reference_answer"],
            "evidence_chunk_ids": case["evidence_chunk_ids"],
            "retrieval_relevant_chunk_ids": case["retrieval_relevant_chunk_ids"],
        }))
        check(f"gold_id_recomputable:{case['batch_id']}", recomputed == case["gold_case_id"], case["batch_id"])

    # parent uniqueness across gold
    parents = [case["parent_candidate_id"] for case in gold_cases]
    check("gold_parent_unique", len(set(parents)) == len(parents), len(set(parents)))

    # duplicates vs batch01 and inside batch02
    dup_rows = []
    max_similarity = 0.0
    max_pair = None
    for case in gold_cases:
        norm_q = normalize_text(case["question"])
        exact = norm_q in batch01_norm
        best = 0.0
        best_q = None
        from difflib import SequenceMatcher
        for prev in batch01_questions:
            ratio = SequenceMatcher(None, norm_q, normalize_text(prev), autojunk=False).ratio()
            if ratio > best:
                best, best_q = ratio, prev
        if best > max_similarity:
            max_similarity, max_pair = best, (case["batch_id"], best_q)
        dup_rows.append({"batch_id": case["batch_id"], "exact_duplicate_with_batch01": exact,
                         "max_similarity": round(best, 4), "closest_batch01_query": best_q})
        check(f"no_exact_duplicate_batch01:{case['batch_id']}", not exact, case["batch_id"])

    internal_pairs = []
    for i, left in enumerate(gold_cases):
        for right in gold_cases[i + 1:]:
            same_q = normalize_text(left["question"]) == normalize_text(right["question"])
            same_a = normalize_text(left["reference_answer"]) == normalize_text(right["reference_answer"])
            if same_q:
                internal_pairs.append({"pair": [left["batch_id"], right["batch_id"]], "same_question": True})
            check(f"no_internal_duplicate:{left['batch_id']}:{right['batch_id']}",
                  not same_q, same_a)
    check("batch02_no_internal_duplicates", not internal_pairs, internal_pairs)

    # ---------- rejected record ----------
    rejected_records = []
    for batch_id in rejected_ids:
        record = packet[batch_id]
        info = classifications[batch_id]
        cand = candidates[record["candidate_id"]]
        evidence_ids = parse_id_list(record["evidence_chunk_ids"])
        check(f"reject_evidence_present:{batch_id}", bool(evidence_ids), batch_id)
        evidence = []
        for chunk_id in evidence_ids:
            check(f"reject_chunk_exists:{batch_id}:{chunk_id}", chunk_id in chunks, chunk_id)
            row = chunks[chunk_id]
            evidence.append({
                "chunk_id": chunk_id,
                "pdf_page": row["page_number"],
                "section_title": row["metadata"].get("section_title"),
                "chunk_text_sha256": row["chunk_text_sha256"],
                "role": "rejection_audit",
                "retrieval_relevant": False,
            })
        sources = [chunks[cid]["source"] for cid in evidence_ids]
        documents = []
        for chunk_id in evidence_ids:
            row = chunks[chunk_id]
            documents.append({
                "source_document": row["source"],
                "document_id": row["document_id"],
                "document_version": row["document_version"],
                "document_content_hash": row["document_content_hash"],
                "source_pdf_sha256": pdf_hash[row["source"]],
                "chunk_id": chunk_id,
                "pdf_page": row["page_number"],
            })
        document_id = chunks[evidence_ids[0]]["document_id"]
        rejected_records.append({
            "batch_id": batch_id,
            "parent_candidate_id": record["candidate_id"],
            "question_type": cand["question_type"],
            "question_type_label": record["question_type"],
            "source_document": "；".join(dict.fromkeys(sources)),
            "documents": documents,
            "document_id": document_id,
            "document_version": chunks[evidence_ids[0]]["document_version"],
            "corpus_snapshot_id": corpus_snapshot_id,
            "source_pdf_sha256": pdf_hash[sources[0]],
            "document_content_hash": chunks[evidence_ids[0]]["document_content_hash"],
            "evidence_chunk_ids": evidence_ids,
            "retrieval_relevant_chunk_ids": [],
            "original_supporting_chunk_ids": parse_id_list(record["original_supporting_chunk_ids"]),
            "review_decision": info["human"]["decision"],
            "review_source": {
                "file": "p2_gold_05_signoff_packet.md",
                "section": batch_id,
                "sha256": packet_hash,
                "workbook_row": workbook_rows[batch_id]["row"],
                "workbook_file": "review.xlsx",
                "human_reviewer": info["human"]["reviewer"],
                "human_reviewed_at": info["human"]["reviewed_at"],
                "human_comment": info["human"]["comment"],
            },
            "source_verification": record["source_verification"],
            "evidence": evidence,
            "original_question": record["original_question"],
            "original_answer": record["original_answer"],
            "rejection_reason": record["review_reason"],
            "rejection_reason_source": "signoff_packet.review_reason",
            "gold_case_id": None,
        })

    # ---------- unsigned record (not gold, not rejection) ----------
    unsigned_records = []
    for batch_id in unsigned_ids:
        record = packet[batch_id]
        info = classifications[batch_id]
        cand = candidates[record["candidate_id"]]
        evidence_ids = parse_id_list(record["evidence_chunk_ids"])
        for chunk_id in evidence_ids:
            check(f"unsigned_chunk_exists:{batch_id}:{chunk_id}", chunk_id in chunks, chunk_id)
        unsigned_records.append({
            "batch_id": batch_id,
            "parent_candidate_id": record["candidate_id"],
            "status": "unsigned_pending_clarification",
            "unsigned_reason": (
                "human_decision 值为「保留测试」，不属于 接受原题／接受修订／驳回 三种已定义取值；"
                "human_comment 为待确认问题「鉴权方式和加密方式是同一个吗？」。"
                "该记录不构成完整人工签核，因此既不纳入 Gold，也不按驳回归档。"),
            "detected_human_decision": info["human"]["decision"],
            "review_source": {
                "file": "p2_gold_05_signoff_packet.md",
                "section": batch_id,
                "sha256": packet_hash,
                "workbook_row": workbook_rows[batch_id]["row"],
                "human_reviewer": info["human"]["reviewer"],
                "human_reviewed_at": info["human"]["reviewed_at"],
                "human_comment": info["human"]["comment"],
            },
            "original_question": record["original_question"],
            "original_answer": record["original_answer"],
            "original_supporting_chunk_ids": parse_id_list(record["original_supporting_chunk_ids"]),
            "recommended_question": record["revised_question"],
            "recommended_answer": record["revised_answer"],
            "evidence_chunk_ids": evidence_ids,
            "retrieval_relevant_chunk_ids": parse_id_list(record["retrieval_relevant_chunk_ids"]),
            "question_type": cand["question_type"],
            "gold_case_id": None,
        })

    # ---------- eval schema compatibility ----------
    gold_jsonl_path = G06 / "retrieval_gold_batch02_13.jsonl"
    gold_jsonl_bytes = "".join(jsonl_lines).encode("utf-8")
    schema_loader = "unavailable"
    schema_cases = 0
    loader_error = None
    try:
        from rag_app.operations.evaluation import load_retrieval_eval_cases
        gold_jsonl_path.write_bytes(gold_jsonl_bytes)
        loaded = load_retrieval_eval_cases(gold_jsonl_path)
        schema_cases = len(loaded)
        schema_loader = "rag_app.operations.evaluation.load_retrieval_eval_cases"
        check("eval_schema_loads", schema_cases == 13, schema_cases)
        for case, loaded_case in zip(gold_cases, loaded):
            check(f"eval_case_query:{case['batch_id']}", loaded_case.query == case["question"], case["batch_id"])
            check(f"eval_case_target_count:{case['batch_id']}",
                  len(loaded_case.expected) == len(case["retrieval_relevant_chunk_ids"]), case["batch_id"])
            check(f"eval_case_note:{case['batch_id']}", loaded_case.note == case["gold_case_id"], case["batch_id"])
    except Exception as exc:  # noqa: BLE001
        loader_error = f"{type(exc).__name__}: {exc}"
        gold_jsonl_path.write_bytes(gold_jsonl_bytes)

    # independent replay of the evaluator match rule over the whole corpus
    comparisons = 0
    negative_mismatches = []
    for case in gold_cases:
        for chunk_id, anchor in [(t["chunk_id"], t["anchor"]) for t in target_records
                                 if t["batch_id"] == case["batch_id"]]:
            row = chunks[chunk_id]
            for other_id, other in chunks.items():
                comparisons += 1
                matched = (other["source"] == row["source"]
                           and other["metadata"].get("section_title") == row["metadata"].get("section_title")
                           and anchor in other["chunk_text"])
                if matched and other_id != chunk_id:
                    negative_mismatches.append({"batch_id": case["batch_id"], "anchor": anchor,
                                                "unexpected_chunk": other_id})
    check("target_replay_no_false_positive", not negative_mismatches, negative_mismatches[:5])

    # first-hit rank sanity for the single-chunk replay (target chunk always rank 1)
    check("comparisons_count", comparisons == 447 * sum(len(c["retrieval_relevant_chunk_ids"]) for c in gold_cases),
          comparisons)

    # ---------- write artifacts ----------
    metadata = {
        "gold_version": "p2-gold-06-batch02-v1",
        "batch": "batch02",
        "corpus_snapshot_id": corpus_snapshot_id,
        "generated_at": now,
        "source_packet_sha256": packet_hash,
        "cases": gold_cases,
        "counts": {
            "gold": len(gold_cases),
            "accepted_original": sum(1 for c in gold_cases if c["answer_variant"] == "original"),
            "accepted_revision": sum(1 for c in gold_cases if c["answer_variant"] == "signed_revision"),
            "cumulative_gold": len(batch01_jsonl) + len(gold_cases),
            "remaining_to_50": 50 - (len(batch01_jsonl) + len(gold_cases)),
        },
    }
    metadata_bytes = (json.dumps(metadata, ensure_ascii=False, indent=2) + NEWLINE).encode("utf-8")

    rejected_bytes = "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + NEWLINE
                             for item in rejected_records).encode("utf-8")
    unsigned_bytes = "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + NEWLINE
                             for item in unsigned_records).encode("utf-8")

    (G06 / "retrieval_gold_batch02_metadata.json").write_bytes(metadata_bytes)
    (G06 / "rejected_batch02_1.jsonl").write_bytes(rejected_bytes)
    (G06 / "unsigned_batch02_1.jsonl").write_bytes(unsigned_bytes)

    # ---------- readback verification ----------
    readback = json.loads((G06 / "retrieval_gold_batch02_metadata.json").read_text(encoding="utf-8"))
    check("metadata_readback_cases", len(readback["cases"]) == 13, len(readback["cases"]))
    jsonl_readback = [json.loads(line) for line in
                      (G06 / "retrieval_gold_batch02_13.jsonl").read_text(encoding="utf-8").splitlines()
                      if line.strip()]
    check("jsonl_readback_lines", len(jsonl_readback) == 13, len(jsonl_readback))
    check("jsonl_note_matches_metadata",
          [item["note"] for item in jsonl_readback] == [case["gold_case_id"] for case in readback["cases"]],
          "note/gold_case_id alignment")
    for item, case in zip(jsonl_readback, readback["cases"]):
        check(f"jsonl_query_matches:{case['batch_id']}", item["query"] == case["question"], case["batch_id"])
        for target, chunk_id in zip(item["expected"], case["retrieval_relevant_chunk_ids"]):
            row = chunks[chunk_id]
            check(f"jsonl_target_matches:{case['batch_id']}",
                  target["source"] == row["source"]
                  and target["section_title"] == row["metadata"].get("section_title")
                  and target["text_contains"] in row["chunk_text"], chunk_id)

    # gold vs rejected disjointness
    check("gold_rejected_disjoint",
          not ({c["parent_candidate_id"] for c in gold_cases} &
               {r["parent_candidate_id"] for r in rejected_records}),
          "parent ids disjoint")

    # ---------- facts for the report ----------
    RESULT["facts"] = {
        "generated_at": now,
        "packet_sha256": packet_hash,
        "packet_sha256_before_signoff": PACKET_HASH_BEFORE_SIGNOFF,
        "corpus_snapshot_id": corpus_snapshot_id,
        "corpus_manifest_sha256": manifest["manifest_sha256"],
        "corpus_chunks": len(chunks),
        "corpus_documents": manifest["document_count"],
        "candidate_count": len(candidates),
        "records": {b: classifications[b] for b in sorted(classifications)},
        "gold_ids": gold_ids,
        "rejected_ids": rejected_ids,
        "unsigned_ids": unsigned_ids,
        "counts": metadata["counts"],
        "gold_evidence_entries": sum(len(c["evidence_chunk_ids"]) for c in gold_cases),
        "gold_unique_evidence_chunks": len({cid for c in gold_cases for cid in c["evidence_chunk_ids"]}),
        "gold_evidence_entries_including_equivalent":
            sum(len(c["evidence"]) for c in gold_cases),
        "retrieval_targets": sum(len(c["retrieval_relevant_chunk_ids"]) for c in gold_cases),
        "retrieval_target_unique_chunks":
            len({cid for c in gold_cases for cid in c["retrieval_relevant_chunk_ids"]}),
        "rejection_evidence_chunks": sum(len(r["evidence_chunk_ids"]) for r in rejected_records),
        "target_replay_comparisons": comparisons,
        "target_replay_false_positives": len(negative_mismatches),
        "schema_loader": schema_loader,
        "schema_loaded_cases": schema_cases,
        "schema_loader_error": loader_error,
        "target_uniqueness": target_records,
        "answer_support": support_checks,
        "duplicate_check_vs_batch01": dup_rows,
        "max_similarity_vs_batch01": {"value": round(max_similarity, 4), "pair": max_pair},
        "batch01_questions": sorted(batch01_questions),
        "workbook_rows": workbook_rows,
        "pdf_sha256": pdf_hash,
        "input_hashes": input_hashes,
        "outputs": {
            "retrieval_gold_batch02_13.jsonl": sha256_bytes(gold_jsonl_bytes),
            "retrieval_gold_batch02_metadata.json": sha256_bytes(metadata_bytes),
            "rejected_batch02_1.jsonl": sha256_bytes(rejected_bytes),
            "unsigned_batch02_1.jsonl": sha256_bytes(unsigned_bytes),
        },
    }

    verify_bytes = (json.dumps(RESULT, ensure_ascii=False, indent=2) + NEWLINE).encode("utf-8")
    (G06 / "p2_gold_06_verify.json").write_bytes(verify_bytes)

    failed = [item for item in RESULT["checks"] if not item["passed"]]
    print("generated_at", now)
    print("checks_total", len(RESULT["checks"]), "failed", len(failed))
    print("gold", len(gold_cases), "original", metadata["counts"]["accepted_original"],
          "revision", metadata["counts"]["accepted_revision"],
          "rejected", len(rejected_records), "unsigned", len(unsigned_records))
    print("cumulative_gold", metadata["counts"]["cumulative_gold"],
          "remaining_to_50", metadata["counts"]["remaining_to_50"])
    print("schema_loader", schema_loader, "cases", schema_cases, "error", loader_error)
    print("targets", RESULT["facts"]["retrieval_targets"], "unique",
          RESULT["facts"]["retrieval_target_unique_chunks"],
          "comparisons", comparisons, "false_positives", len(negative_mismatches))
    print("max_similarity_vs_batch01", RESULT["facts"]["max_similarity_vs_batch01"])


if __name__ == "__main__":
    main()
