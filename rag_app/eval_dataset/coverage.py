"""Corpus-only evidence inventory. Metadata and standard references are not labels."""

from __future__ import annotations

from collections import Counter, defaultdict
import re
import unicodedata

from rag_app.core.error_codes import normalize_error_code


CODE_LABEL = r"(?:(?:异常|错误|故障|报错|返回|状态|告警|报警)(?:代码|码)|(?:error|fault|alarm)\s*code)"
CODE_TOKEN = r"[a-z][-_]?\d{2,6}"
CODE_LEFT = r"(?<![a-z0-9_./-])"
# A final sentence period is allowed, but decimal/subsection continuations are not.
CODE_RIGHT = r"(?![a-z0-9_/-]|\.[a-z0-9])"
_LABELED_CODE = re.compile(
    rf"(?<![a-z0-9]){CODE_LABEL}[ \t:：=为]*{CODE_LEFT}({CODE_TOKEN}){CODE_RIGHT}", re.I,
)
_ERROR_LIKE = re.compile(rf"{CODE_LEFT}e[-_]?\d{{2,6}}{CODE_RIGHT}", re.I)
_FULL_CODE = re.compile(rf"{CODE_LEFT}{CODE_TOKEN}{CODE_RIGHT}", re.I)
_CODE_CUE = re.compile(CODE_LABEL, re.I)
_NON_CODE_CLAUSE = re.compile(
    r"并非|不是|不存在|误抽取|标准编号|标准号|编号片段|"
    r"not\s+(?:an?\s+)?(?:actual\s+)?(?:error|fault)\s*code|"
    r"\b(?:spurious|does not exist|standard (?:number|identifier) fragment)\b", re.I,
)


def evidenced_error_codes(text: str) -> set[str]:
    """Require explicit code context in verbatim text and retain whole tokens."""
    codes = set()
    for clause in re.split(r"[\n\r。！？!?;；]", unicodedata.normalize("NFKC", text)):
        if _NON_CODE_CLAUSE.search(clause):
            continue
        for match in _LABELED_CODE.finditer(clause):
            if not re.search(r"(?:非|not)\s*(?:an?\s*)?$", clause[:match.start()], re.I):
                codes.add(normalize_error_code(match[1]))
    return codes


def error_code_claims(text: str) -> tuple[bool, set[str]]:
    """Treat either word order as a code assertion when the text names a code type."""
    normalized = unicodedata.normalize("NFKC", text)
    has_cue = _CODE_CUE.search(normalized) is not None
    pattern = _FULL_CODE if has_cue else _ERROR_LIKE
    return has_cue, {normalize_error_code(match[0]) for match in pattern.finditer(normalized)}


def audit_corpus(manifest: dict, rows: list[dict]) -> dict:
    topics, parse_status, document_chunks = Counter(), Counter(), Counter()
    evidenced = defaultdict(list)
    declared = set()
    for row in rows:
        metadata = row["metadata"]
        module = (metadata.get("business_module") or "").strip()
        if module:
            topics[module] += 1
        parse_status[metadata.get("chunk_parse_quality_status") or "unknown"] += 1
        document_chunks[row["document_id"]] += 1
        codes = [metadata.get("error_code"), *(metadata.get("error_codes") or [])]
        declared.update(normalize_error_code(code) for code in codes if code)
        for code in sorted(evidenced_error_codes(row["chunk_text"])):
            evidenced[code].append(row["chunk_id"])

    unique = len({row["chunk_text_sha256"] for row in rows})
    return {
        "snapshot_id": manifest["snapshot_id"], "scope": manifest["scope"],
        "valid_document_count": len(document_chunks), "valid_chunk_count": len(rows),
        "unique_chunk_text_count": unique,
        "chunks_by_document": dict(document_chunks),
        "business_topic_count": len(topics), "chunks_by_business_module": dict(topics),
        "business_module_note": "Exported metadata labels; subject classifications require human review.",
        "chunks_without_business_module": len(rows) - sum(topics.values()),
        "chunk_parse_status": dict(parse_status),
        "error_code_fields_in_export_policy": sorted(
            {"error_code", "error_codes"} & set(manifest["metadata_policy"]["fields"])
        ),
        "error_code_fields_excluded_at_export": sorted(
            {"error_code", "error_codes"} & set(manifest["metadata_policy"]["excluded_keys"])
        ),
        "supported_error_code_count": len(evidenced),
        "error_code_evidence_chunk_ids": dict(evidenced),
        "metadata_only_error_code_count": len(declared - evidenced.keys()),
        "error_code_assessment": (
            "Only whole codes with explicit error-code labels in the snapshot text count. "
            "Standard identifiers and metadata without text evidence do not count."
        ),
        "gold_target": 50,
    }
