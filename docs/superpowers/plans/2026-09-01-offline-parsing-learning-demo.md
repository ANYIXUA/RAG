# Offline Parsing Learning Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** 构建一条纯 Python 标准库的 TXT 离线解析、切片、Hash 向量化、SQLite 持久化和 Top-K 查询学习链路。

**Architecture:** 新代码放在独立的 demo/offline_parsing_learning 包内，保持 Parser、Chunker、Embedding、Store 和 Pipeline 单向依赖。Pipeline 是唯一的业务编排层；CLI 只把参数交给 Pipeline，现有 demo/offline_parsing 和生产 rag_app 保持不变。

**Tech Stack:** Python >= 3.10、dataclasses、pathlib、hashlib、re、math、json、sqlite3、argparse、unittest。

**Spec:** docs/superpowers/specs/2026-09-01-offline-parsing-learning-demo-design.md

## Global Constraints

- 第一版只递归处理 UTF-8 TXT 文件。
- 只使用 Python 标准库，不新增依赖。
- 默认切片大小 200 字符、重叠 40 字符。
- Hash Embedding 固定为 64 维，并使用 hashlib.sha256；禁止使用 Python 内置 hash()。
- SQLite 只建立 chunks 一张表，向量保存为 JSON 文本。
- 查询使用全表扫描和余弦相似度。
- 第一版采用同步、失败即停止的流程。
- 不修改 demo/offline_parsing、rag_app 或 tests/test_offline_parsing_demo.py。
- 每个任务都先看到预期失败，再写最少实现让测试通过。

---

## File Map

计划创建：

- demo/offline_parsing_learning/__init__.py：标记独立学习包。
- demo/offline_parsing_learning/models.py：三个不可变数据对象。
- demo/offline_parsing_learning/parser.py：TXT 发现与读取。
- demo/offline_parsing_learning/chunker.py：固定字符窗口切片。
- demo/offline_parsing_learning/embedding.py：确定性 Hash 向量和余弦相似度。
- demo/offline_parsing_learning/store.py：SQLite schema、upsert、计数和 Top-K。
- demo/offline_parsing_learning/pipeline.py：导入与查询编排。
- demo/offline_parsing_learning/cli.py：ingest/search 命令。
- demo/offline_parsing_learning/sample_docs/incident_codes.txt：命中样例。
- demo/offline_parsing_learning/sample_docs/operations.txt：对照样例。
- tests/test_offline_parsing_learning.py：全部学习版测试。

## Task 1: Data Models

**Files:**

- Create: demo/offline_parsing_learning/__init__.py
- Create: demo/offline_parsing_learning/models.py
- Create: tests/test_offline_parsing_learning.py

**Interfaces:**

- Consumes: 无。
- Produces:
  - ParsedDocument(document_id: str, source: str, text: str)
  - TextChunk(chunk_id: str, document_id: str, source: str, chunk_index: int, start_offset: int, end_offset: int, text: str)
  - SearchResult(chunk_id: str, source: str, text: str, score: float)

- [ ] **Step 1: Write the failing model test**

Create tests/test_offline_parsing_learning.py:

~~~python
import unittest

from demo.offline_parsing_learning.models import (
    ParsedDocument,
    SearchResult,
    TextChunk,
)


class ModelsTest(unittest.TestCase):
    def test_models_keep_pipeline_fields(self) -> None:
        document = ParsedDocument(
            document_id="doc-1",
            source="incident_codes.txt",
            text="E203 地址校验失败",
        )
        chunk = TextChunk(
            chunk_id="chunk-1",
            document_id=document.document_id,
            source=document.source,
            chunk_index=0,
            start_offset=0,
            end_offset=len(document.text),
            text=document.text,
        )
        result = SearchResult(
            chunk_id=chunk.chunk_id,
            source=chunk.source,
            text=chunk.text,
            score=1.0,
        )

        self.assertEqual(chunk.document_id, "doc-1")
        self.assertEqual(result.source, "incident_codes.txt")
        self.assertEqual(result.score, 1.0)


if __name__ == "__main__":
    unittest.main()
~~~

- [ ] **Step 2: Run the test and confirm the expected failure**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.ModelsTest -v
~~~

Expected: FAIL with ModuleNotFoundError for demo.offline_parsing_learning.

- [ ] **Step 3: Create the package and minimal models**

Create demo/offline_parsing_learning/__init__.py:

~~~python
"""最小离线解析学习 Demo，不接入生产主链路。"""
~~~

Create demo/offline_parsing_learning/models.py:

~~~python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedDocument:
    document_id: str
    source: str
    text: str


@dataclass(frozen=True)
class TextChunk:
    chunk_id: str
    document_id: str
    source: str
    chunk_index: int
    start_offset: int
    end_offset: int
    text: str


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    source: str
    text: str
    score: float
~~~

- [ ] **Step 4: Run the model test**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.ModelsTest -v
~~~

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

~~~powershell
git add demo/offline_parsing_learning/__init__.py demo/offline_parsing_learning/models.py tests/test_offline_parsing_learning.py
git commit -m "feat: add offline parsing learning models"
~~~

## Task 2: TXT Discovery and Parsing

**Files:**

- Create: demo/offline_parsing_learning/parser.py
- Modify: tests/test_offline_parsing_learning.py

**Interfaces:**

- Consumes: ParsedDocument from Task 1.
- Produces:
  - discover_txt_files(source_dir: Path) -> list[Path]
  - parse_txt_file(path: Path, source_dir: Path) -> ParsedDocument | None

- [ ] **Step 1: Add the failing parser tests**

Add these imports to tests/test_offline_parsing_learning.py:

~~~python
import tempfile
from pathlib import Path

from demo.offline_parsing_learning.parser import (
    discover_txt_files,
    parse_txt_file,
)
~~~

Add this test class:

~~~python
class ParserTest(unittest.TestCase):
    def test_discovers_txt_in_stable_order_and_parses_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "nested"
            nested.mkdir()
            (root / "z.TXT").write_text("最后一个文件", encoding="utf-8")
            (nested / "a.txt").write_text("E203 地址校验失败", encoding="utf-8")

            paths = discover_txt_files(root)
            relative_paths = [
                path.relative_to(root).as_posix()
                for path in paths
            ]
            first = parse_txt_file(paths[0], root)
            repeated = parse_txt_file(paths[0], root)

        self.assertEqual(relative_paths, ["nested/a.txt", "z.TXT"])
        self.assertIsNotNone(first)
        self.assertIsNotNone(repeated)
        assert first is not None
        assert repeated is not None
        self.assertEqual(first.source, "nested/a.txt")
        self.assertEqual(first.text, "E203 地址校验失败")
        self.assertEqual(first.document_id, repeated.document_id)

    def test_empty_txt_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "empty.txt"
            path.write_text(" \n ", encoding="utf-8")

            document = parse_txt_file(path, root)

        self.assertIsNone(document)

    def test_missing_or_empty_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            empty = root / "empty"
            empty.mkdir()

            with self.assertRaises(ValueError):
                discover_txt_files(empty)
            with self.assertRaises(ValueError):
                discover_txt_files(root / "missing")
~~~

- [ ] **Step 2: Run the parser tests and confirm the expected failure**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.ParserTest -v
~~~

Expected: FAIL because demo.offline_parsing_learning.parser does not exist.

- [ ] **Step 3: Implement TXT discovery and parsing**

Create demo/offline_parsing_learning/parser.py:

~~~python
from __future__ import annotations

import hashlib
from pathlib import Path

from .models import ParsedDocument


def discover_txt_files(source_dir: Path) -> list[Path]:
    root = source_dir.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"input directory does not exist: {root}")

    paths = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() == ".txt"
    ]
    paths.sort(
        key=lambda path: path.relative_to(root).as_posix().casefold()
    )
    if not paths:
        raise ValueError(f"no TXT files found: {root}")
    return paths


def parse_txt_file(
    path: Path,
    source_dir: Path,
) -> ParsedDocument | None:
    root = source_dir.resolve()
    resolved_path = path.resolve()
    source = resolved_path.relative_to(root).as_posix()
    text = resolved_path.read_text(encoding="utf-8")
    if not text.strip():
        return None

    document_id = hashlib.sha256(
        source.casefold().encode("utf-8")
    ).hexdigest()[:24]
    return ParsedDocument(
        document_id=document_id,
        source=source,
        text=text,
    )
~~~

- [ ] **Step 4: Run parser and model tests**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.ModelsTest tests.test_offline_parsing_learning.ParserTest -v
~~~

Expected: all tests PASS.

- [ ] **Step 5: Commit Task 2**

~~~powershell
git add demo/offline_parsing_learning/parser.py tests/test_offline_parsing_learning.py
git commit -m "feat: add deterministic TXT parsing"
~~~

## Task 3: Character Window Chunking

**Files:**

- Create: demo/offline_parsing_learning/chunker.py
- Modify: tests/test_offline_parsing_learning.py

**Interfaces:**

- Consumes: ParsedDocument from Task 1.
- Produces:
  - split_document(document: ParsedDocument, chunk_size: int = 200, chunk_overlap: int = 40) -> list[TextChunk]

- [ ] **Step 1: Add the failing chunker tests**

Add this import to tests/test_offline_parsing_learning.py:

~~~python
from demo.offline_parsing_learning.chunker import split_document
~~~

Add this test class:

~~~python
class ChunkerTest(unittest.TestCase):
    def test_splits_text_with_overlap_and_stable_ids(self) -> None:
        document = ParsedDocument(
            document_id="doc-1",
            source="sample.txt",
            text="abcdefghij",
        )

        chunks = split_document(
            document,
            chunk_size=6,
            chunk_overlap=2,
        )
        repeated = split_document(
            document,
            chunk_size=6,
            chunk_overlap=2,
        )

        self.assertEqual(
            [chunk.text for chunk in chunks],
            ["abcdef", "efghij"],
        )
        self.assertEqual(
            [
                (chunk.start_offset, chunk.end_offset)
                for chunk in chunks
            ],
            [(0, 6), (4, 10)],
        )
        self.assertEqual(
            [chunk.chunk_id for chunk in chunks],
            [chunk.chunk_id for chunk in repeated],
        )

    def test_rejects_invalid_chunk_parameters(self) -> None:
        document = ParsedDocument("doc-1", "sample.txt", "abc")

        with self.assertRaises(ValueError):
            split_document(document, chunk_size=0, chunk_overlap=0)
        with self.assertRaises(ValueError):
            split_document(document, chunk_size=3, chunk_overlap=3)
        with self.assertRaises(ValueError):
            split_document(document, chunk_size=3, chunk_overlap=-1)
~~~

- [ ] **Step 2: Run the chunker tests and confirm the expected failure**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.ChunkerTest -v
~~~

Expected: FAIL because demo.offline_parsing_learning.chunker does not exist.

- [ ] **Step 3: Implement fixed-window chunking**

Create demo/offline_parsing_learning/chunker.py:

~~~python
from __future__ import annotations

import hashlib

from .models import ParsedDocument, TextChunk


def split_document(
    document: ParsedDocument,
    *,
    chunk_size: int = 200,
    chunk_overlap: int = 40,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be in [0, chunk_size)"
        )

    chunks: list[TextChunk] = []
    step = chunk_size - chunk_overlap
    start = 0
    chunk_index = 0

    while start < len(document.text):
        end = min(start + chunk_size, len(document.text))
        chunk_text = document.text[start:end]
        payload = (
            f"{document.document_id}\0"
            f"{chunk_index}\0{chunk_text}"
        )
        chunk_id = hashlib.sha256(
            payload.encode("utf-8")
        ).hexdigest()[:24]
        chunks.append(
            TextChunk(
                chunk_id=chunk_id,
                document_id=document.document_id,
                source=document.source,
                chunk_index=chunk_index,
                start_offset=start,
                end_offset=end,
                text=chunk_text,
            )
        )
        if end == len(document.text):
            break
        start += step
        chunk_index += 1

    return chunks
~~~

- [ ] **Step 4: Run all learning tests**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning -v
~~~

Expected: all current tests PASS.

- [ ] **Step 5: Commit Task 3**

~~~powershell
git add demo/offline_parsing_learning/chunker.py tests/test_offline_parsing_learning.py
git commit -m "feat: add overlapping text chunker"
~~~

## Task 4: Deterministic Hash Embedding

**Files:**

- Create: demo/offline_parsing_learning/embedding.py
- Modify: tests/test_offline_parsing_learning.py

**Interfaces:**

- Consumes: str and numeric vectors.
- Produces:
  - DEFAULT_DIMENSION = 64
  - embed_text(text: str, dimension: int = DEFAULT_DIMENSION) -> list[float]
  - cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float

- [ ] **Step 1: Add the failing embedding tests**

Add these imports to tests/test_offline_parsing_learning.py:

~~~python
import math

from demo.offline_parsing_learning.embedding import (
    cosine_similarity,
    embed_text,
)
~~~

Add this test class:

~~~python
class EmbeddingTest(unittest.TestCase):
    def test_embedding_is_deterministic_and_normalized(self) -> None:
        text = "E203 地址校验失败"

        first = embed_text(text)
        second = embed_text(text)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertAlmostEqual(
            math.sqrt(sum(value * value for value in first)),
            1.0,
        )

    def test_cosine_prefers_identical_text(self) -> None:
        query = embed_text("E203 地址校验失败")
        same = embed_text("E203 地址校验失败")
        unrelated = embed_text("网络接口超时")

        self.assertAlmostEqual(
            cosine_similarity(query, same),
            1.0,
        )
        self.assertGreater(
            cosine_similarity(query, same),
            cosine_similarity(query, unrelated),
        )
~~~

- [ ] **Step 2: Run the embedding tests and confirm the expected failure**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.EmbeddingTest -v
~~~

Expected: FAIL because demo.offline_parsing_learning.embedding does not exist.

- [ ] **Step 3: Implement token hashing and cosine similarity**

Create demo/offline_parsing_learning/embedding.py:

~~~python
from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence


DEFAULT_DIMENSION = 64
_TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9_]+|[\u4e00-\u9fff]"
)


def embed_text(
    text: str,
    dimension: int = DEFAULT_DIMENSION,
) -> list[float]:
    if dimension <= 0:
        raise ValueError("dimension must be greater than zero")

    vector = [0.0] * dimension
    tokens = _TOKEN_PATTERN.findall(text.casefold())
    for token in tokens:
        digest = hashlib.sha256(
            token.encode("utf-8")
        ).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimension")
    if not left:
        raise ValueError("vectors must not be empty")

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    dot_product = sum(
        left_value * right_value
        for left_value, right_value in zip(left, right)
    )
    return dot_product / (left_norm * right_norm)
~~~

- [ ] **Step 4: Run all learning tests**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning -v
~~~

Expected: all current tests PASS.

- [ ] **Step 5: Commit Task 4**

~~~powershell
git add demo/offline_parsing_learning/embedding.py tests/test_offline_parsing_learning.py
git commit -m "feat: add deterministic hash embedding"
~~~

## Task 5: SQLite Schema and Idempotent Upsert

**Files:**

- Create: demo/offline_parsing_learning/store.py
- Modify: tests/test_offline_parsing_learning.py

**Interfaces:**

- Consumes: Sequence[tuple[TextChunk, Sequence[float]]].
- Produces:
  - SQLiteVectorStore(db_path: Path)
  - initialize() -> None
  - upsert_chunks(items: Sequence[tuple[TextChunk, Sequence[float]]]) -> int
  - count_chunks() -> int

- [ ] **Step 1: Add the failing SQLite persistence test**

Add this import to tests/test_offline_parsing_learning.py:

~~~python
from demo.offline_parsing_learning.store import SQLiteVectorStore
~~~

Add this test class:

~~~python
class StorePersistenceTest(unittest.TestCase):
    def test_upsert_is_idempotent(self) -> None:
        chunk = TextChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            source="incident_codes.txt",
            chunk_index=0,
            start_offset=0,
            end_offset=4,
            text="E203",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteVectorStore(
                Path(temp_dir) / "vectors.sqlite3"
            )
            first_written = store.upsert_chunks(
                [(chunk, [1.0, 0.0])]
            )
            second_written = store.upsert_chunks(
                [(chunk, [1.0, 0.0])]
            )
            count = store.count_chunks()

        self.assertEqual(first_written, 1)
        self.assertEqual(second_written, 1)
        self.assertEqual(count, 1)
~~~

- [ ] **Step 2: Run the persistence test and confirm the expected failure**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.StorePersistenceTest -v
~~~

Expected: FAIL because demo.offline_parsing_learning.store does not exist.

- [ ] **Step 3: Implement the schema, transaction and upsert**

Create demo/offline_parsing_learning/store.py:

~~~python
from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from .models import TextChunk


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    source TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    start_offset INTEGER NOT NULL,
    end_offset INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding_json TEXT NOT NULL
)
"""

_UPSERT_SQL = """
INSERT INTO chunks (
    chunk_id,
    document_id,
    source,
    chunk_index,
    start_offset,
    end_offset,
    text,
    embedding_json
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(chunk_id) DO UPDATE SET
    document_id = excluded.document_id,
    source = excluded.source,
    chunk_index = excluded.chunk_index,
    start_offset = excluded.start_offset,
    end_offset = excluded.end_offset,
    text = excluded.text,
    embedding_json = excluded.embedding_json
"""


class SQLiteVectorStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(_CREATE_TABLE_SQL)

    def upsert_chunks(
        self,
        items: Sequence[
            tuple[TextChunk, Sequence[float]]
        ],
    ) -> int:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            (
                chunk.chunk_id,
                chunk.document_id,
                chunk.source,
                chunk.chunk_index,
                chunk.start_offset,
                chunk.end_offset,
                chunk.text,
                json.dumps(
                    list(vector),
                    separators=(",", ":"),
                ),
            )
            for chunk, vector in items
        ]
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(_CREATE_TABLE_SQL)
            connection.executemany(_UPSERT_SQL, rows)
        return len(rows)

    def count_chunks(self) -> int:
        if not self.db_path.exists():
            return 0
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM chunks"
            ).fetchone()
        return int(row[0]) if row is not None else 0
~~~

- [ ] **Step 4: Run all learning tests**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning -v
~~~

Expected: all current tests PASS.

- [ ] **Step 5: Commit Task 5**

~~~powershell
git add demo/offline_parsing_learning/store.py tests/test_offline_parsing_learning.py
git commit -m "feat: add SQLite chunk persistence"
~~~

## Task 6: SQLite Top-K Search

**Files:**

- Modify: demo/offline_parsing_learning/store.py
- Modify: tests/test_offline_parsing_learning.py

**Interfaces:**

- Consumes: cosine_similarity() from Task 4 and stored JSON vectors from Task 5.
- Produces:
  - SQLiteVectorStore.search(query_vector: Sequence[float], top_k: int) -> list[SearchResult]

- [ ] **Step 1: Add the failing search test**

Add this test class to tests/test_offline_parsing_learning.py:

~~~python
class StoreSearchTest(unittest.TestCase):
    def test_search_returns_highest_scoring_chunk(self) -> None:
        incident = TextChunk(
            "chunk-incident",
            "doc-incident",
            "incident_codes.txt",
            0,
            0,
            4,
            "E203",
        )
        operations = TextChunk(
            "chunk-operations",
            "doc-operations",
            "operations.txt",
            0,
            0,
            4,
            "网络",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteVectorStore(
                Path(temp_dir) / "vectors.sqlite3"
            )
            store.upsert_chunks(
                [
                    (incident, [1.0, 0.0]),
                    (operations, [0.0, 1.0]),
                ]
            )
            results = store.search([1.0, 0.0], top_k=1)

            with self.assertRaises(ValueError):
                store.search([1.0, 0.0], top_k=0)

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0].source,
            "incident_codes.txt",
        )
        self.assertAlmostEqual(results[0].score, 1.0)
~~~

- [ ] **Step 2: Run the search test and confirm the expected failure**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.StoreSearchTest -v
~~~

Expected: FAIL with AttributeError because SQLiteVectorStore.search is not defined.

- [ ] **Step 3: Implement deterministic Top-K search**

Update the imports in demo/offline_parsing_learning/store.py:

~~~python
from .embedding import cosine_similarity
from .models import SearchResult, TextChunk
~~~

Add this method to SQLiteVectorStore:

~~~python
    def search(
        self,
        query_vector: Sequence[float],
        *,
        top_k: int,
    ) -> list[SearchResult]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"SQLite index does not exist: {self.db_path}"
            )

        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    chunk_id,
                    source,
                    text,
                    embedding_json
                FROM chunks
                """
            ).fetchall()

        results = [
            SearchResult(
                chunk_id=str(row[0]),
                source=str(row[1]),
                text=str(row[2]),
                score=cosine_similarity(
                    query_vector,
                    json.loads(str(row[3])),
                ),
            )
            for row in rows
        ]
        results.sort(
            key=lambda result: (
                -result.score,
                result.chunk_id,
            )
        )
        return results[:top_k]
~~~

- [ ] **Step 4: Run all learning tests**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning -v
~~~

Expected: all current tests PASS.

- [ ] **Step 5: Commit Task 6**

~~~powershell
git add demo/offline_parsing_learning/store.py tests/test_offline_parsing_learning.py
git commit -m "feat: add SQLite top-k search"
~~~

## Task 7: Ingest and Search Pipeline

**Files:**

- Create: demo/offline_parsing_learning/pipeline.py
- Modify: tests/test_offline_parsing_learning.py

**Interfaces:**

- Consumes: discover_txt_files(), parse_txt_file(), split_document(), embed_text() and SQLiteVectorStore.
- Produces:
  - ingest_directory(source_dir: Path, db_path: Path, chunk_size: int = 200, chunk_overlap: int = 40) -> dict[str, int]
  - search_index(db_path: Path, query: str, top_k: int = 5) -> list[SearchResult]

- [ ] **Step 1: Add the failing end-to-end pipeline test**

Add these imports to tests/test_offline_parsing_learning.py:

~~~python
from demo.offline_parsing_learning.pipeline import (
    ingest_directory,
    search_index,
)
~~~

Add this test class:

~~~python
class PipelineTest(unittest.TestCase):
    def test_ingest_is_idempotent_and_query_hits_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            source_dir.mkdir()
            db_path = root / "index" / "vectors.sqlite3"
            (source_dir / "incident_codes.txt").write_text(
                "E203 地址校验失败：请核对标准地址和资源覆盖。",
                encoding="utf-8",
            )
            (source_dir / "operations.txt").write_text(
                "接口超时时，先检查网络和下游服务。",
                encoding="utf-8",
            )

            first = ingest_directory(source_dir, db_path)
            second = ingest_directory(source_dir, db_path)
            count = SQLiteVectorStore(db_path).count_chunks()
            results = search_index(
                db_path,
                "E203 地址校验失败",
                top_k=2,
            )
            with self.assertRaises(ValueError):
                search_index(db_path, " ", top_k=1)

        self.assertEqual(
            first,
            {
                "files_seen": 2,
                "files_skipped": 0,
                "chunks_written": 2,
            },
        )
        self.assertEqual(second, first)
        self.assertEqual(count, 2)
        self.assertEqual(
            results[0].source,
            "incident_codes.txt",
        )
~~~

- [ ] **Step 2: Run the pipeline test and confirm the expected failure**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.PipelineTest -v
~~~

Expected: FAIL because demo.offline_parsing_learning.pipeline does not exist.

- [ ] **Step 3: Implement the orchestration layer**

Create demo/offline_parsing_learning/pipeline.py:

~~~python
from __future__ import annotations

from pathlib import Path

from .chunker import split_document
from .embedding import embed_text
from .models import SearchResult
from .parser import discover_txt_files, parse_txt_file
from .store import SQLiteVectorStore


def ingest_directory(
    source_dir: Path,
    db_path: Path,
    *,
    chunk_size: int = 200,
    chunk_overlap: int = 40,
) -> dict[str, int]:
    paths = discover_txt_files(source_dir)
    items = []
    files_skipped = 0

    for path in paths:
        document = parse_txt_file(path, source_dir)
        if document is None:
            files_skipped += 1
            continue
        for chunk in split_document(
            document,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ):
            items.append((chunk, embed_text(chunk.text)))

    written = SQLiteVectorStore(db_path).upsert_chunks(items)
    return {
        "files_seen": len(paths),
        "files_skipped": files_skipped,
        "chunks_written": written,
    }


def search_index(
    db_path: Path,
    query: str,
    *,
    top_k: int = 5,
) -> list[SearchResult]:
    if not query.strip():
        raise ValueError("query must not be empty")
    query_vector = embed_text(query)
    return SQLiteVectorStore(db_path).search(
        query_vector,
        top_k=top_k,
    )
~~~

- [ ] **Step 4: Run all learning tests**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning -v
~~~

Expected: all current tests PASS.

- [ ] **Step 5: Commit Task 7**

~~~powershell
git add demo/offline_parsing_learning/pipeline.py tests/test_offline_parsing_learning.py
git commit -m "feat: add offline ingest and search pipeline"
~~~

## Task 8: CLI, Sample Documents and Final Acceptance

**Files:**

- Create: demo/offline_parsing_learning/cli.py
- Create: demo/offline_parsing_learning/sample_docs/incident_codes.txt
- Create: demo/offline_parsing_learning/sample_docs/operations.txt
- Modify: tests/test_offline_parsing_learning.py

**Interfaces:**

- Consumes: ingest_directory() and search_index() from Task 7.
- Produces:
  - build_parser() -> argparse.ArgumentParser
  - main(argv: list[str] | None = None) -> int
  - python -m demo.offline_parsing_learning.cli ingest
  - python -m demo.offline_parsing_learning.cli search

- [ ] **Step 1: Add the failing CLI test**

Add these imports to tests/test_offline_parsing_learning.py:

~~~python
import json
from contextlib import redirect_stdout
from io import StringIO

from demo.offline_parsing_learning.cli import main
~~~

Add this test class:

~~~python
class CliTest(unittest.TestCase):
    def test_ingest_and_search_commands_emit_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            source_dir.mkdir()
            db_path = root / "vectors.sqlite3"
            (source_dir / "incident_codes.txt").write_text(
                "E203 地址校验失败：请核对标准地址。",
                encoding="utf-8",
            )

            ingest_output = StringIO()
            with redirect_stdout(ingest_output):
                ingest_code = main(
                    [
                        "ingest",
                        "--input",
                        str(source_dir),
                        "--db",
                        str(db_path),
                    ]
                )

            search_output = StringIO()
            with redirect_stdout(search_output):
                search_code = main(
                    [
                        "search",
                        "--db",
                        str(db_path),
                        "--query",
                        "E203 地址校验失败",
                        "--top-k",
                        "1",
                    ]
                )

        ingest_payload = json.loads(ingest_output.getvalue())
        search_payload = json.loads(search_output.getvalue())
        self.assertEqual(ingest_code, 0)
        self.assertEqual(search_code, 0)
        self.assertEqual(ingest_payload["files_seen"], 1)
        self.assertEqual(
            search_payload[0]["source"],
            "incident_codes.txt",
        )
~~~

- [ ] **Step 2: Run the CLI test and confirm the expected failure**

Run:

~~~powershell
python -B -m unittest tests.test_offline_parsing_learning.CliTest -v
~~~

Expected: FAIL because demo.offline_parsing_learning.cli does not exist.

- [ ] **Step 3: Implement the CLI**

Create demo/offline_parsing_learning/cli.py:

~~~python
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

from .pipeline import ingest_directory, search_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="最小 TXT 离线解析学习 Demo"
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("--input", type=Path, required=True)
    ingest.add_argument("--db", type=Path, required=True)
    ingest.add_argument("--chunk-size", type=int, default=200)
    ingest.add_argument("--chunk-overlap", type=int, default=40)

    search = subparsers.add_parser("search")
    search.add_argument("--db", type=Path, required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--top-k", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "ingest":
            payload = ingest_directory(
                args.input,
                args.db,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            )
        else:
            payload = [
                asdict(result)
                for result in search_index(
                    args.db,
                    args.query,
                    top_k=args.top_k,
                )
            ]
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
~~~

- [ ] **Step 4: Create the fixed sample documents**

Create demo/offline_parsing_learning/sample_docs/incident_codes.txt:

~~~text
E203 地址校验失败：标准地址不存在或资源未覆盖时，请先核对地址库。
~~~

Create demo/offline_parsing_learning/sample_docs/operations.txt:

~~~text
接口超时时，先检查网络连接与下游服务状态，再查看调用日志。
~~~

- [ ] **Step 5: Run focused tests, compilation and full regression**

Run:

~~~powershell
python -m compileall -q demo/offline_parsing_learning tests/test_offline_parsing_learning.py
python -B -m unittest tests.test_offline_parsing_learning -v
python -B -m unittest discover
~~~

Expected:

- compileall exits with code 0.
- all learning tests PASS.
- the repository test suite PASS; if an unrelated pre-existing test fails, record its exact name and output without changing unrelated code.

- [ ] **Step 6: Run the manual acceptance**

Run:

~~~powershell
python -m demo.offline_parsing_learning.cli ingest --input demo/offline_parsing_learning/sample_docs --db .demo_data/offline_parsing_learning/vectors.sqlite3
python -m demo.offline_parsing_learning.cli ingest --input demo/offline_parsing_learning/sample_docs --db .demo_data/offline_parsing_learning/vectors.sqlite3
python -m demo.offline_parsing_learning.cli search --db .demo_data/offline_parsing_learning/vectors.sqlite3 --query "E203 地址校验失败" --top-k 2
~~~

Expected:

- both ingest commands return files_seen = 2, files_skipped = 0 and chunks_written = 2.
- SQLite contains two rows after both imports, as already proven by PipelineTest.
- the first search result has source incident_codes.txt and includes its score and text.

- [ ] **Step 7: Commit Task 8**

~~~powershell
git add demo/offline_parsing_learning/cli.py demo/offline_parsing_learning/sample_docs tests/test_offline_parsing_learning.py
git commit -m "feat: complete offline parsing learning demo"
~~~

## Completion Check

Before calling the learning Demo complete, verify all of the following:

- tests/test_offline_parsing_learning.py passes.
- python -m unittest discover passes or any unrelated pre-existing failure is documented exactly.
- repeated ingest does not increase SQLite row count.
- search returns incident_codes.txt first for E203 地址校验失败.
- git status shows no accidental changes under demo/offline_parsing, rag_app or tests/test_offline_parsing_demo.py.
- no claim is made that Hash + SQLite demonstrates semantic quality, production scale, OCR, Chroma, pgvector or production readiness.
