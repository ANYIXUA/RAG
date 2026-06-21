"""向量存储和混合检索实现。"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Protocol

from rag_app.core.error_codes import normalize_error_code
from rag_app.core.config import Settings
from rag_app.core.models import Chunk, RetrievalResult
from rag_app.core.text_utils import tokenize_for_keyword_search


BM25_K1 = 1.5
BM25_B = 0.75


@dataclass(frozen=True)
class VectorRecord:
    chunk: Chunk
    embedding: list[float]


@dataclass(frozen=True)
class _RecordScore:
    record: VectorRecord
    semantic_score: float
    bm25_score: float
    normalized_bm25_score: float


class VectorStore(Protocol):
    """向量存储接口，隔离在线检索编排和生产存储实现。"""

    def count(self) -> int:
        ...

    def reload(self) -> None:
        ...

    def clear(self) -> None:
        ...

    def upsert(self, records: list[VectorRecord]) -> int:
        ...

    def delete_by_document_ids(self, document_ids: set[str]) -> int:
        ...

    def search(
        self,
        query_embedding: list[float],
        query_text: str | None = None,
        top_k: int = 4,
        min_score: float | None = None,
        relative_score_threshold: float | None = None,
        mode: str = "hybrid",
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        bm25_weight: float | None = None,
        candidate_k: int | None = None,
        tenant_id: str | None = None,
        permission_tags: tuple[str, ...] | list[str] | None = None,
    ) -> list[RetrievalResult]:
        ...

    def search_by_error_code(
        self,
        error_code: str,
        top_k: int = 4,
        tenant_id: str | None = None,
        permission_tags: tuple[str, ...] | list[str] | None = None,
    ) -> list[RetrievalResult]:
        ...


class PostgresVectorStore:
    """使用 PostgreSQL + pgvector 保存并检索知识切片。"""

    def __init__(self, dsn: str, collection_name: str, dimension: int) -> None:
        self.dsn = dsn
        self.collection_name = collection_name
        self.dimension = dimension
        self._ensure_schema()

    def count(self) -> int:
        psycopg, dict_row, _ = _import_psycopg()
        del dict_row
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM rag_knowledge_chunks
                    WHERE collection_name = %s AND status = 'active'
                    """,
                    (self.collection_name,),
                )
                row = cursor.fetchone()
        return int(row[0] if row else 0)

    def reload(self) -> None:
        """PostgreSQL 查询每次都读取服务端最新数据。"""

    def clear(self) -> None:
        psycopg, _, _ = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM rag_knowledge_chunks WHERE collection_name = %s",
                    (self.collection_name,),
                )
                cursor.execute(
                    "DELETE FROM rag_documents WHERE collection_name = %s",
                    (self.collection_name,),
                )

    def upsert(self, records: list[VectorRecord]) -> int:
        if not records:
            return self.count()
        psycopg, _, jsonb = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                for record in records:
                    self._upsert_document(cursor, jsonb, record)
                    self._upsert_chunk(cursor, jsonb, record)
        return self.count()

    def delete_by_document_ids(self, document_ids: set[str]) -> int:
        if not document_ids:
            return 0
        psycopg, _, _ = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM rag_knowledge_chunks
                    WHERE collection_name = %s AND document_id = ANY(%s)
                    """,
                    (self.collection_name, list(document_ids)),
                )
                deleted = cursor.rowcount
                cursor.execute(
                    """
                    DELETE FROM rag_documents
                    WHERE collection_name = %s AND document_id = ANY(%s)
                    """,
                    (self.collection_name, list(document_ids)),
                )
        return max(int(deleted or 0), 0)

    def search(
        self,
        query_embedding: list[float],
        query_text: str | None = None,
        top_k: int = 4,
        min_score: float | None = None,
        relative_score_threshold: float | None = None,
        mode: str = "hybrid",
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        bm25_weight: float | None = None,
        candidate_k: int | None = None,
        tenant_id: str | None = None,
        permission_tags: tuple[str, ...] | list[str] | None = None,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            return []
        record_count = self.count()
        if record_count <= 0:
            return []

        actual_candidate_k = _candidate_limit(
            candidate_k=candidate_k,
            top_k=top_k,
            record_count=record_count,
        )
        normalized_mode = _normalize_mode(mode)
        semantic_scores: dict[str, float] | None = None
        records: list[VectorRecord] = []

        if normalized_mode != "bm25":
            records, semantic_scores = self._search_semantic_candidates(
                query_embedding=query_embedding,
                limit=actual_candidate_k,
            )
        if normalized_mode != "semantic":
            records = _merge_records(
                records,
                self._query_keyword_candidates(
                    query_text=query_text or "",
                    limit=actual_candidate_k,
                ),
            )
        if not records:
            return []

        return _rank_vector_records(
            records=records,
            query_embedding=query_embedding,
            query_text=query_text,
            top_k=top_k,
            min_score=min_score,
            relative_score_threshold=relative_score_threshold,
            mode=mode,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            bm25_weight=bm25_weight,
            candidate_k=actual_candidate_k,
            semantic_scores=semantic_scores,
            tenant_id=tenant_id,
            permission_tags=permission_tags,
        )

    def search_by_error_code(
        self,
        error_code: str,
        top_k: int = 4,
        tenant_id: str | None = None,
        permission_tags: tuple[str, ...] | list[str] | None = None,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            return []
        normalized_code = normalize_error_code(error_code)
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        chunk_id, document_id, chunk_text, metadata,
                        embedding::text AS embedding_text
                    FROM rag_knowledge_chunks
                    WHERE collection_name = %s
                      AND status = 'active'
                      AND (
                          UPPER(error_code) = %s
                          OR metadata->'error_codes' ? %s
                      )
                    ORDER BY priority DESC, updated_at DESC
                    LIMIT %s
                    """,
                    (
                        self.collection_name,
                        normalized_code,
                        normalized_code,
                        max(top_k * 5, top_k),
                    ),
                )
                rows = cursor.fetchall()
        return _search_records_by_error_code(
            records=[_postgres_chunk_row_to_record(row) for row in rows],
            error_code=normalized_code,
            top_k=top_k,
            tenant_id=tenant_id,
            permission_tags=permission_tags,
        )

    def _upsert_document(self, cursor, jsonb, record: VectorRecord) -> None:
        metadata = record.chunk.metadata
        cursor.execute(
            """
            INSERT INTO rag_documents (
                collection_name, document_id, source_type, source_name,
                business_module, title, raw_path, content_hash, metadata, status,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW())
            ON CONFLICT (collection_name, document_id) DO UPDATE SET
                source_type = EXCLUDED.source_type,
                source_name = EXCLUDED.source_name,
                business_module = EXCLUDED.business_module,
                title = EXCLUDED.title,
                raw_path = EXCLUDED.raw_path,
                content_hash = EXCLUDED.content_hash,
                metadata = EXCLUDED.metadata,
                status = 'active',
                updated_at = NOW()
            """,
            (
                self.collection_name,
                record.chunk.document_id,
                str(metadata.get("source_type") or "knowledge_file"),
                _metadata_str(metadata, "source", "filename"),
                _metadata_str(metadata, "business_module"),
                _metadata_str(metadata, "title", "section_title"),
                _metadata_str(metadata, "source_path", "raw_path"),
                _metadata_str(metadata, "content_hash") or _hash_text(record.chunk.text),
                jsonb(metadata),
            ),
        )

    def _upsert_chunk(self, cursor, jsonb, record: VectorRecord) -> None:
        metadata = record.chunk.metadata
        cursor.execute(
            """
            INSERT INTO rag_knowledge_chunks (
                collection_name, chunk_id, document_id, chunk_index, chunk_text,
                summary, keywords, tags, intent_labels, business_module,
                error_code, fault_type, order_type, area_code, priority,
                embedding, metadata, content_hash, version, status, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s::vector, %s, %s, %s, 'active', NOW()
            )
            ON CONFLICT (collection_name, chunk_id) DO UPDATE SET
                document_id = EXCLUDED.document_id,
                chunk_index = EXCLUDED.chunk_index,
                chunk_text = EXCLUDED.chunk_text,
                summary = EXCLUDED.summary,
                keywords = EXCLUDED.keywords,
                tags = EXCLUDED.tags,
                intent_labels = EXCLUDED.intent_labels,
                business_module = EXCLUDED.business_module,
                error_code = EXCLUDED.error_code,
                fault_type = EXCLUDED.fault_type,
                order_type = EXCLUDED.order_type,
                area_code = EXCLUDED.area_code,
                priority = EXCLUDED.priority,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                content_hash = EXCLUDED.content_hash,
                version = EXCLUDED.version,
                status = 'active',
                updated_at = NOW()
            """,
            (
                self.collection_name,
                record.chunk.id,
                record.chunk.document_id,
                _metadata_int(metadata, "chunk_index", 0),
                record.chunk.text,
                _metadata_str(metadata, "summary"),
                _metadata_list(metadata, "keywords"),
                _metadata_list(metadata, "tags", "permission_tags"),
                _metadata_list(metadata, "intent_labels"),
                _metadata_str(metadata, "business_module"),
                _metadata_str(metadata, "error_code"),
                _metadata_str(metadata, "fault_type"),
                _metadata_str(metadata, "order_type"),
                _metadata_str(metadata, "area_code"),
                _metadata_int(metadata, "priority", 50),
                _vector_literal(record.embedding),
                jsonb(metadata),
                _metadata_str(metadata, "content_hash") or _hash_text(record.chunk.text),
                _metadata_int(metadata, "version", 1),
            ),
        )

    def _search_semantic_candidates(
        self,
        query_embedding: list[float],
        limit: int,
    ) -> tuple[list[VectorRecord], dict[str, float]]:
        psycopg, dict_row, _ = _import_psycopg()
        vector = _vector_literal(query_embedding)
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        chunk_id, document_id, chunk_text, metadata,
                        embedding::text AS embedding_text,
                        1 - (embedding <=> %s::vector) AS semantic_score
                    FROM rag_knowledge_chunks
                    WHERE collection_name = %s AND status = 'active'
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (vector, self.collection_name, vector, limit),
                )
                rows = cursor.fetchall()
        records = [_postgres_chunk_row_to_record(row) for row in rows]
        scores = {
            record.chunk.id: float(row.get("semantic_score") or 0.0)
            for record, row in zip(records, rows)
        }
        return records, scores

    def _query_keyword_candidates(self, query_text: str, limit: int) -> list[VectorRecord]:
        tokens = tokenize_for_keyword_search(query_text)[:12]
        if not tokens:
            return []
        predicates = " OR ".join(["chunk_text ILIKE %s"] * len(tokens))
        params: list[Any] = [
            self.collection_name,
            *[f"%{token}%" for token in tokens],
            limit,
        ]
        psycopg, dict_row, _ = _import_psycopg()
        with psycopg.connect(self.dsn, row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT
                        chunk_id, document_id, chunk_text, metadata,
                        embedding::text AS embedding_text
                    FROM rag_knowledge_chunks
                    WHERE collection_name = %s
                      AND status = 'active'
                      AND ({predicates})
                    ORDER BY priority DESC, updated_at DESC
                    LIMIT %s
                    """,
                    tuple(params),
                )
                rows = cursor.fetchall()
        return [_postgres_chunk_row_to_record(row) for row in rows]

    def _ensure_schema(self) -> None:
        psycopg, _, _ = _import_psycopg()
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rag_documents (
                        id BIGSERIAL PRIMARY KEY,
                        collection_name TEXT NOT NULL DEFAULT 'default',
                        document_id TEXT NOT NULL,
                        source_type TEXT NOT NULL,
                        source_name TEXT,
                        business_module TEXT,
                        title TEXT,
                        raw_path TEXT,
                        content_hash TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
                        status TEXT NOT NULL DEFAULT 'active',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS rag_knowledge_chunks (
                        id BIGSERIAL PRIMARY KEY,
                        collection_name TEXT NOT NULL DEFAULT 'default',
                        chunk_id TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        chunk_text TEXT NOT NULL,
                        summary TEXT,
                        keywords TEXT[],
                        tags TEXT[],
                        intent_labels TEXT[],
                        business_module TEXT,
                        error_code TEXT,
                        fault_type TEXT,
                        order_type TEXT,
                        area_code TEXT,
                        priority INTEGER NOT NULL DEFAULT 50,
                        embedding VECTOR(%s) NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
                        content_hash TEXT NOT NULL,
                        version INTEGER NOT NULL DEFAULT 1,
                        status TEXT NOT NULL DEFAULT 'active',
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """ % int(self.dimension)
                )
                cursor.execute(
                    "ALTER TABLE rag_documents ADD COLUMN IF NOT EXISTS collection_name TEXT NOT NULL DEFAULT 'default'"
                )
                cursor.execute(
                    "ALTER TABLE rag_knowledge_chunks ADD COLUMN IF NOT EXISTS collection_name TEXT NOT NULL DEFAULT 'default'"
                )
                cursor.execute(
                    "ALTER TABLE rag_knowledge_chunks ADD COLUMN IF NOT EXISTS error_code TEXT"
                )
                cursor.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_documents_collection_document "
                    "ON rag_documents(collection_name, document_id)"
                )
                cursor.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_chunks_collection_chunk "
                    "ON rag_knowledge_chunks(collection_name, chunk_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_rag_chunks_collection_status "
                    "ON rag_knowledge_chunks(collection_name, status, priority DESC)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_rag_chunks_error_code "
                    "ON rag_knowledge_chunks(collection_name, error_code) "
                    "WHERE error_code IS NOT NULL"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_rag_chunks_metadata "
                    "ON rag_knowledge_chunks USING GIN(metadata)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding "
                    "ON rag_knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
                )


def create_vector_store(settings: Settings) -> VectorStore:
    """根据配置创建向量存储。"""

    if settings.vector_store_provider == "postgresql":
        assert settings.ops_postgres_dsn is not None
        return PostgresVectorStore(
            dsn=settings.ops_postgres_dsn,
            collection_name=settings.collection_name,
            dimension=settings.embedding_dimension,
        )
    raise ValueError(f"Unsupported vector store provider: {settings.vector_store_provider}")


def _rank_vector_records(
    records: list[VectorRecord],
    query_embedding: list[float],
    query_text: str | None = None,
    top_k: int = 4,
    min_score: float | None = None,
    relative_score_threshold: float | None = None,
    mode: str = "hybrid",
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
    bm25_weight: float | None = None,
    candidate_k: int | None = None,
    semantic_scores: dict[str, float] | None = None,
    tenant_id: str | None = None,
    permission_tags: tuple[str, ...] | list[str] | None = None,
) -> list[RetrievalResult]:
    if top_k <= 0 or not records:
        return []

    # 统一排序入口：pgvector 语义候选和关键词候选都会走这里，保证打分语义一致。
    records = _filter_authorized_records(records, tenant_id, permission_tags)
    if not records:
        return []
    actual_bm25_weight = keyword_weight if bm25_weight is None else bm25_weight
    actual_candidate_k = _candidate_limit(
        candidate_k=candidate_k,
        top_k=top_k,
        record_count=len(records),
    )
    query_tokens = tokenize_for_keyword_search(query_text or "")
    actual_semantic_scores = semantic_scores or {
        record.chunk.id: _cosine(query_embedding, record.embedding)
        for record in records
    }
    bm25_scores = _bm25_scores(query_tokens, records)
    normalized_bm25_scores = _normalize_positive_scores(bm25_scores)

    # 先分别取语义候选和 BM25 候选，再按检索模式合并，避免纯关键词命中的业务词被语义召回漏掉。
    semantic_ids = _top_ids(
        actual_semantic_scores,
        limit=actual_candidate_k,
        keep_zero=True,
    )
    bm25_ids = _top_ids(
        bm25_scores,
        limit=actual_candidate_k,
        keep_zero=False,
    )
    candidate_ids = _select_candidate_ids(
        mode=mode,
        semantic_ids=semantic_ids,
        bm25_ids=bm25_ids,
    )
    record_by_id = {record.chunk.id: record for record in records}

    scored: list[RetrievalResult] = []
    for chunk_id in candidate_ids:
        record = record_by_id[chunk_id]
        record_score = _RecordScore(
            record=record,
            semantic_score=actual_semantic_scores.get(chunk_id, 0.0),
            bm25_score=bm25_scores.get(chunk_id, 0.0),
            normalized_bm25_score=normalized_bm25_scores.get(chunk_id, 0.0),
        )
        score = _combine_scores(
            semantic_score=record_score.semantic_score,
            normalized_bm25_score=record_score.normalized_bm25_score,
            mode=mode,
            semantic_weight=semantic_weight,
            bm25_weight=actual_bm25_weight,
        )
        scored.append(
            RetrievalResult(
                chunk=record_score.record.chunk,
                score=score,
                retrieval_score=score,
                semantic_score=record_score.semantic_score,
                bm25_score=record_score.bm25_score,
                normalized_bm25_score=record_score.normalized_bm25_score,
                keyword_score=record_score.normalized_bm25_score,
            )
        )
    if min_score is not None:
        scored = [
            result
            for result in scored
            if result.score > min_score
        ]
    scored.sort(key=lambda result: result.score, reverse=True)
    if relative_score_threshold is not None and scored:
        best_score = scored[0].score
        if best_score > 0 and relative_score_threshold > 0:
            # 相对阈值用于过滤明显弱于首条结果的尾部噪声，减少无关片段进入增强上下文。
            score_floor = best_score * relative_score_threshold
            scored = [
                result
                for result in scored
                if result.score >= score_floor
            ]
    return scored[:top_k]


def _filter_authorized_records(
    records: list[VectorRecord],
    tenant_id: str | None,
    permission_tags: tuple[str, ...] | list[str] | None,
) -> list[VectorRecord]:
    requested_tenant = (tenant_id or "").strip()
    requested_tags = _normalize_permission_tags(permission_tags)
    if not requested_tenant and not requested_tags:
        return records
    return [
        record
        for record in records
        if _record_allowed(record, requested_tenant, requested_tags)
    ]


def _search_records_by_error_code(
    records: list[VectorRecord],
    error_code: str,
    top_k: int = 4,
    tenant_id: str | None = None,
    permission_tags: tuple[str, ...] | list[str] | None = None,
) -> list[RetrievalResult]:
    if top_k <= 0:
        return []
    normalized_code = normalize_error_code(error_code)
    authorized = _filter_authorized_records(records, tenant_id, permission_tags)
    matched = [
        record
        for record in authorized
        if normalized_code in _metadata_error_codes(record.chunk.metadata)
    ]
    return [
        RetrievalResult(
            chunk=record.chunk,
            score=1.0,
            retrieval_score=1.0,
            keyword_score=1.0,
        )
        for record in matched[:top_k]
    ]


def _metadata_error_codes(metadata: dict[str, Any]) -> set[str]:
    values: list[str] = []
    direct = metadata.get("error_code")
    if direct not in (None, ""):
        values.append(str(direct))
    raw_codes = metadata.get("error_codes")
    if isinstance(raw_codes, str):
        values.extend(raw_codes.replace("，", ",").replace("；", ",").replace(";", ",").split(","))
    elif isinstance(raw_codes, (list, tuple, set)):
        values.extend(str(item) for item in raw_codes)
    elif raw_codes not in (None, ""):
        values.append(str(raw_codes))
    return {
        normalize_error_code(value)
        for value in values
        if value and value.strip()
    }


def _record_allowed(
    record: VectorRecord,
    tenant_id: str,
    permission_tags: set[str],
) -> bool:
    metadata = record.chunk.metadata
    record_tenant = str(metadata.get("tenant_id") or "default").strip() or "default"
    if tenant_id and record_tenant != tenant_id:
        return False

    if not permission_tags:
        return True
    record_tags = _normalize_permission_tags(metadata.get("permission_tags"))
    if not record_tags:
        return "public" in permission_tags
    return bool(record_tags & permission_tags)


def _normalize_permission_tags(
    value: tuple[str, ...] | list[str] | set[str] | str | None,
) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        raw_values = value.replace("，", ",").replace("；", ",").replace(";", ",").split(",")
    else:
        raw_values = [str(item) for item in value]
    return {
        item.strip()
        for item in raw_values
        if item and item.strip()
    }


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _bm25_scores(
    query_tokens: list[str],
    records: list[VectorRecord],
) -> dict[str, float]:
    if not query_tokens or not records:
        return {record.chunk.id: 0.0 for record in records}

    # 这里是轻量 BM25，实现重点是灰度阶段可解释：每个 chunk 的关键词命中能和语义分一起写入 trace。
    document_tokens = [
        tokenize_for_keyword_search(record.chunk.text)
        for record in records
    ]
    document_lengths = [len(tokens) for tokens in document_tokens]
    average_length = sum(document_lengths) / len(document_lengths)
    if average_length <= 0:
        average_length = 1.0

    document_frequencies: dict[str, int] = {}
    for tokens in document_tokens:
        for token in set(tokens):
            document_frequencies[token] = document_frequencies.get(token, 0) + 1

    query_terms = set(query_tokens)
    record_scores: dict[str, float] = {}
    corpus_size = len(records)
    for record, tokens, document_length in zip(records, document_tokens, document_lengths):
        token_counts = _count_tokens(tokens)
        score = 0.0
        for token in query_terms:
            term_frequency = token_counts.get(token, 0)
            if term_frequency <= 0:
                continue
            document_frequency = document_frequencies.get(token, 0)
            idf = math.log(
                1 + (corpus_size - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            denominator = term_frequency + BM25_K1 * (
                1 - BM25_B + BM25_B * document_length / average_length
            )
            score += idf * (term_frequency * (BM25_K1 + 1)) / denominator
        record_scores[record.chunk.id] = score
    return record_scores


def _count_tokens(tokens: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    return counts


def _normalize_positive_scores(scores: dict[str, float]) -> dict[str, float]:
    max_score = max((score for score in scores.values() if score > 0), default=0.0)
    if max_score <= 0:
        return {key: 0.0 for key in scores}
    return {
        key: max(score, 0.0) / max_score
        for key, score in scores.items()
    }


def _candidate_limit(candidate_k: int | None, top_k: int, record_count: int) -> int:
    if record_count <= 0:
        return 0
    if candidate_k is None or candidate_k <= 0:
        candidate_k = top_k * 5
    return min(max(top_k, candidate_k), record_count)


def _top_ids(
    scores: dict[str, float],
    limit: int,
    keep_zero: bool,
) -> list[str]:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    result: list[str] = []
    for chunk_id, score in ordered:
        if not keep_zero and score <= 0:
            continue
        result.append(chunk_id)
        if len(result) >= limit:
            break
    return result


def _select_candidate_ids(
    mode: str,
    semantic_ids: list[str],
    bm25_ids: list[str],
) -> list[str]:
    normalized_mode = _normalize_mode(mode)
    if normalized_mode == "semantic":
        return semantic_ids
    if normalized_mode == "bm25":
        return bm25_ids
    return _dedupe([*semantic_ids, *bm25_ids])


def _combine_scores(
    semantic_score: float,
    normalized_bm25_score: float,
    mode: str,
    semantic_weight: float,
    bm25_weight: float,
) -> float:
    normalized_mode = _normalize_mode(mode)
    if normalized_mode == "semantic":
        return semantic_score
    if normalized_mode == "bm25":
        return normalized_bm25_score
    total_weight = semantic_weight + bm25_weight
    if total_weight <= 0:
        semantic_weight = 0.7
        bm25_weight = 0.3
        total_weight = 1.0
    semantic_component = max(semantic_score, 0.0)
    return (
        semantic_component * (semantic_weight / total_weight)
        + normalized_bm25_score * (bm25_weight / total_weight)
    )


def _normalize_mode(mode: str) -> str:
    normalized = mode.lower()
    if normalized in {"keyword", "bm25"}:
        return "bm25"
    if normalized == "semantic":
        return "semantic"
    return "hybrid"


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _merge_records(
    primary: list[VectorRecord],
    secondary: list[VectorRecord],
) -> list[VectorRecord]:
    merged: list[VectorRecord] = []
    seen: set[str] = set()
    for record in [*primary, *secondary]:
        if record.chunk.id in seen:
            continue
        seen.add(record.chunk.id)
        merged.append(record)
    return merged


def _metadata_str(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _metadata_int(metadata: dict[str, Any], key: str, default: int) -> int:
    value = metadata.get(key)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _metadata_list(metadata: dict[str, Any], *keys: str) -> list[str] | None:
    for key in keys:
        value = metadata.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, str):
            items = value.replace("，", ",").replace("；", ",").replace(";", ",").split(",")
        elif isinstance(value, (list, tuple, set)):
            items = [str(item) for item in value]
        else:
            items = [str(value)]
        normalized = [item.strip() for item in items if item and item.strip()]
        if normalized:
            return normalized
    return None


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.12g}" for value in values) + "]"


def _parse_vector_text(value: Any) -> list[float]:
    if value in (None, ""):
        return []
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    if not text:
        return []
    return [float(item) for item in text.split(",") if item.strip()]


def _postgres_chunk_row_to_record(row: dict[str, Any]) -> VectorRecord:
    return VectorRecord(
        chunk=Chunk(
            id=str(row["chunk_id"]),
            document_id=str(row["document_id"]),
            text=str(row["chunk_text"]),
            metadata=_decode_json_value(row.get("metadata"), default={}),
        ),
        embedding=_parse_vector_text(row.get("embedding_text")),
    )


def _decode_json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _import_psycopg():
    try:
        import psycopg
        from psycopg.rows import dict_row
        from psycopg.types.json import Jsonb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PostgreSQL/pgvector 向量库需要安装 psycopg：pip install -e \".[pgsql]\""
        ) from exc
    return psycopg, dict_row, Jsonb
