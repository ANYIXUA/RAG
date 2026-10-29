from __future__ import annotations

import gc
import hashlib
import json
import math
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from .models import SearchResult, TextChunk


_TOKEN_RE = re.compile(r"[A-Za-z]+\d*|\d+|[\u3400-\u9fff]")


class Encoder(Protocol):
    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> Sequence[Sequence[float]]:
        ...


@dataclass(frozen=True)
class DynamicEmbeddingResult:
    embeddings: list[list[float]]
    effective_batch_size: int
    oom_retries: int


class HashEmbedding:
    """无需模型下载的本地替身，只用于打通 Demo，不代表真实语义效果。"""

    def __init__(self, dimension: int = 384) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be greater than zero")
        self.dimension = dimension
        self.model_name = f"hashing-demo-{dimension}"

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> list[list[float]]:
        del batch_size, show_progress_bar
        return [self._encode_one(sentence) for sentence in sentences]

    def _encode_one(self, text: str) -> list[float]:
        tokens = _search_tokens(text)
        vector = [0.0] * self.dimension
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        return _normalize(vector)


class SentenceTransformerEmbedding:
    """真实本地模型路径，显式展示矩阵化 batch encode 调用。"""

    def __init__(
        self,
        model_name: str,
        device: str | None = None,
        *,
        cache_folder: str | None = None,
        revision: str | None = None,
        local_files_only: bool = False,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "缺少 sentence-transformers；请按 Demo requirements.txt 安装"
            ) from exc
        self.model_name = model_name
        self.model = SentenceTransformer(
            model_name,
            device=device,
            cache_folder=cache_folder,
            revision=revision,
            local_files_only=local_files_only,
        )
        self.dimension = int(self.model.get_sentence_embedding_dimension())

    def encode(
        self,
        sentences: Sequence[str],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> list[list[float]]:
        # 关键：一次提交整个句子矩阵，模型内部按 batch_size 并行推理。
        matrix = self.model.encode(
            list(sentences),
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return matrix.tolist()


def embed_with_dynamic_batch(
    encoder: Encoder,
    texts: Sequence[str],
    *,
    initial_batch_size: int = 64,
    min_batch_size: int = 1,
    show_progress_bar: bool = True,
) -> DynamicEmbeddingResult:
    """显存/内存 OOM 时把 128→64→32 逐级减半，并重试同一批文本。"""

    if initial_batch_size <= 0 or min_batch_size <= 0:
        raise ValueError("batch sizes must be greater than zero")
    if min_batch_size > initial_batch_size:
        raise ValueError("min_batch_size cannot exceed initial_batch_size")

    embeddings: list[list[float]] = []
    offset = 0
    current_batch_size = initial_batch_size
    oom_retries = 0
    while offset < len(texts):
        batch = list(texts[offset : offset + current_batch_size])
        try:
            encoded = encoder.encode(
                batch,
                batch_size=current_batch_size,
                show_progress_bar=show_progress_bar,
            )
        except (MemoryError, RuntimeError) as exc:
            if not _is_oom(exc) or current_batch_size <= min_batch_size:
                raise
            current_batch_size = max(min_batch_size, current_batch_size // 2)
            oom_retries += 1
            _release_accelerator_cache()
            continue
        vectors = [[float(value) for value in vector] for vector in encoded]
        if len(vectors) != len(batch):
            raise RuntimeError(
                f"Embedding 数量不匹配: input={len(batch)}, output={len(vectors)}"
            )
        embeddings.extend(vectors)
        offset += len(batch)
    return DynamicEmbeddingResult(
        embeddings=embeddings,
        effective_batch_size=current_batch_size,
        oom_retries=oom_retries,
    )


class SQLiteVectorStore:
    """零额外依赖的本地持久化验收路径；查询时在 Python 中算余弦相似度。"""

    def __init__(self, path: Path, collection_name: str) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self._ensure_schema()

    def upsert(self, chunks: Sequence[TextChunk], embeddings: Sequence[Sequence[float]]) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        rows = [
            (
                self.collection_name,
                chunk.id,
                chunk.document_id,
                chunk.text,
                json.dumps(chunk.metadata, ensure_ascii=False, sort_keys=True),
                json.dumps([float(value) for value in embedding]),
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        with closing(sqlite3.connect(self.path)) as connection:
            connection.executemany(
                """
                INSERT INTO vectors (
                    collection_name, chunk_id, document_id, chunk_text, metadata, embedding
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(collection_name, chunk_id) DO UPDATE SET
                    document_id = excluded.document_id,
                    chunk_text = excluded.chunk_text,
                    metadata = excluded.metadata,
                    embedding = excluded.embedding
                """,
                rows,
            )
            connection.commit()
        return len(rows)

    def query(self, query_embedding: Sequence[float], *, top_k: int = 5) -> list[SearchResult]:
        if top_k <= 0:
            return []
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute(
                """
                SELECT chunk_id, chunk_text, metadata, embedding
                FROM vectors
                WHERE collection_name = ?
                """,
                (self.collection_name,),
            ).fetchall()
        scored = [
            SearchResult(
                id=row[0],
                text=row[1],
                metadata=json.loads(row[2]),
                score=_cosine(query_embedding, json.loads(row[3])),
            )
            for row in rows
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    def count(self) -> int:
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM vectors WHERE collection_name = ?",
                (self.collection_name,),
            ).fetchone()
        return int(row[0] if row else 0)

    def _ensure_schema(self) -> None:
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS vectors (
                    collection_name TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    chunk_text TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    PRIMARY KEY (collection_name, chunk_id)
                )
                """
            )
            connection.commit()


class ChromaVectorStore:
    """ChromaDB 本地 PersistentClient + 批量 upsert 路径。"""

    def __init__(self, persist_dir: Path, collection_name: str) -> None:
        try:
            import chromadb
        except ModuleNotFoundError as exc:
            raise RuntimeError("缺少 chromadb；请按 Demo requirements.txt 安装") from exc
        resolved = persist_dir.resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        self.persist_dir = resolved
        client = chromadb.PersistentClient(path=str(resolved))
        self.client = client
        self.collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )

    @classmethod
    def from_collection(cls, collection: Any) -> "ChromaVectorStore":
        instance = cls.__new__(cls)
        instance.collection = collection
        instance.persist_dir = None
        instance.client = None
        return instance

    def upsert(self, chunks: Sequence[TextChunk], embeddings: Sequence[Sequence[float]]) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return 0
        # 关键：每个 pipeline batch 只调用一次 upsert，不逐条写库。
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=[[float(value) for value in vector] for vector in embeddings],
            metadatas=[_chroma_metadata(chunk.metadata) for chunk in chunks],
        )
        return len(chunks)

    def query(self, query_embedding: Sequence[float], *, top_k: int = 5) -> list[SearchResult]:
        response = self.collection.query(
            query_embeddings=[[float(value) for value in query_embedding]],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = (response.get("ids") or [[]])[0]
        documents = (response.get("documents") or [[]])[0]
        metadatas = (response.get("metadatas") or [[]])[0]
        distances = (response.get("distances") or [[]])[0]
        return [
            SearchResult(
                id=chunk_id,
                text=document,
                metadata=_restore_chroma_metadata(metadata or {}),
                score=1.0 - float(distance),
            )
            for chunk_id, document, metadata, distance in zip(
                ids, documents, metadatas, distances
            )
        ]

    def count(self) -> int:
        return int(self.collection.count())

    def close(self) -> None:
        """释放 Windows 上 Chroma 持有的索引文件句柄。"""

        client = self.client
        self.client = None
        if client is None:
            return
        close = getattr(client, "close", None)
        if callable(close):
            close()
            return
        # 兼容没有公开 close() 的旧 Chroma Client。
        system = getattr(client, "_system", None)
        stop = getattr(system, "stop", None)
        if callable(stop):
            stop()


def _search_tokens(text: str) -> list[str]:
    basic = [token.casefold() for token in _TOKEN_RE.findall(text)]
    cjk = "".join(token for token in basic if len(token) == 1 and "\u3400" <= token <= "\u9fff")
    ngrams = [cjk[index : index + 2] for index in range(max(0, len(cjk) - 1))]
    return basic + ngrams


def _normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(value) ** 2 for value in vector))
    if norm == 0:
        return [0.0 for _ in vector]
    return [float(value) / norm for value in vector]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vector dimensions do not match")
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(float(a) * float(b) for a, b in zip(left, right)) / (left_norm * right_norm)


def _is_oom(exc: BaseException) -> bool:
    if isinstance(exc, MemoryError):
        return True
    message = str(exc).casefold()
    return "out of memory" in message or "cannot allocate memory" in message


def _release_accelerator_cache() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ModuleNotFoundError:
        pass


def _chroma_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    output: dict[str, str | int | float | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            output[key] = value
        else:
            output[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return output


def _restore_chroma_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    restored: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str) and value[:1] in {"[", "{"}:
            try:
                restored[key] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
        restored[key] = value
    return restored
