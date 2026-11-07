"""P6-Silver-E2E-500 任务一：自动生成 500 条 Silver 测试问题。

- 语料：冻结快照 storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl（447 Chunk，SHA-256 先校验）。
- 出题模型：本地 Ollama qwen3:4b-instruct-2507-q4_K_M（loopback-only，零外发），复用
  rag_app/eval_dataset/ollama.py 的 LocalOllama 适配器与它的不可信输入防护。
- 校验：证据 excerpt 必须逐字来自对应 Chunk；answer 中数值/型号/异常码 token 必须在证据或
  Chunk 原文中出现；元叙述指代（“根据文档”）直接拒绝；无答案题做关键词-语料覆盖检查。
- 去重：候选之间、候选与 50 条正式 Gold 查询之间做归一化相似度阈值 0.80 去重。
- 断点续跑：原始候选逐批追加写入 generation_raw.jsonl；--build 确定性汇总为 silver_cases.jsonl。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
import unicodedata
from collections import Counter, deque
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT)]
from rag_app.eval_dataset.ollama import LocalOllama, ModelError  # noqa: E402

OUT = Path(__file__).parent
CORPUS_JSONL = ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl"

GOLD_SOURCES = [
    ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-04/retrieval_gold_batch01_9.jsonl",
    ROOT / "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f/p2-gold-06/retrieval_gold_batch02_13.jsonl",
    ROOT / "p4-gold-completion-01/signed-final-20261105-v1/retrieval_gold_holdout_28.jsonl",
]

MODEL_NAME = "qwen3:4b-instruct-2507-q4_K_M"
ENDPOINT = "http://127.0.0.1:11434"
PROMPT_VERSION = "p6-silver-generate-v1"
TARGETS = {
    "exact_fact": 200,
    "procedure": 100,
    "multi_condition": 100,
    "colloquial": 50,
    "unanswerable": 50,
}
_PER_BATCH_LIMIT = {"exact_fact": 3, "procedure": 3, "multi_condition": 3, "colloquial": 3}
UNANSWERABLE_PER_BATCH = 3

_TASKS = {
    "exact_fact": (
        "题型 exact_fact：提问一个能从单个段落中直接找到答案的具体事实，"
        "重点覆盖数值参数、指标门槛、设备或终端型号、异常或告警代码、时限、数量。"
        "问题里必须包含该事实的某个关键标识（如参数名、设备名、异常码等，且逐字出现在段落里）。"
    ),
    "procedure": (
        "题型 procedure：提问在给定条件下应如何操作、流程步骤、限制或规范要求。"
        "问题应点出条件（对象、场景、阶段），答案可由一个段落支持（该段落包含步骤或规则）。"
    ),
    "multi_condition": (
        "题型 multi_condition：问题必须同时涉及两个不同段落各自给出的条件，组合成一个复合业务场景。"
        "例如以段落A的条件为前提，询问段落B中的规则/数值/约束。"
        "evidence 须给两条、分别来自不同 passage；answer 需要综合两个段落的信息。"
    ),
    "colloquial": (
        "题型 colloquial：模拟一线工程师/用户随口描述现象、诉求或模糊说法，"
        "尽量不直接使用段落中的术语关键词（可用同义自然表达），指定一个仍能回答它的 passage。"
        "题面要自然口语化，但必须能被单个段落回答，answer 仍要有据。"
    ),
}

_PROMPT_ANSWERABLE = """仅依据给定 chunks 生成中文 RAG 评测问题。只做任务指定的题型，最多生成 count 条，证据不足就少写。
硬性要求：
1. 问题模拟真实用户/工程师口吻，自包含；禁止出现“文档”“原文”“本文”“该章节”“根据材料”等指代。
2. 禁止把完整答案写进问题；禁止编造 chunks 中不存在的实体、数值、型号、异常码或条件。
3. answer 必须完全由 evidence 支持且简短（不超过80字），不得引入 chunks 之外的信息。
4. evidence 每项含 passage_id 与 excerpt；excerpt 必须逐字按顺序复制上下文文本中的连续片段（12–300字），
   不要改写、不要省略中间任何字符。
5. 多个问题之间覆盖不同事实，不要把同一事实换种问法。
只返回 {"candidates":[...]}，每个元素含 question、question_type、answer、evidence。
"""

_PROMPT_UNANSWERABLE = """下面给出知识库真实涉及的业务主题词，以及若干明确超出该知识库范围的业务类别。
生成模拟真实用户提问的问题：听上去像合理的运维/装维/智慧家庭相关业务问题，但其答案不属于给定知识主题，
也不在任何运维文档范围内（例如跨品牌对比、价格促销、人事绩效、财务报销、用户账号隐私、
尚未发布的版本计划、非本项目产品线的参数等）。
用一个与主题相关的场景词增加迷惑性，但不要询问知识库覆盖的具体设备/流程细节本身。
只返回 {"candidates":[...]}，每个元素含 question、category（必须取自给定类别列表）、assumed_out_of_scope（一句简短理由，不超过40字）。
最多生成 count 条。
"""

_UNANSWERABLE_TOPICS = {
    "价格与促销": ["资费套餐", "促销活动", "设备收费", "合约价格", "积分兑换"],
    "人事与考核": ["绩效评分", "入职培训", "请假审批", "员工福利", "排班调动"],
    "财务与报销": ["差旅报销", "发票开具", "费用垫付", "税务凭证"],
    "其他产品线": ["路由器对比", "手机系统设置", "购物频道回看", "汽车充电桩安装"],
    "计划与市场": ["新版本发布时间", "行业招标信息", "友商市场份额", "展会日程"],
}


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", s).casefold() if not c.isspace())


def _one_line(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _load_corpus() -> list[dict]:
    corpus = CORPUS_JSONL.read_bytes()
    cfg = json.loads((ROOT / "p3-pilot-01/pilot_config.json").read_text(encoding="utf-8"))
    expected = cfg["frozen_inputs"]["corpus"]["sha256"]
    if _sha256_bytes(corpus) != expected:
        raise SystemExit("冻结语料哈希与 P3/P5 配置不一致，拒绝出题")
    rows = [json.loads(line) for line in corpus.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != 447:
        raise SystemExit(f"语料 Chunk 数量异常：{len(rows)}")
    return rows


def _load_prior_gold_queries() -> list[str]:
    queries: list[str] = []
    for path in GOLD_SOURCES:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("query"):
                    queries.append(row["query"])
    return queries


# ---------------------------------------------------------------- validation

_META_REFERENCE = re.compile(r"文档|原文|本文|该章节|根据材料|参考依据|知识库")


def _contains_verbatim(text: str, needle: str) -> bool:
    """宽松逐字包含：文本先做全量空白折叠后比较，保证跨换行的原文片段能命中。"""
    needle = _one_line(needle)
    if not needle:
        return False
    if needle in text:
        return True
    return needle in re.sub(r"\s+", " ", text)


def _data_tokens(text: str) -> list[str]:
    tokens = re.findall(
        r"[0-9]+(?:\.[0-9]+)?[A-Za-z%‰℃]*|[A-Za-z0-9][A-Za-z0-9_./-]*[A-Za-z0-9]",
        unicodedata.normalize("NFKC", text),
    )
    return [t for t in tokens if len(t) > 1 or t.isdigit()]


def _question_form_ok(question: str) -> bool:
    return re.search(r"[?？]|吗|什么|怎么|如何|哪|为什么|是否|多少|几|嘛|能不能|可以|需要|应该", question) is not None


def _validate_candidate(raw: dict, chunk_texts: dict[str, str], kind: str) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, "invalid_schema"
    question = str(raw.get("question") or "").strip()
    answer = str(raw.get("answer") or "").strip()
    evidence = [e for e in (raw.get("evidence") or []) if isinstance(e, dict)]
    question, answer = _one_line(question), _one_line(answer)
    nq, na = _norm(question), _norm(answer)
    if not 5 <= len(nq) <= 180 or len(question) > 260:
        return None, "bad_question_length"
    if _META_REFERENCE.search(question):
        return None, "meta_reference"
    if not _question_form_ok(question):
        return None, "not_a_question"
    if _META_REFERENCE.search(answer) or not 1 <= len(na) <= 240:
        return None, "bad_answer"
    excerpts: list[dict] = []
    chunk_ids: list[str] = []
    for item in evidence:
        cid = item.get("passage_id") or item.get("chunk_id")
        quote = str(item.get("excerpt") or "").strip()
        if not isinstance(cid, str) or cid not in chunk_texts:
            return None, "unknown_chunk"
        if not 12 <= len(_one_line(quote)) <= 320:
            return None, "bad_excerpt_length"
        if not _contains_verbatim(chunk_texts[cid], quote):
            return None, "excerpt_not_verbatim"
        excerpts.append({"chunk_id": cid, "excerpt": quote})
        if cid not in chunk_ids:
            chunk_ids.append(cid)
    if kind == "multi_condition" and len(chunk_ids) < 2:
        return None, "multi_condition_needs_two_chunks"
    if kind == "exact_fact" and not excerpts:
        return None, "missing_evidence"
    if kind == "multi_condition" and len(excerpts) < 2:
        return None, "multi_condition_needs_two_evidence"
    for e in excerpts:
        if _question_copies_excerpt(question, e["excerpt"]):
            return None, "question_copies_excerpt"
    if _question_copies_excerpt(question, answer):
        return None, "answer_in_question"
    if kind != "colloquial":
        for token in _data_tokens(answer):
            if any(token in e["excerpt"] or token in chunk_texts[e["chunk_id"]] for e in excerpts):
                continue
            return None, f"unsupported_answer_token:{token}"
        for token in _data_tokens(question):
            if any(token in chunk_texts[cid] for cid in chunk_ids):
                continue
            return None, f"unsupported_question_token:{token}"
    return {"question": question, "answer": answer, "excerpt": excerpts, "chunk_ids": chunk_ids}, None


def _validate_unanswerable(raw: dict, corpus_texts: list[str]) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, "invalid_schema"
    question = _one_line(str(raw.get("question") or ""))
    category = raw.get("category")
    reason = _one_line(str(raw.get("assumed_out_of_scope") or ""))
    if category not in _UNANSWERABLE_TOPICS:
        return None, "unknown_category"
    if not 6 <= len(_norm(question)) <= 180 or len(question) > 260:
        return None, "bad_question_length"
    if _META_REFERENCE.search(question):
        return None, "meta_reference"
    if not re.search(r"[?？]|吗|什么|怎么|如何|哪|是否|多少|可以|能不能|有没有|需要|应该|会", question):
        return None, "not_a_question"
    # 关键词覆盖检查：问题中的数字/型号 token 若大量出现在语料中，说明知识库可能覆盖该事实
    for token in _data_tokens(question):
        occurrences = sum(1 for t in corpus_texts if token in t)
        if occurrences >= 6 or occurrences > len(corpus_texts) * 0.02:
            return None, f"kb_token_overlap:{token}"
    return {"question": question, "reason": reason, "category": category}, None


# ---------------------------------------------------------------- batching


def build_packets(corpus: list[dict], rng: random.Random) -> deque[list[dict]]:
    by_doc: dict[str, list[dict]] = {}
    for row in corpus:
        by_doc.setdefault(row["source"], []).append(row)
    packets: list[list[dict]] = []
    for name in sorted(by_doc):
        doc_rows = sorted(by_doc[name], key=lambda r: (r.get("page_number") or 0, r["chunk_id"]))
        windows = [doc_rows[i:i + 3] for i in range(len(doc_rows))]
        rng.shuffle(windows)
        packets.extend(windows)
    rng.shuffle(packets)
    return deque(packets)


def _passage_block(packet: list[dict]) -> tuple[str, dict[str, str]]:
    lines: list[str] = []
    texts: dict[str, str] = {}
    for row in packet:
        cid = row["chunk_id"]
        body = _one_line(row["chunk_text"])
        if len(body) < 16:
            continue
        texts[cid] = body
        lines.append(
            f"passage_id:{cid} | 来源:{row['source']} | 页码:{row.get('page_number') or '未知'}\n{body}"
        )
    return "\n\n".join(lines), texts


_BASE_OPTIONS = {"temperature": 0.6, "top_p": 0.9, "num_ctx": 8192, "num_predict": 1800}

_EVIDENCE_ITEM = {
    "type": "object",
    "properties": {"passage_id": {"type": "string"}, "excerpt": {"type": "string"}},
    "required": ["passage_id", "excerpt"],
}


def _answerable_schema() -> dict:
    return {
        "type": "object",
        "properties": {"candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "question_type": {"type": "string"},
                    "answer": {"type": "string"},
                    "evidence": {"type": "array", "items": _EVIDENCE_ITEM},
                },
                "required": ["question", "question_type", "answer", "evidence"],
            },
        }},
        "required": ["candidates"],
    }


def _unanswerable_schema() -> dict:
    return {
        "type": "object",
        "properties": {"candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "question_type": {"type": "string"},
                    "category": {"type": "string"},
                    "assumed_out_of_scope": {"type": "string"},
                },
                "required": ["question", "category", "assumed_out_of_scope"],
            },
        }},
        "required": ["candidates"],
    }


def _schema_for(kind: str) -> dict:
    return _unanswerable_schema() if kind == "unanswerable" else _answerable_schema()


def _question_copies_excerpt(question: str, excerpt: str) -> bool:
    """问题若几乎照抄证据整句或把答案写进题面，直接拒绝。"""
    nq = _norm(question)
    if len(nq) < 8:
        return True
    for segment in re.split(r"[。；\n]", excerpt):
        ns = _norm(segment)
        if len(ns) >= 10 and ns in nq:
            return True
    return False


def run_generation(args) -> int:
    corpus = _load_corpus()
    corpus_texts = [row["chunk_text"] for row in corpus]
    raw_path = OUT / "generation_raw.jsonl"
    prior_items = []
    if raw_path.exists():
        prior_items = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()
                       if line.strip()]
    counts = Counter(item["question_type"] for item in prior_items)
    print(f"已缓存候选：{dict(counts)}，直接续跑。", flush=True)

    client = LocalOllama(ENDPOINT, MODEL_NAME, timeout=args.timeout)
    digest = client.local_digest()
    print("本地 Ollama 模型 digest:", digest, flush=True)

    rng = random.Random(args.seed)
    packets = build_packets(corpus, rng)
    topic_queue = deque(list(_UNANSWERABLE_TOPICS.keys()))
    errors: Counter = Counter()
    rejections: Counter = Counter()
    accepted_this_run = 0
    consecutive_errors = 0
    batch_id = 0
    started = time.time()

    raw_mode = "a" if raw_path.exists() else "w"
    debug_path = OUT / "generation_raw_debug.jsonl"
    debug_file = debug_path.open(raw_mode, encoding="utf-8")

    def _log_raw(batch_id: int, kind: str, items: object) -> None:
        debug_file.write(json.dumps({
            "batch": batch_id, "kind": kind, "candidates": items,
        }, ensure_ascii=False, sort_keys=True) + "\n")
        debug_file.flush()

    with raw_path.open(raw_mode, encoding="utf-8") as raw_file:
        while batches_remaining(counts) and batch_id < args.max_batches:
            remaining = {k: TARGETS[k] - counts[k] for k in TARGETS if counts[k] < TARGETS[k]}
            kind = max(remaining, key=lambda k: (remaining[k], rng.random()))
            batch_id += 1
            seed = args.seed + batch_id
            try:
                if kind == "unanswerable":
                    topic = topic_queue[0]
                    topic_queue.rotate(-1)
                    user_prompt = (
                        f"知识库真实业务主题词（仅可用于场景包装）：{topic}\n"
                        f"超出知识库范围的类别（category 必须逐一对应取自该列表）："
                        f"{'、'.join(_UNANSWERABLE_TOPICS)}\n"
                        f"count: {UNANSWERABLE_PER_BATCH if counts[kind] > 5 else 2}\n"
                        + _PROMPT_UNANSWERABLE
                    )
                    items = client.generate(
                        user_prompt, {**_BASE_OPTIONS, "seed": seed}, digest, schema=_schema_for(kind),
                    )
                    _log_raw(batch_id, kind, items)
                    if not isinstance(items, list):
                        raise ModelError("invalid_model_inference_output")
                    for raw in items:
                        item, reason = _validate_unanswerable(raw, corpus_texts)
                        if item is None:
                            rejections[reason] += 1
                            continue
                        record = {
                            "question_type": kind,
                            "question": item["question"],
                            "reference_answer": None,
                            "source_evidence": [],
                            "source_document": None,
                            "source_page": None,
                            "source_chunk_ids": [],
                            "out_of_scope_category": item["category"],
                            "assumed_out_of_scope_reason": item["reason"],
                            "generation_batch": batch_id,
                            "generation_seed": seed,
                            "generation_model": f"ollama/{MODEL_NAME}",
                            "generation_model_digest": digest,
                            "prompt_version": PROMPT_VERSION,
                        }
                        raw_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                        counts[kind] += 1
                        accepted_this_run += 1
                else:
                    packet = packets[0]
                    packets.rotate(-1)
                    passage_block, chunk_texts = _passage_block(packet)
                    if len(chunk_texts) < 3:
                        rejections["thin_packet"] += 1
                        continue
                    count = min(_PER_BATCH_LIMIT[kind], TARGETS[kind] - counts[kind])
                    user_prompt = (
                        f"任务：{_TASKS[kind]}\ncount: {count}\n\nchunks 如下：\n{passage_block}\n\n"
                        + _PROMPT_ANSWERABLE
                    )
                    items = client.generate(
                        user_prompt, {**_BASE_OPTIONS, "seed": seed}, digest, schema=_schema_for(kind),
                    )
                    _log_raw(batch_id, kind, items)
                    if not isinstance(items, list):
                        raise ModelError("invalid_model_inference_output")
                    for raw in items:
                        if isinstance(raw, dict):
                            raw["question_type"] = kind
                        item, reason = _validate_candidate(raw, chunk_texts, kind)
                        if item is None:
                            rejections[reason] += 1
                            continue
                        record = {
                            "question_type": kind,
                            "question": item["question"],
                            "reference_answer": item["answer"],
                            "source_evidence": item["excerpt"],
                            "source_document": sorted({corpus_index(corpus, cid)["source"] for cid in item["chunk_ids"]}),
                            "source_page": max(
                                (corpus_index(corpus, cid).get("page_number") for cid in item["chunk_ids"]
                                 if corpus_index(corpus, cid).get("page_number") is not None),
                                default=None,
                            ),
                            "source_chunk_ids": item["chunk_ids"],
                            "generation_batch": batch_id,
                            "generation_seed": seed,
                            "generation_model": f"ollama/{MODEL_NAME}",
                            "generation_model_digest": digest,
                            "prompt_version": PROMPT_VERSION,
                        }
                        raw_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                        counts[kind] += 1
                        accepted_this_run += 1
                raw_file.flush()
                consecutive_errors = 0
            except ModelError as exc:
                errors[str(exc)] += 1
                consecutive_errors += 1
                print(f"[batch {batch_id}] MODEL ERROR {exc}", flush=True)
            except Exception as exc:  # noqa: BLE001
                errors[f"unexpected:{type(exc).__name__}"] += 1
                consecutive_errors += 1
                print(f"[batch {batch_id}] ERROR {exc!r}", flush=True)
            if consecutive_errors >= 5:
                print("连续错误过多，提前停止出题。", flush=True)
                break

            if batch_id % 5 == 0 or batch_id == 1:
                print(f"[batch {batch_id}] counts={dict(counts)} accepted={accepted_this_run} "
                      f"elapsed={time.time() - started:.0f}s "
                      f"rejections={dict(rejections)} errors={dict(errors)}", flush=True)

    summary = {
        "model": f"ollama/{MODEL_NAME}",
        "model_digest": digest,
        "prompt_version": PROMPT_VERSION,
        "seed": args.seed,
        "batches_this_run": batch_id,
        "accepted_this_run": accepted_this_run,
        "counts": dict(counts),
        "remaining": {k: max(0, TARGETS[k] - counts.get(k, 0)) for k in TARGETS},
        "model_errors": dict(errors),
        "rejections": dict(rejections),
        "elapsed_seconds": round(time.time() - started, 1),
        "targets_complete": not batches_remaining(counts),
        "raw_path_sha256": _sha256_bytes(raw_path.read_bytes()) if raw_path.exists() else None,
    }
    (OUT / "generation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1), flush=True)
    return 0 if summary["targets_complete"] else 3


_CORPUS_INDEX: dict[str, dict] | None = None


def corpus_index(corpus: list[dict], cid: str) -> dict:
    global _CORPUS_INDEX
    if _CORPUS_INDEX is None:
        _CORPUS_INDEX = {row["chunk_id"]: row for row in corpus}
    return _CORPUS_INDEX[cid]


def batches_remaining(counts: Counter) -> bool:
    return any(counts[k] < TARGETS[k] for k in TARGETS)


# ---------------------------------------------------------------- build


def build_silver(args) -> int:
    raw_path = OUT / "generation_raw.jsonl"
    raw = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    gold_norm = [_norm(q) for q in _load_prior_gold_queries() if len(_norm(q)) > 6]

    accepted: list[dict] = []
    used_norm: list[str] = list(gold_norm)
    pairs_used: list[tuple[tuple[str, ...], tuple[str, str]]] = []
    counts: Counter = Counter()
    duplicates_rejected = 0
    for row in raw:
        if all(counts[k] >= TARGETS[k] for k in TARGETS):
            break
        kind = row["question_type"]
        if counts[kind] >= TARGETS[kind]:
            continue
        nq = _norm(row["question"])
        if any(SequenceMatcher(None, nq, other, autojunk=False).ratio() >= 0.80 for other in used_norm):
            duplicates_rejected += 1
            continue
        if kind != "unanswerable":
            chunk_key = tuple(sorted(row.get("source_chunk_ids") or []))
            na = _norm(row["reference_answer"])
            if any(
                pair == chunk_key
                and other[0][:80] == na[:80]
                and SequenceMatcher(None, nq, other[1], autojunk=False).ratio() >= 0.6
                for pair, other in pairs_used
            ):
                duplicates_rejected += 1
                continue
            pairs_used.append((chunk_key, (na, nq)))
        counts[kind] += 1
        used_norm.append(nq)
        base = {
            "case_id": f"p6s-{len(accepted) + 1:04d}",
            "question": row["question"],
            "question_type": kind,
            "source_document": row.get("source_document"),
            "source_page": row.get("source_page"),
            "source_chunk_ids": row.get("source_chunk_ids", []),
            "label_type": "silver",
            "generation_model": row.get("generation_model"),
            "generation_version": row.get("generation_model_digest"),
            "generation_seed": row.get("generation_seed"),
            "generation_batch": row.get("generation_batch"),
            "prompt_version": PROMPT_VERSION,
        }
        if kind == "unanswerable":
            base.update({
                "reference_answer": None,
                "source_evidence": [],
                "expected_behavior": "refuse_or_qualify",
                "out_of_scope_category": row.get("out_of_scope_category"),
                "assumed_out_of_scope_reason": row.get("assumed_out_of_scope_reason"),
            })
        else:
            base.update({
                "reference_answer": row["reference_answer"],
                "source_evidence": row.get("source_evidence", []),
                "expected_behavior": "answer",
            })
        accepted.append(base)

    with (OUT / "silver_cases.jsonl").open("w", encoding="utf-8") as f:
        for record in accepted:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {
        "label_type": "silver",
        "prompt_version": PROMPT_VERSION,
        "model": f"ollama/{MODEL_NAME}",
        "seed": args.seed,
        "accepted": len(accepted),
        "by_type": dict(counts),
        "targets": TARGETS,
        "shortfall": {k: max(0, TARGETS[k] - counts.get(k, 0)) for k in TARGETS},
        "duplicates_rejected": duplicates_rejected,
        "gold_prior_query_count": len(gold_norm),
        "raw_available_by_type": dict(Counter(row["question_type"] for row in raw)),
        "inputs": {
            "corpus_sha256": _sha256_bytes(CORPUS_JSONL.read_bytes()),
            "generation_raw_sha256": _sha256_bytes(raw_path.read_bytes()) if raw_path.exists() else None,
            "gold_sources_sha256": [
                {"path": str(p.relative_to(ROOT)), "sha256": _sha256_bytes(p.read_bytes())}
                for p in GOLD_SOURCES
            ],
        },
    }
    (OUT / "silver_build_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    printable = {k: v for k, v in summary.items() if k != "inputs"}
    print(json.dumps(printable, ensure_ascii=False, indent=1), flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true", help="用本地 Ollama 继续生成候选")
    ap.add_argument("--build", action="store_true", help="从 generation_raw.jsonl 构建 silver_cases.jsonl")
    ap.add_argument("--seed", type=int, default=20261106)
    ap.add_argument("--max-batches", type=int, default=700)
    ap.add_argument("--timeout", type=float, default=240.0)
    a = ap.parse_args()
    if not a.generate and not a.build:
        ap.error("选择 --generate 或 --build")
    if a.generate:
        return run_generation(a)
    return build_silver(a)


if __name__ == "__main__":
    raise SystemExit(main())
