"""Generate review-only candidates directly from one verified corpus snapshot."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import unicodedata

from rag_app.eval_dataset.corpus import CorpusExportError, load_corpus_snapshot
from rag_app.eval_dataset.coverage import audit_corpus, error_code_claims, evidenced_error_codes
from rag_app.eval_dataset.ollama import LocalOllama, ModelError, SYSTEM_PROMPT
from rag_app.eval_dataset.schemas import CorpusScope


PROMPT_VERSION = "rag-candidates-p1-v4"
TARGETS = {"exact_entity": 30, "semantic": 35, "multi_condition": 25, "confusable": 30}
MIN_SUPPORT = {"exact_entity": 1, "semantic": 1, "multi_condition": 2, "confusable": 2}
_TEXT_LIMIT = 2200
_TOKEN = re.compile(r"[A-Za-z0-9]+(?:[./_-][A-Za-z0-9]+)*")
_TOKEN_JOIN = re.compile(r"[A-Za-z\d_./+-]")
_UNSAFE_TEXT = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff]")
_PROMPT = """仅用给定 passage 生成自包含的中文检索候选题。只做任务指定的题型，
最多写 count 条。证据不足则少写或返回空数组。禁止编造实体、条件、数值或异常码。
答案必须是一个所选 passage 中连续出现的短原文。问题不要说“本文”“根据原文”。
每题输出 question、difficulty (easy/medium/hard)、proposed_answer 和 evidence。
evidence 数组只输出 passage_id 和任务所需的 anchor，由程序回填原文。
题目之间覆盖不同事实，不要只换一种问法。只返回 {"candidates":[...]}。
"""
_TASKS = {
    "exact_entity": (
        "问题中必须使用某个所选 passage 里逐字出现的专名、设备、接口、标准全号或明确标注的异常码。"
        "额外输出 exact_entity，内容必须同时逐字出现在问题和所选 passage 中。标准编号属于普通实体。"
    ),
    "semantic": "用自然的转述提问，定位一项有业务意义且原文可回答的事实。",
    "multi_condition": (
        "选择来自不同 chunk 的两个 passage，每个都必须提供一个问题涉及的真实条件。"
        "每个 evidence 元素的 anchor 填一个条件短语，须同时出现在问题和对应 passage 中，两者不同。"
    ),
    "confusable": (
        "对比来自不同 chunk 的两个容易混淆的对象或场景。题中写出两者，询问其中一项的规则。"
        "每个 evidence 元素的 anchor 填对应的对象或场景名称，须同时出现在问题和对应 passage 中，两者不同。"
    ),
}


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalized(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def _contains_entity(text: str, entity: str) -> bool:
    text, entity = (unicodedata.normalize("NFKC", value).casefold() for value in (text, entity))
    if entity.isascii():
        return re.search(rf"(?<![a-z0-9_./-]){re.escape(entity)}(?![a-z0-9_/-]|\.[a-z0-9])", text) is not None
    return entity in text


def _answer_is_in_excerpt(answer: str, quote: str, source: str) -> bool:
    if answer not in quote:
        return False
    # Match the exact answer within the quoted occurrence, but inspect the
    # original neighbors so an excerpt boundary cannot turn 50 into 5.
    left = r"(?<![A-Za-z\d_./+-])" if re.fullmatch(r"[A-Za-z\d]", answer[0]) else ""
    right = r"(?![A-Za-z\d_/-]|\.[A-Za-z\d])" if re.fullmatch(r"[A-Za-z\d]", answer[-1]) else ""
    if not left and not right:
        return True
    pattern = re.compile(left + re.escape(answer) + right)
    return any(
        match.end() <= occurrence.end()
        for occurrence in re.finditer(re.escape(quote), source)
        if (match := pattern.search(source, occurrence.start())) is not None
    )


def _batches(rows: list[dict], seed: int):
    # Keep adjacent pages available for questions with two pieces of evidence.
    # Round-robin over document/ACL queues so a long manual cannot crowd out others.
    grouped = defaultdict(list)
    for row in rows:
        grouped[tuple(row["permission_tags"]), row["document_id"]].append(row)
    rng = random.Random(seed)
    queues = deque()
    for key in sorted(grouped, key=lambda group: min(r["chunk_id"] for r in grouped[group])):
        ordered = sorted(grouped[key], key=lambda r: (r["page_number"] or 0, r["chunk_id"]))
        by_text = {}
        for row in ordered:
            by_text.setdefault(row["chunk_text_sha256"], row)
        unique = list(by_text.values())
        packets = [unique[i:i + 3] for i in range(0, len(unique), 3)]
        rng.shuffle(packets)
        queues.append(deque(packets))
    while queues:
        packets = queues.popleft()
        yield packets.popleft()
        if packets:
            queues.append(packets)


def _validate(raw: object, excerpts: dict[str, str], full_text: dict[str, str],
              requested: dict) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, "invalid_candidate_schema"
    question, answer = raw.get("question"), raw.get("proposed_answer")
    kind, difficulty = raw.get("question_type"), raw.get("difficulty")
    if (
        not isinstance(question, str) or not 5 <= len(_normalized(question)) <= 180
        or not isinstance(answer, str) or not 1 <= len(_normalized(answer)) <= 240
        or not isinstance(kind, str) or kind not in TARGETS
        or difficulty not in ("easy", "medium", "hard")
        or len(question) > 250 or len(answer) > 300
        or _UNSAFE_TEXT.search(question) or _UNSAFE_TEXT.search(answer)
    ):
        return None, "invalid_candidate_schema"
    if not requested.get(kind):
        return None, "unrequested_type"
    evidence = raw.get("evidence")
    if not isinstance(evidence, list) or not MIN_SUPPORT[kind] <= len(evidence) <= len(excerpts):
        return None, "insufficient_evidence"
    citations, anchors = {}, {}
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get("chunk_id"), str):
            return None, "invalid_candidate_schema"
        chunk_id, quote = item["chunk_id"], item.get("excerpt")
        if chunk_id not in excerpts:
            return None, "out_of_batch_reference"
        if (
            not isinstance(quote, str) or not 12 <= len(quote.strip()) <= 480
            or quote not in excerpts[chunk_id] or chunk_id in citations
        ):
            return None, "invalid_excerpt"
        citations[chunk_id] = quote
        if MIN_SUPPORT[kind] > 1:
            anchor = item.get("anchor")
            if (
                not isinstance(anchor, str) or not 2 <= len(_normalized(anchor)) <= 45
                or not _contains_entity(question, anchor) or not _contains_entity(quote, anchor)
            ):
                return None, "missing_question_anchor"
            anchors[chunk_id] = anchor
    question, answer = question.strip(), answer.strip()
    if not any(_answer_is_in_excerpt(answer, quote, full_text[key]) for key, quote in citations.items()):
        return None, "unanchored_answer"
    if len({_normalized(quote) for quote in citations.values()}) < MIN_SUPPORT[kind]:
        return None, "insufficient_distinct_evidence"
    if anchors and len({_normalized(anchor) for anchor in anchors.values()}) != len(anchors):
        return None, "duplicate_question_anchor"
    supported_codes = set().union(*(
        evidenced_error_codes(quote) & evidenced_error_codes(full_text[chunk_id])
        for chunk_id, quote in citations.items()
    ))
    code_cue, mentioned_codes = error_code_claims(f"{question}\n{answer}")
    if mentioned_codes - supported_codes or (code_cue and not mentioned_codes):
        return None, "unverified_error_code"

    tokens = _TOKEN.findall(unicodedata.normalize("NFKC", question))
    if any(
        not any(_contains_entity(quote, token) for quote in citations.values())
        for token in tokens
        if any(c.isdigit() for c in token) or (token.isupper() and len(token) > 1)
    ):
        return None, "unsupported_question_token"
    entity = raw.get("exact_entity")
    if kind == "exact_entity" and (
        not isinstance(entity, str) or not 2 <= len(entity.strip()) <= 80
        or not _contains_entity(question, entity.strip())
        or not any(_contains_entity(quote, entity.strip()) for quote in citations.values())
    ):
        return None, "unverified_exact_entity"
    result = {
        "question": question, "question_type": kind, "difficulty": difficulty,
        "proposed_answer": answer, "supporting_chunk_ids": sorted(citations),
        "evidence_excerpt": {key: citations[key] for key in sorted(citations)},
    }
    if kind == "exact_entity":
        result["exact_entity"] = entity.strip()
    if anchors:
        result["question_anchors"] = anchors
    if mentioned_codes:
        result["evidenced_error_codes"] = sorted(mentioned_codes)
    return result, None


def _passages(packet: list[dict]) -> dict[str, tuple[str, str]]:
    passages = {}
    for row in packet:
        text = row["chunk_text"][:_TEXT_LIMIT]
        start = 0
        while start < len(text):
            end = min(start + 360, len(text))
            if end < len(text):
                boundary = max(text.rfind(mark, start + 180, end) for mark in ("。", "；", "\n"))
                if boundary >= 0:
                    end = boundary + 1
                while (
                    end < min(len(text), start + 400)
                    and _TOKEN_JOIN.fullmatch(text[end - 1]) and _TOKEN_JOIN.fullmatch(text[end])
                ):
                    end += 1
            quote = text[start:end].strip()
            if len(quote) >= 12:
                passages[f"p{len(passages) + 1}"] = (row["chunk_id"], quote)
            start = end
    return passages


def _resolve_evidence(raw: object, kind: str, passages: dict[str, tuple[str, str]]) -> dict | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("evidence"), list):
        return None
    evidence = []
    for item in raw["evidence"]:
        if not isinstance(item, dict) or not isinstance(item.get("passage_id"), str):
            return None
        if item["passage_id"] not in passages:
            return None
        chunk_id, excerpt = passages[item["passage_id"]]
        evidence.append({"chunk_id": chunk_id, "excerpt": excerpt, "anchor": item.get("anchor")})
    return {**raw, "question_type": kind, "evidence": evidence}


def _response_schema(kind: str, count: int, passages: dict[str, tuple[str, str]]) -> dict:
    evidence = {"passage_id": {"type": "string", "enum": list(passages)}}
    if MIN_SUPPORT[kind] == 2:
        evidence["anchor"] = {"type": "string", "minLength": 2, "maxLength": 45}
    fields = {
        "question": {"type": "string", "minLength": 5, "maxLength": 180},
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
        "proposed_answer": {"type": "string", "minLength": 1, "maxLength": 180},
        "evidence": {
            "type": "array", "minItems": MIN_SUPPORT[kind], "maxItems": MIN_SUPPORT[kind],
            "items": {"type": "object", "properties": evidence, "required": list(evidence),
                      "additionalProperties": False},
        },
    }
    if kind == "exact_entity":
        fields["exact_entity"] = {"type": "string", "minLength": 2, "maxLength": 80}
    return {
        "type": "object", "required": ["candidates"], "additionalProperties": False,
        "properties": {"candidates": {
            "type": "array", "minItems": 0, "maxItems": count,
            "items": {"type": "object", "properties": fields, "required": list(fields),
                      "additionalProperties": False},
        }},
    }


def _collect(rows, client, model_digest, seed, max_batches, options, candidates, counts, rejected, errors):
    # De-duplication is scoped to the exact ACL cohort, including across batches/types.
    prior = defaultdict(list)
    attempts = 0
    succeeded = 0
    consecutive_errors = 0
    pending = deque((kind, iter(_batches(rows, seed))) for kind in TARGETS)
    while pending and attempts < max_batches:
        kind, packets = pending.popleft()
        if counts[kind] >= TARGETS[kind]:
            continue
        for packet in packets:
            passages = _passages(packet)
            if len({chunk_id for chunk_id, _ in passages.values()}) >= MIN_SUPPORT[kind]:
                break
        else:
            continue
        pending.append((kind, packets))
        tags = tuple(packet[0]["permission_tags"])
        full_text = {r["chunk_id"]: r["chunk_text"] for r in packet}
        count = min(4, TARGETS[kind] - counts[kind])
        data = {"count": count, "task": _TASKS[kind], "passages": [
            {"passage_id": key, "chunk": chunk_id, "text": quote}
            for key, (chunk_id, quote) in passages.items()
        ]}
        attempts += 1
        try:
            items = client.generate(
                _PROMPT + _json_bytes(data).decode("utf-8"), options, model_digest,
                schema=_response_schema(kind, count, passages),
            )
        except ModelError as exc:
            errors[str(exc)] += 1
            consecutive_errors += 1
            if consecutive_errors == 3 or str(exc) in {"model_not_local", "model_not_installed", "model_digest_changed"}:
                break
            continue
        succeeded += 1
        consecutive_errors = 0
        for raw in items:
            proposal = _resolve_evidence(raw, kind, passages)
            if proposal is None:
                rejected["invalid_passage_reference"] += 1
                continue
            candidate, reason = _validate(proposal, full_text, full_text, {kind: count})
            if reason:
                rejected[reason] += 1
                continue
            if counts[kind] == TARGETS[kind]:
                rejected["category_quota_met"] += 1
                continue
            question = _normalized(candidate["question"])
            answer = _normalized(candidate["proposed_answer"])
            if any(
                answer == old_answer or SequenceMatcher(None, question, old_q, autojunk=False).ratio() >= 0.88
                for old_q, old_answer in prior[tags]
            ):
                rejected["duplicate"] += 1
                continue
            prior[tags].append((question, answer))
            candidate["chunk_permission_tags"] = list(tags)
            counts[kind] += 1
            candidates.append(candidate)
    return attempts, succeeded


def run_generation(
    manifest_path: Path, scope: CorpusScope, output_dir: Path, *,
    endpoint: str | None = None, model: str | None = None, seed: int = 42,
    max_batches: int = 72, timeout: float = 120, audit_only: bool = False,
) -> dict:
    if not isinstance(scope, CorpusScope):
        raise ValueError("An explicit CorpusScope is required.")
    manifest, rows = load_corpus_snapshot(manifest_path, expected_scope=scope)
    if (type(seed) is not int or not 0 <= seed <= 2**31 - 1
            or type(max_batches) is not int or not 1 <= max_batches <= 1000):
        raise ValueError("Use a nonnegative 32-bit seed and 1–1000 batches.")
    if not audit_only and (not endpoint or not model):
        raise ValueError("An explicit loopback endpoint and installed model are required.")
    client = None if audit_only else LocalOllama(endpoint, model, timeout)
    source_hashes = {
        name: _digest(Path(__file__).with_name(name).read_bytes())
        for name in ("candidates.py", "corpus.py", "coverage.py", "ollama.py", "schemas.py")
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    coverage = audit_corpus(manifest, rows)
    options = {"seed": seed, "temperature": 0, "num_ctx": 8192, "num_predict": 1200}
    counts, rejected, errors = Counter(), Counter(), Counter()
    candidates = []
    model_digest = None
    attempts = succeeded = 0
    if client:
        try:
            model_digest = client.local_digest()
        except ModelError as exc:
            errors[str(exc)] += 1
        else:
            attempts, succeeded = _collect(
                rows, client, model_digest, seed, max_batches, options, candidates, counts, rejected, errors,
            )

    snapshot_id = manifest["snapshot_id"]
    for candidate in candidates:
        identity = [snapshot_id, candidate["chunk_permission_tags"], _normalized(candidate["question"])]
        candidate.update({
            "candidate_id": "sha256:" + _digest(_json_bytes(identity)),
            "snapshot_id": snapshot_id, "generator_model": model, "prompt_version": PROMPT_VERSION,
            "review_status": "pending_review", "scope": manifest["scope"],
        })
    by_type = {
        kind: {"target": target, "accepted": counts[kind], "shortfall": target - counts[kind]}
        for kind, target in TARGETS.items()
    }
    if audit_only:
        status = "audit_only"
    elif errors:
        status = "partial_model_failure" if succeeded else "model_failed"
    else:
        status = "completed" if len(candidates) == sum(TARGETS.values()) else "completed_with_gaps"
    coverage.update({
        "by_question_type": by_type,
        "gold_readiness": (
            "fewer_than_50_evidence_anchored_candidates_in_this_run" if len(candidates) < 50
            else "candidate_volume_reaches_50_human_review_required"
        ),
        "error_code_candidate_count": sum("evidenced_error_codes" in item for item in candidates),
        "gap_interpretation": (
            "Shortfall measures run yield, not corpus capacity. Error-code coverage requires explicit "
            "text evidence. Other gaps can reflect source coverage, model yield or quality rejection."
        ),
    })
    quality = {
        "snapshot_id": snapshot_id, "status": status, "accepted": len(candidates),
        "by_question_type": by_type, "rejected": dict(rejected), "model_errors": dict(errors),
        "batch_attempts": attempts, "successful_batches": succeeded,
        "human_review_required": ["answer_relevance", "category_fit", "semantic_duplicates", "parse_quality"],
    }
    output = {
        "candidates.jsonl": b"".join(_json_bytes(item) + b"\n" for item in candidates),
        "candidate_quality_report.json": _json_bytes(quality) + b"\n",
        "coverage_gap_report.json": _json_bytes(coverage) + b"\n",
    }
    generation = {
        "schema_version": 1, "snapshot_id": snapshot_id, "scope": manifest["scope"],
        "snapshot_manifest_sha256": manifest["manifest_sha256"],
        "status": status, "candidate_count": len(candidates), "model": model if client else None,
        "model_digest": model_digest, "endpoint": client.endpoint if client else None,
        "options": options, "seed": seed, "prompt_version": PROMPT_VERSION,
        "prompt_sha256": _digest(_json_bytes([SYSTEM_PROMPT, _PROMPT, _TASKS])), "max_batches": max_batches,
        "source_sha256": source_hashes,
        "timeout_seconds": timeout if client else None, "max_chunk_prompt_chars": _TEXT_LIMIT,
        "outputs_sha256": {name: _digest(content) for name, content in output.items()},
    }
    # Publish the manifest last. A directory without it is an interrupted run.
    output["generation_manifest.json"] = _json_bytes(generation) + b"\n"
    for name, content in output.items():
        with (output_dir / name).open("xb") as file:
            file.write(content)
    return generation


def run_candidate_command(args) -> int:
    try:
        result = run_generation(
            args.snapshot_manifest, CorpusScope(args.collection, args.tenant_id, tuple(args.permission_tags)),
            args.output_dir, endpoint=args.endpoint, model=args.model, seed=args.seed,
            max_batches=args.max_batches, timeout=args.timeout_seconds, audit_only=args.audit_only,
        )
    except (CorpusExportError, ValueError, OSError):
        print("Candidate run refused. Check the verified snapshot, explicit scope, model configuration and new output directory.",
              file=sys.stderr)
        return 2
    print(json.dumps({key: result[key] for key in ("snapshot_id", "status", "candidate_count")}))
    return 2 if result["status"] in {"model_failed", "partial_model_failure"} else 0
