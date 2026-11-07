"""P6-Silver-E2E-500 任务四：对 results.jsonl 做探索性自动评分（Silver 指标）。

评分组成：
1. 规则校验（本地）：
   - answer_hallucinated_numbers：答案中的数值/型号 token 是否出现在被检索上下文。
   - citation_check：答案中 [n] 引用标记是否都能映射到本轮实际提供的来源列表。
   - refusal_markers：无答案题是否出现"无法/没有相关/知识库中不明确/转人工"等合理说明。
2. LLM-as-Judge（远端，qwen-plus，与生成模型 qwen-turbo 不同模型；通过 DashScope 兼容接口）：
   - answer_correctness / faithfulness / completeness / citation_correctness（可回答题）
   - refusal_appropriateness（无答案题）
   - confidence（high/medium/low）、 reasons、needs_human_review。

所有分数均为 Silver 探索性指标，不作 Gold 级别声称。
断点续跑：silver_scores.jsonl 已评分 case_id 自动跳过。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT)]

OUT = Path(__file__).parent
RESULTS = OUT / "results.jsonl"
CASES = OUT / "silver_cases.jsonl"
SCORES = OUT / "silver_scores.jsonl"

JUDGE_MODEL = "qwen-plus"
SCORE_VERSION = "p6-silver-score-v1"
_RULE_TOKEN = re.compile(r"[0-9]+(?:\.[0-9]+)?[A-Za-z%‰℃]*|[A-Za-z]{2,}[A-Za-z0-9]*")
_REFUSAL_MARKERS = [
    "无法", "没有相关", "不明确", "知识库", "暂无", "未提供", "未找到", "转人工",
    "不足以", "超出范围", "无法确认", "建议咨询", "人工核实", "没有找到",
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _rule_checks(result: dict, context_texts: list[str]) -> dict:
    answer = (result["generation"] or {}).get("answer") or ""
    rule: dict = {}
    tokens = sorted({t for t in _RULE_TOKEN.findall(answer) if len(t) > 1 or t.isdigit()})
    missing = [
        t for t in tokens
        if not any(t in ctx for ctx in context_texts)
    ]
    rule["answer_tokens_without_context"] = missing[:10]

    citations = sorted(set(re.findall(r"\[(\d{1,2})\]", answer)))
    n_sources = len((result["retrieval"] or {}).get("candidates") or [])
    rule["citations_found"] = [int(c) for c in citations]
    rule["citation_index_valid"] = (
        all(1 <= int(c) <= n_sources for c in citations) if citations else None
    )
    rule["has_citation"] = bool(citations)
    expected = result.get("expected_behavior")
    if expected == "refuse_or_qualify":
        rule["refusal_markers_present"] = any(m in answer for m in _REFUSAL_MARKERS)
    return rule


def _judge_prompt(case_type: str, question: str, reference: str | None, evidence: list[dict],
                  answer: str, cited_context: list[dict], expected: str) -> list[dict]:
    import re as _re

    def trim(t: str, n: int) -> str:
        return _re.sub(r"\s+", " ", t or "")[:n]

    evidence_block = "\n".join(
        f"- [{e['chunk_id'][:12]}] {trim(e['excerpt'], 320)}" for e in (evidence or [])[:4]
    ) or "（无参考证据）"
    context_block = "\n".join(
        f"- [来源{i}] {trim(c.get('metadata'), 120)} | 正文片段：{trim(c.get('text'), 360)}"
        for i, c in enumerate(cited_context[:5], 1)
    ) or "（无检索来源）"
    system = "你是严格的 RAG 问答评测评审。只依据给定信息判断，绝不编造。输出 JSON。"
    if case_type == "unanswerable" or expected == "refuse_or_qualify":
        user = f"""知识库范围外的无答案测试题评审。
用户问题：{question}
参考证据：知识库应不包含该问题答案（出题标注理由：{reference or ''}）
系统回答：{answer}

评分项（0/0.5/1）：
- refusal_appropriateness：回答是否合理地说明无法提供该信息/证据不足（1=清晰拒答或限定说明；0.5=承认不确定但补充了部分内容；0=编造了具体事实或给出与知识库无关的"答案"）。
- hallucination_risk：若回答中出现了具体可验证的事实性断言却无证据支持，此项得1，否则0。
输出 JSON：{{"refusal_appropriateness":x,"hallucination_risk":0或1,"confidence":"high|medium|low","reason":"不超过60字","key_evidence":"支撑或反对句"}}"""
    else:
        user = f"""RAG 问答质量评审。
参考问题：{question}
参考标准答案（Silver 级，可能有遗漏）：{(reference or "")[:400]}
参考证据摘录：{evidence_block}
系统回答：{answer}
实际进入上下文的检索来源：{context_block}

评分项（0/0.5/1）：
- answer_correctness：与参考答案一致；重点核查数值、设备型号、单位、条件是否错误。完全一致=1；数值/型号/单位/主要条件错误=0；方向正确但细节缺失=0.5。
- faithfulness：回答是否被检索来源支持；出现来源不支持的具体事实=0，有关键支持=1。
- completeness：是否完整回答了问题的全部要点（多条件/多步骤问题更要看遗漏）。
- citation_correctness：评分标准：(a) 引用标记 [n] 与来源编号对应 (b) 来源内容确实支持该结论 (c) 无"看似有引用实则无证据"的句子。
输出 JSON：{{"answer_correctness":x,"faithfulness":x,"completeness":x,"citation_correctness":x,"confidence":"high|medium|low","reason":"不超过80字","key_evidence":"支撑或反对句","flags":["数值错误","设备型号错误","单位/规格错误","条件错误","答案不完整","无证据编造","引用不实","引用缺失"]}}"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _context_items(result: dict, limit: int = 5) -> list[dict]:
    cands = (result["retrieval"] or {}).get("candidates") or []
    items: list[dict] = []
    for c in cands[:limit]:
        row = CORPUS_CACHE.get(c["chunk_id"], {})
        items.append({
            "chunk_id": c["chunk_id"],
            "metadata": f"来源{c.get('source')} 页{c.get('page_number')} | {c.get('title') or ''}",
            "score": c.get("score"),
            "text": (row.get("chunk_text") or "")[:400],
        })
    return items


def _rank_chunk_texts(result: dict) -> list[str]:
    # 规则校验使用的上下文来自结果中记录的候选（chunk id），正文用于 token 存在性检查需查语料
    chunk_ids = [c["chunk_id"] for c in (result["retrieval"] or {}).get("candidates") or []]
    texts: list[str] = []
    if chunk_ids and CORPUS_CACHE:
        for cid in chunk_ids:
            texts.append(CORPUS_CACHE.get(cid, {}).get("chunk_text", ""))
    return texts + [
        str(c.get("metadata", "")) for c in _context_items(result)
    ]


CORPUS_CACHE: dict[str, dict] = {}
CORPUS_SHA256 = None


def _load_corpus() -> tuple[dict[str, dict], str]:
    corpus_path = ROOT / "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl"
    raw = corpus_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()  # noqa: F821
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    return {row["chunk_id"]: row for row in rows}, digest


import hashlib  # noqa: E402


class Judge:
    def __init__(self, model: str = JUDGE_MODEL) -> None:
        from openai import OpenAI
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY") or os.environ.get("DASHSCOPE_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            timeout=30.0,
        )
        self.model = model
        self.usage_tokens = 0

    def judge(self, messages: list[dict]) -> dict:
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=0.0,
            response_format={"type": "json_object"},
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            self.usage_tokens += (getattr(usage, "prompt_tokens", 0) or 0) + (getattr(usage, "completion_tokens", 0) or 0)
        content = response.choices[0].message.content or "{}"
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, re.S)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return {"parse_failure": content[:200]}


def _score_row(row: dict, judge: Judge) -> dict:
    base = {
        "case_id": row["case_id"],
        "label_type": row.get("label_type", "silver"),
        "score_version": SCORE_VERSION,
        "run_state": row["run_state"],
    }
    if row["run_state"] != "success":
        base.update({
            "applicable": False,
            "answer_correctness": None, "faithfulness": None, "completeness": None,
            "citation_correctness": None, "refusal_appropriateness": None,
            "confidence": None, "reason": "run_failed", "needs_human_review": False,
            "failure_bucket": "model_call_or_execution_failure",
        })
        return base
    answer = (row["generation"] or {}).get("answer") or ""
    evidence = row.get("reference_evidence") or []
    rule = _rule_checks(row, _rank_chunk_texts(row))
    base["rule_checks"] = rule
    try:
        messages = _judge_prompt(
            row["question_type"], row["question"], row.get("reference_answer"),
            evidence, answer, _context_items(row), row.get("expected_behavior") or "answer",
        )
        judged = judge.judge(messages)
    except Exception as exc:  # noqa: BLE001
        base.update({
            "applicable": False, "score_effective": False,
            "answer_correctness": None, "faithfulness": None, "completeness": None,
            "citation_correctness": None, "refusal_appropriateness": None,
            "confidence": None, "reason": f"judge_error:{type(exc).__name__}",
            "needs_human_review": True, "failure_bucket": "judge_uncertain",
        })
        return base
    base["applicable"] = True
    base["judge_raw"] = judged
    numeric_fields = {}
    for field in ("answer_correctness", "faithfulness", "completeness",
                  "citation_correctness", "refusal_appropriateness", "hallucination_risk"):
        value = judged.get(field)
        if isinstance(value, (int, float)) and 0 <= float(value) <= 1.2:
            numeric_fields[field] = round(min(float(value), 1.0), 2)
    base.update(numeric_fields)
    base["confidence"] = judged.get("confidence")
    base["reason"] = judged.get("reason")
    base["key_evidence"] = judged.get("key_evidence")
    base["flags"] = judged.get("flags") or []
    low_conf = base.get("confidence") == "low" or "parse_failure" in judged
    uncertain = any(base.get(f) is None for f in numeric_fields if f in _expected_fields(row))
    base["needs_human_review"] = bool(low_conf or uncertain)
    base["failure_bucket"] = _failure_bucket(base, row, rule)
    return base


def _expected_fields(row: dict) -> list[str]:
    if row.get("question_type") == "unanswerable" or row.get("expected_behavior") == "refuse_or_qualify":
        return ["refusal_appropriateness"]
    return ["answer_correctness", "faithfulness", "completeness", "citation_correctness"]


def _failure_bucket(score: dict, row: dict, rule: dict) -> str:
    if not score.get("applicable"):
        return "judge_uncertain"
    if row.get("expected_behavior") == "refuse_or_qualify":
        if score.get("refusal_appropriateness", 0) < 0.5:
            return "no_evidence_hallucination"
        return "none_or_pass"
    answer_correctness = score.get("answer_correctness")
    faithfulness = score.get("faithfulness")
    completeness = score.get("completeness")
    citation = score.get("citation_correctness")
    if faithfulness is not None and faithfulness <= 0.5 and (answer_correctness or 0) < 0.5:
        return "no_evidence_hallucination"
    if citation is not None and citation < 0.5:
        return "citation_error"
    if rule.get("citations_found") and rule.get("citation_index_valid") is False:
        return "citation_error"
    if completeness is not None and completeness < 0.5 and (answer_correctness or 0) >= 0.5:
        return "answer_incomplete"
    if rule.get("answer_tokens_without_context") and (answer_correctness or 0) >= 0.5:
        return "retrieval_hit_but_context_miss"
    if answer_correctness == 0:
        if rule.get("answer_tokens_without_context"):
            return "no_evidence_hallucination"
        return "answer_wrong_with_evidence"
    return "none_or_pass"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=4)
    args = ap.parse_args()

    global CORPUS_CACHE
    _prepare_env()
    CORPUS_CACHE, digest = _load_corpus()

    results = [json.loads(l) for l in RESULTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    case_meta: dict[str, dict] = {}
    if CASES.exists():
        for line in CASES.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                case_meta[c["case_id"]] = c
    for row in results:
        meta = case_meta.get(row["case_id"], {})
        row.setdefault("expected_behavior", meta.get("expected_behavior"))
        row.setdefault("source_evidence", meta.get("source_evidence", []))
        row.setdefault("source_chunk_ids", meta.get("source_chunk_ids", []))
        row.setdefault("reference_answer", meta.get("reference_answer"))
        if row.get("expected_behavior") == "refuse_or_qualify":
            row["reference_answer"] = (
                meta.get("assumed_out_of_scope_reason") or "出题标注：超出知识库范围"
            )
    done: set[str] = set()
    if SCORES.exists():
        done = {json.loads(l)["case_id"] for l in SCORES.read_text(encoding="utf-8").splitlines() if l.strip()}
    todo = [r for r in results if r["case_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"待评分 {len(todo)} / 已评分 {len(done)}", flush=True)

    judge = Judge()
    lock = Lock()
    started = time.time()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(_score_row, row, judge): row["case_id"] for row in todo}
        n = 0
        for future in as_completed(futures):
            score = future.result()
            with lock, SCORES.open("a", encoding="utf-8") as f:
                f.write(json.dumps(score, ensure_ascii=False) + "\n")
            n += 1
            if n % 50 == 0:
                print(f"scored {n}/{len(todo)} elapsed={time.time() - started:.0f}s "
                      f"tokens~{judge.usage_tokens}", flush=True)
    print(f"评分完成 {n} 条，judge tokens≈{judge.usage_tokens}（用于成本估算）", flush=True)
    return 0


def _prepare_env() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


if __name__ == "__main__":
    raise SystemExit(main())
