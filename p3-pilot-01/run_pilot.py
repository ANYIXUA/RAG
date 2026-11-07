#!/usr/bin/env python
"""P3-Pilot-01：22 条 Gold × 四组检索方式的探索性评估。

设计原则：

- 复用生产检索实现（``PostgresVectorStore.search`` + ``CrossEncoderReranker``），
  不复制、不改写打分逻辑；本脚本只负责加载 Gold、跑四组配置、按 Chunk ID 计分。
- 四组共用同一份冻结语料、同一次查询向量、同一套 TopK 与阈值参数。
- 所有产物都是真实检索结果，缺失能力（例如重排不可用）会显式记账，不补造。

用法::

    python -B p3-pilot-01/run_pilot.py --out-dir p3-pilot-01/runs/run1 --label run1
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import re
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)

OUTPUTS_DIR = (
    "storage/evaluation/outputs/01a1a5b7-cbe4-70e3-b1a7-cddfd5378f1f"
)
GOLD_SOURCES = {
    "batch01_jsonl": f"{OUTPUTS_DIR}/p2-gold-04/retrieval_gold_batch01_9.jsonl",
    "batch01_metadata": f"{OUTPUTS_DIR}/p2-gold-04/retrieval_gold_batch01_metadata.json",
    "batch01_manifest": f"{OUTPUTS_DIR}/p2-gold-04/gold_batch01_manifest.json",
    "batch02_jsonl": f"{OUTPUTS_DIR}/p2-gold-06/retrieval_gold_batch02_13.jsonl",
    "batch02_metadata": f"{OUTPUTS_DIR}/p2-gold-06/retrieval_gold_batch02_metadata.json",
    "batch02_manifest": f"{OUTPUTS_DIR}/p2-gold-06/gold_batch02_manifest.json",
}
CORPUS_JSONL = "storage/evaluation/corpus/p1-20261104-v2/corpus.jsonl"
CORPUS_MANIFEST = "storage/evaluation/corpus/p1-20261104-v2/corpus.manifest.json"

#: 评估集必须排除的批次：B23 未签核，B28–B42 属第三批候选，B24 已拒收。
EXCLUDED_BATCH_IDS = {"B23", "B24"} | {f"B{n}" for n in range(28, 43)}
#: 已签核 Gold 的批次白名单，用于反向校验合并结果。
EXPECTED_BATCH01 = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B09", "B12"]
EXPECTED_BATCH02 = [
    "B13", "B14", "B15", "B16", "B17", "B18", "B19",
    "B20", "B21", "B22", "B25", "B26", "B27",
]

K_VALUES = (1, 3, 5, 10)
#: 指标的最大截断深度；同时是检索返回深度的上限。
EVAL_MAX_K = 10
#: 四组共用：检索返回深度（C 组该深度即 D 组的重排候选池）。
RETRIEVAL_TOP_K = 20

METHODS = [
    {
        "key": "A",
        "name": "bm25_only",
        "mode": "bm25",
        "rerank": False,
        "supplementary": False,
        "description": "BM25 关键词检索（生产候选池）",
    },
    {
        "key": "B",
        "name": "vector_only",
        "mode": "semantic",
        "rerank": False,
        "supplementary": False,
        "description": "向量（余弦）检索",
    },
    {
        "key": "C",
        "name": "hybrid",
        "mode": "hybrid",
        "rerank": False,
        "supplementary": False,
        "description": "BM25 + 向量加权融合",
    },
    {
        "key": "D",
        "name": "hybrid_rerank",
        "mode": "hybrid",
        "rerank": True,
        "supplementary": False,
        "description": "混合检索 + Cross-Encoder 重排",
    },
    {
        "key": "A2",
        "name": "bm25_full_corpus",
        "mode": "bm25_full_corpus",
        "rerank": False,
        "supplementary": True,
        "description": (
            "诊断组（不计入四组对照）：绕过生产 keyword 候选池，"
            "在全部 447 个冻结 Chunk 上直接算同一套 BM25"
        ),
    },
]


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact_dsn(dsn: str) -> str:
    return re.sub(r":([^:@/]+)@", ":***@", dsn)


def load_env(path: Path) -> None:
    """加载 .env，但仅补齐缺失变量，不覆盖已显式设置的进程环境。"""

    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def with_local_dsn(dsn: str, host: str, port: int) -> str:
    """把容器网络主机名换成宿主机已发布端口，保留凭据与库名。"""

    return re.sub(r"@[^/@:]+:\d+/", f"@{host}:{port}/", dsn)


def dedupe_ids(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in ids:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


# --------------------------------------------------------------------------
# 预检：Gold 装载 + 冻结语料 + 向量库一致性
# --------------------------------------------------------------------------
def load_gold() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from rag_app.operations.evaluation import load_retrieval_eval_cases

    batch01 = load_retrieval_eval_cases(Path(GOLD_SOURCES["batch01_jsonl"]))
    batch02 = load_retrieval_eval_cases(Path(GOLD_SOURCES["batch02_jsonl"]))
    meta01 = json.loads(Path(GOLD_SOURCES["batch01_metadata"]).read_text(encoding="utf-8"))
    meta02 = json.loads(Path(GOLD_SOURCES["batch02_metadata"]).read_text(encoding="utf-8"))
    manifest02 = json.loads(
        Path(GOLD_SOURCES["batch02_manifest"]).read_text(encoding="utf-8")
    )
    meta_by_gold_id = {
        case["gold_case_id"]: case
        for case in [*meta01["cases"], *meta02["cases"]]
    }

    merged: list[dict[str, Any]] = []
    for batch_name, cases in (("batch01", batch01), ("batch02", batch02)):
        for case in cases:
            if case.note is None:
                raise ValueError(f"{batch_name} 存在没有 Gold ID（note）的样本：{case.query}")
            meta = meta_by_gold_id.get(case.note)
            if meta is None:
                raise ValueError(f"{batch_name} 的 Gold ID 在 metadata 中缺失：{case.note}")
            merged.append(
                {
                    "batch": batch_name,
                    "batch_id": meta["batch_id"],
                    "gold_case_id": case.note,
                    "query": case.query,
                    "expected": [
                        {
                            "source": target.source,
                            "section_title": target.section_title,
                            "text_contains": target.text_contains,
                        }
                        for target in case.expected
                    ],
                    "relevant_chunk_ids": dedupe_ids(
                        list(meta.get("retrieval_relevant_chunk_ids") or [])
                    ),
                    "evidence_chunk_ids": dedupe_ids(list(meta.get("evidence_chunk_ids") or [])),
                    "requires_all_evidence": bool(meta.get("requires_all_evidence")),
                    "question_type": meta.get("question_type"),
                    "review_decision": meta.get("review_decision"),
                }
            )

    provenance = {
        "sources": {
            key: {"path": rel, "sha256": sha256_file(Path(rel))}
            for key, rel in GOLD_SOURCES.items()
        },
        "batch01_cases": len(batch01),
        "batch02_cases": len(batch02),
        "merged_cases": len(merged),
        "batch01_manifest_gold_version": json.loads(
            Path(GOLD_SOURCES["batch01_manifest"]).read_text(encoding="utf-8")
        ).get("gold_version"),
        "batch02_manifest_gold_version": manifest02.get("gold_version"),
        "batch02_manifest_gold_file_sha256": manifest02.get("gold_file_sha256"),
    }
    return merged, provenance


def load_corpus() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    path = Path(CORPUS_JSONL)
    rows: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        rows[payload["chunk_id"]] = payload
    manifest = json.loads(Path(CORPUS_MANIFEST).read_text(encoding="utf-8"))
    info = {
        "path": CORPUS_JSONL,
        "sha256": sha256_file(path),
        "record_count": len(rows),
        "snapshot_id": manifest.get("snapshot_id"),
        "manifest_sha256_field": manifest.get("manifest_sha256"),
        "document_count": manifest.get("document_count"),
        "created_at": manifest.get("created_at"),
    }
    return rows, info


def verify_corpus_against_database(
    corpus: dict[str, dict[str, Any]],
    dsn: str,
) -> dict[str, Any]:
    """比对冻结语料与向量库中的 active Chunk：ID 集合与正文哈希必须完全一致。"""

    import psycopg

    with psycopg.connect(dsn, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT chunk_id, chunk_text FROM rag_knowledge_chunks "
                "WHERE collection_name = %s AND status = 'active'",
                ("default",),
            )
            db_rows = cursor.fetchall()

    db_text = {row[0]: row[1] for row in db_rows}
    corpus_ids = set(corpus)
    db_ids = set(db_text)
    mismatched = [
        chunk_id
        for chunk_id in corpus_ids & db_ids
        if sha256_text(corpus[chunk_id]["chunk_text"]) != sha256_text(db_text[chunk_id])
    ]
    result = {
        "database_active_chunks": len(db_ids),
        "corpus_chunks": len(corpus_ids),
        "id_sets_equal": corpus_ids == db_ids,
        "only_in_database": sorted(db_ids - corpus_ids)[:10],
        "only_in_corpus": sorted(corpus_ids - db_ids)[:10],
        "text_sha256_mismatches": mismatched[:10],
        "text_sha256_mismatch_count": len(mismatched),
        "consistent": corpus_ids == db_ids and not mismatched,
    }
    if not result["consistent"]:
        raise RuntimeError(
            "冻结语料与向量库 active Chunk 不一致，拒绝在不可信的语料上评测："
            + json.dumps(result, ensure_ascii=False)
        )
    return result


def check_gold_against_corpus(
    cases: list[dict[str, Any]],
    corpus: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    missing: list[dict[str, str]] = []
    empty_relevance: list[str] = []
    excluded_found: list[str] = []
    for case in cases:
        if not case["relevant_chunk_ids"]:
            empty_relevance.append(case["gold_case_id"])
        for chunk_id in case["relevant_chunk_ids"]:
            if chunk_id not in corpus:
                missing.append({"gold_case_id": case["gold_case_id"], "chunk_id": chunk_id})
        if case["batch_id"] in EXCLUDED_BATCH_IDS:
            excluded_found.append(case["batch_id"])

    batch_ids = [case["batch_id"] for case in cases]
    duplicates = sorted({item for item in batch_ids if batch_ids.count(item) > 1})
    queries = [case["query"] for case in cases]
    duplicate_queries = sorted({item for item in queries if queries.count(item) > 1})
    result = {
        "cases": len(cases),
        "questions_present": all(bool(case["query"].strip()) for case in cases),
        "expected_present": all(bool(case["expected"]) for case in cases),
        "relevant_ids_missing_from_corpus": missing,
        "cases_without_relevant_ids": empty_relevance,
        "excluded_batch_ids_present": sorted(set(excluded_found)),
        "duplicate_batch_ids": duplicates,
        "duplicate_queries": duplicate_queries,
        "batch_ids": batch_ids,
        "batch_ids_match_expected": (
            batch_ids[: len(EXPECTED_BATCH01)] == EXPECTED_BATCH01
            and batch_ids[len(EXPECTED_BATCH01):] == EXPECTED_BATCH02
        ),
        "relevant_chunk_ids_total": sum(len(case["relevant_chunk_ids"]) for case in cases),
        "requires_all_evidence_cases": sum(
            1 for case in cases if case["requires_all_evidence"]
        ),
    }
    problems = (
        missing
        or empty_relevance
        or excluded_found
        or duplicates
        or duplicate_queries
        or not result["batch_ids_match_expected"]
        or not result["questions_present"]
        or not result["expected_present"]
    )
    result["ok"] = not problems
    if problems:
        raise RuntimeError("Gold 预检失败：" + json.dumps(result, ensure_ascii=False))
    return result


# --------------------------------------------------------------------------
# 运行四组检索
# --------------------------------------------------------------------------
def build_settings():
    from rag_app.core.config import Settings

    load_env(REPO_ROOT / ".env")
    host = os.environ.get("RAG_PILOT_PG_HOST", "127.0.0.1")
    port = int(os.environ.get("RAG_PILOT_PG_PORT", "15432"))
    raw_dsn = os.environ.get("RAG_OPS_POSTGRES_DSN", "")
    if not raw_dsn:
        raise RuntimeError("缺少 RAG_OPS_POSTGRES_DSN，无法连接向量库。")
    local_dsn = with_local_dsn(raw_dsn, host, port)
    os.environ["RAG_OPS_POSTGRES_DSN"] = local_dsn
    settings = Settings.from_env(base_dir=REPO_ROOT)
    return settings, local_dsn


def hf_snapshot_revisions(model_id: str) -> list[str]:
    """从本地 HuggingFace 缓存读出该模型已落盘的 commit 快照号。"""

    safe = "models--" + model_id.replace("/", "--")
    snapshots = Path.home() / ".cache" / "huggingface" / "hub" / safe / "snapshots"
    if not snapshots.exists():
        return []
    return sorted(path.name for path in snapshots.iterdir() if path.is_dir())


def package_versions() -> dict[str, str]:
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for name in ("psycopg", "torch", "sentence_transformers", "transformers", "openai"):
        try:
            module = __import__(name)
            versions[name] = getattr(module, "__version__", "unknown")
        except Exception as exc:  # pragma: no cover - 记录不可用原因即可
            versions[name] = f"unavailable({type(exc).__name__})"
    return versions


def build_corpus_records(corpus: dict[str, dict[str, Any]]) -> list:
    """把冻结语料装成 VectorRecord（只用于 A2 诊断组的全库 BM25）。"""

    from rag_app.core.models import Chunk
    from rag_app.indexing.vector_store import VectorRecord

    records = []
    for chunk_id in sorted(corpus):
        row = corpus[chunk_id]
        metadata = dict(row.get("metadata") or {})
        metadata.setdefault("source", row.get("source"))
        records.append(
            VectorRecord(
                chunk=Chunk(
                    id=chunk_id,
                    document_id=row["document_id"],
                    text=row["chunk_text"],
                    metadata=metadata,
                ),
                embedding=[],
            )
        )
    return records


def bm25_full_corpus_search(
    records: list,
    query: str,
    settings,
    top_k: int,
) -> list[dict[str, Any]]:
    """A2 诊断：跳过生产 keyword 候选池，直接在 447 个 Chunk 上算同一套 BM25。

    复用生产模块的 ``_bm25_scores`` 与 ``_normalize_positive_scores``，
    并施加与四组相同的 ``min_similarity_score`` / ``relative_score_threshold``。
    """

    from rag_app.core.text_utils import tokenize_for_keyword_search
    from rag_app.indexing.vector_store import _bm25_scores, _normalize_positive_scores

    tokens = tokenize_for_keyword_search(query)
    scores = _bm25_scores(tokens, records)
    normalized = _normalize_positive_scores(scores)
    ranked = sorted(
        ((chunk_id, score) for chunk_id, score in normalized.items() if score > 0),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]
    if settings.min_similarity_score is not None:
        ranked = [item for item in ranked if item[1] > settings.min_similarity_score]
    if ranked and settings.relative_score_threshold:
        floor = ranked[0][1] * settings.relative_score_threshold
        ranked = [item for item in ranked if item[1] >= floor]

    record_by_id = {record.chunk.id: record for record in records}
    output: list[dict[str, Any]] = []
    for chunk_id, score in ranked:
        metadata = record_by_id[chunk_id].chunk.metadata or {}
        output.append(
            {
                "chunk_id": chunk_id,
                "score": round(float(score), 6),
                "semantic_score": None,
                "bm25_score": round(float(scores.get(chunk_id, 0.0)), 6),
                "normalized_bm25_score": round(float(score), 6),
                "rerank_score": None,
                "source": metadata.get("source"),
                "section_title": metadata.get("section_title"),
            }
        )
    return output


def search_once(
    store,
    settings,
    embedding: list[float],
    query: str,
    mode: str,
) -> list:
    return store.search(
        query_embedding=embedding,
        query_text=query,
        top_k=RETRIEVAL_TOP_K,
        min_score=settings.min_similarity_score,
        relative_score_threshold=settings.relative_score_threshold,
        mode=mode,
        semantic_weight=settings.semantic_weight,
        keyword_weight=settings.bm25_weight,
        bm25_weight=settings.bm25_weight,
        candidate_k=settings.retrieval_candidate_k,
        tenant_id=None,
        permission_tags=None,
    )


def result_to_record(result) -> dict[str, Any]:
    metadata = result.chunk.metadata or {}
    return {
        "chunk_id": result.chunk.id,
        "score": round(float(result.score), 6),
        "semantic_score": None
        if result.semantic_score is None
        else round(float(result.semantic_score), 6),
        "bm25_score": None
        if result.bm25_score is None
        else round(float(result.bm25_score), 6),
        "normalized_bm25_score": None
        if getattr(result, "normalized_bm25_score", None) is None
        else round(float(result.normalized_bm25_score), 6),
        "rerank_score": None
        if result.rerank_score is None
        else round(float(result.rerank_score), 6),
        "source": metadata.get("source"),
        "section_title": metadata.get("section_title"),
    }


def run(args: argparse.Namespace) -> int:
    from rag_app.indexing.embeddings import create_embedder
    from rag_app.indexing.vector_store import create_vector_store
    from rag_app.operations.retrieval_metrics import (
        coverage_at_k,
        first_relevant_rank,
        hit_at_k,
        ndcg_at_k,
        percentile,
        recall_at_k,
        reciprocal_rank_at_k,
    )

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    os.environ.setdefault("PYTHONHASHSEED", str(args.seed))

    settings, local_dsn = build_settings()

    started_at = utc_now()
    wall_start = time.perf_counter()

    cases, gold_provenance = load_gold()
    corpus, corpus_info = load_corpus()
    corpus_db_check = verify_corpus_against_database(corpus, local_dsn)
    gold_checks = check_gold_against_corpus(cases, corpus)

    embedder = create_embedder(settings)
    store = create_vector_store(settings)

    reranker = None
    rerank_status: dict[str, Any] = {
        "requested": not args.skip_rerank,
        "available": False,
        "reason": "not_attempted",
    }
    if not args.skip_rerank:
        try:
            from rag_app.retrieval.rerank import CrossEncoderReranker

            reranker = CrossEncoderReranker(settings.rerank_model)
            inner_config = getattr(getattr(reranker.model, "model", None), "config", None)
            rerank_status = {
                "requested": True,
                "available": True,
                "reason": None,
                "model_name": reranker.model_name,
                "resolved_model_name_or_path": getattr(
                    inner_config, "_name_or_path", None
                ),
                "hf_snapshot_revisions": hf_snapshot_revisions(settings.rerank_model),
            }
        except Exception as exc:
            rerank_status = {
                "requested": True,
                "available": False,
                "reason": f"{type(exc).__name__}: {exc}"[:500],
            }
    else:
        rerank_status = {"requested": False, "available": False, "reason": "skip_rerank"}

    # 查询向量只算一次，四组共用；向量化耗时单独记账，不计入检索耗时。
    query_vectors: dict[str, list[float]] = {}
    embedding_latency_ms: dict[str, float] = {}
    for case in cases:
        start = time.perf_counter()
        query_vectors[case["gold_case_id"]] = embedder.embed([case["query"]])[0]
        embedding_latency_ms[case["gold_case_id"]] = round(
            (time.perf_counter() - start) * 1000, 3
        )

    active_methods = [m for m in METHODS if not (m["rerank"] and reranker is None)]

    # 预热：避免把首次连接/首次推理的固定开销算进首条查询。
    warmup_query = "预热检索链路，不参与评测"
    warmup_vector = embedder.embed([warmup_query])[0]
    for method in active_methods:
        if method["mode"] == "bm25_full_corpus":
            continue
        results = search_once(store, settings, warmup_vector, warmup_query, method["mode"])
        if method["rerank"]:
            reranker.rerank(warmup_query, results, RETRIEVAL_TOP_K)

    corpus_records = build_corpus_records(corpus)

    ranking_records: list[dict[str, Any]] = []
    per_method_cases: dict[str, list[dict[str, Any]]] = {m["name"]: [] for m in active_methods}

    for case in cases:
        embedding = query_vectors[case["gold_case_id"]]
        relevant = set(case["relevant_chunk_ids"])
        required = set(case["evidence_chunk_ids"]) if case["requires_all_evidence"] else set()

        for method in active_methods:
            started = time.perf_counter()
            if method["mode"] == "bm25_full_corpus":
                records = bm25_full_corpus_search(
                    corpus_records, case["query"], settings, RETRIEVAL_TOP_K
                )
                search_ms = (time.perf_counter() - started) * 1000
                rerank_ms = 0.0
            else:
                results = search_once(
                    store, settings, embedding, case["query"], method["mode"]
                )
                search_ms = (time.perf_counter() - started) * 1000
                rerank_ms = 0.0
                if method["rerank"]:
                    started = time.perf_counter()
                    results = reranker.rerank(case["query"], results, RETRIEVAL_TOP_K)
                    rerank_ms = (time.perf_counter() - started) * 1000
                records = [result_to_record(item) for item in results]

            ranked_ids = [item["chunk_id"] for item in records]

            case_metrics = {
                "hit": {f"hit@{k}": hit_at_k(ranked_ids, relevant, k) for k in K_VALUES},
                "mrr_at_10": reciprocal_rank_at_k(ranked_ids, relevant, EVAL_MAX_K),
                "ndcg_at_10": ndcg_at_k(ranked_ids, relevant, EVAL_MAX_K),
                "recall_at_10": recall_at_k(ranked_ids, relevant, EVAL_MAX_K),
                "first_relevant_rank": first_relevant_rank(ranked_ids, relevant, EVAL_MAX_K),
                "retrieved_count": len(records),
                "no_result": len(records) == 0,
                "search_latency_ms": round(search_ms, 3),
                "rerank_latency_ms": round(rerank_ms, 3),
                "retrieval_latency_ms": round(search_ms + rerank_ms, 3),
            }
            if required:
                case_metrics["required_evidence_coverage_at_10"] = coverage_at_k(
                    ranked_ids, required, EVAL_MAX_K
                )

            ranking_records.append(
                {
                    "method": method["name"],
                    "method_key": method["key"],
                    "batch_id": case["batch_id"],
                    "gold_case_id": case["gold_case_id"],
                    "question_type": case["question_type"],
                    "requires_all_evidence": case["requires_all_evidence"],
                    "query": case["query"],
                    "mode": method["mode"],
                    "rerank_applied": method["rerank"],
                    "retrieval_top_k": RETRIEVAL_TOP_K,
                    "embedding_latency_ms": embedding_latency_ms[case["gold_case_id"]],
                    "relevant_chunk_ids": case["relevant_chunk_ids"],
                    **(
                        {"required_evidence_chunk_ids": case["evidence_chunk_ids"]}
                        if required
                        else {}
                    ),
                    "ranked_chunk_ids": ranked_ids,
                    "relevant_ranks": {
                        chunk_id: (ranked_ids.index(chunk_id) + 1)
                        for chunk_id in case["relevant_chunk_ids"]
                        if chunk_id in ranked_ids
                    },
                    "results": records,
                    "metrics": case_metrics,
                }
            )
            per_method_cases[method["name"]].append(case_metrics)

    # 汇总
    metrics: dict[str, Any] = {}
    supplementary_metrics: dict[str, Any] = {}
    for method in active_methods:
        rows = per_method_cases[method["name"]]
        latencies = [row["retrieval_latency_ms"] for row in rows]
        coverage_rows = [
            row["required_evidence_coverage_at_10"]
            for row in rows
            if "required_evidence_coverage_at_10" in row
        ]
        bucket = supplementary_metrics if method["supplementary"] else metrics
        bucket[method["name"]] = {
            "method_key": method["key"],
            "description": method["description"],
            "mode": method["mode"],
            "rerank_applied": method["rerank"],
            "supplementary": method["supplementary"],
            "case_count": len(rows),
            "hit@1": round(sum(row["hit"]["hit@1"] for row in rows) / len(rows), 6),
            "hit@3": round(sum(row["hit"]["hit@3"] for row in rows) / len(rows), 6),
            "hit@5": round(sum(row["hit"]["hit@5"] for row in rows) / len(rows), 6),
            "hit@10": round(sum(row["hit"]["hit@10"] for row in rows) / len(rows), 6),
            "mrr@10": round(sum(row["mrr_at_10"] for row in rows) / len(rows), 6),
            "ndcg@10": round(sum(row["ndcg_at_10"] for row in rows) / len(rows), 6),
            "recall@10": round(sum(row["recall_at_10"] for row in rows) / len(rows), 6),
            "no_result_rate": round(
                sum(1 for row in rows if row["no_result"]) / len(rows), 6
            ),
            "avg_retrieved": round(
                sum(row["retrieved_count"] for row in rows) / len(rows), 3
            ),
            "mrr@10_missing_truncated": "首个相关 Chunk 未进入 Top10 记 0",
            "latency_p50_ms": round(percentile(latencies, 0.5), 3),
            "latency_p95_ms": round(percentile(latencies, 0.95), 3),
            "latency_mean_ms": round(sum(latencies) / len(latencies), 3),
            "required_evidence_case_count": len(coverage_rows),
            "required_evidence_coverage@10": (
                None
                if not coverage_rows
                else round(sum(coverage_rows) / len(coverage_rows), 6)
            ),
        }

    # 差异：绝对变化 + 相对变化率（仅在基线 > 0 时给出）
    def delta(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for metric_name in (
            "hit@1", "hit@3", "hit@5", "hit@10",
            "mrr@10", "ndcg@10", "recall@10",
            "latency_p50_ms", "latency_p95_ms",
        ):
            diff = round(candidate[metric_name] - baseline[metric_name], 6)
            base = baseline[metric_name]
            out[metric_name] = {
                "absolute": diff,
                "relative_percent": None
                if base == 0
                else round(diff / base * 100, 3),
            }
        return out

    deltas: dict[str, Any] = {}
    for method in active_methods:
        if method["supplementary"] or method["name"] == "bm25_only":
            continue
        deltas[f"{method['name']}_vs_bm25_only"] = delta(
            metrics[method["name"]], metrics["bm25_only"]
        )
    if "hybrid_rerank" in metrics:
        deltas["hybrid_rerank_vs_hybrid"] = delta(
            metrics["hybrid_rerank"], metrics["hybrid"]
        )
    for method in active_methods:
        if method["supplementary"]:
            continue
        if method["name"] not in {"hybrid", "bm25_only"}:
            continue
        deltas[f"{method['name']}_vs_vector_only"] = delta(
            metrics[method["name"]], metrics["vector_only"]
        )
    for name, values in supplementary_metrics.items():
        deltas[f"{name}_vs_bm25_only"] = delta(values, metrics["bm25_only"])

    run_config = {
        "pilot": "P3-Pilot-01",
        "label": args.label,
        "started_at": started_at,
        "finished_at": utc_now(),
        "wall_seconds": round(time.perf_counter() - wall_start, 3),
        "evaluation_scope": "exploratory_22_gold_not_official_50_benchmark",
        "dataset": {
            "gold_cases": len(cases),
            "batches": ["batch01(9)", "batch02(13)"],
            **gold_provenance,
        },
        "corpus": corpus_info,
        "corpus_database_equivalence": corpus_db_check,
        "gold_checks": gold_checks,
        "retrieval": {
            "implementation": "rag_app.indexing.vector_store.PostgresVectorStore.search",
            "vector_store_provider": settings.vector_store_provider,
            "collection_name": settings.collection_name,
            "retrieval_top_k": RETRIEVAL_TOP_K,
            "retrieval_candidate_k": settings.retrieval_candidate_k,
            "evaluation_k_values": list(K_VALUES),
            "evaluation_max_k": EVAL_MAX_K,
            "truncation_rule": (
                "先按生产排序取前 retrieval_top_k 条，再按评估 K 截断；"
                "截断只丢尾部，不重排、不补位。"
            ),
            "fusion_algorithm": (
                "加权线性融合：score = semantic_weight/sum_weight * cosine + "
                "bm25_weight/sum_weight * max_normalized_bm25；非 RRF、非排名倒数融合。"
            ),
            "fusion_parameters": {
                "semantic_weight": settings.semantic_weight,
                "bm25_weight": settings.bm25_weight,
                "normalized_by": "bm25 / 本候选池内最大 bm25",
            },
            "candidate_pool": (
                "semantic top-N 与 keyword(ILIKE) top-N 的并集，N = retrieval_candidate_k"
            ),
            "bm25": {
                "k1": 1.5,
                "b": 0.75,
                "tokenizer": "rag_app.core.text_utils.tokenize_for_keyword_search"
                "（ASCII 词 + 中文二字组）",
            },
            "filters": {
                "min_similarity_score": settings.min_similarity_score,
                "relative_score_threshold": settings.relative_score_threshold,
                "applied_to": "四组完全相同",
            },
            "query_rewriting": (
                "未启用：四组都直接用 Gold 原句做 query 文本与查询向量，"
                "以隔离查询改写/意图路由的影响。"
            ),
            "tenant_id": None,
            "permission_tags": None,
        },
        "rerank": {
            "provider": "cross-encoder",
            "model": settings.rerank_model,
            "candidate_count": RETRIEVAL_TOP_K,
            "status": rerank_status,
        },
        "models": {
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.openai_embedding_model,
            "embedding_dimension": settings.embedding_dimension,
            "embedding_endpoint": settings.openai_base_url,
            "chat_model_unused": settings.openai_chat_model,
            "rerank_model": settings.rerank_model,
        },
        "environment": {
            "packages": package_versions(),
            "config_fingerprint": settings.config_fingerprint,
            "config_sources": list(settings.config_sources),
            "dsn_redacted": redact_dsn(local_dsn),
            "seed": args.seed,
            "randomness": (
                "检索排序为确定性打分（无采样）；重排为 CPU 前向推理，无 dropout；"
                "已固定 random.seed 与 PYTHONHASHSEED，结果不受随机性影响。"
            ),
        },
        "methods": [m for m in active_methods],
        "metrics_definitions": {
            "relevance": "二元：chunk_id ∈ retrieval_relevant_chunk_ids 即相关；多相关 Chunk 用集合语义。",
            "hit@k": "Top-k 内至少一个相关 Chunk 记为 1，按 22 题求均值。",
            "mrr@10": "首个相关 Chunk 名次的倒数；Top10 未命中记 0；按 22 题求均值。",
            "ndcg@10": "二元增益 DCG@10 / IDCG@10；IDCG 取 min(|相关集合|, 10) 个理想位置。",
            "recall@10": "Top10 覆盖的相关 Chunk 数 / 该题相关 Chunk 总数；按 22 题求均值。",
            "required_evidence_coverage@10": (
                "补充指标：requires_all_evidence 的题，Top10 覆盖 evidence_chunk_ids 的比例。"
            ),
            "latency": "单次检索调用耗时（含重排时为检索+重排）；p50/p95 用线性插值分位数。",
        },
    }

    # 写盘
    (out_dir / "run_config.json").write_text(
        json.dumps(run_config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    preflight = {
        "gold": gold_provenance,
        "gold_checks": gold_checks,
        "corpus": corpus_info,
        "corpus_database_equivalence": corpus_db_check,
        "rerank_status": rerank_status,
    }
    (out_dir / "preflight.json").write_text(
        json.dumps(preflight, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (out_dir / "rankings.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for record in ranking_records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    payload = {
        "pilot": "P3-Pilot-01",
        "label": args.label,
        "case_count": len(cases),
        "k_values": list(K_VALUES),
        "max_k": EVAL_MAX_K,
        "retrieval_top_k": RETRIEVAL_TOP_K,
        "metrics": metrics,
        "supplementary_metrics": supplementary_metrics,
        "deltas": deltas,
        "active_methods": [m["name"] for m in active_methods],
        "unavailable_methods": [
            {"name": m["name"], "reason": rerank_status.get("reason")}
            for m in METHODS
            if m not in active_methods
        ],
    }
    metrics_path = out_dir / "metrics.json"
    metrics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fingerprints = {
        "rankings_sha256": sha256_file(out_dir / "rankings.jsonl"),
        "metrics_sha256": sha256_file(metrics_path),
        "run_config_sha256": sha256_file(out_dir / "run_config.json"),
        "preflight_sha256": sha256_file(out_dir / "preflight.json"),
        "gold_sources_sha256": {
            key: sha256_file(Path(rel)) for key, rel in GOLD_SOURCES.items()
        },
        "corpus_sha256": corpus_info["sha256"],
    }
    (out_dir / "fingerprints.json").write_text(
        json.dumps(fingerprints, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(
        {
            "out_dir": str(out_dir),
            "cases": len(cases),
            "active_methods": [m["name"] for m in active_methods],
            "rerank": rerank_status,
            "metrics": metrics,
            "fingerprints": {
                "rankings_sha256": fingerprints["rankings_sha256"],
                "metrics_sha256": fingerprints["metrics_sha256"],
            },
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P3-Pilot-01 检索评估")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--label", default="run")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--skip-rerank", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(run(parse_args(sys.argv[1:])))
