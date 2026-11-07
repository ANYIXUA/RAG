"""Sync RAG offline parsing outputs into a Dify knowledge base."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol
from datetime import datetime, timezone

from rag_app.core.config import Settings


class DifySyncError(RuntimeError):
    pass


class DifyDocumentClient(Protocol):
    def create_document_by_text(self, dataset_id: str, payload: dict) -> dict:
        ...

    def update_document_by_text(self, dataset_id: str, document_id: str, payload: dict) -> dict:
        ...


@dataclass(frozen=True)
class DifySyncItem:
    source_path: str
    action: str
    status: str
    dify_document_id: str | None = None
    dify_batch_id: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class DifySyncResult:
    dataset_id: str
    dry_run: bool
    created: int = 0
    updated: int = 0
    disabled: int = 0
    skipped: int = 0
    failed: int = 0
    items: list[DifySyncItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [asdict(item) for item in self.items]
        return payload


class UrlLibDifyDocumentClient:
    def __init__(self, api_base_url: str, api_key: str, timeout_seconds: int = 30) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def create_document_by_text(self, dataset_id: str, payload: dict) -> dict:
        return self._post_json(
            f"/datasets/{dataset_id}/document/create-by-text",
            payload,
        )

    def update_document_by_text(self, dataset_id: str, document_id: str, payload: dict) -> dict:
        return self._post_json(
            f"/datasets/{dataset_id}/documents/{document_id}/update-by-text",
            payload,
        )

    def _post_json(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.api_base_url}{path}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            raise DifySyncError(str(exc)) from exc


class JsonDifySyncStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "documents": {}}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {"version": 1, "documents": {}}
        documents = payload.get("documents")
        if not isinstance(documents, dict):
            payload["documents"] = {}
        payload.setdefault("version", 1)
        return payload

    def save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class DifyDocumentSyncService:
    def __init__(
        self,
        *,
        settings: Settings,
        client: DifyDocumentClient,
        state_store: JsonDifySyncStateStore | None = None,
    ) -> None:
        self.settings = settings
        self.client = client
        self.state_store = state_store or JsonDifySyncStateStore(default_state_path(settings))

    def sync(self, dataset_id: str, *, dry_run: bool = False) -> DifySyncResult:
        manifest = _load_manifest(self.settings.manifest_path)
        manifest_files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
        state = self.state_store.load()
        documents = state.setdefault("documents", {})
        items: list[DifySyncItem] = []
        counters = {"created": 0, "updated": 0, "disabled": 0, "skipped": 0, "failed": 0}

        current_paths = set()
        for source_path, manifest_entry in manifest_files.items():
            source_key = str(source_path)
            current_paths.add(source_key)
            entry = manifest_entry if isinstance(manifest_entry, dict) else {}
            if not _is_quality_allowed(entry, self.settings):
                counters["skipped"] += 1
                items.append(DifySyncItem(source_key, "skip", "parse_quality_skipped"))
                continue
            source_file = Path(source_key)
            if not source_file.exists():
                counters["failed"] += 1
                items.append(DifySyncItem(source_key, "sync", "failed", error="source_file_missing"))
                continue
            previous = documents.get(source_key)
            action = _resolve_action(previous, entry, dataset_id)
            if action == "skip":
                counters["skipped"] += 1
                items.append(
                    DifySyncItem(
                        source_key,
                        "skip",
                        "unchanged",
                        dify_document_id=str(previous.get("dify_document_id")) if previous else None,
                    )
                )
                continue
            if dry_run:
                counters["created" if action == "create" else "updated"] += 1
                items.append(DifySyncItem(source_key, action, "dry_run"))
                continue
            try:
                payload = _document_payload(source_file, entry)
                if action == "create":
                    response = self.client.create_document_by_text(dataset_id, payload)
                    counters["created"] += 1
                else:
                    assert previous is not None
                    response = self.client.update_document_by_text(
                        dataset_id,
                        str(previous["dify_document_id"]),
                        payload,
                    )
                    counters["updated"] += 1
                dify_document_id = _response_document_id(response) or (
                    str(previous.get("dify_document_id")) if previous else None
                )
                dify_batch_id = _response_batch_id(response)
                documents[source_key] = _state_entry(
                    source_path=source_key,
                    dataset_id=dataset_id,
                    entry=entry,
                    dify_document_id=dify_document_id,
                    dify_batch_id=dify_batch_id,
                    status="synced",
                    error=None,
                )
                items.append(
                    DifySyncItem(
                        source_key,
                        action,
                        "synced",
                        dify_document_id=dify_document_id,
                        dify_batch_id=dify_batch_id,
                    )
                )
            except Exception as exc:
                counters["failed"] += 1
                documents[source_key] = _state_entry(
                    source_path=source_key,
                    dataset_id=dataset_id,
                    entry=entry,
                    dify_document_id=(str(previous.get("dify_document_id")) if previous else None),
                    dify_batch_id=(str(previous.get("dify_batch_id")) if previous else None),
                    status="failed",
                    error=str(exc),
                )
                items.append(DifySyncItem(source_key, action, "failed", error=str(exc)))

        for source_path, previous in list(documents.items()):
            if source_path in current_paths or previous.get("dify_dataset_id") != dataset_id:
                continue
            counters["disabled"] += 1
            items.append(
                DifySyncItem(
                    source_path,
                    "disable",
                    "dry_run" if dry_run else "stale",
                    dify_document_id=str(previous.get("dify_document_id") or ""),
                )
            )
            if not dry_run:
                previous["sync_status"] = "stale"
                previous["last_error"] = None

        if not dry_run:
            self.state_store.save(state)
        return DifySyncResult(
            dataset_id=dataset_id,
            dry_run=dry_run,
            created=counters["created"],
            updated=counters["updated"],
            disabled=counters["disabled"],
            skipped=counters["skipped"],
            failed=counters["failed"],
            items=items,
        )


def create_dify_document_sync_service(settings: Settings) -> DifyDocumentSyncService:
    if not settings.dify_api_base_url:
        raise ValueError("RAG_DIFY_API_BASE_URL is required for Dify document sync")
    if not settings.dify_api_key:
        raise ValueError("RAG_DIFY_API_KEY is required for Dify document sync")
    return DifyDocumentSyncService(
        settings=settings,
        client=UrlLibDifyDocumentClient(
            api_base_url=settings.dify_api_base_url,
            api_key=settings.dify_api_key,
            timeout_seconds=settings.dify_sync_timeout_seconds,
        ),
    )


def default_state_path(settings: Settings) -> Path:
    return settings.storage_dir / f"{settings.collection_name}_dify_sync_state.json"


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "files": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {"version": 1, "files": {}}


def _is_quality_allowed(entry: dict[str, Any], settings: Settings) -> bool:
    status = str(entry.get("parse_quality_status") or "parsed_success")
    return status in set(settings.allowed_parse_quality_statuses) and not bool(entry.get("ocr_required", False))


def _resolve_action(previous: dict[str, Any] | None, entry: dict[str, Any], dataset_id: str) -> str:
    if not previous or previous.get("dify_dataset_id") != dataset_id or not previous.get("dify_document_id"):
        return "create"
    for key in ("content_hash", "parser_version", "chunker_version"):
        if str(previous.get(key) or "") != str(entry.get(key) or ""):
            return "update"
    return "skip"


def _document_payload(source_file: Path, entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(entry.get("filename") or source_file.name),
        "text": source_file.read_text(encoding="utf-8"),
        "indexing_technique": "high_quality",
        "doc_form": "text_model",
        "doc_language": "Chinese",
        "original_document_id": str(entry.get("document_id") or source_file.stem),
    }


def _response_document_id(response: dict[str, Any]) -> str | None:
    document = response.get("document") if isinstance(response, dict) else None
    if isinstance(document, dict) and document.get("id"):
        return str(document["id"])
    return None


def _response_batch_id(response: dict[str, Any]) -> str | None:
    if isinstance(response, dict) and response.get("batch"):
        return str(response["batch"])
    return None


def _state_entry(
    *,
    source_path: str,
    dataset_id: str,
    entry: dict[str, Any],
    dify_document_id: str | None,
    dify_batch_id: str | None,
    status: str,
    error: str | None,
) -> dict[str, Any]:
    return {
        "source_path": source_path,
        "document_id": entry.get("document_id"),
        "content_hash": entry.get("content_hash"),
        "parser_version": entry.get("parser_version"),
        "chunker_version": entry.get("chunker_version"),
        "parse_quality_status": entry.get("parse_quality_status"),
        "tenant_id": entry.get("tenant_id"),
        "permission_tags": entry.get("permission_tags"),
        "dify_dataset_id": dataset_id,
        "dify_document_id": dify_document_id,
        "dify_batch_id": dify_batch_id,
        "sync_status": status,
        "last_synced_at": _utc_now(),
        "last_error": error,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
