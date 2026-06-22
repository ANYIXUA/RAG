"""离线知识库构建与刷新流程。"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rag_app.indexing.chunking import WhitespaceChunker
from rag_app.core.config import Settings
from rag_app.indexing.embeddings import Embedder, create_embedder
from rag_app.ingestion.governance import (
    KnowledgeGovernancePolicy,
    failed_to_dict,
    skipped_to_dict,
)
from rag_app.ingestion.loaders import DirectoryDocumentLoader
from rag_app.core.models import Document, OfflineRefreshReport
from rag_app.indexing.vector_store import VectorRecord, VectorStore, create_vector_store


class OfflineKnowledgeBuilder:
    """只在离线阶段运行的知识库构建器。"""

    def __init__(
        self,
        settings: Settings,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
        chunker: WhitespaceChunker | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or create_embedder(settings)
        self.vector_store = vector_store or create_vector_store(settings)
        self.chunker = chunker or WhitespaceChunker(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "OfflineKnowledgeBuilder":
        return cls(Settings.from_env(base_dir=base_dir))

    def refresh(
        self,
        source_dir: Path | None = None,
        reset: bool = False,
        force: bool = False,
    ) -> OfflineRefreshReport:
        # 1. 确定本次刷新使用的知识源目录，并把治理规则绑定到该目录。
        #    这里先过滤掉配置、评测集、训练集和未审核外部资料，避免脏数据进入灰度知识库。
        actual_source_dir = source_dir or self.settings.data_dir
        #确定哪些数据可以进入知识库，哪些数据跳过
        governance_policy = KnowledgeGovernancePolicy(
            source_dir=actual_source_dir,
            registry_path=self.settings.knowledge_registry_path,
            default_status=self.settings.knowledge_default_status,
            require_approval_for_crawled=self.settings.require_approval_for_crawled,
        )
        load_report = DirectoryDocumentLoader(
            actual_source_dir,
            governance_policy=governance_policy,
            pdf_complex_parser=self.settings.pdf_complex_parser,
            pdf_bordered_table_parser=self.settings.pdf_bordered_table_parser,
            pdf_borderless_table_parser=self.settings.pdf_borderless_table_parser,
            pdf_semistructured_table_parser=self.settings.pdf_semistructured_table_parser,
        ).load_with_report()
        documents, quality_skipped = _apply_parse_quality_gate(
            documents=load_report.documents,
            settings=self.settings,
        )
        documents_by_source = {
            str(document.metadata["source_path"]): document
            for document in documents
        }

        # 2. manifest 是离线增量刷新的基准。
        #    它记录上一次入库文件的内容哈希、解析器版本和切片器版本，用来判断是否需要重建向量。
        manifest = {} if reset else self._load_manifest()
        manifest_files = manifest.get("files", {})

        #找出已经被删除的文档
        removed_sources = set(manifest_files) - set(documents_by_source)
        #找出被删除文档的旧document_id
        removed_document_ids = {
            manifest_files[source]["document_id"]
            for source in removed_sources
        }

        changed_documents: list[Document] = []#本次需要重新处理的文档
        changed_old_document_ids: set[str] = set()#发生变化的旧文档
        skipped = 0#本次不用重新处理的文档

        #重新遍历当前通过治理和质量检查后的文档
        parser_config_fingerprint = _parser_config_fingerprint(self.settings)
        for source_path, document in documents_by_source.items():
            previous = manifest_files.get(source_path)#不为空则说明上次处理过
            content_hash = str(document.metadata["content_hash"])#文档内容有更新hash值就会发生改变
            parser_version = str(document.metadata.get("parser_version", ""))#解析逻辑变更会影响解析后的文本内容
            chunker_version = getattr(self.chunker, "version", "unknown")#切片方式改变，向量也需要重建
            embedding_model = _embedding_fingerprint(self.settings)
            #满足任意一个条件，就需要重新治理
            if (
                force #是否强制刷新
                or previous is None
                or previous.get("content_hash") != content_hash
                or previous.get("parser_version") != parser_version
                or _document_parser_config_changed(
                    previous,
                    document,
                    parser_config_fingerprint,
                )
                or previous.get("chunker_version") != chunker_version
                or previous.get("embedding_model") != embedding_model
            ):
                changed_documents.append(document)
                if previous is not None:
                    changed_old_document_ids.add(str(previous["document_id"]))
            else:
                skipped += 1

        # 3. 为保证灰度版本的向量库干净，先删除已移除文件和已变更文件的旧切片。
        #    reset 表示全量重建，直接清空 collection；普通刷新只清理受影响 document_id。
        if reset:
            self.vector_store.clear() #清空整个向量库
        else:
            self.vector_store.delete_by_document_ids(#只删除受影响的文档
                removed_document_ids | changed_old_document_ids
            )

        # 4. 只对变化文档重新切片和向量化。
        #    这能降低刷新成本，也减少灰度发布前构建窗口里的不确定性。
        chunks = self.chunker.split_documents(changed_documents)#切片
        embeddings = self.embedder.embed([chunk.text for chunk in chunks])#向量化
        document_metadata_by_id = {
            document.id: document.metadata
            for document in changed_documents
        }
        records = [#构造写入向量库的记录
            VectorRecord(
                chunk=chunk,
                embedding=embedding,
                document_metadata=document_metadata_by_id.get(chunk.document_id),
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        stored_records = self.vector_store.upsert(records) if records else self.vector_store.count()

        # 5. 写回新的 manifest。
        #    除了哈希和版本，也保留治理状态、业务模块、parser/chunker 信息，方便回溯某个知识版本如何构建。

        next_manifest_files = {#先保留没有被删除的旧纪录
            source: value
            for source, value in manifest_files.items()
            if source not in removed_sources
        }
        chunk_counts = _count_chunks_by_document(chunks)#统计每个文档切了多少个chunk
        refreshed_at = _utc_now()#记录本次的刷新时间
        for document in changed_documents:
            source_path = str(document.metadata["source_path"])
            #用当前文档的新信息，覆盖旧信息
            next_manifest_files[source_path] = {
                "document_id": document.id,
                "content_hash": document.metadata["content_hash"],
                "source": document.metadata.get("source"),
                "filename": document.metadata.get("filename"),
                "extension": document.metadata.get("extension"),
                "title": document.metadata.get("title"),
                "source_type": document.metadata.get("source_type"),
                "business_module": document.metadata.get("business_module"),
                "knowledge_status": document.metadata.get("knowledge_status"),
                "review_status": document.metadata.get("review_status"),
                "reviewer": document.metadata.get("reviewer"),
                "reviewed_at": document.metadata.get("reviewed_at"),
                "knowledge_version": document.metadata.get("knowledge_version"),
                "governance_source": document.metadata.get("governance_source"),
                "parser_name": document.metadata.get("parser_name"),
                "parser_version": document.metadata.get("parser_version"),
                "parser_config_fingerprint": _document_parser_config_fingerprint(
                    document,
                    parser_config_fingerprint,
                ),
                "parse_quality_status": document.metadata.get("parse_quality_status"),
                "parse_warnings": document.metadata.get("parse_warnings"),
                "ocr_required": document.metadata.get("ocr_required"),
                "page_count": document.metadata.get("page_count"),
                "empty_page_count": document.metadata.get("empty_page_count"),
                "low_text_page_count": document.metadata.get("low_text_page_count"),
                "scanned_page_candidates": document.metadata.get("scanned_page_candidates"),
                "table_like_page_count": document.metadata.get("table_like_page_count"),
                "chunker_version": getattr(self.chunker, "version", "unknown"),
                "embedding_provider": self.settings.embedding_provider,
                "embedding_model": _embedding_fingerprint(self.settings),
                "embedding_dimension": self.settings.embedding_dimension,
                "chunk_count": chunk_counts.get(document.id, 0),
                "refreshed_at": refreshed_at,
            }

        # 6. refresh_report 面向运维和发布检查，记录本次刷新看到、跳过、失败和入库的数量。
        #新的manifest写入磁盘，记录的是本次知识库的最后一个状态
        self._save_manifest(
            {
                "version": 1,
                "collection_name": self.settings.collection_name,
                "source_dir": str(actual_source_dir),
                "vector_store_path": self.settings.vector_store_location,
                "refreshed_at": refreshed_at,
                "governance": { #记录治理规则和统计信息
                    "registry_path": str(self.settings.knowledge_registry_path),
                    "default_status": self.settings.knowledge_default_status,
                    "require_approval_for_crawled": self.settings.require_approval_for_crawled,
                    "parse_quality_gate_enabled": self.settings.parse_quality_gate_enabled,
                    "allowed_parse_quality_statuses": list(
                        self.settings.allowed_parse_quality_statuses
                    ),
                    "files_seen": load_report.files_seen,
                    "skipped_by_policy": len(load_report.skipped) + len(quality_skipped),
                    "failed": len(load_report.failed),
                },
                "files": next_manifest_files,
            }
        )

        report = OfflineRefreshReport( #离线刷新的报告
            source_dir=str(actual_source_dir),
            manifest_path=str(self.settings.manifest_path),
            vector_store_path=self.settings.vector_store_location,
            documents_seen=len(documents),
            documents_changed=len(changed_documents),
            documents_skipped=skipped,
            documents_removed=len(removed_sources),
            chunks_embedded=len(chunks),
            stored_records=stored_records,
            files_seen=load_report.files_seen,
            documents_skipped_by_policy=len(load_report.skipped) + len(quality_skipped),
            documents_failed=len(load_report.failed),
            skipped_files=[*skipped_to_dict(load_report.skipped), *quality_skipped],
            failed_files=failed_to_dict(load_report.failed),
            refresh_report_path=str(self.settings.refresh_report_path),
            manifest_backup_path=str(self.settings.manifest_backup_path),
        )
        self._save_refresh_report(report)
        return report

    def _load_manifest(self) -> dict[str, Any]:
        if not self.settings.manifest_path.exists():
            return {"version": 1, "files": {}}
        return json.loads(self.settings.manifest_path.read_text(encoding="utf-8"))

    def _save_manifest(self, manifest: dict[str, Any]) -> None:
        self.settings.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        if self.settings.manifest_path.exists():
            self.settings.manifest_backup_path.write_text(
                self.settings.manifest_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
        self.settings.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_refresh_report(self, report: OfflineRefreshReport) -> None:
        self.settings.refresh_report_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.refresh_report_path.write_text(
            json.dumps(asdict(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _count_chunks_by_document(chunks) -> dict[str, int]:
    counts: dict[str, int] = {}
    for chunk in chunks:
        counts[chunk.document_id] = counts.get(chunk.document_id, 0) + 1
    return counts


def _embedding_fingerprint(settings: Settings) -> str:
    """记录会影响向量结果的 Embedding 配置，用于增量刷新判断。"""

    if settings.embedding_provider == "openai":
        return f"openai:{settings.openai_embedding_model}:{settings.embedding_dimension}"
    return f"{settings.embedding_provider}:{settings.embedding_dimension}"


def _document_parser_config_changed(
    previous: dict[str, Any],
    document: Document,
    parser_config_fingerprint: str,
) -> bool:
    if not _is_pdf_document(document):
        return False
    return previous.get("parser_config_fingerprint") != parser_config_fingerprint


def _document_parser_config_fingerprint(
    document: Document,
    parser_config_fingerprint: str,
) -> str | None:
    return parser_config_fingerprint if _is_pdf_document(document) else None


def _is_pdf_document(document: Document) -> bool:
    extension = str(document.metadata.get("extension") or "").strip().lower()
    media_type = str(document.metadata.get("media_type") or "").strip().lower()
    parser_name = str(document.metadata.get("parser_name") or "").strip().lower()
    filename = str(document.metadata.get("filename") or document.metadata.get("source") or "")
    return (
        extension == ".pdf"
        or media_type == "pdf"
        or parser_name == "pdf"
        or filename.lower().endswith(".pdf")
    )


def _parser_config_fingerprint(settings: Settings) -> str:
    payload = {
        "pdf_complex_parser": settings.pdf_complex_parser,
        "pdf_bordered_table_parser": settings.pdf_bordered_table_parser,
        "pdf_borderless_table_parser": settings.pdf_borderless_table_parser,
        "pdf_semistructured_table_parser": settings.pdf_semistructured_table_parser,
        "pdf_ocr_enabled": _env_config_value("RAG_PDF_OCR_ENABLED"),
        "pdf_ocr_lang": _env_config_value("RAG_PDF_OCR_LANG"),
        "tesseract_cmd": _env_config_value("RAG_TESSERACT_CMD"),
        "mineru_online_enabled": _env_config_value("RAG_MINERU_ONLINE_ENABLED"),
        "mineru_online_api_base": _env_config_value("RAG_MINERU_ONLINE_API_BASE"),
        "mineru_online_language": _env_config_value("RAG_MINERU_ONLINE_LANGUAGE"),
        "mineru_online_enable_table": _env_config_value("RAG_MINERU_ONLINE_ENABLE_TABLE"),
        "mineru_online_enable_ocr": _env_config_value("RAG_MINERU_ONLINE_ENABLE_OCR"),
        "mineru_online_enable_formula": _env_config_value("RAG_MINERU_ONLINE_ENABLE_FORMULA"),
        "mineru_online_page_range": _env_config_value("RAG_MINERU_ONLINE_PAGE_RANGE"),
        "mineru_online_token_hash": _secret_config_fingerprint(
            os.getenv("RAG_MINERU_ONLINE_TOKEN") or os.getenv("MINERU_API_TOKEN")
        ),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _env_config_value(name: str) -> str:
    return str(os.getenv(name, "")).strip()


def _secret_config_fingerprint(value: str | None) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def _apply_parse_quality_gate(
    documents: list[Document],
    settings: Settings,
) -> tuple[list[Document], list[dict[str, str]]]:
    """发布门禁：低质量解析结果不进入正式向量索引。"""

    if not settings.parse_quality_gate_enabled:
        return documents, []

    allowed = set(settings.allowed_parse_quality_statuses)
    accepted: list[Document] = []
    skipped: list[dict[str, str]] = []
    for document in documents:
        status = str(document.metadata.get("parse_quality_status") or "parsed_success")
        if status in allowed and not bool(document.metadata.get("ocr_required", False)):
            accepted.append(document)
            continue
        skipped.append(
            {
                "source": str(document.metadata.get("source") or document.metadata.get("filename") or document.id),
                "reason": "parse_quality_gate",
                "detail": (
                    f"解析质量状态为 {status}，ocr_required="
                    f"{bool(document.metadata.get('ocr_required', False))}，未进入正式索引"
                ),
            }
        )
    return accepted, skipped


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
