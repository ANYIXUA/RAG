"""文档加载工具。"""

from __future__ import annotations

from pathlib import Path

from rag_app.ingestion.governance import (
    DocumentLoadReport,
    FailedFile,
    GovernanceDecision,
    KnowledgeGovernancePolicy,
    SkippedFile,
)
from rag_app.core.models import Document
from rag_app.ingestion.parsing import parse_document_file


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".rst",
    ".csv",
    ".json",
    ".jsonl",
    ".html",
    ".htm",
    ".docx",
    ".xlsx",
    ".pdf",
    ".pptx",
    ".srt",
    ".vtt",
}


class DirectoryDocumentLoader:
    """从目录树中加载文本类文件。"""

    def __init__(
        self,
        source_dir: Path,
        extensions: set[str] | None = None,
        governance_policy: KnowledgeGovernancePolicy | None = None,
    ) -> None:
        self.source_dir = source_dir
        self.extensions = extensions or SUPPORTED_EXTENSIONS #确认支持的文件后缀
        self.governance_policy = governance_policy or KnowledgeGovernancePolicy(#绑定治理策略
            source_dir=source_dir
        )

    def load(self) -> list[Document]:
        """兼容旧调用：只返回允许入库的文档列表。"""

        return self.load_with_report().documents

    def load_with_report(self) -> DocumentLoadReport:
        """加载目录并返回治理跳过、解析失败和入库文档明细。"""

        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory does not exist: {self.source_dir}")
        if not self.source_dir.is_dir():
            raise NotADirectoryError(f"Source path must be a directory: {self.source_dir}")

        documents: list[Document] = []
        skipped: list[SkippedFile] = []
        failed: list[FailedFile] = []
        files_seen = 0
        for path in sorted(self.source_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in self.extensions:
                continue
            files_seen += 1
            precheck = self.governance_policy.precheck_path(path)
            if not precheck.accepted:
                skipped.append(_skipped_file(path, self.governance_policy, precheck))
                continue
            try:#调用解析器解析文档
                document = parse_document_file(path, source_dir=self.source_dir)
            except Exception as exc:  # noqa: BLE001 - 离线刷新需要报告失败明细后继续处理其他文件。
                failed.append(
                    FailedFile(
                        source=self.governance_policy.relative_source(path),
                        reason=type(exc).__name__,
                        detail=str(exc),
                    )
                )
                continue
            if document is not None:#解析成果，做文档治理
                decision = self.governance_policy.evaluate_document(document)
                if decision.accepted: #治理通过，写入治理元数据
                    documents.append(
                        self.governance_policy.apply_metadata(document, decision)
                    )
                else: #解析成功，治理不通过，加入skippped
                    source = str(
                        document.metadata.get("source") or path.name
                    ).replace("\\", "/")
                    skipped.append(
                        SkippedFile(
                            source=source,
                            reason=decision.reason,
                            detail=decision.detail,
                        )
                    )
            else:
                skipped.append(
                    SkippedFile(
                        source=self.governance_policy.relative_source(path),
                        reason="empty_document",
                        detail="解析后正文为空",
                    )
                )
        return DocumentLoadReport(
            documents=documents,
            files_seen=files_seen,
            skipped=skipped,
            failed=failed,
        )


def _skipped_file(
    path: Path,
    policy: KnowledgeGovernancePolicy,
    decision: GovernanceDecision,
) -> SkippedFile:
    return SkippedFile(
        source=policy.relative_source(path),
        reason=decision.reason,
        detail=decision.detail,
    )
