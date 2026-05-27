"""知识入库治理策略。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from dataclasses import replace
from pathlib import Path
from typing import Any

from rag_app.core.models import Document


APPROVED_STATUSES = {"approved", "published", "active"}
BLOCKED_STATUSES = {"draft", "pending", "pending_review", "rejected", "deprecated"}
SYSTEM_FILENAMES = {
    "knowledge_registry.json",
    "knowledge_sources.json",
}
DATASET_NAME_PARTS = ("retrieval_eval", "embedding_dataset", "training_dataset")


@dataclass(frozen=True) #自动生成__init__的工具，frozen=True表示对象创建后字段不能再修改
class GovernanceDecision:
    """单个文件是否允许进入知识库的判断结果。"""

    accepted: bool
    reason: str
    detail: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SkippedFile:
    """被治理策略跳过的文件。"""

    source: str
    reason: str
    detail: str


@dataclass(frozen=True)
class FailedFile:
    """解析失败的文件。"""

    source: str
    reason: str
    detail: str


@dataclass(frozen=True)
class DocumentLoadReport:
    """目录加载后的文档、跳过和失败统计。"""

    documents: list[Document]
    files_seen: int
    skipped: list[SkippedFile]
    failed: list[FailedFile]


class KnowledgeGovernancePolicy:
    """判断知识文件是否允许入库。"""

    def __init__(
        self,
        source_dir: Path,
        registry_path: Path | None = None,
        default_status: str = "approved",
        require_approval_for_crawled: bool = True,
    ) -> None:
        self.source_dir = source_dir.resolve()
        self.registry_path = registry_path
        self.default_status = _normalize_status(default_status)
        self.require_approval_for_crawled = require_approval_for_crawled
        self.registry = _load_registry(registry_path)

    def precheck_path(self, path: Path) -> GovernanceDecision:
        """在解析前跳过明显不是知识正文的文件。"""

        relative_source = self.relative_source(path)
        filename = path.name.lower()
        suffix = path.suffix.lower()
        if filename in SYSTEM_FILENAMES:
            return GovernanceDecision(
                accepted=False,
                reason="system_file",
                detail="系统配置或治理清单不进入知识库",
            )
        if suffix == ".jsonl" or any(part in filename for part in DATASET_NAME_PARTS):
            return GovernanceDecision(
                accepted=False,
                reason="dataset_file",
                detail="训练集或评测集不进入知识库",
            )
        if any(part.startswith(".") for part in Path(relative_source).parts):
            return GovernanceDecision(
                accepted=False,
                reason="hidden_file",
                detail="隐藏目录或隐藏文件不进入知识库",
            )
        return GovernanceDecision(accepted=True, reason="candidate", detail="候选知识文件")

    def evaluate_document(self, document: Document) -> GovernanceDecision:
        """根据元数据、front matter 和治理清单判断文档是否入库。"""

        metadata = dict(document.metadata)
        relative_source = _normalize_source(str(metadata.get("source") or ""))
        registry_entry = self.registry.get(relative_source, {})
        is_crawled = _is_crawled_document(relative_source, metadata)
        explicit_status = (
            registry_entry.get("status")
            or registry_entry.get("knowledge_status")
            or metadata.get("knowledge_status")
            or metadata.get("review_status")
        )
        if explicit_status is None and is_crawled and self.require_approval_for_crawled:
            explicit_status = "pending_review"
        status = _normalize_status(str(explicit_status or self.default_status))

        if is_crawled and self.require_approval_for_crawled and status not in APPROVED_STATUSES:
            return GovernanceDecision(
                accepted=False,
                reason="pending_review",
                detail="外部网页资料需要人工审核为 approved 后才能入库",
                metadata=_governance_metadata(
                    status=status,
                    registry_entry=registry_entry,
                    fallback_metadata=metadata,
                    source="registry" if registry_entry else "front_matter_or_default",
                ),
            )
        if status in BLOCKED_STATUSES:
            return GovernanceDecision(
                accepted=False,
                reason=status,
                detail=f"知识状态为 {status}，不进入主知识库",
                metadata=_governance_metadata(
                    status=status,
                    registry_entry=registry_entry,
                    fallback_metadata=metadata,
                    source="registry" if registry_entry else "front_matter_or_default",
                ),
            )
        if status not in APPROVED_STATUSES:
            return GovernanceDecision(
                accepted=False,
                reason="unknown_status",
                detail=f"未知知识状态：{status}",
                metadata=_governance_metadata(
                    status=status,
                    registry_entry=registry_entry,
                    fallback_metadata=metadata,
                    source="registry" if registry_entry else "front_matter_or_default",
                ),
            )

        return GovernanceDecision(
            accepted=True,
            reason="approved",
            detail="知识已通过治理策略",
            metadata=_governance_metadata(
                status=status,
                registry_entry=registry_entry,
                fallback_metadata=metadata,
                source="registry" if registry_entry else "default_curated_policy",
            ),
        )

    def apply_metadata(self, document: Document, decision: GovernanceDecision) -> Document:
        """把治理元数据写入文档，便于后续切片和 manifest 追踪。"""

        metadata = {**document.metadata, **decision.metadata}
        return replace(document, metadata=metadata)

    def relative_source(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.source_dir).as_posix()
        except ValueError:
            return path.as_posix()


def skipped_to_dict(items: list[SkippedFile]) -> list[dict[str, str]]:
    """把跳过明细转换为可 JSON 序列化的结构。"""

    return [
        {"source": item.source, "reason": item.reason, "detail": item.detail}
        for item in items
    ]


def failed_to_dict(items: list[FailedFile]) -> list[dict[str, str]]:
    """把失败明细转换为可 JSON 序列化的结构。"""

    return [
        {"source": item.source, "reason": item.reason, "detail": item.detail}
        for item in items
    ]


def _load_registry(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("entries"), list):
        return {
            _normalize_source(str(item["path"])): dict(item)
            for item in payload["entries"]
            if isinstance(item, dict) and item.get("path")
        }
    if isinstance(payload, dict):
        return {
            _normalize_source(str(key)): dict(value)
            for key, value in payload.items()
            if isinstance(value, dict)
        }
    raise ValueError("knowledge registry must be an object or contain entries array")


def _governance_metadata(
    status: str,
    registry_entry: dict[str, Any],
    fallback_metadata: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    review_status = str(
        registry_entry.get("review_status")
        or fallback_metadata.get("review_status")
        or status
    )
    return {
        "knowledge_status": status,
        "review_status": review_status,
        "reviewer": registry_entry.get("reviewer") or fallback_metadata.get("reviewer"),
        "reviewed_at": registry_entry.get("reviewed_at") or fallback_metadata.get("reviewed_at"),
        "knowledge_version": registry_entry.get("version")
        or fallback_metadata.get("knowledge_version")
        or fallback_metadata.get("version"),
        "governance_source": source,
    }


def _is_crawled_document(relative_source: str, metadata: dict[str, Any]) -> bool:
    source_type = str(metadata.get("source_type") or "").lower()
    parts = Path(relative_source).parts
    return (
        source_type == "web_crawl"
        or "crawled" in {part.lower() for part in parts}
    )


def _normalize_source(value: str) -> str:
    return value.replace("\\", "/").strip()


def _normalize_status(value: str) -> str:
    return value.strip().lower().replace("-", "_")
